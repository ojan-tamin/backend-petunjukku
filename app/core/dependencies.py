"""Shared FastAPI dependencies for the current foundation phase."""

from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.db.session import get_db_session
from app.services.local_llm_service import LocalLLMService


def get_settings_dependency() -> Settings:
    return settings


def get_db() -> Generator[Session, None, None]:
    yield from get_db_session()


@lru_cache(maxsize=1)
def get_local_llm_service() -> LocalLLMService:
    return LocalLLMService(settings)
