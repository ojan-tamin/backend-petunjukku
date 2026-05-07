from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import TranscriptionStatusEnum
from app.schemas.studio_message import ChatResponse


class AudioRecordResponse(BaseModel):
    id: UUID
    session_id: UUID
    message_id: UUID | None
    file_path: str
    mime_type: str | None
    duration_seconds: int | None
    transcript: str | None
    transcription_status: TranscriptionStatusEnum
    created_at: datetime

    model_config = {"from_attributes": True}


class AudioUploadResponse(BaseModel):
    audio_record: AudioRecordResponse
    chat_response: ChatResponse | None = None
    stt_status: str
