from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from jobhunter_api.deduplication import canonical_url


def test_canonical_url_preserves_job_identity() -> None:
    assert (
        canonical_url("https://EXAMPLE.test:443/job?id=12&utm_source=x#apply")
        == "https://example.test/job?id=12"
    )
    assert canonical_url("https://example.test/job?id=13") != canonical_url(
        "https://example.test/job?id=12"
    )


def test_retry_conflict_and_false_merge(signed_client: TestClient) -> None:
    client = signed_client
    data = {"raw_text": "Graduate role", "location_hint": "Dublin", "source_name": "board"}
    a = client.post("/api/v1/jobs/import", json=data, headers={"Idempotency-Key": "retry"})
    b = client.post("/api/v1/jobs/import", json=data, headers={"Idempotency-Key": "retry"})
    assert a.status_code == 201 and b.status_code == 200 and a.json() == b.json()
    assert (
        client.post(
            "/api/v1/jobs/import",
            json={**data, "raw_text": "Different"},
            headers={"Idempotency-Key": "retry"},
        ).status_code
        == 409
    )
    c = client.post("/api/v1/jobs/import", json={**data, "location_hint": "London"})
    assert c.status_code == 201 and c.json()["id"] != a.json()["id"]
    d = client.post("/api/v1/jobs/import", json={**data, "raw_text": " GRADUATE   role "})
    assert d.status_code == 200 and d.json()["id"] == a.json()["id"]


def test_source_identity_and_concurrent_import(signed_client: TestClient) -> None:
    client = signed_client
    data = {"raw_text": "First version", "external_id": "123", "source_name": "board"}
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(
            pool.map(lambda _: client.post("/api/v1/jobs/import", json=data), range(4))
        )
    assert sorted(r.status_code for r in responses) == [200, 200, 200, 201]
    assert len({r.json()["id"] for r in responses}) == 1
    changed = client.post("/api/v1/jobs/import", json={**data, "raw_text": "Changed version"})
    assert changed.status_code == 200
    assert changed.json()["raw_text"] == "First version"  # never silently overwrite reviewed data
    different = client.post("/api/v1/jobs/import", json={**data, "source_name": "other-board"})
    assert different.status_code == 201
