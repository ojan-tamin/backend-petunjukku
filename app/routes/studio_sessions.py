"""Studio session routes for workflow inspection, planning updates, and finalization."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.enums import WorkflowTypeEnum
from app.core.dependencies import get_db
from app.schemas.studio_session import (
    PlanningStateUpdateRequest,
    SessionServiceHealthResponse,
    StudioSessionCreateRequest,
    StudioSessionDetailResponse,
    StudioSessionFinalizationResponse,
    StudioSessionSeedPreview,
    StudioSessionSeedRequest,
    WorkflowDefinitionResponse,
    WorkflowSummary,
)
from app.services.session_service import (
    build_session_preview,
    create_studio_session,
    finalize_studio_session,
    get_studio_session_detail,
    get_service_health,
    get_workflow_definition,
    list_workflow_summaries,
    SessionNotFoundError,
    SessionServiceError,
    SessionValidationError,
    update_studio_session_planning_state,
)

router = APIRouter(prefix="/studio-sessions", tags=["studio-sessions"])


@router.get("/health", response_model=SessionServiceHealthResponse)
def studio_session_health() -> SessionServiceHealthResponse:
    return SessionServiceHealthResponse.model_validate(get_service_health())


@router.get("/workflows", response_model=list[WorkflowSummary])
def read_workflow_summaries() -> list[WorkflowSummary]:
    return [
        WorkflowSummary.model_validate(workflow_summary)
        for workflow_summary in list_workflow_summaries()
    ]


@router.get("/workflows/{workflow_type}", response_model=WorkflowDefinitionResponse)
def read_workflow_definition(
    workflow_type: WorkflowTypeEnum,
) -> WorkflowDefinitionResponse:
    return WorkflowDefinitionResponse.model_validate(
        get_workflow_definition(workflow_type)
    )


@router.post("/preview", response_model=StudioSessionSeedPreview)
def preview_studio_session(
    payload: StudioSessionSeedRequest,
) -> StudioSessionSeedPreview:
    return StudioSessionSeedPreview.model_validate(
        build_session_preview(
            title=payload.title,
            workflow_type=payload.workflow_type,
        )
    )


@router.post("", response_model=StudioSessionDetailResponse)
def create_studio_session_route(
    payload: StudioSessionCreateRequest,
    db: Session = Depends(get_db),
) -> StudioSessionDetailResponse:
    try:
        return StudioSessionDetailResponse.model_validate(
            create_studio_session(
                db,
                workflow_type=payload.workflow_type,
                title=payload.title,
                user_email=payload.user_email,
                user_display_name=payload.user_display_name,
            )
        )
    except SessionServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{session_id}", response_model=StudioSessionDetailResponse)
def read_studio_session(
    session_id: UUID,
    db: Session = Depends(get_db),
) -> StudioSessionDetailResponse:
    try:
        return StudioSessionDetailResponse.model_validate(
            get_studio_session_detail(db, session_id)
        )
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{session_id}/planning-state", response_model=StudioSessionDetailResponse)
def update_planning_state(
    session_id: UUID,
    payload: PlanningStateUpdateRequest,
    db: Session = Depends(get_db),
) -> StudioSessionDetailResponse:
    try:
        return StudioSessionDetailResponse.model_validate(
            update_studio_session_planning_state(
                db,
                session_id=session_id,
                collected_fields=payload.collected_fields,
                advance_stage=payload.advance_stage,
            )
        )
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SessionValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{session_id}/finalize", response_model=StudioSessionFinalizationResponse)
def finalize_studio_session_route(
    session_id: UUID,
    db: Session = Depends(get_db),
) -> StudioSessionFinalizationResponse:
    try:
        return StudioSessionFinalizationResponse.model_validate(
            finalize_studio_session(
                db,
                session_id=session_id,
            )
        )
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SessionValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
