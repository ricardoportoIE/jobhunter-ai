"""Evaluation integrity: labels stay private and unsupported claims cannot pass validation."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "reasoning_comparison", ROOT / "scripts/compare_reasoning_models.py"
)
assert SPEC and SPEC.loader
comparison = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(comparison)


def test_labels_and_rationale_are_not_sent_to_models() -> None:
    dataset = json.loads((ROOT / "data/evals/reasoning-cases.json").read_text(encoding="utf-8"))
    assert len(dataset["cases"]) == 32
    for case in dataset["cases"]:
        payload, _, _ = comparison.task_input(case)
        assert "expected" not in payload and "rationale" not in payload
        assert case["rationale"] not in json.dumps(payload)
        assert case["id"] not in json.dumps(payload)


def test_triage_rejects_invented_evidence_quote() -> None:
    case = {"task": "triage_probe"}
    payload = {"vacancy": "Projects accepted.", "candidate": "Completed a Python project."}
    output = {
        "decision": "VIABLE_AFTER_REVIEW",
        "employment_gate": "REVIEW_BEFORE_START",
        "vacancy_quote": "Projects accepted.",
        "candidate_quote": "Five years of paid Python employment.",
    }
    with pytest.raises(ValueError, match="Non-verbatim"):
        comparison.validate_result(case, payload, output)


def test_guardrail_does_not_conceal_raw_model_error() -> None:
    case = {"task": "matching", "expected": {"status": "unknown"}}
    raw = {"assessments": [{"status": "met"}]}
    validated = {"assessments": [{"status": "unknown"}]}
    result = comparison.grading(case, raw, validated)
    assert result["raw_correct"] is False
    assert result["validated_correct"] is True
    assert result["false_positive"] is True
    assert result["guardrail_changed"] is True


def test_unavailable_outputs_stay_in_denominator() -> None:
    rows = [
        {
            "model": comparison.MODELS[0],
            "task": "matching",
            "case_id": "case",
            "status": "failed",
            "actual_eur": "0",
        }
    ]
    summary = comparison.summarize(rows)[comparison.MODELS[0]]
    assert summary["attempted"] == 1 and summary["completed"] == 0
    assert summary["matching"]["attempted"] == 1
    assert summary["matching"]["raw_correct"] == 0
