"""Auth service helpers for the deferred foundation boundary."""

from __future__ import annotations

from app.schemas.auth import AuthHealthResponse


def get_auth_health() -> AuthHealthResponse:
    return AuthHealthResponse(
        status="ok",
        mode="deferred",
        implemented_boundaries=[
            "auth route namespace",
            "user persistence model",
            "secret hashing utilities",
        ],
        deferred_flows=[
            "identity provider integration",
            "token issuance and refresh",
            "session revocation",
            "role-based authorization",
        ],
    )
