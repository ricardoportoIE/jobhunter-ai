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
from jobhunter_api.store import Row

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
                "source_start_line": 2,
                "source_end_line": 2,
            },
            {
                "claim": "Postgraduate Diploma in Computing.",
                "category": "education",
                "source_start_line": 3,
                "source_end_line": 3,
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
    assert read_cv(("\ufeff" + CV_TEXT).encode("utf-8"), "cv.md") == CV_TEXT
    with pytest.raises(Problem):
        read_cv(b"\xff\x00" + b"binary content" * 5, "cv.md")
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


def test_wrapped_source_ranges_preserve_exact_whitespace_and_intervening_lines() -> None:
    text = (
        "Alex Example\nBuilt a Python API with\n  PostgreSQL in 2025.\n"
        "Other coursework.\nFinal project: 10/10."
    )
    data: Row = {
        "display_name": "Alex Example",
        "warnings": [],
        "facts": [
            {
                "claim": "Built a Python API with PostgreSQL in 2025.",
                "category": "project",
                "source_start_line": 2,
                "source_end_line": 5,
            }
        ],
    }
    result = validate_cv(data, text)
    assert result["facts"][0]["quote"] == text.split("\n", 1)[1]
    assert "Other coursework." in result["facts"][0]["quote"]
    for start, end in [(0, 2), (3, 2), (2, 99)]:
        data["facts"][0].update(source_start_line=start, source_end_line=end)
        with pytest.raises(ValueError, match="source range"):
            validate_cv(data, text)
    with pytest.raises(ValueError, match="No supported facts"):
        validate_cv({"display_name": None, "facts": [], "warnings": []}, text)


def test_markdown_retry_after_invalid_output_is_explicit_and_cached(
    signed_client: TestClient,
) -> None:
    client = signed_client
    headers = {
        "Content-Type": "application/octet-stream",
        "X-CV-Filename": "cv.md",
        "X-AI-Consent": "true",
        "Idempotency-Key": "first-cv-attempt",
    }
    bad = output()
    bad["facts"][0]["source_end_line"] = 100  # type: ignore[index]
    with patch("jobhunter_api.cv_import.get_provider") as provider:
        provider.return_value.complete.side_effect = [
            Completion(json.dumps(bad), 100, 100, "fixture", 1, "completed"),
            Completion(json.dumps(output()), 100, 100, "fixture", 1, "completed"),
        ]
        failed = client.post(
            "/api/v1/candidate/cv/extract", content=CV_TEXT.encode(), headers=headers
        )
        assert failed.status_code == 422
        assert failed.json()["error"]["code"] == "CV_EXTRACTION_INVALID"
        assert client.get("/api/v1/candidate/cv/drafts").json() == []
        assert client.get("/api/v1/candidate/facts").json() == []
        assert (
            client.post(
                "/api/v1/candidate/cv/extract", content=CV_TEXT.encode(), headers=headers
            ).status_code
            == 409
        )
        headers["Idempotency-Key"] = "explicit-retry"
        success = client.post(
            "/api/v1/candidate/cv/extract", content=CV_TEXT.encode(), headers=headers
        )
        assert success.status_code == 200
        replay = client.post(
            "/api/v1/candidate/cv/extract", content=CV_TEXT.encode(), headers=headers
        )
        assert replay.json()["id"] == success.json()["id"]
        assert all(f["quote"] in CV_TEXT for f in success.json()["facts"])
        assert provider.return_value.complete.call_count == 2


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
