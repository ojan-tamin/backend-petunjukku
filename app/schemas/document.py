from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import DocumentTypeEnum


class GeneratedDocumentResponse(BaseModel):
    id: UUID
    session_id: UUID
    document_type: DocumentTypeEnum
    title: str
    content: str
    document_output: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GenerateDocumentResponse(BaseModel):
    document_id: UUID
    title: str
    document_type: DocumentTypeEnum
    content: str
