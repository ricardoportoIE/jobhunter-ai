from typing import Any
from unittest.mock import Mock

import pytest

from jobhunter_api.source_http import SourceFailure, request_json


def wire(
    monkeypatch: pytest.MonkeyPatch,
    statuses: list[int],
    headers: dict[str, str] | None = None,
    content: bytes = b"{}",
) -> Mock:
    responses = []
    for status in statuses:
        response = Mock(status=status)
        response.getheaders.return_value = list((headers or {}).items())
        response.read1.side_effect = [content, b""]
        responses.append(response)
    connection = Mock()
    connection.getresponse.side_effect = responses
    monkeypatch.setattr(
        "jobhunter_api.source_http.public_target",
        lambda _: (
            "gmail.googleapis.com",
            "/test",
            ["1.1.1.1"],
        ),
    )
    monkeypatch.setattr(
        "jobhunter_api.source_http.http.client.HTTPSConnection", lambda *a, **kw: connection
    )
    monkeypatch.setattr(
        "jobhunter_api.source_http.socket.create_connection", lambda *a, **kw: Mock()
    )
    monkeypatch.setattr("jobhunter_api.source_http.ssl.create_default_context", lambda: Mock())
    return connection


@pytest.mark.parametrize(
    "status,code,stop",
    [
        (301, "SOURCE_HTTP_ERROR", False),
        (401, "SOURCE_ACCESS_DENIED", True),
        (403, "SOURCE_ACCESS_DENIED", True),
        (404, "SOURCE_NOT_FOUND", False),
        (429, "SOURCE_RATE_LIMIT", False),
    ],
)
def test_http_failures_never_follow_redirects(
    monkeypatch: pytest.MonkeyPatch, status: int, code: str, stop: bool
) -> None:
    connection = wire(
        monkeypatch, [status], {"Location": "https://127.0.0.1/private", "Retry-After": "86400"}
    )
    with pytest.raises(SourceFailure) as failure:
        request_json("https://gmail.googleapis.com/gmail/v1/users/me/messages")
    assert failure.value.code == code and failure.value.stop is stop
    assert connection.request.call_count == 1
    if status == 429:
        assert failure.value.retry_at is not None


def test_retry_policy_and_body_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = wire(monkeypatch, [503, 502, 200])
    assert request_json("https://boards-api.greenhouse.io/v1/boards/example/jobs")[0] == 200
    assert connection.request.call_count == 3
    connection = wire(monkeypatch, [503])
    with pytest.raises(SourceFailure):
        request_json("https://oauth2.googleapis.com/token", body=b"synthetic")
    assert connection.request.call_count == 1
    wire(monkeypatch, [200], content=b"x" * 21)
    monkeypatch.setattr("jobhunter_api.source_http.MAX_BYTES", 20)
    with pytest.raises(SourceFailure) as failure:
        request_json("https://gmail.googleapis.com/gmail/v1/users/me/messages")
    assert failure.value.code == "SOURCE_CONTENT_LIMIT"


def test_invalid_grant_disables_connection_and_empty_revoke_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wire(monkeypatch, [400])
    with pytest.raises(SourceFailure) as failure:
        request_json("https://oauth2.googleapis.com/token", body=b"synthetic")
    assert failure.value.code == "GMAIL_RECONNECT" and failure.value.stop
    wire(monkeypatch, [200], content=b"")
    assert request_json("https://oauth2.googleapis.com/revoke", body=b"synthetic")[2] == {}


def test_transport_revalidates_dns_and_preserves_bearer_only_on_allowed_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = wire(monkeypatch, [200])
    lookups: list[str] = []

    def target(url: str) -> tuple[str, str, list[str]]:
        lookups.append(url)
        return "gmail.googleapis.com", "/gmail/v1/users/me/labels", ["1.1.1.1"]

    monkeypatch.setattr("jobhunter_api.source_http.public_target", target)
    request_json(
        "https://gmail.googleapis.com/gmail/v1/users/me/labels",
        headers={"Authorization": "Bearer synthetic"},
    )
    assert len(lookups) == 1
    kwargs: dict[str, Any] = connection.request.call_args.kwargs
    assert kwargs["headers"]["Authorization"] == "Bearer synthetic"
    with pytest.raises(SourceFailure):
        request_json("https://evil.example/steal", headers={"Authorization": "Bearer synthetic"})
    assert len(lookups) == 1 and connection.request.call_count == 1
