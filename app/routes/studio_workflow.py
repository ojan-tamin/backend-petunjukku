from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.document import GenerateDocumentResponse
from app.schemas.summary import SummaryResponse
from app.services.document_service import build_session_summary, generate_document

router = APIRouter(tags=["Studio Workflow"])


@router.get("/{session_id}/summary", response_model=SummaryResponse)
def get_summary(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return build_session_summary(db, current_user, session_id)


@router.post("/{session_id}/summary", response_model=SummaryResponse)
def create_summary(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return build_session_summary(db, current_user, session_id)


@router.post("/{session_id}/generate", response_model=GenerateDocumentResponse)
def generate_session_document(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = generate_document(db, current_user, session_id)
    return GenerateDocumentResponse(
        document_id=document.id,
        title=document.title,
        document_type=document.document_type,
        content=document.content,
    )
