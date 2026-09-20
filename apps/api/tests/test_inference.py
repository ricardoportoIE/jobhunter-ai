import json

import httpx
import pytest
from openai import OpenAI
from pydantic import BaseModel, SecretStr

from jobhunter_api.ai_matching import ReliableMatch
from jobhunter_api.inference import OpenAIInference, ProviderFailure, constrained_schema
from jobhunter_api.package_domain import StrategyOutput
from jobhunter_api.settings import Settings


class Example(BaseModel):
    title: str | None


def test_ids_are_enumerated_without_cross_request_schema_leakage() -> None:
    payload = {"facts": [{"id": "f"}], "evidence": [{"id": "e"}], "requirements": [{"id": "r"}]}
    contract = constrained_schema(ReliableMatch, payload)
    assert contract["$defs"]["Grounding"]["properties"]["fact_id"]["enum"] == ["f"]
    assert contract["$defs"]["Grounding"]["properties"]["evidence_id"]["enum"] == ["e"]
    assert contract["$defs"]["SuggestedAssessment"]["properties"]["requirement_id"]["enum"] == ["r"]
    nullable = contract["$defs"]["Clarification"]["properties"]["requirement_id"]["anyOf"]
    assert nullable[0]["enum"] == ["r"] and nullable[1]["type"] == "null"
    strategy = constrained_schema(StrategyOutput, payload)
    assert strategy["properties"]["cv_fact_ids"]["items"]["enum"] == ["f"]
    assert (
        "enum"
        not in constrained_schema(ReliableMatch, {})["$defs"]["Grounding"]["properties"]["fact_id"]
    )


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


@pytest.mark.parametrize("refusal", [False, True])
@pytest.mark.parametrize("model", ["gpt-4.1-mini-2025-04-14", "gpt-5.6-luna"])
def test_sdk_success_and_refusal_keep_usage(refusal: bool, model: str) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["model"] == model
        if model == "gpt-5.6-luna":
            assert body["reasoning"] == {"effort": "high"} and "temperature" not in body
        else:
            assert body["temperature"] == 0 and "reasoning" not in body
        content = (
            {"type": "refusal", "refusal": "declined"}
            if refusal
            else {"type": "output_text", "text": '{"title":null}', "annotations": []}
        )
        return httpx.Response(
            200,
            headers={"x-request-id": "request-fixture"},
            json={
                "id": "resp-fixture",
                "object": "response",
                "created_at": 0,
                "status": "completed",
                "model": "gpt-4.1-mini-2025-04-14",
                "output": [
                    {
                        "id": "msg-fixture",
                        "type": "message",
                        "role": "assistant",
                        "status": "completed",
                        "content": [content],
                    }
                ],
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 2,
                    "total_tokens": 12,
                    "input_tokens_details": {"cached_tokens": 5},
                    "output_tokens_details": {"reasoning_tokens": 1},
                },
            },
        )

    adapter = OpenAIInference(
        Settings(db_password=SecretStr("test"), openai_api_key=SecretStr("synthetic-key"))
    )
    adapter.client = OpenAI(
        api_key="synthetic-key",
        max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(respond)),
    )
    result = adapter.complete(model, "extract", "data", Example, 200, effort="high")
    assert result.status == ("refused" if refusal else "completed")
    assert result.input_tokens == 10 and result.output_tokens == 2
    assert result.request_id == "request-fixture"
    assert result.reasoning_tokens == 1 and result.cached_input_tokens == 5
