"""Session schemas for workflow and planning-state boundaries."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import (
    GeneratedDocumentKindEnum,
    GeneratedDocumentStatusEnum,
    SessionStatusEnum,
    WorkflowTypeEnum,
)


class PlanningStateSnapshot(BaseModel):
    workflow_type: WorkflowTypeEnum
    current_stage: str
    collected_fields: dict[str, Any] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    completion_score: int
    is_ready_for_summary: bool
    is_ready_for_generation: bool
    version: int


class WorkflowStageSummary(BaseModel):
    id: str
    label: str
    description: str
    required_fields: list[str]
    next_stage: str | None


class WorkflowSummary(BaseModel):
    workflow_type: WorkflowTypeEnum
    label: str
    description: str
    first_stage: str
    stage_count: int


class WorkflowDefinitionResponse(BaseModel):
    workflow_type: WorkflowTypeEnum
    label: str
    description: str
    stages: list[WorkflowStageSummary]
    supported_fields: list[str] = Field(default_factory=list)
    summary_required_fields: list[str] = Field(default_factory=list)
    generation_required_fields: list[str] = Field(default_factory=list)
    initial_state: PlanningStateSnapshot


class StudioSessionSeedRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    workflow_type: WorkflowTypeEnum


class StudioSessionCreateRequest(StudioSessionSeedRequest):
    user_email: str = Field(default="demo.teacher@local")
    user_display_name: str = Field(default="Demo Teacher", max_length=150)


class PlanningStateUpdateRequest(BaseModel):
    collected_fields: dict[str, Any] = Field(default_factory=dict)
    advance_stage: bool = True


class GeneratedDocumentSnapshot(BaseModel):
    id: UUID
    session_id: UUID
    user_id: UUID
    kind: GeneratedDocumentKindEnum
    title: str
    status: GeneratedDocumentStatusEnum
    content_json: dict[str, Any] = Field(default_factory=dict)
    content_markdown: str | None = None
    storage_uri: str | None = None
    version: int
    generated_from_state_version: int
    created_at: datetime
    updated_at: datetime


class StudioSessionDetailResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    workflow_type: WorkflowTypeEnum
    current_stage: str
    status: SessionStatusEnum
    completion_score: int
    last_message_at: datetime | None = None
    planning_state: PlanningStateSnapshot
    generated_documents: list[GeneratedDocumentSnapshot] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class StudioSessionFinalizationResponse(BaseModel):
    session: StudioSessionDetailResponse
    generated_document: GeneratedDocumentSnapshot


class StudioSessionSeedPreview(BaseModel):
    title: str
    workflow_type: WorkflowTypeEnum
    initial_state: PlanningStateSnapshot


class SessionServiceHealthResponse(BaseModel):
    status: str
    database: str
    contract_version: str
    available_workflows: list[str]
