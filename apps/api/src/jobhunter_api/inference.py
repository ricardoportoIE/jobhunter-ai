"""Single explicit OpenAI adapter. No tools, retries, fallback providers or response storage."""

from dataclasses import dataclass
from time import monotonic
from typing import Any, Protocol

from openai import APIStatusError, OpenAI
from pydantic import BaseModel

from jobhunter_api.settings import Settings


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


class StructuredInference(Protocol):
    def complete(
        self, model: str, prompt: str, data: str, schema: type[BaseModel], max_output: int
    ) -> Completion: ...


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

    def complete(
        self, model: str, prompt: str, data: str, schema: type[BaseModel], max_output: int
    ) -> Completion:
        start = monotonic()
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
                        "schema": strict_schema(schema.model_json_schema()),
                    }
                },
                max_output_tokens=max_output,
                store=False,
                temperature=0,
            )
        except APIStatusError as exc:
            # Do not propagate headers, request bodies, credentials or provider error text.
            raise ProviderFailure(
                f"PROVIDER_HTTP_{exc.status_code}", charge_unknown=exc.status_code >= 500
            ) from None
        except Exception:
            raise ProviderFailure("PROVIDER_UNAVAILABLE", charge_unknown=True) from None
        if response.usage is None:
            raise ProviderFailure("USAGE_MISSING", charge_unknown=True)
        return Completion(
            text=response.output_text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            request_id=response._request_id,
            elapsed_ms=round((monotonic() - start) * 1000),
            status=response.status or "unknown",
        )
