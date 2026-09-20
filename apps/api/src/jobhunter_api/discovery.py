"""Opt-in source registry and versioned, owner-scoped discovery contracts."""

from datetime import UTC, date, datetime, timedelta
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import Field, model_validator

from jobhunter_api.auth import Actor, settings_for
from jobhunter_api.errors import Problem
from jobhunter_api.profile import Input, Version
from jobhunter_api.records import get_record, insert, list_records, owner_lock, public, update
from jobhunter_api.store import Row, connect

router = APIRouter(prefix="/api/v1/discovery", tags=["discovery"])


class SourceInput(Input):
    provider: Literal["greenhouse", "gmail"]
    name: str = Field(min_length=1, max_length=100)
    reference: str = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def reference_format(self) -> "SourceInput":
        import re

        if self.provider == "greenhouse" and not re.fullmatch(r"[a-z0-9_-]{1,100}", self.reference):
            raise ValueError("Use the board token, not a URL")
        if self.provider == "gmail" and self.reference != "alerts":
            raise ValueError("Only one dedicated Gmail alerts connection is supported")
        return self


class SourceEdit(Version):
    enabled: bool = False
    terms_url: str = Field(default="", max_length=2000)
    permission_note: str = Field(default="", max_length=2000)
    review_until: date | None = None
    access_confirmed: bool = False
    label_id: str = Field(default="", max_length=100, pattern=r"^[A-Za-z0-9_-]*$")
    label_name: str = Field(default="", max_length=100)

    @model_validator(mode="after")
    def review(self) -> "SourceEdit":
        if self.enabled:
            today = datetime.now(UTC).date()
            if (
                not self.access_confirmed
                or not self.permission_note.strip()
                or not self.review_until
                or not today <= self.review_until <= today + timedelta(days=90)
            ):
                raise ValueError("Enabling requires an access review valid for at most 90 days")
            parts = urlsplit(self.terms_url)
            if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
                raise ValueError("Provide the applicable terms or permission reference")
        return self


def source_ready(source: Row) -> bool:
    data = source["data"]
    return bool(
        data["enabled"]
        and data.get("review_until")
        and date.fromisoformat(data["review_until"]) >= datetime.now(UTC).date()
    )


@router.get("/sources")
def sources(actor: Actor, request: Request) -> list[Row]:
    with connect(settings_for(request)) as db:
        return [
            {**public(row), "ready": source_ready(row)}
            for row in list_records(db, actor.id, "discovery_source")
        ]


@router.post("/sources", status_code=201)
def create_source(data: SourceInput, actor: Actor, request: Request) -> Row:
    with connect(settings_for(request)) as db:
        owner_lock(db, actor.id)
        current = list_records(db, actor.id, "discovery_source")
        if len(current) >= 10:
            raise Problem(422, "SOURCE_LIMIT", "Use at most ten sources for the local pilot.")
        if any(
            row["data"]["provider"] == data.provider and row["data"]["reference"] == data.reference
            for row in current
        ):
            raise Problem(409, "SOURCE_EXISTS", "This source has already been added.")
        return public(
            insert(
                db,
                actor.id,
                "discovery_source",
                {
                    **data.model_dump(),
                    "enabled": False,
                    "terms_url": "",
                    "permission_note": "",
                    "review_until": None,
                    "reviewed_at": None,
                    "label_id": "",
                    "label_name": "",
                    "connected": False,
                    "last_synced_at": None,
                    "next_sync_at": None,
                    "active_run": None,
                    "lease_until": None,
                    "last_error": None,
                    "etag": None,
                    "last_modified": None,
                },
            )
        )


@router.patch("/sources/{source_id}")
def edit_source(source_id: UUID, data: SourceEdit, actor: Actor, request: Request) -> Row:
    with connect(settings_for(request)) as db:
        owner_lock(db, actor.id)
        row = get_record(db, actor.id, "discovery_source", source_id)
        if (
            data.enabled
            and row["data"]["provider"] == "gmail"
            and (not row["data"]["connected"] or not data.label_id.startswith("Label_"))
        ):
            raise Problem(422, "GMAIL_LABEL_REQUIRED", "Connect Gmail and choose a custom label.")
        values = data.model_dump(mode="json", exclude={"expected_version", "access_confirmed"})
        return public(
            update(
                db,
                row,
                data.expected_version,
                {
                    **row["data"],
                    **values,
                    "reviewed_at": datetime.now(UTC).isoformat()
                    if data.enabled
                    else row["data"]["reviewed_at"],
                },
            )
        )


@router.get("/sources/{source_id}/runs")
def runs(source_id: UUID, actor: Actor, request: Request) -> list[Row]:
    with connect(settings_for(request)) as db:
        get_record(db, actor.id, "discovery_source", source_id)
        rows = db.execute(
            "SELECT * FROM records WHERE owner_id=%s AND kind='discovery_run' "
            "AND data->>'source_id'=%s AND NOT deleted ORDER BY updated_at DESC,id LIMIT 30",
            (actor.id, str(source_id)),
        ).fetchall()
        return [public(row) for row in rows]
