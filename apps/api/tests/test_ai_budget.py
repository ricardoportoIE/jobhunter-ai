from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from jobhunter_api.ai_budget import cost, execute, reserve, totals
from jobhunter_api.errors import Problem
from jobhunter_api.inference import Completion, ProviderFailure
from jobhunter_api.settings import Settings
from jobhunter_api.store import connect

MODEL = "gpt-4.1-mini-2025-04-14"


def owner(settings: Settings) -> UUID:
    with connect(settings) as db:
        row = db.execute("SELECT id FROM users LIMIT 1").fetchone()
        assert row
        return UUID(str(row["id"]))


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
