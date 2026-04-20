"""create initial foundation tables

Revision ID: 28d77849332c
Revises:
Create Date: 2026-04-17 18:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "28d77849332c"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


workflow_type_enum = sa.Enum(
    "intrakurikuler",
    "pjbl",
    name="workflow_type_enum",
    native_enum=False,
)
session_status_enum = sa.Enum(
    "active",
    "paused",
    "completed",
    "archived",
    name="session_status_enum",
    native_enum=False,
)
message_sender_enum = sa.Enum(
    "user",
    "assistant",
    "system",
    name="message_sender_enum",
    native_enum=False,
)
message_type_enum = sa.Enum(
    "text",
    "summary",
    "tool_result",
    "note",
    name="message_type_enum",
    native_enum=False,
)
generated_document_kind_enum = sa.Enum(
    "lesson_plan",
    "project_plan",
    "summary",
    name="generated_document_kind_enum",
    native_enum=False,
)
generated_document_status_enum = sa.Enum(
    "draft",
    "ready",
    "final",
    "failed",
    name="generated_document_status_enum",
    native_enum=False,
)
audio_transcription_status_enum = sa.Enum(
    "pending",
    "completed",
    "failed",
    name="audio_transcription_status_enum",
    native_enum=False,
)
ai_interaction_status_enum = sa.Enum(
    "pending",
    "succeeded",
    "failed",
    name="ai_interaction_status_enum",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=150), nullable=False),
        sa.Column("auth_provider", sa.String(length=64), nullable=False, server_default="deferred"),
        sa.Column("external_subject", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="teacher"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_subject"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "studio_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("workflow_type", workflow_type_enum, nullable=False),
        sa.Column("current_stage", sa.String(length=120), nullable=False),
        sa.Column("status", session_status_enum, nullable=False, server_default="active"),
        sa.Column("completion_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_studio_sessions_user_id"), "studio_sessions", ["user_id"], unique=False)

    op.create_table(
        "planning_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_type", workflow_type_enum, nullable=False),
        sa.Column("current_stage", sa.String(length=120), nullable=False),
        sa.Column("collected_fields", sa.JSON(), nullable=False),
        sa.Column("missing_fields", sa.JSON(), nullable=False),
        sa.Column("completion_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_ready_for_summary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["session_id"], ["studio_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index(op.f("ix_planning_states_session_id"), "planning_states", ["session_id"], unique=True)

    op.create_table(
        "studio_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("sender_type", message_sender_enum, nullable=False),
        sa.Column("message_type", message_type_enum, nullable=False, server_default="text"),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["session_id"], ["studio_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "sequence_number", name="uq_studio_messages_session_sequence"),
    )
    op.create_index(op.f("ix_studio_messages_session_id"), "studio_messages", ["session_id"], unique=False)

    op.create_table(
        "generated_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", generated_document_kind_enum, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("status", generated_document_status_enum, nullable=False, server_default="draft"),
        sa.Column("content_json", sa.JSON(), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=True),
        sa.Column("storage_uri", sa.String(length=500), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("generated_from_state_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["session_id"], ["studio_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_generated_documents_session_id"), "generated_documents", ["session_id"], unique=False)
    op.create_index(op.f("ix_generated_documents_user_id"), "generated_documents", ["user_id"], unique=False)

    op.create_table(
        "audio_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("storage_uri", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("transcription_status", audio_transcription_status_enum, nullable=False, server_default="pending"),
        sa.Column("transcript_text", sa.Text(), nullable=True),
        sa.Column("transcript_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["session_id"], ["studio_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audio_records_session_id"), "audio_records", ["session_id"], unique=False)

    op.create_table(
        "ai_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=True),
        sa.Column("stage_id", sa.String(length=120), nullable=True),
        sa.Column("operation", sa.String(length=120), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=True),
        sa.Column("model_name", sa.String(length=120), nullable=True),
        sa.Column("status", ai_interaction_status_enum, nullable=False, server_default="pending"),
        sa.Column("request_payload", sa.JSON(), nullable=False),
        sa.Column("response_payload", sa.JSON(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["message_id"], ["studio_messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["studio_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_logs_message_id"), "ai_logs", ["message_id"], unique=False)
    op.create_index(op.f("ix_ai_logs_session_id"), "ai_logs", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_logs_session_id"), table_name="ai_logs")
    op.drop_index(op.f("ix_ai_logs_message_id"), table_name="ai_logs")
    op.drop_table("ai_logs")
    op.drop_index(op.f("ix_audio_records_session_id"), table_name="audio_records")
    op.drop_table("audio_records")
    op.drop_index(op.f("ix_generated_documents_user_id"), table_name="generated_documents")
    op.drop_index(op.f("ix_generated_documents_session_id"), table_name="generated_documents")
    op.drop_table("generated_documents")
    op.drop_index(op.f("ix_studio_messages_session_id"), table_name="studio_messages")
    op.drop_table("studio_messages")
    op.drop_index(op.f("ix_planning_states_session_id"), table_name="planning_states")
    op.drop_table("planning_states")
    op.drop_index(op.f("ix_studio_sessions_user_id"), table_name="studio_sessions")
    op.drop_table("studio_sessions")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
