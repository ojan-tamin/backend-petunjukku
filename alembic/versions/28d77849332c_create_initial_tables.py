"""create initial studio guru tables

Revision ID: 28d77849332c
Revises:
Create Date: 2026-04-16 15:15:29.113553
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "28d77849332c"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=True),
        sa.Column("email", sa.String(length=150), nullable=False),
        sa.Column("hashed_password", sa.Text(), nullable=False),
        sa.Column("school_name", sa.String(length=200), nullable=True),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "studio_sessions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("document_type", sa.Enum("intrakurikuler", "pjbl", name="document_type_enum"), nullable=False),
        sa.Column("current_stage", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "review", "completed", "archived", name="session_status_enum"),
            server_default="active",
            nullable=False,
        ),
        sa.Column("completion_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_studio_sessions_user_id"), "studio_sessions", ["user_id"])

    op.create_table(
        "generated_documents",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("session_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("document_type", sa.Enum("intrakurikuler", "pjbl", name="document_type_enum"), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("document_output", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["studio_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_generated_documents_session_id"), "generated_documents", ["session_id"])
    op.create_index(op.f("ix_generated_documents_user_id"), "generated_documents", ["user_id"])

    op.create_table(
        "planning_states",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("session_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("workflow_type", sa.String(length=50), nullable=False),
        sa.Column("current_stage", sa.String(length=50), nullable=False),
        sa.Column("collected_fields", sa.JSON(), nullable=False),
        sa.Column("missing_fields", sa.JSON(), nullable=False),
        sa.Column("completion_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_ready_for_summary", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_ready_for_generation", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["studio_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_planning_states_session_id"), "planning_states", ["session_id"], unique=True)

    op.create_table(
        "studio_messages",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("session_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("role", sa.Enum("user", "assistant", "system", name="message_role_enum"), nullable=False),
        sa.Column(
            "message_type",
            sa.Enum("text", "voice_transcript", "summary", "revision_note", name="message_type_enum"),
            server_default="text",
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["studio_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "sequence_number", name="uq_session_sequence_number"),
    )
    op.create_index(op.f("ix_studio_messages_session_id"), "studio_messages", ["session_id"])

    op.create_table(
        "ai_logs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("session_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("message_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("step_name", sa.String(length=100), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("prompt_text", sa.Text(), nullable=True),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("input_payload", sa.JSON(), nullable=True),
        sa.Column("output_payload", sa.JSON(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["studio_messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["studio_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_logs_message_id"), "ai_logs", ["message_id"])
    op.create_index(op.f("ix_ai_logs_session_id"), "ai_logs", ["session_id"])

    op.create_table(
        "audio_records",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("session_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("message_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column(
            "transcription_status",
            sa.Enum("pending", "success", "failed", name="transcription_status_enum"),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["studio_messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["studio_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id"),
    )
    op.create_index(op.f("ix_audio_records_session_id"), "audio_records", ["session_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_audio_records_session_id"), table_name="audio_records")
    op.drop_table("audio_records")
    op.drop_index(op.f("ix_ai_logs_session_id"), table_name="ai_logs")
    op.drop_index(op.f("ix_ai_logs_message_id"), table_name="ai_logs")
    op.drop_table("ai_logs")
    op.drop_index(op.f("ix_studio_messages_session_id"), table_name="studio_messages")
    op.drop_table("studio_messages")
    op.drop_index(op.f("ix_planning_states_session_id"), table_name="planning_states")
    op.drop_table("planning_states")
    op.drop_index(op.f("ix_generated_documents_user_id"), table_name="generated_documents")
    op.drop_index(op.f("ix_generated_documents_session_id"), table_name="generated_documents")
    op.drop_table("generated_documents")
    op.drop_index(op.f("ix_studio_sessions_user_id"), table_name="studio_sessions")
    op.drop_table("studio_sessions")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
