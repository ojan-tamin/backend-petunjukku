"""Domain enums for the backend foundation."""

from __future__ import annotations

from enum import Enum


class WorkflowTypeEnum(str, Enum):
    INTRAKURIKULER = "intrakurikuler"
    PJBL = "pjbl"


class SessionStatusEnum(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class MessageSenderEnum(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageTypeEnum(str, Enum):
    TEXT = "text"
    SUMMARY = "summary"
    TOOL_RESULT = "tool_result"
    NOTE = "note"


class GeneratedDocumentKindEnum(str, Enum):
    LESSON_PLAN = "lesson_plan"
    PROJECT_PLAN = "project_plan"
    SUMMARY = "summary"


class GeneratedDocumentStatusEnum(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    FINAL = "final"
    FAILED = "failed"


class AudioTranscriptionStatusEnum(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class AIInteractionStatusEnum(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
