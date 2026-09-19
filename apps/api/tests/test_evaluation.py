import importlib.util
from pathlib import Path
from typing import Any

from jobhunter_api.scoring import evaluate


def test_twenty_public_cases_and_no_expected_label_leakage() -> None:
    path = Path(__file__).resolve().parents[3] / "scripts/evaluate_phase1.py"
    spec = importlib.util.spec_from_file_location("evaluation", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = module.run()
    assert report["summary"]["cases_executed"] == 20
    assert report["summary"]["conservative_invariants_passed"] == 20
    assert report["summary"]["cases_with_review_differences"] > 0
    case: dict[str, Any] = {
        "case_id": "TEST",
        "title": "Junior",
        "description": "Python",
        "location": "Dublin",
        "seniority": "junior",
        "mentioned_skills": ["Python"],
        "expected": {"triage": "BLOCK"},
    }
    before = module.predict(case)
    case["expected"] = {"triage": "PURSUE_WITH_REVIEW", "score": 100}
    assert module.predict(case) == before
    assert (
        evaluate(
            {"requirements": [], "title": "Work alongside senior engineers", "seniority": "junior"},
            {"facts": [], "evidence": []},
            [],
            module.AT,
        )["recommendation"]
        == "REVIEW"
    )
