from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.schemas.studio_message import StudioMessageCreate, StudioMessageResponse
from app.services.message_service import (
    create_message,
    get_messages_by_session,
    get_session_for_user,
)

router = APIRouter(
    prefix="/studio/sessions/{session_id}/messages",
    tags=["Studio Messages"],
)


@router.post(
    "", response_model=StudioMessageResponse, status_code=status.HTTP_201_CREATED
)
def create_session_message(
    session_id: UUID,
    message_in: StudioMessageCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    current_user_id = (
        current_user["id"] if isinstance(current_user, dict) else current_user.id
    )

    session = get_session_for_user(db, current_user_id, session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    message = create_message(db, session, message_in)
    return message


@router.get("", response_model=list[StudioMessageResponse])
def list_session_messages(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    current_user_id = (
        current_user["id"] if isinstance(current_user, dict) else current_user.id
    )

    session = get_session_for_user(db, current_user_id, session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    return get_messages_by_session(db, session)
