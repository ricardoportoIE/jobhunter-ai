"""Public-only parser benchmark. Default is offline; --live explicitly enables bounded API calls."""

import argparse
import json
import math
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from jobhunter_api.ai_budget import totals
from jobhunter_api.errors import Problem
from jobhunter_api.job_parser import PARSER_VERSION, get_provider, parse_vacancy
from jobhunter_api.settings import Settings
from jobhunter_api.store import connect

ROOT = Path(__file__).resolve().parents[1]
MODELS = ["gpt-4.1-mini-2025-04-14", "gpt-4.1-nano-2025-04-14"]


def source_text(case: dict[str, Any]) -> str:
    """No design labels, expected outcomes, split or seniority annotation enters inference."""
    return "\n".join(
        [
            case["title"],
            f"Employer: {case['employer_alias']}",
            f"Location: {case['location']}, {case['country']}",
            case["description"],
            "Mentioned technologies: " + ", ".join(case["mentioned_skills"]),
        ]
    )


def check_fields(case: dict[str, Any], result: dict[str, Any]) -> dict[str, bool]:
    fields = result["fields"]
    return {
        field: str(fields.get(field, "")).casefold() == str(case[label]).casefold()
        for field, label in (
            ("title", "title"),
            ("company_name", "employer_alias"),
            ("location", "location"),
            ("country", "country"),
        )
    }


def percentile(values: list[int], quantile: float) -> int | None:
    return sorted(values)[max(0, math.ceil(len(values) * quantile) - 1)] if values else None


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summaries = {}
    for model in MODELS:
        subset = [row for row in rows if row["model"] == model]
        valid = [row for row in subset if row["status"] == "succeeded"]
        latency = [row["latency_ms"] for row in subset if row.get("latency_ms") is not None]
        field_count = sum(len(row.get("field_checks", {})) for row in subset)
        field_correct = sum(sum(row.get("field_checks", {}).values()) for row in subset)
        summaries[model] = {
            "attempted": len(subset),
            "valid_outputs": len(valid),
            "valid_output_rate": len(valid) / len(subset) if subset else None,
            "field_accuracy_on_valid_outputs": field_correct / field_count if field_count else None,
            "refusals": sum(row.get("error_code") == "MODEL_REFUSAL" for row in subset),
            "invalid_outputs": sum(row["status"] == "invalid" for row in subset),
            "latency_p50_ms": percentile(latency, 0.5),
            "latency_p95_ms": percentile(latency, 0.95),
            "cost_eur": str(
                sum(
                    (Decimal(row.get("actual_eur") or "0") for row in subset),
                    Decimal(0),
                )
            ),
            "by_split": {
                split: {
                    "attempted": sum(r["split"] == split for r in subset),
                    "valid": sum(r["split"] == split for r in valid),
                }
                for split in {r["split"] for r in subset}
            },
            "human_review": "pending",
        }
    return summaries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--max-additional-eur", type=Decimal, default=Decimal("1.00"))
    parser.add_argument("--output", type=Path, default=ROOT / "data/evals/phase2-benchmark.json")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--attempt", type=int, choices=(1, 2), default=1)
    args = parser.parse_args()
    dataset = json.loads((ROOT / "data/evals/real-cases.json").read_text(encoding="utf-8"))
    cases = dataset["cases"]
    assert len(cases) == 20 and len({c["case_id"] for c in cases}) == 20
    if args.check:
        assert args.output.exists()
        report = json.loads(args.output.read_text(encoding="utf-8"))
        assert report["dataset_version"] == dataset["dataset_version"]
        assert report["prompt_version"] == PARSER_VERSION
        assert report["human_gold"] is False
        assert report["status"] in {
            "not_run_billing_required",
            "interrupted",
            "executed_pending_review",
        }
        print("Phase 2 public benchmark contract validated; no API calls.")
        return
    report: dict[str, Any] = {
        "dataset_version": dataset["dataset_version"],
        "prompt_version": PARSER_VERSION,
        "human_gold": False,
        "case_count": len(cases),
        "models": MODELS,
        "status": "not_run_billing_required",
        "results": [],
        "model_selection": None,
        "human_review": "pending",
        "gates": {
            "valid_output_rate": 0.95,
            "field_accuracy": 0.95,
            "quoted_spans_valid": 1.0,
            "human_entailment_review": "required",
        },
        "limitations": [
            "Public paraphrases, not complete original adverts.",
            "Labels are design annotations, not human gold.",
            "No candidate data; this benchmark cannot establish matching accuracy.",
            "Confidence scores are not calibrated probabilities.",
        ],
        "blocked_reason": "API returned HTTP 429 twice; user confirmed billing is not configured.",
    }
    if not args.live:
        if args.output.exists():
            print("Existing report preserved. Use --check to validate it.")
            return
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print("Offline benchmark plan recorded. No inference or quality measurements fabricated.")
        return
    if not args.max_additional_eur.is_finite() or not 0 < args.max_additional_eur <= 1:
        raise SystemExit("The benchmark allows at most EUR 1 of additional project budget.")
    settings = Settings().runtime()
    with connect(settings) as db:
        actor = db.execute("SELECT id FROM users WHERE username='local'").fetchone()
        if not actor:
            raise SystemExit("Bootstrap the local account first.")
        before = totals(db, settings)
    settings = settings.model_copy(
        update={
            "ai_monthly_eur": min(
                settings.ai_monthly_eur,
                Decimal(before["allocated_eur"]) + args.max_additional_eur,
            )
        }
    )
    report.update(
        status="executed_pending_review",
        blocked_reason=None,
        executed_at=datetime.now(UTC).isoformat(),
    )
    stop = False
    for model in MODELS:
        for case in cases:
            identity = uuid5(NAMESPACE_URL, "jobhunter-p2-public-" + case["case_id"])
            job = {
                "id": identity,
                "version": 1,
                "data": {"raw_text": source_text(case)},
            }
            item: dict[str, Any] = {
                "case_id": case["case_id"],
                "model": model,
                "split": case["split"],
            }
            key = (
                f"benchmark:{dataset['dataset_version']}:{PARSER_VERSION}:"
                f"{model}:{case['case_id']}:{args.attempt}"
            )
            try:
                response = parse_vacancy(
                    settings,
                    get_provider(settings),
                    actor["id"],
                    job,
                    key=key,
                    model=model,
                )
                item.update(
                    status="succeeded",
                    result=response["result"],
                    field_checks=check_fields(case, response["result"]),
                )
                with connect(settings) as db:
                    run = db.execute(
                        "SELECT actual_eur,latency_ms,input_tokens,output_tokens,error_code "
                        "FROM ai_calls WHERE id=%s",
                        (response["run_id"],),
                    ).fetchone()
                    if run:
                        item.update(
                            {k: str(v) if isinstance(v, Decimal) else v for k, v in run.items()}
                        )
            except Problem as exc:
                item.update(status="failed", error_code=exc.code)
                # Stop on provider, billing, stale prices, budget or unknown charges; no retry loop.
                if exc.code != "AI_INVALID_OUTPUT":
                    report.update(status="interrupted", blocked_reason=exc.code)
                    stop = True
                with connect(settings) as db:
                    run = db.execute(
                        "SELECT status,actual_eur,latency_ms,input_tokens,output_tokens,error_code "
                        "FROM ai_calls WHERE owner_id=%s AND operation='parse' AND request_key=%s",
                        (actor["id"], key),
                    ).fetchone()
                    if run:
                        item.update(
                            {k: str(v) if isinstance(v, Decimal) else v for k, v in run.items()}
                        )
            report["results"].append(item)
            report["metrics"] = summarize(report["results"])
            args.output.write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(case["case_id"], model, item["status"], flush=True)
            if stop:
                break
        if stop:
            break
    print("Benchmark recorded; model promotion requires human review of citations and errors.")


if __name__ == "__main__":
    main()
