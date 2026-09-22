"""Integration tests use a separate database, never the local application DB."""

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

import psycopg
import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from psycopg import sql
from pydantic import SecretStr

from jobhunter_api.main import create_app
from jobhunter_api.manage import migrate, provision
from jobhunter_api.settings import Settings
from jobhunter_api.store import connect

TEST_PASSWORD = "synthetic-test-password-only"
ORIGIN = "http://127.0.0.1:5173"


@pytest.fixture(scope="session")
def database_settings() -> Settings:
    name = os.environ.get("JOBHUNTER_TEST_DB_NAME")
    if not name:
        pytest.skip("Set JOBHUNTER_TEST_DB_NAME=jobhunter_test to run PostgreSQL integration tests")
    if not name.startswith("jobhunter_test"):
        pytest.fail("Refusing to use a database without jobhunter_test prefix")
    settings = Settings()
    assert settings.db_name != name
    with psycopg.connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname="postgres",
        user=settings.db_user,
        password=settings.db_password.get_secret_value(),
        autocommit=True,
    ) as admin:
        if not admin.execute("SELECT 1 FROM pg_database WHERE datname=%s", (name,)).fetchone():
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    test_settings = settings.model_copy(
        update={
            "db_name": name,
            "openai_api_key": None,
            "gmail_client_id": "",
            "gmail_client_secret": None,
            "gmail_redirect_uri": ORIGIN + "/",
            "discovery_encryption_key": None,
            "ai_prices_reviewed": datetime.now(UTC).date(),
        }
    )
    if not test_settings.app_db_password:
        test_settings.app_db_password = SecretStr("ci-synthetic-runtime-only")
    migrate(test_settings)
    provision(test_settings)
    return test_settings


@pytest.fixture
def db_settings(database_settings: Settings) -> Settings:
    with connect(database_settings) as db:
        db.execute("TRUNCATE users,login_limits,audit_events,ai_calls CASCADE")
        db.execute(
            "INSERT INTO users (id,username,password_hash) VALUES (%s,'local',%s)",
            (uuid4(), PasswordHasher().hash(TEST_PASSWORD)),
        )
    return database_settings


@pytest.fixture
def client(db_settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(db_settings), raise_server_exceptions=False) as client:
        client.headers["Origin"] = ORIGIN
        yield client


@pytest.fixture
def signed_client(client: TestClient) -> TestClient:
    response = client.post("/api/v1/session", json={"username": "local", "password": TEST_PASSWORD})
    assert response.status_code == 200, response.text
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return client
