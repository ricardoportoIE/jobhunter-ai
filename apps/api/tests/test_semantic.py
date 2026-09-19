import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from jobhunter_api.inference import Completion
from jobhunter_api.semantic import cosine, vectors


def test_cosine_and_invalid_embeddings() -> None:
    assert cosine([1, 0], [1, 0]) == 1
    assert cosine([1, 0], [0, 1]) == 0
    with pytest.raises(ValueError):
        vectors(json.dumps({"vectors": [[0] * 256]}), 1)
    with pytest.raises(ValueError):
        vectors(json.dumps({"vectors": [[float("nan")] * 256]}), 1)


def test_versioned_search_cache_and_explicit_processing(signed_client: TestClient) -> None:
    client = signed_client
    job = client.post("/api/v1/jobs/import", json={"raw_text": "Python APIs in Dublin"}).json()
    index_body = {"kind": "job", "source_id": job["id"], "expected_version": 1}
    assert client.post("/api/v1/ai/index", json=index_body).status_code == 422
    index_body["external_processing_confirmed"] = True
    with patch("jobhunter_api.semantic.embedding_provider") as provider:
        provider.return_value.embed.return_value = Completion(
            json.dumps({"vectors": [[1.0] + [0.0] * 255]}), 10, 0, "test", 2, "completed"
        )
        result = client.post("/api/v1/ai/index", json=index_body)
        assert result.status_code == 200, result.text
        assert client.post("/api/v1/ai/index", json=index_body).json()["cached"]
        assert provider.return_value.embed.call_count == 1
        search = client.post(
            "/api/v1/ai/search",
            json={
                "query": "Python backend",
                "kind": "job",
                "external_processing_confirmed": True,
            },
        )
        assert search.json()["items"][0]["id"] == job["id"]
        assert search.json()["items"][0]["similarity"] == 1.0
    client.patch(f"/api/v1/jobs/{job['id']}", json={"expected_version": 1, "title": "Changed"})
    assert client.get("/api/v1/ai/index").json()["job"] == []
    empty = client.post(
        "/api/v1/ai/search",
        json={
            "query": "Python backend",
            "external_processing_confirmed": True,
        },
    )
    assert empty.json()["items"] == [] and empty.json()["run_id"] is None
