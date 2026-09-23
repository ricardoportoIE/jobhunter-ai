# P5 validation record

Date: 23 September 2026. Final corrected cold-start acceptance passed.
All AWS application records are synthetic. Account identifiers, credentials, source
material, Terraform state and recovery dumps remain outside Git.

## Verification results

| Check | Result |
|---|---|
| API and PostgreSQL integration | 165 passed; no skipped tests |
| Frontend components | 31 passed |
| Chromium desktop and mobile journeys | 16 passed, including accessibility checks |
| Cost, reservation, source and controller regressions | 18 passed |
| Host backup/restore failure paths | 7 passed |
| Mocked Terraform plans | 3 passed; no cloud resources created by these tests |
| Python types and API package build | Passed; 74 source files checked |
| Python/frontend lint, formatting and production build | Passed |
| Frozen evaluation contracts and phase-0 design checks | Passed without paid AI calls |
| Documentation | Automated checks passed; authored changes reviewed in British English |
| First live AWS attempt | Workflow, recovery, telemetry and scheduled termination passed after the Buildx correction |
| Corrected cold start | Passed without manual bootstrap intervention |
| Final residual-resource scan | Both attempts clear; all provisioned session resources removed |

The API retains two upstream deprecation warnings from its testing dependencies.
Windows application controls blocked the managed Python interpreter, so API checks
ran in Python 3.13 Linux containers and browser checks used the Playwright Chromium
container. The first container invocation lacked the local runtime database credential;
the corrected test environment passed the full suite. Personal application records
were not used as test fixtures.

The corrected deployment used source commit `2e86e4f`, Terraform 1.16.0 and the
locked AWS provider 6.66.0. Both live attempts recorded successful Scheduler
termination and clear residual scans. The independent export command was also
exercised successfully before the second bucket was removed. The final monetary
reservation remains in the private ledger; cleanup does not erase cost history.

## What the cloud exercise establishes

Terraform provisions a dedicated VPC with no inbound security-group rules, one
`t3.medium` with standard CPU credits and encrypted disposable gp3 storage, narrowly
scoped runtime roles, a private S3 bucket, CloudWatch readiness monitoring and a
Scheduler termination deadline. IMDSv2 is required with a hop limit of one.

The host generates its own credentials, starts the Docker application and seeds a
fictional candidate. The exercise checks denied unauthenticated access, authenticated
profile review, vacancy review, deterministic scoring and shortlisting. It confirms
that Gmail is unconfigured and there are no discovery sources or paid AI calls.

The database backup is uploaded to S3, downloaded again and restored to a separate
scratch database. SHA-256 and record digests must agree before success is recorded.
The controller then exports the recovery artefacts locally and observes a healthy
CloudWatch metric. It advances only that session's Scheduler target and observes
actual instance termination. The independent host timer is checked as armed; it is
not described as having fired during the exercise.

Terraform subsequently removes the remaining session resources. The residual scan
checks live compute, EBS, network resources, snapshots, addresses, the exact bucket,
IAM roles/profile, alarm, log group and schedule. A failed query prevents a clean
result. Historical metric samples can remain under AWS retention rules without an
active host publishing further data.

## Issues found and corrected

The first Amazon Linux bootstrap exposed Docker Buildx 0.12.1, below the minimum
required by Compose. The host was recovered using the verified official Buildx
binary; bootstrap now pins both Compose and Buildx with SHA-256 digests. The selected
releases were Compose v5.5.1 and Buildx v0.37.1.

The initial cleanup removed infrastructure but its verification encountered the
NAT gateway CLI's singular `--filter` argument. Correcting the scanner and repeating
cleanup produced a clear residual report. A regression now covers that argument and
ensures read failures do not become false clean results.

AWS's tagging index briefly retained a terminated instance and deleted volume.
Preflight now confirms their state with EC2 directly. Only confirmed termination or
an explicit not-found response is ignored; unknown resources and denied reads still
block deployment. This is also covered by a regression.

The first GitHub infrastructure job exposed a missing Linux package checksum in the
provider lockfile. The signed HashiCorp checksums are now recorded for both Windows
and Linux amd64; the provider version remains 6.66.0. A clean Linux initialisation,
validation and mocked test run verifies the corrected lockfile without AWS access.

## Cost evidence and limits

Thirteen paid regional SKUs were fetched from AWS Pricing, without free-tier credits.
The quoted `t3.medium` rate was USD 0.0456/hour, public IPv4 USD 0.005/hour and gp3
storage USD 0.088/GB-month. The [runbook](runbook.md) records all cost categories and
conservative workload quantities. These figures are dated quote evidence, not
permanent prices.

Each two-hour attempt was conservatively estimated at **EUR 2.08**. The corrected
attempt reused the first **EUR 5 reservation**, subject to verified cleanup, the
original deadline and a combined estimate of **EUR 4.16**. It did not reset the ledger
or release money. The monthly gate also retained EUR 5 for residual resources and
the full EUR 10 inference envelope.

The operator's USD 1 opening project spend is a declaration, not a billing API
reconciliation. With conservative conversion and contingency, the gate projected
EUR 11.57 against the EUR 15 AWS envelope and EUR 21.57 against EUR 25 combined.
Actual AWS charges may arrive later; these estimates and reservations are not a
final invoice or an AWS-enforced billing cap.

The demonstration does not establish production availability, sustained load capacity,
interactive browser port-forwarding compatibility or cloud AI performance. It leaves
no permanent application URL. Everyday use and personal data remain local.
