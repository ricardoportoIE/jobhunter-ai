from fastapi.testclient import TestClient

from jobhunter_api.store import Row


def prepare(client: TestClient, questions: list[str] | None = None) -> tuple[Row, Row, Row]:
    evidence = client.post(
        "/api/v1/candidate/evidence",
        json={
            "source_type": "candidate_attestation",
            "source_ref": "Synthetic portfolio",
            "locator": "project",
            "content": "Developed a personal Python API with automated tests.",
            "review_confirmed": True,
        },
    ).json()
    fact = client.post(
        "/api/v1/candidate/facts",
        json={
            "claim": "Developed a personal Python API with automated tests.",
            "category": "project",
            "status": "verified",
            "evidence_ids": [evidence["id"]],
            "allowed_uses": ["cv", "cover_letter", "application_form"],
            "review_confirmed": True,
        },
    ).json()
    profile = client.get("/api/v1/candidate/profile").json()
    profile = client.patch(
        "/api/v1/candidate/profile",
        json={
            "expected_version": profile["version"],
            "display_name": "Alex Example",
        },
    ).json()
    profile = client.post(
        "/api/v1/candidate/profile/review", json={"expected_version": profile["version"]}
    ).json()
    job = client.post(
        "/api/v1/jobs/import",
        json={"raw_text": "Python developer at Example Labs. Python required."},
    ).json()
    job = client.patch(
        f"/api/v1/jobs/{job['id']}",
        json={
            "expected_version": job["version"],
            "title": "Python Developer",
            "company_name": "Example Labs",
            "requirements": [
                {
                    "text": "Python",
                    "category": "technical_skills",
                    "source_locator": "Python required",
                }
            ],
            "review_confirmed": True,
        },
    ).json()
    response = client.post(
        f"/api/v1/jobs/{job['id']}/strategy",
        json={
            "job_version": job["version"],
            "profile_version": profile["version"],
            "fact_ids": [fact["id"]],
            "use_ai": False,
            "questions": questions or [],
            "contact_lines": ["alex@example.test"],
        },
    )
    assert response.status_code == 201, response.text
    return job, fact, response.json()


def generate(client: TestClient, job: Row, fact: Row, strategy: Row) -> Row:
    path = f"/api/v1/jobs/{job['id']}/generate-package"
    assert (
        client.post(
            path, json={"strategy_id": strategy["id"], "strategy_version": strategy["version"]}
        ).status_code
        == 409
    )
    approved = client.post(
        f"/api/v1/strategies/{strategy['id']}/approve",
        json={
            "expected_version": strategy["version"],
            "cv_fact_ids": [fact["id"]],
            "letter_fact_ids": [fact["id"]],
            "review_confirmed": True,
        },
    )
    assert approved.status_code == 200, approved.text
    body = {"strategy_id": strategy["id"], "strategy_version": approved.json()["version"]}
    response = client.post(path, json=body)
    assert response.status_code == 201, response.text
    assert client.post(path, json=body).json()["id"] == response.json()["id"]
    return dict(response.json())


def test_generation_revision_sensitive_review_and_stale_sources(signed_client: TestClient) -> None:
    client = signed_client
    job, fact, strategy = prepare(client, ["Expected salary?"])
    package = generate(client, job, fact, strategy)
    path = f"/api/v1/packages/{package['id']}"
    assert package["content"]["cv"][0]["text"] == fact["claim"]
    assert package["content"]["answers"][0]["classification"] == "SENSITIVE"
    assert not package["validation"]["valid"]
    review = {
        "expected_version": package["version"],
        "decision": "approve",
        "review_confirmed": True,
    }
    assert client.post(path + "/review", json=review).status_code == 422
    edit = {
        "expected_version": package["version"],
        "cv_fact_ids": [fact["id"]],
        "letter_fact_ids": [fact["id"]],
        "review_confirmed": True,
        "manual_answers": {"0": "I would like to discuss the range for this role."},
    }
    assert client.patch(path, json=edit).status_code == 422
    revised = client.patch(path, json={**edit, "attest_answers": True}).json()
    assert revised["status"] == "NEEDS_REVIEW" and revised["version"] == 2
    assert "I would like" in client.get(path + "/diff?from_version=1").json()["diff"]
    review["expected_version"] = revised["version"]
    assert client.post(path + "/review", json=review).status_code == 422
    approved = client.post(path + "/review", json={**review, "sensitive_review_confirmed": True})
    assert approved.status_code == 200 and approved.json()["status"] == "APPROVED"
    assert len(client.get(path + "/history").json()) == 3
    assert client.patch(path, json={**edit, "attest_answers": True}).status_code == 409
    client.patch(
        f"/api/v1/jobs/{job['id']}", json={"expected_version": job["version"], "title": "Changed"}
    )
    assert client.get(path).json()["stale"]
    assert client.post(path + "/review", json={**review, "expected_version": 3}).status_code == 409


def test_ai_consent_and_document_usage_required(signed_client: TestClient) -> None:
    client = signed_client
    job, fact, strategy = prepare(client)
    body = {
        "job_version": job["version"],
        "profile_version": strategy["snapshot"]["profile"]["version"],
        "fact_ids": [fact["id"]],
        "use_ai": True,
    }
    assert client.post(f"/api/v1/jobs/{job['id']}/strategy", json=body).status_code == 422
    assert (
        client.post(
            f"/api/v1/strategies/{strategy['id']}/approve",
            json={
                "expected_version": 1,
                "cv_fact_ids": [job["id"]],
                "letter_fact_ids": [fact["id"]],
                "review_confirmed": True,
            },
        ).status_code
        == 422
    )
