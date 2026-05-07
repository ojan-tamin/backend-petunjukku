from __future__ import annotations

from app.ai.workflow import (
    INTRAKURIKULER_STAGES,
    all_required_fields,
    initial_stage,
    required_fields_for,
)


def _has_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def missing_fields(workflow_type: str, stage: str, fields: dict) -> list[str]:
    return [field for field in required_fields_for(workflow_type, stage) if not _has_value(fields.get(field))]


def completion_score(workflow_type: str, fields: dict) -> int:
    required = all_required_fields(workflow_type)
    if not required:
        return 0
    filled = sum(1 for field in required if _has_value(fields.get(field)))
    return round((filled / len(required)) * 100)


def next_stage_for(workflow_type: str, current_stage: str, fields: dict) -> str:
    if workflow_type == "pjbl":
        return "pjbl_stage_1"

    stage = current_stage if current_stage in INTRAKURIKULER_STAGES else initial_stage(workflow_type)
    while stage != "stage_5" and not missing_fields(workflow_type, stage, fields):
        index = INTRAKURIKULER_STAGES.index(stage)
        stage = INTRAKURIKULER_STAGES[index + 1]
    return stage


def evaluate_state(
    *,
    workflow_type: str,
    current_stage: str,
    fields: dict,
    approved_summary: bool = False,
    revision_requested: bool = False,
) -> dict:
    next_stage = next_stage_for(workflow_type, current_stage, fields)
    score = completion_score(workflow_type, fields)
    missing = missing_fields(workflow_type, next_stage, fields)

    is_ready_for_summary = False
    if workflow_type == "pjbl":
        is_ready_for_summary = score == 100
    else:
        is_ready_for_summary = next_stage == "stage_5" and score == 100

    is_ready_for_generation = bool(is_ready_for_summary and approved_summary)
    if revision_requested:
        is_ready_for_generation = False

    return {
        "next_stage": next_stage,
        "missing_fields": missing,
        "completion_score": score,
        "is_ready_for_summary": is_ready_for_summary,
        "is_ready_for_generation": is_ready_for_generation,
    }
