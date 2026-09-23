"""Operate only an isolated synthetic P5 host; never print credentials or record content."""

import argparse
import hashlib
import http.cookiejar
import json
import os
import re
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

ROOT = Path("/opt/jobhunter")
BASE = "http://127.0.0.1:15173"


def command(arguments, *, input=None):
    return subprocess.run(
        arguments, cwd=ROOT, input=input, capture_output=True, check=True, timeout=120
    ).stdout


def compose(*args, **kwargs):
    return command(["docker", "compose", *args], **kwargs)


def sql(database, statement):
    return (
        compose(
            "exec",
            "-T",
            "db",
            "psql",
            "-U",
            "jobhunter",
            "-d",
            database,
            "-At",
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            statement,
        )
        .decode()
        .strip()
    )


def context():
    session = Path("/opt/jobhunter-session").read_text().strip()
    bucket = Path("/opt/jobhunter-bucket").read_text().strip()
    if not re.fullmatch(r"p5-[a-z0-9]{12}", session) or not re.fullmatch(
        rf"jobhunter-{session}-[0-9]{{12}}", bucket
    ):
        raise ValueError("Not a recognised P5 host")
    return session, bucket


def report(name, values):
    target = ROOT / ".private" / (name + ".json")
    target.write_text(json.dumps(values, indent=2) + "\n")
    target.chmod(0o600)
    print(json.dumps(values))


def verify():
    context()
    cookies = http.cookiejar.CookieJar()
    client = build_opener(HTTPCookieProcessor(cookies))
    csrf = ""

    def call(path, method="GET", data=None):
        headers = {"Origin": BASE, "Content-Type": "application/json"}
        if csrf:
            headers["X-CSRF-Token"] = csrf
        request = Request(
            BASE + "/api/v1" + path,
            method=method,
            headers=headers,
            data=json.dumps(data).encode() if data is not None else None,
        )
        with client.open(request, timeout=20) as response:
            return json.load(response)

    try:
        call("/candidate/profile")
    except HTTPError as error:
        assert error.code == 401
    else:
        raise ValueError("Unauthenticated data access unexpectedly succeeded")
    password = (ROOT / ".private/login.txt").read_text().split("Password: ", 1)[1].strip()
    csrf = call("/session", "POST", {"username": "local", "password": password})["csrf_token"]
    profile = call("/candidate/profile")
    profile = call(
        "/candidate/profile",
        "PATCH",
        {
            "expected_version": profile["version"],
            "display_name": "Synthetic P5 candidate",
        },
    )
    profile = call("/candidate/profile/review", "POST", {"expected_version": profile["version"]})
    facts = call("/candidate/facts")
    assert len(facts) == 1 and "Fictional demonstration" in facts[0]["claim"]
    job = call(
        "/jobs/import",
        "POST",
        {
            "raw_text": (
                "Synthetic Junior Python Developer. Python required; personal projects accepted."
            ),
            "source_name": "P5 synthetic validation",
            "external_id": "p5-synthetic-job",
        },
    )
    job = call("/jobs/" + job["id"])
    job = call(
        "/jobs/" + job["id"],
        "PATCH",
        {
            "expected_version": job["version"],
            "review_confirmed": True,
            "title": "Junior Python developer",
            "seniority": "junior",
            "requirements": [
                {
                    "text": "Python",
                    "category": "technical_skills",
                    "source_locator": "Sentence 2",
                }
            ],
        },
    )
    match = call(
        "/jobs/" + job["id"] + "/analyse",
        "POST",
        {
            "job_version": job["version"],
            "profile_version": profile["version"],
            "review_confirmed": True,
            "assessments": [
                {
                    "requirement_id": job["requirements"][0]["id"],
                    "status": "met",
                    "reason": "The reviewed synthetic Python project supports this requirement.",
                    "fact_ids": [facts[0]["id"]],
                }
            ],
        },
    )
    assert match["score"] == 100 and match["coverage"] == 0.3
    application = call("/applications", "POST", {"job_id": job["id"], "match_id": match["id"]})
    assert application["status"] == "SHORTLISTED"
    assert not call("/discovery/gmail/status")["configured"]
    assert call("/discovery/sources") == []
    report(
        "workflow",
        {
            "synthetic_workflow": "passed",
            "unauthenticated_access": "denied",
            "score": 100,
            "coverage": 0.3,
            "paid_calls": 0,
        },
    )


def record_hash(database):
    return sql(
        database,
        "SELECT md5(coalesce(string_agg(id::text || kind || version::text || data::text, "
        "'' ORDER BY id),'')) FROM records",
    )


def backup():
    _, bucket = context()
    digest_before = record_hash("jobhunter")
    payload = compose(
        "exec",
        "-T",
        "db",
        "pg_dump",
        "-U",
        "jobhunter",
        "-d",
        "jobhunter",
        "-Fc",
        "--no-owner",
    )
    target = ROOT / ".private/demo.dump"
    target.write_bytes(payload)
    target.chmod(0o600)
    digest = hashlib.sha256(payload).hexdigest()
    if digest_before != record_hash("jobhunter"):
        raise ValueError("Data changed during backup; retry while the demo is idle")
    report(
        "backup",
        {"sha256": digest, "bytes": len(payload), "records_hash": digest_before},
    )
    for name in ("demo.dump", "backup.json", "workflow.json"):
        command(
            [
                "aws",
                "s3",
                "cp",
                str(ROOT / ".private" / name),
                f"s3://{bucket}/backup/{name}",
                "--region",
                "eu-west-1",
                "--only-show-errors",
            ]
        )


def restore_check():
    _, bucket = context()
    # Restore from the uploaded copy, not the original local dump.
    target = ROOT / ".private/restored.dump"
    command(
        [
            "aws",
            "s3",
            "cp",
            f"s3://{bucket}/backup/demo.dump",
            str(target),
            "--region",
            "eu-west-1",
            "--only-show-errors",
        ]
    )
    metadata = json.loads((ROOT / ".private/backup.json").read_text())
    assert hashlib.sha256(target.read_bytes()).hexdigest() == metadata["sha256"]
    database = "jobhunter_p5_restore"
    # A fixed, separate scratch database; the running application's database is untouched.
    compose("exec", "-T", "db", "createdb", "-U", "jobhunter", database)
    try:
        compose(
            "exec",
            "-T",
            "db",
            "pg_restore",
            "-U",
            "jobhunter",
            "-d",
            database,
            "--no-owner",
            "--no-privileges",
            "--exit-on-error",
            input=target.read_bytes(),
        )
        assert record_hash(database) == metadata["records_hash"]
    finally:
        compose("exec", "-T", "db", "dropdb", "-U", "jobhunter", database)
    report("restore", {"restore": "passed", "backup_sha256": metadata["sha256"]})
    command(
        [
            "aws",
            "s3",
            "cp",
            str(ROOT / ".private/restore.json"),
            f"s3://{bucket}/backup/restore.json",
            "--region",
            "eu-west-1",
            "--only-show-errors",
        ]
    )


def health():
    session, _ = context()
    ready = 0
    try:
        with build_opener().open(BASE + "/api/health/ready", timeout=5) as response:
            ready = int(response.status == 200 and json.load(response)["status"] == "ready")
    except (OSError, ValueError, KeyError):
        pass
    group = "/jobhunter/p5/" + session
    # Repeated creation is harmless; only fixed operational metadata enters the stream.
    subprocess.run(
        [
            "aws",
            "logs",
            "create-log-stream",
            "--log-group-name",
            group,
            "--log-stream-name",
            "health",
            "--region",
            "eu-west-1",
        ],
        capture_output=True,
        check=False,
        timeout=30,
    )
    command(
        [
            "aws",
            "cloudwatch",
            "put-metric-data",
            "--namespace",
            "JobHunter/P5",
            "--metric-data",
            json.dumps(
                [
                    {
                        "MetricName": "Ready",
                        "Value": ready,
                        "Unit": "Count",
                        "Dimensions": [{"Name": "Session", "Value": session}],
                    }
                ]
            ),
            "--region",
            "eu-west-1",
        ]
    )
    command(
        [
            "aws",
            "logs",
            "put-log-events",
            "--log-group-name",
            group,
            "--log-stream-name",
            "health",
            "--log-events",
            json.dumps(
                [
                    {
                        "timestamp": int(time.time() * 1000),
                        "message": json.dumps({"ready": ready, "synthetic": True}),
                    }
                ]
            ),
            "--region",
            "eu-west-1",
        ]
    )
    report("health", {"ready": bool(ready), "telemetry": "published"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["verify", "backup", "restore-check", "health"])
    args = parser.parse_args()
    os.umask(0o077)
    try:
        {
            "verify": verify,
            "backup": backup,
            "restore-check": restore_check,
            "health": health,
        }[args.action]()
    except Exception as error:
        # HTTP responses, process stderr and environment values can contain private data.
        print(
            json.dumps(
                {
                    "operation": args.action,
                    "status": "failed",
                    "error_type": type(error).__name__,
                }
            )
        )
        raise SystemExit(1) from None
