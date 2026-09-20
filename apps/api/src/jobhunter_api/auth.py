"""Opaque, expiring sessions with CSRF, same-origin writes and persistent throttling."""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from jobhunter_api.errors import Problem
from jobhunter_api.settings import Settings
from jobhunter_api.store import connect

router = APIRouter(prefix="/api/v1", tags=["session"])
hasher = PasswordHasher()
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(24))
COOKIE = "jobhunter_session"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def settings_for(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def check_origin(request: Request) -> None:
    if request.headers.get("origin") not in settings_for(request).allowed_origins:
        raise Problem(403, "ORIGIN_REJECTED", "Unauthorized origin.")


@dataclass(frozen=True)
class Principal:
    id: UUID
    csrf: str
    token_hash: str


def authenticated(request: Request) -> Principal:
    token = request.cookies.get(COOKIE, "")
    if not token or len(token) > 128:
        raise Problem(401, "AUTH_REQUIRED", "Start a session.")
    with connect(settings_for(request)) as db:
        row = db.execute(
            "SELECT owner_id,csrf_token FROM sessions WHERE token_hash=%s AND expires_at>now()",
            (digest(token),),
        ).fetchone()
    if row is None:
        raise Problem(401, "AUTH_REQUIRED", "Session expired. Please log in again.")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        check_origin(request)
        if not secrets.compare_digest(request.headers.get("x-csrf-token", ""), row["csrf_token"]):
            raise Problem(403, "CSRF_REJECTED", "Refresh the session before continuing.")
    return Principal(row["owner_id"], row["csrf_token"], digest(token))


Actor = Annotated[Principal, Depends(authenticated)]


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=100)
    password: SecretStr = Field(min_length=1, max_length=256)


@router.post("/session")
def login(data: Login, request: Request, response: Response) -> dict[str, str]:
    check_origin(request)
    settings = settings_for(request)
    # Global bucket is appropriate for the single-user local deployment. It cannot
    # be bypassed using arbitrary usernames or forwarded IP headers.
    with connect(settings) as db:
        row = db.execute(
            "INSERT INTO login_limits VALUES ('local',1,now()+interval '1 minute') "
            "ON CONFLICT(bucket) DO UPDATE SET attempts=CASE WHEN "
            "login_limits.resets_at<now() THEN 1 ELSE login_limits.attempts+1 END, "
            "resets_at=CASE WHEN login_limits.resets_at<now() THEN "
            "now()+interval '1 minute' ELSE login_limits.resets_at END "
            "RETURNING attempts"
        ).fetchone()
    assert row is not None
    if row["attempts"] > 10:
        raise Problem(429, "LOGIN_LIMIT", "Please wait a minute before trying again.")
    with connect(settings) as db:
        user = db.execute(
            "SELECT id,password_hash FROM users WHERE username=%s", (data.username,)
        ).fetchone()
        try:
            hasher.verify(
                user["password_hash"] if user else DUMMY_HASH, data.password.get_secret_value()
            )
        except VerificationError:
            raise Problem(401, "INVALID_LOGIN", "Invalid user or password.") from None
        if not user:
            raise Problem(401, "INVALID_LOGIN", "Invalid user or password.")
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        db.execute(
            "DELETE FROM sessions WHERE expires_at<=now() OR token_hash=%s",
            (digest(request.cookies.get(COOKIE, "")),),
        )
        db.execute(
            "INSERT INTO sessions (token_hash,owner_id,csrf_token,expires_at) VALUES (%s,%s,%s,%s)",
            (
                digest(token),
                user["id"],
                csrf,
                datetime.now(UTC) + timedelta(seconds=settings.session_seconds),
            ),
        )
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        samesite="strict",
        secure=settings.cookie_secure,
        max_age=settings.session_seconds,
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return {"user_id": str(user["id"]), "csrf_token": csrf}


@router.get("/session")
def current(actor: Actor, response: Response) -> dict[str, str]:
    response.headers["Cache-Control"] = "no-store"
    return {"user_id": str(actor.id), "csrf_token": actor.csrf}


@router.delete("/session", status_code=204)
def logout(actor: Actor, request: Request, response: Response) -> None:
    with connect(settings_for(request)) as db:
        db.execute("DELETE FROM sessions WHERE token_hash=%s", (actor.token_hash,))
    response.delete_cookie(COOKIE, path="/", httponly=True, samesite="strict")
