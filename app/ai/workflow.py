from __future__ import annotations

INTRAKURIKULER_STAGES = ["stage_1", "stage_2", "stage_3", "stage_4", "stage_5"]

STAGE_LABELS = {
    "stage_1": "Konteks dasar pembelajaran",
    "stage_2": "Tujuan pembelajaran",
    "stage_3": "Rancangan kegiatan pembelajaran",
    "stage_4": "Asesmen dan unsur pendukung",
    "stage_5": "Review dan finalisasi dokumen",
}

INTRAKURIKULER_REQUIRED_FIELDS = {
    "stage_1": [
        "education_level",
        "grade_level",
        "subject_or_theme",
        "topic",
        "duration",
    ],
    "stage_2": [
        "learning_objectives",
        "expected_competencies",
    ],
    "stage_3": [
        "learning_model",
        "opening_activities",
        "main_activities",
        "closing_activities",
    ],
    "stage_4": [
        "assessment_types",
        "success_indicators",
        "learning_media",
        "learning_resources",
    ],
    "stage_5": [],
}

INTRAKURIKULER_OPTIONAL_FIELDS = {
    "stage_1": ["phase", "school_context", "student_characteristics"],
    "stage_2": ["special_notes"],
    "stage_3": ["teaching_approach", "learning_methods", "differentiation_strategy"],
    "stage_4": [
        "assessment_techniques",
        "assessment_instruments",
        "teacher_reflection_prompt",
        "student_reflection_prompt",
    ],
    "stage_5": ["revision_notes"],
}

PJBL_REQUIRED_FIELDS = {
    "pjbl_stage_1": [
        "project_identity",
        "project_topic",
        "project_objectives",
        "driving_question",
        "final_product",
        "project_steps",
        "project_schedule",
        "student_roles",
        "project_assessment",
        "rubric",
        "reflection",
    ]
}

FIELD_LABELS = {
    "education_level": "jenjang pendidikan",
    "phase": "fase",
    "grade_level": "kelas",
    "subject_or_theme": "mata pelajaran atau tema",
    "topic": "topik atau materi utama",
    "duration": "alokasi waktu",
    "school_context": "konteks sekolah",
    "student_characteristics": "karakteristik siswa",
    "learning_objectives": "tujuan pembelajaran",
    "expected_competencies": "kompetensi yang diharapkan",
    "special_notes": "catatan khusus",
    "teaching_approach": "pendekatan pembelajaran",
    "learning_model": "model pembelajaran",
    "learning_methods": "metode pembelajaran",
    "opening_activities": "kegiatan pembuka",
    "main_activities": "kegiatan inti",
    "closing_activities": "kegiatan penutup",
    "differentiation_strategy": "strategi diferensiasi",
    "assessment_types": "jenis asesmen",
    "assessment_techniques": "teknik penilaian",
    "assessment_instruments": "instrumen penilaian",
    "success_indicators": "indikator keberhasilan",
    "learning_media": "media pembelajaran",
    "learning_resources": "sumber belajar",
    "teacher_reflection_prompt": "refleksi guru",
    "student_reflection_prompt": "refleksi siswa",
    "project_identity": "identitas proyek",
    "project_topic": "topik proyek",
    "project_objectives": "tujuan proyek",
    "driving_question": "pertanyaan pemantik",
    "final_product": "produk akhir",
    "project_steps": "langkah kegiatan proyek",
    "project_schedule": "jadwal pelaksanaan",
    "student_roles": "pembagian peran siswa",
    "project_assessment": "asesmen proyek",
    "rubric": "rubrik penilaian",
    "reflection": "refleksi",
}


def required_fields_for(workflow_type: str, stage: str) -> list[str]:
    if workflow_type == "pjbl":
        return PJBL_REQUIRED_FIELDS.get(stage, [])
    return INTRAKURIKULER_REQUIRED_FIELDS.get(stage, [])


def all_required_fields(workflow_type: str) -> list[str]:
    field_map = PJBL_REQUIRED_FIELDS if workflow_type == "pjbl" else INTRAKURIKULER_REQUIRED_FIELDS
    fields: list[str] = []
    for values in field_map.values():
        fields.extend(values)
    return fields


def initial_stage(workflow_type: str) -> str:
    return "pjbl_stage_1" if workflow_type == "pjbl" else "stage_1"


def field_label(field: str) -> str:
    return FIELD_LABELS.get(field, field.replace("_", " "))
