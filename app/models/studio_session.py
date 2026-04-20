"""Studio session model."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import SessionStatusEnum, WorkflowTypeEnum


class StudioSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "studio_sessions"

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    workflow_type: Mapped[WorkflowTypeEnum] = mapped_column(
        Enum(
            WorkflowTypeEnum,
            name="workflow_type_enum",
            native_enum=False,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
    )
    current_stage: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[SessionStatusEnum] = mapped_column(
        Enum(
            SessionStatusEnum,
            name="session_status_enum",
            native_enum=False,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=SessionStatusEnum.ACTIVE,
        server_default=SessionStatusEnum.ACTIVE.value,
    )
    completion_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped["User"] = relationship("User", back_populates="studio_sessions")
    planning_state: Mapped["PlanningState | None"] = relationship(
        "PlanningState",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
    )
    messages: Mapped[list["StudioMessage"]] = relationship(
        "StudioMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="StudioMessage.sequence_number",
    )
    generated_documents: Mapped[list["GeneratedDocument"]] = relationship(
        "GeneratedDocument",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    audio_records: Mapped[list["AudioRecord"]] = relationship(
        "AudioRecord",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    ai_logs: Mapped[list["AILog"]] = relationship(
        "AILog",
        back_populates="session",
        cascade="all, delete-orphan",
    )
