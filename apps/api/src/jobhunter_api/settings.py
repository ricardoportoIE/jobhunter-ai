"""Explicit environment configuration; credentials have no fallback."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JOBHUNTER_", hide_input_in_errors=True)

    db_host: str = "127.0.0.1"
    db_port: int = Field(default=5433, ge=1, le=65535)
    db_name: str = "jobhunter"
    db_user: str = "jobhunter"
    db_password: SecretStr = Field(min_length=1)
