"""Centralized SQLAlchemy engine and session helpers."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from threading import RLock

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None
_lock = RLock()


def _build_engine() -> Engine:
    connect_args: dict[str, object] = {}
    engine_kwargs: dict[str, object] = {
        "echo": settings.sql_echo,
        "future": True,
        "pool_pre_ping": True,
    }

    if settings.database_url_is_sqlite:
        connect_args["check_same_thread"] = False
        if settings.database_url.endswith(":memory:"):
            engine_kwargs["poolclass"] = StaticPool

    engine = create_engine(
        settings.database_url,
        connect_args=connect_args,
        **engine_kwargs,
    )

    if settings.database_url_is_sqlite:

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def get_engine() -> Engine:
    global _engine
    with _lock:
        if _engine is None:
            _engine = _build_engine()
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    with _lock:
        if _session_factory is None:
            _session_factory = sessionmaker(
                bind=get_engine(),
                autoflush=False,
                autocommit=False,
                future=True,
            )
    return _session_factory


def get_db_session() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def database_healthcheck() -> bool:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def dispose_engine() -> None:
    global _engine, _session_factory
    with _lock:
        if _engine is not None:
            _engine.dispose()
        _engine = None
        _session_factory = None
