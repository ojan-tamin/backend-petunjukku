"""Centralized runtime settings for the backend foundation."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized application configuration."""

    app_name: str = Field(default="backend-petunjukku", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    database_url: str = Field(
        default="sqlite:///./backend_petunjukku.db",
        alias="DATABASE_URL",
    )
    sql_echo: bool = Field(default=False, alias="SQL_ECHO")
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        alias="CORS_ALLOW_ORIGINS",
    )
    local_llm_enabled: bool = Field(default=False, alias="LOCAL_LLM_ENABLED")
    local_llm_backend: str = Field(default="auto", alias="LOCAL_LLM_BACKEND")
    local_llm_provider: str = Field(default="auto", alias="LOCAL_LLM_PROVIDER")
    local_llm_model_path: str = Field(default="", alias="LOCAL_LLM_MODEL_PATH")
    local_llm_device: str = Field(default="auto", alias="LOCAL_LLM_DEVICE")
    local_llm_max_new_tokens: int = Field(
        default=256,
        alias="LOCAL_LLM_MAX_NEW_TOKENS",
    )
    local_llm_temperature: float = Field(
        default=0.7,
        alias="LOCAL_LLM_TEMPERATURE",
    )
    local_llm_top_p: float = Field(default=0.95, alias="LOCAL_LLM_TOP_P")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @field_validator("app_env", mode="before")
    @classmethod
    def normalize_app_env(cls, value: object) -> str:
        normalized = str(value or "development").strip().lower()
        aliases = {
            "dev": "development",
            "prod": "production",
        }
        normalized = aliases.get(normalized, normalized)
        allowed = {"development", "test", "staging", "production"}
        if normalized not in allowed:
            raise ValueError(f"APP_ENV must be one of: {', '.join(sorted(allowed))}")
        return normalized

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug(cls, value: object) -> bool:
        if isinstance(value, bool):
            return value
        normalized = str(value or "").strip().lower()
        if normalized in {"1", "true", "yes", "on", "debug", "development"}:
            return True
        if normalized in {"0", "false", "no", "off", "release", "prod", "production"}:
            return False
        return bool(value)

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_v1_prefix(cls, value: str) -> str:
        prefix = str(value or "").strip()
        if not prefix.startswith("/"):
            raise ValueError("API_V1_PREFIX must start with '/'.")
        return prefix.rstrip("/") or "/api/v1"

    @field_validator("local_llm_backend", mode="before")
    @classmethod
    def normalize_local_llm_backend(cls, value: object) -> str:
        normalized = str(value or "auto").strip().lower()
        allowed = {"auto", "ort-genai", "transformers"}
        if normalized not in allowed:
            raise ValueError(
                f"LOCAL_LLM_BACKEND must be one of: {', '.join(sorted(allowed))}"
            )
        return normalized

    @field_validator("local_llm_provider", mode="before")
    @classmethod
    def normalize_local_llm_provider(cls, value: object) -> str:
        normalized = str(value or "auto").strip().lower()
        allowed = {"auto", "cpu", "directml"}
        if normalized not in allowed:
            raise ValueError(
                f"LOCAL_LLM_PROVIDER must be one of: {', '.join(sorted(allowed))}"
            )
        return normalized

    @field_validator("local_llm_device", mode="before")
    @classmethod
    def normalize_local_llm_device(cls, value: object) -> str:
        normalized = str(value or "auto").strip().lower()
        allowed = {"auto", "cpu", "directml"}
        if normalized not in allowed:
            raise ValueError(
                f"LOCAL_LLM_DEVICE must be one of: {', '.join(sorted(allowed))}"
            )
        return normalized

    @field_validator("local_llm_model_path", mode="before")
    @classmethod
    def normalize_local_llm_model_path(cls, value: object) -> str:
        return str(value or "").strip()

    @field_validator("local_llm_max_new_tokens", mode="before")
    @classmethod
    def validate_local_llm_max_new_tokens(cls, value: object) -> int:
        token_count = int(value or 0)
        if token_count <= 0:
            raise ValueError("LOCAL_LLM_MAX_NEW_TOKENS must be greater than zero.")
        return token_count

    @field_validator("local_llm_temperature", mode="before")
    @classmethod
    def validate_local_llm_temperature(cls, value: object) -> float:
        temperature = float(value)
        if temperature < 0:
            raise ValueError("LOCAL_LLM_TEMPERATURE must be greater than or equal to zero.")
        return temperature

    @field_validator("local_llm_top_p", mode="before")
    @classmethod
    def validate_local_llm_top_p(cls, value: object) -> float:
        top_p = float(value)
        if not 0 < top_p <= 1:
            raise ValueError("LOCAL_LLM_TOP_P must be between 0 and 1.")
        return top_p

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def normalize_cors_origins(cls, value: object) -> list[str]:
        if isinstance(value, str):
            raw_value = value.strip()
            if not raw_value:
                return []
            if raw_value.startswith("["):
                parsed = json.loads(raw_value)
                if not isinstance(parsed, list):
                    raise ValueError("CORS_ALLOW_ORIGINS JSON value must be a list.")
                return [str(item).strip() for item in parsed if str(item).strip()]
            return [item.strip() for item in raw_value.split(",") if item.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return []

    @model_validator(mode="after")
    def validate_minimum_settings(self) -> "Settings":
        database_url = str(self.database_url or "").strip()
        if not database_url:
            raise ValueError("DATABASE_URL must not be empty.")

        supported_schemes = ("sqlite://", "postgresql://", "postgresql+psycopg://")
        if not database_url.startswith(supported_schemes):
            raise ValueError(
                "DATABASE_URL must use sqlite://, postgresql://, or postgresql+psycopg://."
            )

        if self.app_env == "production" and self.debug:
            raise ValueError("DEBUG must be false when APP_ENV=production.")

        return self

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def docs_url(self) -> str | None:
        return None if self.is_production else "/docs"

    @property
    def redoc_url(self) -> str | None:
        return None if self.is_production else "/redoc"

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def ai_contracts_dir(self) -> Path:
        return self.project_root / "app" / "ai_contracts"

    @property
    def database_url_is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def local_llm_model_dir(self) -> Path | None:
        if not self.local_llm_model_path:
            return None
        return Path(self.local_llm_model_path).expanduser()

    @property
    def local_llm_offload_dir(self) -> Path:
        return self.project_root / ".local_llm_offload"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
