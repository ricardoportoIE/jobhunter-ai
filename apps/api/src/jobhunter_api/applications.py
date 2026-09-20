"""Manual tracker. Records user actions; contains no outbound delivery operation."""

from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Query, Request, Response
from psycopg.types.json import Jsonb
from pydantic import Field

from jobhunter_api.auth import Actor, settings_for
from jobhunter_api.deduplication import fingerprint
from jobhunter_api.errors import Problem
from jobhunter_api.profile import Input, Text, Version
from jobhunter_api.records import get_record, insert, owner_lock, profile, public, update
from jobhunter_api.scoring import eligible
from jobhunter_api.store import Row, connect

router = APIRouter(prefix="/api/v1/applications", tags=["applications"])
TRANSITIONS = {
    "SHORTLISTED": {"RESEARCHED", "SUBMITTED", "WITHDRAWN", "EXPIRED"},
    "RESEARCHED": {"SUBMITTED", "WITHDRAWN", "EXPIRED"},
    "SUBMITTED": {"INTERVIEWING", "OFFERED", "REJECTED", "WITHDRAWN"},
    "INTERVIEWING": {"OFFERED", "REJECTED", "WITHDRAWN"},
    "OFFERED": set(),
    "REJECTED": set(),
    "WITHDRAWN": set(),
    "EXPIRED": set(),
}


class Shortlist(Input):
    job_id: UUID
    match_id: UUID | None = None


class Event(Version):
    to_status: Literal[
        "RESEARCHED", "SUBMITTED", "INTERVIEWING", "OFFERED", "REJECTED", "WITHDRAWN", "EXPIRED"
    ]
    note: str = Field(default="", max_length=3000)
    manual_confirmation: bool = False
    submitted_at: datetime | None = None
    channel: Text | None = None
    receipt_ref: Text | None = None


@router.post("", status_code=201)
def shortlist(data: Shortlist, actor: Actor, request: Request, response: Response) -> Row:
    with connect(settings_for(request)) as db:
        owner_lock(db, actor.id)
        job = get_record(db, actor.id, "job", data.job_id)
        existing = db.execute(
            "SELECT * FROM records WHERE owner_id=%s AND kind='application' AND data->>'job_id'=%s",
            (actor.id, str(data.job_id)),
        ).fetchone()
        if existing:
            response.status_code = 200
            return public(existing)
        if data.match_id:
            match = get_record(db, actor.id, "match", data.match_id)["data"]
            candidate = profile(db, actor.id)
            snapshot = match["profile_snapshot"]
            evidence = {e["id"]: e for e in snapshot["evidence"]}
            used = {fid for a in match["input_assessments"] for fid in a["fact_ids"]}
            invalid_fact = any(
                not eligible(f, evidence, datetime.now(UTC))
                for f in snapshot["facts"]
                if f["id"] in used
            )
            if (
                match["job_id"] != str(data.job_id)
                or match["job_version"] != job["version"]
                or match["profile_version"] != candidate["version"]
                or invalid_fact
            ):
                raise Problem(409, "STALE_MATCH", "Update the analysis before using this result.")
        now = datetime.now(UTC).isoformat()
        return public(
            insert(
                db,
                actor.id,
                "application",
                {
                    "job_id": str(data.job_id),
                    "job_title": job["data"].get("title"),
                    "company_name": job["data"].get("company_name"),
                    "match_id": str(data.match_id) if data.match_id else None,
                    "status": "SHORTLISTED",
                    "submission": None,
                    "events": [
                        {
                            "id": str(uuid4()),
                            "from_status": None,
                            "to_status": "SHORTLISTED",
                            "origin": "manual_record",
                            "actor_id": str(actor.id),
                            "at": now,
                            "note": "",
                        }
                    ],
                    "created_at": now,
                },
            )
        )


@router.get("")
def applications(
    actor: Actor,
    request: Request,
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> Row:
    with connect(settings_for(request)) as db:
        rows = db.execute(
            "SELECT * FROM records WHERE owner_id=%s AND kind='application' "
            "AND NOT deleted ORDER BY updated_at DESC LIMIT %s OFFSET %s",
            (actor.id, limit, offset),
        ).fetchall()
        total = db.execute(
            "SELECT count(*) AS total FROM records WHERE owner_id=%s "
            "AND kind='application' AND NOT deleted",
            (actor.id,),
        ).fetchone()
        return {"items": [public(r) for r in rows], "total": total["total"] if total else 0}


@router.get("/{application_id}")
def application(application_id: UUID, actor: Actor, request: Request) -> Row:
    with connect(settings_for(request)) as db:
        return public(get_record(db, actor.id, "application", application_id))


@router.post("/{application_id}/events")
def transition(application_id: UUID, data: Event, actor: Actor, request: Request) -> Row:
    payload_hash = fingerprint(data.model_dump(mode="json"))
    key = request.headers.get("idempotency-key", "implicit:" + payload_hash)
    if not key.strip() or len(key) > 200:
        raise Problem(422, "INVALID_KEY", "Invalid idempotency key.")
    operation = "application-event:" + str(application_id)
    with connect(settings_for(request)) as db:
        owner_lock(db, actor.id)
        current = get_record(db, actor.id, "application", application_id)
        previous = db.execute(
            "SELECT * FROM idempotency WHERE owner_id=%s AND operation=%s AND key=%s",
            (actor.id, operation, key),
        ).fetchone()
        if previous:
            if previous["payload_hash"] != payload_hash:
                raise Problem(409, "IDEMPOTENCY_CONFLICT", "The key already records another event.")
            return dict(previous["response"])
        old = current["data"]["status"]
        if data.to_status not in TRANSITIONS[old]:
            raise Problem(409, "INVALID_TRANSITION", "Transition not allowed from this state.")
        submission = current["data"].get("submission")
        if data.to_status == "SUBMITTED":
            if (
                not data.manual_confirmation
                or not data.submitted_at
                or not data.channel
                or not data.receipt_ref
            ):
                raise Problem(
                    422,
                    "MANUAL_CONFIRMATION_REQUIRED",
                    "Confirm manual submission, date, channel and receipt.",
                )
            if data.submitted_at.tzinfo is None or data.submitted_at > datetime.now(
                UTC
            ) + timedelta(minutes=5):
                raise Problem(
                    422, "INVALID_DATE", "Provide the actual submission date with timezone."
                )
            submission = {
                "origin": "manual_record",
                "channel": data.channel,
                "submitted_at": data.submitted_at.isoformat(),
                "receipt_ref": data.receipt_ref,
            }
        event = {
            "id": str(uuid4()),
            "from_status": old,
            "to_status": data.to_status,
            "origin": "manual_record",
            "actor_id": str(actor.id),
            "at": datetime.now(UTC).isoformat(),
            "note": data.note,
        }
        changed = update(
            db,
            current,
            data.expected_version,
            {
                **current["data"],
                "status": data.to_status,
                "submission": submission,
                "events": [*current["data"]["events"], event],
            },
        )
        result = public(changed)
        db.execute(
            "INSERT INTO idempotency VALUES (%s,%s,%s,%s,%s)",
            (actor.id, operation, key, payload_hash, Jsonb(result)),
        )
        return result
