"""Owned, versioned records. Callers keep writes and audit events in one transaction."""

from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from jobhunter_api.errors import Problem
from jobhunter_api.store import Connection, Row


def owner_lock(db: Connection, owner: UUID) -> None:
    db.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (str(owner),))
    if not db.execute("SELECT id FROM users WHERE id=%s", (owner,)).fetchone():
        raise Problem(401, "AUTH_REQUIRED", "The account is not available.")


def audit(db: Connection, owner: UUID, action: str, entity: UUID, version: int) -> None:
    db.execute(
        "INSERT INTO audit_events (id,owner_id,action,entity_id,version) VALUES (%s,%s,%s,%s,%s)",
        (uuid4(), owner, action, entity, version),
    )


def get_record(db: Connection, owner: UUID, kind: str, record_id: UUID) -> Row:
    row = db.execute(
        "SELECT * FROM records WHERE id=%s AND owner_id=%s AND kind=%s AND NOT deleted",
        (record_id, owner, kind),
    ).fetchone()
    if row is None:
        raise Problem(404, "NOT_FOUND", "Record not found.")
    return row


def public(row: Row) -> Row:
    return {**row["data"], "id": str(row["id"]), "version": row["version"]}


def insert(db: Connection, owner: UUID, kind: str, data: Row) -> Row:
    identity = uuid4()
    row = db.execute(
        "INSERT INTO records (id,owner_id,kind,data) VALUES (%s,%s,%s,%s) RETURNING *",
        (identity, owner, kind, Jsonb(data)),
    ).fetchone()
    assert row is not None
    audit(db, owner, f"{kind}.created", identity, 1)
    return row


def update(db: Connection, row: Row, expected: int, data: Row, *, deleted: bool = False) -> Row:
    if row["version"] != expected:
        raise Problem(409, "VERSION_CONFLICT", "The record changed. Update before editing.")
    changed = db.execute(
        "UPDATE records SET data=%s,version=version+1,deleted=%s,updated_at=now() "
        "WHERE id=%s AND owner_id=%s AND version=%s RETURNING *",
        (Jsonb(data), deleted, row["id"], row["owner_id"], expected),
    ).fetchone()
    if changed is None:
        raise Problem(409, "VERSION_CONFLICT", "Another edit was completed first.")
    audit(
        db,
        row["owner_id"],
        f"{row['kind']}.deleted" if deleted else f"{row['kind']}.updated",
        row["id"],
        changed["version"],
    )
    return changed


def list_records(db: Connection, owner: UUID, kind: str) -> list[Row]:
    return list(
        db.execute(
            "SELECT * FROM records WHERE owner_id=%s AND kind=%s "
            "AND NOT deleted ORDER BY updated_at DESC,id",
            (owner, kind),
        ).fetchall()
    )


def profile(db: Connection, owner: UUID) -> Row:
    rows = list_records(db, owner, "profile")
    if rows:
        return rows[0]
    return insert(
        db,
        owner,
        "profile",
        {
            "display_name": None,
            "target_roles": [],
            "markets": [],
            "locations": [],
            "work_modes": [],
            "status": "draft",
        },
    )


def invalidate_profile(db: Connection, owner: UUID) -> None:
    current = profile(db, owner)
    update(db, current, current["version"], {**current["data"], "status": "draft"})


def source_update_pending(
    db: Connection, owner: UUID, job_id: UUID, *, include_missing: bool = False
) -> bool:
    return (
        db.execute(
            "SELECT 1 FROM records WHERE owner_id=%s AND kind='discovery_item' AND NOT deleted "
            "AND data->>'job_id'=%s AND (data->>'content_hash' "
            "IS DISTINCT FROM data->>'saved_hash' "
            "OR (%s AND data->>'availability'='not_listed')) LIMIT 1",
            (owner, str(job_id), include_missing),
        ).fetchone()
        is not None
    )


def require_current_source(db: Connection, owner: UUID, job_id: UUID) -> None:
    if source_update_pending(db, owner, job_id):
        raise Problem(
            409,
            "SOURCE_UPDATE_PENDING",
            "The advert changed. Compare and apply its source update before continuing.",
        )
