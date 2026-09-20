"""Owned application strategies, immutable revision history and explicit document approval."""

from datetime import UTC, datetime
from difflib import unified_diff
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Query, Request, Response
from psycopg.types.json import Jsonb
from pydantic import Field

from jobhunter_api.ai_budget import structured
from jobhunter_api.auth import Actor, settings_for
from jobhunter_api.deduplication import fingerprint
from jobhunter_api.document_rendering import artifact
from jobhunter_api.errors import Problem
from jobhunter_api.job_parser import get_provider
from jobhunter_api.package_domain import (
    STRATEGY_PROMPT,
    STRATEGY_VERSION,
    Selection,
    StrategyOutput,
    StrategyRequest,
    capture,
    check_current,
    compose,
    stale,
    validate_strategy,
    validation,
)
from jobhunter_api.profile import Input, Text, Version
from jobhunter_api.records import get_record, insert, owner_lock, public, update
from jobhunter_api.store import Connection, Row, connect

router = APIRouter(prefix="/api/v1", tags=["application packages"])


@router.get("/packages/{package_id}/download/{filename}")
def download(
    package_id: UUID,
    filename: Literal[
        "cv.docx",
        "cv.pdf",
        "cover-letter.docx",
        "cover-letter.pdf",
        "answers.json",
        "package.json",
        "bundle.zip",
    ],
    actor: Actor,
    request: Request,
    expected_version: int = Query(ge=1),
) -> Response:
    import hashlib

    with connect(settings_for(request)) as db:
        owner_lock(db, actor.id)
        row = get_record(db, actor.id, "package", package_id)
        payload = row["data"]
        check_current(db, actor.id, payload["snapshot"])
        if row["version"] != expected_version or payload["status"] != "APPROVED":
            raise Problem(
                409, "APPROVAL_REQUIRED", "Approve the current package version before downloading."
            )
        if payload["review"]["content_hash"] != fingerprint(payload["content"]):
            raise Problem(409, "CONTENT_CHANGED", "Content differs from the approved revision.")
        content, media = artifact(public(row), filename)
    return Response(
        content,
        media_type=media,
        headers={
            "Content-Disposition": f'attachment; filename="package-v{expected_version}-{filename}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "X-Document-SHA256": hashlib.sha256(content).hexdigest(),
        },
    )


def checkpoint(db: Connection, row: Row) -> None:
    db.execute(
        "INSERT INTO snapshots (id,owner_id,kind,source_id,version,data) "
        "VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
        (uuid4(), row["owner_id"], row["kind"], row["id"], row["version"], Jsonb(row["data"])),
    )


@router.post("/jobs/{job_id}/strategy", status_code=201)
def strategy(job_id: UUID, data: StrategyRequest, actor: Actor, request: Request) -> Row:
    settings = settings_for(request)
    with connect(settings) as db:
        owner_lock(db, actor.id)
        snapshot = capture(db, actor.id, job_id, data)
    payload = {
        "job_id": str(job_id),
        "job_version": data.job_version,
        "profile_version": data.profile_version,
        "job": {
            k: snapshot["job"][k] for k in ("title", "company_name", "requirements", "risk_flags")
        },
        "facts": [
            {
                k: f[k]
                for k in ("id", "version", "claim", "category", "allowed_uses", "evidence_ids")
            }
            for f in snapshot["facts"]
        ],
        "evidence": [{k: e[k] for k in ("id", "version", "content")} for e in snapshot["evidence"]],
        "questions": data.questions,
    }
    # Verify that a document can be composed before reserving a paid call.
    cv = [f["id"] for f in snapshot["facts"] if "cv" in f["allowed_uses"]][:20]
    letter = [f["id"] for f in snapshot["facts"] if "cover_letter" in f["allowed_uses"]][:5]
    if not cv or not letter:
        raise Problem(
            422, "DOCUMENT_FACTS_REQUIRED", "Select authorised facts for CV and cover letter."
        )
    run_id = None
    if data.use_ai:
        if not data.external_processing_confirmed:
            raise Problem(422, "CONSENT_REQUIRED", "Confirm sending facts and questions to OpenAI.")
        response = structured(
            settings,
            get_provider(settings),
            actor.id,
            "strategy",
            request.headers.get("idempotency-key"),
            payload,
            STRATEGY_PROMPT,
            STRATEGY_VERSION,
            StrategyOutput,
            lambda output: validate_strategy(output, snapshot),
        )
        result, run_id = response["result"], response["run_id"]
    else:
        result = {
            "cv_fact_ids": cv,
            "letter_fact_ids": letter,
            "focus": [
                {
                    "requirement_id": r["id"],
                    "fact_ids": [],
                    "explanation": "Review evidence and gaps manually.",
                }
                for r in snapshot["job"]["requirements"]
            ],
            "answers": [{"question_index": i, "fact_ids": []} for i in range(len(data.questions))],
            "risks": ["Manual strategy: selection without AI relevance evaluation."],
            "interview_points": [],
        }
    signature = fingerprint({"snapshot": snapshot, "result": result, "run_id": run_id})
    with connect(settings) as db:
        owner_lock(db, actor.id)
        check_current(db, actor.id, snapshot)
        previous = db.execute(
            "SELECT * FROM records WHERE owner_id=%s AND kind='strategy' "
            "AND data->>'signature'=%s AND NOT deleted",
            (actor.id, signature),
        ).fetchone()
        if previous:
            return public(previous)
        return public(
            insert(
                db,
                actor.id,
                "strategy",
                {
                    "job_id": str(job_id),
                    "snapshot": snapshot,
                    "selection": result,
                    "signature": signature,
                    "run_id": run_id,
                    "status": "NEEDS_REVIEW",
                    "created_at": datetime.now(UTC).isoformat(),
                    "reviewed_at": None,
                },
            )
        )


@router.get("/jobs/{job_id}/strategies")
def strategies(job_id: UUID, actor: Actor, request: Request) -> list[Row]:
    return listing(job_id, "strategy", actor, request)


@router.get("/jobs/{job_id}/packages")
def packages(job_id: UUID, actor: Actor, request: Request) -> list[Row]:
    return listing(job_id, "package", actor, request)


def listing(job_id: UUID, kind: str, actor: Actor, request: Request) -> list[Row]:
    with connect(settings_for(request)) as db:
        get_record(db, actor.id, "job", job_id)
        rows = db.execute(
            "SELECT * FROM records WHERE owner_id=%s AND kind=%s "
            "AND data->>'job_id'=%s AND NOT deleted ORDER BY updated_at DESC LIMIT 30",
            (actor.id, kind, str(job_id)),
        ).fetchall()
        return [{**public(r), "stale": stale(db, actor.id, r["data"]["snapshot"])} for r in rows]


@router.post("/strategies/{strategy_id}/approve")
def approve_strategy(strategy_id: UUID, data: Selection, actor: Actor, request: Request) -> Row:
    with connect(settings_for(request)) as db:
        owner_lock(db, actor.id)
        row = get_record(db, actor.id, "strategy", strategy_id)
        snapshot = row["data"]["snapshot"]
        check_current(db, actor.id, snapshot)
        selection = {
            **row["data"]["selection"],
            "cv_fact_ids": [str(i) for i in data.cv_fact_ids],
            "letter_fact_ids": [str(i) for i in data.letter_fact_ids],
        }
        try:
            validate_strategy(selection, snapshot)
        except ValueError:
            raise Problem(422, "INVALID_SELECTION", "Selection outside authorised uses.") from None
        checkpoint(db, row)
        return public(
            update(
                db,
                row,
                data.expected_version,
                {
                    **row["data"],
                    "selection": selection,
                    "status": "APPROVED",
                    "reviewed_at": datetime.now(UTC).isoformat(),
                    "reviewed_by": str(actor.id),
                },
            )
        )


class Generate(Input):
    strategy_id: UUID
    strategy_version: int = Field(ge=1)


@router.post("/jobs/{job_id}/generate-package", status_code=201)
def generate(job_id: UUID, data: Generate, actor: Actor, request: Request) -> Row:
    with connect(settings_for(request)) as db:
        owner_lock(db, actor.id)
        plan = get_record(db, actor.id, "strategy", data.strategy_id)
        if plan["data"]["job_id"] != str(job_id):
            raise Problem(404, "NOT_FOUND", "Strategy not found in this job.")
        if plan["version"] != data.strategy_version or plan["data"]["status"] != "APPROVED":
            raise Problem(409, "STRATEGY_REVIEW_REQUIRED", "Approve the current strategy version.")
        snapshot, selection = plan["data"]["snapshot"], plan["data"]["selection"]
        check_current(db, actor.id, snapshot)
        previous = db.execute(
            "SELECT * FROM records WHERE owner_id=%s AND kind='package' "
            "AND data->>'strategy_id'=%s AND (data->>'strategy_version')::int=%s "
            "AND NOT deleted",
            (actor.id, str(data.strategy_id), data.strategy_version),
        ).fetchone()
        if previous:
            return public(previous)
        content = compose(snapshot, selection)
        return public(
            insert(
                db,
                actor.id,
                "package",
                {
                    "job_id": str(job_id),
                    "strategy_id": str(data.strategy_id),
                    "strategy_version": data.strategy_version,
                    "snapshot": snapshot,
                    "selection": selection,
                    "content": content,
                    "content_hash": fingerprint(content),
                    "manual_answers": {},
                    "validation": validation(content, snapshot, selection, {}),
                    "status": "NEEDS_REVIEW",
                    "created_at": datetime.now(UTC).isoformat(),
                    "review": None,
                },
            )
        )


@router.get("/packages/{package_id}")
def read_package(package_id: UUID, actor: Actor, request: Request) -> Row:
    with connect(settings_for(request)) as db:
        row = get_record(db, actor.id, "package", package_id)
        return {**public(row), "stale": stale(db, actor.id, row["data"]["snapshot"])}


class Revise(Selection):
    manual_answers: dict[str, Text] = Field(default_factory=dict, max_length=20)
    attest_answers: bool = False


@router.patch("/packages/{package_id}")
def revise(package_id: UUID, data: Revise, actor: Actor, request: Request) -> Row:
    with connect(settings_for(request)) as db:
        owner_lock(db, actor.id)
        row = get_record(db, actor.id, "package", package_id)
        snapshot = row["data"]["snapshot"]
        check_current(db, actor.id, snapshot)
        if any(
            k not in {str(i) for i in range(len(snapshot["questions"]))}
            for k in data.manual_answers
        ):
            raise Problem(422, "INVALID_QUESTION", "Answer linked to non-existent question.")
        if data.manual_answers and not data.attest_answers:
            raise Problem(
                422, "ATTESTATION_REQUIRED", "Confirm the truthfulness of manual answers."
            )
        selection = {
            **row["data"]["selection"],
            "cv_fact_ids": [str(i) for i in data.cv_fact_ids],
            "letter_fact_ids": [str(i) for i in data.letter_fact_ids],
        }
        try:
            validate_strategy(selection, snapshot)
        except ValueError:
            raise Problem(
                422, "INVALID_SELECTION", "Facts not authorised for this document."
            ) from None
        content = compose(snapshot, selection, data.manual_answers)
        checkpoint(db, row)
        return public(
            update(
                db,
                row,
                data.expected_version,
                {
                    **row["data"],
                    "selection": selection,
                    "content": content,
                    "content_hash": fingerprint(content),
                    "manual_answers": data.manual_answers,
                    "review": None,
                    "manual_answers_attested_by": str(actor.id) if data.manual_answers else None,
                    "validation": validation(content, snapshot, selection, data.manual_answers),
                    "status": "NEEDS_REVIEW",
                },
            )
        )


class Review(Version):
    decision: Literal["approve", "reject"]
    review_confirmed: Literal[True]
    sensitive_review_confirmed: bool = False
    note: str = Field(default="", max_length=3000)


@router.post("/packages/{package_id}/review")
def review(package_id: UUID, data: Review, actor: Actor, request: Request) -> Row:
    with connect(settings_for(request)) as db:
        owner_lock(db, actor.id)
        row = get_record(db, actor.id, "package", package_id)
        payload = row["data"]
        check_current(db, actor.id, payload["snapshot"])
        checked = validation(
            payload["content"], payload["snapshot"], payload["selection"], payload["manual_answers"]
        )
        if data.decision == "approve":
            if not checked["valid"]:
                raise Problem(422, "VALIDATION_FAILED", "Resolve pending issues before approving.")
            if (
                any(a["classification"] == "SENSITIVE" for a in payload["content"]["answers"])
                and not data.sensitive_review_confirmed
            ):
                raise Problem(
                    422, "SENSITIVE_REVIEW_REQUIRED", "Confirm review of sensitive answers."
                )
        checkpoint(db, row)
        return public(
            update(
                db,
                row,
                data.expected_version,
                {
                    **payload,
                    "validation": checked,
                    "status": "APPROVED" if data.decision == "approve" else "REJECTED",
                    "review": {
                        "actor_id": str(actor.id),
                        "at": datetime.now(UTC).isoformat(),
                        "content_hash": payload["content_hash"],
                        **data.model_dump(exclude={"expected_version"}),
                    },
                },
            )
        )


@router.get("/packages/{package_id}/history")
def history(package_id: UUID, actor: Actor, request: Request) -> list[Row]:
    with connect(settings_for(request)) as db:
        row = get_record(db, actor.id, "package", package_id)
        previous = db.execute(
            "SELECT version,data FROM snapshots WHERE owner_id=%s "
            "AND kind='package' AND source_id=%s ORDER BY version",
            (actor.id, package_id),
        ).fetchall()
        return [
            {
                "version": r["version"],
                "status": r["data"]["status"],
                "content_hash": r["data"]["content_hash"],
            }
            for r in [*previous, row]
        ]


@router.get("/packages/{package_id}/diff")
def diff(package_id: UUID, actor: Actor, request: Request, from_version: int = Query(ge=1)) -> Row:
    import json

    with connect(settings_for(request)) as db:
        row = get_record(db, actor.id, "package", package_id)
        previous = db.execute(
            "SELECT data FROM snapshots WHERE owner_id=%s AND kind='package' "
            "AND source_id=%s AND version=%s",
            (actor.id, package_id, from_version),
        ).fetchone()
        if not previous:
            raise Problem(404, "NOT_FOUND", "Previous version not found.")
        a = json.dumps(previous["data"]["content"], ensure_ascii=False, indent=2).splitlines()
        b = json.dumps(row["data"]["content"], ensure_ascii=False, indent=2).splitlines()
        return {
            "from_version": from_version,
            "to_version": row["version"],
            "diff": "\n".join(
                unified_diff(
                    a, b, fromfile=f"v{from_version}", tofile=f"v{row['version']}", lineterm=""
                )
            ),
        }
