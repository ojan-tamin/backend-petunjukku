from sqlalchemy.orm import Session

from app.models.enums import DocumentTypeEnum, SessionStatusEnum
from app.models.planning_state import PlanningState
from app.models.studio_session import StudioSession
from app.models.user import User
from app.schemas.studio_session import StudioSessionCreate


def get_initial_stage(document_type: DocumentTypeEnum) -> str:
    if document_type == DocumentTypeEnum.INTRAKURIKULER:
        return "intra_stage_1_learning_brief"
    elif document_type == DocumentTypeEnum.PJBL:
        return "pjbl_stage_1_identity_context"
    return "unknown_stage"


def get_initial_state_data(document_type: DocumentTypeEnum) -> dict:
    if document_type == DocumentTypeEnum.INTRAKURIKULER:
        return {
            "meta": {
                "document_type": "intrakurikuler",
                "current_stage": "intra_stage_1_learning_brief",
                "completion_score": 0,
                "is_ready_for_summary": False,
                "is_ready_for_generation": False,
            },
            "learning_brief": {},
            "curriculum": {},
            "classroom_context": {},
            "problem_definition": {},
            "strategy": {},
        }

    if document_type == DocumentTypeEnum.PJBL:
        return {
            "meta": {
                "document_type": "pjbl",
                "current_stage": "pjbl_stage_1_identity_context",
                "completion_score": 0,
                "is_ready_for_summary": False,
                "is_ready_for_generation": False,
            },
            "identity_context": {},
            "goals_driving_question": {},
            "project_execution": {},
            "assessment_guardrails": {},
            "resources_finalize": {},
        }

    return {}


def create_studio_session(
    db: Session,
    user: User,
    session_in: StudioSessionCreate,
) -> StudioSession:
    initial_stage = get_initial_stage(session_in.document_type)

    session = StudioSession(
        user_id=user.id,
        title=session_in.title,
        document_type=session_in.document_type,
        current_stage=initial_stage,
        status=SessionStatusEnum.ACTIVE,
        completion_score=0,
    )

    db.add(session)
    db.flush()  # supaya session.id sudah ada sebelum buat planning_state

    planning_state = PlanningState(
        session_id=session.id,
        document_type=session_in.document_type,
        state_data=get_initial_state_data(session_in.document_type),
        completion_score=0,
        is_ready_for_summary=False,
        is_ready_for_generation=False,
        version=1,
    )

    db.add(planning_state)
    db.commit()
    db.refresh(session)

    return session


def get_user_sessions(db: Session, user: User) -> list[StudioSession]:
    return (
        db.query(StudioSession)
        .filter(StudioSession.user_id == user.id)
        .order_by(StudioSession.updated_at.desc())
        .all()
    )


def get_session_by_id(db: Session, user: User, session_id) -> StudioSession | None:
    return (
        db.query(StudioSession)
        .filter(
            StudioSession.id == session_id,
            StudioSession.user_id == user.id,
        )
        .first()
    )
