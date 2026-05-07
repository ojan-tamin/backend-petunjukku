from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.studio_message import (
    ChatResponse,
    StudioMessageCreate,
    StudioMessageResponse,
)
from app.services.message_service import get_messages_by_session, process_user_message
from app.services.session_service import require_session

router = APIRouter(tags=["Studio Messages"])


@router.post("", response_model=ChatResponse, status_code=201)
def create_session_message(
    session_id: UUID,
    message_in: StudioMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return process_user_message(
        db,
        current_user,
        session_id,
        message_in.text,
        message_type=message_in.message_type,
    )


@router.get("", response_model=list[StudioMessageResponse])
def list_session_messages(
    session_id: UUID,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = require_session(db, current_user, session_id)
    return get_messages_by_session(db, session, limit=limit, offset=offset)
