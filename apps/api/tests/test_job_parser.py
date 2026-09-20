import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from jobhunter_api.inference import Completion
from jobhunter_api.job_parser import ParsedJob, validate_extraction
from jobhunter_api.store import Row

RAW = "Junior Python Developer in Dublin. Python is required. Hybrid."


def parsed() -> Row:
    data: Row = {
        name: {"value": None, "quote": None, "confidence": 0}
        for name in ParsedJob.model_fields
        if name not in {"requirements", "risk_flags"}
    }
    data.update(
        {
            "title": {
                "value": "Junior Python Developer",
                "quote": "Junior Python Developer",
                "confidence": 0.95,
            },
            "location": {"value": "Dublin", "quote": "Dublin", "confidence": 0.95},
            "requirements": [
                {
                    "text": "Python",
                    "category": "technical_skills",
                    "importance": "required",
                    "is_eliminatory": False,
                    "future_authorisation": False,
                    "quote": "Python is required.",
                    "confidence": 0.95,
                }
            ],
            "risk_flags": [],
        }
    )
    return data


def test_quotes_unknowns_and_domain_validation() -> None:
    data = parsed()
    result = validate_extraction(ParsedJob.model_validate(data).model_dump(), RAW)
    assert result["fields"]["salary"] is None and result["fields"]["sponsorship"] is None
    assert result["citations"]["location"]["quote"] == "Dublin"
    data["title"]["quote"] = "Invented title"
    with pytest.raises(ValueError):
        validate_extraction(data, RAW)
    data = parsed()
    data["country"] = {"value": "INVALID", "quote": "Dublin", "confidence": 0.9}
    with pytest.raises(ValueError):
        validate_extraction(data, RAW)


def test_unknown_annotations_become_notes_without_inventing_values() -> None:
    raw = RAW + " Salary described without numeric amount."
    data = parsed()
    data["salary"] = {
        "value": {"minimum": None, "maximum": None, "currency": None, "period": None},
        "quote": "Salary described without numeric amount.",
        "confidence": 1,
    }
    result = validate_extraction(data, raw)
    assert result["fields"]["salary"] is None
    assert "salary" not in result["citations"]
    assert "Salary described without numeric amount." in result["risk_flags"][0]
    data["salary"]["quote"] = "Competitive invented salary"
    with pytest.raises(ValueError):
        validate_extraction(data, raw)
    data["salary"] = {"value": None, "quote": None, "confidence": 0.8}
    with pytest.raises(ValueError):
        validate_extraction(data, raw)
    data["salary"] = {"value": None, "quote": None, "confidence": 0}
    data["sponsorship"] = {"value": "available", "quote": None, "confidence": 0}
    with pytest.raises(ValueError):
        validate_extraction(data, raw)


def test_parser_is_idempotent_and_never_publishes(signed_client: TestClient) -> None:
    client = signed_client
    job = client.post("/api/v1/jobs/import", json={"raw_text": RAW}).json()
    with patch("jobhunter_api.job_parser.get_provider") as provider:
        provider.return_value.complete.return_value = Completion(
            json.dumps(parsed()), 100, 100, "test", 10, "completed"
        )
        response = client.post(
            f"/api/v1/ai/jobs/{job['id']}/parse", json={"expected_version": job["version"]}
        )
        assert response.status_code == 200, response.text
        replay = client.post(
            f"/api/v1/ai/jobs/{job['id']}/parse", json={"expected_version": job["version"]}
        )
        assert replay.json()["cached"]
        assert provider.return_value.complete.call_count == 1
    current = client.get(f"/api/v1/jobs/{job['id']}").json()
    assert current["status"] == "DISCOVERED" and current["title"] is None
    latest = client.get(f"/api/v1/ai/jobs/{job['id']}/extraction").json()
    assert latest["run_id"] == response.json()["run_id"] and not latest["stale"]
    history = client.get("/api/v1/ai/runs").json()
    assert len(history) == 1 and "raw_text" not in history[0]
    payload = {"expected_version": job["version"], "run_id": latest["run_id"]}
    draft = client.post(f"/api/v1/ai/jobs/{job['id']}/draft", json=payload)
    assert draft.status_code == 200, draft.text
    assert draft.json()["title"] == "Junior Python Developer"
    assert draft.json()["status"] == "DISCOVERED"
    assert draft.json()["reviewed_by"] is None
    repeated = client.post(f"/api/v1/ai/jobs/{job['id']}/draft", json=payload)
    assert repeated.json()["version"] == draft.json()["version"]
    client.patch(
        f"/api/v1/jobs/{job['id']}",
        json={
            "expected_version": draft.json()["version"],
            "title": "Human correction",
            "review_confirmed": True,
        },
    )
    assert client.post(f"/api/v1/ai/jobs/{job['id']}/draft", json=payload).status_code == 409
