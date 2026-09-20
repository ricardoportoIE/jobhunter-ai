import json
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from test_ai_budget import owner
from test_packages import prepare

from jobhunter_api.ai_budget import execute
from jobhunter_api.clarifications import Resolution, apply_gate, source_conflicts
from jobhunter_api.inference import Completion
from jobhunter_api.research import ResearchInput, validate_research
from jobhunter_api.settings import Settings
from jobhunter_api.store import Row


def test_scope_conflict_requires_review_but_incidental_senior_does_not() -> None:
    base = {"title": "Junior Software Engineer", "raw_text": "Work with senior engineers."}
    assert source_conflicts(base) == []
    assert source_conflicts({**base, "raw_text": "Senior position; no junior opening."})
    assert source_conflicts({**base, "raw_text": "Description: Graduate Data Engineer."})


def test_notes_cannot_clear_unknown_mandatory_requirements_or_explicit_blockers() -> None:
    issue = {
        "key": "a" * 64,
        "code": "DECISIVE_INFORMATION_MISSING",
        "requires_assessment_change": True,
    }
    note = Resolution(
        key=issue["key"],
        note="I would like to proceed anyway.",
        source_reference="A note without eligibility evidence",
    )
    result: Row = {"recommendation": "PRIORITISE", "review_flags": [], "score": 100}
    apply_gate(result, [issue], [note], uuid4())
    assert result["recommendation"] == "REVIEW" and result["score"] == 100
    assert result["clarifications"] == [issue]
    blocked: Row = {"recommendation": "BLOCKED", "review_flags": []}
    apply_gate(blocked, [issue], [], uuid4())
    assert blocked["recommendation"] == "BLOCKED"


def test_divergence_survives_selecting_favourable_run_and_manual_scoring(
    signed_client: TestClient,
    db_settings: Settings,
) -> None:
    client = signed_client
    job, _, strategy = prepare(client)
    profile_version = strategy["snapshot"]["profile"]["version"]
    req = job["requirements"][0]["id"]
    for operation, status in (("suggest", "met"), ("suggest_review", "unmet")):
        output = {
            "job_id": job["id"],
            "job_version": job["version"],
            "profile_version": profile_version,
            "comparison_key": "same-input",
            "assessments": [{"requirement_id": req, "status": status, "reason": status}],
            "clarifications": [],
        }

        def checked(_: Completion, output: Row = output) -> Row:
            return output

        execute(
            db_settings,
            owner(db_settings),
            operation,
            None,
            output,
            "gpt-5.6-luna",
            "v1",
            1000,
            500,
            lambda: Completion("{}", 1, 1, None, 1, "completed"),
            checked,
        )
    url = f"/api/v1/jobs/{job['id']}"
    issues = client.get(url + "/clarifications").json()
    assert len(issues) == 1 and issues[0]["code"] == "ASSESSMENT_DISAGREEMENT"
    assert {a["status"] for a in issues[0]["alternatives"]} == {"met", "unmet"}
    body = {
        "job_version": job["version"],
        "profile_version": profile_version,
        "review_confirmed": True,
        "assessments": [],
    }
    scored = client.post(url + "/analyse", json=body)
    assert scored.status_code == 201, scored.text
    assert scored.json()["recommendation"] == "REVIEW"
    assert scored.json()["clarifications"][0]["code"] == "ASSESSMENT_DISAGREEMENT"
    bad = client.post(
        url + "/analyse",
        json={
            **body,
            "clarification_resolutions": [
                {
                    "key": "b" * 64,
                    "note": "This is an outdated clarification.",
                    "source_reference": "original",
                }
            ],
        },
    )
    assert bad.status_code == 409


@pytest.mark.parametrize(
    "domain", ["127.0.0.1", "https://gov.ie/path", "a.local", "gov.ie@evil.org"]
)
def test_research_requires_public_domains(domain: str) -> None:
    with pytest.raises(ValueError):
        ResearchInput(expected_version=1, question="Public question?", allowed_domains=[domain])


def research_completion(url: str = "https://www.gov.ie/example") -> Completion:
    return Completion(
        json.dumps(
            {
                "answer": "Synthetic public answer [1]",
                "citations": [{"url": url, "title": "Source", "start": 24, "end": 27}],
                "web_search_calls": 1,
            }
        ),
        100,
        100,
        "test",
        2,
        "completed",
        web_search_calls=1,
    )


def test_research_rejects_foreign_or_fabricated_citations() -> None:
    payload = {"question": "Public question?", "allowed_domains": ["gov.ie"]}
    result = validate_research(research_completion(), payload)
    assert result["review_required"] and not result["candidate_facts_changed"]
    for url in ["https://gov.ie.evil.org/example", "file:///secret", "https://x:pass@gov.ie"]:
        with pytest.raises(ValueError):
            validate_research(research_completion(url), payload)


def test_research_consent_minimisation_history_and_no_profile_mutation(
    signed_client: TestClient,
    db_settings: Settings,
) -> None:
    client = signed_client
    job, _, _ = prepare(client)
    before = client.get("/api/v1/candidate/profile").json()
    body = {
        "expected_version": job["version"],
        "question": "Where are official permit rules?",
        "allowed_domains": ["gov.ie"],
    }
    url = f"/api/v1/jobs/{job['id']}/research"
    assert client.post(url, json=body).status_code == 422
    assert client.post(url, json={**body, "external_processing_confirmed": True}).status_code == 409
    settings = db_settings.model_copy(update={"openai_api_key": SecretStr("synthetic")})
    with (
        patch("jobhunter_api.research.settings_for", return_value=settings),
        patch("jobhunter_api.research.search", return_value=research_completion()) as search,
    ):
        response = client.post(url, json={**body, "external_processing_confirmed": True})
        assert response.status_code == 200, response.text
        payload = search.call_args.args[3]
        assert set(payload) == {"question", "allowed_domains", "as_of"}
        assert client.get("/api/v1/candidate/profile").json() == before
        assert len(client.get(url).json()) == 1
        assert search.call_count == 1
        cached = client.post(url, json={**body, "external_processing_confirmed": True})
        assert cached.json()["cached"] and search.call_count == 1
        expires = datetime.fromisoformat(response.json()["result"]["refresh_after"])
        assert datetime.now(UTC) < expires < datetime.now(UTC) + timedelta(hours=2)
