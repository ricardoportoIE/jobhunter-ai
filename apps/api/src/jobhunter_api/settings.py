"""Explicit environment configuration; credentials have no fallback."""

from datetime import date
from decimal import Decimal
from hashlib import sha256
from typing import Literal, cast

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

type Model = Literal["gpt-4.1-mini-2025-04-14", "gpt-4.1-nano-2025-04-14", "gpt-5.6-luna"]
type Effort = Literal["none", "low", "medium", "high", "xhigh", "max"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JOBHUNTER_", hide_input_in_errors=True)

    db_host: str = "127.0.0.1"
    db_port: int = Field(default=5433, ge=1, le=65535)
    db_name: str = "jobhunter"
    db_user: str = "jobhunter"
    db_password: SecretStr = Field(min_length=1)
    allowed_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]
    session_seconds: int = Field(default=28800, ge=60, le=86400)
    cookie_secure: bool = False
    app_db_user: str = "jobhunter_app"
    app_db_password: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    ai_model: Model = "gpt-4.1-mini-2025-04-14"
    ai_parsing_model: Model | None = None
    ai_matching_model: Model = "gpt-5.6-luna"
    ai_strategy_model: Model | None = None
    ai_review_model: Model = "gpt-5.6-luna"
    ai_research_model: Literal["gpt-5.6-luna"] = "gpt-5.6-luna"
    ai_parsing_effort: Effort = "high"
    ai_matching_effort: Effort = "high"
    ai_strategy_effort: Effort = "high"
    ai_review_effort: Effort = "high"
    ai_research_effort: Effort = "high"
    ai_parsing_prompt_suffix: str = Field(default="", max_length=4000)
    ai_matching_prompt_suffix: str = Field(default="", max_length=4000)
    ai_strategy_prompt_suffix: str = Field(default="", max_length=4000)
    ai_review_prompt_suffix: str = Field(default="", max_length=4000)
    ai_research_prompt_suffix: str = Field(default="", max_length=4000)
    ai_max_output_tokens: int = Field(default=8000, ge=1000, le=16000)
    ai_monthly_eur: Decimal = Field(default=Decimal("10"), gt=0, le=10)
    combined_monthly_eur: Decimal = Field(default=Decimal("25"), gt=0, le=25)
    # Conservative accounting allowance, NOT a live exchange-rate quote.
    ai_eur_per_usd: Decimal = Field(default=Decimal("1.25"), ge=1, le=5)
    ai_prices_reviewed: date = date(2026, 9, 20)
    ai_timeout_seconds: float = Field(default=180, ge=1, le=210)

    def prompt(self, operation: str, instructions: str, version: str) -> tuple[str, str]:
        task = {
            "parse": "parsing",
            "suggest": "matching",
            "suggest_review": "review",
            "strategy": "strategy",
            "research": "research",
        }.get(operation)
        suffix = str(getattr(self, f"ai_{task}_prompt_suffix", "")).strip()
        if not suffix:
            return instructions, version
        return (
            instructions + "\nAdditional operator guidance:\n" + suffix,
            version + "+" + sha256(suffix.encode()).hexdigest()[:12],
        )

    def policy(self, operation: str, override: str | None = None) -> tuple[str, Effort | None]:
        task = {
            "parse": "parsing",
            "suggest": "matching",
            "suggest_review": "review",
            "strategy": "strategy",
            "research": "research",
        }.get(operation)
        model = override or (getattr(self, f"ai_{task}_model") if task else None) or self.ai_model
        effort = getattr(self, f"ai_{task}_effort", "high") if model == "gpt-5.6-luna" else None
        return model, cast(Effort | None, effort)

    def runtime(self) -> "Settings":
        if self.app_db_password:
            return self.model_copy(
                update={"db_user": self.app_db_user, "db_password": self.app_db_password}
            )
        return self
