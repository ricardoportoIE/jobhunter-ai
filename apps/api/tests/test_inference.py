import json

import httpx
import pytest
from openai import OpenAI
from pydantic import BaseModel, SecretStr

from jobhunter_api.inference import OpenAIInference, ProviderFailure
from jobhunter_api.settings import Settings


class Example(BaseModel):
    title: str | None


def test_provider_contract_and_redaction() -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(401, json={"error": {"message": "sensitive provider text"}})

    adapter = OpenAIInference(
        Settings(db_password=SecretStr("test"), openai_api_key=SecretStr("synthetic-key"))
    )
    adapter.client = OpenAI(
        api_key="synthetic-key",
        max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(respond)),
    )
    with pytest.raises(ProviderFailure) as error:
        adapter.complete("gpt-4.1-mini-2025-04-14", "extract", "untrusted text", Example, 200)
    assert str(error.value) == "PROVIDER_HTTP_401"
    assert error.value.charge_unknown is False
    assert len(requests) == 1
    body = json.loads(requests[0].content)
    assert body["store"] is False
    assert "tools" not in body
    assert body["text"]["format"]["schema"]["required"] == ["title"]
    assert body["text"]["format"]["schema"]["additionalProperties"] is False
