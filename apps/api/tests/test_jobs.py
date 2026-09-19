import hashlib

from fastapi.testclient import TestClient


def test_import_review_unknowns_and_xss(signed_client: TestClient) -> None:
    client = signed_client
    raw = '  <script>alert("xss")</script>\nPython required.  '
    response = client.post(
        "/api/v1/jobs/import",
        json={"raw_text": raw, "source_url": "http://169.254.169.254/latest/meta-data/"},
    )
    assert response.status_code == 201
    job = response.json()
    assert job["raw_text"] == raw
    assert job["content_sha256"] == hashlib.sha256(raw.encode()).hexdigest()
    assert job["salary"] is None and job["sponsorship"] is None
    assert job["status"] == "DISCOVERED"
    changed = client.patch(
        f"/api/v1/jobs/{job['id']}",
        json={
            "expected_version": 1,
            "title": '<img src=x onerror="alert(1)">',
            "requirements": [
                {"text": "Python", "category": "technical_skills", "source_locator": "line 2"}
            ],
        },
    ).json()
    assert changed["status"] == "DISCOVERED"
    response = client.patch(
        f"/api/v1/jobs/{job['id']}",
        json={
            "expected_version": changed["version"],
            "title": "Junior developer",
            "review_confirmed": True,
        },
    )
    assert response.status_code == 200 and response.json()["status"] == "PARSED"
    assert client.get("/api/v1/jobs?q=Junior&status=PARSED").json()["total"] == 1
    assert client.get("/api/v1/jobs?status=DISCOVERED").json()["total"] == 0


def test_import_limits_and_auth(client: TestClient, signed_client: TestClient) -> None:
    response = signed_client.post("/api/v1/jobs/import", json={"raw_text": "x" * 50001})
    assert response.status_code == 422
    response = signed_client.post("/api/v1/jobs/import", content=b"x" * 140000)
    assert response.status_code == 413
    assert (
        signed_client.post(
            "/api/v1/jobs/import", json={"raw_text": "x", "source_url": "javascript:alert(1)"}
        ).status_code
        == 422
    )
    client.cookies.clear()
    assert client.get("/api/v1/jobs").status_code == 401
