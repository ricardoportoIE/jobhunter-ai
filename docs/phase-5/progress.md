# P5 — Temporary AWS demonstration

Every stage receives a local commit after its checks. Push follows final review.
All cloud resources are temporary; everyday use and personal records remain local.

| Stage | Scope | Status |
|---|---|---|
| P5-01 | Architecture, budget and acceptance boundaries | Defined |
| P5-02 | Terraform, isolation and termination controls | Implemented; validation and two mocked plans passed |
| P5-03 | Bootstrap, synthetic workflow, backup/restore and telemetry | In progress |
| P5-04 | Cost gate, session controller and automated checks | Pending |
| P5-05 | Live exercise, evidence, verified teardown and final review | Pending |

The concrete topology and trade-offs are in [ADR-005](../adr/0005-temporary-aws-demo.md).
The operator selected the `portfolio` AWS profile and reported USD 1 of project AWS
spending for the current month. This is operator-supplied evidence, not a billing API
reconciliation. Prices, current account identity and any existing resources must still
be checked before reserving a session. No actual account identifiers or credentials
belong in public reports.

The authenticated profile currently has PowerUserAccess. AWS refused an IAM role
read, so an administrator must apply the narrowly scoped additional policy before
live deployment. The account-specific copy is private; the reviewable template is
`infra/p5/operator-iam-policy.template.json`. No role or cloud resource was created
during the mocked Terraform tests. Both roles carry a PowerUserAccess permissions
boundary in addition to their narrower runtime policies.
