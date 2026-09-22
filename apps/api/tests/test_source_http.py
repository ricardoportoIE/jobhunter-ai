import json
from typing import Any
from unittest.mock import Mock

import pytest

from jobhunter_api.source_http import SourceFailure, connect_address, request_json


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


@pytest.mark.parametrize(
    "addresses", [["2607:f8b0::1", "142.250.1.1"], ["142.250.1.1", "2607:f8b0::1"]]
)
def test_unreachable_address_falls_back_before_oauth_post(
    monkeypatch: pytest.MonkeyPatch, addresses: list[str]
) -> None:
    connection = wire(monkeypatch, [200])
    monkeypatch.setattr(
        "jobhunter_api.source_http.public_target",
        lambda _: ("oauth2.googleapis.com", "/token", addresses),
    )
    raw = Mock()
    dial = Mock(side_effect=[OSError(101, "Network unreachable"), raw])
    monkeypatch.setattr("jobhunter_api.source_http.socket.create_connection", dial)
    request_json("https://oauth2.googleapis.com/token", body=b"synthetic")
    assert [call.args[0] for call in dial.call_args_list] == [(a, 443) for a in addresses]
    assert connection.request.call_count == 1
    assert connection.request.call_args.args[0] == "POST"
    raw.close.assert_called_once()


def test_all_addresses_unreachable_never_sends_oauth_post(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = wire(monkeypatch, [200])
    dial = Mock(side_effect=OSError(101, "Network unreachable"))
    monkeypatch.setattr("jobhunter_api.source_http.socket.create_connection", dial)
    with pytest.raises(SourceFailure) as failure:
        request_json("https://oauth2.googleapis.com/token", body=b"synthetic")
    assert failure.value.code == "SOURCE_UNAVAILABLE"
    assert dial.call_count == 1
    connection.request.assert_not_called()


def test_address_fallback_keeps_the_overall_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("jobhunter_api.source_http.time.monotonic", Mock(side_effect=[1, 5]))
    dial = Mock(side_effect=TimeoutError)
    monkeypatch.setattr("jobhunter_api.source_http.socket.create_connection", dial)
    with pytest.raises(SourceFailure) as failure:
        connect_address(["2607:f8b0::1", "142.250.1.1"], deadline=4)
    assert failure.value.code == "SOURCE_TIMEOUT"
    dial.assert_called_once_with(("2607:f8b0::1", 443), timeout=3)


@pytest.mark.parametrize(
    "field,reason", [("details", "SERVICE_DISABLED"), ("errors", "accessNotConfigured")]
)
def test_disabled_gmail_api_is_distinct_and_redacted(
    monkeypatch: pytest.MonkeyPatch, field: str, reason: str
) -> None:
    content = json.dumps(
        {"error": {field: [{"reason": reason}], "message": "private-sentinel"}}
    ).encode()
    connection = wire(monkeypatch, [403], content=content)
    with pytest.raises(SourceFailure) as failure:
        request_json("https://gmail.googleapis.com/gmail/v1/users/me/labels")
    assert failure.value.code == "GMAIL_API_DISABLED" and failure.value.stop
    assert "private-sentinel" not in str(failure.value)
    assert connection.request.call_count == 1


@pytest.mark.parametrize(
    "content",
    [
        b"invalid",
        b"[]",
        b'{"error":{"details":null}}',
        b'{"error":{"details":[null]}}',
        b"x" * 16385,
    ],
)
def test_unrecognised_or_oversized_forbidden_body_stays_denied(
    monkeypatch: pytest.MonkeyPatch, content: bytes
) -> None:
    wire(monkeypatch, [403], content=content)
    with pytest.raises(SourceFailure) as failure:
        request_json("https://gmail.googleapis.com/gmail/v1/users/me/labels")
    assert failure.value.code == "SOURCE_ACCESS_DENIED"
