# P5 — Temporary AWS demonstration

Every stage receives a local commit after its checks. Push follows final review.
All cloud resources are temporary; everyday use and personal records remain local.

| Stage | Scope | Status |
|---|---|---|
| P5-01 | Architecture, budget and acceptance boundaries | Defined |
| P5-02 | Terraform, isolation and termination controls | Implemented; validation and two mocked plans passed |
| P5-03 | Bootstrap, synthetic workflow, backup/restore and telemetry | Implemented; local workflow and seven failure-path checks passed; AWS checks pending |
| P5-04 | Cost gate, session controller and automated checks | Implemented; twelve offline regression checks passed |
| P5-05 | Live exercise, evidence, verified teardown and final review | Pending |

The concrete topology and trade-offs are in [ADR-005](../adr/0005-temporary-aws-demo.md).
The operator selected the `portfolio` AWS profile and reported USD 1 of project AWS
spending for the current month. This is operator-supplied evidence, not a billing API
reconciliation. Prices, current account identity and any existing resources must still
be checked before reserving a session. No actual account identifiers or credentials
belong in public reports.

The authenticated profile has PowerUserAccess plus the scoped additional policy
applied by the operator. The previously refused IAM read is now authorised. The
account-specific copy is private; the reviewable template is
`infra/p5/operator-iam-policy.template.json`. No role or cloud resource was created
during the mocked Terraform tests. Both roles carry a PowerUserAccess permissions
boundary in addition to their narrower runtime policies.

## Local runtime evidence

`python scripts/check_p5_local.py` built a disposable Compose project with newly
generated credentials and synthetic records. Authentication, profile review, vacancy
review, deterministic analysis and shortlisting passed twice. A PostgreSQL dump was
restored into a separate scratch database, with matching file and record digests.
The test removed its containers, network and volume in a `finally` block. Existing
local application data was not used. Object transfer used a local file substitute:
this does not establish that S3 permissions, SSM access or CloudWatch work in AWS.

Seven offline host tests cover session isolation, a changing database during backup,
corrupt downloads, failed restore cleanup and data verification before success is
reported. Terraform's two mocked plans also passed after release-tag validation was
added. The live cloud checks remain part of P5-05.

The [session runbook](runbook.md) describes immutable source/plan inputs, current SKU
quotes, atomic reservations and automatic cleanup. Twelve regression tests cover
unknown/stale costs, competing reservations, monthly carry-over, changed plans,
source exclusions and cleanup after a failed apply. CI also exercises the local
synthetic runtime and the mocked Terraform plans without cloud credentials.
