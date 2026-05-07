from uuid import UUID

from pydantic import BaseModel


class SummaryResponse(BaseModel):
    session_id: UUID
    summary: str
    sections: dict
    missing_fields: list[str]
    is_ready_for_generation: bool
