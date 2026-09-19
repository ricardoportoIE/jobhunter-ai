"""Execute a conservative public baseline; expectations are read only after prediction."""

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from jobhunter_api.deduplication import identity_keys
from jobhunter_api.scoring import ALGORITHM, evaluate

ROOT = Path(__file__).resolve().parents[1]
AT = datetime(2026, 9, 19, tzinfo=UTC)
TRIAGE_MAP = {
    "BLOCK": "BLOCKED",
    "REVIEW": "REVIEW",
    "PURSUE_WITH_REVIEW": "APPLY_AFTER_REVIEW",
    "DEPRIORITISE": "TRACK_OR_ARCHIVE",
    "SECONDARY": "TRACK_OR_ARCHIVE",
}


def predict(case: dict[str, Any]) -> dict[str, Any]:
    # Only already structured public input fields are used. No expected labels,
    # personal CV, private provenance or invented positive assessments enter the engine.
    job = {
        "title": case["title"],
        "seniority": case["seniority"],
        "sponsorship": None,
        "requirements": [
            {
                "id": str(uuid5(NAMESPACE_URL, case["case_id"] + "/" + skill)),
                "text": skill,
                "category": "technical_skills",
                "importance": "required",
                "is_eliminatory": False,
                "source_locator": "public mentioned_skills",
            }
            for skill in case["mentioned_skills"]
        ],
    }
    result = evaluate(job, {"facts": [], "evidence": []}, [], AT)
    identities = identity_keys({"raw_text": case["description"], "location_hint": case["location"]})
    return {
        "recommendation": result["recommendation"],
        "score": result["score"],
        "coverage": result["coverage"],
        "hard_block": bool(result["blockers"]),
        "employment_gate": result["employment_gate"],
        "flags": result["review_flags"],
        "identity_keys": identities,
    }


def run() -> dict[str, Any]:
    path = ROOT / "data/evals/real-cases.json"
    dataset = json.loads(path.read_text(encoding="utf-8"))
    predictions = {case["case_id"]: predict(case) for case in dataset["cases"]}
    results = []
    for case in dataset["cases"]:
        identity, expected = case["case_id"], case["expected"]
        actual = predictions[identity]
        duplicates = [
            key
            for key, other in predictions.items()
            if key != identity and set(actual["identity_keys"]) & set(other["identity_keys"])
        ]
        differences = []
        if actual["recommendation"] != TRIAGE_MAP[expected["triage"]]:
            differences.append("triage_taxonomy_or_missing_reviewed_profile")
        missing_flags = sorted(set(expected["flags"]) - set(actual["flags"]))
        if missing_flags:
            differences.append("semantic_flags_require_manual_review")
        if expected["duplicate_of"] and expected["duplicate_of"] not in duplicates:
            differences.append("duplicate_not_proven_by_public_paraphrase_identity")
        critical = (
            actual["hard_block"] == expected["hard_block"]
            and actual["score"] is None
            and actual["employment_gate"] == "REVIEW_BEFORE_START"
        )
        results.append(
            {
                "case_id": identity,
                "split": case["split"],
                "expected_triage": expected["triage"],
                "actual": actual,
                "detected_duplicates": duplicates,
                "expected_duplicate": expected["duplicate_of"],
                "missing_expected_flags": missing_flags,
                "differences": differences,
                "conservative_invariants_passed": critical,
                "human_review": {"status": "pending", "decision": None},
            }
        )
    return {
        "dataset_version": dataset["dataset_version"],
        "dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "algorithm_version": ALGORITHM,
        "evaluation_at": AT.isoformat(),
        "scope": "Public conservative baseline without candidate profile or semantic parser; "
        "not a fit benchmark.",
        "human_gold": False,
        "triage_mapping_for_comparison": TRIAGE_MAP,
        "summary": {
            "cases_executed": len(results),
            "conservative_invariants_passed": sum(
                r["conservative_invariants_passed"] for r in results
            ),
            "mapped_recommendation_agreement": sum(
                not any(d.startswith("triage_") for d in r["differences"]) for r in results
            ),
            "cases_with_review_differences": sum(bool(r["differences"]) for r in results),
            "by_split": dict(Counter(r["split"] for r in results)),
        },
        "cases": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Verify the committed reproducible report"
    )
    args = parser.parse_args()
    report = run()
    destination = ROOT / "data/evals/phase1-results.json"
    if args.check:
        assert json.loads(destination.read_text(encoding="utf-8")) == report
    else:
        destination.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    assert report["summary"]["conservative_invariants_passed"] == 20
    print(json.dumps(report["summary"]))


if __name__ == "__main__":
    main()
