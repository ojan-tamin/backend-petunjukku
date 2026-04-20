"""Session service for workflow inspection, planning-state updates, and finalization."""

from __future__ import annotations

from functools import lru_cache
from typing import Any
from uuid import UUID

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.db.session import database_healthcheck
from app.models.enums import (
    GeneratedDocumentKindEnum,
    GeneratedDocumentStatusEnum,
    SessionStatusEnum,
    WorkflowTypeEnum,
)
from app.models.generated_document import GeneratedDocument
from app.models.planning_state import PlanningState
from app.models.studio_session import StudioSession
from app.models.user import User

EXPECTED_WORKFLOWS = {workflow_type.value for workflow_type in WorkflowTypeEnum}
CONTRACTS_PATH = settings.ai_contracts_dir / "stage_definitions.yaml"
DEFAULT_DEFERRED_USER_EMAIL = "demo.teacher@local"
DEFAULT_DEFERRED_USER_DISPLAY_NAME = "Demo Teacher"
LEGACY_FIELD_ALIASES: dict[WorkflowTypeEnum, dict[str, str]] = {
    WorkflowTypeEnum.PJBL: {
        "theme": "project_theme",
        "class_level": "grade_level",
        "subject_focus": "subject_or_theme",
        "local_context": "school_context",
        "learning_outcomes": "project_objectives",
        "final_artifact": "final_product",
        "milestones": "project_stages",
        "collaboration_model": "grouping_strategy",
        "assessment_plan": "assessment_focus",
        "resource_needs": "resources_needed",
    }
}


class SessionServiceError(Exception):
    """Base error for session planning and finalization operations."""


class SessionNotFoundError(SessionServiceError):
    """Raised when a studio session cannot be found."""


class SessionValidationError(SessionServiceError):
    """Raised when the requested update is invalid for the workflow contract."""


def _normalize_stage(stage: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(stage["id"]),
        "label": str(stage["label"]),
        "description": str(stage["description"]),
        "required_fields": [str(field_name) for field_name in stage["required_fields"]],
        "next_stage": str(stage["next_stage"]) if stage["next_stage"] is not None else None,
    }


def _normalize_field_list(value: object, *, context: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{context} must be a list of non-empty field names.")
    normalized = [str(item).strip() for item in value if str(item).strip()]
    if len(normalized) != len(value):
        raise ValueError(f"{context} contains blank field names.")
    return normalized


def _validate_stage_definitions(data: dict[str, Any]) -> dict[str, Any]:
    version = str(data.get("version") or "").strip()
    if not version:
        raise ValueError("Workflow contracts must define a non-empty version.")

    workflows = data.get("workflows")
    if not isinstance(workflows, dict):
        raise ValueError("Workflow contracts must define a 'workflows' mapping.")

    workflow_keys = set(workflows.keys())
    missing_workflows = EXPECTED_WORKFLOWS - workflow_keys
    unexpected_workflows = workflow_keys - EXPECTED_WORKFLOWS
    if missing_workflows or unexpected_workflows:
        raise ValueError(
            "Workflow contracts must contain exactly these workflows: "
            f"{sorted(EXPECTED_WORKFLOWS)}."
        )

    normalized_workflows: dict[str, Any] = {}
    for workflow_key in sorted(EXPECTED_WORKFLOWS):
        workflow = workflows.get(workflow_key)
        if not isinstance(workflow, dict):
            raise ValueError(f"Workflow '{workflow_key}' must map to an object.")

        label = str(workflow.get("label") or "").strip()
        description = str(workflow.get("description") or "").strip()
        stages = workflow.get("stages")
        if not label or not description:
            raise ValueError(f"Workflow '{workflow_key}' must define label and description.")
        if not isinstance(stages, list) or not stages:
            raise ValueError(f"Workflow '{workflow_key}' must define a non-empty stages list.")

        stage_ids: list[str] = []
        normalized_stages: list[dict[str, Any]] = []
        aggregated_fields: list[str] = []
        for stage in stages:
            if not isinstance(stage, dict):
                raise ValueError(f"Workflow '{workflow_key}' contains an invalid stage entry.")
            required_keys = {"id", "label", "description", "required_fields", "next_stage"}
            if not required_keys.issubset(stage):
                missing_keys = sorted(required_keys - set(stage.keys()))
                raise ValueError(
                    f"Workflow '{workflow_key}' stage is missing keys: {missing_keys}."
                )

            normalized_stage = _normalize_stage(stage)
            stage_ids.append(normalized_stage["id"])
            normalized_stages.append(normalized_stage)
            aggregated_fields.extend(normalized_stage["required_fields"])

        if len(stage_ids) != len(set(stage_ids)):
            raise ValueError(f"Workflow '{workflow_key}' contains duplicate stage ids.")

        valid_stage_ids = set(stage_ids)
        for stage in normalized_stages:
            next_stage = stage["next_stage"]
            if next_stage is not None and next_stage not in valid_stage_ids:
                raise ValueError(
                    f"Workflow '{workflow_key}' stage '{stage['id']}' points to unknown next_stage '{next_stage}'."
                )

        supported_fields = workflow.get("supported_fields")
        if supported_fields is None:
            supported_fields = list(dict.fromkeys(aggregated_fields))
        normalized_supported_fields = _normalize_field_list(
            supported_fields,
            context=f"Workflow '{workflow_key}' supported_fields",
        )

        summary_required_fields = workflow.get("summary_required_fields")
        if summary_required_fields is None:
            summary_required_fields = list(normalized_supported_fields)
        normalized_summary_fields = _normalize_field_list(
            summary_required_fields,
            context=f"Workflow '{workflow_key}' summary_required_fields",
        )

        generation_required_fields = workflow.get("generation_required_fields")
        if generation_required_fields is None:
            generation_required_fields = list(normalized_supported_fields)
        normalized_generation_fields = _normalize_field_list(
            generation_required_fields,
            context=f"Workflow '{workflow_key}' generation_required_fields",
        )

        supported_field_set = set(normalized_supported_fields)
        for field_name in normalized_summary_fields + normalized_generation_fields:
            if field_name not in supported_field_set:
                raise ValueError(
                    f"Workflow '{workflow_key}' readiness field '{field_name}' must also be listed in supported_fields."
                )
        for stage in normalized_stages:
            for field_name in stage["required_fields"]:
                if field_name not in supported_field_set:
                    raise ValueError(
                        f"Workflow '{workflow_key}' stage '{stage['id']}' field '{field_name}' must be listed in supported_fields."
                    )

        normalized_workflows[workflow_key] = {
            "label": label,
            "description": description,
            "stages": normalized_stages,
            "supported_fields": normalized_supported_fields,
            "summary_required_fields": normalized_summary_fields,
            "generation_required_fields": normalized_generation_fields,
        }

    return {
        "version": version,
        "workflows": normalized_workflows,
    }


@lru_cache(maxsize=1)
def load_stage_definitions() -> dict[str, Any]:
    with CONTRACTS_PATH.open("r", encoding="utf-8") as file_handle:
        raw_data = yaml.safe_load(file_handle) or {}

    if not isinstance(raw_data, dict):
        raise ValueError("Workflow contracts must deserialize into a mapping.")

    return _validate_stage_definitions(raw_data)


def get_workflow_contract(workflow_type: WorkflowTypeEnum) -> dict[str, Any]:
    definitions = load_stage_definitions()
    workflow = definitions["workflows"].get(workflow_type.value)
    if not isinstance(workflow, dict):
        raise ValueError(f"Unknown workflow contract: {workflow_type.value}")
    return workflow


def _find_stage(workflow: dict[str, Any], stage_id: str) -> dict[str, Any]:
    for stage in workflow["stages"]:
        if stage["id"] == stage_id:
            return stage
    raise SessionValidationError(f"Unknown workflow stage: {stage_id}")


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) > 0
    return True


def _normalize_collected_fields(
    workflow_type: WorkflowTypeEnum,
    workflow: dict[str, Any],
    collected_fields: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    supported_fields = set(workflow["supported_fields"])
    legacy_aliases = LEGACY_FIELD_ALIASES.get(workflow_type, {})

    for field_name, raw_value in (collected_fields or {}).items():
        normalized_name = str(field_name).strip()
        if not normalized_name:
            continue
        normalized_name = legacy_aliases.get(normalized_name, normalized_name)
        if _is_present(raw_value):
            normalized[normalized_name] = raw_value

    return normalized


def _calculate_missing_fields(required_fields: list[str], collected_fields: dict[str, Any]) -> list[str]:
    return [
        field_name for field_name in required_fields if not _is_present(collected_fields.get(field_name))
    ]


def _resolve_stage_progression(
    workflow: dict[str, Any],
    current_stage: str,
    collected_fields: dict[str, Any],
    *,
    advance_stage: bool,
) -> tuple[str, list[str]]:
    stage = _find_stage(workflow, current_stage)
    missing_fields = _calculate_missing_fields(stage["required_fields"], collected_fields)
    if not advance_stage:
        return current_stage, missing_fields

    resolved_stage = current_stage
    while not missing_fields and stage["next_stage"] is not None:
        resolved_stage = str(stage["next_stage"])
        stage = _find_stage(workflow, resolved_stage)
        missing_fields = _calculate_missing_fields(stage["required_fields"], collected_fields)

    return resolved_stage, missing_fields


def _calculate_completion_score(workflow: dict[str, Any], collected_fields: dict[str, Any]) -> int:
    supported_fields = workflow["supported_fields"]
    if not supported_fields:
        return 100

    populated_fields = sum(
        1 for field_name in supported_fields if _is_present(collected_fields.get(field_name))
    )
    return int(round((populated_fields / len(supported_fields)) * 100))


def _calculate_readiness(workflow: dict[str, Any], collected_fields: dict[str, Any]) -> tuple[bool, bool]:
    is_ready_for_summary = all(
        _is_present(collected_fields.get(field_name))
        for field_name in workflow["summary_required_fields"]
    )
    is_ready_for_generation = all(
        _is_present(collected_fields.get(field_name))
        for field_name in workflow["generation_required_fields"]
    )
    return is_ready_for_summary, is_ready_for_generation


def _build_planning_state_values(
    workflow_type: WorkflowTypeEnum,
    *,
    current_stage: str,
    collected_fields: dict[str, Any] | None,
    version: int,
    advance_stage: bool,
) -> dict[str, Any]:
    workflow = get_workflow_contract(workflow_type)
    normalized_fields = _normalize_collected_fields(workflow_type, workflow, collected_fields)
    resolved_stage, missing_fields = _resolve_stage_progression(
        workflow,
        current_stage,
        normalized_fields,
        advance_stage=advance_stage,
    )
    completion_score = _calculate_completion_score(workflow, normalized_fields)
    is_ready_for_summary, is_ready_for_generation = _calculate_readiness(
        workflow,
        normalized_fields,
    )

    return {
        "workflow_type": workflow_type,
        "current_stage": resolved_stage,
        "collected_fields": normalized_fields,
        "missing_fields": missing_fields,
        "completion_score": completion_score,
        "is_ready_for_summary": is_ready_for_summary,
        "is_ready_for_generation": is_ready_for_generation,
        "version": version,
    }


def build_initial_planning_state(workflow_type: WorkflowTypeEnum) -> dict[str, Any]:
    workflow = get_workflow_contract(workflow_type)
    first_stage = workflow["stages"][0]
    return _build_planning_state_values(
        workflow_type,
        current_stage=first_stage["id"],
        collected_fields={},
        version=1,
        advance_stage=False,
    )


def list_workflow_summaries() -> list[dict[str, Any]]:
    definitions = load_stage_definitions()
    workflow_summaries: list[dict[str, Any]] = []
    for workflow_key in sorted(definitions["workflows"].keys()):
        workflow = definitions["workflows"][workflow_key]
        workflow_summaries.append(
            {
                "workflow_type": WorkflowTypeEnum(workflow_key),
                "label": workflow["label"],
                "description": workflow["description"],
                "first_stage": workflow["stages"][0]["id"],
                "stage_count": len(workflow["stages"]),
            }
        )
    return workflow_summaries


def get_workflow_definition(workflow_type: WorkflowTypeEnum) -> dict[str, Any]:
    workflow = get_workflow_contract(workflow_type)
    return {
        "workflow_type": workflow_type,
        "label": workflow["label"],
        "description": workflow["description"],
        "stages": workflow["stages"],
        "supported_fields": workflow["supported_fields"],
        "summary_required_fields": workflow["summary_required_fields"],
        "generation_required_fields": workflow["generation_required_fields"],
        "initial_state": build_initial_planning_state(workflow_type),
    }


def build_session_preview(
    *,
    title: str | None,
    workflow_type: WorkflowTypeEnum,
) -> dict[str, Any]:
    workflow_definition = get_workflow_definition(workflow_type)
    resolved_title = (title or "").strip() or workflow_definition["label"]
    return {
        "title": resolved_title,
        "workflow_type": workflow_type,
        "initial_state": workflow_definition["initial_state"],
    }


def _get_or_create_deferred_user(
    db: Session,
    *,
    user_email: str | None,
    user_display_name: str | None,
) -> User:
    normalized_email = (user_email or DEFAULT_DEFERRED_USER_EMAIL).strip().lower()
    normalized_display_name = (
        (user_display_name or DEFAULT_DEFERRED_USER_DISPLAY_NAME).strip()
        or DEFAULT_DEFERRED_USER_DISPLAY_NAME
    )

    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is not None:
        if user.display_name != normalized_display_name:
            user.display_name = normalized_display_name
        return user

    user = User(
        email=normalized_email,
        display_name=normalized_display_name,
    )
    db.add(user)
    db.flush()
    return user


def _load_session(db: Session, session_id: UUID) -> StudioSession | None:
    statement = (
        select(StudioSession)
        .options(
            joinedload(StudioSession.planning_state),
            joinedload(StudioSession.generated_documents),
        )
        .where(StudioSession.id == session_id)
    )
    return db.execute(statement).unique().scalar_one_or_none()


def _serialize_generated_document(document: GeneratedDocument) -> dict[str, Any]:
    return {
        "id": document.id,
        "session_id": document.session_id,
        "user_id": document.user_id,
        "kind": document.kind,
        "title": document.title,
        "status": document.status,
        "content_json": document.content_json,
        "content_markdown": document.content_markdown,
        "storage_uri": document.storage_uri,
        "version": document.version,
        "generated_from_state_version": document.generated_from_state_version,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }


def _serialize_planning_state(state: PlanningState) -> dict[str, Any]:
    return {
        "workflow_type": state.workflow_type,
        "current_stage": state.current_stage,
        "collected_fields": state.collected_fields,
        "missing_fields": list(state.missing_fields),
        "completion_score": state.completion_score,
        "is_ready_for_summary": state.is_ready_for_summary,
        "is_ready_for_generation": state.is_ready_for_generation,
        "version": state.version,
    }


def _serialize_session(session: StudioSession) -> dict[str, Any]:
    if session.planning_state is None:
        raise SessionValidationError("Studio session does not have a planning_state record.")

    ordered_documents = sorted(
        session.generated_documents,
        key=lambda document: (document.version, document.created_at),
    )
    return {
        "id": session.id,
        "user_id": session.user_id,
        "title": session.title,
        "workflow_type": session.workflow_type,
        "current_stage": session.current_stage,
        "status": session.status,
        "completion_score": session.completion_score,
        "last_message_at": session.last_message_at,
        "planning_state": _serialize_planning_state(session.planning_state),
        "generated_documents": [
            _serialize_generated_document(document)
            for document in ordered_documents
        ],
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }


def create_studio_session(
    db: Session,
    *,
    workflow_type: WorkflowTypeEnum,
    title: str | None,
    user_email: str | None,
    user_display_name: str | None,
) -> dict[str, Any]:
    initial_state = build_initial_planning_state(workflow_type)
    workflow_definition = get_workflow_definition(workflow_type)
    resolved_title = (title or "").strip() or workflow_definition["label"]
    user = _get_or_create_deferred_user(
        db,
        user_email=user_email,
        user_display_name=user_display_name,
    )

    session = StudioSession(
        user_id=user.id,
        title=resolved_title,
        workflow_type=workflow_type,
        current_stage=initial_state["current_stage"],
        status=SessionStatusEnum.ACTIVE,
        completion_score=initial_state["completion_score"],
    )
    planning_state = PlanningState(
        workflow_type=workflow_type,
        current_stage=initial_state["current_stage"],
        collected_fields=initial_state["collected_fields"],
        missing_fields=initial_state["missing_fields"],
        completion_score=initial_state["completion_score"],
        is_ready_for_summary=initial_state["is_ready_for_summary"],
        is_ready_for_generation=initial_state["is_ready_for_generation"],
        version=initial_state["version"],
    )
    session.planning_state = planning_state

    db.add(session)
    db.commit()

    stored_session = _load_session(db, session.id)
    if stored_session is None:
        raise SessionServiceError("Studio session could not be reloaded after creation.")
    return _serialize_session(stored_session)


def get_studio_session_detail(db: Session, session_id: UUID) -> dict[str, Any]:
    session = _load_session(db, session_id)
    if session is None:
        raise SessionNotFoundError(f"Studio session '{session_id}' was not found.")
    return _serialize_session(session)


def update_studio_session_planning_state(
    db: Session,
    *,
    session_id: UUID,
    collected_fields: dict[str, Any],
    advance_stage: bool,
) -> dict[str, Any]:
    session = _load_session(db, session_id)
    if session is None:
        raise SessionNotFoundError(f"Studio session '{session_id}' was not found.")
    if session.planning_state is None:
        raise SessionValidationError("Studio session does not have a planning_state record.")

    workflow = get_workflow_contract(session.workflow_type)
    current_fields = dict(session.planning_state.collected_fields or {})
    current_fields.update(collected_fields)
    next_version = int(session.planning_state.version) + 1
    next_state = _build_planning_state_values(
        session.workflow_type,
        current_stage=session.planning_state.current_stage,
        collected_fields=current_fields,
        version=next_version,
        advance_stage=advance_stage,
    )

    session.planning_state.current_stage = next_state["current_stage"]
    session.planning_state.collected_fields = next_state["collected_fields"]
    session.planning_state.missing_fields = next_state["missing_fields"]
    session.planning_state.completion_score = next_state["completion_score"]
    session.planning_state.is_ready_for_summary = next_state["is_ready_for_summary"]
    session.planning_state.is_ready_for_generation = next_state["is_ready_for_generation"]
    session.planning_state.version = next_state["version"]

    session.current_stage = next_state["current_stage"]
    session.completion_score = next_state["completion_score"]
    if session.planning_state.is_ready_for_generation:
        session.status = SessionStatusEnum.ACTIVE

    # Ensure missing fields are always aligned with the refreshed contract.
    current_stage = _find_stage(workflow, session.planning_state.current_stage)
    session.planning_state.missing_fields = _calculate_missing_fields(
        current_stage["required_fields"],
        session.planning_state.collected_fields,
    )

    db.commit()

    stored_session = _load_session(db, session.id)
    if stored_session is None:
        raise SessionServiceError("Studio session could not be reloaded after planning update.")
    return _serialize_session(stored_session)


def _format_markdown_value(value: Any) -> str:
    if isinstance(value, list):
        return "\n".join(f"- {item}" for item in value)
    if isinstance(value, dict):
        return "\n".join(f"- **{key}**: {item}" for key, item in value.items())
    return str(value)


def _render_generated_document_markdown(
    session: StudioSession,
    planning_state: PlanningState,
) -> str:
    workflow = get_workflow_contract(session.workflow_type)
    title = (
        planning_state.collected_fields.get("project_title")
        or session.title
    )
    lines = [
        f"# {title}",
        "",
        f"- Workflow: {session.workflow_type.value}",
        f"- Stage: {planning_state.current_stage}",
        f"- Completion Score: {planning_state.completion_score}",
        "",
    ]

    for stage in workflow["stages"]:
        section_lines: list[str] = []
        for field_name in stage["required_fields"]:
            value = planning_state.collected_fields.get(field_name)
            if not _is_present(value):
                continue
            pretty_name = field_name.replace("_", " ").title()
            section_lines.append(f"## {pretty_name}")
            section_lines.append(_format_markdown_value(value))
            section_lines.append("")
        if section_lines:
            lines.extend(section_lines)

    return "\n".join(lines).strip()


def finalize_studio_session(
    db: Session,
    *,
    session_id: UUID,
) -> dict[str, Any]:
    session = _load_session(db, session_id)
    if session is None:
        raise SessionNotFoundError(f"Studio session '{session_id}' was not found.")
    if session.planning_state is None:
        raise SessionValidationError("Studio session does not have a planning_state record.")
    if not session.planning_state.is_ready_for_generation:
        raise SessionValidationError(
            "Planning state is not ready for generation. Complete all required PJBL fields first."
        )

    latest_version = max(
        (document.version for document in session.generated_documents),
        default=0,
    )
    generated_document = GeneratedDocument(
        session_id=session.id,
        user_id=session.user_id,
        kind=(
            GeneratedDocumentKindEnum.PROJECT_PLAN
            if session.workflow_type == WorkflowTypeEnum.PJBL
            else GeneratedDocumentKindEnum.LESSON_PLAN
        ),
        title=(
            str(session.planning_state.collected_fields.get("project_title") or session.title)
            .strip()
            or session.title
        ),
        status=GeneratedDocumentStatusEnum.FINAL,
        content_json={
            "session_id": str(session.id),
            "workflow_type": session.workflow_type.value,
            "current_stage": session.planning_state.current_stage,
            "completion_score": session.planning_state.completion_score,
            "is_ready_for_summary": session.planning_state.is_ready_for_summary,
            "is_ready_for_generation": session.planning_state.is_ready_for_generation,
            "collected_fields": session.planning_state.collected_fields,
        },
        content_markdown=_render_generated_document_markdown(
            session,
            session.planning_state,
        ),
        version=latest_version + 1,
        generated_from_state_version=session.planning_state.version,
    )

    session.generated_documents.append(generated_document)
    session.status = SessionStatusEnum.COMPLETED
    session.completion_score = session.planning_state.completion_score

    db.commit()

    stored_session = _load_session(db, session.id)
    if stored_session is None:
        raise SessionServiceError("Studio session could not be reloaded after finalization.")
    if not stored_session.generated_documents:
        raise SessionServiceError("Finalization completed but no generated document was found.")

    latest_document = max(stored_session.generated_documents, key=lambda document: document.version)
    return {
        "session": _serialize_session(stored_session),
        "generated_document": _serialize_generated_document(latest_document),
    }


def get_service_health() -> dict[str, Any]:
    definitions = load_stage_definitions()
    return {
        "status": "ok",
        "database": "ok" if database_healthcheck() else "unavailable",
        "contract_version": definitions["version"],
        "available_workflows": sorted(definitions["workflows"].keys()),
    }
