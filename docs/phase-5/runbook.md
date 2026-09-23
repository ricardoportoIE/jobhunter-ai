# Temporary AWS session runbook

P5 deploys an isolated synthetic demonstration, checks it and destroys it in one
controlled run. It does not publish a permanent website. Read
[ADR-005](../adr/0005-temporary-aws-demo.md) before changing the topology.

## Prerequisites

- Python 3.13 or later, Git, AWS CLI v2 and Terraform 1.16.0.
- A clean, reviewed Git commit. Only allowlisted files from that commit are uploaded.
- An authenticated AWS profile with the scoped IAM permissions described in the
  [infrastructure guide](../../infra/p5/README.md).
- Known current-month project AWS spending, checked within the preceding 24 hours,
  including any existing resources. Record the actual time and source of the evidence.

The CLI isolates Terraform state beneath `.private/p5/sessions/`. Keep that directory
and the SQLite ledger: deleting them discards the local record of reservations and
resources. They are private operational state, not portfolio material. Never copy the
local application `.env`, credentials, CVs or mailbox records into a session.

## Prepare, inspect and run

Replace the example spending amount, timestamp, reference and profile with verified
values. `prepare` performs read-only AWS calls and creates a local saved Terraform
plan. It does not reserve money or create cloud resources.

```powershell
python scripts/p5.py prepare --profile portfolio --hours 2 --spending-usd 1 --spending-checked-at "2026-09-23T12:00:00+00:00" --spending-reference "Operator-confirmed project spending, including existing resources"
```

Review the generated session's `quote.json`, `spending.json`, `variables.json` and
private `terraform.log`. Keep the reported session identifier for recovery:

```powershell
python scripts/p5.py run p5-012345abcdef
```

`run` verifies the account and input digests, reserves EUR 5 atomically, applies only
the saved plan and tests private SSM access, synthetic application behaviour, a
database backup/restoration and CloudWatch readiness. It exports the synthetic dump
and reports locally. It then advances that session's termination schedule to exercise
actual AWS termination. The operating-system timer is checked separately as armed;
the controller does not claim that both timers fired.

A `finally` block attempts full Terraform teardown even after failed apply or failed
checks. A process crash, interrupted network connection or expired AWS session can
still prevent cleanup. The cloud and host timers terminate compute but cannot remove
all residual resources. Reauthenticate if needed and recover with:

```powershell
python scripts/p5.py destroy p5-012345abcdef
```

Destroy is available even when quotes are stale or the budget is exhausted. It uses
only the selected session state and checks residual resources by exact names and
session tags. Any failed query or remaining resource prevents a clean result.
Historical CloudWatch metric samples may remain under AWS retention rules; no further
custom metric publishing continues after the host is terminated.

## Budget interpretation

The quote retrieves 13 paid SKUs directly from AWS Pricing in `eu-west-1`: compute,
gp3 storage, public IPv4, S3 storage and requests, CloudWatch logs/storage/metric/alarm
and API requests, Scheduler invocations and outbound transfer. A missing SKU, wrong
unit or stale quote blocks allocation. Free-tier prices and credits are ignored.

The closed plan has one `t3.medium`, 24 GB of gp3 and no inbound access. Pricing uses
the entire requested session duration, one GB each for object storage, logs and
outbound transfer, full-month storage/metric/alarm charges, 1,000 S3 PUT and GET
requests, 10,000 CloudWatch requests and ten Scheduler invocations. These are
conservative workload allowances, not AWS-enforced traffic limits. Unexpected use
can still exceed an estimate. No NAT Gateway, load balancer, RDS, customer-managed
KMS key or paid AI call is provisioned. Standard SSM EC2 Session Manager/Run Command,
IAM and the dedicated VPC have no additional provisioned charge in this topology.

For accounting, USD amounts use EUR 1.25 per USD plus 25% contingency. These are
conservative planning parameters, not a live foreign-exchange quote. The gate keeps
the EUR 5 monthly residual allowance and the full EUR 10 inference envelope reserved,
and emits threshold notices at 50%, 80% and 100%. The existing local AI gate remains
responsible for inference spending. No notification email is sent.

Current-month reservations remain counted after teardown because billing is delayed.
There is deliberately no command to reset them. Existing spending plus reservations
may allow fewer than two sessions. Unknown spending blocks new allocation; an
operator declaration is labelled as such and is not a billing API reconciliation.

One sequential cold-start retry may use `prepare --reuse-reservation <session>` with
the other preparation arguments. This requires verified cleanup of the first attempt,
fresh evidence, the same account and a deadline no later than the original deadline.
Both conservative attempt estimates must fit the existing EUR 5 reservation. The
retry counts towards the two-attempt monthly limit, cannot itself be retried and does
not release or reset money. Its separate state and artefacts preserve both attempts.

Compose and Buildx are both pinned to official release digests. The first live test
exposed an older Buildx in Amazon Linux's Docker package; explicitly installing the
verified Buildx binary is now part of bootstrap rather than relying on that package.

## Evidence and validation

Offline checks run in CI without AWS credentials. `check_p5_local.py` validates the
Docker/PostgreSQL workflow using a local substitute for S3. Only a live session can
establish that IAM, SSM, S3, telemetry and scheduled termination actually work.

Private live artefacts include `acceptance.json`, `backup.json`, `restore.json`,
`health.json`, `residuals.json` and the synthetic database dump. Publish only an
editorially reviewed, anonymised report with actual outcomes and limitations.

Pricing references: [AWS Pricing API](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/price-changes.html),
[EC2](https://aws.amazon.com/ec2/pricing/on-demand/),
[VPC](https://aws.amazon.com/vpc/pricing/), [S3](https://aws.amazon.com/s3/pricing/),
[CloudWatch](https://aws.amazon.com/cloudwatch/pricing/),
[EventBridge](https://aws.amazon.com/eventbridge/pricing/) and
[Systems Manager](https://aws.amazon.com/systems-manager/pricing/).
