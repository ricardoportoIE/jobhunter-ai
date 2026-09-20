"""Pure scoring v0.2: explicit assessments, verified evidence and decimal half-up math."""

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

type Document = dict[str, Any]
WEIGHTS = {
    "technical_skills": 30,
    "seniority_experience": 20,
    "portfolio": 15,
    "education": 10,
    "location_work_mode": 10,
    "salary": 5,
    "work_authorisation_hours": 5,
    "career_value": 5,
}
VALUES = {"met": Decimal(1), "partial": Decimal("0.5"), "unmet": Decimal(0)}
ALGORITHM = "deterministic-manual-0.2.0"


def rounded(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def eligible(
    fact: Document, evidence: dict[str, Document], at: datetime, use: str = "matching"
) -> bool:
    if fact.get("status") != "verified" or use not in fact.get("allowed_uses", []):
        return False
    if not fact.get("reviewed_at") or not fact.get("reviewed_by") or not fact.get("evidence_ids"):
        return False
    for key, direction in (("valid_from", "start"), ("valid_until", "end")):
        if fact.get(key):
            instant = datetime.fromisoformat(fact[key].replace("Z", "+00:00"))
            if (direction == "start" and at < instant) or (direction == "end" and at >= instant):
                return False
    return all(
        identity in evidence
        and evidence[identity].get("reviewed_at")
        and fact.get("evidence_versions", {}).get(identity) == evidence[identity]["version"]
        for identity in fact["evidence_ids"]
    )


def evaluate(
    job: Document, snapshot: Document, assessments: list[Document], at: datetime
) -> Document:
    requirements = job["requirements"]
    requirements_by_id = {r["id"]: r for r in requirements}
    if len({a["requirement_id"] for a in assessments}) != len(assessments):
        raise ValueError("Duplicate assessment")
    if any(a["requirement_id"] not in requirements_by_id for a in assessments):
        raise ValueError("Unknown requirement")
    facts = {f["id"]: f for f in snapshot["facts"]}
    evidence = {e["id"]: e for e in snapshot["evidence"]}
    decisions = {a["requirement_id"]: a for a in assessments}
    breakdown: list[Document] = []
    blockers: list[Document] = []
    gaps: list[Document] = []
    flags = list(job.get("risk_flags", []))
    effective_total, achieved_total = Decimal(0), Decimal(0)
    unknown_eliminatory = False
    auth_known, auth_blocked = False, False
    if job.get("sponsorship") is None:
        flags.append("SPONSORSHIP_UNKNOWN")
    if (job.get("seniority") or "").strip().casefold() in {
        "senior",
        "lead",
        "principal",
        "staff",
        "manager",
        "head",
        "architect",
    }:
        blockers.append(
            {
                "requirement_id": None,
                "reason": "Nível avançado confirmado na revisão da vaga.",
                "fact_ids": [],
                "evidence_ids": [],
            }
        )
        flags.append("SENIORITY_EXCLUDED")
    for category, weight in WEIGHTS.items():
        applicable, known, achieved = Decimal(0), Decimal(0), Decimal(0)
        details = []
        for req in requirements:
            if req["category"] != category:
                continue
            internal = Decimal(2 if req["importance"] == "required" else 1)
            applicable += internal
            assessment = decisions.get(req["id"], {})
            outcome = assessment.get("status", "unknown")
            fact_ids = assessment.get("fact_ids", [])
            reason = assessment.get("reason", "Sem avaliação confirmada.")
            if any(identity not in facts for identity in fact_ids):
                raise ValueError("Unknown or foreign fact")
            linked_evidence = sorted(
                {eid for fid in fact_ids for eid in facts[fid]["evidence_ids"]}
            )
            if (
                outcome in {"met", "partial"}
                and category != "career_value"
                and (
                    not fact_ids or not all(eligible(facts[fid], evidence, at) for fid in fact_ids)
                )
            ):
                outcome = "unknown"
                reason = "A avaliação positiva não tem fatos válidos para matching. " + reason
                flags.append("FACT_NOT_ELIGIBLE")
            if outcome not in {"met", "partial", "unmet", "unknown"}:
                raise ValueError("Invalid assessment status")
            if outcome != "unknown":
                known += internal
                achieved += internal * VALUES[outcome]
            if outcome in {"unknown", "unmet", "partial"}:
                gaps.append(
                    {
                        "requirement_id": req["id"],
                        "text": req["text"],
                        "status": outcome,
                        "reason": reason,
                    }
                )
            if req["is_eliminatory"]:
                if outcome == "unmet":
                    blockers.append(
                        {
                            "requirement_id": req["id"],
                            "reason": reason,
                            "fact_ids": fact_ids,
                            "evidence_ids": linked_evidence,
                        }
                    )
                    auth_blocked |= category == "work_authorisation_hours"
                elif outcome == "unknown" and not (
                    category == "work_authorisation_hours" and req.get("future_authorisation")
                ):
                    unknown_eliminatory = True
            details.append(
                {
                    "requirement_id": req["id"],
                    "status": outcome,
                    "reason": reason,
                    "fact_ids": fact_ids,
                    "evidence_ids": linked_evidence,
                    "importance_weight": int(internal),
                }
            )
        coverage = known / applicable if applicable else Decimal(0)
        attainment = achieved / known if known else None
        effective = Decimal(weight) * coverage
        effective_total += effective
        achieved_total += effective * attainment if attainment is not None else Decimal(0)
        if category == "work_authorisation_hours":
            auth_known = bool(applicable and known == applicable and achieved == known)
        breakdown.append(
            {
                "category": category,
                "weight": weight,
                "coverage": rounded(coverage),
                "attainment": rounded(attainment) if attainment is not None else None,
                "effective_weight": rounded(effective),
                "assessments": details,
            }
        )
    score = rounded(100 * achieved_total / effective_total) if effective_total else None
    coverage_total = effective_total / 100
    if blockers:
        recommendation = "BLOCKED"
    elif unknown_eliminatory or coverage_total < Decimal("0.70") or score is None:
        recommendation = "REVIEW"
    elif score >= 85:
        recommendation = "PRIORITISE"
    elif score >= 70:
        recommendation = "APPLY_AFTER_REVIEW"
    elif score >= 55:
        recommendation = "REVIEW"
    else:
        recommendation = "TRACK_OR_ARCHIVE"
    return {
        "algorithm_version": ALGORITHM,
        "weights_version": "0.2.0",
        "score": score,
        "coverage": rounded(coverage_total),
        "recommendation": recommendation,
        "breakdown": breakdown,
        "blockers": blockers,
        "gaps": gaps,
        "employment_gate": "BLOCKED"
        if auth_blocked
        else "READY_WITHIN_CONFIRMED_LIMITS"
        if auth_known
        else "REVIEW_BEFORE_START",
        "review_flags": sorted(set(flags)),
        "created_at": at.isoformat(),
        "explanation": "Cálculo das avaliações explícitas; cobertura mede os dados conhecidos.",
    }
