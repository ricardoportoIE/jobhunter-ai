from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from test_discovery import add_source, enable

from jobhunter_api.discovery_sync import Reader, synchronise
from jobhunter_api.greenhouse import DiscoveredItem, DiscoveryBatch, read_greenhouse
from jobhunter_api.settings import Settings
from jobhunter_api.source_http import SourceFailure, request_json, retry_time
from jobhunter_api.store import Row, connect


def item(title: str = "Junior Python developer") -> DiscoveredItem:
    return DiscoveredItem(
        external_id="42",
        title=title,
        location="Dublin",
        url="https://example.com/jobs/42",
        raw_text="Python projects required.",
    )


def reader(client: TestClient, value: Reader) -> None:
    cast(FastAPI, client.app).state.discovery_reader = value


def due(settings: Settings, source: Row) -> None:
    with connect(settings) as db:
        db.execute(
            "UPDATE records SET data=data || '{\"next_sync_at\":null}'::jsonb WHERE id=%s",
            (source["id"],),
        )


def test_sync_revisions_promotion_and_absence(
    signed_client: TestClient, db_settings: Settings
) -> None:
    client = signed_client
    source = enable(client, add_source(client))
    endpoint = f"/api/v1/discovery/sources/{source['id']}/sync"
    reader(client, lambda _: DiscoveryBatch(items=[item()], complete=True))
    first = client.post(endpoint)
    assert first.status_code == 200, first.text
    assert first.json()["counts"]["new"] == 1
    assert client.post(endpoint).status_code == 429
    found = client.get("/api/v1/discovery/items?unread=true&q=Dublin").json()["items"][0]
    saved = client.post(
        f"/api/v1/discovery/items/{found['id']}/save", json={"expected_version": found["version"]}
    )
    assert saved.status_code == 200, saved.text
    job = saved.json()
    assert job["title"] == item().title and job["status"] == "DISCOVERED"
    assert job["salary"] is None and job["sponsorship"] is None
    due(db_settings, source)
    reader(client, lambda _: DiscoveryBatch(items=[item("Senior developer")], complete=True))
    assert client.post(endpoint).json()["counts"]["changed"] == 1
    changed = client.get("/api/v1/discovery/items?unread=true").json()["items"][0]
    assert changed["notice"] == "changed"
    assert client.get(f"/api/v1/jobs/{job['id']}").json() == job
    assert (
        client.post(
            f"/api/v1/discovery/items/{found['id']}/save",
            json={"expected_version": found["version"]},
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/v1/discovery/items/{changed['id']}/save",
            json={"expected_version": changed["version"]},
        ).json()["id"]
        == job["id"]
    )
    due(db_settings, source)
    reader(client, lambda _: DiscoveryBatch(complete=True))
    assert client.post(endpoint).json()["counts"]["missing"] == 1
    assert client.get("/api/v1/discovery/items").json()["items"][0]["availability"] == "not_listed"
    assert len(client.get("/api/v1/candidate/export").json()["snapshots"]) == 2


def test_conditional_reads_failures_and_pause(
    signed_client: TestClient, db_settings: Settings
) -> None:
    client = signed_client
    source = enable(client, add_source(client))
    endpoint = f"/api/v1/discovery/sources/{source['id']}/sync"
    reader(client, lambda _: DiscoveryBatch(items=[item()], complete=True, etag='"v1"'))
    client.post(endpoint)
    due(db_settings, source)
    reader(client, lambda _: DiscoveryBatch(not_modified=True))
    assert client.post(endpoint).json()["status"] == "unchanged"
    assert client.get("/api/v1/discovery/items").json()["items"][0]["version"] == 1
    retry_at = (datetime.now(UTC) + timedelta(days=2)).isoformat()

    def limited(_: Row) -> DiscoveryBatch:
        raise SourceFailure("SOURCE_RATE_LIMIT", retry_at=retry_at)

    due(db_settings, source)
    reader(client, limited)
    assert client.post(endpoint).json()["status"] == "failed"
    assert client.get("/api/v1/discovery/sources").json()[0]["next_sync_at"] == retry_at
    assert client.get("/api/v1/discovery/items").json()["items"][0]["availability"] == "listed"

    def pause(_: Row) -> DiscoveryBatch:
        current = client.get("/api/v1/discovery/sources").json()[0]
        client.patch(
            f"/api/v1/discovery/sources/{source['id']}",
            json={"expected_version": current["version"], "enabled": False},
        )
        return DiscoveryBatch(items=[item("Changed while paused")], complete=True)

    due(db_settings, source)
    reader(client, pause)
    assert client.post(endpoint).json()["status"] == "cancelled"
    assert client.get("/api/v1/discovery/items").json()["items"][0]["title"] == item().title
    assert client.post(endpoint).status_code == 409


def test_global_network_lock_and_access_failure(
    signed_client: TestClient, db_settings: Settings
) -> None:
    client = signed_client
    source = enable(client, add_source(client))
    endpoint = f"/api/v1/discovery/sources/{source['id']}/sync"
    with connect(db_settings) as lane:
        lane.execute("SELECT pg_advisory_lock(71004)")
        lane.commit()
        assert client.post(endpoint).status_code == 409
        lane.execute("SELECT pg_advisory_unlock(71004)")

    def denied(_: Row) -> DiscoveryBatch:
        raise SourceFailure("SOURCE_ACCESS_DENIED", stop=True)

    reader(client, denied)
    assert client.post(endpoint).json()["error_code"] == "SOURCE_ACCESS_DENIED"
    assert not client.get("/api/v1/discovery/sources").json()[0]["enabled"]


def test_expiry_and_owner_isolation(signed_client: TestClient, db_settings: Settings) -> None:
    client = signed_client
    source = enable(client, add_source(client))
    with connect(db_settings) as db:
        db.execute(
            'UPDATE records SET data=data || \'{"review_until":"2000-01-01"}\'::jsonb WHERE id=%s',
            (source["id"],),
        )
    assert not client.get("/api/v1/discovery/sources").json()[0]["ready"]
    assert client.post(f"/api/v1/discovery/sources/{source['id']}/sync").status_code == 409
    from uuid import uuid4

    from jobhunter_api.errors import Problem

    with pytest.raises(Problem) as failure:
        synchronise(db_settings, uuid4(), UUID(source["id"]), lambda _: DiscoveryBatch())
    assert failure.value.status == 401


def test_partial_batch_does_not_remove_missing_items(
    signed_client: TestClient, db_settings: Settings
) -> None:
    client = signed_client
    source = enable(client, add_source(client))
    endpoint = f"/api/v1/discovery/sources/{source['id']}/sync"
    reader(client, lambda _: DiscoveryBatch(items=[item()], complete=True))
    client.post(endpoint)
    due(db_settings, source)
    reader(client, lambda _: DiscoveryBatch(complete=False))
    assert client.post(endpoint).json()["counts"]["missing"] == 0
    assert client.get("/api/v1/discovery/items").json()["items"][0]["availability"] == "listed"


def test_greenhouse_content_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "jobs": [
            {
                "id": 42,
                "internal_job_id": 10,
                "title": "Developer",
                "absolute_url": "https://example.com/jobs/42",
                "location": {"name": "Dublin"},
                "content": "&lt;p&gt;Python &amp; APIs&lt;/p&gt;",
                "updated_at": "2026-09-20",
            }
        ],
        "meta": {"total": 1},
    }
    monkeypatch.setattr(
        "jobhunter_api.greenhouse.request_json", lambda *a, **kw: (200, {}, payload)
    )
    result = read_greenhouse({"data": {"reference": "synthetic"}})
    assert result.complete and result.items[0].raw_text == "Python & APIs"
    assert result.items[0].company is None
    payload["meta"] = {"total": 2}
    with pytest.raises(SourceFailure):
        read_greenhouse({"data": {"reference": "synthetic"}})


def test_transport_rejects_unknown_hosts_and_parses_retry() -> None:
    with pytest.raises(SourceFailure):
        request_json("https://127.0.0.1/internal")
    assert retry_time("120") is not None
    assert retry_time("Wed, 21 Oct 2030 07:28:00 GMT") == "2030-10-21T07:28:00+00:00"
    assert retry_time("invalid") is None
