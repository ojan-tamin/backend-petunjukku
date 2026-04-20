"""AI interaction log model for observability."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AIInteractionStatusEnum


class AILog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_logs"

    session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("studio_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("studio_messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    stage_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    operation: Mapped[str] = mapped_column(String(120), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[AIInteractionStatusEnum] = mapped_column(
        Enum(
            AIInteractionStatusEnum,
            name="ai_interaction_status_enum",
            native_enum=False,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=AIInteractionStatusEnum.PENDING,
        server_default=AIInteractionStatusEnum.PENDING.value,
    )
    request_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    response_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped["StudioSession"] = relationship(
        "StudioSession",
        back_populates="ai_logs",
    )
    message: Mapped["StudioMessage | None"] = relationship(
        "StudioMessage",
        back_populates="ai_logs",
    )
