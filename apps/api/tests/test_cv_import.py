import io
import json
from unittest.mock import patch
from zipfile import ZipFile

import pytest
from docx import Document
from fastapi.testclient import TestClient
from reportlab.pdfgen.canvas import Canvas

from jobhunter_api.cv_import import read_cv, validate_cv
from jobhunter_api.cv_text_worker import extract
from jobhunter_api.errors import Problem
from jobhunter_api.inference import Completion

CV_TEXT = "Alex Example\nBuilt a Python API in 2025.\nPostgraduate Diploma in Computing."


def document() -> bytes:
    stream = io.BytesIO()
    doc = Document()
    for line in CV_TEXT.splitlines():
        doc.add_paragraph(line)
    doc.save(stream)
    return stream.getvalue()


def output() -> dict[str, object]:
    return {
        "display_name": "Alex Example",
        "warnings": [],
        "facts": [
            {
                "claim": "Built a Python API in 2025.",
                "category": "project",
                "quote": "Built a Python API in 2025.",
            },
            {
                "claim": "Postgraduate Diploma in Computing.",
                "category": "education",
                "quote": "Postgraduate Diploma in Computing.",
            },
        ],
    }


def test_real_docx_pdf_parser_and_rejected_uploads() -> None:
    assert "Built a Python API" in read_cv(document(), "cv.docx")
    stream = io.BytesIO()
    canvas = Canvas(stream)
    canvas.drawString(72, 700, CV_TEXT.replace("\n", " "))
    canvas.save()
    assert "Alex Example" in read_cv(stream.getvalue(), "cv.pdf")
    with pytest.raises(Problem):
        read_cv(b"not a Word document", "old.doc")
    with pytest.raises(Problem):
        read_cv(b"<html>not a PDF</html>", "cv.pdf")
    with pytest.raises(ValueError, match="CV_UNSAFE_DOCUMENT"):
        stream = io.BytesIO()
        with ZipFile(stream, "w") as archive:
            archive.writestr("word/document.xml", b'<!DOCTYPE x [<!ENTITY a "secret">]><x>&a;</x>')
        extract(stream.getvalue(), ".docx")
    with pytest.raises(ValueError, match="CV_UNSAFE_DOCUMENT"):
        stream = io.BytesIO()
        with ZipFile(stream, "w") as archive:
            archive.writestr("word/vbaProject.bin", b"macro")
        extract(stream.getvalue(), ".docx")
    data = output()
    data["display_name"] = "Invented Name"
    with pytest.raises(ValueError):
        validate_cv(data, CV_TEXT)


def test_cv_draft_edit_remove_add_apply_and_replay(signed_client: TestClient) -> None:
    client = signed_client
    original = client.get("/api/v1/candidate/profile").json()
    headers = {
        "Content-Type": "application/octet-stream",
        "X-CV-Filename": "cv.docx",
        "X-AI-Consent": "true",
    }
    with patch("jobhunter_api.cv_import.get_provider") as provider:
        provider.return_value.complete.return_value = Completion(
            json.dumps(output()), 100, 100, "fixture", 1, "completed"
        )
        response = client.post("/api/v1/candidate/cv/extract", content=document(), headers=headers)
        assert response.status_code == 200, response.text
        draft = response.json()
        assert client.get("/api/v1/candidate/facts").json() == []
        assert client.get("/api/v1/candidate/profile").json() == original
        payload = {
            key: draft[key]
            for key in (
                "display_name",
                "target_roles",
                "markets",
                "locations",
                "work_modes",
                "facts",
            )
        }
        payload["facts"] = [
            draft["facts"][0],
            {
                "claim": "I prefer hybrid roles.",
                "category": "preference",
                "quote": "",
                "sensitivity": "private",
            },
        ]
        changed = client.patch(
            f"/api/v1/candidate/cv/drafts/{draft['id']}",
            json={**payload, "expected_version": draft["version"]},
        )
        assert changed.status_code == 200, changed.text
        apply = {
            "expected_version": changed.json()["version"],
            "expected_profile_version": original["version"],
            "review_confirmed": True,
            "allowed_uses": ["matching", "cv"],
        }
        endpoint = f"/api/v1/candidate/cv/drafts/{draft['id']}/apply"
        assert client.post(endpoint, json={**apply, "review_confirmed": False}).status_code == 422
        applied = client.post(endpoint, json=apply)
        assert applied.status_code == 200, applied.text
        assert client.post(endpoint, json=apply).json() == applied.json()
        facts = client.get("/api/v1/candidate/facts").json()
        assert len(facts) == 2 and all(fact["status"] == "verified" for fact in facts)
        assert not any("Diploma" in fact["claim"] for fact in facts)
        assert {e["source_type"] for e in client.get("/api/v1/candidate/evidence").json()} == {
            "cv",
            "candidate_attestation",
        }
        assert client.get("/api/v1/candidate/profile").json()["status"] == "draft"
        assert provider.return_value.complete.call_count == 1


def test_cv_auth_consent_size_and_profile_conflict(signed_client: TestClient) -> None:
    client = signed_client
    headers = {"Content-Type": "application/octet-stream", "X-CV-Filename": "cv.docx"}
    assert (
        client.post("/api/v1/candidate/cv/extract", content=document(), headers=headers).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/candidate/cv/extract", content=b"x" * (4 * 1024 * 1024 + 1), headers=headers
        ).status_code
        == 413
    )
    with patch("jobhunter_api.cv_import.get_provider") as provider:
        provider.return_value.complete.return_value = Completion(
            json.dumps(output()), 100, 100, "fixture", 1, "completed"
        )
        draft = client.post(
            "/api/v1/candidate/cv/extract",
            content=document(),
            headers={**headers, "X-AI-Consent": "true"},
        ).json()
    current = client.get("/api/v1/candidate/profile").json()
    changed = client.patch(
        "/api/v1/candidate/profile",
        json={"expected_version": current["version"], "display_name": "Existing reviewed name"},
    )
    assert changed.status_code == 200
    response = client.post(
        f"/api/v1/candidate/cv/drafts/{draft['id']}/apply",
        json={
            "expected_version": draft["version"],
            "expected_profile_version": current["version"],
            "review_confirmed": True,
            "allowed_uses": ["matching"],
        },
    )
    assert response.status_code == 409 and client.get("/api/v1/candidate/facts").json() == []
    client.cookies.clear()
    assert client.get("/api/v1/candidate/cv/drafts").status_code == 401
