import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import MessageTypeEnum, SenderTypeEnum


class StudioMessage(Base):
    __tablename__ = "studio_messages"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "sequence_number", name="uq_session_sequence_number"
        ),
    )

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
    sender_type: Mapped[SenderTypeEnum] = mapped_column(
        Enum(
            SenderTypeEnum,
            name="sender_type_enum",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
    )
    message_type: Mapped[MessageTypeEnum] = mapped_column(
        Enum(
            MessageTypeEnum,
            name="message_type_enum",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=MessageTypeEnum.TEXT,
        server_default=MessageTypeEnum.TEXT.value,
    )
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    session: Mapped["StudioSession"] = relationship(
        "StudioSession", back_populates="messages"
    )

    audio_record: Mapped["AudioRecord | None"] = relationship(
        "AudioRecord",
        back_populates="message",
        uselist=False,
    )

    ai_logs: Mapped[list["AILog"]] = relationship(
        "AILog",
        back_populates="message",
        cascade="all, delete-orphan",
    )
