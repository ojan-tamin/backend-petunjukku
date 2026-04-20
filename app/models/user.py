"""User model reserved for future auth ownership and session scoping."""

from __future__ import annotations

from sqlalchemy import Boolean, String, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(150), nullable=False)
    auth_provider: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="deferred",
        server_default="deferred",
    )
    external_subject: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
    )
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="teacher",
        server_default="teacher",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
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
    audio_records: Mapped[list["AudioRecord"]] = relationship(
        "AudioRecord",
        back_populates="uploaded_by_user",
    )
