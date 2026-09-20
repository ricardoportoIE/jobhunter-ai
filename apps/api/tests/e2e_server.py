"""Disposable browser-test server: fixed test DB and synthetic credentials only."""

import argparse
import os
from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

import psycopg
import uvicorn
from ai_fixture_provider import BrowserFixtureProvider
from argon2 import PasswordHasher
from psycopg import sql
from pydantic import SecretStr

from jobhunter_api.main import create_app
from jobhunter_api.manage import migrate, provision
from jobhunter_api.settings import Settings
from jobhunter_api.store import connect


def main() -> None:
    if os.environ.get("JOBHUNTER_E2E") != "1":
        raise RuntimeError("Run through the Playwright test configuration")
    admin = Settings()
    name = "jobhunter_test_e2e"
    assert admin.db_name != name
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset-login-limit", action="store_true")
    args = parser.parse_args()
    if args.reset_login_limit:
        # Each independent browser journey starts with a clean test-only login bucket.
        # Production throttling remains covered by the API authentication tests.
        with connect(admin.model_copy(update={"db_name": name})) as db:
            db.execute("DELETE FROM login_limits")
        return
    with psycopg.connect(
        host=admin.db_host,
        port=admin.db_port,
        dbname="postgres",
        user=admin.db_user,
        password=admin.db_password.get_secret_value(),
        autocommit=True,
    ) as db:
        if not db.execute("SELECT 1 FROM pg_database WHERE datname=%s", (name,)).fetchone():
            db.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    settings = admin.model_copy(
        update={
            "db_name": name,
            "app_db_user": "jobhunter_e2e",
            "app_db_password": SecretStr("synthetic-e2e-database-only"),
            "allowed_origins": ["http://127.0.0.1:5174"],
            "openai_api_key": SecretStr("synthetic-e2e-not-a-real-key"),
            "ai_review_model": "gpt-4.1-mini-2025-04-14",
            "ai_prices_reviewed": datetime.now(UTC).date(),
        }
    )
    migrate(settings)
    provision(settings)
    with connect(settings) as db:
        db.execute("TRUNCATE users,login_limits,audit_events,ai_calls CASCADE")
        db.execute(
            "INSERT INTO users(id,username,password_hash) VALUES (%s,'local',%s)",
            (uuid4(), PasswordHasher().hash("synthetic-browser-test-only")),
        )
    fixture = BrowserFixtureProvider()
    with (
        patch("jobhunter_api.job_parser.get_provider", return_value=fixture),
        patch("jobhunter_api.cv_import.get_provider", return_value=fixture),
        patch("jobhunter_api.job_url.get_provider", return_value=fixture),
        patch(
            "jobhunter_api.job_url.fetch_vacancy",
            side_effect=lambda url: (
                url,
                "Junior Python Developer\nExample Labs\nDublin\nPython is required.\n"
                "Personal projects accepted. Apply through the public careers portal.",
            ),
        ),
        patch("jobhunter_api.ai_matching.get_provider", return_value=fixture),
        patch("jobhunter_api.packages.get_provider", return_value=fixture),
        patch("jobhunter_api.semantic.embedding_provider", return_value=fixture),
        patch("jobhunter_api.research.search", return_value=fixture.research()),
    ):
        uvicorn.run(create_app(settings), host="127.0.0.1", port=8001, access_log=False)


if __name__ == "__main__":
    main()
