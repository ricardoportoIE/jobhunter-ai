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


def test_location_and_arrangement_filter_before_pagination(signed_client: TestClient) -> None:
    client = signed_client
    for index in range(24):
        imported = client.post("/api/v1/jobs/import", json={"raw_text": f"Filter fixture {index}"})
        assert imported.status_code == 201
        response = client.patch(
            f"/api/v1/jobs/{imported.json()['id']}",
            json={
                "expected_version": 1,
                "title": "Python Developer",
                "location": "Dublin" if index < 3 else "Cork",
                "work_mode": "remote" if index != 1 else "hybrid",
                "review_confirmed": True,
            },
        )
        assert response.status_code == 200
    unknown = client.post("/api/v1/jobs/import", json={"raw_text": "Unknown location and mode"})
    assert unknown.status_code == 201
    response = client.get("/api/v1/jobs?location=dUbLiN&work_mode=remote&q=Python&limit=1")
    assert response.status_code == 200
    page = response.json()
    assert page["total"] == 2 and len(page["items"]) == 1
    assert page["items"][0]["location"] == "Dublin"
    next_page = client.get(
        "/api/v1/jobs?location=dUbLiN&work_mode=remote&q=Python&limit=1&offset=1"
    ).json()
    assert next_page["total"] == 2
    assert page["items"][0]["id"] != next_page["items"][0]["id"]
    assert client.get("/api/v1/jobs?work_mode=hybrid").json()["total"] == 1
    assert client.get("/api/v1/jobs").json()["total"] == 25
    assert client.get("/api/v1/jobs?location=Unknown").json()["total"] == 0


def test_filter_values_are_validated_and_wildcards_are_literal(signed_client: TestClient) -> None:
    client = signed_client
    job = client.post("/api/v1/jobs/import", json={"raw_text": "Literal filters"}).json()
    assert (
        client.patch(
            f"/api/v1/jobs/{job['id']}",
            json={"expected_version": 1, "title": "100% Python", "location": "A_B"},
        ).status_code
        == 200
    )
    assert client.get("/api/v1/jobs?q=%25").json()["total"] == 1
    assert client.get("/api/v1/jobs?location=A_B").json()["total"] == 1
    assert client.get("/api/v1/jobs?location=%25").json()["total"] == 0
    assert client.get("/api/v1/jobs?q=' OR 1=1 --").json()["total"] == 0
    assert client.get("/api/v1/jobs?location=" + "x" * 201).status_code == 422
    assert client.get("/api/v1/jobs?work_mode=unknown").status_code == 422
