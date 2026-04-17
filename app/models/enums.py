import enum


class DocumentTypeEnum(str, enum.Enum):
    INTRAKURIKULER = "intrakurikuler"
    PJBL = "pjbl"


class SessionStatusEnum(str, enum.Enum):
    ACTIVE = "active"
    REVIEW = "review"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class SenderTypeEnum(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageTypeEnum(str, enum.Enum):
    TEXT = "text"
    VOICE_TRANSCRIPT = "voice_transcript"
    SUMMARY = "summary"
    REVISION_NOTE = "revision_note"


class DocumentStatusEnum(str, enum.Enum):
    DRAFT = "draft"
    FINAL = "final"
    REVISED = "revised"


class TranscriptionStatusEnum(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
