from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.studio_message import PlanningStateResponse, StudioMessageResponse
from app.schemas.studio_session import (
    StudioSessionCreate,
    StudioSessionDetailResponse,
    StudioSessionResponse,
)
from app.services.message_service import get_messages_by_session
from app.services.session_service import (
    create_studio_session,
    get_session_by_id,
    get_user_sessions,
)

router = APIRouter(tags=["Studio Sessions"])


@router.post("", response_model=StudioSessionResponse, status_code=201)
def create_session(
    session_in: StudioSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_studio_session(db, current_user, session_in)


@router.get("", response_model=list[StudioSessionResponse])
def list_sessions(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_user_sessions(db, current_user, limit=limit, offset=offset)


@router.get("/{session_id}", response_model=StudioSessionDetailResponse)
def get_session_detail(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = get_session_by_id(db, current_user, session_id)
    if not session:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Session not found")

    planning_state = None
    if session.planning_state:
        planning_state = PlanningStateResponse(
            current_stage=session.planning_state.current_stage,
            collected_fields=session.planning_state.collected_fields or {},
            missing_fields=list(session.planning_state.missing_fields or []),
            completion_score=session.planning_state.completion_score,
            is_ready_for_summary=session.planning_state.is_ready_for_summary,
            is_ready_for_generation=session.planning_state.is_ready_for_generation,
            version=session.planning_state.version,
        )
    messages = [
        StudioMessageResponse.model_validate(message)
        for message in get_messages_by_session(db, session)
    ]
    return StudioSessionDetailResponse(
        id=session.id,
        user_id=session.user_id,
        title=session.title,
        document_type=session.document_type,
        current_stage=session.current_stage,
        status=session.status,
        completion_score=session.completion_score,
        last_message_at=session.last_message_at,
        created_at=session.created_at,
        updated_at=session.updated_at,
        planning_state=planning_state,
        messages=messages,
    )
