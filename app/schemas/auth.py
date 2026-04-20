"""Auth schemas for the deferred foundation boundary."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AuthHealthResponse(BaseModel):
    status: str = Field(..., description="Operational status of the auth boundary.")
    mode: str = Field(..., description="Current auth mode for this phase.")
    implemented_boundaries: list[str] = Field(
        ...,
        description="Auth-related surfaces that already exist in the foundation.",
    )
    deferred_flows: list[str] = Field(
        ...,
        description="Auth flows intentionally postponed to later phases.",
    )
