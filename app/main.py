from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine
from app.routes.audio import router as audio_router
from app.routes.auth import router as auth_router
from app.routes.documents import router as documents_router
from app.routes.documents import session_router as session_documents_router
from app.routes.studio_messages import router as studio_messages_router
from app.routes.studio_sessions import router as studio_sessions_router
from app.routes.studio_workflow import router as studio_workflow_router

app = FastAPI(title=settings.app_name)

if settings.cors_allow_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request, exc: Exception):
    from fastapi import HTTPException

    if isinstance(exc, HTTPException):
        raise exc
    detail = str(exc) if settings.debug else "Internal server error"
    return JSONResponse(status_code=500, content={"detail": detail})


app.include_router(auth_router)
app.include_router(studio_sessions_router, prefix="/sessions")
app.include_router(studio_messages_router, prefix="/sessions/{session_id}/messages")
app.include_router(studio_workflow_router, prefix="/sessions")
app.include_router(audio_router, prefix="/sessions")
app.include_router(session_documents_router, prefix="/sessions")
app.include_router(documents_router, prefix="/documents")

# Compatibility aliases for the original Repository B route shape.
app.include_router(studio_sessions_router, prefix="/studio/sessions")
app.include_router(
    studio_messages_router,
    prefix="/studio/sessions/{session_id}/messages",
)


@app.get("/")
def root():
    return {"message": "Petunjukku Backend is running"}


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "environment": settings.app_env,
    }


@app.get("/health/db")
def db_health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception:
        return {"status": "error", "database": "unavailable"}
