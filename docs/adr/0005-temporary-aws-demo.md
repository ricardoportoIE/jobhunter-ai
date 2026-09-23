# ADR-005 — A small, private AWS demonstration

Status: adopted for P5 implementation. Date: 23 September 2026.

## Decision

Use a dedicated Terraform state for each temporary session in `eu-west-1`. A single
Amazon Linux EC2 instance runs the existing Docker application with PostgreSQL on an
encrypted, disposable root volume. A dedicated VPC/security group accepts no inbound
traffic. AWS Systems Manager provides authenticated commands and port forwarding.
The host has a public IPv4 address only for outbound package and AWS API access.

This is a portfolio demonstration with synthetic data, not a production deployment.
The conceptual multi-service architecture in phase 0 remains a possible later design.
RDS, Fargate, Cognito, API Gateway, NAT Gateway and an ALB add integration work and
provisioned costs that are not needed to validate this delivery's acceptance criteria.
The application retains its local authentication behind IAM-controlled SSM access.

Terraform manages the network, encrypted storage, IAM, private S3 artefacts/backups,
CloudWatch health monitoring and an EventBridge Scheduler termination deadline.
An operating-system shutdown timer provides a second termination mechanism. Neither
mechanism guarantees a billing cap: the operator must destroy the complete state and
verify residual resources even after automatic compute termination.

## Data and credentials

Only an explicitly constructed source bundle and synthetic seed data enter AWS.
Local `.env`, CVs, mailbox records, exports, Git history and actual AI/OAuth credentials
are excluded. Remote database and login credentials are generated on the instance;
they are not embedded in Terraform, user data or command output. The remote pilot
does not enable Gmail, paid inference or scheduled discovery of real sources.

SSM uses temporary IAM credentials. Instance metadata requires IMDSv2 with a hop
limit of one, so application containers cannot retrieve the instance role. The role
can read its source bundle, write its backup prefix and publish bounded operational
telemetry. Root storage is deleted when the instance terminates. Backups are copied
to private local storage before the session bucket is destroyed.

## Cost and lifecycle controls

Retain the existing EUR 15 AWS and EUR 10 AI monthly envelopes. A session reserves
EUR 5 plus the separate EUR 5 monthly residual-resource allowance. Quotes and spending
evidence must be current and complete before apply. Unknown values, stale evidence,
an unsettled active session or insufficient budget block new deployment. Free-tier
credits are not part of the estimate. The initial live exercise targets two hours;
eight hours is the maximum permitted session duration.

The local controller binds the reservation to the AWS account, region, source digest,
Terraform plan and session state. Reservations persist across failures. Teardown and
export remain available when the spending gate is closed. Destroy is restricted to
the selected session; it must not alter unrelated resources or the local application.

## Acceptance evidence

Validate a fresh deployment, private access, synthetic application flow, database
backup/restore, health telemetry, deadline configuration and complete teardown.
Record actual outcomes separately from offline tests. Missing AWS access or reliable
cost information leaves live acceptance pending rather than claiming completion.

## References

- [SSM Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html)
- [Instance-initiated termination](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Using_ChangingInstanceInitiatedShutdownBehavior.html)
- [Scheduler universal targets](https://docs.aws.amazon.com/scheduler/latest/UserGuide/managing-targets-universal.html)
- [Instance metadata and user data](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-metadata.html)
- [Existing budget decision](0004-local-first-budget.md)
