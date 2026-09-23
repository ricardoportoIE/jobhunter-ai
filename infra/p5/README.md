# Temporary AWS infrastructure

This module belongs to the [P5 demonstration](../../docs/adr/0005-temporary-aws-demo.md).
Use the session controller and its reviewed cost inputs for a live session. Direct
Terraform commands bypass local budget reservations and are for validation only.
The local backend state, plans, generated variables and artefacts must stay in `.private/`.

```powershell
terraform -chdir=infra/p5 init -backend=false
terraform -chdir=infra/p5 validate
terraform -chdir=infra/p5 test
```

The committed tests use a mocked AWS provider and plan-only runs. They do not create
cloud resources or require credentials. Do not add an unmocked apply run to CI.
The dependency lockfile fixes the provider selected during validation.

The operator needs an authenticated AWS profile and permission to create the scoped
session resources. PowerUserAccess alone lacks the required IAM operations. An
administrator can review `operator-iam-policy.template.json`, replace `ACCOUNT_ID`
with the intended account and add it to the relevant permission set. The added
permissions are restricted to `jobhunter-p5-*` roles/profiles, the SSM core policy,
the required service principals and a PowerUserAccess boundary for new roles.

An IPv4 address is used only for outbound HTTPS. The security group has no inbound
rules. Access through SSM remains private even though the host has outbound internet
connectivity. EBS and S3 are encrypted; S3 public access is blocked. Each session has
an AWS termination schedule and an operating-system timer. These stop compute but
do not remove every resource: complete Terraform teardown and a residual scan are
mandatory. No production availability or hard AWS billing cap is claimed.

## Host checks

```powershell
python -m unittest discover -s infra/p5/host -p "test_*.py"
python scripts/check_p5_local.py
```

The second command requires Docker and unused local ports 15173, 18000 and 15433.
It builds a separate Compose project with fictional records, exercises the host's
application and PostgreSQL recovery operations, then removes that project's volumes
and containers. Private results stay beneath `.private/p5/`. S3 transfer is replaced
with local file copying in this check; AWS integration still needs a live session.
