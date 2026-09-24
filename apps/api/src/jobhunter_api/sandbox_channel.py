"""Local receiver with durable idempotency; deliberately contains no network client."""

from uuid import UUID

from jobhunter_api.errors import Problem
from jobhunter_api.records import get_record, insert, owner_lock, public
from jobhunter_api.settings import Settings
from jobhunter_api.store import Connection, Row, connect
from jobhunter_api.submission_domain import check_authorisation, now


def lookup(db: Connection, owner: UUID, application_id: str) -> Row | None:
    row = db.execute(
        "SELECT * FROM records WHERE owner_id=%s AND kind='sandbox_receipt' "
        "AND data->>'application_id'=%s AND NOT deleted",
        (owner, application_id),
    ).fetchone()
    return public(row) if row else None


def deliver(settings: Settings, owner: UUID, workflow_id: UUID, attempt_id: str) -> Row:
    with connect(settings) as db:
        owner_lock(db, owner)
        workflow = get_record(db, owner, "submission_workflow", workflow_id)
        data = workflow["data"]
        previous = lookup(db, owner, data["application_id"])
        if previous:
            if (
                previous["payload_hash"] != data["payload_hash"]
                or previous["attempt_id"] != attempt_id
            ):
                raise Problem(
                    409, "RECEIPT_CONFLICT", "A different rehearsal was already accepted."
                )
            return previous
        # Reconciliation and late acceptance use the same lock and persisted state.
        if data["status"] != "DISPATCHING" or data["attempt_id"] != attempt_id:
            raise Problem(
                409, "ATTEMPT_CLOSED", "This attempt is no longer authorised for acceptance."
            )
        check_authorisation(db, owner, workflow)
        return public(
            insert(
                db,
                owner,
                "sandbox_receipt",
                {
                    "application_id": data["application_id"],
                    "workflow_id": str(workflow_id),
                    "attempt_id": attempt_id,
                    "payload_hash": data["payload_hash"],
                    "channel": data["payload"]["channel"],
                    "recipient": data["payload"]["recipient"],
                    "accepted_at": now().isoformat(),
                    "simulated": True,
                },
            )
        )
