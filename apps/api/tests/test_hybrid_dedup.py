from fastapi.testclient import TestClient


def test_similar_adverts_are_not_merged_and_require_versioned_review(
    signed_client: TestClient,
) -> None:
    client = signed_client
    first = client.post(
        "/api/v1/jobs/import",
        json={
            "raw_text": (
                "Junior Python engineer using SQL APIs Docker and Linux Dublin hybrid team."
            ),
            "location_hint": "Dublin",
        },
    ).json()
    second = client.post(
        "/api/v1/jobs/import",
        json={
            "raw_text": (
                "Junior Python engineer using SQL APIs Docker and Linux Dublin hybrid team today."
            ),
            "location_hint": "Cork",
        },
    ).json()
    url = f"/api/v1/ai/jobs/{first['id']}/duplicates"
    candidates = client.get(url).json()
    assert len(candidates["items"]) == 1 and not candidates["automatic_merge"]
    assert candidates["items"][0]["conflicts"] == ["LOCALIDADES_DIFERENTES"]
    body = {
        "expected_version": 1,
        "target_id": second["id"],
        "target_version": 1,
        "decision": "duplicate",
        "reason": "Reviewed",
        "review_confirmed": True,
    }
    assert client.post(url, json=body).status_code == 409
    body["decision"] = "distinct"
    assert client.post(url, json=body).status_code == 200
    assert client.get(url).json()["items"] == []
    assert client.get("/api/v1/jobs").json()["total"] == 2


def test_confirmed_duplicate_preserves_both_records(signed_client: TestClient) -> None:
    client = signed_client
    jobs = [
        client.post(
            "/api/v1/jobs/import",
            json={
                "raw_text": "Python APIs SQL junior hybrid Dublin " + suffix,
            },
        ).json()
        for suffix in ("role", "opportunity")
    ]
    url = f"/api/v1/ai/jobs/{jobs[0]['id']}/duplicates"
    body = {
        "expected_version": 1,
        "target_id": jobs[1]["id"],
        "target_version": 1,
        "decision": "duplicate",
        "reason": "Same advertised position",
        "review_confirmed": True,
    }
    first, replay = client.post(url, json=body), client.post(url, json=body)
    assert first.status_code == replay.status_code == 200
    assert first.json()["id"] == replay.json()["id"]
    assert client.get("/api/v1/jobs").json()["total"] == 1
    assert client.get("/api/v1/jobs?archived=true").json()["total"] == 1
