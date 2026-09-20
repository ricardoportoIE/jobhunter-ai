"""Opt-in paid holdout and complete HTTP workflow. Synthetic candidates; shared real cost ledger."""

import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4
from zipfile import ZipFile

import psycopg
from argon2 import PasswordHasher
from docx import Document
from fastapi.testclient import TestClient
from psycopg import sql
from pydantic import BaseModel, SecretStr
from pypdf import PdfReader

from jobhunter_api.ai_budget import execute, totals
from jobhunter_api.ai_matching import RELIABLE_PROMPT, RELIABLE_VERSION, ReliableMatch, reliable
from jobhunter_api.clarifications import source_conflicts
from jobhunter_api.errors import Problem
from jobhunter_api.inference import (
    CONTRACT_VERSION,
    Completion,
    OpenAIInference,
    constrained_schema,
)
from jobhunter_api.jobs import JobEdit
from jobhunter_api.main import create_app
from jobhunter_api.manage import migrate, provision
from jobhunter_api.research import RESEARCH_VERSION, search, validate_research
from jobhunter_api.settings import Effort, Settings
from jobhunter_api.store import Row, connect

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/evals/migration-holdout.json"
REPORT = ROOT / "data/evals/migration-live.json"
MODELS = ("gpt-4.1-mini-2025-04-14", "gpt-5.6-luna")


def digest() -> str:
    return hashlib.sha256(DATA.read_text(encoding="utf-8").encode()).hexdigest()


class MeteredProvider:
    """Even disposable DB workflows reserve actual costs in the primary application ledger."""

    def __init__(self, settings: Settings, owner: UUID, tag: str):
        self.settings, self.owner, self.tag = settings, owner, tag
        self.calls: list[str] = []
        self.last: Completion | None = None

    def complete(
        self,
        model: str,
        prompt: str,
        data: str,
        schema: type[BaseModel],
        max_output: int,
        *,
        effort: Effort | None = None,
    ) -> Completion:
        provider = OpenAIInference(self.settings)
        contract = constrained_schema(schema, json.loads(data))
        bound = len((prompt + data + json.dumps(contract)).encode()) + 2048
        try:
            response = execute(
                self.settings,
                self.owner,
                "migration_" + schema.__name__,
                None,
                {
                    "tag": self.tag,
                    "data": data,
                    "prompt": prompt,
                    "schema": contract,
                },
                model,
                "migration-1/" + RELIABLE_VERSION,
                bound,
                max_output,
                lambda: provider.complete(model, prompt, data, schema, max_output, effort=effort),
                lambda completion: asdict(completion),
                execution_config={"effort": effort, "contract_version": CONTRACT_VERSION},
            )
        finally:
            provider.client.close()
        self.calls.append(response["run_id"])
        self.last = Completion(**response["result"])
        return self.last


def checks(case: Row, result: Row, raw: Row | None = None) -> Row:
    actual = {a["requirement_id"]: a["status"] for a in result["assessments"]}
    statuses = [actual[r["id"]] for r in case["payload"]["requirements"]]
    raw_by_id = {a["requirement_id"]: a["status"] for a in (raw or result)["assessments"]}
    raw_statuses = [raw_by_id[r["id"]] for r in case["payload"]["requirements"]]
    deterministic = source_conflicts(
        {"title": case["payload"]["job_title"], "raw_text": case["payload"]["vacancy_text"]}
    )
    clarified = bool(result.get("clarifications") or deterministic)
    return {
        "statuses": statuses,
        "raw_statuses": raw_statuses,
        "guardrail_changed": raw_statuses != statuses,
        "raw_unsupported_positive": any(
            a in {"met", "partial"} and e in {"unknown", "unmet"}
            for a, e in zip(raw_statuses, case["expected_statuses"], strict=True)
        ),
        "expected_statuses": case["expected_statuses"],
        "statuses_correct": statuses == case["expected_statuses"],
        "clarification_present": clarified,
        "clarification_correct": not case["clarification_required"] or clarified,
        "unsupported_positive": any(
            a in {"met", "partial"} and e in {"unknown", "unmet"}
            for a, e in zip(statuses, case["expected_statuses"], strict=True)
        ),
    }


def holdout(settings: Settings, owner: UUID, case: Row, model: str, repeat: int) -> Row:
    tag = f"holdout-{case['case_id']}-{model}-{repeat}"
    provider = MeteredProvider(settings, owner, tag)
    row: Row = {"key": tag, "case_id": case["case_id"], "model": model, "repeat": repeat}
    try:
        completion = provider.complete(
            model,
            RELIABLE_PROMPT,
            json.dumps(case["payload"]),
            ReliableMatch,
            8000 if model == MODELS[1] else 5000,
            effort="high" if model == MODELS[1] else None,
        )
        output = ReliableMatch.model_validate_json(completion.text).model_dump(mode="json")
        result = reliable(output, case["payload"])
        row.update(
            valid=True, result=result, checks=checks(case, result, json.loads(completion.text))
        )
    except (Problem, ValueError, KeyError) as exc:
        row.update(valid=False, error=exc.code if isinstance(exc, Problem) else type(exc).__name__)
    row["run_ids"] = provider.calls
    if provider.last:
        row["completion"] = asdict(provider.last)
    return row


def request(client: TestClient, method: str, path: str, body: Row | None = None) -> Row:
    response = client.request(method, "/api/v1" + path, json=body)
    if response.status_code not in {200, 201}:
        raise ValueError(f"HTTP {response.status_code} at {path}: {response.text[:500]}")
    return dict(response.json())


def pipeline(admin: Settings, paid: Settings, owner: UUID, model: str, case: str) -> Row:
    name = "jobhunter_test_migration"
    assert name.startswith("jobhunter_test") and name != admin.db_name
    with psycopg.connect(
        host=admin.db_host,
        port=admin.db_port,
        dbname="postgres",
        user=admin.db_user,
        password=admin.db_password.get_secret_value(),
        autocommit=True,
    ) as db:
        if not db.execute("SELECT 1 FROM pg_database WHERE datname=%s", (name,)).fetchone():
            db.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    settings = admin.model_copy(
        update={
            "db_name": name,
            "app_db_user": "jobhunter_migration",
            "app_db_password": SecretStr("synthetic-migration-only"),
            "ai_parsing_model": model,
            "ai_matching_model": model,
            "ai_strategy_model": model,
            "openai_api_key": None,
            "ai_prices_reviewed": datetime.now(UTC).date(),
        }
    )
    migrate(settings)
    provision(settings)
    password = "synthetic-migration-password"
    with connect(settings) as db:
        db.execute("TRUNCATE users,login_limits,audit_events,ai_calls CASCADE")
        db.execute(
            "INSERT INTO users (id,username,password_hash) VALUES (%s,'local',%s)",
            (uuid4(), PasswordHasher().hash(password)),
        )
    tag = f"pipeline-{model}-{case}"
    provider = MeteredProvider(paid, owner, tag)
    result: Row = {"key": tag, "model": model, "case": case, "passed": False}
    with (
        patch("jobhunter_api.job_parser.get_provider", return_value=provider),
        patch("jobhunter_api.ai_matching.get_provider", return_value=provider),
        patch("jobhunter_api.packages.get_provider", return_value=provider),
        TestClient(create_app(settings), raise_server_exceptions=False) as client,
    ):
        client.headers["Origin"] = "http://127.0.0.1:5173"
        session = request(client, "POST", "/session", {"username": "local", "password": password})
        client.headers["X-CSRF-Token"] = session["csrf_token"]
        try:
            claim = "Built a personal Python API with SQL storage and automated tests."
            evidence = request(
                client,
                "POST",
                "/candidate/evidence",
                {
                    "source_type": "candidate_attestation",
                    "source_ref": "Synthetic fixture",
                    "locator": "portfolio",
                    "content": claim,
                    "review_confirmed": True,
                },
            )
            fact = request(
                client,
                "POST",
                "/candidate/facts",
                {
                    "claim": claim,
                    "category": "project",
                    "status": "verified",
                    "evidence_ids": [evidence["id"]],
                    "allowed_uses": ["matching", "cv", "cover_letter", "application_form"],
                    "review_confirmed": True,
                },
            )
            candidate = request(client, "GET", "/candidate/profile")
            candidate = request(
                client,
                "PATCH",
                "/candidate/profile",
                {"expected_version": candidate["version"], "display_name": "Alex Example"},
            )
            candidate = request(
                client,
                "POST",
                "/candidate/profile/review",
                {"expected_version": candidate["version"]},
            )
            raw = (
                "Junior Software Engineer\nCompany: Example Labs\nLocation: Dublin, Ireland.\n"
                "Python and SQL are required. Personal projects accepted. "
                "Automated tests desirable."
            )
            if case == "conflict":
                raw += (
                    "\nDescription: Graduate Data Engineer. "
                    "The job title and body differ; confirm the role."
                )
            else:
                raw += "\nWe provide mentoring and learning opportunities." * 80
            job = request(client, "POST", "/jobs/import", {"raw_text": raw})
            route = f"/jobs/{job['id']}"
            parsed = request(
                client, "POST", f"/ai{route}/parse", {"expected_version": job["version"]}
            )
            result["extraction"] = parsed["result"]
            assert parsed["result"]["fields"]["sponsorship"] is None
            assert parsed["result"]["fields"]["salary"] is None
            assert parsed["result"]["requirements"]
            job = request(
                client,
                "POST",
                f"/ai{route}/draft",
                {"expected_version": job["version"], "run_id": parsed["run_id"]},
            )
            assert job["status"] == "DISCOVERED"
            corrections = {}
            for field, reviewed_value in {
                "title": "Junior Software Engineer",
                "company_name": "Example Labs",
            }.items():
                if job[field] is None:
                    assert reviewed_value in raw
                    corrections[field] = reviewed_value
            result["scripted_human_corrections"] = corrections
            job = request(
                client,
                "PATCH",
                route,
                {
                    **{k: job[k] for k in JobEdit.model_fields if k in job},
                    **corrections,
                    "expected_version": job["version"],
                    "review_confirmed": True,
                },
            )
            matching_body = {
                "job_version": job["version"],
                "profile_version": candidate["version"],
                "fact_ids": [fact["id"]],
                "external_processing_confirmed": True,
            }
            suggestion = request(client, "POST", f"/ai{route}/suggest", matching_body)
            replay = request(client, "POST", f"/ai{route}/suggest", matching_body)
            assert replay["cached"] and replay["run_id"] == suggestion["run_id"]
            result["matching"] = suggestion["result"]
            match = request(
                client,
                "POST",
                route + "/analyse",
                {
                    "job_version": job["version"],
                    "profile_version": candidate["version"],
                    "review_confirmed": True,
                    "ai_run_id": suggestion["run_id"],
                    "assessments": [
                        {k: a[k] for k in ("requirement_id", "status", "reason", "fact_ids")}
                        for a in suggestion["result"]["assessments"]
                    ],
                },
            )
            if case == "conflict":
                assert match["recommendation"] == "REVIEW" and match["clarifications"]
            result["recommendation"] = match["recommendation"]
            strategy = request(
                client,
                "POST",
                route + "/strategy",
                {
                    **matching_body,
                    "use_ai": True,
                    "questions": ["Describe a software project."],
                    "contact_lines": ["alex@example.test"],
                },
            )
            result["strategy"] = strategy["selection"]
            selection = strategy["selection"]
            assert selection["answers"][0]["fact_ids"] == [fact["id"]]
            strategy = request(
                client,
                "POST",
                f"/strategies/{strategy['id']}/approve",
                {
                    "expected_version": strategy["version"],
                    "cv_fact_ids": selection["cv_fact_ids"],
                    "letter_fact_ids": selection["letter_fact_ids"],
                    "review_confirmed": True,
                },
            )
            package = request(
                client,
                "POST",
                route + "/generate-package",
                {"strategy_id": strategy["id"], "strategy_version": strategy["version"]},
            )
            path = f"/packages/{package['id']}"
            assert (
                client.get("/api/v1" + path + "/download/cv.pdf?expected_version=1").status_code
                == 409
            )
            package = request(
                client,
                "POST",
                path + "/review",
                {
                    "expected_version": package["version"],
                    "decision": "approve",
                    "review_confirmed": True,
                },
            )
            artifact = client.get(
                "/api/v1" + path + f"/download/bundle.zip?expected_version={package['version']}"
            )
            assert artifact.status_code == 200
            with ZipFile(BytesIO(artifact.content)) as bundle:
                for stem in ("cv", "cover-letter"):
                    text = " ".join(
                        p.text for p in Document(BytesIO(bundle.read(stem + ".docx"))).paragraphs
                    )
                    pdf = " ".join(
                        p.extract_text()
                        for p in PdfReader(BytesIO(bundle.read(stem + ".pdf"))).pages
                    )
                    assert claim in text and claim in pdf
                result["document_claims"] = package["content"]
            target = ROOT / ".private/evals/migration" / f"{model}-{case}.zip"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(artifact.content)
            request(
                client,
                "PATCH",
                route,
                {"expected_version": job["version"], "title": "Changed source"},
            )
            assert (
                client.get(
                    "/api/v1" + path + f"/download/cv.pdf?expected_version={package['version']}"
                ).status_code
                == 409
            )
            result.update(
                passed=True,
                cache_passed=True,
                stale_download_blocked=True,
                document_claims_verbatim=True,
                extraction_draft_gate=True,
            )
        except (AssertionError, ValueError, KeyError) as exc:
            result["error"] = str(exc) or type(exc).__name__
    result["run_ids"] = provider.calls
    if provider.last:
        result["last_completion"] = asdict(provider.last)
    return result


def web_probe(settings: Settings, owner: UUID) -> Row:
    payload = {
        "question": (
            "Qual é a página oficial atual do Critical Skills Employment Permit na Irlanda? "
            "Informe o link e se a página apresenta data de atualização; "
            "não avalie elegibilidade individual."
        ),
        "allowed_domains": ["enterprise.gov.ie", "gov.ie"],
        "as_of": datetime.now(UTC).date().isoformat(),
    }
    provider = OpenAIInference(settings)
    try:
        response = execute(
            settings,
            owner,
            "migration_web",
            None,
            payload,
            MODELS[1],
            RESEARCH_VERSION,
            200000,
            8000,
            lambda: search(provider, MODELS[1], "high", payload, 8000),
            lambda completion: validate_research(completion, payload),
            execution_config={"effort": "high", "tools": ["web_search"]},
            max_tool_calls=3,
        )
        return {"passed": True, "run_ids": [response["run_id"]], "result": response["result"]}
    except Problem as exc:
        return {"passed": False, "error": exc.code}
    finally:
        provider.client.close()


def summarize(report: Row) -> Row:
    output = {}
    expected = {
        c["case_id"]: c["clarification_required"]
        for c in json.loads(DATA.read_text(encoding="utf-8"))["cases"]
    }
    for model in MODELS:
        rows = [r for r in report["holdout"] if r["model"] == model]
        valid = [r for r in rows if r["valid"]]
        output[model] = {
            "attempts": len(rows),
            "valid": len(valid),
            "status_correct": sum(r["checks"]["statuses_correct"] for r in valid),
            "clarification_correct": sum(r["checks"]["clarification_correct"] for r in valid),
            "unsupported_positives": sum(r["checks"]["unsupported_positive"] for r in valid),
            "raw_unsupported_positives": sum(
                r["checks"]["raw_unsupported_positive"] for r in valid
            ),
            "guardrail_changes": sum(r["checks"]["guardrail_changed"] for r in valid),
            "extra_clarifications": sum(
                r["checks"]["clarification_present"] and not expected[r["case_id"]] for r in valid
            ),
            "human_correction_needed": sum(
                not r["valid"]
                or not r["checks"]["statuses_correct"]
                or not r["checks"]["clarification_correct"]
                for r in rows
            ),
            "unstable_cases": [
                key
                for key in sorted({r["case_id"] for r in rows})
                if len(
                    {
                        json.dumps(r.get("checks", {}).get("statuses"))
                        for r in rows
                        if r["case_id"] == key
                    }
                )
                > 1
            ],
        }
    return output


def save(report: Row) -> None:
    report["summary"] = summarize(report)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def check_report(report: Row, cases: list[Row]) -> None:
    assert report["dataset_sha256"] == digest()
    assert report["contract_version"] == CONTRACT_VERSION
    assert len(report["holdout"]) == len(cases) * 4
    assert len({r["key"] for r in report["holdout"]}) == len(cases) * 4
    assert {r["key"] for r in report["holdout"]} == {
        f"holdout-{case['case_id']}-{model}-{repeat}"
        for case in cases
        for model in MODELS
        for repeat in (1, 2)
    }
    for row in report["holdout"]:
        if row["valid"]:
            case = next(c for c in cases if c["case_id"] == row["case_id"])
            result = reliable(
                ReliableMatch.model_validate_json(row["completion"]["text"]).model_dump(
                    mode="json"
                ),
                case["payload"],
            )
            assert row["checks"] == checks(case, result, json.loads(row["completion"]["text"]))
    assert report["summary"] == summarize(report)
    assert {(r["model"], r["case"]) for r in report["pipelines"]} == {
        (model, case) for model in MODELS for case in ("standard", "conflict")
    }
    assert all(r["passed"] for r in report["pipelines"] if r["model"] == MODELS[1])
    for row in report["pipelines"]:
        if not row["passed"]:
            assert "AI_INVALID_OUTPUT" in row["error"] and "matching" not in row
            output = ReliableMatch.model_validate_json(row["last_completion"]["text"])
            assert any(
                i.kind == "EVIDENCE_CONFLICT" and len(set(i.fact_ids)) < 2
                for i in output.clarifications
            )
        else:
            assert row["cache_passed"] and row["stale_download_blocked"]
            assert row["document_claims_verbatim"] and row["extraction_draft_gate"]
    assert report["web"]["passed"]
    human = json.loads((ROOT / "data/evals/user-decisions.json").read_text(encoding="utf-8"))
    assert human["label_author"] == "user" and len(human["labels"]) == 3
    assert {r["case_id"] for r in human["labels"]} == {"REAL-01", "REAL-10", "REAL-12"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--retry-pipeline", action="store_true")
    parser.add_argument("--part", choices=["all", "holdout", "pipeline", "web"], default="all")
    args = parser.parse_args()
    cases = json.loads(DATA.read_text(encoding="utf-8"))["cases"]
    if args.check:
        check_report(json.loads(REPORT.read_text(encoding="utf-8")), cases)
        print("Migration evidence verified offline; imperfections remain visible in summary.")
        return
    if not args.live:
        print(
            "Use --live for explicit real calls, at most EUR 1 additional reserved budget per run."
        )
        return
    admin = Settings()
    settings = admin.runtime()
    with connect(settings) as db:
        actor = db.execute("SELECT id FROM users WHERE username='local'").fetchone()
        assert actor
        before = totals(db, settings)
    settings = settings.model_copy(
        update={
            "ai_monthly_eur": min(
                settings.ai_monthly_eur, Decimal(before["allocated_eur"]) + Decimal("1")
            )
        }
    )
    report = (
        json.loads(REPORT.read_text(encoding="utf-8"))
        if REPORT.exists()
        else {
            "dataset_sha256": digest(),
            "prompt_version": RELIABLE_VERSION,
            "contract_version": CONTRACT_VERSION,
            "human_gold": False,
            "started_at": datetime.now(UTC).isoformat(),
            "holdout": [],
            "pipelines": [],
            "web": {},
        }
    )
    assert report["dataset_sha256"] == digest()
    if args.retry_pipeline:
        report.setdefault("pipeline_attempts", []).extend(
            r for r in report["pipelines"] if not r["passed"]
        )
        report["pipelines"] = [r for r in report["pipelines"] if r["passed"]]
        save(report)
    if args.part in {"all", "holdout"}:
        done = {r["key"] for r in report["holdout"]}
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(holdout, settings, actor["id"], case, model, repeat)
                for case in cases
                for model in MODELS
                for repeat in (1, 2)
                if f"holdout-{case['case_id']}-{model}-{repeat}" not in done
            ]
            for future in as_completed(futures):
                row = future.result()
                report["holdout"].append(row)
                save(report)
                print(row["key"], row.get("checks", row.get("error")), flush=True)
    if args.part in {"all", "pipeline"}:
        done = {r["key"] for r in report["pipelines"]}
        for model in MODELS:
            for case in ("standard", "conflict"):
                if f"pipeline-{model}-{case}" in done:
                    continue
                row = pipeline(admin, settings, actor["id"], model, case)
                report["pipelines"].append(row)
                save(report)
                print(row["key"], "passed" if row["passed"] else row["error"], flush=True)
    if args.part in {"all", "web"} and not report["web"]:
        report["web"] = web_probe(settings, actor["id"])
        save(report)
        print("Web probe:", report["web"].get("passed"), report["web"].get("error"), flush=True)
    ids = {
        identity
        for r in [
            *report["holdout"],
            *report["pipelines"],
            *report.get("pipeline_attempts", []),
            report["web"],
        ]
        for identity in r.get("run_ids", [])
    }
    with connect(settings) as db:
        rows = db.execute(
            "SELECT id,model,actual_eur,input_tokens,output_tokens,latency_ms,price_snapshot "
            "FROM ai_calls WHERE id=ANY(%s::uuid[])",
            (list(ids),),
        ).fetchall()
    report["ledger"] = [{**r, "id": str(r["id"]), "actual_eur": str(r["actual_eur"])} for r in rows]
    report["cost_eur"] = str(sum((r["actual_eur"] or Decimal(0) for r in rows), Decimal(0)))
    save(report)
    print("Saved report. Accounted EUR", report["cost_eur"], flush=True)


if __name__ == "__main__":
    main()
