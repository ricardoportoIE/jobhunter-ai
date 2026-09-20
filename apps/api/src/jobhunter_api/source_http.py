"""Bounded HTTPS transport for fixed discovery providers, with no redirects."""

import http.client
import json
import socket
import ssl
import time
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

from jobhunter_api.job_url import public_target
from jobhunter_api.store import Row

HOSTS = {"boards-api.greenhouse.io", "gmail.googleapis.com", "oauth2.googleapis.com"}
MAX_BYTES = 4 * 1024 * 1024


class SourceFailure(Exception):
    def __init__(self, code: str, *, stop: bool = False, retry_at: str | None = None):
        self.code, self.stop, self.retry_at = code, stop, retry_at


def retry_time(value: str | None) -> str | None:
    if not value:
        return None
    try:
        when = (
            datetime.now(UTC) + timedelta(seconds=max(0, int(value)))
            if value.isdigit()
            else parsedate_to_datetime(value)
        )
        return when.astimezone(UTC).isoformat()
    except (ValueError, OverflowError, TypeError):
        return None


def request_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
    deadline: float | None = None,
) -> tuple[int, dict[str, str], Row]:
    if urlsplit(url).hostname not in HOSTS:
        raise SourceFailure("SOURCE_ENDPOINT_REJECTED", stop=True)
    deadline = deadline or time.monotonic() + 15
    for attempt in range(3):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise SourceFailure("SOURCE_TIMEOUT")
        connection: http.client.HTTPSConnection | None = None
        raw: socket.socket | None = None
        try:
            host, path, addresses = public_target(url)
            connection = http.client.HTTPSConnection(host, timeout=min(remaining, 8))
            raw = socket.create_connection((addresses[0], 443), timeout=min(remaining, 8))
            connection.sock = ssl.create_default_context().wrap_socket(raw, server_hostname=host)
            connection.request(
                "POST" if body is not None else "GET",
                path,
                body=body,
                headers={
                    "User-Agent": "JobHunterAI/1.0",
                    "Accept": "application/json",
                    "Accept-Encoding": "identity",
                    **(headers or {}),
                },
            )
            response = connection.getresponse()
            result_headers = {key.lower(): value for key, value in response.getheaders()}
            status = response.status
            if status == 304:
                return status, result_headers, {}
            if status in {401, 403}:
                raise SourceFailure("SOURCE_ACCESS_DENIED", stop=True)
            if status == 429 or status in {502, 503, 504}:
                retry_at = retry_time(result_headers.get("retry-after"))
                if status == 429 or retry_at or attempt == 2 or body is not None:
                    raise SourceFailure(
                        "SOURCE_RATE_LIMIT" if status == 429 else "SOURCE_UNAVAILABLE",
                        retry_at=retry_at,
                    )
                continue
            if status != 200:
                if status == 400 and url == "https://oauth2.googleapis.com/token":
                    raise SourceFailure("GMAIL_RECONNECT", stop=True)
                raise SourceFailure("SOURCE_NOT_FOUND" if status == 404 else "SOURCE_HTTP_ERROR")
            if result_headers.get("content-encoding", "identity") not in {"identity", ""}:
                raise SourceFailure("SOURCE_INVALID_RESPONSE")
            chunks = bytearray()
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError
                if connection.sock:
                    connection.sock.settimeout(min(remaining, 8))
                chunk = response.read1(min(65536, MAX_BYTES + 1 - len(chunks)))
                if not chunk:
                    break
                chunks.extend(chunk)
                if len(chunks) > MAX_BYTES:
                    raise SourceFailure("SOURCE_CONTENT_LIMIT")
            result = json.loads(chunks) if chunks else {}
            if not isinstance(result, dict):
                raise SourceFailure("SOURCE_INVALID_RESPONSE")
            return status, result_headers, result
        except SourceFailure:
            raise
        except (ValueError, RecursionError):
            raise SourceFailure("SOURCE_INVALID_RESPONSE") from None
        except Exception:
            if attempt == 2 or body is not None:
                raise SourceFailure("SOURCE_UNAVAILABLE") from None
        finally:
            if connection:
                connection.close()
            if raw:
                raw.close()
    raise SourceFailure("SOURCE_UNAVAILABLE")
