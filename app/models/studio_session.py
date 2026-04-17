import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import DocumentTypeEnum, SessionStatusEnum


class StudioSession(Base):
    __tablename__ = "studio_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)

    document_type: Mapped[DocumentTypeEnum] = mapped_column(
        Enum(
            DocumentTypeEnum,
            name="document_type_enum",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
    )
    current_stage: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[SessionStatusEnum] = mapped_column(
        Enum(
            SessionStatusEnum,
            name="session_status_enum",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=SessionStatusEnum.ACTIVE,
        server_default=SessionStatusEnum.ACTIVE.value,
    )
    completion_score: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship("User", back_populates="studio_sessions")

    messages: Mapped[list["StudioMessage"]] = relationship(
        "StudioMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="StudioMessage.sequence_number",
    )

    planning_state: Mapped["PlanningState | None"] = relationship(
        "PlanningState",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
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
