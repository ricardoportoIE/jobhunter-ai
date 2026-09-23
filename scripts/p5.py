"""Prepare and exercise a private, disposable AWS demo with automatic cleanup."""

import argparse
import concurrent.futures
import hashlib
import io
import json
import os
import re
import secrets
import subprocess
import tarfile
import time
from datetime import timedelta
from pathlib import Path
from urllib.request import Request, urlopen

import p5_costs as costs

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / ".private/p5"
REGION = "eu-west-1"
MODULE_FILES = (
    "main.tf",
    "variables.tf",
    "versions.tf",
    "outputs.tf",
    "bootstrap.sh.tftpl",
    ".terraform.lock.hcl",
)
RESOURCES = {
    "aws_vpc.demo",
    "aws_subnet.demo",
    "aws_internet_gateway.demo",
    "aws_route_table.demo",
    "aws_route_table_association.demo",
    "aws_security_group.demo",
    "aws_s3_bucket.session",
    "aws_s3_bucket_public_access_block.session",
    "aws_s3_bucket_server_side_encryption_configuration.session",
    "aws_s3_bucket_policy.session",
    "aws_s3_object.bundle",
    "aws_iam_role.host",
    "aws_iam_role.expiry",
    "aws_iam_role_policy_attachment.ssm",
    "aws_iam_role_policy.host",
    "aws_iam_role_policy.expiry",
    "aws_iam_instance_profile.host",
    "aws_cloudwatch_log_group.demo",
    "aws_cloudwatch_metric_alarm.health",
    "aws_instance.demo",
    "aws_scheduler_schedule.expiry",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)


def environment(profile):
    result = {k: v for k, v in os.environ.items() if not k.startswith(("AWS_", "TF_"))}
    result.update(
        AWS_PROFILE=profile,
        AWS_DEFAULT_REGION=REGION,
        AWS_PAGER="",
        AWS_CLI_OUTPUT_ENCODING="UTF-8",
        AWS_CLI_FILE_ENCODING="UTF-8",
    )
    return result


def aws(profile, *arguments, region=REGION, absent=()):
    result = subprocess.run(
        [
            "aws",
            *arguments,
            "--profile",
            profile,
            "--region",
            region,
            "--output",
            "json",
            "--no-cli-pager",
        ],
        capture_output=True,
        timeout=90,
        check=False,
        env=environment(profile),
    )
    if result.returncode:
        found = re.search(rb"\(([A-Za-z0-9_.-]+)\) when calling", result.stderr)
        code = found[1].decode() if found else "CLIError"
        if code in absent:
            return None
        # Provider messages may contain account details; keep terminal output concise.
        raise RuntimeError(f"AWS {arguments[0]} {arguments[1]} failed: {code}")
    return json.loads(result.stdout) if result.stdout.strip() else {}


def identity(profile):
    return aws(profile, "sts", "get-caller-identity")["Account"]


def live_tagged_resources(profile, account):
    """Resolve stale EC2 tag-index entries against the authoritative service API."""
    resources = aws(
        profile,
        "resourcegroupstaggingapi",
        "get-resources",
        "--tag-filters",
        "Key=Project,Values=jobhunter-ai",
    )["ResourceTagMappingList"]
    active = []
    for resource in resources:
        prefix = f"arn:aws:ec2:{REGION}:{account}:"
        arn = resource["ResourceARN"]
        if arn.startswith(prefix + "instance/"):
            result = aws(
                profile,
                "ec2",
                "describe-instances",
                "--instance-ids",
                arn.rsplit("/", 1)[1],
                absent=("InvalidInstanceID.NotFound",),
            )
            if result is None or all(
                i["State"]["Name"] == "terminated"
                for r in result["Reservations"]
                for i in r["Instances"]
            ):
                continue
        elif arn.startswith(prefix + "volume/"):
            if (
                aws(
                    profile,
                    "ec2",
                    "describe-volumes",
                    "--volume-ids",
                    arn.rsplit("/", 1)[1],
                    absent=("InvalidVolume.NotFound",),
                )
                is None
            ):
                continue
        active.append(resource)
    return active


def allowed_source(name):
    exact = {
        "compose.yaml",
        ".env.example",
        "scripts/init_env.py",
        "infra/p5/host/start.sh",
        "infra/p5/host/operations.py",
        "apps/api/Dockerfile",
        "apps/api/.dockerignore",
        "apps/api/pyproject.toml",
        "apps/api/uv.lock",
        "apps/web/Dockerfile",
        "apps/web/.dockerignore",
        "apps/web/package.json",
        "apps/web/package-lock.json",
        "apps/web/index.html",
        "apps/web/tsconfig.json",
        "apps/web/vite.config.ts",
        "apps/web/nginx.conf",
    }
    if name in exact:
        return True
    parts = Path(name).parts
    return (
        name.startswith(("apps/api/src/", "apps/web/src/"))
        and not any(part.startswith(".") or part == "__pycache__" for part in parts)
        and Path(name).suffix in {".py", ".sql", ".ts", ".tsx", ".css", ".json"}
    )


def bundle(destination, revision):
    names = (
        subprocess.check_output(["git", "ls-tree", "-r", "--name-only", revision], cwd=ROOT)
        .decode()
        .splitlines()
    )
    selected = [name for name in names if allowed_source(name)]
    raw = subprocess.check_output(["git", "archive", "--format=tar", revision, *selected], cwd=ROOT)
    with (
        tarfile.open(fileobj=io.BytesIO(raw)) as source,
        tarfile.open(destination, "w:gz") as target,
    ):
        for member in source:
            if member.isdir():
                continue
            if not member.isfile() or not allowed_source(member.name):
                raise ValueError("Source bundle contains an unexpected member")
            target.addfile(member, source.extractfile(member))
    if destination.stat().st_size > 10_000_000:
        raise ValueError("Source bundle exceeds the reviewed 10 MB allowance")


def quotation(profile):
    def fetch(item):
        key, (service, sku, unit) = item
        result = aws(
            profile,
            "pricing",
            "get-products",
            "--service-code",
            service,
            "--filters",
            f"Type=TERM_MATCH,Field=sku,Value={sku}",
            region="us-east-1",
        )
        prices = [json.loads(p) for p in result["PriceList"]]
        if len(prices) != 1:
            raise ValueError("The reviewed regional SKU is missing or ambiguous")
        product = prices[0]
        dimensions = [
            d
            for term in product["terms"]["OnDemand"].values()
            for d in term["priceDimensions"].values()
            if d["unit"] == unit
        ]
        # Maximum paid tier, deliberately ignoring free-tier discounts.
        rate = max(costs.amount(d["pricePerUnit"]["USD"]) for d in dimensions)
        return key, {"sku": sku, "unit": unit, "usd": str(rate), "product": product}

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        rates = dict(pool.map(fetch, costs.SKUS.items()))
    return {"checked_at": costs.now().isoformat(), "region": REGION, "rates": rates}


def tf(folder, profile, *arguments):
    env = environment(profile)
    env["TF_DATA_DIR"] = str(folder / "terraform-data")
    result = subprocess.run(
        ["terraform", f"-chdir={folder / 'module'}", *arguments],
        env=env,
        capture_output=True,
        timeout=1200,
        check=False,
    )
    with (folder / "terraform.log").open("ab") as handle:
        handle.write(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError("Terraform failed; inspect this session's private terraform.log")
    return result.stdout


def validate_plan(plan):
    changes = {c["address"]: c for c in plan["resource_changes"] if c["mode"] == "managed"}
    if set(changes) != RESOURCES or any(
        c["change"]["actions"] != ["create"] for c in changes.values()
    ):
        raise ValueError("Only the reviewed fresh-session resource set may be created")
    instance = changes["aws_instance.demo"]["change"]["after"]
    disk = instance["root_block_device"][0]
    metadata = instance["metadata_options"][0]
    group = changes["aws_security_group.demo"]["change"]["after"]
    if (
        instance["instance_type"] != "t3.medium"
        or disk["volume_size"] != 24
        or disk["volume_type"] != "gp3"
        or not disk["encrypted"]
        or not disk["delete_on_termination"]
        or instance["monitoring"]
        or instance["credit_specification"][0]["cpu_credits"] != "standard"
        or instance["instance_initiated_shutdown_behavior"] != "terminate"
        or metadata["http_tokens"] != "required"
        or metadata["http_put_response_hop_limit"] != 1
        or group["ingress"]
    ):
        raise ValueError("The plan violates the closed cost or isolation model")


def prepare(args):
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT).strip():
        raise ValueError("Commit reviewed changes before preparing an immutable session")
    account = identity(args.profile)
    parent = None
    if args.reuse_reservation:
        parent_folder, parent = load_session(args.reuse_reservation)
        intact(parent_folder, parent)
        if parent["account"] != account or any(residuals(parent).values()):
            raise ValueError(
                "The original reservation must belong to this account and be cleaned up"
            )
    existing = live_tagged_resources(args.profile, account)
    if existing:
        raise ValueError("Existing tagged project resources require review and cleanup first")
    aws(
        args.profile,
        "iam",
        "get-role",
        "--role-name",
        "jobhunter-p5-permission-probe",
        absent=("NoSuchEntity",),
    )
    session_id = "p5-" + secrets.token_hex(6)
    folder = PRIVATE / "sessions" / session_id
    folder.mkdir(parents=True)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    (folder / "module").mkdir()
    for name in MODULE_FILES:
        content = subprocess.check_output(["git", "show", f"{revision}:infra/p5/{name}"], cwd=ROOT)
        (folder / "module" / name).write_bytes(content)
    bundle(folder / "source.tar.gz", revision)
    quote = quotation(args.profile)
    costs.estimate(quote, args.hours, costs.now())
    write(folder / "quote.json", quote)
    write(
        folder / "spending.json",
        {
            "account": account,
            "month": costs.now().strftime("%Y-%m"),
            "checked_at": args.spending_checked_at,
            "usd": args.spending_usd,
            "reference": args.spending_reference,
        },
    )
    ami = aws(
        args.profile,
        "ssm",
        "get-parameter",
        "--name",
        "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64",
    )["Parameter"]["Value"]
    images = aws(args.profile, "ec2", "describe-images", "--owners", "amazon", "--image-ids", ami)
    if len(images["Images"]) != 1 or images["Images"][0]["Architecture"] != "x86_64":
        raise ValueError("The AMI is not the expected Amazon-owned architecture")
    with urlopen(
        Request(
            "https://api.github.com/repos/docker/compose/releases/latest",
            headers={"User-Agent": "JobHunter-P5"},
        ),
        timeout=30,
    ) as response:
        release = json.load(response)
    asset = next(a for a in release["assets"] if a["name"] == "docker-compose-linux-x86_64")
    compose_digest = asset["digest"].removeprefix("sha256:")
    if not re.fullmatch(r"[a-f0-9]{64}", compose_digest):
        raise ValueError("Docker Compose release has no verified SHA-256 digest")
    with urlopen(
        Request(
            "https://api.github.com/repos/docker/buildx/releases/latest",
            headers={"User-Agent": "JobHunter-P5"},
        ),
        timeout=30,
    ) as response:
        buildx_release = json.load(response)
    buildx_asset = next(
        a
        for a in buildx_release["assets"]
        if a["name"] == f"buildx-{buildx_release['tag_name']}.linux-amd64"
    )
    buildx_digest = buildx_asset["digest"].removeprefix("sha256:")
    if not re.fullmatch(r"[a-f0-9]{64}", buildx_digest):
        raise ValueError("Docker Buildx release has no verified SHA-256 digest")
    expires = (costs.now() + timedelta(hours=args.hours)).replace(microsecond=0)
    if parent:
        expires = min(expires, costs.timestamp(parent["expires_at"]))
    variables = {
        "account_id": account,
        "session_id": session_id,
        "ami_id": ami,
        "expires_at": expires.isoformat(),
        "bundle_path": str(folder / "source.tar.gz"),
        "bundle_sha256": digest(folder / "source.tar.gz"),
        "compose_version": release["tag_name"],
        "compose_sha256": compose_digest,
        "buildx_version": buildx_release["tag_name"],
        "buildx_sha256": buildx_digest,
    }
    write(folder / "variables.json", variables)
    tf(
        folder,
        args.profile,
        "init",
        "-input=false",
        "-no-color",
        "-lockfile=readonly",
        f"-backend-config=path={folder / 'terraform.tfstate'}",
    )
    tf(
        folder,
        args.profile,
        "plan",
        "-input=false",
        "-no-color",
        f"-var-file={folder / 'variables.json'}",
        f"-out={folder / 'plan.tfplan'}",
    )
    plan = json.loads(tf(folder, args.profile, "show", "-json", str(folder / "plan.tfplan")))
    validate_plan(plan)
    binding = {
        "id": session_id,
        "account": account,
        "profile": args.profile,
        "region": REGION,
        "revision": revision,
        "hours": args.hours,
        "expires_at": expires.isoformat(),
        "files": {
            str(p.relative_to(folder)): digest(p)
            for p in [
                folder / "source.tar.gz",
                folder / "variables.json",
                folder / "plan.tfplan",
                folder / "quote.json",
                folder / "spending.json",
                *[folder / "module" / name for name in MODULE_FILES],
            ]
        },
    }
    if parent:
        binding["parent"] = parent["id"]
    write(folder / "session.json", binding)
    print(
        json.dumps({"session": session_id, "status": "prepared", "cloud_resources_created": False})
    )


def load_session(session_id):
    if not re.fullmatch(r"p5-[a-f0-9]{12}", session_id):
        raise ValueError("Invalid session identifier")
    folder = PRIVATE / "sessions" / session_id
    session = json.loads((folder / "session.json").read_text())
    if session["id"] != session_id or session["region"] != REGION:
        raise ValueError("Session binding mismatch")
    if identity(session["profile"]) != session["account"]:
        raise ValueError("AWS account differs from the prepared session")
    return folder, session


def intact(folder, session):
    for name, expected in session["files"].items():
        path = (folder / name).resolve()
        if not path.is_relative_to(folder.resolve()) or digest(path) != expected:
            raise ValueError("Prepared inputs changed; prepare a fresh session")


def remote(session, instance, commands):
    result = aws(
        session["profile"],
        "ssm",
        "send-command",
        "--instance-ids",
        instance,
        "--document-name",
        "AWS-RunShellScript",
        "--parameters",
        json.dumps({"commands": commands, "executionTimeout": ["900"]}),
    )
    command_id = result["Command"]["CommandId"]
    deadline = time.monotonic() + 960
    while time.monotonic() < deadline:
        invocation = aws(
            session["profile"],
            "ssm",
            "get-command-invocation",
            "--command-id",
            command_id,
            "--instance-id",
            instance,
            absent=("InvocationDoesNotExist",),
        )
        if invocation and invocation["Status"] == "Success":
            return invocation["StandardOutputContent"]
        if invocation and invocation["Status"] in {"Failed", "Cancelled", "TimedOut"}:
            raise RuntimeError("Remote synthetic check failed; inspect private host diagnostics")
        time.sleep(5)
    raise TimeoutError("Remote synthetic check timed out")


def exercise(folder, session):
    outputs = json.loads(tf(folder, session["profile"], "output", "-json"))
    instance, bucket = outputs["instance_id"]["value"], outputs["bucket"]["value"]
    write(folder / "outputs.json", outputs)
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        info = aws(
            session["profile"],
            "ssm",
            "describe-instance-information",
            "--filters",
            f"Key=InstanceIds,Values={instance}",
        )["InstanceInformationList"]
        if info and info[0]["PingStatus"] == "Online":
            break
        time.sleep(10)
    else:
        raise TimeoutError("The private SSM host did not become available")
    print("SSM connected; waiting for synthetic bootstrap and recovery checks.", flush=True)
    result = remote(
        session,
        instance,
        [
            "set -eu",
            "for i in $(seq 1 80); do "
            "test ! -f /opt/jobhunter/.private/ready || break; sleep 10; done",
            "test -f /opt/jobhunter/.private/ready",
            "systemctl is-active --quiet jobhunter-expiry.timer",
            "python3 /opt/jobhunter/infra/p5/host/operations.py health",
            "cat /opt/jobhunter/.private/workflow.json /opt/jobhunter/.private/restore.json",
            "curl --fail --silent http://127.0.0.1:15173/ | grep -q '<div id=\"root\"></div>'",
        ],
    )
    (folder / "remote-check.txt").write_text(result)
    for name in ("demo.dump", "backup.json", "workflow.json", "restore.json"):
        aws(
            session["profile"],
            "s3",
            "cp",
            f"s3://{bucket}/backup/{name}",
            str(folder / name),
            "--only-show-errors",
        )
    backup = json.loads((folder / "backup.json").read_text())
    if digest(folder / "demo.dump") != backup["sha256"]:
        raise ValueError("The exported backup failed SHA-256 verification")
    health = aws(
        session["profile"],
        "cloudwatch",
        "get-metric-statistics",
        "--namespace",
        "JobHunter/P5",
        "--metric-name",
        "Ready",
        "--dimensions",
        f"Name=Session,Value={session['id']}",
        "--statistics",
        "Maximum",
        "--period",
        "60",
        "--start-time",
        (costs.now() - timedelta(minutes=30)).isoformat(),
        "--end-time",
        (costs.now() + timedelta(minutes=1)).isoformat(),
    )
    if not any(p["Maximum"] == 1 for p in health["Datapoints"]):
        raise ValueError("No healthy CloudWatch metric has been observed")
    write(folder / "health.json", health)
    # Exercise the actual cloud deadline after export, rather than merely inspect its plan.
    schedule = aws(
        session["profile"], "scheduler", "get-schedule", "--name", "jobhunter-" + session["id"]
    )
    if json.loads(schedule["Target"]["Input"])["InstanceIds"] != [instance]:
        raise ValueError("Termination schedule targets a different instance")
    expiry = (costs.now() + timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%S")
    aws(
        session["profile"],
        "scheduler",
        "update-schedule",
        "--name",
        schedule["Name"],
        "--schedule-expression",
        f"at({expiry})",
        "--schedule-expression-timezone",
        "UTC",
        "--flexible-time-window",
        '{"Mode":"OFF"}',
        "--target",
        json.dumps(schedule["Target"]),
    )
    print("Backup exported; exercising the AWS termination deadline.", flush=True)
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        state = aws(session["profile"], "ec2", "describe-instances", "--instance-ids", instance)
        if state["Reservations"][0]["Instances"][0]["State"]["Name"] == "terminated":
            write(
                folder / "acceptance.json",
                {
                    "private_ssm": "passed",
                    "synthetic_workflow": "passed",
                    "backup_restore": "passed",
                    "health_metric": "passed",
                    "scheduler_termination": "passed",
                    "host_timer": "armed",
                },
            )
            return
        time.sleep(10)
    raise TimeoutError("Scheduled termination was not observed")


def residuals(session):
    profile, sid = session["profile"], session["id"]
    filters = f"Name=tag:Session,Values={sid}"
    checks = {}
    for operation, key in (
        ("describe-instances", "Reservations"),
        ("describe-volumes", "Volumes"),
        ("describe-vpcs", "Vpcs"),
        ("describe-subnets", "Subnets"),
        ("describe-security-groups", "SecurityGroups"),
        ("describe-network-interfaces", "NetworkInterfaces"),
        ("describe-internet-gateways", "InternetGateways"),
        ("describe-route-tables", "RouteTables"),
        ("describe-addresses", "Addresses"),
        ("describe-nat-gateways", "NatGateways"),
        ("describe-vpc-endpoints", "VpcEndpoints"),
        ("describe-snapshots", "Snapshots"),
    ):
        filter_option = "--filter" if operation == "describe-nat-gateways" else "--filters"
        data = aws(profile, "ec2", operation, filter_option, filters)[key]
        if operation == "describe-instances":
            data = [i for r in data for i in r["Instances"] if i["State"]["Name"] != "terminated"]
        if operation == "describe-nat-gateways":
            data = [x for x in data if x["State"] != "deleted"]
        checks[operation] = len(data)
    name = "jobhunter-" + sid
    # Exact identity checks cover services that do not support the same tag query.
    checks["bucket"] = int(
        aws(
            profile,
            "s3api",
            "head-bucket",
            "--bucket",
            f"{name}-{session['account']}",
            absent=("404", "NoSuchBucket", "NotFound"),
        )
        is not None
    )
    for suffix in ("host", "expiry"):
        checks[suffix + "_role"] = int(
            aws(
                profile,
                "iam",
                "get-role",
                "--role-name",
                name + "-" + suffix,
                absent=("NoSuchEntity",),
            )
            is not None
        )
    checks["profile"] = int(
        aws(
            profile,
            "iam",
            "get-instance-profile",
            "--instance-profile-name",
            name + "-host",
            absent=("NoSuchEntity",),
        )
        is not None
    )
    checks["schedule"] = int(
        aws(
            profile,
            "scheduler",
            "get-schedule",
            "--name",
            name,
            absent=("ResourceNotFoundException",),
        )
        is not None
    )
    checks["alarms"] = len(
        aws(profile, "cloudwatch", "describe-alarms", "--alarm-names", name)["MetricAlarms"]
    )
    checks["logs"] = len(
        aws(
            profile,
            "logs",
            "describe-log-groups",
            "--log-group-name-prefix",
            "/jobhunter/p5/" + sid,
        )["logGroups"]
    )
    return checks


def destroy(folder, session):
    # No price freshness or budget gate: cleanup must work after an interruption.
    if identity(session["profile"]) != session["account"]:
        raise ValueError("Refusing cleanup in a different AWS account")
    tf(
        folder,
        session["profile"],
        "destroy",
        "-auto-approve",
        "-input=false",
        "-no-color",
        f"-var-file={folder / 'variables.json'}",
    )
    checks = residuals(session)
    write(folder / "residuals.json", checks)
    if any(checks.values()):
        raise ValueError("Residual session resources remain; cleanup is not complete")
    costs.mark_destroyed(PRIVATE / "ledger.sqlite", session["id"])
    print("Session destroyed; residual scan clear. Monetary reservation retained.", flush=True)


def run(session_id):
    folder, session = load_session(session_id)
    intact(folder, session)
    if costs.timestamp(session["expires_at"]) - costs.now() < timedelta(minutes=45):
        raise ValueError("Too little time remains; prepare a fresh session")
    quote = json.loads((folder / "quote.json").read_text())
    spending = json.loads((folder / "spending.json").read_text())
    if session.get("parent"):
        parent_folder, parent = load_session(session["parent"])
        intact(parent_folder, parent)
        if any(residuals(parent).values()):
            raise ValueError("The original session still has residual resources")
        summary = costs.reserve_retry(
            PRIVATE / "ledger.sqlite",
            session,
            parent,
            json.loads((parent_folder / "quote.json").read_text()),
            quote,
            spending,
        )
    else:
        summary = costs.reserve(PRIVATE / "ledger.sqlite", session, quote, spending)
    write(folder / "reservation.json", summary)
    print(json.dumps(summary), flush=True)
    try:
        print("Applying the reserved temporary session.", flush=True)
        tf(
            folder,
            session["profile"],
            "apply",
            "-input=false",
            "-no-color",
            str(folder / "plan.tfplan"),
        )
        print("Infrastructure created; checking private access and synthetic data.", flush=True)
        exercise(folder, session)
    finally:
        destroy(folder, session)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--profile", required=True)
    prepare_parser.add_argument("--hours", type=int, choices=range(1, 9), default=2)
    prepare_parser.add_argument("--spending-usd", required=True)
    prepare_parser.add_argument("--spending-checked-at", required=True)
    prepare_parser.add_argument("--spending-reference", required=True)
    prepare_parser.add_argument("--reuse-reservation")
    for action in ("run", "destroy"):
        commands.add_parser(action).add_argument("session")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args)
    elif args.action == "run":
        run(args.session)
    else:
        destroy(*load_session(args.session))


if __name__ == "__main__":
    main()
