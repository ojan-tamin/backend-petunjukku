from __future__ import annotations

from app.ai.workflow import field_label


SUMMARY_GROUPS = {
    "Konteks dasar pembelajaran": [
        "education_level",
        "phase",
        "grade_level",
        "subject_or_theme",
        "topic",
        "duration",
        "school_context",
        "student_characteristics",
    ],
    "Tujuan pembelajaran": [
        "learning_objectives",
        "expected_competencies",
        "special_notes",
    ],
    "Rancangan kegiatan pembelajaran": [
        "teaching_approach",
        "learning_model",
        "learning_methods",
        "opening_activities",
        "main_activities",
        "closing_activities",
        "differentiation_strategy",
    ],
    "Asesmen dan unsur pendukung": [
        "assessment_types",
        "assessment_techniques",
        "assessment_instruments",
        "success_indicators",
        "learning_media",
        "learning_resources",
        "teacher_reflection_prompt",
        "student_reflection_prompt",
    ],
    "Catatan/revisi": ["revision_notes"],
}

PJBL_GROUPS = {
    "Identitas proyek": ["project_identity", "project_topic"],
    "Tujuan dan pertanyaan pemantik": ["project_objectives", "driving_question"],
    "Rancangan proyek": ["final_product", "project_steps", "project_schedule", "student_roles"],
    "Asesmen dan refleksi": ["project_assessment", "rubric", "reflection"],
}


def build_summary_sections(workflow_type: str, fields: dict) -> dict:
    groups = PJBL_GROUPS if workflow_type == "pjbl" else SUMMARY_GROUPS
    sections: dict[str, dict[str, str]] = {}
    for title, keys in groups.items():
        values = {}
        for key in keys:
            value = fields.get(key)
            if value:
                values[field_label(key)] = str(value)
        sections[title] = values
    return sections


def build_summary_text(workflow_type: str, fields: dict, missing_fields: list[str]) -> str:
    sections = build_summary_sections(workflow_type, fields)
    lines = ["Ringkasan hasil diskusi:"]
    for title, values in sections.items():
        lines.append(f"\n## {title}")
        if not values:
            lines.append("- Belum ada data yang terisi.")
            continue
        for label, value in values.items():
            lines.append(f"- {label}: {value}")

    lines.append("\n## Field yang belum lengkap")
    if missing_fields:
        for field in missing_fields:
            lines.append(f"- {field_label(field)}")
    else:
        lines.append("- Tidak ada field wajib yang belum lengkap.")

    lines.append("\nMohon konfirmasi apakah ringkasan ini sudah sesuai sebelum dokumen final dibuat.")
    return "\n".join(lines)
