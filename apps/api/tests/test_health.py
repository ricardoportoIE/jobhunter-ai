import logging
from unittest.mock import patch

import psycopg
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError

from jobhunter_api.database import check_database
from jobhunter_api.main import create_app, database_is_ready
from jobhunter_api.settings import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(db_password=SecretStr("test-only-not-a-real-credential"))


def test_liveness_does_not_depend_on_database(settings: Settings) -> None:
    application = create_app(settings)
    with (
        patch("jobhunter_api.main.check_database", side_effect=AssertionError("Do not query DB")),
        TestClient(application) as client,
    ):
        response = client.get("/api/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "jobhunter-api"}


@pytest.mark.parametrize("available,expected_status", [(True, 200), (False, 503)])
def test_readiness_reflects_database_state(
    settings: Settings, available: bool, expected_status: int
) -> None:
    application = create_app(settings)
    application.dependency_overrides[database_is_ready] = lambda: available
    with TestClient(application) as client:
        response = client.get("/api/health/ready")
    assert response.status_code == expected_status
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "status": "ready" if available else "not_ready",
        "checks": {"database": "ok" if available else "unavailable"},
    }


def test_database_failure_does_not_disclose_credentials(
    settings: Settings, caplog: pytest.LogCaptureFixture
) -> None:
    secret = settings.db_password.get_secret_value()
    with (
        patch("jobhunter_api.database.psycopg.connect", side_effect=psycopg.Error(secret)),
        caplog.at_level(logging.WARNING),
    ):
        assert check_database(settings) is False
    assert secret not in caplog.text
    assert "Database readiness check failed" in caplog.text


def test_missing_password_fails_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JOBHUNTER_DB_PASSWORD", raising=False)
    with pytest.raises(ValidationError):
        Settings()


def test_empty_password_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(db_password=SecretStr(""))
