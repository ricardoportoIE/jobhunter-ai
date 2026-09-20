# ADR-004 — Local development and temporary AWS environments

Status: adopted for phase 1 based on the supplied preferences. Date: 2026-09-19.

The combined budget is €25/month: up to €15 for AWS and €10 for inference. The permanent production topology originally described cannot safely fit within this limit. The product will run locally; AWS will initially support reproducible temporary demonstrations and validation.

## Decision

Phase 1 uses no cloud services or LLM. Phases 2–3 use inference only within budget. Phase 5 creates temporary environments, captures anonymised technical evidence, exports necessary data and destroys project resources with Terraform after each session. RDS, ECS, NAT Gateway and ALB do not remain active by default. Never destroy resources outside the selected Terraform workspace/state.

Plan up to two eight-hour sessions per month, with an initial maximum AWS reservation of €5 per session and €5 for storage, logs, residual resources and monthly contingency. The preflight must use current quotes for all resources; if a session exceeds its reservation, reduce the topology or do not deploy. The time limit is a control mechanism, not a price guarantee.

Set alerts at 50%, 80% and 100% for each sub-budget and the combined budget. Block new paid calls and new applies when confirmed cost + reservations + maximum estimated cost would exceed a limit. Unknown spending or stale billing information prevents new allocation. Destruction, export and actions needed to shut down resources remain permitted after the limit is reached.

AWS Budgets may notify late, and existing resources continue to incur charges. Protection requires preflight checks, atomic reservations, TTL and verifiable clean-up; do not promise an AWS-enforced hard billing cap. No infrastructure or operational blocking controls are implemented in this phase.

## Consequences

The baseline has no AWS service available 24/7. Personal data and canonical state remain local; cloud demonstrations use synthetic seed data wherever possible. Portfolio evidence records infrastructure that was actually validated and then removed, without advertising a permanent URL. Continuous deployment would require a new budget and ADR.
