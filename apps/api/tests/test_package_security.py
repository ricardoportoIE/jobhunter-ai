import json
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from test_packages import generate, prepare

from jobhunter_api.inference import Completion
from jobhunter_api.manage import erase
from jobhunter_api.settings import Settings
from jobhunter_api.store import connect


def test_foreign_package_and_csrf_are_rejected(
    signed_client: TestClient, db_settings: Settings
) -> None:
    client = signed_client
    job, fact, strategy = prepare(client)
    package = generate(client, job, fact, strategy)
    path = f"/api/v1/packages/{package['id']}"
    csrf = client.headers["X-CSRF-Token"]
    client.headers["X-CSRF-Token"] = "wrong"
    assert (
        client.post(
            path + "/review",
            json={"expected_version": 1, "decision": "approve", "review_confirmed": True},
        ).status_code
        == 403
    )
    client.headers["X-CSRF-Token"] = csrf
    stranger = uuid4()
    with connect(db_settings) as db:
        db.execute("ALTER TABLE users DROP CONSTRAINT users_single_user_key")
        db.execute(
            "INSERT INTO users(id,username,password_hash) VALUES (%s,'other','unused')", (stranger,)
        )
        db.execute("UPDATE records SET owner_id=%s WHERE id=%s", (stranger, package["id"]))
    try:
        for suffix in (
            "",
            "/history",
            "/diff?from_version=1",
            "/download/cv.pdf?expected_version=1",
        ):
            assert client.get(path + suffix).status_code == 404
    finally:
        with connect(db_settings) as db:
            db.execute("DELETE FROM users WHERE id=%s", (stranger,))
            db.execute("ALTER TABLE users ADD CONSTRAINT users_single_user_key UNIQUE(single_user)")
    client.cookies.clear()
    assert client.get(path).status_code == 401


def test_ai_cannot_add_claims_or_send_contact(signed_client: TestClient) -> None:
    client = signed_client
    job, fact, strategy = prepare(client)
    body = {
        "job_version": job["version"],
        "profile_version": strategy["snapshot"]["profile"]["version"],
        "fact_ids": [fact["id"]],
        "use_ai": True,
        "external_processing_confirmed": True,
        "contact_lines": ["DO-NOT-SEND@example.test"],
    }
    result = {**strategy["selection"], "cv_fact_ids": [str(uuid4())]}
    with patch("jobhunter_api.packages.get_provider") as provider:
        provider.return_value.complete.return_value = Completion(
            json.dumps(result), 100, 100, "synthetic", 1, "completed"
        )
        response = client.post(f"/api/v1/jobs/{job['id']}/strategy", json=body)
        assert response.status_code == 422, response.text
        transmitted = provider.return_value.complete.call_args.args[2]
        assert "DO-NOT-SEND" not in transmitted and "source_ref" not in transmitted
        assert "display_name" not in transmitted
    assert len(client.get(f"/api/v1/jobs/{job['id']}/strategies").json()) == 1


def test_private_export_and_erasure_include_package_history(
    signed_client: TestClient, db_settings: Settings
) -> None:
    client = signed_client
    job, fact, strategy = prepare(client)
    package = generate(client, job, fact, strategy)
    client.post(
        f"/api/v1/packages/{package['id']}/review",
        json={"expected_version": 1, "decision": "reject", "review_confirmed": True},
    )
    exported = client.get("/api/v1/candidate/export").json()
    assert any(r["kind"] == "package" for r in exported["records"])
    assert any(r["kind"] == "package" for r in exported["snapshots"])
    erase(db_settings, "DELETE_LOCAL_APPLICATION_DATA")
    with connect(db_settings) as db:
        records = db.execute(
            "SELECT count(*) AS n FROM records WHERE kind IN ('package','strategy')"
        ).fetchone()
        snapshots = db.execute(
            "SELECT count(*) AS n FROM snapshots WHERE kind='package'"
        ).fetchone()
        assert records is not None and records["n"] == 0
        assert snapshots is not None and snapshots["n"] == 0
