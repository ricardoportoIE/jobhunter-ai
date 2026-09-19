"""Reviewed profile/job versions are copied into reproducible analysis snapshots."""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import Field

from jobhunter_api.auth import Actor, settings_for
from jobhunter_api.errors import Problem
from jobhunter_api.profile import Input, Text
from jobhunter_api.records import audit, get_record, insert, owner_lock, profile, public
from jobhunter_api.scoring import eligible, evaluate
from jobhunter_api.store import Row, connect

router = APIRouter(prefix="/api/v1", tags=["matching"])


class Assessment(Input):
    requirement_id: UUID
    status: Literal["met", "partial", "unmet", "unknown"]
    reason: Text
    fact_ids: list[UUID] = Field(default_factory=list, max_length=50)


class Analysis(Input):
    job_version: int = Field(ge=1)
    profile_version: int = Field(ge=1)
    review_confirmed: Literal[True]
    assessments: list[Assessment] = Field(default_factory=list, max_length=100)
    ai_run_id: UUID | None = None


@router.post("/jobs/{job_id}/analyse", status_code=201)
def analyse(job_id: UUID, data: Analysis, actor: Actor, request: Request) -> Row:
    with connect(settings_for(request)) as db:
        owner_lock(db, actor.id)
        job, candidate = get_record(db, actor.id, "job", job_id), profile(db, actor.id)
        if job["version"] != data.job_version or candidate["version"] != data.profile_version:
            raise Problem(409, "VERSION_CONFLICT", "Atualize a vaga e o perfil antes de analisar.")
        if job["data"]["status"] == "DISCOVERED" or candidate["data"]["status"] != "reviewed":
            raise Problem(
                409, "REVIEW_REQUIRED", "Reveja a vaga e publique o perfil antes de analisar."
            )
        stored = db.execute(
            "SELECT data FROM snapshots WHERE owner_id=%s AND kind='profile' "
            "AND source_id=%s AND version=%s",
            (actor.id, candidate["id"], candidate["version"]),
        ).fetchone()
        if not stored:
            raise Problem(409, "REVIEW_REQUIRED", "Snapshot do perfil ausente.")
        assessments = [item.model_dump(mode="json") for item in data.assessments]
        if data.ai_run_id:
            suggestion = db.execute(
                "SELECT result FROM ai_calls WHERE id=%s AND owner_id=%s "
                "AND operation='suggest' AND status='succeeded'",
                (data.ai_run_id, actor.id),
            ).fetchone()
            if (
                not suggestion
                or suggestion["result"]["job_id"] != str(job_id)
                or suggestion["result"]["job_version"] != data.job_version
                or suggestion["result"]["profile_version"] != data.profile_version
            ):
                raise Problem(409, "STALE_SUGGESTION", "Sugestão de IA ausente ou desatualizada.")
        at = datetime.now(UTC)
        try:
            result = evaluate(public(job), stored["data"], assessments, at)
        except ValueError:
            raise Problem(
                422, "INVALID_ASSESSMENT", "Confira requisitos e referências de fatos."
            ) from None
        row = insert(
            db,
            actor.id,
            "match",
            {
                **result,
                "job_id": str(job_id),
                "job_version": job["version"],
                "profile_version": candidate["version"],
                "candidate_id": str(candidate["id"]),
                "job_snapshot": public(job),
                "profile_snapshot": stored["data"],
                "input_assessments": assessments,
                "reviewed_by": str(actor.id),
                "ai_run_id": str(data.ai_run_id) if data.ai_run_id else None,
            },
        )
        # SCORED is derived workflow metadata, not an edit to reviewed source content.
        db.execute(
            "UPDATE records SET data=jsonb_set(data,'{status}','\"SCORED\"') "
            "WHERE id=%s AND owner_id=%s",
            (job_id, actor.id),
        )
        audit(db, actor.id, "job.scored", job_id, job["version"])
        return {**public(row), "stale": False}


@router.get("/matches/{match_id}")
def match(match_id: UUID, actor: Actor, request: Request) -> Row:
    with connect(settings_for(request)) as db:
        owner_lock(db, actor.id)
        row = get_record(db, actor.id, "match", match_id)
        candidate = profile(db, actor.id)
        job = get_record(db, actor.id, "job", UUID(row["data"]["job_id"]))
        stale = (
            candidate["version"] != row["data"]["profile_version"]
            or job["version"] != row["data"]["job_version"]
        )
        snapshot = row["data"]["profile_snapshot"]
        evidence = {e["id"]: e for e in snapshot["evidence"]}
        used = {fid for a in row["data"]["input_assessments"] for fid in a["fact_ids"]}
        stale |= any(
            not eligible(fact, evidence, datetime.now(UTC))
            for fact in snapshot["facts"]
            if fact["id"] in used
        )
        return {**public(row), "stale": stale}


@router.get("/jobs/{job_id}/matches")
def job_matches(job_id: UUID, actor: Actor, request: Request) -> list[Row]:
    with connect(settings_for(request)) as db:
        get_record(db, actor.id, "job", job_id)
        rows = db.execute(
            "SELECT * FROM records WHERE owner_id=%s AND kind='match' "
            "AND data->>'job_id'=%s ORDER BY updated_at DESC LIMIT 30",
            (actor.id, str(job_id)),
        ).fetchall()
        return [
            {
                "id": str(r["id"]),
                "score": r["data"]["score"],
                "coverage": r["data"]["coverage"],
                "created_at": r["data"]["created_at"],
            }
            for r in rows
        ]
