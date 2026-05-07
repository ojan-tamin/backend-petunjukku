from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.document import GeneratedDocumentResponse
from app.services.document_service import (
    get_document,
    list_documents,
    list_session_documents,
)

router = APIRouter(tags=["Documents"])
session_router = APIRouter(tags=["Documents"])


@router.get("", response_model=list[GeneratedDocumentResponse])
def get_documents(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_documents(db, current_user, limit=limit, offset=offset)


@router.get("/{document_id}", response_model=GeneratedDocumentResponse)
def get_document_detail(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_document(db, current_user, document_id)


@session_router.get("/{session_id}/documents", response_model=list[GeneratedDocumentResponse])
def get_documents_for_session(
    session_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_session_documents(db, current_user, session_id, limit=limit, offset=offset)
