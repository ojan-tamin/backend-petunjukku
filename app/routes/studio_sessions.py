from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.studio_session import StudioSessionCreate, StudioSessionResponse
from app.services.session_service import (
    create_studio_session,
    get_session_by_id,
    get_user_sessions,
)

router = APIRouter(prefix="/studio/sessions", tags=["Studio Sessions"])


@router.post(
    "", response_model=StudioSessionResponse, status_code=status.HTTP_201_CREATED
)
def create_session(
    session_in: StudioSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = create_studio_session(db, current_user, session_in)
    return session


@router.get("", response_model=list[StudioSessionResponse])
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_user_sessions(db, current_user)


@router.get("/{session_id}", response_model=StudioSessionResponse)
def get_session_detail(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = get_session_by_id(db, current_user, session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    return session
