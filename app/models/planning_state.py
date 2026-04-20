"""Planning state model driven by workflow contracts."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, JSON, String, Uuid, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import WorkflowTypeEnum


class PlanningState(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "planning_states"

    session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("studio_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
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
    collected_fields: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    missing_fields: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    completion_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    is_ready_for_summary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    is_ready_for_generation: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    session: Mapped["StudioSession"] = relationship(
        "StudioSession",
        back_populates="planning_state",
    )
