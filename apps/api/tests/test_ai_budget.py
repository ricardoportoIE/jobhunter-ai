from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from jobhunter_api.ai_admin import reconcile
from jobhunter_api.ai_budget import cost, execute, reserve, totals
from jobhunter_api.errors import Problem
from jobhunter_api.inference import Completion, ProviderFailure
from jobhunter_api.manage import erase
from jobhunter_api.settings import Settings
from jobhunter_api.store import connect

MODEL = "gpt-4.1-mini-2025-04-14"


def owner(settings: Settings) -> UUID:
    with connect(settings) as db:
        row = db.execute("SELECT id FROM users LIMIT 1").fetchone()
        assert row
        return UUID(str(row["id"]))


def test_task_policies_tool_cost_and_cache_configuration(db_settings: Settings) -> None:
    identity = owner(db_settings)
    assert db_settings.policy("suggest") == ("gpt-5.6-luna", "high")
    assert db_settings.policy("parse") == (MODEL, None)
    customized = db_settings.model_copy(update={"ai_matching_prompt_suffix": "Explain ambiguity."})
    prompt, version = customized.prompt("suggest", "Base rules", "v1")
    assert prompt.startswith("Base rules") and prompt.endswith("Explain ambiguity.")
    assert version.startswith("v1+") and customized.prompt("parse", "Base", "v1") == ("Base", "v1")
    calls = []

    def invoke() -> Completion:
        calls.append(1)
        return Completion(
            "{}",
            100,
            200,
            "fixture",
            2,
            "completed",
            reasoning_tokens=150,
            cached_input_tokens=50,
            web_search_calls=2,
        )

    def run(key: str, effort: str = "high", version: str = "v1") -> dict[str, object]:
        return execute(
            db_settings,
            identity,
            "research",
            key,
            {},
            "gpt-5.6-luna",
            version,
            1000,
            500,
            invoke,
            lambda _: {"ok": True},
            execution_config={"effort": effort},
            max_tool_calls=3,
        )

    first = run("first")
    assert run("another-key")["run_id"] == first["run_id"] and len(calls) == 1
    assert run("medium", "medium")["run_id"] != first["run_id"]
    assert run("new-prompt", version="v2")["run_id"] != first["run_id"]
    with connect(db_settings) as db:
        row = db.execute("SELECT * FROM ai_calls WHERE id=%s", (first["run_id"],)).fetchone()
    assert row
    expected = cost("gpt-5.6-luna", 100, 200, db_settings.ai_eur_per_usd)
    assert row["actual_eur"] == expected + Decimal("0.02") * db_settings.ai_eur_per_usd
    assert row["actual_eur"] <= row["reserved_eur"]
    assert row["price_snapshot"]["usage"]["reasoning_tokens"] == 150


def test_unexpected_tool_usage_blocks_further_spending(db_settings: Settings) -> None:
    with pytest.raises(Problem) as error:
        execute(
            db_settings,
            owner(db_settings),
            "research",
            None,
            {},
            "gpt-5.6-luna",
            "v1",
            1000,
            500,
            lambda: Completion("{}", 100, 200, None, 1, "completed", web_search_calls=4),
            lambda _: {},
            max_tool_calls=3,
        )
    assert error.value.code == "USAGE_OUT_OF_BOUND"
    with connect(db_settings) as db:
        assert totals(db, db_settings)["unreconciled"]


def test_atomic_reservations_across_workers(db_settings: Settings) -> None:
    settings = db_settings.model_copy(
        update={"ai_monthly_eur": cost(MODEL, 1000, 100, Decimal("1.25"))}
    )
    identity = owner(settings)

    def attempt(index: int) -> str:
        try:
            reserve(
                settings.runtime(), identity, "test", str(index), str(index), MODEL, "v1", 1000, 100
            )
            return "reserved"
        except Problem as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = list(pool.map(attempt, range(4)))
    assert outcomes.count("reserved") == 1
    assert outcomes.count("AI_BUDGET_EXCEEDED") == 3


def test_idempotency_settlement_and_unknown_cost(db_settings: Settings) -> None:
    identity = owner(db_settings)
    calls: list[str] = []

    def complete() -> Completion:
        calls.append("called")
        return Completion("{}", 20, 10, "request-fixture", 2, "completed")

    def run(key: str, payload: str = "same") -> dict[str, object]:
        return execute(
            db_settings,
            identity,
            "test",
            key,
            {"text": payload},
            MODEL,
            "v1",
            1000,
            100,
            complete,
            lambda _: {"ok": True},
        )

    first, second = run("key"), run("key")
    assert first["run_id"] == second["run_id"] and second["cached"]
    assert len(calls) == 1
    with pytest.raises(Problem, match="Chave"):
        run("key", "changed")

    def timeout() -> Completion:
        raise ProviderFailure("TIMEOUT", charge_unknown=True)

    with pytest.raises(Problem):
        execute(
            db_settings,
            identity,
            "timeout",
            "unknown",
            {},
            MODEL,
            "v1",
            1000,
            100,
            timeout,
            lambda _: {},
        )
    with connect(db_settings) as db:
        budget = totals(db, db_settings)
    assert budget["unreconciled"] and Decimal(budget["reserved_eur"]) > 0
    with pytest.raises(Problem) as blocked:
        run("next", "new")
    assert blocked.value.code == "COST_UNRECONCILED"


def test_price_age_combined_budget_and_invalid_output(db_settings: Settings) -> None:
    identity = owner(db_settings)
    stale = db_settings.model_copy(update={"ai_prices_reviewed": date(2020, 1, 1)})
    with pytest.raises(Problem) as error:
        reserve(stale, identity, "test", "x", "x", MODEL, "v1", 100, 100)
    assert error.value.code == "PRICES_STALE"
    restricted = db_settings.model_copy(update={"combined_monthly_eur": Decimal("15")})
    with pytest.raises(Problem) as error:
        reserve(restricted, identity, "test", "x", "x", MODEL, "v1", 100, 100)
    assert error.value.code == "AI_BUDGET_EXCEEDED"
    with pytest.raises(Problem) as error:
        execute(
            db_settings,
            identity,
            "invalid",
            "x",
            {},
            MODEL,
            "v1",
            100,
            100,
            lambda: Completion("", 20, 30, None, 5, "incomplete"),
            lambda _: {},
        )
    assert error.value.code == "AI_INVALID_OUTPUT"
    with connect(db_settings) as db:
        row = db.execute("SELECT * FROM ai_calls").fetchone()
    assert row and row["status"] == "invalid" and row["actual_eur"] > 0


def test_interrupted_reservation_survives_month_rollover_and_reconciliation(
    db_settings: Settings,
) -> None:
    identity = owner(db_settings)
    call, _ = reserve(db_settings, identity, "test", "month", "month", MODEL, "v1", 1000, 100)
    with connect(db_settings) as db:
        db.execute(
            "UPDATE ai_calls SET created_at=now()-interval '35 days' WHERE id=%s", (call["id"],)
        )
        usage = totals(db, db_settings)
    assert usage["unreconciled"] and Decimal(usage["reserved_eur"]) == call["reserved_eur"]
    reconcile(db_settings, call["id"], Decimal("0.0005"))
    with connect(db_settings) as db:
        usage = totals(db, db_settings)
    assert not usage["unreconciled"] and Decimal(usage["spent_eur"]) == Decimal("0.0005")


def test_erasure_during_inference_cannot_restore_personal_results(db_settings: Settings) -> None:
    identity = owner(db_settings)

    def complete() -> Completion:
        erase(db_settings, "DELETE_LOCAL_APPLICATION_DATA")
        return Completion("private output", 10, 10, "test", 2, "completed")

    with pytest.raises(Problem) as error:
        execute(
            db_settings,
            identity,
            "test",
            "erase",
            {},
            MODEL,
            "v1",
            100,
            100,
            complete,
            lambda _: {"private": "must not return after erasure"},
        )
    assert error.value.code == "AI_RUN_CANCELLED"
    with connect(db_settings) as db:
        row = db.execute("SELECT owner_id,result,status FROM ai_calls").fetchone()
        assert row == {"owner_id": None, "result": None, "status": "running"}
        assert db.execute("SELECT count(*) AS n FROM audit_events").fetchone() == {"n": 0}


def test_explicit_retry_keeps_cost_history_and_recovers_original_key(db_settings: Settings) -> None:
    identity = owner(db_settings)

    def refused() -> Completion:
        raise ProviderFailure("PROVIDER_HTTP_429", charge_unknown=False)

    with pytest.raises(Problem):
        execute(
            db_settings,
            identity,
            "retry",
            "original",
            {},
            MODEL,
            "v1",
            100,
            100,
            refused,
            lambda _: {},
        )
    retried = execute(
        db_settings,
        identity,
        "retry",
        "second",
        {},
        MODEL,
        "v1",
        100,
        100,
        lambda: Completion("{}", 10, 10, None, 1, "completed"),
        lambda _: {"ok": True},
    )
    recovered = execute(
        db_settings, identity, "retry", "original", {}, MODEL, "v1", 100, 100, refused, lambda _: {}
    )
    assert recovered["cached"] and recovered["run_id"] == retried["run_id"]
    with connect(db_settings) as db:
        assert db.execute("SELECT count(*) AS n FROM ai_calls").fetchone() == {"n": 2}
    reserve(db_settings, identity, "running", "first", "same", MODEL, "v1", 100, 100)
    with pytest.raises(Problem) as error:
        reserve(db_settings, identity, "running", "other", "same", MODEL, "v1", 100, 100)
    assert error.value.code == "AI_IN_PROGRESS"
