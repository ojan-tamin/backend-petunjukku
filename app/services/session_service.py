from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.ai.stage_manager import missing_fields
from app.ai.workflow import initial_stage
from app.models.enums import DocumentTypeEnum, SessionStatusEnum
from app.models.planning_state import PlanningState
from app.models.studio_session import StudioSession
from app.models.user import User
from app.schemas.studio_session import StudioSessionCreate


def create_studio_session(
    db: Session,
    user: User,
    session_in: StudioSessionCreate,
) -> StudioSession:
    workflow_type = session_in.document_type.value
    stage = initial_stage(workflow_type)

    session = StudioSession(
        user_id=user.id,
        title=session_in.title,
        document_type=session_in.document_type,
        current_stage=stage,
        status=SessionStatusEnum.ACTIVE,
        completion_score=0,
    )

    db.add(session)
    db.flush()

    planning_state = PlanningState(
        session_id=session.id,
        workflow_type=workflow_type,
        current_stage=stage,
        collected_fields={},
        missing_fields=missing_fields(workflow_type, stage, {}),
        completion_score=0,
        is_ready_for_summary=False,
        is_ready_for_generation=False,
        version=1,
    )

    db.add(planning_state)
    db.commit()
    db.refresh(session)

    return session


def get_user_sessions(
    db: Session,
    user: User,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[StudioSession]:
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    return (
        db.query(StudioSession)
        .filter(StudioSession.user_id == user.id)
        .order_by(StudioSession.updated_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_session_by_id(db: Session, user: User, session_id: UUID) -> StudioSession | None:
    return (
        db.query(StudioSession)
        .filter(
            StudioSession.id == session_id,
            StudioSession.user_id == user.id,
        )
        .first()
    )


def require_session(db: Session, user: User, session_id: UUID) -> StudioSession:
    session = get_session_by_id(db, user, session_id)
    if not session:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Session not found")
    return session


def document_type_from_session(session: StudioSession) -> DocumentTypeEnum:
    return session.document_type
