"""Frozen cases, unmodified raw responses and user decisions remain independently auditable."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("migration", ROOT / "scripts/evaluate_migration.py")
assert SPEC and SPEC.loader
migration = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(migration)


def test_migration_report_and_explicit_user_labels() -> None:
    report = json.loads(migration.REPORT.read_text(encoding="utf-8"))
    cases = json.loads(migration.DATA.read_text(encoding="utf-8"))["cases"]
    migration.check_report(report, cases)
    for case in cases:
        assert "expected_statuses" not in case["payload"]
        assert "clarification_required" not in case["payload"]


def test_guardrail_cannot_hide_raw_positive_error() -> None:
    case = {
        "payload": {"requirements": [{"id": "r"}], "job_title": "Junior", "vacancy_text": ""},
        "expected_statuses": ["unknown"],
        "clarification_required": False,
    }
    checked = migration.checks(
        case,
        {"assessments": [{"requirement_id": "r", "status": "unknown"}]},
        {"assessments": [{"requirement_id": "r", "status": "met"}]},
    )
    assert checked["raw_unsupported_positive"] and checked["guardrail_changed"]
    assert not checked["unsupported_positive"]
