"""FastAPI entry point for the backend foundation."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import database_healthcheck
from app.routes.auth import router as auth_router
from app.routes.local_llm import router as local_llm_router
from app.routes.studio_sessions import router as studio_sessions_router


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
    )

    if settings.cors_allow_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allow_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(auth_router, prefix=settings.api_v1_prefix)
    app.include_router(local_llm_router, prefix=settings.api_v1_prefix)
    app.include_router(studio_sessions_router, prefix=settings.api_v1_prefix)

    @app.get("/", tags=["meta"])
    def root() -> dict[str, object]:
        return {
            "name": settings.app_name,
            "environment": settings.app_env,
            "docs_url": settings.docs_url,
            "routes": [
                f"{settings.api_v1_prefix}/auth/health",
                f"{settings.api_v1_prefix}/local-llm/status",
                f"{settings.api_v1_prefix}/local-llm/chat",
                f"{settings.api_v1_prefix}/studio-sessions/health",
                f"{settings.api_v1_prefix}/studio-sessions/workflows",
                f"{settings.api_v1_prefix}/studio-sessions",
                f"{settings.api_v1_prefix}/studio-sessions/{{session_id}}",
                f"{settings.api_v1_prefix}/studio-sessions/{{session_id}}/planning-state",
                f"{settings.api_v1_prefix}/studio-sessions/{{session_id}}/finalize",
            ],
        }

    @app.get("/health", tags=["meta"])
    def health_check() -> dict[str, str]:
        return {
            "status": "ok",
            "app_name": settings.app_name,
            "environment": settings.app_env,
            "database": "ok" if database_healthcheck() else "unavailable",
        }

    @app.get("/health/ready", tags=["meta"])
    def readiness_check() -> dict[str, str]:
        if not database_healthcheck():
            raise HTTPException(
                status_code=503,
                detail="Database connection is unavailable.",
            )
        return {"status": "ready"}

    return app


app = create_application()
