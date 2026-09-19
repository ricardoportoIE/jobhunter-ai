from uuid import uuid4

from fastapi.testclient import TestClient

from jobhunter_api.settings import Settings
from jobhunter_api.store import connect


def create_evidence(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/candidate/evidence",
        json={
            "source_type": "candidate_attestation",
            "source_ref": "synthetic:demo",
            "locator": "exercise",
            "content": "Fictional Python project",
            "review_confirmed": True,
        },
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


def test_fact_review_snapshot_and_invalidation(
    signed_client: TestClient, db_settings: Settings
) -> None:
    client = signed_client
    data: dict[str, object] = {
        "claim": "Python fictional project",
        "category": "skill",
        "status": "verified",
        "allowed_uses": ["matching"],
    }
    assert client.post("/api/v1/candidate/facts", json=data).status_code == 422
    evidence = create_evidence(client)
    data.update(evidence_ids=[evidence["id"]], review_confirmed=True)
    response = client.post("/api/v1/candidate/facts", json=data)
    assert response.status_code == 201, response.text
    fact = response.json()
    profile = client.get("/api/v1/candidate/profile").json()
    response = client.post(
        "/api/v1/candidate/profile/review", json={"expected_version": profile["version"]}
    )
    assert response.status_code == 200
    published = response.json()
    assert published["status"] == "reviewed"
    with connect(db_settings) as db:
        snapshot = db.execute(
            "SELECT data FROM snapshots WHERE version=%s", (published["version"],)
        ).fetchone()
        assert snapshot and snapshot["data"]["facts"][0]["status"] == "verified"
    data.update(status="revoked", expected_version=fact["version"], review_confirmed=False)
    assert client.patch(f"/api/v1/candidate/facts/{fact['id']}", json=data).status_code == 200
    changed = client.get("/api/v1/candidate/profile").json()
    assert changed["status"] == "draft" and changed["version"] > published["version"]
    assert client.patch(f"/api/v1/candidate/facts/{fact['id']}", json=data).status_code == 409


def test_owned_references_and_deletion(signed_client: TestClient, db_settings: Settings) -> None:
    client = signed_client
    item = create_evidence(client)
    assert client.get(f"/api/v1/candidate/evidence/{uuid4()}").status_code == 404
    # An authenticated session for a different actor cannot read or mutate this record.
    with connect(db_settings) as db:
        db.execute("ALTER TABLE users DROP CONSTRAINT users_single_user_key")
        other = uuid4()
        db.execute(
            "INSERT INTO users(id,username,password_hash) VALUES (%s,'other','unused')", (other,)
        )
        db.execute("UPDATE records SET owner_id=%s WHERE id=%s", (other, item["id"]))
    try:
        assert client.get(f"/api/v1/candidate/evidence/{item['id']}").status_code == 404
        assert (
            client.delete(f"/api/v1/candidate/evidence/{item['id']}?expected_version=1").status_code
            == 404
        )
    finally:
        with connect(db_settings) as db:
            db.execute("DELETE FROM users WHERE id=%s", (other,))
            db.execute("ALTER TABLE users ADD CONSTRAINT users_single_user_key UNIQUE(single_user)")


def test_dates_and_profile_optimistic_lock(signed_client: TestClient) -> None:
    client = signed_client
    assert (
        client.post(
            "/api/v1/candidate/facts",
            json={
                "claim": "x",
                "category": "skill",
                "valid_from": "2026-09-01T00:00:00Z",
                "valid_until": "2026-08-01T00:00:00Z",
            },
        ).status_code
        == 422
    )
    current = client.get("/api/v1/candidate/profile").json()
    update = {"expected_version": current["version"], "display_name": "Synthetic Candidate"}
    assert client.patch("/api/v1/candidate/profile", json=update).status_code == 200
    assert client.patch("/api/v1/candidate/profile", json=update).status_code == 409
