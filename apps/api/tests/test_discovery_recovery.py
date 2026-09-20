from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb
from test_discovery import add_source, enable
from test_discovery_sync import due, item, reader
from test_gmail import configure

from jobhunter_api.auth import Principal, authenticated
from jobhunter_api.discovery_worker import tick
from jobhunter_api.errors import Problem
from jobhunter_api.gmail import put_secret
from jobhunter_api.greenhouse import DiscoveryBatch
from jobhunter_api.main import create_app
from jobhunter_api.manage import erase
from jobhunter_api.package_domain import StrategyRequest, capture
from jobhunter_api.records import insert, update
from jobhunter_api.settings import Settings
from jobhunter_api.store import connect


def test_foreign_owner_cannot_read_or_change_sources(
    signed_client: TestClient, db_settings: Settings
) -> None:
    source = add_source(signed_client)
    app = create_app(db_settings)
    # Keep the single-user schema intact while exercising ownership checks.
    app.dependency_overrides[authenticated] = lambda: Principal(uuid4(), "synthetic", "synthetic")
    with TestClient(app) as other:
        assert other.get("/api/v1/discovery/sources").json() == []
        path = f"/api/v1/discovery/sources/{source['id']}"
        assert other.get(path + "/runs").status_code == 404
        assert other.post(path + "/sync").status_code == 401
        assert other.patch(path, json={"expected_version": 1}).status_code == 401


def test_worker_only_checks_due_reviewed_sources(
    signed_client: TestClient, db_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = add_source(signed_client)
    calls = []
    monkeypatch.setattr(
        "jobhunter_api.discovery_worker.synchronise", lambda *args: calls.append(args)
    )
    tick(db_settings.runtime())
    assert not calls
    source = enable(signed_client, source)
    tick(db_settings.runtime())
    assert len(calls) == 1 and calls[0][2] == UUID(source["id"])
    with connect(db_settings) as db:
        db.execute(
            "UPDATE records SET data=data || %s WHERE id=%s",
            (
                Jsonb(
                    {
                        "next_sync_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
                    }
                ),
                source["id"],
            ),
        )
    tick(db_settings.runtime())
    assert len(calls) == 1


def test_interrupted_run_recovers_and_data_erasure_removes_tokens(
    signed_client: TestClient, db_settings: Settings
) -> None:
    source = enable(signed_client, add_source(signed_client))
    settings = configure(signed_client, db_settings)
    with connect(db_settings) as db:
        row = db.execute("SELECT * FROM records WHERE id=%s", (source["id"],)).fetchone()
        assert row
        run = insert(
            db, row["owner_id"], "discovery_run", {"source_id": source["id"], "status": "running"}
        )
        update(
            db,
            row,
            row["version"],
            {
                **row["data"],
                "active_run": str(run["id"]),
                "lease_until": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
            },
        )
        put_secret(db, settings, row["owner_id"], row["id"], "oauth", {"synthetic": True})
    reader(signed_client, lambda _: DiscoveryBatch(items=[item()], complete=True))
    result = signed_client.post(f"/api/v1/discovery/sources/{source['id']}/sync")
    assert result.json()["status"] == "completed"
    runs = signed_client.get(f"/api/v1/discovery/sources/{source['id']}/runs").json()
    assert any(run["status"] == "interrupted" for run in runs)
    erase(db_settings, "DELETE_LOCAL_APPLICATION_DATA")
    with connect(db_settings) as db:
        assert db.execute("SELECT count(*) AS n FROM discovery_secrets").fetchone() == {"n": 0}


def test_source_change_blocks_package_capture(
    signed_client: TestClient, db_settings: Settings
) -> None:
    source = enable(signed_client, add_source(signed_client))
    endpoint = f"/api/v1/discovery/sources/{source['id']}/sync"
    reader(signed_client, lambda _: DiscoveryBatch(items=[item()], complete=True))
    signed_client.post(endpoint)
    found = signed_client.get("/api/v1/discovery/items").json()["items"][0]
    job = signed_client.post(
        f"/api/v1/discovery/items/{found['id']}/save", json={"expected_version": 1}
    ).json()
    due(db_settings, source)
    reader(
        signed_client, lambda _: DiscoveryBatch(items=[item("Changed requirements")], complete=True)
    )
    signed_client.post(endpoint)
    with connect(db_settings) as db:
        row = db.execute("SELECT * FROM records WHERE id=%s", (job["id"],)).fetchone()
        assert row
        with pytest.raises(Problem) as failure:
            capture(
                db,
                row["owner_id"],
                row["id"],
                StrategyRequest(job_version=job["version"], profile_version=1, fact_ids=[uuid4()]),
            )
        assert failure.value.code == "SOURCE_UPDATE_PENDING"
