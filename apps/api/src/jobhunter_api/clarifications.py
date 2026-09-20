"""Version-bound clarification gates; unresolved uncertainty cannot select an optimistic result."""

import re
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import Field

from jobhunter_api.auth import Actor, settings_for
from jobhunter_api.deduplication import fingerprint
from jobhunter_api.errors import Problem
from jobhunter_api.profile import Input
from jobhunter_api.records import get_record, list_records, profile, public
from jobhunter_api.store import Connection, Row, connect

router = APIRouter(prefix="/api/v1/jobs", tags=["clarifications"])


class Resolution(Input):
    key: str = Field(min_length=64, max_length=64)
    note: str = Field(min_length=20, max_length=3000)
    source_reference: str = Field(min_length=5, max_length=2000)


def source_conflicts(job: Row) -> list[Row]:
    issues = []
    title, raw = job.get("title") or "", job.get("raw_text") or ""
    junior_title = bool(re.search(r"\b(junior|graduate|intern|jr)\b", title, re.I))
    senior_body = bool(
        re.search(
            r"senior.only|exclusively senior|senior position|senior role|no junior (route|opening)",
            raw,
            re.I,
        )
    )
    data_body = bool(
        re.search(r"(body|description|role)[:\s].{0,70}graduate data engineer", raw, re.I)
    )
    if junior_title and (senior_body or ("software" in title.casefold() and data_body)):
        issues.append(
            {
                "code": "TITLE_BODY_CONFLICT",
                "requirement_id": None,
                "message": "Título e descrição divergem. Confirme a função e o nível da vaga.",
            }
        )
    for flag in job.get("risk_flags", []):
        if re.search(r"conflict|contrad|diverg|inconsisten", flag, re.I):
            issues.append({"code": "JOB_CONTRADICTION", "requirement_id": None, "message": flag})
    if re.search(
        r"ignore (all |prior |previous )?instructions|system override|ignore instru", raw, re.I
    ):
        issues.append(
            {
                "code": "UNTRUSTED_INSTRUCTIONS",
                "requirement_id": None,
                "message": "Há comandos dirigidos à IA no anúncio. Confira os requisitos na fonte.",
            }
        )
    return issues


def current_runs(db: Connection, owner: UUID, job: Row, candidate: Row) -> list[Row]:
    rows = db.execute(
        "SELECT id,model,result,operation FROM ai_calls WHERE owner_id=%s "
        "AND operation IN ('suggest','suggest_review') AND status='succeeded' "
        "AND result->>'job_id'=%s AND result->>'job_version'=%s "
        "AND result->>'profile_version'=%s ORDER BY created_at DESC LIMIT 30",
        (owner, job["id"], str(job["version"]), str(candidate["version"])),
    ).fetchall()
    versions = {
        str(r["id"]): r["version"]
        for kind in ("fact", "evidence")
        for r in list_records(db, owner, kind)
    }
    return [
        r
        for r in rows
        if all(
            versions.get(item["id"]) == item.get("version")
            for kind in ("facts", "evidence")
            for item in r["result"].get("input_snapshot", {}).get(kind, [])
        )
    ]


def collect(
    db: Connection, owner: UUID, job: Row, candidate: Row, assessments: list[Row] | None = None
) -> list[Row]:
    issues = source_conflicts(job)
    groups: dict[str, list[Row]] = {}
    for run in current_runs(db, owner, job, candidate):
        result = run["result"]
        issues.extend(
            {
                "code": issue["kind"],
                "requirement_id": issue["requirement_id"],
                "message": issue["explanation"],
                "fact_ids": issue["fact_ids"],
            }
            for issue in result.get("clarifications", [])
        )
        group = result.get("comparison_key", fingerprint(result.get("input_snapshot", {})))
        groups.setdefault(group, []).append(run)
    for runs in groups.values():
        for req in job["requirements"]:
            answers = [
                {
                    "run_id": str(run["id"]),
                    "model": run["model"],
                    "status": item["status"],
                    "reason": item["reason"],
                }
                for run in runs
                for item in run["result"]["assessments"]
                if item["requirement_id"] == req["id"]
            ]
            if len({a["status"] for a in answers}) > 1:
                issues.append(
                    {
                        "code": "ASSESSMENT_DISAGREEMENT",
                        "requirement_id": req["id"],
                        "message": "As avaliações divergem sobre as mesmas evidências. Esclareça.",
                        "alternatives": answers,
                    }
                )
    if assessments is not None:
        by_id = {a["requirement_id"]: a for a in assessments}
        for req in job["requirements"]:
            if (
                req["is_eliminatory"]
                and by_id.get(req["id"], {}).get("status", "unknown") in {"unknown", "partial"}
                and not (
                    req.get("future_authorisation")
                    and req["category"] == "work_authorisation_hours"
                )
            ):
                issues.append(
                    {
                        "code": "DECISIVE_INFORMATION_MISSING",
                        "requirement_id": req["id"],
                        "message": "Requisito eliminatório ainda não confirmado: " + req["text"],
                    }
                )
    unique = {}
    for issue in issues:
        key = fingerprint(
            {
                "job_id": job["id"],
                "job_version": job["version"],
                "profile_version": candidate["version"],
                "code": issue["code"],
                "requirement_id": issue["requirement_id"],
                "fact_ids": sorted(issue.get("fact_ids", [])),
                "alternatives": issue.get("alternatives", []),
            }
        )
        unique[key] = {**issue, "key": key}
    return list(unique.values())


def apply_gate(result: Row, issues: list[Row], resolutions: list[Resolution], actor: UUID) -> None:
    known = {i["key"] for i in issues}
    if len({r.key for r in resolutions}) != len(resolutions) or any(
        r.key not in known for r in resolutions
    ):
        raise Problem(
            409, "CLARIFICATIONS_CHANGED", "Atualize os esclarecimentos antes de confirmar."
        )
    resolved = {r.key for r in resolutions}
    pending = [
        issue
        for issue in issues
        if issue["key"] not in resolved or issue["code"] == "DECISIVE_INFORMATION_MISSING"
    ]
    result["clarifications"] = pending
    result["clarification_resolutions"] = [
        {**r.model_dump(), "reviewed_by": str(actor)} for r in resolutions
    ]
    if pending:
        if result["recommendation"] != "BLOCKED":
            result["recommendation"] = "REVIEW"
        result["review_flags"] = list(
            dict.fromkeys([*result["review_flags"], "CLARIFICATION_REQUIRED"])
        )


@router.get("/{job_id}/clarifications")
def pending(job_id: UUID, actor: Actor, request: Request) -> list[Row]:
    with connect(settings_for(request)) as db:
        job = public(get_record(db, actor.id, "job", job_id))
        candidate = public(profile(db, actor.id))
        return collect(db, actor.id, job, candidate)
