"""Versioned embeddings and owner-scoped local cosine search; no cloud vector store."""

import json
import math
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import Field

from jobhunter_api.ai_budget import execute
from jobhunter_api.auth import Actor, settings_for
from jobhunter_api.errors import Problem
from jobhunter_api.inference import EmbeddingInference, OpenAIInference
from jobhunter_api.profile import Input, Version
from jobhunter_api.records import get_record, list_records, owner_lock, public
from jobhunter_api.scoring import eligible
from jobhunter_api.settings import Settings
from jobhunter_api.store import Connection, Row, connect

router = APIRouter(prefix="/api/v1/ai", tags=["semantic search"])
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_VERSION = "embedding-256-chunks-1.0"


def embedding_provider(settings: Settings) -> EmbeddingInference:
    if not settings.openai_api_key or not settings.openai_api_key.get_secret_value():
        raise Problem(409, "AI_NOT_CONFIGURED", "Configure a chave de IA no backend local.")
    return OpenAIInference(settings)


def vectors(data: str, expected: int) -> Row:
    result = json.loads(data)
    rows = result["vectors"]
    if len(rows) != expected:
        raise ValueError("Invalid vector count")
    for row in rows:
        if len(row) != 256 or not all(
            isinstance(v, (int, float)) and math.isfinite(v) for v in row
        ):
            raise ValueError("Invalid vector")
        if not any(row):
            raise ValueError("Empty vector")
    return {"vectors": rows}


def embed(
    settings: Settings,
    provider: EmbeddingInference,
    owner: UUID,
    texts: list[str],
    metadata: Row,
    key: str | None = None,
) -> Row:
    return execute(
        settings,
        owner,
        "embed",
        key,
        {"texts": texts, **metadata},
        EMBEDDING_MODEL,
        EMBEDDING_VERSION,
        sum(len(t.encode("utf-8")) for t in texts) + 256,
        0,
        lambda: provider.embed(texts),
        lambda c: vectors(c.text, len(texts)),
    )


def permitted_facts(db: Connection, owner: UUID) -> dict[str, Row]:
    evidence = {str(row["id"]): public(row) for row in list_records(db, owner, "evidence")}
    return {
        str(row["id"]): row
        for row in list_records(db, owner, "fact")
        if row["data"]["sensitivity"] != "sensitive"
        and eligible(public(row), evidence, datetime.now(UTC))
        and all(evidence[eid]["sensitivity"] != "sensitive" for eid in row["data"]["evidence_ids"])
    }


class IndexInput(Version):
    kind: Literal["job", "fact"]
    source_id: UUID
    external_processing_confirmed: Literal[True]


@router.post("/index")
def index(data: IndexInput, actor: Actor, request: Request) -> Row:
    settings = settings_for(request)
    with connect(settings) as db:
        row = get_record(db, actor.id, data.kind, data.source_id)
        if row["version"] != data.expected_version:
            raise Problem(409, "VERSION_CONFLICT", "Atualize o registro antes de indexar.")
        if data.kind == "fact" and str(data.source_id) not in permitted_facts(db, actor.id):
            raise Problem(409, "FACT_NOT_ELIGIBLE", "Fato sem evidência válida para IA externa.")
        content = row["data"]["raw_text" if data.kind == "job" else "claim"]
    # 1000 Unicode characters <= 4000 UTF-8 bytes/tokens, below per-input model limit.
    chunks = [content[start : start + 1000] for start in range(0, len(content), 1000)]
    result = embed(
        settings,
        embedding_provider(settings),
        actor.id,
        chunks,
        {"kind": data.kind, "id": str(data.source_id), "version": data.expected_version},
        request.headers.get("idempotency-key"),
    )
    with connect(settings) as db:
        owner_lock(db, actor.id)
        current = get_record(db, actor.id, data.kind, data.source_id)
        if current["version"] != data.expected_version:
            raise Problem(409, "VERSION_CONFLICT", "O registro mudou durante a indexação.")
        if data.kind == "fact" and str(data.source_id) not in permitted_facts(db, actor.id):
            raise Problem(409, "FACT_NOT_ELIGIBLE", "O fato perdeu validade durante a indexação.")
        for chunk, vector in enumerate(result["result"]["vectors"]):
            db.execute(
                "INSERT INTO ai_embeddings VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (
                    actor.id,
                    data.kind,
                    data.source_id,
                    data.expected_version,
                    EMBEDDING_MODEL,
                    chunk,
                    vector,
                    result["run_id"],
                ),
            )
    return {"run_id": result["run_id"], "cached": result["cached"], "chunks": len(chunks)}


def cosine(a: list[float], b: list[float]) -> float:
    denominator = math.sqrt(sum(v * v for v in a) * sum(v * v for v in b))
    return sum(x * y for x, y in zip(a, b, strict=True)) / denominator if denominator else 0


def current_vectors(db: Connection, owner: UUID, kind: str) -> list[Row]:
    rows = list(
        db.execute(
            "SELECT e.*,r.data FROM ai_embeddings e JOIN records r ON r.id=e.source_id "
            "AND r.owner_id=e.owner_id WHERE e.owner_id=%s AND e.kind=%s "
            "AND e.source_version=r.version AND NOT r.deleted AND e.model=%s "
            "AND coalesce((r.data->>'archived')::boolean,false)=false "
            "ORDER BY r.updated_at DESC,e.chunk LIMIT 5001",
            (owner, kind, EMBEDDING_MODEL),
        ).fetchall()
    )
    if len(rows) > 5000:
        raise Problem(
            409, "INDEX_CAPACITY", "Índice local excede 5000 trechos; arquive vagas antigas."
        )
    if kind == "fact":
        allowed = permitted_facts(db, owner)
        rows = [r for r in rows if str(r["source_id"]) in allowed]
    return rows


class SearchInput(Input):
    query: str = Field(min_length=1, max_length=1000)
    kind: Literal["job", "fact"] = "job"
    external_processing_confirmed: Literal[True]


@router.post("/search")
def search(data: SearchInput, actor: Actor, request: Request) -> Row:
    settings = settings_for(request)
    with connect(settings) as db:
        candidates = current_vectors(db, actor.id, data.kind)
    if not candidates:
        return {"items": [], "indexed_documents": 0, "run_id": None}
    result = embed(
        settings,
        embedding_provider(settings),
        actor.id,
        [data.query],
        {"purpose": "search"},
        request.headers.get("idempotency-key"),
    )
    query = result["result"]["vectors"][0]
    # Re-read after network I/O to exclude revoked, edited or deleted records.
    with connect(settings) as db:
        candidates = current_vectors(db, actor.id, data.kind)
    ranked: dict[str, Row] = {}
    for row in candidates:
        identity = str(row["source_id"])
        score = cosine(query, row["vector"])
        if identity not in ranked or score > ranked[identity]["similarity"]:
            ranked[identity] = {
                "id": identity,
                "version": row["source_version"],
                "kind": data.kind,
                "similarity": round(score, 4),
                "label": row["data"].get("title")
                or row["data"].get("claim")
                or "Vaga aguardando revisão",
            }
    return {
        "items": sorted(ranked.values(), key=lambda r: r["similarity"], reverse=True)[:10],
        "indexed_documents": len(ranked),
        "run_id": result["run_id"],
    }


@router.get("/index")
def indexed(actor: Actor, request: Request) -> Row:
    with connect(settings_for(request)) as db:
        return {
            kind: list({str(r["source_id"]) for r in current_vectors(db, actor.id, kind)})
            for kind in ("job", "fact")
        }
