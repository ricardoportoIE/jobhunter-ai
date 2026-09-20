"""Similar text suggests review. Only an explicit versioned decision archives a duplicate."""

import re
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import Field

from jobhunter_api.auth import Actor, settings_for
from jobhunter_api.deduplication import identity_keys, normalized
from jobhunter_api.errors import Problem
from jobhunter_api.profile import Text, Version
from jobhunter_api.records import get_record, insert, owner_lock, public, update
from jobhunter_api.semantic import cosine, current_vectors
from jobhunter_api.store import Row, connect

router = APIRouter(prefix="/api/v1/ai/jobs", tags=["duplicate review"])


def jaccard(left: str, right: str) -> float:
    a, b = set(re.findall(r"\w+", normalized(left))), set(re.findall(r"\w+", normalized(right)))
    return len(a & b) / len(a | b) if a | b else 0


def conflicts(a: Row, b: Row) -> list[str]:
    result = []
    for field in ("location", "company_name"):
        left, right = a.get(field), b.get(field)
        if field == "location":
            left, right = left or a.get("location_hint"), right or b.get("location_hint")
        if left and right and normalized(left) != normalized(right):
            result.append(
                "LOCALIDADES_DIFERENTES" if field == "location" else "EMPRESAS_DIFERENTES"
            )
    return result


@router.get("/{job_id}/duplicates")
def candidates(job_id: UUID, actor: Actor, request: Request) -> Row:
    with connect(settings_for(request)) as db:
        job = get_record(db, actor.id, "job", job_id)
        others = db.execute(
            "SELECT * FROM records WHERE owner_id=%s AND kind='job' AND NOT deleted "
            "AND id<>%s AND (data->>'archived')::boolean=false ORDER BY updated_at DESC LIMIT 501",
            (actor.id, job_id),
        ).fetchall()
        if len(others) > 500:
            raise Problem(409, "DEDUPE_CAPACITY", "Archive old jobs to compare up to 500 jobs.")
        vectors: dict[str, list[list[float]]] = {}
        for row in current_vectors(db, actor.id, "job"):
            vectors.setdefault(str(row["source_id"]), []).append(row["vector"])
        means = {
            identity: [sum(column) / len(rows) for column in zip(*rows, strict=True)]
            for identity, rows in vectors.items()
        }
        reviews = db.execute(
            "SELECT data FROM records WHERE owner_id=%s AND kind='duplicate_review' "
            "AND NOT deleted",
            (actor.id,),
        ).fetchall()
    items = []
    for other in others:
        if any(
            r["data"]["decision"] == "distinct"
            and r["data"]["versions"]
            == {str(job_id): job["version"], str(other["id"]): other["version"]}
            for r in reviews
        ):
            continue
        lexical = jaccard(job["data"]["raw_text"], other["data"]["raw_text"])
        semantic = (
            cosine(means[str(job_id)], means[str(other["id"])])
            if str(job_id) in means and str(other["id"]) in means
            else None
        )
        identity = bool(set(identity_keys(job["data"])) & set(identity_keys(other["data"])))
        if identity or lexical >= 0.65 or (semantic is not None and semantic >= 0.90):
            items.append(
                {
                    "job": public(other),
                    "lexical_similarity": round(lexical, 4),
                    "semantic_similarity": round(semantic, 4) if semantic is not None else None,
                    "shared_identity": identity,
                    "conflicts": conflicts(job["data"], other["data"]),
                    "review_required": True,
                }
            )
    return {
        "items": sorted(
            items,
            key=lambda item: (
                item["shared_identity"],
                item["semantic_similarity"] or item["lexical_similarity"],
            ),
            reverse=True,
        )[:20],
        "compared": len(others),
        "automatic_merge": False,
    }


class DuplicateDecision(Version):
    target_id: UUID
    target_version: int = Field(ge=1)
    decision: Literal["duplicate", "distinct"]
    reason: Text
    review_confirmed: Literal[True]


@router.post("/{job_id}/duplicates")
def decide(job_id: UUID, data: DuplicateDecision, actor: Actor, request: Request) -> Row:
    if job_id == data.target_id:
        raise Problem(422, "INVALID_DUPLICATE", "Choose another job to compare.")
    with connect(settings_for(request)) as db:
        owner_lock(db, actor.id)
        job = get_record(db, actor.id, "job", job_id)
        target = get_record(db, actor.id, "job", data.target_id)
        versions = {str(job_id): data.expected_version, str(data.target_id): data.target_version}
        previous = db.execute(
            "SELECT * FROM records WHERE owner_id=%s AND kind='duplicate_review' "
            "AND data->>'job_id'=%s AND data->>'target_id'=%s ORDER BY updated_at DESC LIMIT 1",
            (actor.id, str(job_id), str(data.target_id)),
        ).fetchone()
        if (
            previous
            and previous["data"]["versions"] == versions
            and previous["data"]["decision"] == data.decision
        ):
            return public(previous)
        if job["version"] != data.expected_version or target["version"] != data.target_version:
            raise Problem(409, "VERSION_CONFLICT", "Update both jobs before deciding.")
        if data.decision == "duplicate":
            if conflicts(job["data"], target["data"]):
                raise Problem(
                    409, "DUPLICATE_CONFLICT", "Review company/location discrepancies first."
                )
            if target["data"]["archived"] or target["data"].get("duplicate_of"):
                raise Problem(409, "INVALID_TARGET", "Choose an active main job.")
            update(
                db,
                job,
                data.expected_version,
                {**job["data"], "archived": True, "duplicate_of": str(data.target_id)},
            )
        return public(
            insert(
                db,
                actor.id,
                "duplicate_review",
                {
                    "job_id": str(job_id),
                    "target_id": str(data.target_id),
                    "versions": versions,
                    "decision": data.decision,
                    "reason": data.reason,
                    "reviewed_by": str(actor.id),
                },
            )
        )
