"""Atomic synchronisation with a durable lease and one network reader at a time."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from jobhunter_api.discovery import source_ready
from jobhunter_api.errors import Problem
from jobhunter_api.greenhouse import DiscoveryBatch, read_greenhouse
from jobhunter_api.records import get_record, insert, owner_lock, public, update
from jobhunter_api.settings import Settings
from jobhunter_api.source_http import SourceFailure
from jobhunter_api.store import Connection, Row, connect

type Reader = Callable[[Row], DiscoveryBatch]


def capture(db: Connection, owner: UUID, source: Row, batch: DiscoveryBatch) -> Row:
    now = datetime.now(UTC).isoformat()
    rows = db.execute(
        "SELECT * FROM records WHERE owner_id=%s AND kind='discovery_item' "
        "AND data->>'source_id'=%s AND NOT deleted",
        (owner, str(source["id"])),
    ).fetchall()
    existing = {row["data"]["external_id"]: row for row in rows}
    counts = {"new": 0, "changed": 0, "missing": 0, "unchanged": 0}
    for item in batch.items:
        old = existing.pop(item.external_id, None)
        common = {
            **item.model_dump(),
            "source_id": str(source["id"]),
            "content_hash": item.fingerprint(),
            "last_seen_at": now,
            "availability": "listed",
        }
        if old is None:
            insert(
                db,
                owner,
                "discovery_item",
                {
                    **common,
                    "first_seen_at": now,
                    "notice": "new",
                    "seen": False,
                    "dismissed": False,
                    "job_id": None,
                },
            )
            counts["new"] += 1
        elif (
            old["data"]["content_hash"] != item.fingerprint()
            or old["data"]["availability"] != "listed"
        ):
            snapshot_item(db, old)
            update(
                db,
                old,
                old["version"],
                {**old["data"], **common, "notice": "changed", "seen": False, "dismissed": False},
            )
            counts["changed"] += 1
        else:
            # Refresh provenance without manufacturing a new content revision or audit event.
            db.execute(
                "UPDATE records SET data=jsonb_set(data,'{last_seen_at}',%s) WHERE id=%s",
                (Jsonb(now), old["id"]),
            )
            counts["unchanged"] += 1
    if batch.complete:
        for old in existing.values():
            if old["data"]["availability"] == "listed":
                snapshot_item(db, old)
                update(
                    db,
                    old,
                    old["version"],
                    {
                        **old["data"],
                        "availability": "not_listed",
                        "notice": "missing",
                        "seen": False,
                    },
                )
                counts["missing"] += 1
    return counts


def snapshot_item(db: Connection, row: Row) -> None:
    db.execute(
        "INSERT INTO snapshots (id,owner_id,kind,source_id,version,data) "
        "VALUES (%s,%s,'discovery_item',%s,%s,%s) ON CONFLICT DO NOTHING",
        (uuid4(), row["owner_id"], row["id"], row["version"], Jsonb(row["data"])),
    )


def synchronise(
    settings: Settings, owner: UUID, source_id: UUID, reader: Reader | None = None
) -> Row:
    # A session lock spans only this bounded read; no transaction stays open on the network.
    with connect(settings) as lane:
        locked = lane.execute("SELECT pg_try_advisory_lock(71004) AS locked").fetchone()
        lane.commit()
        if not locked or not locked["locked"]:
            raise Problem(409, "SYNC_BUSY", "Another source is being checked. Try again shortly.")
        try:
            return run_sync(settings, owner, source_id, reader)
        finally:
            lane.execute("SELECT pg_advisory_unlock(71004)")


def run_sync(settings: Settings, owner: UUID, source_id: UUID, reader: Reader | None) -> Row:
    now = datetime.now(UTC)
    with connect(settings) as db:
        owner_lock(db, owner)
        source = get_record(db, owner, "discovery_source", source_id)
        data = source["data"]
        if not source_ready(source):
            raise Problem(409, "SOURCE_DISABLED", "Enable the source with a current access review.")
        if data.get("lease_until") and datetime.fromisoformat(data["lease_until"]) > now:
            raise Problem(409, "SYNC_BUSY", "This source is already being checked.")
        if data.get("next_sync_at") and datetime.fromisoformat(data["next_sync_at"]) > now:
            raise Problem(
                429, "SYNC_NOT_DUE", "This source is up to date. Check its next refresh time."
            )
        if data.get("active_run"):
            abandoned = get_record(db, owner, "discovery_run", UUID(data["active_run"]))
            update(
                db,
                abandoned,
                abandoned["version"],
                {
                    **abandoned["data"],
                    "status": "interrupted",
                    "finished_at": now.isoformat(),
                    "error_code": "SYNC_INTERRUPTED",
                },
            )
        run = insert(
            db,
            owner,
            "discovery_run",
            {
                "source_id": str(source_id),
                "status": "running",
                "started_at": now.isoformat(),
                "finished_at": None,
                "counts": {},
                "error_code": None,
            },
        )
        source = update(
            db,
            source,
            source["version"],
            {
                **data,
                "active_run": str(run["id"]),
                "lease_until": (now + timedelta(minutes=5)).isoformat(),
            },
        )
    failure: SourceFailure | None = None
    batch = DiscoveryBatch()
    try:
        if reader:
            batch = reader(source)
        elif data["provider"] == "greenhouse":
            batch = read_greenhouse(source)
        else:
            raise SourceFailure("GMAIL_NOT_CONFIGURED", stop=True)
    except SourceFailure as error:
        failure = error
    except Exception:
        failure = SourceFailure("SOURCE_UNAVAILABLE")
    with connect(settings) as db:
        owner_lock(db, owner)
        current = get_record(db, owner, "discovery_source", source_id)
        now = datetime.now(UTC)
        counts: Row = {}
        if current["data"].get("active_run") != str(run["id"]):
            raise Problem(409, "SYNC_SUPERSEDED", "A newer source check replaced this run.")
        if current["version"] != source["version"] or not source_ready(current):
            status = "cancelled"
        elif failure:
            status = "failed"
        else:
            counts = capture(db, owner, source, batch) if not batch.not_modified else {}
            status = "unchanged" if batch.not_modified else "completed"
        successful = status in {"unchanged", "completed"}
        next_time = now + (timedelta(days=1) if successful else timedelta(minutes=15))
        if failure and failure.retry_at:
            next_time = max(next_time, datetime.fromisoformat(failure.retry_at))
        values = {
            **current["data"],
            "active_run": None,
            "lease_until": None,
            "next_sync_at": next_time.isoformat(),
            "last_error": failure.code if failure else None,
        }
        if failure and failure.stop:
            values["enabled"] = False
        if successful:
            values["last_synced_at"] = now.isoformat()
            if not batch.not_modified:
                values.update(
                    etag=batch.etag, last_modified=batch.last_modified, cursor=batch.cursor
                )
        update(db, current, current["version"], values)
        return public(
            update(
                db,
                run,
                run["version"],
                {
                    **run["data"],
                    "status": status,
                    "counts": counts,
                    "finished_at": now.isoformat(),
                    "error_code": failure.code if failure else None,
                },
            )
        )
