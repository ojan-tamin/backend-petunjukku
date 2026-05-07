from __future__ import annotations

import re
from typing import Any


SUBJECT_ALIASES = {
    "ipa": "IPA",
    "ips": "IPS",
    "matematika": "Matematika",
    "mtk": "Matematika",
    "bahasa indonesia": "Bahasa Indonesia",
    "bahasa inggris": "Bahasa Inggris",
    "ppkn": "PPKn",
    "pkn": "PPKn",
    "pai": "PAI",
    "informatika": "Informatika",
    "seni budaya": "Seni Budaya",
    "pjok": "PJOK",
    "ipas": "IPAS",
}


def clean_text(value: Any, limit: int = 600) -> str:
    return " ".join(str(value or "").strip().split())[:limit]


def _first_match(patterns: list[str], text: str, *, flags: int = re.IGNORECASE) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            return clean_text(match.group(1), 600)
    return ""


def _extract_subject(text: str) -> str:
    lowered = text.lower()
    explicit = _first_match(
        [
            r"(?:mapel|mata pelajaran)\s+(?:adalah\s+)?([^,.]+)",
            r"(?:untuk|di)\s+pelajaran\s+([^,.]+)",
        ],
        text,
    )
    if explicit:
        return explicit
    for alias, label in SUBJECT_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", lowered):
            return label
    return ""


def _extract_grade(text: str) -> str:
    match = re.search(r"\bkelas\s+([1-9]|1[0-2])\b", text, re.IGNORECASE)
    if match:
        return f"Kelas {match.group(1)}"
    return ""


def _extract_phase(text: str) -> str:
    match = re.search(r"\bfase\s+([a-f])\b", text, re.IGNORECASE)
    if match:
        return f"Fase {match.group(1).upper()}"
    return ""


def _extract_education_level(text: str) -> str:
    lowered = text.lower()
    if re.search(r"\b(sd|mi|sekolah dasar)\b", lowered):
        return "SD/MI"
    if re.search(r"\b(smp|mts)\b", lowered):
        return "SMP/MTs"
    if re.search(r"\b(sma|ma|smk|mak)\b", lowered):
        return "SMA/SMK/MA"
    grade = _extract_grade(text)
    if grade:
        number = int(re.search(r"\d+", grade).group(0))
        if number <= 6:
            return "SD/MI"
        if number <= 9:
            return "SMP/MTs"
        return "SMA/SMK/MA"
    return ""


def _extract_topic(text: str) -> str:
    explicit = _first_match(
        [
            r"(?:topik|materi|tema)\s+(?:utamanya\s+|adalah\s+|tentang\s+)?([^,.]+)",
            r"(?:membahas|belajar tentang|tentang)\s+([^,.]+)",
        ],
        text,
    )
    if explicit:
        return explicit

    parts = [part.strip() for part in re.split(r"[,.;]", text) if part.strip()]
    for part in parts:
        lowered = part.lower()
        if any(marker in lowered for marker in ("kelas", "fase", "mapel", "mata pelajaran")):
            continue
        if 2 <= len(part.split()) <= 8:
            return clean_text(part, 160)
    return ""


def _extract_duration(text: str) -> str:
    return _first_match(
        [
            r"(\d+\s*(?:jp|jam pelajaran|jam|menit|pertemuan|minggu))",
            r"(?:alokasi waktu|durasi)\s+(?:adalah\s+)?([^,.]+)",
        ],
        text,
    )


def _extract_sentence_after(keywords: list[str], text: str) -> str:
    joined = "|".join(re.escape(keyword) for keyword in keywords)
    return _first_match([rf"(?:{joined})\s*(?:adalah|:|-)?\s*([^.;]+)"], text)


def _extract_stage_1(text: str) -> dict[str, str]:
    return {
        "education_level": _extract_education_level(text),
        "phase": _extract_phase(text),
        "grade_level": _extract_grade(text),
        "subject_or_theme": _extract_subject(text),
        "topic": _extract_topic(text),
        "duration": _extract_duration(text),
        "school_context": _extract_sentence_after(["konteks sekolah", "sekolah"], text),
        "student_characteristics": _extract_sentence_after(
            ["karakteristik siswa", "karakter siswa", "muridnya", "siswanya"], text
        ),
    }


def _extract_intrakurikuler(text: str, current_stage: str) -> dict[str, str]:
    updates = _extract_stage_1(text)
    updates.update(
        {
            "learning_objectives": _extract_sentence_after(
                ["tujuan pembelajaran", "tujuannya", "agar siswa", "siswa mampu", "siswa dapat"],
                text,
            ),
            "expected_competencies": _extract_sentence_after(
                ["kompetensi", "capaian", "kemampuan"], text
            ),
            "special_notes": _extract_sentence_after(["catatan khusus", "catatan"], text),
            "teaching_approach": _extract_sentence_after(["pendekatan"], text),
            "learning_model": _extract_sentence_after(["model pembelajaran", "model"], text),
            "learning_methods": _extract_sentence_after(["metode"], text),
            "opening_activities": _extract_sentence_after(
                ["kegiatan pembuka", "pembuka", "awal pembelajaran"], text
            ),
            "main_activities": _extract_sentence_after(
                ["kegiatan inti", "aktivitas inti", "inti pembelajaran"], text
            ),
            "closing_activities": _extract_sentence_after(
                ["kegiatan penutup", "penutup", "akhir pembelajaran"], text
            ),
            "differentiation_strategy": _extract_sentence_after(["diferensiasi"], text),
            "assessment_types": _extract_sentence_after(["jenis asesmen", "asesmen", "penilaian"], text),
            "assessment_techniques": _extract_sentence_after(["teknik penilaian"], text),
            "assessment_instruments": _extract_sentence_after(["instrumen"], text),
            "success_indicators": _extract_sentence_after(["indikator keberhasilan", "berhasil jika"], text),
            "learning_media": _extract_sentence_after(["media pembelajaran", "media"], text),
            "learning_resources": _extract_sentence_after(["sumber belajar", "referensi"], text),
            "teacher_reflection_prompt": _extract_sentence_after(["refleksi guru"], text),
            "student_reflection_prompt": _extract_sentence_after(["refleksi siswa"], text),
        }
    )
    return {key: value for key, value in updates.items() if value}


def _extract_pjbl(text: str) -> dict[str, str]:
    return {
        "project_identity": _extract_sentence_after(["identitas proyek"], text),
        "project_topic": _extract_sentence_after(["topik proyek", "tema proyek"], text) or _extract_topic(text),
        "project_objectives": _extract_sentence_after(["tujuan proyek"], text),
        "driving_question": _extract_sentence_after(["pertanyaan pemantik"], text),
        "final_product": _extract_sentence_after(["produk akhir"], text),
        "project_steps": _extract_sentence_after(["langkah kegiatan", "langkah proyek"], text),
        "project_schedule": _extract_sentence_after(["jadwal"], text),
        "student_roles": _extract_sentence_after(["peran siswa", "pembagian peran"], text),
        "project_assessment": _extract_sentence_after(["asesmen proyek"], text),
        "rubric": _extract_sentence_after(["rubrik"], text),
        "reflection": _extract_sentence_after(["refleksi"], text),
    }


def user_approved_summary(text: str) -> bool:
    lowered = text.lower()
    approval_markers = [
        "setuju",
        "sudah sesuai",
        "sudah benar",
        "lanjut generate",
        "buat dokumen",
        "generate dokumen",
        "finalkan",
    ]
    return any(marker in lowered for marker in approval_markers)


def user_requested_revision(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in ("revisi", "ubah", "ganti", "koreksi", "perbaiki"))


def interpret_user_message(
    *,
    workflow_type: str,
    current_stage: str,
    current_fields: dict,
    user_message: str,
) -> dict:
    raw_updates = (
        _extract_pjbl(user_message)
        if workflow_type == "pjbl"
        else _extract_intrakurikuler(user_message, current_stage)
    )

    updated_fields = dict(current_fields or {})
    changed: dict[str, str] = {}
    for key, value in raw_updates.items():
        cleaned = clean_text(value, 1200)
        if not cleaned:
            continue
        if updated_fields.get(key) == cleaned:
            continue
        updated_fields[key] = cleaned
        changed[key] = cleaned

    return {
        "updated_fields": changed,
        "collected_fields": updated_fields,
        "approved_summary": user_approved_summary(user_message),
        "revision_requested": user_requested_revision(user_message),
    }
