from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import DocumentTypeEnum, SessionStatusEnum
from app.schemas.studio_message import PlanningStateResponse, StudioMessageResponse


class StudioSessionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    document_type: DocumentTypeEnum


class StudioSessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str | None
    document_type: DocumentTypeEnum
    current_stage: str
    status: SessionStatusEnum
    completion_score: int
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StudioSessionDetailResponse(StudioSessionResponse):
    planning_state: PlanningStateResponse | None = None
    messages: list[StudioMessageResponse] = Field(default_factory=list)
