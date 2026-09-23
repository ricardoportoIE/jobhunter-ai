"""Exercise the P5 host workflow in a disposable local Compose project, without AWS."""

import importlib.util
import json
import os
import secrets
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    name = "p5-local-" + secrets.token_hex(6)
    target = ROOT / ".private/p5" / name
    target.mkdir(parents=True)
    paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    for name_in_git in filter(None, paths):
        if name_in_git.startswith(("apps/api/", "apps/web/")) or name_in_git in {
            "compose.yaml",
            ".env.example",
            "scripts/init_env.py",
        }:
            destination = target / name_in_git
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name_in_git, destination)
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("JOBHUNTER_") and key not in {"WEB_PORT", "API_PORT"}
    }
    environment["COMPOSE_PROJECT_NAME"] = name

    def run(arguments, **kwargs):
        return subprocess.run(
            arguments, cwd=target, env=environment, check=True, timeout=600, **kwargs
        )

    run(["python", "scripts/init_env.py"])
    with (target / ".env").open("a") as handle:
        handle.write("\nWEB_PORT=15173\nAPI_PORT=18000\nJOBHUNTER_DB_PORT=15433\n")
    (target / ".private").mkdir()
    spec = importlib.util.spec_from_file_location("host", ROOT / "infra/p5/host/operations.py")
    host = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(host)
    host.ROOT = target
    host.context = lambda: (name, "local-s3-substitute")
    objects = target / "local-s3-substitute"
    objects.mkdir()

    def command(arguments, *, input=None):
        if arguments[:3] == ["aws", "s3", "cp"]:
            source, destination = arguments[3:5]
            if source.startswith("s3://"):
                source = objects / source.rsplit("/", 1)[1]
            else:
                destination = objects / destination.rsplit("/", 1)[1]
            shutil.copyfile(source, destination)
            return b""
        return run(arguments, input=input, capture_output=True).stdout

    host.command = command
    try:
        run(["docker", "compose", "up", "--build", "--detach", "--wait", "--wait-timeout", "180"])
        run(
            [
                "docker",
                "compose",
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "-v",
                f"{target / '.private'}:/private",
                "migrate",
                "python",
                "-m",
                "jobhunter_api.manage",
                "bootstrap",
                "--credentials-file",
                "/private/login.txt",
            ]
        )
        run(
            [
                "docker",
                "compose",
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "migrate",
                "python",
                "-m",
                "jobhunter_api.manage",
                "seed",
            ]
        )
        host.verify()
        host.verify()
        host.backup()
        host.restore_check()
        print(json.dumps({"local_workflow": "passed", "aws_exercised": False}))
    finally:
        run(["docker", "compose", "down", "--volumes", "--remove-orphans"])
        print("Disposable Compose project removed; private evidence retained locally.")


if __name__ == "__main__":
    main()
