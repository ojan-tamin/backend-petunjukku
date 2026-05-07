from __future__ import annotations

from app.ai.summary import build_summary_text
from app.ai.workflow import STAGE_LABELS, field_label


def build_assistant_message(
    *,
    workflow_type: str,
    current_stage: str,
    updated_fields: dict,
    collected_fields: dict,
    missing_fields: list[str],
    completion_score: int,
    is_ready_for_summary: bool,
    is_ready_for_generation: bool,
    approved_summary: bool,
) -> str:
    if is_ready_for_generation:
        return "Baik Bapak/Ibu, ringkasannya sudah disetujui. Dokumen final sudah siap dibuat."

    if is_ready_for_summary and current_stage == "stage_5":
        summary = build_summary_text(workflow_type, collected_fields, missing_fields)
        if approved_summary:
            return "Terima kasih, Bapak/Ibu. Saya akan siapkan dokumen final berdasarkan ringkasan ini."
        return f"{summary}\n\nJika sudah sesuai, balas dengan setuju atau lanjut generate."

    field_notes = ""
    if updated_fields:
        labels = ", ".join(field_label(field) for field in updated_fields.keys())
        field_notes = f"Saya sudah mencatat {labels}. "

    if workflow_type == "pjbl":
        questions = _build_questions(missing_fields)
        return (
            f"{field_notes}Kelengkapan rancangan PjBL saat ini {completion_score}%. "
            f"{questions}"
        ).strip()

    stage_label = STAGE_LABELS.get(current_stage, "tahap saat ini")
    questions = _build_questions(missing_fields)
    return (
        f"{field_notes}Kita sedang berada di tahap {stage_label}. "
        f"Kelengkapan sementara {completion_score}%. {questions}"
    ).strip()


def build_clarification_message(
    *,
    missing_fields: list[str],
    current_stage: str,
) -> str:
    questions = _build_questions(missing_fields)
    stage_label = STAGE_LABELS.get(current_stage, "tahap saat ini")
    return (
        f"Maaf Bapak/Ibu, jawaban tadi belum memuat informasi yang dibutuhkan untuk {stage_label}. "
        f"{questions}"
    ).strip()


def _build_questions(missing_fields: list[str]) -> str:
    selected = missing_fields[:3]
    if not selected:
        return "Data pada tahap ini sudah cukup. Saya akan lanjut ke tahap berikutnya."

    if len(selected) == 1:
        return f"Boleh Bapak/Ibu lengkapi {field_label(selected[0])}?"

    readable = ", ".join(field_label(field) for field in selected[:-1])
    readable = f"{readable}, dan {field_label(selected[-1])}"
    return f"Boleh Bapak/Ibu lengkapi {readable}?"
