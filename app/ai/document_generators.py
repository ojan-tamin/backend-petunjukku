from __future__ import annotations

from app.ai.workflow import field_label


def _value(fields: dict, key: str) -> str:
    value = fields.get(key)
    return str(value).strip() if value else "(belum diisi)"


def _line(label: str, value: str) -> str:
    return f"- {label}: {value}"


def generate_intrakurikuler_document(fields: dict) -> dict:
    title = f"Dokumen Intrakurikuler - {_value(fields, 'subject_or_theme')} {_value(fields, 'grade_level')}"
    sections = {
        "Identitas Pembelajaran": [
            _line("Jenjang", _value(fields, "education_level")),
            _line("Fase", _value(fields, "phase")),
            _line("Kelas", _value(fields, "grade_level")),
            _line("Mata pelajaran/tema", _value(fields, "subject_or_theme")),
            _line("Topik", _value(fields, "topic")),
            _line("Alokasi waktu", _value(fields, "duration")),
        ],
        "Konteks dan Karakteristik Siswa": [
            _line("Konteks sekolah", _value(fields, "school_context")),
            _line("Karakteristik siswa", _value(fields, "student_characteristics")),
        ],
        "Tujuan Pembelajaran": [_value(fields, "learning_objectives")],
        "Kompetensi/Capaian yang Diharapkan": [_value(fields, "expected_competencies")],
        "Pendekatan, Model, dan Metode Pembelajaran": [
            _line("Pendekatan", _value(fields, "teaching_approach")),
            _line("Model", _value(fields, "learning_model")),
            _line("Metode", _value(fields, "learning_methods")),
        ],
        "Kegiatan Pembuka": [_value(fields, "opening_activities")],
        "Kegiatan Inti": [_value(fields, "main_activities")],
        "Kegiatan Penutup": [_value(fields, "closing_activities")],
        "Strategi Diferensiasi": [_value(fields, "differentiation_strategy")],
        "Asesmen": [
            _line("Jenis asesmen", _value(fields, "assessment_types")),
            _line("Teknik penilaian", _value(fields, "assessment_techniques")),
            _line("Instrumen penilaian", _value(fields, "assessment_instruments")),
        ],
        "Indikator Keberhasilan": [_value(fields, "success_indicators")],
        "Media Pembelajaran": [_value(fields, "learning_media")],
        "Sumber Belajar": [_value(fields, "learning_resources")],
        "Refleksi Guru": [_value(fields, "teacher_reflection_prompt")],
        "Refleksi Siswa": [_value(fields, "student_reflection_prompt")],
    }
    content = _sections_to_markdown(title, sections)
    return {"title": title, "content": content, "document_output": {"sections": sections}}


def generate_pjbl_document(fields: dict) -> dict:
    title = f"Dokumen PjBL - {_value(fields, 'project_topic')}"
    sections = {
        "Identitas Proyek": [_value(fields, "project_identity")],
        "Topik Proyek": [_value(fields, "project_topic")],
        "Tujuan Proyek": [_value(fields, "project_objectives")],
        "Pertanyaan Pemantik": [_value(fields, "driving_question")],
        "Produk Akhir": [_value(fields, "final_product")],
        "Langkah Kegiatan Proyek": [_value(fields, "project_steps")],
        "Jadwal Pelaksanaan": [_value(fields, "project_schedule")],
        "Pembagian Peran Siswa": [_value(fields, "student_roles")],
        "Asesmen Proyek": [_value(fields, "project_assessment")],
        "Rubrik Penilaian": [_value(fields, "rubric")],
        "Refleksi": [_value(fields, "reflection")],
    }
    content = _sections_to_markdown(title, sections)
    return {"title": title, "content": content, "document_output": {"sections": sections}}


def _sections_to_markdown(title: str, sections: dict[str, list[str]]) -> str:
    lines = [f"# {title}"]
    for heading, values in sections.items():
        lines.append(f"\n## {heading}")
        for value in values:
            text = str(value).strip()
            if text.startswith("- "):
                lines.append(text)
            else:
                lines.append(text)
    return "\n".join(lines)


def readable_missing_fields(missing_fields: list[str]) -> list[str]:
    return [field_label(field) for field in missing_fields]
