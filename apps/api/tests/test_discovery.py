from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from jobhunter_api.store import Row


def add_source(client: TestClient, provider: str = "greenhouse") -> Row:
    response = client.post(
        "/api/v1/discovery/sources",
        json={
            "provider": provider,
            "name": "Synthetic careers",
            "reference": "synthetic" if provider == "greenhouse" else "alerts",
        },
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


def enable(client: TestClient, source: Row) -> Row:
    response = client.patch(
        f"/api/v1/discovery/sources/{source['id']}",
        json={
            "expected_version": source["version"],
            "enabled": True,
            "access_confirmed": True,
            "terms_url": "https://example.com/terms",
            "permission_note": "Synthetic permission for contract tests only.",
            "review_until": (datetime.now(UTC).date() + timedelta(days=30)).isoformat(),
        },
    )
    assert response.status_code == 200, response.text
    return dict(response.json())


def test_source_lifecycle_review_and_ownership(signed_client: TestClient) -> None:
    client = signed_client
    source = add_source(client)
    assert source["enabled"] is False
    response = client.patch(
        f"/api/v1/discovery/sources/{source['id']}",
        json={
            "expected_version": 1,
            "enabled": True,
        },
    )
    assert response.status_code == 422
    enabled = enable(client, source)
    assert enabled["enabled"] and enabled["reviewed_at"]
    assert client.get("/api/v1/discovery/sources").json()[0]["ready"]
    assert (
        client.patch(
            f"/api/v1/discovery/sources/{source['id']}",
            json={
                "expected_version": 1,
            },
        ).status_code
        == 409
    )
    assert client.get(f"/api/v1/discovery/sources/{uuid4()}/runs").status_code == 404
    assert client.get(f"/api/v1/discovery/sources/{source['id']}/runs").json() == []


def test_source_input_duplicates_and_gmail_gate(signed_client: TestClient) -> None:
    client = signed_client
    for reference in ("../internal", "https://example.com", "a?x=1"):
        assert (
            client.post(
                "/api/v1/discovery/sources",
                json={
                    "provider": "greenhouse",
                    "name": "Test",
                    "reference": reference,
                },
            ).status_code
            == 422
        )
    add_source(client)
    assert (
        client.post(
            "/api/v1/discovery/sources",
            json={
                "provider": "greenhouse",
                "name": "Other name",
                "reference": "synthetic",
            },
        ).status_code
        == 409
    )
    gmail = add_source(client, "gmail")
    assert (
        client.patch(
            f"/api/v1/discovery/sources/{gmail['id']}",
            json={
                "expected_version": 1,
                "enabled": True,
                "access_confirmed": True,
                "terms_url": "https://example.com/terms",
                "permission_note": "Read alerts",
                "review_until": datetime.now(UTC).date().isoformat(),
            },
        ).json()["error"]["code"]
        == "GMAIL_LABEL_REQUIRED"
    )
    client.headers.pop("X-CSRF-Token")
    assert (
        client.post(
            "/api/v1/discovery/sources",
            json={
                "provider": "gmail",
                "name": "Mail",
                "reference": "alerts",
            },
        ).status_code
        == 403
    )
