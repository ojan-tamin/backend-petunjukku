import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import DocumentStatusEnum, DocumentTypeEnum


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"

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
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_type: Mapped[DocumentTypeEnum] = mapped_column(
        Enum(
            DocumentTypeEnum,
            name="document_type_enum",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    content_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[DocumentStatusEnum] = mapped_column(
        Enum(
            DocumentStatusEnum,
            name="document_status_enum",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=DocumentStatusEnum.DRAFT,
        server_default=DocumentStatusEnum.DRAFT.value,
    )
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

    session: Mapped["StudioSession"] = relationship(
        "StudioSession", back_populates="generated_documents"
    )
    user: Mapped["User"] = relationship("User", back_populates="generated_documents")
