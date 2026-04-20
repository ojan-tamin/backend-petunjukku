"""Generated document model for future exports and summaries."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import GeneratedDocumentKindEnum, GeneratedDocumentStatusEnum


class GeneratedDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "generated_documents"

    session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("studio_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[GeneratedDocumentKindEnum] = mapped_column(
        Enum(
            GeneratedDocumentKindEnum,
            name="generated_document_kind_enum",
            native_enum=False,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[GeneratedDocumentStatusEnum] = mapped_column(
        Enum(
            GeneratedDocumentStatusEnum,
            name="generated_document_status_enum",
            native_enum=False,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=GeneratedDocumentStatusEnum.DRAFT,
        server_default=GeneratedDocumentStatusEnum.DRAFT.value,
    )
    content_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    content_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    generated_from_state_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    session: Mapped["StudioSession"] = relationship(
        "StudioSession",
        back_populates="generated_documents",
    )
    user: Mapped["User"] = relationship("User", back_populates="generated_documents")
