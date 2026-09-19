"""Disposable browser-test server: fixed test DB and synthetic credentials only."""

import os
from uuid import uuid4

import psycopg
import uvicorn
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
        }
    )
    migrate(settings)
    provision(settings)
    with connect(settings) as db:
        db.execute("TRUNCATE users,login_limits,audit_events CASCADE")
        db.execute(
            "INSERT INTO users(id,username,password_hash) VALUES (%s,'local',%s)",
            (uuid4(), PasswordHasher().hash("synthetic-browser-test-only")),
        )
    uvicorn.run(create_app(settings), host="127.0.0.1", port=8001, access_log=False)


if __name__ == "__main__":
    main()
