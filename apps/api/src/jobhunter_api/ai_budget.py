"""Committed reservations precede network I/O. Unknown charges fail closed."""

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import ROUND_CEILING, Decimal
from typing import Any
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb
from pydantic import BaseModel, ValidationError

from jobhunter_api.deduplication import fingerprint
from jobhunter_api.errors import Problem
from jobhunter_api.inference import Completion, ProviderFailure, StructuredInference, strict_schema
from jobhunter_api.records import audit
from jobhunter_api.settings import Settings
from jobhunter_api.store import Connection, Row, connect

PRICES = {
    "gpt-4.1-mini-2025-04-14": (Decimal("0.40"), Decimal("1.60")),
    "gpt-4.1-nano-2025-04-14": (Decimal("0.10"), Decimal("0.40")),
    "text-embedding-3-small": (Decimal("0.02"), Decimal("0")),
}
MICRO = Decimal("0.00000001")


def cost(model: str, inputs: int, outputs: int, conversion: Decimal) -> Decimal:
    incoming, outgoing = PRICES[model]
    return ((incoming * inputs + outgoing * outputs) * conversion / 1000000).quantize(
        MICRO, rounding=ROUND_CEILING
    )


def totals(db: Connection, settings: Settings) -> Row:
    row = db.execute(
        "SELECT coalesce(sum(coalesce(actual_eur,reserved_eur)),0) AS allocated, "
        "coalesce(sum(actual_eur),0) AS spent, "
        "coalesce(sum(reserved_eur) FILTER (WHERE actual_eur IS NULL),0) AS reserved "
        "FROM ai_calls WHERE created_at >= date_trunc('month', now() AT TIME ZONE 'UTC') "
        "AT TIME ZONE 'UTC'"
    ).fetchone()
    assert row is not None
    # Reserve the entire separate AWS allowance; phase 2 has no AWS billing integration.
    combined = row["allocated"] + Decimal("15")
    uncertain = bool(
        db.execute(
            "SELECT 1 FROM ai_calls WHERE status='uncertain' OR "
            "(status='running' AND created_at < now()-interval '5 minutes') LIMIT 1"
        ).fetchone()
    )
    return {
        "spent_eur": str(row["spent"]),
        "reserved_eur": str(row["reserved"]),
        "allocated_eur": str(row["allocated"]),
        "limit_eur": str(settings.ai_monthly_eur),
        "combined_allocated_eur": str(combined),
        "combined_limit_eur": str(settings.combined_monthly_eur),
        "aws_allowance_eur": "15",
        "unreconciled": uncertain,
        "alerts": [
            threshold
            for threshold in (50, 80, 100)
            if row["allocated"] >= settings.ai_monthly_eur * threshold / 100
        ],
        "combined_alerts": [
            threshold
            for threshold in (50, 80, 100)
            if combined >= settings.combined_monthly_eur * threshold / 100
        ],
    }


def reserve(
    settings: Settings,
    owner: UUID,
    operation: str,
    key: str,
    payload_hash: str,
    model: str,
    prompt_version: str,
    input_bound: int,
    max_output: int,
) -> tuple[Row, bool]:
    if not key.strip() or len(key) > 200:
        raise Problem(422, "INVALID_KEY", "Chave de execução inválida.")
    if model not in PRICES or not 0 < input_bound <= 120000 or not 0 <= max_output <= 6000:
        raise Problem(422, "AI_INPUT_LIMIT", "Conteúdo acima do limite de uma execução de IA.")
    amount = cost(model, input_bound, max_output, settings.ai_eur_per_usd)
    with connect(settings) as db:
        db.execute("SELECT pg_advisory_xact_lock(71020)")
        existing = db.execute(
            "SELECT * FROM ai_calls WHERE owner_id=%s AND operation=%s AND request_key=%s",
            (owner, operation, key),
        ).fetchone()
        if existing:
            if existing["payload_hash"] != payload_hash:
                raise Problem(409, "IDEMPOTENCY_CONFLICT", "Chave utilizada com outro conteúdo.")
            if existing["status"] == "succeeded":
                return existing, True
            raise Problem(
                409,
                "AI_EXECUTION_EXISTS",
                "Execução em andamento ou já encerrada. Consulte o histórico de IA.",
            )
        age = (datetime.now(UTC).date() - settings.ai_prices_reviewed).days
        if age < 0 or age > 30:
            raise Problem(409, "PRICES_STALE", "Atualize a revisão dos preços antes de usar IA.")
        usage = totals(db, settings)
        if usage["unreconciled"]:
            raise Problem(
                409,
                "COST_UNRECONCILED",
                "Há uma execução com custo desconhecido. Reconcilie o histórico de IA.",
            )
        if (
            Decimal(usage["allocated_eur"]) + amount > settings.ai_monthly_eur
            or Decimal(usage["combined_allocated_eur"]) + amount > settings.combined_monthly_eur
        ):
            raise Problem(429, "AI_BUDGET_EXCEEDED", "Limite mensal reservado para IA atingido.")
        attempts = db.execute(
            "SELECT count(*) AS n FROM ai_calls WHERE owner_id=%s AND operation=%s "
            "AND payload_hash=%s AND created_at>now()-interval '1 day'",
            (owner, operation, payload_hash),
        ).fetchone()
        if attempts and attempts["n"] >= 2:
            raise Problem(429, "AI_RETRY_LIMIT", "Limite de duas tentativas por conteúdo em 24h.")
        identity = uuid4()
        row = db.execute(
            "INSERT INTO ai_calls (id,owner_id,operation,request_key,payload_hash,model,"
            "prompt_version,price_snapshot,status,reserved_eur) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'running',%s) RETURNING *",
            (
                identity,
                owner,
                operation,
                key,
                payload_hash,
                model,
                prompt_version,
                Jsonb(
                    {
                        "input_usd_per_million": str(PRICES[model][0]),
                        "output_usd_per_million": str(PRICES[model][1]),
                        "eur_per_usd_allowance": str(settings.ai_eur_per_usd),
                        "reviewed": settings.ai_prices_reviewed.isoformat(),
                        "input_token_bound": input_bound,
                        "max_output_tokens": max_output,
                    }
                ),
                amount,
            ),
        ).fetchone()
        assert row is not None
        audit(db, owner, "ai.reserved", identity, 1)
        return row, False


def settle(
    settings: Settings,
    call: Row,
    completion: Completion | None,
    status: str,
    result: Row | None = None,
    error: str | None = None,
) -> None:
    if completion is None:
        amount = Decimal(0) if status == "failed" else None
    else:
        amount = cost(
            call["model"],
            completion.input_tokens,
            completion.output_tokens,
            Decimal(call["price_snapshot"]["eur_per_usd_allowance"]),
        )
    with connect(settings) as db:
        db.execute("SELECT pg_advisory_xact_lock(71020)")
        db.execute(
            "UPDATE ai_calls SET status=%s,actual_eur=%s,input_tokens=%s,output_tokens=%s,"
            "latency_ms=%s,provider_request_id=%s,result=%s,error_code=%s,finished_at=now() "
            "WHERE id=%s AND status='running'",
            (
                status,
                amount,
                completion.input_tokens if completion else None,
                completion.output_tokens if completion else None,
                completion.elapsed_ms if completion else None,
                completion.request_id if completion else None,
                Jsonb(result),
                error,
                call["id"],
            ),
        )
        audit(db, call["owner_id"], "ai." + status, call["id"], 1)


def execute(
    settings: Settings,
    owner: UUID,
    operation: str,
    key: str | None,
    payload: Row,
    model: str,
    prompt_version: str,
    input_bound: int,
    max_output: int,
    invoke: Callable[[], Completion],
    validate: Callable[[Completion], Row],
) -> Row:
    hashed = fingerprint({"payload": payload, "model": model, "prompt": prompt_version})
    call, cached = reserve(
        settings,
        owner,
        operation,
        key or hashed,
        hashed,
        model,
        prompt_version,
        input_bound,
        max_output,
    )
    if cached:
        return {"run_id": str(call["id"]), "cached": True, "result": call["result"]}
    try:
        completion = invoke()
        if completion.input_tokens < 0 or completion.output_tokens < 0:
            raise ProviderFailure("USAGE_INVALID", charge_unknown=True)
    except ProviderFailure as exc:
        settle(
            settings, call, None, "uncertain" if exc.charge_unknown else "failed", error=exc.code
        )
        raise Problem(
            502,
            "AI_PROVIDER_ERROR",
            "A IA não concluiu a chamada. Consulte o histórico antes de tentar novamente.",
        ) from None
    except Exception:
        settle(settings, call, None, "uncertain", error="UNEXPECTED_PROVIDER_ERROR")
        raise Problem(
            502, "AI_PROVIDER_ERROR", "Chamada interrompida; custo em reconciliação."
        ) from None
    try:
        if completion.status != "completed":
            raise ValueError("Incomplete or refused output")
        result = validate(completion)
    except (ValueError, ValidationError, KeyError, TypeError):
        settle(settings, call, completion, "invalid", error="INVALID_OUTPUT")
        raise Problem(
            422,
            "AI_INVALID_OUTPUT",
            "A resposta da IA não passou na validação. Os dados revisados foram preservados.",
        ) from None
    settle(settings, call, completion, "succeeded", result)
    return {"run_id": str(call["id"]), "cached": False, "result": result}


def structured(
    settings: Settings,
    provider: StructuredInference,
    owner: UUID,
    operation: str,
    key: str | None,
    payload: Row,
    prompt: str,
    prompt_version: str,
    schema: type[BaseModel],
    validate: Callable[[dict[str, Any]], Row],
    model: str | None = None,
) -> Row:
    import json

    selected = model or settings.ai_model
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    contract = json.dumps(strict_schema(schema.model_json_schema()))
    bound = len((prompt + serialized + contract).encode("utf-8")) + 2048

    def checked(completion: Completion) -> Row:
        return validate(schema.model_validate_json(completion.text).model_dump(mode="json"))

    return execute(
        settings,
        owner,
        operation,
        key,
        {"data": payload, "schema": schema.model_json_schema(), "instructions": prompt},
        selected,
        prompt_version,
        bound,
        5000,
        lambda: provider.complete(selected, prompt, serialized, schema, 5000),
        checked,
    )
