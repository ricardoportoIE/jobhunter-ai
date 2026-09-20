"""Candidate declarations require explicit review; references never access the filesystem."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Query, Request
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict, Field, model_validator

from jobhunter_api.auth import Actor, settings_for
from jobhunter_api.errors import Problem
from jobhunter_api.records import (
    audit,
    get_record,
    insert,
    invalidate_profile,
    list_records,
    owner_lock,
    profile,
    public,
    update,
)
from jobhunter_api.store import Row, connect

router = APIRouter(prefix="/api/v1/candidate", tags=["candidate"])
type Text = Annotated[str, Field(min_length=1, max_length=3000)]
type Sensitivity = Literal["public", "private", "sensitive"]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Version(Input):
    expected_version: int = Field(ge=1)


class ProfileEdit(Version):
    display_name: Text | None = None
    target_roles: list[Text] = Field(default_factory=list, max_length=20)
    markets: list[Literal["IE", "GB"]] = Field(default_factory=list, max_length=2)
    locations: list[Text] = Field(default_factory=list, max_length=30)
    work_modes: list[Literal["hybrid", "remote", "onsite"]] = Field(
        default_factory=list, max_length=3
    )


class EvidenceInput(Input):
    source_type: Literal[
        "candidate_attestation", "cv", "repository", "certificate", "employment_record", "other"
    ]
    source_ref: Text
    locator: Text
    content: str = Field(min_length=1, max_length=10000)
    sensitivity: Sensitivity = "private"
    review_confirmed: bool = False


class EvidenceEdit(EvidenceInput, Version):
    pass


class FactInput(Input):
    claim: Text
    category: Literal[
        "skill",
        "experience",
        "education",
        "project",
        "certification",
        "achievement",
        "preference",
        "constraint",
    ]
    status: Literal["unverified", "verified", "expired", "revoked"] = "unverified"
    evidence_ids: list[UUID] = Field(default_factory=list, max_length=50)
    sensitivity: Sensitivity = "private"
    allowed_uses: list[Literal["matching", "cv", "cover_letter", "application_form"]] = Field(
        default_factory=list, max_length=4
    )
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    review_confirmed: bool = False

    @model_validator(mode="after")
    def dates(self) -> FactInput:
        for value in (self.valid_from, self.valid_until):
            if value and value.tzinfo is None:
                raise ValueError("Dates require timezone")
        if self.valid_from and self.valid_until and self.valid_until <= self.valid_from:
            raise ValueError("Invalid validity interval")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("Duplicate evidence")
        return self


class FactEdit(FactInput, Version):
    pass


@router.get("/profile")
def read_profile(actor: Actor, request: Request) -> Row:
    with connect(settings_for(request)) as db:
        owner_lock(db, actor.id)
        return public(profile(db, actor.id))


@router.patch("/profile")
def edit_profile(data: ProfileEdit, actor: Actor, request: Request) -> Row:
    with connect(settings_for(request)) as db:
        owner_lock(db, actor.id)
        current = profile(db, actor.id)
        return public(
            update(
                db,
                current,
                data.expected_version,
                {**data.model_dump(exclude={"expected_version"}), "status": "draft"},
            )
        )


@router.post("/profile/review")
def review_profile(data: Version, actor: Actor, request: Request) -> Row:
    with connect(settings_for(request)) as db:
        owner_lock(db, actor.id)
        current = profile(db, actor.id)
        current = update(
            db, current, data.expected_version, {**current["data"], "status": "reviewed"}
        )
        snapshot = {
            "profile": public(current),
            "facts": [public(r) for r in list_records(db, actor.id, "fact")],
            "evidence": [public(r) for r in list_records(db, actor.id, "evidence")],
        }
        db.execute(
            "INSERT INTO snapshots (id,owner_id,kind,source_id,version,data) "
            "VALUES (%s,%s,'profile',%s,%s,%s)",
            (uuid4(), actor.id, current["id"], current["version"], Jsonb(snapshot)),
        )
        audit(db, actor.id, "profile.reviewed", current["id"], current["version"])
        return public(current)


@router.get("/facts")
def facts(actor: Actor, request: Request) -> list[Row]:
    with connect(settings_for(request)) as db:
        return [public(row) for row in list_records(db, actor.id, "fact")]


@router.get("/evidence")
def evidence(actor: Actor, request: Request) -> list[Row]:
    with connect(settings_for(request)) as db:
        return [public(row) for row in list_records(db, actor.id, "evidence")]


@router.get("/evidence/{record_id}")
def read_evidence(record_id: UUID, actor: Actor, request: Request) -> Row:
    with connect(settings_for(request)) as db:
        return public(get_record(db, actor.id, "evidence", record_id))


def save_evidence(
    data: EvidenceInput, actor: Actor, request: Request, record_id: UUID | None
) -> Row:
    payload = data.model_dump(mode="json", exclude={"expected_version", "review_confirmed"})
    payload.update(
        content_sha256=hashlib.sha256(data.content.encode()).hexdigest(),
        reviewed_by=str(actor.id) if data.review_confirmed else None,
        reviewed_at=datetime.now(UTC).isoformat() if data.review_confirmed else None,
    )
    with connect(settings_for(request)) as db:
        owner_lock(db, actor.id)
        if record_id is not None and isinstance(data, EvidenceEdit):
            row = update(
                db, get_record(db, actor.id, "evidence", record_id), data.expected_version, payload
            )
        else:
            row = insert(db, actor.id, "evidence", payload)
        invalidate_profile(db, actor.id)
        return public(row)


@router.post("/evidence", status_code=201)
def add_evidence(data: EvidenceInput, actor: Actor, request: Request) -> Row:
    return save_evidence(data, actor, request, None)


@router.patch("/evidence/{record_id}")
def edit_evidence(record_id: UUID, data: EvidenceEdit, actor: Actor, request: Request) -> Row:
    return save_evidence(data, actor, request, record_id)


def save_fact(data: FactInput, actor: Actor, request: Request, record_id: UUID | None) -> Row:
    with connect(settings_for(request)) as db:
        owner_lock(db, actor.id)
        evidence = [
            get_record(db, actor.id, "evidence", identity) for identity in data.evidence_ids
        ]
        if data.status == "verified" and (
            not data.review_confirmed
            or not evidence
            or not data.allowed_uses
            or any(not r["data"].get("reviewed_at") for r in evidence)
        ):
            raise Problem(
                422,
                "REVIEW_REQUIRED",
                "Verification requires confirmation, uses and reviewed evidence.",
            )
        payload = data.model_dump(mode="json", exclude={"expected_version", "review_confirmed"})
        payload.update(
            reviewed_by=str(actor.id) if data.status == "verified" else None,
            reviewed_at=datetime.now(UTC).isoformat() if data.status == "verified" else None,
            evidence_versions={str(r["id"]): r["version"] for r in evidence},
        )
        if record_id is not None and isinstance(data, FactEdit):
            row = update(
                db, get_record(db, actor.id, "fact", record_id), data.expected_version, payload
            )
        else:
            row = insert(db, actor.id, "fact", payload)
        invalidate_profile(db, actor.id)
        return public(row)


@router.post("/facts", status_code=201)
def add_fact(data: FactInput, actor: Actor, request: Request) -> Row:
    return save_fact(data, actor, request, None)


@router.patch("/facts/{record_id}")
def edit_fact(record_id: UUID, data: FactEdit, actor: Actor, request: Request) -> Row:
    return save_fact(data, actor, request, record_id)


@router.delete("/{collection}/{record_id}", status_code=204)
def delete_record(
    collection: Literal["facts", "evidence"],
    record_id: UUID,
    actor: Actor,
    request: Request,
    expected_version: Annotated[int, Query(ge=1)],
) -> None:
    kind = "fact" if collection == "facts" else "evidence"
    with connect(settings_for(request)) as db:
        owner_lock(db, actor.id)
        row = get_record(db, actor.id, kind, record_id)
        update(db, row, expected_version, row["data"], deleted=True)
        invalidate_profile(db, actor.id)
