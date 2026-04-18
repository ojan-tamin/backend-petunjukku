from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import MessageTypeEnum, SenderTypeEnum


class StudioMessageCreate(BaseModel):
    message_text: str = Field(..., min_length=1)
    sender_type: SenderTypeEnum
    message_type: MessageTypeEnum = MessageTypeEnum.TEXT


class StudioMessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    sender_type: SenderTypeEnum
    message_type: MessageTypeEnum
    message_text: str
    sequence_number: int
    created_at: datetime

    model_config = {"from_attributes": True}
