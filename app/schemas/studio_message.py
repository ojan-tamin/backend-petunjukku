from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.enums import MessageTypeEnum, SenderTypeEnum


class StudioMessageCreate(BaseModel):
    content: str | None = Field(default=None, min_length=1)
    message_text: str | None = Field(default=None, min_length=1)
    message_type: MessageTypeEnum = MessageTypeEnum.TEXT

    @model_validator(mode="after")
    def require_content(self) -> "StudioMessageCreate":
        if not (self.content or self.message_text):
            raise ValueError("content is required")
        return self

    @property
    def text(self) -> str:
        return str(self.content or self.message_text or "").strip()


class StudioMessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    role: SenderTypeEnum
    message_type: MessageTypeEnum
    content: str
    sequence_number: int
    created_at: datetime

    model_config = {"from_attributes": True}


class PlanningStateResponse(BaseModel):
    current_stage: str
    collected_fields: dict
    missing_fields: list[str]
    completion_score: int
    is_ready_for_summary: bool
    is_ready_for_generation: bool
    version: int


class ChatResponse(BaseModel):
    session_id: UUID
    assistant_message: str
    planning_state: PlanningStateResponse
    current_stage: str
    completion_score: int
    is_ready_for_summary: bool
    is_ready_for_generation: bool
