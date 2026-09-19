from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from psycopg.errors import InsufficientPrivilege

from jobhunter_api.manage import erase
from jobhunter_api.settings import Settings
from jobhunter_api.store import connect


def test_audit_and_snapshots_are_append_only(db_settings: Settings) -> None:
    for statement in (
        "DELETE FROM audit_events",
        "UPDATE audit_events SET action='tampered'",
        "TRUNCATE audit_events",
        "DELETE FROM snapshots",
        "DROP TABLE records",
    ):
        with pytest.raises(InsufficientPrivilege), connect(db_settings.runtime()) as db:
            db.execute(statement)
    with connect(db_settings.runtime()) as db:
        role = db.execute(
            "SELECT rolsuper,rolcreaterole,rolcreatedb FROM pg_roles WHERE rolname=current_user"
        ).fetchone()
        assert role and not any(role.values())


def test_audit_failure_rolls_back_and_redacts(
    signed_client: TestClient, db_settings: Settings, caplog: pytest.LogCaptureFixture
) -> None:
    marker = "sensitive-payload-must-not-appear"
    with patch("jobhunter_api.records.audit", side_effect=RuntimeError(marker)):
        response = signed_client.post("/api/v1/jobs/import", json={"raw_text": marker})
    assert response.status_code == 500 and response.headers["x-request-id"]
    assert marker not in response.text and marker not in caplog.text
    with connect(db_settings) as db:
        assert db.execute("SELECT count(*) AS n FROM records").fetchone() == {"n": 0}
        assert db.execute("SELECT count(*) AS n FROM audit_events").fetchone() == {"n": 0}


def test_export_and_explicit_local_erasure(
    signed_client: TestClient, db_settings: Settings
) -> None:
    client = signed_client
    client.post("/api/v1/jobs/import", json={"raw_text": "Fictional private data"})
    response = client.get("/api/v1/candidate/export")
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    assert response.headers["content-disposition"].startswith("attachment;")
    assert len(response.json()["audit_events"]) == 1
    assert "password_hash" not in response.text and "csrf_token" not in response.text
    with pytest.raises(ValueError):
        erase(db_settings, "")
    assert client.get("/api/v1/jobs").json()["total"] == 1
    erase(db_settings, "DELETE_LOCAL_APPLICATION_DATA")
    assert client.get("/api/v1/session").status_code == 401
    with connect(db_settings) as db:
        for table in (
            "records",
            "audit_events",
            "snapshots",
            "idempotency",
            "job_keys",
            "sessions",
        ):
            from psycopg import sql

            assert db.execute(
                sql.SQL("SELECT count(*) AS n FROM {}").format(sql.Identifier(table))
            ).fetchone() == {"n": 0}
        assert db.execute("SELECT count(*) AS n FROM users").fetchone() == {"n": 1}
