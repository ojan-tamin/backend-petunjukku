"""Audio record model for future voice workflows."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AudioTranscriptionStatusEnum


class AudioRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "audio_records"

    session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("studio_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    storage_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    transcription_status: Mapped[AudioTranscriptionStatusEnum] = mapped_column(
        Enum(
            AudioTranscriptionStatusEnum,
            name="audio_transcription_status_enum",
            native_enum=False,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=AudioTranscriptionStatusEnum.PENDING,
        server_default=AudioTranscriptionStatusEnum.PENDING.value,
    )
    transcript_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    session: Mapped["StudioSession"] = relationship(
        "StudioSession",
        back_populates="audio_records",
    )
    uploaded_by_user: Mapped["User | None"] = relationship(
        "User",
        back_populates="audio_records",
    )
