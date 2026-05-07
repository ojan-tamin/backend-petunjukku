from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ai.dialogue_manager import build_assistant_message
from app.ai.interpreter import interpret_user_message
from app.ai.stage_manager import evaluate_state, missing_fields
from app.ai.workflow import initial_stage
from app.models.enums import MessageTypeEnum, SenderTypeEnum
from app.models.planning_state import PlanningState
from app.models.studio_message import StudioMessage
from app.models.studio_session import StudioSession
from app.models.user import User
from app.schemas.studio_message import ChatResponse, PlanningStateResponse
from app.services.flow_intra_ai_service import FlowIntraAIError, get_flow_intra_ai_service
from app.services.session_service import require_session


def get_next_sequence_number(db: Session, session_id: UUID) -> int:
    max_sequence = (
        db.query(func.max(StudioMessage.sequence_number))
        .filter(StudioMessage.session_id == session_id)
        .scalar()
    )
    return 1 if max_sequence is None else int(max_sequence) + 1


def create_message(
    db: Session,
    session: StudioSession,
    *,
    role: SenderTypeEnum,
    content: str,
    message_type: MessageTypeEnum = MessageTypeEnum.TEXT,
) -> StudioMessage:
    message = StudioMessage(
        session_id=session.id,
        role=role,
        message_type=message_type,
        content=content,
        sequence_number=get_next_sequence_number(db, session.id),
    )
    db.add(message)
    session.last_message_at = datetime.now(timezone.utc)
    db.add(session)
    db.flush()
    return message


def get_messages_by_session(
    db: Session,
    session: StudioSession,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[StudioMessage]:
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    return (
        db.query(StudioMessage)
        .filter(StudioMessage.session_id == session.id)
        .order_by(StudioMessage.sequence_number.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_or_create_planning_state(db: Session, session: StudioSession) -> PlanningState:
    if session.planning_state:
        return session.planning_state

    workflow_type = session.document_type.value
    stage = initial_stage(workflow_type)
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
    db.flush()
    return planning_state


def process_user_message(
    db: Session,
    user: User,
    session_id: UUID,
    content: str,
    *,
    message_type: MessageTypeEnum = MessageTypeEnum.TEXT,
) -> ChatResponse:
    session = require_session(db, user, session_id)
    planning_state = get_or_create_planning_state(db, session)

    user_message = create_message(
        db,
        session,
        role=SenderTypeEnum.USER,
        content=content,
        message_type=message_type,
    )

    if planning_state.workflow_type == "intrakurikuler":
        chat_history = [
            {"role": message.role.value, "content": message.content}
            for message in get_messages_by_session(db, session, limit=20)
        ]
        try:
            ai_result = get_flow_intra_ai_service().process_turn(
                user_message=content,
                current_stage=planning_state.current_stage,
                collected_fields=planning_state.collected_fields or {},
                missing_fields=list(planning_state.missing_fields or []),
                chat_history=chat_history,
            )
        except FlowIntraAIError as exc:
            raise HTTPException(
                status_code=getattr(exc, "status_code", 503),
                detail=getattr(exc, "public_detail", "AI Flow Intra service is unavailable"),
            ) from exc

        assistant_message = ai_result.assistant_message
        planning_state.collected_fields = ai_result.collected_fields
        planning_state.current_stage = ai_result.next_stage
        planning_state.missing_fields = ai_result.missing_fields
        planning_state.completion_score = ai_result.completion_score
        planning_state.is_ready_for_summary = ai_result.is_ready_for_summary
        planning_state.is_ready_for_generation = ai_result.is_ready_for_generation
    else:
        interpretation = interpret_user_message(
            workflow_type=planning_state.workflow_type,
            current_stage=planning_state.current_stage,
            current_fields=planning_state.collected_fields or {},
            user_message=content,
        )
        evaluation = evaluate_state(
            workflow_type=planning_state.workflow_type,
            current_stage=planning_state.current_stage,
            fields=interpretation["collected_fields"],
            approved_summary=interpretation["approved_summary"],
            revision_requested=interpretation["revision_requested"],
        )

        assistant_message = build_assistant_message(
            workflow_type=planning_state.workflow_type,
            current_stage=evaluation["next_stage"],
            updated_fields=interpretation["updated_fields"],
            collected_fields=interpretation["collected_fields"],
            missing_fields=evaluation["missing_fields"],
            completion_score=evaluation["completion_score"],
            is_ready_for_summary=evaluation["is_ready_for_summary"],
            is_ready_for_generation=evaluation["is_ready_for_generation"],
            approved_summary=interpretation["approved_summary"],
        )

        planning_state.collected_fields = interpretation["collected_fields"]
        planning_state.current_stage = evaluation["next_stage"]
        planning_state.missing_fields = evaluation["missing_fields"]
        planning_state.completion_score = evaluation["completion_score"]
        planning_state.is_ready_for_summary = evaluation["is_ready_for_summary"]
        planning_state.is_ready_for_generation = evaluation["is_ready_for_generation"]

    planning_state.version += 1

    session.current_stage = planning_state.current_stage
    session.completion_score = planning_state.completion_score

    db.add(planning_state)
    db.add(session)

    create_message(
        db,
        session,
        role=SenderTypeEnum.ASSISTANT,
        content=assistant_message,
        message_type=MessageTypeEnum.TEXT,
    )
    db.commit()
    db.refresh(planning_state)
    db.refresh(user_message)

    planning_response = PlanningStateResponse(
        current_stage=planning_state.current_stage,
        collected_fields=planning_state.collected_fields or {},
        missing_fields=list(planning_state.missing_fields or []),
        completion_score=planning_state.completion_score,
        is_ready_for_summary=planning_state.is_ready_for_summary,
        is_ready_for_generation=planning_state.is_ready_for_generation,
        version=planning_state.version,
    )
    return ChatResponse(
        session_id=session.id,
        assistant_message=assistant_message,
        planning_state=planning_response,
        current_stage=planning_state.current_stage,
        completion_score=planning_state.completion_score,
        is_ready_for_summary=planning_state.is_ready_for_summary,
        is_ready_for_generation=planning_state.is_ready_for_generation,
    )
