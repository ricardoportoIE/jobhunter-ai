from datetime import UTC, datetime, timedelta

from conftest import TEST_PASSWORD
from fastapi.testclient import TestClient

from jobhunter_api.settings import Settings
from jobhunter_api.store import connect


def test_session_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/session")
    assert response.status_code == 401
    assert response.json()["error"]["correlation_id"]


def test_cookie_csrf_origin_logout_and_replay(signed_client: TestClient) -> None:
    client = signed_client
    assert client.get("/api/v1/session").status_code == 200
    cookie = client.cookies.get("jobhunter_session")
    assert client.delete("/api/v1/session", headers={"X-CSRF-Token": "wrong"}).status_code == 403
    assert (
        client.delete("/api/v1/session", headers={"Origin": "https://evil.test"}).status_code == 403
    )
    assert client.delete("/api/v1/session").status_code == 204
    client.cookies.set("jobhunter_session", cookie or "")
    assert client.get("/api/v1/session").status_code == 401


def test_password_hash_and_expiration(signed_client: TestClient, db_settings: Settings) -> None:
    with connect(db_settings) as db:
        row = db.execute("SELECT password_hash FROM users").fetchone()
        assert row and row["password_hash"].startswith("$argon2id$")
        assert TEST_PASSWORD not in row["password_hash"]
        db.execute("UPDATE sessions SET expires_at=%s", (datetime.now(UTC) - timedelta(seconds=1),))
    assert signed_client.get("/api/v1/session").status_code == 401


def test_login_throttled_and_redacted(client: TestClient) -> None:
    for _ in range(10):
        response = client.post("/api/v1/session", json={"username": "local", "password": "wrong"})
        assert response.status_code == 401
        assert "wrong" not in response.text
    assert (
        client.post("/api/v1/session", json={"username": "different", "password": "x"}).status_code
        == 429
    )


def test_login_origin_and_cookie_flags(client: TestClient) -> None:
    data = {"username": "local", "password": TEST_PASSWORD}
    assert client.post("/api/v1/session", json=data, headers={"Origin": "null"}).status_code == 403
    response = client.post("/api/v1/session", json=data)
    assert response.status_code == 200
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]
    assert "Max-Age=28800" in response.headers["set-cookie"]
