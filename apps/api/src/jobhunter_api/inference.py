"""Single explicit OpenAI adapter. No tools, retries, fallback providers or response storage."""

import json
from dataclasses import dataclass
from time import monotonic
from typing import Any, Protocol

from openai import APIStatusError, OpenAI
from pydantic import BaseModel

from jobhunter_api.settings import Effort, Settings

CONTRACT_VERSION = "structured-ids-1.0"


class ProviderFailure(Exception):
    def __init__(self, code: str, *, charge_unknown: bool) -> None:
        self.code = code
        self.charge_unknown = charge_unknown
        super().__init__(code)


@dataclass(frozen=True)
class Completion:
    text: str
    input_tokens: int
    output_tokens: int
    request_id: str | None
    elapsed_ms: int
    status: str
    reasoning_tokens: int = 0
    cached_input_tokens: int = 0
    web_search_calls: int = 0


class StructuredInference(Protocol):
    def complete(
        self,
        model: str,
        prompt: str,
        data: str,
        schema: type[BaseModel],
        max_output: int,
        *,
        effort: Effort | None = None,
    ) -> Completion: ...


class EmbeddingInference(Protocol):
    def embed(self, texts: list[str]) -> Completion: ...


def strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """All response fields are required; absence is represented with null."""
    if schema.get("type") == "object":
        schema["additionalProperties"] = False
        schema["required"] = list(schema.get("properties", {}))
    schema.pop("default", None)
    for value in schema.values():
        if isinstance(value, dict):
            strict_schema(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    strict_schema(item)
    return schema


def constrained_schema(schema: type[BaseModel], payload: dict[str, Any]) -> dict[str, Any]:
    """Constrain supplied IDs at generation time; semantic/ownership checks still run afterward."""
    contract = strict_schema(schema.model_json_schema())
    facts = sorted({str(f["id"]) for f in payload.get("facts", [])})
    evidence = sorted({str(e["id"]) for e in payload.get("evidence", [])})
    requirements = sorted(
        {
            str(r["id"])
            for r in payload.get("requirements", payload.get("job", {}).get("requirements", []))
        }
    )
    permitted = {
        "fact_id": facts,
        "fact_ids": facts,
        "cv_fact_ids": facts,
        "letter_fact_ids": facts,
        "evidence_id": evidence,
        "requirement_id": requirements,
    }

    def restrict(node: dict[str, Any], ids: list[str]) -> None:
        if node.get("type") == "array":
            restrict(node["items"], ids)
        elif "anyOf" in node:
            for branch in node["anyOf"]:
                restrict(branch, ids)
        elif node.get("type") == "string":
            node["enum"] = ids

    def visit(node: dict[str, Any]) -> None:
        for field, child in node.get("properties", {}).items():
            ids = permitted.get(field)
            if ids and len(ids) <= 250:
                restrict(child, ids)
        for value in node.values():
            if isinstance(value, dict):
                visit(value)
            elif isinstance(value, list):
                for child in value:
                    if isinstance(child, dict):
                        visit(child)

    visit(contract)
    return contract


class OpenAIInference:
    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise ProviderFailure("AI_NOT_CONFIGURED", charge_unknown=False)
        self.client = OpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            base_url="https://api.openai.com/v1",
            max_retries=0,
            timeout=settings.ai_timeout_seconds,
        )

    def embed(self, texts: list[str]) -> Completion:
        import json

        start = monotonic()
        try:
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=texts,
                dimensions=256,
                encoding_format="float",
            )
        except APIStatusError as exc:
            detail = exc.body.get("error", exc.body) if isinstance(exc.body, dict) else {}
            code = (
                "PROVIDER_INSUFFICIENT_QUOTA"
                if isinstance(detail, dict) and detail.get("code") == "insufficient_quota"
                else f"PROVIDER_HTTP_{exc.status_code}"
            )
            raise ProviderFailure(
                code, charge_unknown=exc.status_code >= 500 or exc.status_code == 408
            ) from None
        except Exception:
            raise ProviderFailure("PROVIDER_UNAVAILABLE", charge_unknown=True) from None
        ordered = sorted(response.data, key=lambda item: item.index)
        if [item.index for item in ordered] != list(range(len(texts))):
            raise ProviderFailure("EMBEDDINGS_MISSING", charge_unknown=True)
        return Completion(
            json.dumps({"vectors": [item.embedding for item in ordered]}),
            response.usage.prompt_tokens,
            0,
            response._request_id,
            round((monotonic() - start) * 1000),
            "completed",
        )

    def complete(
        self,
        model: str,
        prompt: str,
        data: str,
        schema: type[BaseModel],
        max_output: int,
        *,
        effort: Effort | None = None,
    ) -> Completion:
        start = monotonic()
        options: dict[str, Any] = (
            {"reasoning": {"effort": effort or "high"}}
            if model == "gpt-5.6-luna"
            else {"temperature": 0}
        )
        try:
            payload = json.loads(data)
        except ValueError:
            payload = {}
        contract = constrained_schema(schema, payload if isinstance(payload, dict) else {})
        try:
            response = self.client.responses.create(
                model=model,
                instructions=prompt,
                input=data,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": schema.__name__,
                        "strict": True,
                        "schema": contract,
                    }
                },
                max_output_tokens=max_output,
                store=False,
                **options,
            )
        except APIStatusError as exc:
            # Do not propagate headers, request bodies, credentials or provider error text.
            code = f"PROVIDER_HTTP_{exc.status_code}"
            detail = exc.body.get("error", exc.body) if isinstance(exc.body, dict) else {}
            if isinstance(detail, dict) and detail.get("code") == "insufficient_quota":
                code = "PROVIDER_INSUFFICIENT_QUOTA"
            raise ProviderFailure(
                code, charge_unknown=exc.status_code >= 500 or exc.status_code == 408
            ) from None
        except Exception:
            raise ProviderFailure("PROVIDER_UNAVAILABLE", charge_unknown=True) from None
        if response.usage is None:
            raise ProviderFailure("USAGE_MISSING", charge_unknown=True)
        refused = any(
            item.type == "message" and any(part.type == "refusal" for part in item.content)
            for item in response.output
        )
        return Completion(
            text=response.output_text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            request_id=response._request_id,
            elapsed_ms=round((monotonic() - start) * 1000),
            status="refused" if refused else response.status or "unknown",
            reasoning_tokens=(response.usage.output_tokens_details.reasoning_tokens or 0)
            if response.usage.output_tokens_details
            else 0,
            cached_input_tokens=(response.usage.input_tokens_details.cached_tokens or 0)
            if response.usage.input_tokens_details
            else 0,
        )
