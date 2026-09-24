"""Sandbox acceptance and authorisation tests against real PostgreSQL transactions."""

from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb
from test_packages import generate, prepare

from jobhunter_api import sandbox_channel, submission_domain
from jobhunter_api.settings import Settings
from jobhunter_api.store import Row, connect


def setup(client: TestClient) -> tuple[Row, Row, Row]:
    job, fact, strategy = prepare(client)
    package = generate(client, job, fact, strategy)
    response = client.post(
        f"/api/v1/packages/{package['id']}/review",
        json={
            "expected_version": package["version"],
            "decision": "approve",
            "review_confirmed": True,
        },
    )
    assert response.status_code == 200, response.text
    package = response.json()
    response = client.post(
        f"/api/v1/jobs/{job['id']}/analyse",
        json={
            "job_version": job["version"],
            "profile_version": strategy["snapshot"]["profile"]["version"],
            "review_confirmed": True,
            "assessments": [],
        },
    )
    assert response.status_code == 201, response.text
    app = client.post("/api/v1/applications", json={"job_id": job["id"]}).json()
    response = client.post(
        f"/api/v1/applications/{app['id']}/submission",
        json={
            "package_id": package["id"],
            "package_version": package["version"],
        },
    )
    assert response.status_code == 200, response.text
    return app, package, response.json()


def authorise(client: TestClient, workflow: Row) -> Row:
    response = client.post(
        f"/api/v1/submissions/{workflow['id']}/authorise",
        json={
            "expected_version": workflow["version"],
            "payload_hash": workflow["payload_hash"],
            "submission_confirmed": True,
        },
    )
    assert response.status_code == 200, response.text
    return dict(response.json())


def action(client: TestClient, workflow: Row, verb: str) -> Row:
    response = client.post(
        f"/api/v1/submissions/{workflow['id']}/{verb}",
        json={"expected_version": workflow["version"]},
    )
    assert response.status_code == 200, response.text
    return dict(response.json())


def test_separate_approval_receipt_replay_and_export(signed_client: TestClient) -> None:
    client = signed_client
    app, package, workflow = setup(client)
    url = f"/api/v1/submissions/{workflow['id']}"
    assert (
        client.post(url + "/execute", json={"expected_version": workflow["version"]}).status_code
        == 409
    )
    approval = {"expected_version": workflow["version"], "payload_hash": workflow["payload_hash"]}
    assert client.post(url + "/authorise", json=approval).status_code == 422
    assert (
        client.post(
            url + "/authorise",
            json={**approval, "submission_confirmed": True, "payload_hash": "0" * 64},
        ).status_code
        == 409
    )
    approved = authorise(client, workflow)
    result = action(client, approved, "execute")
    assert result["status"] == "SIMULATED" and result["receipt"]["simulated"]
    assert result["receipt"]["payload_hash"] == workflow["payload_hash"]
    assert action(client, approved, "execute") == result
    assert action(client, result, "reconcile") == result
    tracker = client.get(f"/api/v1/applications/{app['id']}").json()
    assert tracker["status"] == "SHORTLISTED" and tracker["submission"] is None
    assert len(tracker["events"]) == 2 and tracker["events"][-1]["origin"] == "local_sandbox"
    assert (
        client.post(
            f"/api/v1/applications/{app['id']}/submission",
            json={"package_id": package["id"], "package_version": package["version"]},
        ).status_code
        == 409
    )
    exported = client.get("/api/v1/candidate/export").json()
    records = exported["records"]
    approvals = [
        s
        for s in exported["snapshots"]
        if s["kind"] == "submission_workflow" and s["data"]["status"] == "APPROVED"
    ]
    assert len(approvals) == 1
    assert approvals[0]["data"]["authorisation"]["payload_hash"] == workflow["payload_hash"]
    assert len([r for r in records if r["kind"] == "sandbox_receipt"]) == 1
    assert [h["status"] for h in result["history"]] == [
        "NEEDS_REVIEW",
        "APPROVED",
        "DISPATCHING",
        "SIMULATED",
    ]
    assert "evidence" not in workflow["payload"]["content"]


def test_expiry_and_cancel_require_fresh_confirmation(
    signed_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = signed_client
    app, package, workflow = setup(client)
    approved = authorise(client, workflow)
    future = submission_domain.now() + timedelta(minutes=16)
    with monkeypatch.context() as patch:
        patch.setattr(submission_domain, "now", lambda: future)
        response = client.post(
            f"/api/v1/submissions/{workflow['id']}/execute",
            json={"expected_version": approved["version"]},
        )
        assert response.status_code == 409
    cancelled = action(client, approved, "cancel")
    assert cancelled["authorisation"] is None
    assert (
        client.post(
            f"/api/v1/submissions/{workflow['id']}/execute",
            json={"expected_version": cancelled["version"]},
        ).status_code
        == 409
    )
    prepared = client.post(
        f"/api/v1/applications/{app['id']}/submission",
        json={"package_id": package["id"], "package_version": package["version"]},
    ).json()
    assert prepared["status"] == "NEEDS_REVIEW" and prepared["authorisation"] is None


@pytest.mark.parametrize(
    "change", ["profile", "job", "package", "evidence", "analysis", "application"]
)
def test_changed_inputs_block_delivery(signed_client: TestClient, change: str) -> None:
    client = signed_client
    app, package, workflow = setup(client)
    approved = authorise(client, workflow)
    if change == "profile":
        profile = client.get("/api/v1/candidate/profile").json()
        response = client.patch(
            "/api/v1/candidate/profile",
            json={"expected_version": profile["version"], "display_name": "Changed Name"},
        )
    elif change == "job":
        job = client.get(f"/api/v1/jobs/{app['job_id']}").json()
        response = client.patch(
            f"/api/v1/jobs/{job['id']}", json={"expected_version": job["version"], "archived": True}
        )
    elif change == "package":
        response = client.post(
            f"/api/v1/packages/{package['id']}/review",
            json={
                "expected_version": package["version"],
                "decision": "reject",
                "review_confirmed": True,
            },
        )
    elif change == "evidence":
        evidence = package["snapshot"]["evidence"][0]
        response = client.patch(
            f"/api/v1/candidate/evidence/{evidence['id']}",
            json={
                "expected_version": evidence["version"],
                "source_type": evidence["source_type"],
                "source_ref": evidence["source_ref"],
                "locator": evidence["locator"],
                "content": "Evidence corrected.",
                "review_confirmed": True,
            },
        )
    elif change == "analysis":
        response = client.post(
            f"/api/v1/jobs/{app['job_id']}/analyse",
            json={
                "job_version": package["snapshot"]["job"]["version"],
                "profile_version": package["snapshot"]["profile"]["version"],
                "assessments": [],
                "review_confirmed": True,
            },
        )
    else:
        response = client.post(
            f"/api/v1/applications/{app['id']}/events",
            json={"expected_version": app["version"], "to_status": "WITHDRAWN"},
        )
    assert response.is_success, response.text
    assert (
        client.post(
            f"/api/v1/submissions/{workflow['id']}/execute",
            json={"expected_version": approved["version"]},
        ).status_code
        == 409
    )
    assert client.get(f"/api/v1/applications/{app['id']}/submission").json()["receipt"] is None


@pytest.mark.parametrize("accepted", [False, True])
def test_lost_result_requires_reconciliation(
    signed_client: TestClient, monkeypatch: pytest.MonkeyPatch, accepted: bool
) -> None:
    client = signed_client
    app, _, workflow = setup(client)
    approved = authorise(client, workflow)
    original = sandbox_channel.deliver
    calls = 0

    def interrupted(settings: Settings, owner: UUID, identity: UUID, attempt: str) -> Row:
        nonlocal calls
        calls += 1
        if accepted:
            original(settings, owner, identity, attempt)
        raise TimeoutError("Synthetic lost acknowledgement")

    with monkeypatch.context() as patch:
        patch.setattr(sandbox_channel, "deliver", interrupted)
        uncertain = action(client, approved, "execute")
        assert uncertain["status"] == "UNKNOWN"
        assert action(client, approved, "execute")["status"] == "UNKNOWN"
        assert calls == 1
    result = action(client, uncertain, "reconcile")
    assert result["status"] == ("SIMULATED" if accepted else "FAILED")
    if not accepted:
        assert result["authorisation"] is None
        assert action(client, authorise(client, result), "execute")["status"] == "SIMULATED"
    assert len(client.get(f"/api/v1/applications/{app['id']}").json()["events"]) == 2


def test_scope_owner_csrf_and_unapproved_package(
    signed_client: TestClient, db_settings: Settings
) -> None:
    client = signed_client
    app, package, workflow = setup(client)
    for verb in ("authorise", "execute", "cancel", "reconcile"):
        body = (
            {
                "expected_version": 1,
                "payload_hash": workflow["payload_hash"],
                "submission_confirmed": True,
            }
            if verb == "authorise"
            else {"expected_version": 1}
        )
        assert client.post(f"/api/v1/submissions/{uuid4()}/{verb}", json=body).status_code == 404
    assert (
        client.post(
            f"/api/v1/submissions/{workflow['id']}/execute",
            json={"expected_version": 1},
            headers={"X-CSRF-Token": "wrong"},
        ).status_code
        == 403
    )
    with connect(db_settings) as db:
        row = db.execute("SELECT * FROM records WHERE id=%s", (workflow["id"],)).fetchone()
        assert row
        other = uuid4()
        db.execute("ALTER TABLE users DROP CONSTRAINT users_single_user_key")
        db.execute(
            "INSERT INTO users (id,username,password_hash) VALUES (%s,'other','unused')", (other,)
        )
        db.execute("UPDATE records SET owner_id=%s WHERE id=%s", (other, workflow["id"]))
    try:
        assert client.get(f"/api/v1/applications/{app['id']}/submission").json() is None
        for verb in ("authorise", "execute", "cancel", "reconcile"):
            body = {"expected_version": 1}
            if verb == "authorise":
                body.update(payload_hash=workflow["payload_hash"], submission_confirmed=True)
            assert (
                client.post(f"/api/v1/submissions/{workflow['id']}/{verb}", json=body).status_code
                == 404
            )
    finally:
        with connect(db_settings) as db:
            db.execute("DELETE FROM users WHERE id=%s", (other,))
            db.execute("ALTER TABLE users ADD CONSTRAINT users_single_user_key UNIQUE(single_user)")
    assert (
        client.post(
            f"/api/v1/applications/{app['id']}/submission",
            json={"package_id": package["id"], "package_version": 999},
        ).status_code
        == 409
    )


@pytest.mark.parametrize(
    "field,value", [("recommendation", "BLOCKED"), ("clarifications", [{"key": "pending"}])]
)
def test_analysis_gates(
    signed_client: TestClient, db_settings: Settings, field: str, value: object
) -> None:
    client = signed_client
    app, package, _ = setup(client)
    with connect(db_settings) as db:
        db.execute(
            "UPDATE records SET data=jsonb_set(data,%s,%s) WHERE kind='match'",
            ([field], Jsonb(value)),
        )
    response = client.post(
        f"/api/v1/applications/{app['id']}/submission",
        json={"package_id": package["id"], "package_version": package["version"]},
    )
    assert (
        response.status_code == 409
        and response.json()["error"]["code"] == "APPLICATION_REVIEW_REQUIRED"
    )
