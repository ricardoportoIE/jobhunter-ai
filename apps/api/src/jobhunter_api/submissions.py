"""Explicit review, durable checkpoints and outcome reconciliation for sandbox submissions."""

from datetime import timedelta
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Request
from pydantic import Field

from jobhunter_api import sandbox_channel
from jobhunter_api.auth import Actor, settings_for
from jobhunter_api.deduplication import fingerprint
from jobhunter_api.errors import Problem
from jobhunter_api.profile import Input, Version
from jobhunter_api.records import get_record, insert, owner_lock, public
from jobhunter_api.store import Row, connect
from jobhunter_api.submission_domain import (
    CHANNEL,
    RECIPIENT,
    UNCERTAIN,
    advance,
    application_gate,
    check_authorisation,
    check_binding,
    complete,
    envelope,
    now,
)

router = APIRouter(prefix="/api/v1", tags=["sandbox submissions"])


class Prepare(Input):
    package_id: UUID
    package_version: int = Field(ge=1)


class Authorise(Version):
    payload_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    submission_confirmed: Literal[True]


@router.get("/applications/{application_id}/submission")
def current(application_id: UUID, actor: Actor, request: Request) -> Row | None:
    with connect(settings_for(request)) as db:
        get_record(db, actor.id, "application", application_id)
        row = db.execute(
            "SELECT * FROM records WHERE owner_id=%s AND kind='submission_workflow' "
            "AND data->>'application_id'=%s AND NOT deleted",
            (actor.id, str(application_id)),
        ).fetchone()
        return public(row) if row else None


@router.post("/applications/{application_id}/submission")
def prepare(application_id: UUID, data: Prepare, actor: Actor, request: Request) -> Row:
    with connect(settings_for(request)) as db:
        owner_lock(db, actor.id)
        app = get_record(db, actor.id, "application", application_id)
        package = get_record(db, actor.id, "package", data.package_id)
        if package["version"] != data.package_version:
            raise Problem(409, "VERSION_CONFLICT", "Reload the current package before continuing.")
        match = application_gate(db, actor.id, app, package)
        payload = envelope(app, package, match)
        row = db.execute(
            "SELECT * FROM records WHERE owner_id=%s AND kind='submission_workflow' "
            "AND data->>'application_id'=%s AND NOT deleted",
            (actor.id, str(application_id)),
        ).fetchone()
        if row and row["data"]["status"] in {*UNCERTAIN, "SIMULATED"}:
            raise Problem(
                409,
                "ATTEMPT_EXISTS",
                "Check the existing attempt before preparing another rehearsal.",
            )
        if row and row["data"]["payload"] == payload and row["data"]["status"] != "CANCELLED":
            return public(row)
        fields = {
            "application_id": str(application_id),
            "payload": payload,
            "payload_hash": fingerprint(payload),
            "authorisation": None,
            "attempt_id": None,
            "receipt": None,
        }
        if row:
            return public(advance(db, row, "NEEDS_REVIEW", **fields))
        return public(
            insert(
                db,
                actor.id,
                "submission_workflow",
                {
                    **fields,
                    "status": "NEEDS_REVIEW",
                    "history": [
                        {"status": "NEEDS_REVIEW", "at": now().isoformat(), "attempt_id": None}
                    ],
                },
            )
        )


@router.post("/submissions/{workflow_id}/authorise")
def authorise(workflow_id: UUID, data: Authorise, actor: Actor, request: Request) -> Row:
    with connect(settings_for(request)) as db:
        owner_lock(db, actor.id)
        row = get_record(db, actor.id, "submission_workflow", workflow_id)
        if row["version"] != data.expected_version or row["data"]["status"] not in {
            "NEEDS_REVIEW",
            "FAILED",
            "APPROVED",
        }:
            raise Problem(409, "VERSION_CONFLICT", "Reload the rehearsal before authorising it.")
        check_binding(db, actor.id, row)
        if row["data"]["payload_hash"] != data.payload_hash:
            raise Problem(
                409, "SUBMISSION_CHANGED", "The reviewed payload changed. Review it again."
            )
        return public(
            advance(
                db,
                row,
                "APPROVED",
                authorisation={
                    "actor_id": str(actor.id),
                    "scope": "submission:sandbox",
                    "channel": CHANNEL,
                    "recipient": RECIPIENT,
                    "payload_hash": data.payload_hash,
                    "approved_at": now().isoformat(),
                    "expires_at": (now() + timedelta(minutes=15)).isoformat(),
                },
            )
        )


@router.post("/submissions/{workflow_id}/cancel")
def cancel(workflow_id: UUID, data: Version, actor: Actor, request: Request) -> Row:
    with connect(settings_for(request)) as db:
        owner_lock(db, actor.id)
        row = get_record(db, actor.id, "submission_workflow", workflow_id)
        if row["version"] != data.expected_version or row["data"]["status"] in {
            *UNCERTAIN,
            "SIMULATED",
        }:
            raise Problem(
                409,
                "ATTEMPT_EXISTS",
                "An accepted or uncertain attempt cannot be cancelled. Check its result.",
            )
        if row["data"]["status"] == "CANCELLED":
            return public(row)
        return public(advance(db, row, "CANCELLED", authorisation=None))


@router.post("/submissions/{workflow_id}/execute")
def execute(workflow_id: UUID, data: Version, actor: Actor, request: Request) -> Row:
    settings = settings_for(request)
    with connect(settings) as db:
        owner_lock(db, actor.id)
        row = get_record(db, actor.id, "submission_workflow", workflow_id)
        if row["data"]["status"] in {*UNCERTAIN, "SIMULATED"}:
            return public(row)
        if row["version"] != data.expected_version or row["data"]["status"] != "APPROVED":
            raise Problem(
                409,
                "SUBMISSION_APPROVAL_REQUIRED",
                "Authorise the current rehearsal before running it.",
            )
        check_authorisation(db, actor.id, row)
        attempt_id = str(uuid4())
        row = advance(db, row, "DISPATCHING", attempt_id=attempt_id)
    # The checkpoint is committed before acceptance in a separate transaction.
    try:
        receipt = sandbox_channel.deliver(settings, actor.id, workflow_id, attempt_id)
    except Exception:
        # Never infer non-delivery from an exception or expose its private payload.
        with connect(settings) as db:
            owner_lock(db, actor.id)
            row = get_record(db, actor.id, "submission_workflow", workflow_id)
            if row["data"]["status"] == "DISPATCHING" and row["data"]["attempt_id"] == attempt_id:
                row = advance(db, row, "UNKNOWN")
            return public(row)
    with connect(settings) as db:
        owner_lock(db, actor.id)
        row = get_record(db, actor.id, "submission_workflow", workflow_id)
        return public(complete(db, row, receipt))


@router.post("/submissions/{workflow_id}/reconcile")
def reconcile(workflow_id: UUID, data: Version, actor: Actor, request: Request) -> Row:
    with connect(settings_for(request)) as db:
        owner_lock(db, actor.id)
        row = get_record(db, actor.id, "submission_workflow", workflow_id)
        if row["data"]["status"] == "SIMULATED":
            return public(row)
        if row["version"] != data.expected_version or row["data"]["status"] not in UNCERTAIN:
            raise Problem(
                409,
                "RECONCILIATION_NOT_REQUIRED",
                "Reload the current attempt before checking its result.",
            )
        # A failed lookup rolls back; it is never interpreted as an absent receipt.
        receipt = sandbox_channel.lookup(db, actor.id, row["data"]["application_id"])
        if receipt:
            return public(complete(db, row, receipt))
        return public(advance(db, row, "FAILED", authorisation=None))
