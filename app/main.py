from fastapi import FastAPI
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine
from app.routes.auth import router as auth_router
from app.routes.studio_messages import router as studio_messages_router
from app.routes.studio_sessions import router as studio_sessions_router

app = FastAPI(title=settings.app_name)


app.include_router(auth_router)
app.include_router(studio_sessions_router)
app.include_router(studio_messages_router)


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
    except Exception as e:
        return {"status": "error", "database": str(e)}
