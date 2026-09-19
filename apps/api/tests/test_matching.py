from datetime import datetime

from fastapi.testclient import TestClient
from test_profile import create_evidence

from jobhunter_api.scoring import evaluate


def test_reproducible_snapshot_and_invalidation(signed_client: TestClient) -> None:
    client = signed_client
    evidence = create_evidence(client)
    fact = client.post(
        "/api/v1/candidate/facts",
        json={
            "claim": "Synthetic Python project",
            "category": "skill",
            "status": "verified",
            "evidence_ids": [evidence["id"]],
            "allowed_uses": ["matching"],
            "review_confirmed": True,
        },
    ).json()
    profile = client.get("/api/v1/candidate/profile").json()
    job = client.post("/api/v1/jobs/import", json={"raw_text": "Python required"}).json()
    body = {
        "job_version": job["version"],
        "profile_version": profile["version"],
        "review_confirmed": True,
    }
    assert client.post(f"/api/v1/jobs/{job['id']}/analyse", json=body).status_code == 409
    profile = client.post(
        "/api/v1/candidate/profile/review", json={"expected_version": profile["version"]}
    ).json()
    job = client.patch(
        f"/api/v1/jobs/{job['id']}",
        json={
            "expected_version": job["version"],
            "review_confirmed": True,
            "title": "Junior developer",
            "requirements": [
                {"text": "Python", "category": "technical_skills", "source_locator": "line 1"}
            ],
        },
    ).json()
    body.update(
        job_version=job["version"],
        profile_version=profile["version"],
        assessments=[
            {
                "requirement_id": job["requirements"][0]["id"],
                "status": "met",
                "reason": "Reviewed project",
                "fact_ids": [fact["id"]],
            }
        ],
    )
    response = client.post(f"/api/v1/jobs/{job['id']}/analyse", json=body)
    assert response.status_code == 201, response.text
    match = response.json()
    assert match["score"] == 100 and match["coverage"] == 0.3 and not match["stale"]
    reproduced = evaluate(
        match["job_snapshot"],
        match["profile_snapshot"],
        match["input_assessments"],
        datetime.fromisoformat(match["created_at"]),
    )
    assert reproduced["breakdown"] == match["breakdown"]
    assert (
        client.delete(f"/api/v1/candidate/evidence/{evidence['id']}?expected_version=1").status_code
        == 204
    )
    assert client.get(f"/api/v1/matches/{match['id']}").json()["stale"]
    assert client.post(f"/api/v1/jobs/{job['id']}/analyse", json=body).status_code == 409
