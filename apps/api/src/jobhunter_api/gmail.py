"""Read-only Gmail OAuth and bounded, explicitly labelled email discovery."""

import base64
import hashlib
import json
import re
import secrets
import time
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode, urlsplit
from uuid import UUID, uuid4

from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Request
from pydantic import Field

from jobhunter_api.auth import Actor, digest, settings_for
from jobhunter_api.errors import Problem
from jobhunter_api.greenhouse import DiscoveredItem, DiscoveryBatch
from jobhunter_api.job_url import PageText
from jobhunter_api.profile import Input
from jobhunter_api.records import get_record, owner_lock, public, update
from jobhunter_api.settings import Settings
from jobhunter_api.source_http import SourceFailure, request_json
from jobhunter_api.store import Connection, Row, connect

router = APIRouter(prefix="/api/v1/discovery/gmail", tags=["Gmail discovery"])
SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_URL = "https://gmail.googleapis.com/gmail/v1/users/me"


def cipher(settings: Settings) -> Fernet:
    try:
        if not settings.discovery_encryption_key:
            raise ValueError
        return Fernet(settings.discovery_encryption_key.get_secret_value().encode())
    except (ValueError, TypeError):
        raise Problem(
            409, "GMAIL_NOT_CONFIGURED", "Configure Gmail credentials and encryption first."
        ) from None


def configured(settings: Settings) -> bool:
    try:
        cipher(settings)
        uri = urlsplit(settings.gmail_redirect_uri)
        origin = f"{uri.scheme}://{uri.netloc}"
        return bool(
            settings.gmail_client_id
            and settings.gmail_client_secret
            and settings.gmail_client_secret.get_secret_value()
            and origin in settings.allowed_origins
            and uri.path in {"", "/"}
            and not uri.query
            and not uri.fragment
            and not uri.username
            and (
                uri.scheme == "https"
                or uri.scheme == "http"
                and uri.hostname in {"127.0.0.1", "localhost"}
            )
        )
    except Problem:
        return False


def seal(settings: Settings, owner: UUID, source_id: UUID, purpose: str, value: Row) -> str:
    return (
        cipher(settings)
        .encrypt(
            json.dumps(
                {"owner": str(owner), "source": str(source_id), "purpose": purpose, "value": value}
            ).encode()
        )
        .decode()
    )


def unseal(settings: Settings, owner: UUID, source_id: UUID, purpose: str, value: str) -> Row:
    try:
        envelope = json.loads(cipher(settings).decrypt(value.encode()))
        if (envelope["owner"], envelope["source"], envelope["purpose"]) != (
            str(owner),
            str(source_id),
            purpose,
        ):
            raise ValueError
        return dict(envelope["value"])
    except (InvalidToken, ValueError, KeyError, TypeError):
        raise Problem(409, "GMAIL_RECONNECT", "Reconnect Gmail to restore access.") from None


def put_secret(
    db: Connection,
    settings: Settings,
    owner: UUID,
    source_id: UUID,
    purpose: str,
    value: Row,
    expires: datetime | None = None,
) -> None:
    db.execute(
        "INSERT INTO discovery_secrets VALUES (%s,%s,%s,%s,%s) "
        "ON CONFLICT(owner_id,source_id,purpose) DO UPDATE "
        "SET ciphertext=excluded.ciphertext,expires_at=excluded.expires_at",
        (owner, source_id, purpose, seal(settings, owner, source_id, purpose, value), expires),
    )


@router.get("/status")
def status(actor: Actor, request: Request) -> Row:
    settings = settings_for(request)
    return {
        "configured": configured(settings),
        "redirect_uri": settings.gmail_redirect_uri,
        "scope": SCOPE,
    }


class StartOAuth(Input):
    source_id: UUID
    reading_confirmed: bool = False


@router.post("/start")
def start(data: StartOAuth, actor: Actor, request: Request) -> Row:
    settings = settings_for(request)
    if not configured(settings):
        raise Problem(
            409, "GMAIL_NOT_CONFIGURED", "Configure Gmail credentials and encryption first."
        )
    if not data.reading_confirmed:
        raise Problem(422, "GMAIL_CONSENT_REQUIRED", "Confirm read-only access before connecting.")
    state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(48)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    )
    with connect(settings) as db:
        owner_lock(db, actor.id)
        source = get_record(db, actor.id, "discovery_source", data.source_id)
        if source["data"]["provider"] != "gmail" or source["data"]["enabled"]:
            raise Problem(409, "GMAIL_PAUSE_REQUIRED", "Pause the Gmail source before connecting.")
        update(db, source, source["version"], {**source["data"], "last_error": None})
        put_secret(
            db,
            settings,
            actor.id,
            data.source_id,
            "oauth",
            {"state_hash": digest(state), "session_hash": actor.token_hash, "verifier": verifier},
            datetime.now(UTC) + timedelta(minutes=10),
        )
    return {
        "url": "https://accounts.google.com/o/oauth2/v2/auth?"
        + urlencode(
            {
                "client_id": settings.gmail_client_id,
                "redirect_uri": settings.gmail_redirect_uri,
                "response_type": "code",
                "scope": SCOPE,
                "access_type": "offline",
                "prompt": "consent",
                "state": f"{data.source_id}.{state}",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )
    }


class CompleteOAuth(Input):
    state: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=4000)


@router.post("/complete")
def complete(data: CompleteOAuth, actor: Actor, request: Request) -> Row:
    settings = settings_for(request)
    if not configured(settings):
        raise Problem(409, "GMAIL_NOT_CONFIGURED", "Configure Gmail first.")
    try:
        source_text, state = data.state.split(".", 1)
        source_id = UUID(source_text)
    except ValueError:
        raise Problem(422, "OAUTH_STATE_INVALID", "Restart the Gmail connection.") from None
    with connect(settings) as db:
        owner_lock(db, actor.id)
        source = get_record(db, actor.id, "discovery_source", source_id)
        stored = db.execute(
            "SELECT * FROM discovery_secrets WHERE owner_id=%s AND source_id=%s "
            "AND purpose='oauth' AND expires_at>now()",
            (actor.id, source_id),
        ).fetchone()
        if not stored:
            raise Problem(409, "OAUTH_STATE_INVALID", "The connection expired. Start again.")
        flow = unseal(settings, actor.id, source_id, "oauth", stored["ciphertext"])
        if (
            not secrets.compare_digest(flow["state_hash"], digest(state))
            or flow["session_hash"] != actor.token_hash
        ):
            raise Problem(
                403, "OAUTH_STATE_INVALID", "Use the session that started the connection."
            )
        db.execute(
            "DELETE FROM discovery_secrets WHERE owner_id=%s AND source_id=%s AND purpose='oauth'",
            (actor.id, source_id),
        )
    assert settings.gmail_client_secret
    try:
        _, _, token = request_json(
            TOKEN_URL,
            body=urlencode(
                {
                    "client_id": settings.gmail_client_id,
                    "client_secret": settings.gmail_client_secret.get_secret_value(),
                    "redirect_uri": settings.gmail_redirect_uri,
                    "grant_type": "authorization_code",
                    "code": data.code,
                    "code_verifier": flow["verifier"],
                }
            ).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        validate_token(token, require_scope=True)
        if (
            not isinstance(token.get("refresh_token"), str)
            or not token["refresh_token"]
            or len(token["refresh_token"]) > 10000
        ):
            raise SourceFailure("GMAIL_RECONNECT")
    except SourceFailure as error:
        if error.code in {"SOURCE_UNAVAILABLE", "SOURCE_TIMEOUT", "SOURCE_RATE_LIMIT"}:
            raise Problem(
                503,
                "GMAIL_CONNECTION_FAILED",
                "The local service could not reach Google or Google is temporarily unavailable. "
                "Check the connection and start Gmail sign-in again.",
            ) from None
        raise Problem(
            409,
            "GMAIL_RECONNECT",
            "Google could not connect. Start again and grant read-only access.",
        ) from None
    with connect(settings) as db:
        owner_lock(db, actor.id)
        current = get_record(db, actor.id, "discovery_source", source_id)
        if current["version"] != source["version"]:
            raise Problem(409, "VERSION_CONFLICT", "The source changed. Restart the connection.")
        put_secret(db, settings, actor.id, source_id, "token", token_value(token))
        return public(
            update(
                db,
                current,
                current["version"],
                {
                    **current["data"],
                    "connected": True,
                    "connection_id": str(uuid4()),
                    "enabled": False,
                    "label_id": "",
                    "label_name": "",
                    "cursor": None,
                    "last_error": None,
                    "next_sync_at": None,
                },
            )
        )


def validate_token(token: Row, *, require_scope: bool = False) -> None:
    if (
        not isinstance(token.get("access_token"), str)
        or not token["access_token"]
        or len(token["access_token"]) > 10000
        or token.get("token_type", "").lower() != "bearer"
        or not isinstance(token.get("expires_in"), int)
        or not 60 <= token["expires_in"] <= 86400
        or (require_scope or "scope" in token)
        and set(token.get("scope", "").split()) != {SCOPE}
    ):
        raise SourceFailure("GMAIL_RECONNECT", stop=True)


def token_value(token: Row) -> Row:
    return {
        "access_token": token["access_token"],
        "refresh_token": token["refresh_token"],
        "expires_at": (datetime.now(UTC) + timedelta(seconds=token["expires_in"])).isoformat(),
    }


def access_token(settings: Settings, source: Row, deadline: float) -> str:
    owner, source_id = source["owner_id"], source["id"]
    with connect(settings) as db:
        row = db.execute(
            "SELECT ciphertext FROM discovery_secrets WHERE owner_id=%s "
            "AND source_id=%s AND purpose='token'",
            (owner, source_id),
        ).fetchone()
    if not source["data"]["connected"] or not row:
        raise SourceFailure("GMAIL_RECONNECT", stop=True)
    try:
        token = unseal(settings, owner, source_id, "token", row["ciphertext"])
    except Problem:
        raise SourceFailure("GMAIL_RECONNECT", stop=True) from None
    if datetime.fromisoformat(token["expires_at"]) <= datetime.now(UTC) + timedelta(seconds=60):
        if not configured(settings) or not settings.gmail_client_secret:
            raise SourceFailure("GMAIL_NOT_CONFIGURED", stop=True)
        _, _, refreshed = request_json(
            TOKEN_URL,
            deadline=deadline,
            body=urlencode(
                {
                    "client_id": settings.gmail_client_id,
                    "client_secret": settings.gmail_client_secret.get_secret_value(),
                    "refresh_token": token["refresh_token"],
                    "grant_type": "refresh_token",
                }
            ).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        validate_token(refreshed)
        token = token_value(
            {**refreshed, "refresh_token": refreshed.get("refresh_token") or token["refresh_token"]}
        )
        with connect(settings) as db:
            owner_lock(db, owner)
            current = get_record(db, owner, "discovery_source", source_id)
            present = db.execute(
                "SELECT ciphertext FROM discovery_secrets WHERE owner_id=%s "
                "AND source_id=%s AND purpose='token'",
                (owner, source_id),
            ).fetchone()
            if (
                not current["data"]["connected"]
                or not present
                or present["ciphertext"] != row["ciphertext"]
            ):
                raise SourceFailure("GMAIL_RECONNECT", stop=True)
            put_secret(db, settings, owner, source_id, "token", token)
    return str(token["access_token"])


def gmail_get(path: str, token: str, deadline: float) -> Row:
    if not (
        path == "/labels"
        or path.startswith("/messages?")
        or re.fullmatch(r"/messages/[A-Za-z0-9_-]+\?format=full", path)
    ):
        raise SourceFailure("SOURCE_ENDPOINT_REJECTED", stop=True)
    return request_json(
        GMAIL_URL + path, headers={"Authorization": "Bearer " + token}, deadline=deadline
    )[2]


def custom_labels(token: str, deadline: float) -> list[Row]:
    payload = gmail_get("/labels", token, deadline)
    values = payload.get("labels", [])
    if not isinstance(values, list) or len(values) > 10000:
        raise SourceFailure("SOURCE_INVALID_RESPONSE")
    return [
        {"id": value["id"], "name": value["name"]}
        for value in values
        if value.get("type") == "user"
        and re.fullmatch(r"Label_[A-Za-z0-9_-]+", value.get("id", ""))
        and isinstance(value.get("name"), str)
        and len(value["name"]) <= 100
    ]


@router.get("/{source_id}/labels")
def labels(source_id: UUID, actor: Actor, request: Request) -> list[Row]:
    settings = settings_for(request)
    with connect(settings) as db:
        source = get_record(db, actor.id, "discovery_source", source_id)
    deadline = time.monotonic() + 15
    try:
        return custom_labels(access_token(settings, source, deadline), deadline)
    except SourceFailure:
        raise Problem(
            409, "GMAIL_RECONNECT", "Could not read labels. Check the Gmail connection."
        ) from None


@router.post("/{source_id}/disconnect")
def disconnect(source_id: UUID, actor: Actor, request: Request) -> Row:
    settings = settings_for(request)
    with connect(settings) as db:
        owner_lock(db, actor.id)
        source = get_record(db, actor.id, "discovery_source", source_id)
        row = db.execute(
            "SELECT ciphertext FROM discovery_secrets WHERE owner_id=%s "
            "AND source_id=%s AND purpose='token'",
            (actor.id, source_id),
        ).fetchone()
        db.execute(
            "DELETE FROM discovery_secrets WHERE owner_id=%s AND source_id=%s",
            (actor.id, source_id),
        )
        update(
            db,
            source,
            source["version"],
            {
                **source["data"],
                "enabled": False,
                "connected": False,
                "label_id": "",
                "label_name": "",
                "cursor": None,
            },
        )
    revoked = False
    if row:
        try:
            token = unseal(settings, actor.id, source_id, "token", row["ciphertext"])
            request_json(
                "https://oauth2.googleapis.com/revoke",
                body=urlencode(
                    {
                        "token": token["refresh_token"],
                    }
                ).encode(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            revoked = True
        except (SourceFailure, Problem):
            pass
    return {"disconnected": True, "revoked": revoked}


class EmailText(PageText):
    def __init__(self, links: list[str]) -> None:
        super().__init__()
        self.links = links

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        super().handle_starttag(tag, attrs)
        if tag == "a" and len(self.links) < 30:
            reference = dict(attrs).get("href")
            if reference:
                self.links.append(reference)


def message_text(payload: Row, depth: int = 0, links: list[str] | None = None) -> str:
    links = links if links is not None else []
    if depth > 12:
        raise SourceFailure("SOURCE_CONTENT_LIMIT")
    # Attachments are never requested, decoded or followed.
    if payload.get("filename"):
        return ""
    parts = payload.get("parts", [])
    if len(parts) > 100:
        raise SourceFailure("SOURCE_CONTENT_LIMIT")
    if parts:
        text = "\n".join(filter(None, (message_text(part, depth + 1, links) for part in parts)))
    elif payload.get("mimeType") in {"text/plain", "text/html"}:
        data = payload.get("body", {}).get("data", "")
        if len(data) > 100000:
            raise SourceFailure("SOURCE_CONTENT_LIMIT")
        text = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode(
            "utf-8", errors="replace"
        )
        if payload.get("mimeType") == "text/html":
            parser = EmailText(links)
            parser.feed(text)
            text = "\n".join(parser.parts)
        else:
            links.extend(re.findall(r"https://[^\s<>\"']+", text)[: max(0, 30 - len(links))])
    else:
        text = ""
    if len(text) > 50000:
        raise SourceFailure("SOURCE_CONTENT_LIMIT")
    return text


def read_gmail(settings: Settings, source: Row) -> DiscoveryBatch:
    deadline = time.monotonic() + 60
    token = access_token(settings, source, deadline)
    label_id = source["data"]["label_id"]
    if not any(label["id"] == label_id for label in custom_labels(token, deadline)):
        raise SourceFailure("GMAIL_LABEL_MISSING", stop=True)
    params = {"labelIds": label_id, "maxResults": "20", "includeSpamTrash": "false"}
    payload = gmail_get("/messages?" + urlencode(params), token, deadline)
    messages = payload.get("messages", [])
    if not isinstance(messages, list) or len(messages) > 20:
        raise SourceFailure("SOURCE_INVALID_RESPONSE")
    cursor = payload.get("nextPageToken")
    if source["data"].get("cursor"):
        try:
            older = gmail_get(
                "/messages?" + urlencode({**params, "pageToken": source["data"]["cursor"]}),
                token,
                deadline,
            )
        except SourceFailure as error:
            if error.code == "SOURCE_HTTP_ERROR":
                raise SourceFailure("GMAIL_CURSOR_EXPIRED") from None
            raise
        backlog = older.get("messages", [])
        if not isinstance(backlog, list) or len(backlog) > 20:
            raise SourceFailure("SOURCE_INVALID_RESPONSE")
        messages = [*messages, *backlog]
        cursor = older.get("nextPageToken")
    if cursor is not None and (not isinstance(cursor, str) or len(cursor) > 2000):
        raise SourceFailure("SOURCE_INVALID_RESPONSE")
    items = []
    visited: set[str] = set()
    for message in messages:
        message_id = str(message["id"])
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", message_id):
            raise SourceFailure("SOURCE_INVALID_RESPONSE")
        if message_id in visited:
            continue
        visited.add(message_id)
        try:
            value = gmail_get(f"/messages/{message_id}?format=full", token, deadline)
        except SourceFailure as error:
            if error.code == "SOURCE_NOT_FOUND":
                continue
            raise
        if label_id not in value.get("labelIds", []):
            continue  # Labels may change between listing and reading a message.
        content = value["payload"]
        headers = {header["name"].lower(): header["value"] for header in content.get("headers", [])}
        links: list[str] = []
        text = message_text(content, links=links)
        safe_links = []
        for link in dict.fromkeys(links):
            try:
                if len(link) > 2000:
                    continue
                safe_links.append(DiscoveredItem.safe_reference(link))
            except ValueError:
                continue
        if not text.strip():
            continue
        items.append(
            DiscoveredItem(
                external_id=f"{source['data'].get('connection_id', 'legacy')}:{message_id}",
                title=headers.get("subject", "Email alert")[:500] or "Email alert",
                url=f"https://mail.google.com/mail/u/0/#all/{message_id}",
                raw_text=text,
                source_updated_at=str(value.get("internalDate", ""))[:100],
                item_type="email",
                links=safe_links[:30],
            )
        )
    return DiscoveryBatch(items=items, cursor=cursor)
