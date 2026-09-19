from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient


def test_manual_tracker_transition_guards_and_replay(signed_client: TestClient) -> None:
    client = signed_client
    job = client.post("/api/v1/jobs/import", json={"raw_text": "Fictional job"}).json()
    app = client.post("/api/v1/applications", json={"job_id": job["id"]}).json()
    duplicate = client.post("/api/v1/applications", json={"job_id": job["id"]})
    assert duplicate.status_code == 200 and duplicate.json()["id"] == app["id"]
    url = f"/api/v1/applications/{app['id']}/events"
    assert client.post(url, json={"expected_version": 1, "to_status": "OFFERED"}).status_code == 409
    manual = {"expected_version": 1, "to_status": "SUBMITTED"}
    assert client.post(url, json=manual).status_code == 422
    manual.update(
        manual_confirmation=True,
        channel="Employer portal",
        receipt_ref="synthetic receipt",
        submitted_at=datetime.now(UTC).isoformat(),
    )
    assert (
        client.post(
            url,
            json={**manual, "submitted_at": (datetime.now(UTC) + timedelta(days=1)).isoformat()},
        ).status_code
        == 422
    )
    response = client.post(url, json=manual)
    assert response.status_code == 200, response.text
    submitted = response.json()
    assert submitted["submission"]["origin"] == "manual_record"
    assert client.post(url, json=manual).json() == submitted
    assert len(client.get(f"/api/v1/applications/{app['id']}").json()["events"]) == 2
    terminal = client.post(url, json={"expected_version": 2, "to_status": "REJECTED"}).json()
    assert terminal["status"] == "REJECTED"
    assert (
        client.post(url, json={"expected_version": 3, "to_status": "INTERVIEWING"}).status_code
        == 409
    )
    assert client.get(f"/api/v1/applications/{uuid4()}").status_code == 404


def test_event_idempotency_payload_conflict(signed_client: TestClient) -> None:
    client = signed_client
    job = client.post("/api/v1/jobs/import", json={"raw_text": "Another fictional job"}).json()
    app = client.post("/api/v1/applications", json={"job_id": job["id"]}).json()
    url = f"/api/v1/applications/{app['id']}/events"
    headers = {"Idempotency-Key": "event-key"}
    assert (
        client.post(
            url, headers=headers, json={"expected_version": 1, "to_status": "RESEARCHED"}
        ).status_code
        == 200
    )
    assert (
        client.post(
            url, headers=headers, json={"expected_version": 2, "to_status": "EXPIRED"}
        ).status_code
        == 409
    )
