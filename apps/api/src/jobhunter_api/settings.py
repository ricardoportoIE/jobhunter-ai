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
    allowed_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]
    session_seconds: int = Field(default=28800, ge=60, le=86400)
    cookie_secure: bool = False
    app_db_user: str = "jobhunter_app"
    app_db_password: SecretStr | None = None

    def runtime(self) -> "Settings":
        if self.app_db_password:
            return self.model_copy(
                update={"db_user": self.app_db_user, "db_password": self.app_db_password}
            )
        return self
