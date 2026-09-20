import hashlib
import json
from io import BytesIO
from zipfile import ZipFile

from docx import Document
from fastapi.testclient import TestClient
from pypdf import PdfReader
from test_packages import generate, prepare


def test_approved_artifacts_same_facts_and_no_private_metadata(signed_client: TestClient) -> None:
    client = signed_client
    job, fact, strategy = prepare(client)
    package = generate(client, job, fact, strategy)
    path = f"/api/v1/packages/{package['id']}"
    assert client.get(path + "/download/cv.pdf?expected_version=1").status_code == 409
    approved = client.post(
        path + "/review",
        json={
            "expected_version": 1,
            "decision": "approve",
            "review_confirmed": True,
        },
    ).json()
    response = client.get(path + f"/download/bundle.zip?expected_version={approved['version']}")
    assert response.status_code == 200, response.text
    assert response.headers["x-document-sha256"] == hashlib.sha256(response.content).hexdigest()
    with ZipFile(BytesIO(response.content)) as bundle:
        manifest = json.loads(bundle.read("manifest.json"))
        for name, digest in manifest["files"].items():
            assert hashlib.sha256(bundle.read(name)).hexdigest() == digest
        for stem in ("cv", "cover-letter"):
            doc = Document(BytesIO(bundle.read(stem + ".docx")))
            assert fact["claim"] in "\n".join(p.text for p in doc.paragraphs)
            assert doc.core_properties.author == ""
            for style in ("Normal", "Title", "Heading 1"):
                assert "w:pBdr" not in doc.styles[style].element.xml
            pdf = PdfReader(BytesIO(bundle.read(stem + ".pdf")))
            assert len(pdf.pages) == 1
            assert fact["claim"] in " ".join(p.extract_text() for p in pdf.pages)
            assert "Alex Example" in pdf.pages[0].extract_text()
        exported = json.loads(bundle.read("package.json"))
        assert (
            "snapshot" not in exported and "source_ref" not in bundle.read("package.json").decode()
        )
        assert exported["content"] == approved["content"]
    assert client.get(path + "/download/cv.pdf?expected_version=1").status_code == 409
    client.delete(f"/api/v1/candidate/facts/{fact['id']}?expected_version={fact['version']}")
    assert client.get(path + "/download/cv.pdf?expected_version=2").status_code == 409
