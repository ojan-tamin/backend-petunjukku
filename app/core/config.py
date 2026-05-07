from typing import Any

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Petunjukku Backend"
    app_env: str = "development"
    debug: bool = True

    database_url: str = "sqlite:///./backend_petunjukku.db"
    sql_echo: bool = False

    secret_key: str = Field(
        default="change-this-secret",
        validation_alias=AliasChoices("SECRET_KEY", "JWT_SECRET_KEY"),
    )
    algorithm: str = Field(default="HS256", validation_alias=AliasChoices("ALGORITHM", "JWT_ALGORITHM"))
    access_token_expire_minutes: int = 60

    llm_provider: str = Field(default="openrouter", validation_alias=AliasChoices("LLM_PROVIDER"))
    llm_model: str = Field(
        default="moonshotai/kimi-k2.5:nitro",
        validation_alias=AliasChoices("LLM_MODEL", "ORCHESTRATION_CHAT_MODEL", "OPENROUTER_MODEL"),
    )
    llm_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LLM_API_KEY", "OPENROUTER_API_KEY"),
    )
    llm_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        validation_alias=AliasChoices("LLM_BASE_URL", "OPENROUTER_BASE_URL"),
    )
    llm_temperature: float = 0.2
    llm_max_tokens: int = 2048
    llm_timeout_seconds: float = Field(
        default=60.0,
        validation_alias=AliasChoices("LLM_TIMEOUT_SECONDS", "OPENROUTER_CHAT_TIMEOUT_SECONDS"),
    )
    llm_max_retries: int = Field(
        default=2,
        validation_alias=AliasChoices("LLM_MAX_RETRIES", "OPENROUTER_CHAT_MAX_RETRIES"),
    )
    llm_http_referer: str | None = Field(
        default="https://petunjukku.id",
        validation_alias=AliasChoices("LLM_HTTP_REFERER", "OPENROUTER_HTTP_REFERER"),
    )

    cors_allow_origins: list[str] = Field(default_factory=list)

    @field_validator("debug", "sql_echo", mode="before")
    @classmethod
    def parse_boolish(cls, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        text = str(value or "").strip().lower()
        if text in {"1", "true", "yes", "on", "debug", "development"}:
            return True
        if text in {"0", "false", "no", "off", "release", "prod", "production"}:
            return False
        return False

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if not value:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        text = str(value).strip()
        if text.startswith("[") and text.endswith("]"):
            import json

            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except json.JSONDecodeError:
                return []
        return [item.strip() for item in text.split(",") if item.strip()]

    @field_validator("llm_provider", mode="before")
    @classmethod
    def normalize_llm_provider(cls, value: Any) -> str:
        provider = str(value or "openrouter").strip().lower()
        aliases = {
            "openai-compatible": "openrouter",
            "openai_compatible": "openrouter",
            "openrouter.ai": "openrouter",
        }
        return aliases.get(provider, provider)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
