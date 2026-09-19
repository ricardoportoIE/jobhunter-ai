from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from jobhunter_api.scoring import WEIGHTS, Document, evaluate, rounded

AT = datetime(2026, 9, 19, tzinfo=UTC)
SNAPSHOT: Document = {
    "facts": [
        {
            "id": "fact",
            "status": "verified",
            "allowed_uses": ["matching"],
            "reviewed_at": AT.isoformat(),
            "reviewed_by": "reviewer",
            "evidence_ids": ["evidence"],
            "evidence_versions": {"evidence": 1},
            "valid_from": None,
            "valid_until": None,
        }
    ],
    "evidence": [{"id": "evidence", "version": 1, "reviewed_at": AT.isoformat()}],
}


def requirement(identity: str, category: str = "technical_skills", **fields: object) -> Document:
    return {
        "id": identity,
        "text": identity,
        "category": category,
        "importance": "required",
        "is_eliminatory": False,
        **fields,
    }


def assessment(identity: str, status: str) -> Document:
    return {
        "requirement_id": identity,
        "status": status,
        "reason": "Explicit synthetic assessment",
        "fact_ids": ["fact"] if status in {"met", "partial"} else [],
    }


def test_no_data_is_not_zero() -> None:
    result = evaluate({"requirements": [requirement("a")]}, SNAPSHOT, [], AT)
    assert result["score"] is None and result["coverage"] == 0
    assert result["recommendation"] == "REVIEW"
    assert result["employment_gate"] == "REVIEW_BEFORE_START"


def test_adr_example_and_rounding() -> None:
    reqs = [requirement(str(i)) for i in range(5)] + [
        requirement("experience", "seniority_experience")
    ]
    decisions = [assessment(str(i), "met" if i < 4 else "unmet") for i in range(5)]
    decisions.append(assessment("experience", "partial"))
    result = evaluate({"requirements": reqs}, SNAPSHOT, decisions, AT)
    assert (result["score"], result["coverage"], result["recommendation"]) == (68, 0.5, "REVIEW")
    assert rounded(Decimal("0.125")) == 0.13


def test_required_weight_and_unknown_coverage() -> None:
    reqs = [
        requirement("required"),
        requirement("preferred", importance="preferred"),
        requirement("unknown"),
    ]
    result = evaluate(
        {"requirements": reqs},
        SNAPSHOT,
        [assessment("required", "met"), assessment("preferred", "unmet")],
        AT,
    )
    assert result["score"] == 66.67 and result["coverage"] == 0.18


def test_blocker_dominates_and_future_authorisation_is_separate() -> None:
    reqs = [requirement(c, c) for c in WEIGHTS]
    reqs[-2].update(is_eliminatory=True, future_authorisation=True)
    decisions = [assessment(c, "met") for c in WEIGHTS if c != "work_authorisation_hours"]
    result = evaluate({"requirements": reqs}, SNAPSHOT, decisions, AT)
    assert result["score"] == 100 and result["coverage"] == 0.95
    assert result["recommendation"] == "PRIORITISE"
    assert result["employment_gate"] == "REVIEW_BEFORE_START"
    decisions.append(assessment("work_authorisation_hours", "unmet"))
    result = evaluate({"requirements": reqs}, SNAPSHOT, decisions, AT)
    assert result["recommendation"] == "BLOCKED" and result["employment_gate"] == "BLOCKED"
    reqs[-2]["future_authorisation"] = False
    result = evaluate({"requirements": reqs}, SNAPSHOT, decisions[:-1], AT)
    assert result["recommendation"] == "REVIEW"


@pytest.mark.parametrize(
    "change",
    [
        {"status": "revoked"},
        {"allowed_uses": ["cv"]},
        {"valid_until": AT.isoformat()},
        {"valid_from": "2027-01-01T00:00:00Z"},
        {"evidence_versions": {"evidence": 2}},
    ],
)
def test_invalid_facts_cannot_support_positive_assessment(change: Document) -> None:
    snapshot = deepcopy(SNAPSHOT)
    snapshot["facts"][0].update(change)
    result = evaluate({"requirements": [requirement("a")]}, snapshot, [assessment("a", "met")], AT)
    assert result["score"] is None and "FACT_NOT_ELIGIBLE" in result["review_flags"]


def test_seniority_only_explicit_level_and_foreign_references() -> None:
    assert (
        evaluate({"requirements": [], "seniority": "staff"}, SNAPSHOT, [], AT)["recommendation"]
        == "BLOCKED"
    )
    assert (
        evaluate({"requirements": [], "seniority": "junior/senior"}, SNAPSHOT, [], AT)[
            "recommendation"
        ]
        == "REVIEW"
    )
    with pytest.raises(ValueError):
        evaluate(
            {"requirements": [requirement("a")]},
            SNAPSHOT,
            [{**assessment("a", "met"), "fact_ids": ["foreign"]}],
            AT,
        )
