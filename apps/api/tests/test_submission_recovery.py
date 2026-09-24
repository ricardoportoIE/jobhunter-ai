"""Fault injection at committed checkpoints, including concurrent recovery."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb
from test_submissions import action, authorise, setup

from jobhunter_api import sandbox_channel, submission_domain, submissions
from jobhunter_api.main import create_app
from jobhunter_api.records import insert
from jobhunter_api.settings import Settings
from jobhunter_api.store import Connection, Row, connect


def receipt_count(settings: Settings) -> int:
    with connect(settings) as db:
        count = db.execute(
            "SELECT count(*) AS n FROM records WHERE kind='sandbox_receipt'"
        ).fetchone()
        assert count
        return int(count["n"])


@pytest.mark.parametrize("accepted", [False, True])
def test_concurrent_reconciliation_fences_late_acceptance(
    signed_client: TestClient,
    db_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    accepted: bool,
) -> None:
    client = signed_client
    app, _, workflow = setup(client)
    approved = authorise(client, workflow)
    reached, release = Event(), Event()
    original = sandbox_channel.deliver
    calls = 0

    def paused(settings: Settings, owner: UUID, identity: UUID, attempt: str) -> Row:
        nonlocal calls
        calls += 1
        receipt = original(settings, owner, identity, attempt) if accepted else None
        reached.set()
        assert release.wait(10)
        return receipt or original(settings, owner, identity, attempt)

    with monkeypatch.context() as patch, ThreadPoolExecutor(max_workers=1) as pool:
        patch.setattr(sandbox_channel, "deliver", paused)
        running = pool.submit(action, client, approved, "execute")
        try:
            assert reached.wait(10)
            persisted = client.get(f"/api/v1/applications/{app['id']}/submission").json()
            assert persisted["status"] == "DISPATCHING"
            assert action(client, approved, "execute")["status"] == "DISPATCHING"
            reconciled = action(client, persisted, "reconcile")
            assert reconciled["status"] == ("SIMULATED" if accepted else "FAILED")
        finally:
            release.set()
        assert running.result(timeout=10)["status"] == reconciled["status"]
    assert calls == 1 and receipt_count(db_settings) == int(accepted)
    if not accepted:
        assert action(client, authorise(client, reconciled), "execute")["status"] == "SIMULATED"
    assert receipt_count(db_settings) == 1
    assert len(client.get(f"/api/v1/applications/{app['id']}").json()["events"]) == 2


@pytest.mark.parametrize("accepted", [False, True])
def test_recovery_in_new_application_instance(
    signed_client: TestClient,
    db_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    accepted: bool,
) -> None:
    client = signed_client
    app, _, workflow = setup(client)
    approved = authorise(client, workflow)
    original = sandbox_channel.deliver

    def crash(settings: Settings, owner: UUID, identity: UUID, attempt: str) -> Row:
        if accepted:
            original(settings, owner, identity, attempt)
        raise RuntimeError("Synthetic process interruption")

    with monkeypatch.context() as patch:
        patch.setattr(sandbox_channel, "deliver", crash)
        action(client, approved, "execute")
    with TestClient(create_app(db_settings)) as restarted:
        restarted.cookies.update(client.cookies)
        restarted.headers.update(client.headers)
        saved = restarted.get(f"/api/v1/applications/{app['id']}/submission").json()
        result = action(restarted, saved, "reconcile")
        assert result["status"] == ("SIMULATED" if accepted else "FAILED")
    assert receipt_count(db_settings) == int(accepted)


def test_crash_after_acceptance_before_completion_is_recoverable(
    signed_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    db_settings: Settings,
) -> None:
    client = signed_client
    app, _, workflow = setup(client)
    approved = authorise(client, workflow)

    def crash(db: Connection, row: Row, receipt: Row) -> Row:
        raise RuntimeError("Synthetic completion failure")

    with monkeypatch.context() as patch:
        patch.setattr(submissions, "complete", crash)
        response = client.post(
            f"/api/v1/submissions/{workflow['id']}/execute",
            json={"expected_version": approved["version"]},
        )
        assert response.status_code == 500
    saved = client.get(f"/api/v1/applications/{app['id']}/submission").json()
    assert saved["status"] == "DISPATCHING" and receipt_count(db_settings) == 1
    assert action(client, saved, "reconcile")["status"] == "SIMULATED"


def test_receiver_unavailable_is_not_treated_as_non_delivery(
    signed_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = signed_client
    app, _, workflow = setup(client)
    approved = authorise(client, workflow)

    def unavailable(*args: object) -> Row:
        raise TimeoutError("Synthetic receiver outage")

    with monkeypatch.context() as patch:
        patch.setattr(sandbox_channel, "deliver", unavailable)
        unknown = action(client, approved, "execute")
        patch.setattr(sandbox_channel, "lookup", unavailable)
        response = client.post(
            f"/api/v1/submissions/{workflow['id']}/reconcile",
            json={"expected_version": unknown["version"]},
        )
        assert response.status_code == 500
    assert client.get(f"/api/v1/applications/{app['id']}/submission").json()["status"] == "UNKNOWN"
    assert action(client, unknown, "reconcile")["status"] == "FAILED"


@pytest.mark.parametrize("change", ["expiry", "withdrawal"])
def test_receiver_rechecks_after_checkpoint(
    signed_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    db_settings: Settings,
    change: str,
) -> None:
    client = signed_client
    app, _, workflow = setup(client)
    approved = authorise(client, workflow)
    original = sandbox_channel.deliver
    future = submission_domain.now() + timedelta(minutes=16)

    def changed(settings: Settings, owner: UUID, identity: UUID, attempt: str) -> Row:
        if change == "withdrawal":
            response = client.post(
                f"/api/v1/applications/{app['id']}/events",
                json={"expected_version": app["version"], "to_status": "WITHDRAWN"},
            )
            assert response.status_code == 200
        else:
            monkeypatch.setattr(submission_domain, "now", lambda: future)
        return original(settings, owner, identity, attempt)

    monkeypatch.setattr(sandbox_channel, "deliver", changed)
    result = action(client, approved, "execute")
    assert result["status"] == "UNKNOWN" and receipt_count(db_settings) == 0
    assert action(client, result, "reconcile")["status"] == "FAILED"


def test_future_employment_review_is_not_application_approval(
    signed_client: TestClient,
    db_settings: Settings,
) -> None:
    client = signed_client
    _, _, workflow = setup(client)
    with connect(db_settings) as db:
        db.execute(
            "UPDATE records SET data=jsonb_set(data,'{employment_gate}',%s) WHERE kind='match'",
            (Jsonb("REVIEW_BEFORE_START"),),
        )
    assert action(client, authorise(client, workflow), "execute")["status"] == "SIMULATED"
    with connect(db_settings) as db:
        match = db.execute("SELECT data FROM records WHERE kind='match'").fetchone()
        assert match and match["data"]["employment_gate"] == "REVIEW_BEFORE_START"


def test_reconciliation_rejects_mismatched_receipt(
    signed_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = signed_client
    _, _, workflow = setup(client)
    approved = authorise(client, workflow)

    def unavailable(*args: object) -> Row:
        raise TimeoutError("Synthetic lost response")

    monkeypatch.setattr(sandbox_channel, "deliver", unavailable)
    unknown = action(client, approved, "execute")
    monkeypatch.setattr(
        sandbox_channel, "lookup", lambda *args: {"payload_hash": "wrong", "attempt_id": "wrong"}
    )
    response = client.post(
        f"/api/v1/submissions/{workflow['id']}/reconcile",
        json={"expected_version": unknown["version"]},
    )
    assert response.status_code == 409 and response.json()["error"]["code"] == "RECEIPT_CONFLICT"


@pytest.mark.parametrize("change", ["expired_fact", "missing_source", "changed_source"])
def test_source_validity_is_rechecked_before_acceptance(
    signed_client: TestClient,
    db_settings: Settings,
    change: str,
) -> None:
    client = signed_client
    app, package, workflow = setup(client)
    approved = authorise(client, workflow)
    with connect(db_settings) as db:
        if change == "expired_fact":
            db.execute(
                "UPDATE records SET data=jsonb_set(data,'{valid_until}',%s) WHERE kind='fact'",
                (Jsonb((submission_domain.now() - timedelta(days=1)).isoformat()),),
            )
        else:
            row = db.execute("SELECT owner_id FROM records WHERE id=%s", (app["id"],)).fetchone()
            assert row
            insert(
                db,
                row["owner_id"],
                "discovery_item",
                {
                    "job_id": app["job_id"],
                    "content_hash": "new" if change == "changed_source" else "same",
                    "saved_hash": "same",
                    "availability": "not_listed" if change == "missing_source" else "listed",
                },
            )
    response = client.post(
        f"/api/v1/submissions/{workflow['id']}/execute",
        json={"expected_version": approved["version"]},
    )
    assert response.status_code == 409 and receipt_count(db_settings) == 0


def test_channel_cannot_be_selected_by_advert_or_request(signed_client: TestClient) -> None:
    client = signed_client
    app, package, workflow = setup(client)
    response = client.post(
        f"/api/v1/applications/{app['id']}/submission",
        json={
            "package_id": package["id"],
            "package_version": package["version"],
            "channel": "gmail",
            "recipient": "someone@example.test",
        },
    )
    assert response.status_code == 422
    assert workflow["payload"]["recipient"] == "sandbox://jobhunter/application-receiver"
    assert workflow["payload"]["channel"] == "local_sandbox"
