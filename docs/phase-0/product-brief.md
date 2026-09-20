# Product brief — phase 0

Date: 2026-09-19. Status: phase 0 definition consolidated after analysing the CV, supplied preferences and the user's factual confirmation.

## Problem and audience

A person moving into software engineering needs to gather vacancies, assess suitability and tailor applications without losing factual consistency. The initial audience is a candidate for graduate/junior opportunities, prioritising Python/Java backend, then software/full-stack and applied AI. Ireland, particularly Dublin, takes precedence over the United Kingdom. The search targets full-time work, with conditions for starting reviewed separately. Recruiters are the portfolio audience, not MVP users.

The product's main task is to answer: ‘Is this application worth pursuing, based on what I can substantiate and my constraints?’

## Scope by delivery

| Delivery | Included | Success criterion |
|---|---|---|
| Phase 1: local core | Factual profile, companies, text import, structured editing, deterministic scoring, evidence, tracker, local authentication and auditing | A job progresses through import → requirement review → reproducible score → dashboard |
| Phases 2–3: functional MVP | AI parsing, semantic deduplication where useful, CV/cover letter, factual validation and human review | An approved package points to specific evidence versions |
| Phase 4: discovery | Opt-in email and one permitted API connector, company research and alerts | An enabled source produces traceable opportunities |
| Phase 5: temporary AWS demonstration | Reproducible infrastructure, backups, costs and observability | Deployment validated, evidence captured and resources destroyed; everyday use remains local |
| Phase 6: orchestration | One permitted channel or sandbox with final confirmation | No submission without specific, valid approval |

Outside the MVP: multi-tenancy, billing, mobile, dozens of connectors, proprietary models, bulk submission and LinkedIn automation.

## Product constraints

- Job content is untrusted data, never instructions for tools.
- A claim may support a document only if it is verified, current and authorised for that use.
- Unknown data is displayed as unknown. Do not infer work authorisation, sponsorship, salary or experience.
- Disqualifying requirements are assessed separately from the score.
- Sensitive fields require specific review; package approval is not submission approval.
- British English in application documents and all project documentation. This documentation convention was updated on 2026-09-20 at the user's request; technical documentation was originally written in Portuguese. See the [documentation policy](../documentation-policy.md).

## Proposed metrics — no baseline yet

| Metric | Measurement | Proposed initial target |
|---|---|---|
| Active time per analysis | Time 5 manual analyses and 5 using the product, with the same tasks | Reduce the median by 50% |
| Agreement with recommendations | Human review of 20 jobs, recording disagreements | At least 16/20 after calibration |
| Reproducibility | Same profile snapshot, job, weights and algorithm | Identical results |
| Factual document coverage | Factual claims with approved evidence / total claims | 100%; block final generation on failure |
| Improper submissions | Submission without valid approval or duplicate submission | Zero |
| Cost | Token ledger + AWS report per environment | €25/month combined: €15 AWS and €10 AI |

These targets are proposed acceptance criteria, not achieved results. Interview and response rates will be tracked without attributing causality to the score in a small sample.

## Consolidated decisions

Preferences, master CV and budget supplied; the user confirmed that facts and dates are current. Minimum salary and relocation limits remain undefined by explicit choice, without a disqualifying filter. Gmail is the first alert provider, to be integrated only in phase 4. The metrics above are pilot engineering targets; their baselines are still to be measured. See [discovery](discovery.md) and [matching](matching-policy.md).
