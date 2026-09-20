import json
import socket
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from test_job_parser import RAW, parsed

from jobhunter_api.errors import Problem
from jobhunter_api.inference import Completion
from jobhunter_api.job_url import fetch_vacancy, page_text, public_target, safe_address


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.1",
        "169.254.169.254",
        "::1",
        "fc00::1",
        "224.0.0.1",
        "64:ff9b::7f00:1",
        "2002:7f00:1::",
    ],
)
def test_private_and_translated_addresses_are_denied(address: str) -> None:
    assert not safe_address(address)
    with (
        patch(
            "socket.getaddrinfo",
            return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443))],
        ),
        pytest.raises(Problem),
    ):
        public_target("https://careers.example.com/job")


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "https://user:password@example.com",
        "https://example.com:8443",
        "https://linkedin.com./jobs/1",
        "https://localhost",
        "file:///etc/passwd",
    ],
)
def test_invalid_urls_never_connect(url: str) -> None:
    with pytest.raises(Problem):
        public_target(url)


def test_structured_page_and_multiple_jobs() -> None:
    advert = {
        "@type": "JobPosting",
        "title": "Junior Python Developer",
        "description": "<p>" + RAW * 3 + "</p>",
    }
    page = (
        '<script type="application/ld+json">'
        + json.dumps(advert)
        + "</script><script>alert(1)</script>"
    )
    text = page_text(page.encode(), "text/html")
    assert "Python" in text and "alert(1)" not in text and "<p>" not in text
    with pytest.raises(Problem) as error:
        page_text(
            (
                '<script type="application/ld+json">'
                + json.dumps([advert, {**advert, "title": "Different vacancy"}])
                + "</script>"
            ).encode(),
            "text/html",
        )
    assert error.value.code == "URL_MULTIPLE_JOBS"


def test_robots_denial_and_redirect_destination_validation() -> None:
    with (
        patch(
            "jobhunter_api.job_url.public_target", return_value=("example.com", "/job", ["8.8.8.8"])
        ),
        patch(
            "jobhunter_api.job_url.request_page",
            return_value=(200, {}, b"User-agent: *\nDisallow: /"),
        ),
        pytest.raises(Problem) as error,
    ):
        fetch_vacancy("https://example.com/job")
    assert error.value.code == "URL_ACCESS_RESTRICTED"
    with (
        patch(
            "jobhunter_api.job_url.public_target",
            side_effect=[
                ("example.com", "/job", ["8.8.8.8"]),
                Problem(422, "URL_NOT_ALLOWED", "Blocked"),
            ],
        ),
        patch(
            "jobhunter_api.job_url.request_page",
            side_effect=[(404, {}, b""), (302, {"location": "https://127.0.0.1/private"}, b"")],
        ),
        pytest.raises(Problem) as error,
    ):
        fetch_vacancy("https://example.com/job")
    assert error.value.code == "URL_NOT_ALLOWED"


def test_url_import_extracts_draft_preserves_review_and_recovers_failure(
    signed_client: TestClient,
) -> None:
    client = signed_client
    with (
        patch(
            "jobhunter_api.job_url.fetch_vacancy", return_value=("https://example.com/jobs/1", RAW)
        ),
        patch("jobhunter_api.job_url.get_provider") as provider,
    ):
        provider.return_value.complete.return_value = Completion(
            json.dumps(parsed()), 100, 100, "fixture", 1, "completed"
        )
        assert (
            client.post(
                "/api/v1/jobs/import-url", json={"url": "https://example.com/jobs/1"}
            ).status_code
            == 422
        )
        result = client.post(
            "/api/v1/jobs/import-url",
            json={"url": "https://example.com/jobs/1", "ai_consent": True},
        )
        assert result.status_code in {200, 201}, result.text
        body = result.json()
        assert (
            body["extraction_error"] is None and body["job"]["title"] == "Junior Python Developer"
        )
        assert body["job"]["status"] == "DISCOVERED" and body["job"]["reviewed_at"] is None
        repeated = client.post(
            "/api/v1/jobs/import-url",
            json={"url": "https://example.com/jobs/1", "ai_consent": True},
        )
        assert repeated.json()["job"]["id"] == body["job"]["id"]
        assert provider.return_value.complete.call_count == 1
    with (
        patch(
            "jobhunter_api.job_url.fetch_vacancy",
            return_value=("https://example.com/jobs/2", RAW + " New vacancy"),
        ),
        patch(
            "jobhunter_api.job_url.get_provider",
            side_effect=Problem(409, "AI_NOT_CONFIGURED", "Configure AI"),
        ),
    ):
        result = client.post(
            "/api/v1/jobs/import-url",
            json={"url": "https://example.com/jobs/2", "ai_consent": True},
        )
        assert result.json()["extraction_error"] == "AI_NOT_CONFIGURED"
        assert client.get("/api/v1/jobs/" + result.json()["job"]["id"]).status_code == 200
