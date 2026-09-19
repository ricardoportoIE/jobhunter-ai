"""Check the local stack; optionally interrupt and restore its database."""

import argparse
import json
import re
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def fetch(url: str) -> tuple[int, str]:
    try:
        with urlopen(url, timeout=8) as response:
            return response.status, response.read().decode("utf-8")
    except HTTPError as error:
        return error.code, error.read().decode("utf-8")


def expect_json(url: str, status: int, payload: dict[str, object]) -> None:
    actual_status, body = fetch(url)
    assert actual_status == status, f"Unexpected HTTP status: {actual_status} at {url}"
    assert json.loads(body) == payload, f"Unexpected response at {url}"


def compose(*arguments: str) -> None:
    subprocess.run(["docker", "compose", *arguments], cwd=ROOT, check=True, timeout=90)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--web-url", default="http://127.0.0.1:5173")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--exercise-db-recovery", action="store_true")
    args = parser.parse_args()
    web, api = args.web_url.rstrip("/"), args.api_url.rstrip("/")
    for url in (web, api):
        parsed = urlparse(url)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
            parser.error("Smoke checks are restricted to local HTTP endpoints.")

    ready = {"status": "ready", "checks": {"database": "ok"}}
    live = {"status": "ok", "service": "jobhunter-api"}
    for base in (web, api):
        expect_json(f"{base}/api/health/live", 200, live)
        expect_json(f"{base}/api/health/ready", 200, ready)
        status, body = fetch(f"{base}/api/openapi.json")
        assert status == 200 and "/api/health/ready" in json.loads(body)["paths"]
        status, body = fetch(f"{base}/api/docs")
        assert status == 200 and "SwaggerUIBundle" in body

    status, html = fetch(web)
    assert status == 200 and '<div id="root"></div>' in html
    assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', html)
    assert len(assets) >= 2, "Built JavaScript/CSS assets were not found"
    for asset in assets:
        status, body = fetch(web + asset)
        assert status == 200 and body and not body.lstrip().startswith("<!doctype html>")
    assert fetch(web + "/assets/missing.js")[0] == 404
    assert fetch(web + "/healthz") == (200, "ok")
    print("PASS: frontend assets, API, PostgreSQL, proxy and OpenAPI.")

    if args.exercise_db_recovery:
        try:
            compose("stop", "db")
            for base in (web, api):
                expect_json(f"{base}/api/health/live", 200, live)
                expect_json(
                    f"{base}/api/health/ready",
                    503,
                    {
                        "status": "not_ready",
                        "checks": {"database": "unavailable"},
                    },
                )
            print("PASS: database outage returns 503; API liveness stays 200.")
        finally:
            compose("start", "db")

        deadline = time.monotonic() + 60
        while True:
            try:
                for base in (web, api):
                    expect_json(f"{base}/api/health/ready", 200, ready)
                break
            except (AssertionError, URLError, TimeoutError):
                if time.monotonic() >= deadline:
                    raise
                time.sleep(1)
        print("PASS: database recovered without restarting the API or frontend.")


if __name__ == "__main__":
    main()
