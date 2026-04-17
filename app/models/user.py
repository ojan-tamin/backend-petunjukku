import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(
        String(150), nullable=False, unique=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    school_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="teacher")

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

    studio_sessions: Mapped[list["StudioSession"]] = relationship(
        "StudioSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    generated_documents: Mapped[list["GeneratedDocument"]] = relationship(
        "GeneratedDocument",
        back_populates="user",
        cascade="all, delete-orphan",
    )
