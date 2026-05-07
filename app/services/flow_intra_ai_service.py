from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.ai.dialogue_manager import build_assistant_message, build_clarification_message
from app.ai.interpreter import (
    clean_text,
    interpret_user_message,
    user_approved_summary,
    user_requested_revision,
)
from app.ai.json_parser import JSONParseError, extract_json_object
from app.ai.llm_client import LLMClient, LLMError
from app.ai.prompts.flow_intra_prompt import (
    build_document_messages,
    build_flow_intra_messages,
    build_summary_messages,
)
from app.ai.stage_manager import evaluate_state
from app.ai.workflow import (
    INTRAKURIKULER_OPTIONAL_FIELDS,
    INTRAKURIKULER_REQUIRED_FIELDS,
)
from app.core.config import settings


class FlowIntraAIError(RuntimeError):
    status_code = 503
    public_detail = "AI Flow Intra service is unavailable"


class FlowIntraAIInvalidOutputError(FlowIntraAIError):
    status_code = 502
    public_detail = "AI Flow Intra returned invalid structured output"


@dataclass(frozen=True)
class FlowIntraTurnResult:
    updated_fields: dict[str, Any]
    collected_fields: dict[str, Any]
    missing_fields: list[str]
    current_stage: str
    next_stage: str
    completion_score: int
    is_ready_for_summary: bool
    is_ready_for_generation: bool
    assistant_message: str


def _allowed_intra_fields() -> set[str]:
    fields: set[str] = set()
    for values in INTRAKURIKULER_REQUIRED_FIELDS.values():
        fields.update(values)
    for values in INTRAKURIKULER_OPTIONAL_FIELDS.values():
        fields.update(values)
    return fields


def _sanitize_updated_fields(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    allowed = _allowed_intra_fields()
    cleaned: dict[str, Any] = {}
    for key, value in raw.items():
        field = str(key or "").strip()
        if field not in allowed:
            continue
        if value is None:
            continue
        if isinstance(value, str):
            text_value = clean_text(value, 1200)
            if text_value:
                cleaned[field] = text_value
            continue
        if isinstance(value, (list, tuple)):
            values = [clean_text(item, 280) for item in value if clean_text(item, 280)]
            if values:
                cleaned[field] = values
            continue
        if isinstance(value, dict):
            compact = {str(k): clean_text(v, 300) for k, v in value.items() if clean_text(v, 300)}
            if compact:
                cleaned[field] = compact
    return cleaned


class FlowIntraAIService:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def process_turn(
        self,
        *,
        user_message: str,
        current_stage: str,
        collected_fields: dict[str, Any],
        missing_fields: list[str],
        chat_history: list[dict[str, str]] | None = None,
    ) -> FlowIntraTurnResult:
        messages = build_flow_intra_messages(
            user_message=user_message,
            current_stage=current_stage,
            collected_fields=collected_fields,
            missing_fields=missing_fields,
            chat_history=chat_history,
        )
        parse_error = False
        try:
            raw = self.llm_client.generate(
                messages,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
                response_format="json_object",
            )
            payload = extract_json_object(raw)
        except JSONParseError as exc:
            parse_error = True
            payload = self._fallback_payload(
                user_message=user_message,
                current_stage=current_stage,
                collected_fields=collected_fields,
            )
        except LLMError as exc:
            raise FlowIntraAIError(exc.public_detail) from exc

        updated_fields = _sanitize_updated_fields(payload.get("updated_fields"))
        merged_fields = dict(collected_fields or {})
        merged_fields.update(updated_fields)

        approved_summary = bool(payload.get("is_ready_for_generation")) or user_approved_summary(user_message)
        revision_requested = user_requested_revision(user_message)
        evaluation = evaluate_state(
            workflow_type="intrakurikuler",
            current_stage=current_stage,
            fields=merged_fields,
            approved_summary=approved_summary,
            revision_requested=revision_requested,
        )

        no_new_information = (
            not updated_fields
            and not approved_summary
            and not revision_requested
            and bool(evaluation["missing_fields"])
        )
        if no_new_information:
            assistant_message = build_clarification_message(
                missing_fields=evaluation["missing_fields"],
                current_stage=evaluation["next_stage"],
            )
        else:
            assistant_message = build_assistant_message(
                workflow_type="intrakurikuler",
                current_stage=evaluation["next_stage"],
                updated_fields=updated_fields,
                collected_fields=merged_fields,
                missing_fields=evaluation["missing_fields"],
                completion_score=evaluation["completion_score"],
                is_ready_for_summary=evaluation["is_ready_for_summary"],
                is_ready_for_generation=evaluation["is_ready_for_generation"],
                approved_summary=approved_summary,
            )
        if parse_error:
            assistant_message = clean_text(assistant_message, 2400)

        return FlowIntraTurnResult(
            updated_fields=updated_fields,
            collected_fields=merged_fields,
            missing_fields=list(evaluation["missing_fields"]),
            current_stage=current_stage,
            next_stage=evaluation["next_stage"],
            completion_score=int(evaluation["completion_score"]),
            is_ready_for_summary=bool(evaluation["is_ready_for_summary"]),
            is_ready_for_generation=bool(evaluation["is_ready_for_generation"]),
            assistant_message=assistant_message,
        )

    @staticmethod
    def _fallback_payload(
        *,
        user_message: str,
        current_stage: str,
        collected_fields: dict[str, Any],
    ) -> dict[str, Any]:
        interpretation = interpret_user_message(
            workflow_type="intrakurikuler",
            current_stage=current_stage,
            current_fields=collected_fields or {},
            user_message=user_message,
        )
        return {
            "updated_fields": interpretation["updated_fields"],
            "is_ready_for_generation": interpretation["approved_summary"],
        }

    def generate_summary(
        self,
        *,
        collected_fields: dict[str, Any],
        missing_fields: list[str],
    ) -> str:
        try:
            summary = self.llm_client.generate(
                build_summary_messages(
                    collected_fields=collected_fields,
                    missing_fields=missing_fields,
                ),
                temperature=0.2,
                max_tokens=max(settings.llm_max_tokens, 2048),
            )
        except LLMError as exc:
            raise FlowIntraAIError(exc.public_detail) from exc
        text = str(summary or "").strip()
        if not text:
            raise FlowIntraAIInvalidOutputError("LLM summary is empty")
        return text

    def generate_intrakurikuler_document(self, *, collected_fields: dict[str, Any]) -> dict[str, Any]:
        try:
            content = self.llm_client.generate(
                build_document_messages(collected_fields=collected_fields),
                temperature=0.25,
                max_tokens=max(settings.llm_max_tokens, 4096),
            )
        except LLMError as exc:
            raise FlowIntraAIError(exc.public_detail) from exc
        content = str(content or "").strip()
        if not content:
            raise FlowIntraAIInvalidOutputError("LLM document is empty")
        subject = clean_text(collected_fields.get("subject_or_theme"), 80) or "Intrakurikuler"
        grade = clean_text(collected_fields.get("grade_level"), 80)
        title = f"Dokumen Intrakurikuler - {subject}{(' ' + grade) if grade else ''}"
        return {
            "title": title,
            "content": content,
            "document_output": {
                "provider": settings.llm_provider,
                "model": settings.llm_model,
                "source": "llm",
                "fields": collected_fields,
            },
        }


def get_flow_intra_ai_service() -> FlowIntraAIService:
    return FlowIntraAIService()
