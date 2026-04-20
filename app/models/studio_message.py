"""Studio message model."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Integer, JSON, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import MessageSenderEnum, MessageTypeEnum


class StudioMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "studio_messages"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "sequence_number",
            name="uq_studio_messages_session_sequence",
        ),
    )

    session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("studio_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_type: Mapped[MessageSenderEnum] = mapped_column(
        Enum(
            MessageSenderEnum,
            name="message_sender_enum",
            native_enum=False,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
    )
    message_type: Mapped[MessageTypeEnum] = mapped_column(
        Enum(
            MessageTypeEnum,
            name="message_type_enum",
            native_enum=False,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=MessageTypeEnum.TEXT,
        server_default=MessageTypeEnum.TEXT.value,
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    session: Mapped["StudioSession"] = relationship(
        "StudioSession",
        back_populates="messages",
    )
    ai_logs: Mapped[list["AILog"]] = relationship(
        "AILog",
        back_populates="message",
    )
