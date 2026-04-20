"""Auth routes for the deferred auth boundary."""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.auth import AuthHealthResponse
from app.services.auth_service import get_auth_health

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/health", response_model=AuthHealthResponse)
def auth_health() -> AuthHealthResponse:
    return get_auth_health()
