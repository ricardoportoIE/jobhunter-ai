import json
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_profile import create_evidence

from jobhunter_api.ai_matching import grounded
from jobhunter_api.inference import Completion
from jobhunter_api.store import Row


def test_grounding_rejects_invention_and_project_to_experience() -> None:
    payload: Row = {
        "job_id": "job",
        "job_version": 1,
        "profile_version": 1,
        "requirements": [{"id": "r", "category": "seniority_experience"}],
        "facts": [
            {
                "id": "f",
                "claim": "Python study project",
                "category": "project",
                "evidence_ids": ["e"],
            }
        ],
        "evidence": [{"id": "e", "content": "Personal Python project"}],
    }
    result: Row = {
        "assessments": [
            {
                "requirement_id": "r",
                "status": "met",
                "confidence": 0.9,
                "reason": "Has Python",
                "citations": [
                    {
                        "fact_id": "f",
                        "evidence_id": "e",
                        "fact_quote": "Python study project",
                        "evidence_quote": "Personal Python project",
                    }
                ],
            }
        ],
        "limitations": [],
    }
    assert grounded(result, payload)["assessments"][0]["status"] == "unknown"
    result["assessments"][0]["citations"][0]["evidence_quote"] = "Commercial employment"
    with pytest.raises(ValueError):
        grounded(result, payload)
    result["assessments"][0].update(citations=[], status="met")
    with pytest.raises(ValueError):
        grounded(result, payload)


def test_selected_evidence_and_human_review_before_score(signed_client: TestClient) -> None:
    client = signed_client
    evidence = create_evidence(client)
    fact = client.post(
        "/api/v1/candidate/facts",
        json={
            "claim": "Synthetic Python project",
            "category": "project",
            "status": "verified",
            "evidence_ids": [evidence["id"]],
            "allowed_uses": ["matching"],
            "review_confirmed": True,
        },
    ).json()
    candidate = client.get("/api/v1/candidate/profile").json()
    candidate = client.post(
        "/api/v1/candidate/profile/review",
        json={
            "expected_version": candidate["version"],
        },
    ).json()
    job = client.post("/api/v1/jobs/import", json={"raw_text": "Python required"}).json()
    job = client.patch(
        f"/api/v1/jobs/{job['id']}",
        json={
            "expected_version": 1,
            "review_confirmed": True,
            "requirements": [
                {
                    "text": "Python",
                    "category": "technical_skills",
                    "source_locator": "Python required",
                }
            ],
        },
    ).json()
    url = f"/api/v1/ai/jobs/{job['id']}/suggest"
    body = {
        "job_version": job["version"],
        "profile_version": candidate["version"],
        "fact_ids": [fact["id"]],
        "external_processing_confirmed": True,
    }
    assert client.post(url, json={**body, "fact_ids": [str(uuid4())]}).status_code == 422
    assert (
        client.post(url, json={**body, "external_processing_confirmed": False}).status_code == 422
    )
    empty = client.post(url, json={**body, "fact_ids": []})
    assert empty.status_code == 200 and empty.json()["run_id"] is None
    requirement = job["requirements"][0]["id"]
    output = {
        "assessments": [
            {
                "requirement_id": requirement,
                "status": "met",
                "confidence": 0.9,
                "reason": "Projeto Python documentado",
                "citations": [
                    {
                        "fact_id": fact["id"],
                        "evidence_id": evidence["id"],
                        "fact_quote": fact["claim"],
                        "evidence_quote": evidence["content"],
                    }
                ],
            }
        ],
        "limitations": ["Não comprova experiência comercial."],
    }
    with patch("jobhunter_api.ai_matching.get_provider") as provider:
        provider.return_value.complete.return_value = Completion(
            json.dumps(output), 100, 100, "fixture", 2, "completed"
        )
        response = client.post(url, json=body)
        assert response.status_code == 200, response.text
        transmitted = json.loads(provider.return_value.complete.call_args.args[2])
        assert "display_name" not in transmitted and "source_ref" not in transmitted["evidence"][0]
        assert client.get(f"/api/v1/jobs/{job['id']}/matches").json() == []
    assessments = [
        {k: a[k] for k in ("requirement_id", "status", "reason", "fact_ids")}
        for a in response.json()["result"]["assessments"]
    ]
    match_body = {
        "job_version": job["version"],
        "profile_version": candidate["version"],
        "assessments": assessments,
        "ai_run_id": response.json()["run_id"],
    }
    assert client.post(f"/api/v1/jobs/{job['id']}/analyse", json=match_body).status_code == 422
    approved = client.post(
        f"/api/v1/jobs/{job['id']}/analyse",
        json={
            **match_body,
            "review_confirmed": True,
        },
    )
    assert approved.status_code == 201 and approved.json()["score"] == 100
    assert approved.json()["ai_run_id"] == response.json()["run_id"]
