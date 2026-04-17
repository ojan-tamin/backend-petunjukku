import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import TranscriptionStatusEnum


class AudioRecord(Base):
    __tablename__ = "audio_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("studio_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("studio_messages.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    transcript_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcription_status: Mapped[TranscriptionStatusEnum] = mapped_column(
        Enum(
            TranscriptionStatusEnum,
            name="transcription_status_enum",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=TranscriptionStatusEnum.PENDING,
        server_default=TranscriptionStatusEnum.PENDING.value,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    session: Mapped["StudioSession"] = relationship(
        "StudioSession", back_populates="audio_records"
    )
    message: Mapped["StudioMessage | None"] = relationship(
        "StudioMessage", back_populates="audio_record"
    )
