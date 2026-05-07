from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.audio_record import AudioRecord
from app.models.enums import MessageTypeEnum, TranscriptionStatusEnum
from app.models.user import User
from app.schemas.audio import AudioUploadResponse
from app.services.message_service import process_user_message
from app.services.session_service import require_session

router = APIRouter(tags=["Audio"])


@router.post("/{session_id}/audio", response_model=AudioUploadResponse, status_code=201)
async def upload_audio(
    session_id: UUID,
    file: UploadFile = File(...),
    transcript: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = require_session(db, current_user, session_id)

    upload_dir = Path("uploads") / "audio" / str(session.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_suffix = Path(file.filename or "audio.bin").suffix or ".bin"
    target = upload_dir / f"{uuid4().hex}{safe_suffix}"

    content = await file.read()
    target.write_bytes(content)

    audio_record = AudioRecord(
        session_id=session.id,
        file_path=str(target),
        mime_type=file.content_type,
        transcript=transcript,
        transcription_status=(
            TranscriptionStatusEnum.SUCCESS
            if transcript and transcript.strip()
            else TranscriptionStatusEnum.PENDING
        ),
    )
    db.add(audio_record)
    db.commit()
    db.refresh(audio_record)

    chat_response = None
    if transcript and transcript.strip():
        chat_response = process_user_message(
            db,
            current_user,
            session.id,
            transcript.strip(),
            message_type=MessageTypeEnum.VOICE_TRANSCRIPT,
        )

    return AudioUploadResponse(
        audio_record=audio_record,
        chat_response=chat_response,
        stt_status=(
            "transcript_processed"
            if chat_response
            else "stt_not_configured_audio_saved_only"
        ),
    )
