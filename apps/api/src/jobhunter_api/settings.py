"""Explicit environment configuration; credentials have no fallback."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    ai_model: Literal["gpt-4.1-mini-2025-04-14", "gpt-4.1-nano-2025-04-14"] = (
        "gpt-4.1-mini-2025-04-14"
    )
    ai_monthly_eur: Decimal = Field(default=Decimal("10"), gt=0, le=10)
    combined_monthly_eur: Decimal = Field(default=Decimal("25"), gt=0, le=25)
    # Conservative accounting allowance, NOT a live exchange-rate quote.
    ai_eur_per_usd: Decimal = Field(default=Decimal("1.25"), ge=1, le=5)
    ai_prices_reviewed: date = date(2026, 9, 19)
    ai_timeout_seconds: float = Field(default=40, ge=1, le=45)

    def runtime(self) -> "Settings":
        if self.app_db_password:
            return self.model_copy(
                update={"db_user": self.app_db_user, "db_password": self.app_db_password}
            )
        return self
