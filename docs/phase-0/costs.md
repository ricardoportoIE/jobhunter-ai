# Final phase 0 budget

Defined on 2026-09-19: **€25 per month combined, up to €15 for AWS and €10 for inference**. These limits include allowances for tax, exchange rates, retries and residual charges. No paid service was activated.

## Baseline within budget

| Stage | AWS | Inference | Condition |
|---|---:|---:|---|
| Local phase 1 | €0 | €0 | No cloud resources or LLM |
| Local phases 2–3 | €0 by default | Up to €10/month | Benchmark and usage ledger before calls |
| AWS validation sessions | Reservation of up to €5/session, two sessions/month | Within the same €10 | Quote approved by preflight and TTL of at most 8h |
| Residual resources, logs, storage and AWS allowance | €5/month reservation | — | Total AWS authorisation never exceeds €15 |

Reservations are project authorisation limits, not guaranteed topology prices. The baseline has no 24/7 AWS environment. If the regional quote exceeds the reservation, reduce the environment or run locally only. See [ADR-004](../adr/0004-local-first-budget.md).

## Inference estimate

Reference volume: 300 analyses/month with 4,000 input tokens and 1,000 output tokens per analysis; 30 packages with 10,000 input and 3,000 output tokens per package. Total: 1.5 million input and 0.39 million output tokens, counting all calls within each task.

Using the consulted reference rate for Haiku 4.5 through the direct API, US$1/M input and US$5/M output, the calculation is `1.5 × 1 + 0.39 × 5 = US$3.45`. Adding 30% for retries/validation gives US$4.49. This is a scenario, not a provider selection; it excludes paid web research or additional context. [Official rate](https://platform.claude.com/docs/en/about-claude/pricing).

For budget reservations, provisionally use conservative parity of US$1=€1 as a **planning parameter, not an exchange-rate quote**, plus a 30% tax/currency allowance: approximately €5.84. Replace this with actual exchange rates and taxes during preflight. Actual charges and reservations take precedence over this approximation. The €10 limit does not authorise unlimited agent calls.

## Temporary AWS estimate

Scenario: up to 8h of a small Single-AZ database, temporary API and network; occasional document tasks; low log and storage volumes. For planning, reserve €0.40/h for compute+network, €0.80 for session storage/requests/residual resources and 25% contingency: `(8 × 0.40 + 0.80) × 1.25 = €5`. The aggregate rate is a conservative assumption to validate, not a quoted regional price. Two sessions reserve €10, leaving €5 for additional AWS costs.

Before any apply, export a quote by SKU in eu-west-1: RDS+storage/backups, Fargate/Lambda, networking/NAT or endpoints, IP addresses, any ALB, logs, Secrets Manager, S3, ECR and transfer. The complete topology may exceed €5 and must then be reduced. Do not rely on a free tier, credits or a chat subscription.

A stopped RDS instance still incurs storage charges; NAT and other provisioned resources incur charges while they exist. Destroying compute alone does not prove that spending has ended. References: [RDS](https://aws.amazon.com/rds/postgresql/pricing/), [VPC](https://aws.amazon.com/vpc/pricing/), [Fargate](https://aws.amazon.com/fargate/pricing/), [Lambda](https://aws.amazon.com/lambda/pricing/). Regional prices will be revalidated at deployment time.

## Spending interruption policy

Alerts at 50/80/100%: combined €12.50/€20/€25, AWS €7.50/€12/€15 and AI €5/€8/€10. Before an operation, check `confirmed spending + open reservations + maximum projected cost`. Block if any applicable limit would be exceeded. Missing reliable data blocks new spending; manual reviews do not automatically reset the counter.

A billing alarm may arrive late and does not shut down existing resources. The design requires atomic reservations, token/call limits, TTL, teardown and residual resource checks. At €25, block new deployments and paid inference; continue allowing exports and actions that stop costs. These protections still need implementation in their respective phases.

After each session: save anonymised technical evidence, export necessary data, destroy the correct Terraform workspace, check RDS/ECS/NAT/ALB/IPs/endpoints/snapshots and update the ledger. Canonical personal state remains local.
