"""Manual import and reviewed requirements. URLs are never fetched."""

from __future__ import annotations

import hashlib
from typing import Annotated, Literal
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from fastapi import APIRouter, Query, Request, Response
from psycopg.types.json import Jsonb
from pydantic import ConfigDict, Field, model_validator

from jobhunter_api.auth import Actor, settings_for
from jobhunter_api.deduplication import fingerprint, identity_keys, normalized
from jobhunter_api.errors import Problem
from jobhunter_api.profile import Input, Text, Version
from jobhunter_api.records import (
    get_record,
    insert,
    owner_lock,
    public,
    source_update_pending,
    update,
)
from jobhunter_api.store import Connection, Row, connect

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])
type Category = Literal[
    "technical_skills",
    "seniority_experience",
    "portfolio",
    "education",
    "location_work_mode",
    "salary",
    "work_authorisation_hours",
    "career_value",
]


class JobImport(Input):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    raw_text: str = Field(min_length=1, max_length=50000)
    source_name: str = Field(default="manual", min_length=1, max_length=200)
    source_url: str | None = Field(default=None, max_length=2000)
    external_id: str | None = Field(default=None, min_length=1, max_length=200)
    location_hint: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def reference(self) -> JobImport:
        if not self.raw_text.strip():
            raise ValueError("Empty content")
        if self.source_url:
            url = urlsplit(self.source_url)
            _ = url.port
            if (
                url.scheme not in {"http", "https"}
                or not url.hostname
                or url.username
                or url.password
            ):
                raise ValueError("Only HTTP(S) references without credentials are accepted")
        return self


class Requirement(Input):
    id: UUID = Field(default_factory=uuid4)
    text: Text
    category: Category
    importance: Literal["required", "preferred"] = "required"
    is_eliminatory: bool = False
    source_locator: Text
    future_authorisation: bool = False


class Salary(Input):
    minimum: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    maximum: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    currency: str | None = Field(default=None, pattern="^[A-Z]{3}$")
    period: Literal["hour", "day", "month", "year"] | None = None

    @model_validator(mode="after")
    def range(self) -> Salary:
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("Salary range reversed")
        return self


class JobEdit(Version):
    title: Text | None = None
    company_name: Text | None = None
    location: Text | None = None
    country: Literal["IE", "GB", "OTHER"] | None = None
    work_mode: Literal["hybrid", "onsite", "remote"] | None = None
    employment_type: Text | None = None
    seniority: Text | None = None
    salary: Salary | None = None
    work_authorisation: Text | None = None
    sponsorship: Literal["available", "unavailable", "conditional"] | None = None
    requirements: list[Requirement] = Field(default_factory=list, max_length=100)
    risk_flags: list[Text] = Field(default_factory=list, max_length=30)
    archived: bool = False
    review_confirmed: bool = False

    @model_validator(mode="after")
    def identifiers(self) -> JobEdit:
        if len({r.id for r in self.requirements}) != len(self.requirements):
            raise ValueError("Duplicate requirement")
        return self


@router.post("/import", status_code=201)
def import_job(data: JobImport, actor: Actor, request: Request, response: Response) -> Row:
    with connect(settings_for(request)) as db:
        return import_record(db, actor.id, data, response, request.headers.get("idempotency-key"))


def import_record(
    db: Connection, owner: UUID, data: JobImport, response: Response, key: str | None = None
) -> Row:
    owner_lock(db, owner)
    payload_hash = fingerprint(data.model_dump())
    key = "implicit:" + payload_hash if key is None else key
    if not key.strip() or len(key) > 200:
        raise Problem(422, "INVALID_KEY", "Invalid idempotency key.")
    previous = db.execute(
        "SELECT payload_hash,response FROM idempotency "
        "WHERE owner_id=%s AND operation='import' AND key=%s",
        (owner, key),
    ).fetchone()
    if previous:
        if previous["payload_hash"] != payload_hash:
            raise Problem(
                409,
                "IDEMPOTENCY_CONFLICT",
                "The key has already been used with different content.",
            )
        response.status_code = 200
        return dict(previous["response"])
    keys = identity_keys(data.model_dump())
    duplicates = db.execute(
        "SELECT DISTINCT job_id FROM job_keys WHERE owner_id=%s AND key=ANY(%s)",
        (owner, keys),
    ).fetchall()
    if len(duplicates) > 1:
        raise Problem(409, "DUPLICATE_CONFLICT", "References point to different jobs.")
    if duplicates:
        existing = get_record(db, owner, "job", duplicates[0]["job_id"])
        old_location = existing["data"].get("location_hint")
        if (
            old_location
            and data.location_hint
            and normalized(old_location) != normalized(data.location_hint)
        ):
            raise Problem(
                409,
                "LOCATION_CONFLICT",
                "Same reference with different locations; review the source.",
            )
        result = public(existing)
        response.status_code = 200
    else:
        result = None
    payload = JobEdit(expected_version=1).model_dump(
        mode="json", exclude={"expected_version", "review_confirmed"}
    )
    payload.update(
        data.model_dump(),
        content_sha256=hashlib.sha256(data.raw_text.encode()).hexdigest(),
        status="DISCOVERED",
        reviewed_by=None,
        reviewed_at=None,
    )
    if result is None:
        result = public(insert(db, owner, "job", payload))
    for identity in keys:
        db.execute(
            "INSERT INTO job_keys VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
            (owner, identity, result["id"]),
        )
    db.execute(
        "INSERT INTO idempotency VALUES (%s,'import',%s,%s,%s)",
        (owner, key, payload_hash, Jsonb(result)),
    )
    return result


@router.get("")
def jobs(
    actor: Actor,
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    offset: Annotated[int, Query(ge=0)] = 0,
    q: str = "",
    location: Annotated[str, Query(max_length=200)] = "",
    work_mode: Literal["hybrid", "onsite", "remote"] | None = None,
    status: Literal["DISCOVERED", "PARSED", "SCORED"] | None = None,
    archived: bool = False,
) -> Row:
    if len(q) > 200:
        raise Problem(422, "INVALID_INPUT", "Search too long.")
    with connect(settings_for(request)) as db:
        conditions = (
            "owner_id=%s AND kind='job' AND NOT deleted AND "
            "(data->>'archived')::boolean=%s AND "
            "(%s::text IS NULL OR data->>'status'=%s) AND "
            "(coalesce(data->>'title','') ILIKE %s OR coalesce(data->>'company_name','') ILIKE %s) "
            "AND coalesce(data->>'location','') ILIKE %s "
            "AND (%s::text IS NULL OR data->>'work_mode'=%s)"
        )

        # Treat search terms as text, rather than allowing SQL wildcard filters.
        def pattern(text: str) -> str:
            return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"

        params = (
            actor.id,
            archived,
            status,
            status,
            pattern(q),
            pattern(q),
            pattern(location),
            work_mode,
            work_mode,
        )
        # conditions contains only fixed SQL; all user values are bound parameters.
        from psycopg import sql

        rows = db.execute(
            sql.SQL(
                "SELECT * FROM records WHERE "
                + conditions
                + " ORDER BY updated_at DESC,id LIMIT %s OFFSET %s"
            ),
            (*params, limit, offset),
        ).fetchall()
        total = db.execute(
            sql.SQL("SELECT count(*) AS total FROM records WHERE " + conditions), params
        ).fetchone()
        return {
            "items": [public(r) for r in rows],
            "total": total["total"] if total else 0,
            "limit": limit,
            "offset": offset,
        }


@router.get("/{job_id}")
def job(job_id: UUID, actor: Actor, request: Request) -> Row:
    with connect(settings_for(request)) as db:
        result = public(get_record(db, actor.id, "job", job_id))
        if source_update_pending(db, actor.id, job_id, include_missing=True):
            result["source_update_pending"] = True
        return result


@router.patch("/{job_id}")
def edit_job(job_id: UUID, data: JobEdit, actor: Actor, request: Request) -> Row:
    from datetime import UTC, datetime

    with connect(settings_for(request)) as db:
        owner_lock(db, actor.id)
        row = get_record(db, actor.id, "job", job_id)
        payload = {
            **row["data"],
            **data.model_dump(mode="json", exclude={"expected_version", "review_confirmed"}),
            "status": "PARSED" if data.review_confirmed else "DISCOVERED",
            "reviewed_by": str(actor.id) if data.review_confirmed else None,
            "reviewed_at": datetime.now(UTC).isoformat() if data.review_confirmed else None,
        }
        return public(update(db, row, data.expected_version, payload))
