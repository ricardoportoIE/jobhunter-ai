"""Version-bound authorisation for a local application rehearsal."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from jobhunter_api.clarifications import collect
from jobhunter_api.deduplication import fingerprint
from jobhunter_api.errors import Problem
from jobhunter_api.package_domain import check_current, validation
from jobhunter_api.records import get_record, profile, public, source_update_pending, update
from jobhunter_api.scoring import eligible
from jobhunter_api.store import Connection, Row

CHANNEL = "local_sandbox"
RECIPIENT = "sandbox://jobhunter/application-receiver"
UNCERTAIN = {"DISPATCHING", "UNKNOWN"}


def now() -> datetime:
    return datetime.now(UTC)


def application_gate(db: Connection, owner: UUID, app: Row, package: Row) -> Row:
    """Recheck rules at preparation, approval and receiver acceptance."""
    if app["data"]["status"] not in {"SHORTLISTED", "RESEARCHED"}:
        raise Problem(
            409, "APPLICATION_CLOSED", "Only an active, unsubmitted application can be rehearsed."
        )
    data = package["data"]
    if data["job_id"] != app["data"]["job_id"]:
        raise Problem(409, "PACKAGE_JOB_MISMATCH", "Choose a package for this vacancy.")
    check_current(db, owner, data["snapshot"])
    if (
        data["status"] != "APPROVED"
        or not data.get("review")
        or data["review"]["content_hash"] != fingerprint(data["content"])
        or not validation(
            data["content"], data["snapshot"], data["selection"], data["manual_answers"]
        )["valid"]
    ):
        raise Problem(
            409,
            "PACKAGE_APPROVAL_REQUIRED",
            "Approve the current documents before preparing a rehearsal.",
        )
    job_id = UUID(data["job_id"])
    if source_update_pending(db, owner, job_id, include_missing=True):
        raise Problem(
            409, "SOURCE_UNAVAILABLE", "Review the changed or unavailable vacancy source first."
        )
    match = db.execute(
        "SELECT * FROM records WHERE owner_id=%s AND kind='match' AND NOT deleted "
        "AND data->>'job_id'=%s ORDER BY updated_at DESC,id DESC LIMIT 1",
        (owner, str(job_id)),
    ).fetchone()
    job, candidate = public(get_record(db, owner, "job", job_id)), public(profile(db, owner))
    if not match or (
        match["data"]["job_version"] != job["version"]
        or match["data"]["profile_version"] != candidate["version"]
    ):
        raise Problem(
            409, "ANALYSIS_REQUIRED", "Review a current analysis before preparing a rehearsal."
        )
    result = match["data"]
    evidence = {e["id"]: e for e in result["profile_snapshot"]["evidence"]}
    used = {f for a in result["input_assessments"] for f in a["fact_ids"]}
    resolved = {r["key"] for r in result.get("clarification_resolutions", [])}
    issues = collect(db, owner, job, candidate, result["input_assessments"])
    if (
        result["recommendation"] == "BLOCKED"
        or result["blockers"]
        or result.get("clarifications")
        or any(i["key"] not in resolved or i.get("requires_assessment_change") for i in issues)
        or any(
            not eligible(f, evidence, now())
            for f in result["profile_snapshot"]["facts"]
            if f["id"] in used
        )
    ):
        raise Problem(
            409,
            "APPLICATION_REVIEW_REQUIRED",
            "Resolve application blockers and clarifications in the analysis first.",
        )
    return match


def envelope(app: Row, package: Row, match: Row) -> Row:
    content = package["data"]["content"]
    return {
        "channel": CHANNEL,
        "recipient": RECIPIENT,
        "application_id": str(app["id"]),
        "application_version": app["version"],
        "job_id": app["data"]["job_id"],
        "package_id": str(package["id"]),
        "package_version": package["version"],
        "package_hash": fingerprint(content),
        "match_id": str(match["id"]),
        "content": {
            "name": content["name"],
            "contact_lines": content["contact_lines"],
            "job_title": content["job_title"],
            "company_name": content["company_name"],
            "cv": [c["text"] for c in content["cv"]],
            "cover_letter": [c["text"] for c in content["cover_letter"]],
            "answers": [{"question": a["question"], "text": a["text"]} for a in content["answers"]],
        },
    }


def check_binding(db: Connection, owner: UUID, workflow: Row) -> None:
    data = workflow["data"]
    payload = data["payload"]
    app = get_record(db, owner, "application", UUID(data["application_id"]))
    package = get_record(db, owner, "package", UUID(payload["package_id"]))
    match = application_gate(db, owner, app, package)
    if envelope(app, package, match) != payload or fingerprint(payload) != data["payload_hash"]:
        raise Problem(
            409,
            "SUBMISSION_CHANGED",
            "The reviewed application changed. Prepare and authorise it again.",
        )


def check_authorisation(db: Connection, owner: UUID, workflow: Row) -> None:
    check_binding(db, owner, workflow)
    data = workflow["data"]
    approval = data.get("authorisation")
    if not approval or (
        approval["actor_id"] != str(owner)
        or approval["scope"] != "submission:sandbox"
        or approval["payload_hash"] != data["payload_hash"]
        or approval["recipient"] != RECIPIENT
        or approval["channel"] != CHANNEL
        or datetime.fromisoformat(approval["expires_at"]) <= now()
    ):
        raise Problem(
            409,
            "SUBMISSION_APPROVAL_REQUIRED",
            "Authorisation expired or is missing. Review and authorise this rehearsal again.",
        )


def advance(db: Connection, row: Row, status: str, **changes: object) -> Row:
    # Preserve the exact previous payload and authorisation, including revoked revisions.
    db.execute(
        "INSERT INTO snapshots (id,owner_id,kind,source_id,version,data) "
        "VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
        (uuid4(), row["owner_id"], row["kind"], row["id"], row["version"], Jsonb(row["data"])),
    )
    event = {
        "status": status,
        "at": now().isoformat(),
        "attempt_id": changes.get("attempt_id", row["data"].get("attempt_id")),
    }
    return update(
        db,
        row,
        row["version"],
        {
            **row["data"],
            **changes,
            "status": status,
            "history": [*row["data"].get("history", []), event],
        },
    )


def complete(db: Connection, workflow: Row, receipt: Row) -> Row:
    data = workflow["data"]
    if (
        receipt["payload_hash"] != data["payload_hash"]
        or receipt["attempt_id"] != data["attempt_id"]
    ):
        raise Problem(
            409,
            "RECEIPT_CONFLICT",
            "The receipt does not match this attempt. Keep it pending for investigation.",
        )
    if data["status"] == "SIMULATED":
        return workflow
    app = get_record(db, workflow["owner_id"], "application", UUID(data["application_id"]))
    update(
        db,
        app,
        app["version"],
        {
            **app["data"],
            "last_simulation": receipt,
            "events": [
                *app["data"]["events"],
                {
                    "id": receipt["id"],
                    "from_status": app["data"]["status"],
                    "to_status": app["data"]["status"],
                    "origin": "local_sandbox",
                    "actor_id": str(workflow["owner_id"]),
                    "at": now().isoformat(),
                    "note": "Local rehearsal completed. Nothing was sent to an employer.",
                },
            ],
        },
    )
    return advance(db, workflow, "SIMULATED", receipt=receipt, authorisation=None)
