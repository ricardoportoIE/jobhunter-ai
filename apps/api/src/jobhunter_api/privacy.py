"""Authenticated export; erasure is an explicit local administration operation."""

from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response

from jobhunter_api.auth import Actor, settings_for
from jobhunter_api.records import owner_lock, public
from jobhunter_api.store import Row, connect

router = APIRouter(prefix="/api/v1/candidate", tags=["privacy"])


@router.get("/export")
def export(actor: Actor, request: Request, response: Response) -> Row:
    with connect(settings_for(request)) as db:
        owner_lock(db, actor.id)
        records = db.execute(
            "SELECT * FROM records WHERE owner_id=%s ORDER BY kind,id", (actor.id,)
        ).fetchall()
        snapshots = db.execute(
            "SELECT kind,source_id,version,data,created_at FROM snapshots "
            "WHERE owner_id=%s ORDER BY created_at",
            (actor.id,),
        ).fetchall()
        events = db.execute(
            "SELECT id,action,entity_id,version,created_at FROM audit_events "
            "WHERE owner_id=%s ORDER BY created_at,id",
            (actor.id,),
        ).fetchall()
        response.headers["Content-Disposition"] = 'attachment; filename="jobhunter-export.json"'
        runs = db.execute(
            "SELECT id,operation,model,prompt_version,price_snapshot,status,actual_eur,"
            "reserved_eur,input_tokens,output_tokens,latency_ms,error_code,result,created_at "
            "FROM ai_calls WHERE owner_id=%s ORDER BY created_at",
            (actor.id,),
        ).fetchall()
        return {
            "format_version": "1.0",
            "exported_at": datetime.now(UTC).isoformat(),
            "records": [{**public(r), "kind": r["kind"], "deleted": r["deleted"]} for r in records],
            "snapshots": snapshots,
            "audit_events": events,
            "ai_runs": runs,
            "embedding_index": db.execute(
                "SELECT kind,source_id,source_version,model,chunk,vector,run_id "
                "FROM ai_embeddings WHERE owner_id=%s ORDER BY source_id,chunk",
                (actor.id,),
            ).fetchall(),
        }
