"""Authenticated AI status and redacted local execution tracing."""

from fastapi import APIRouter, Request

from jobhunter_api.ai_budget import totals
from jobhunter_api.auth import Actor, settings_for
from jobhunter_api.store import Row, connect

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])


@router.get("/status")
def status(actor: Actor, request: Request) -> Row:
    settings = settings_for(request)
    with connect(settings) as db:
        return {
            "configured": bool(
                settings.openai_api_key and settings.openai_api_key.get_secret_value()
            ),
            "model": settings.ai_model,
            "tasks": {
                op: {"model": settings.policy(op)[0], "effort": settings.policy(op)[1]}
                for op in (
                    "cv_extract",
                    "parse",
                    "suggest",
                    "suggest_review",
                    "strategy",
                    "research",
                )
            },
            "budget": totals(db, settings),
        }


@router.get("/runs")
def runs(actor: Actor, request: Request) -> list[Row]:
    with connect(settings_for(request)) as db:
        return list(
            db.execute(
                "SELECT id,operation,model,prompt_version,status,reserved_eur,actual_eur,"
                "input_tokens,output_tokens,latency_ms,error_code,created_at,"
                "price_snapshot->'execution_config' AS execution_config,"
                "price_snapshot->'usage' AS usage "
                "FROM ai_calls WHERE owner_id=%s ORDER BY created_at DESC LIMIT 50",
                (actor.id,),
            ).fetchall()
        )
