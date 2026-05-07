from __future__ import annotations

import json
from typing import Any

from app.ai.workflow import (
    FIELD_LABELS,
    INTRAKURIKULER_OPTIONAL_FIELDS,
    INTRAKURIKULER_REQUIRED_FIELDS,
    STAGE_LABELS,
)


FLOW_INTRA_SYSTEM_PROMPT = """
Kamu adalah asisten guru untuk Flow Intrakurikuler Studio Guru.
Tugasmu membantu Bapak/Ibu guru menyusun rancangan pembelajaran intrakurikuler secara bertahap.

Aturan utama:
- Balas hanya dengan JSON valid, tanpa markdown, tanpa teks pembuka, tanpa blok kode.
- JSON harus persis memakai key pada Format JSON wajib. Jangan menambah key lain.
- Bahasa assistant_message harus bahasa Indonesia natural dan menggunakan sapaan Bapak/Ibu.
- updated_fields hanya memuat informasi yang benar-benar disebutkan atau dikoreksi user.
- Jika user menjawab tidak relevan, kosongkan updated_fields dan isi assistant_message dengan pertanyaan ulang yang spesifik.
- Jangan menghapus field lama kecuali user eksplisit meminta revisi/koreksi/penggantian.
- Jangan bertanya ulang informasi yang sudah ada pada collected_fields.
- Tanyakan maksimal 1 sampai 3 hal dalam satu pesan.
- Jangan menghasilkan dokumen final sebelum user menyetujui ringkasan.
- Jika user menyetujui ringkasan, set is_ready_for_generation true.
- Jika user meminta revisi besar, update field terkait dan set is_ready_for_generation false.

Format JSON wajib:
{
  "updated_fields": {},
  "missing_fields": [],
  "current_stage": "stage_1",
  "next_stage": "stage_1",
  "completion_score": 0,
  "is_ready_for_summary": false,
  "is_ready_for_generation": false,
  "assistant_message": ""
}
""".strip()


SUMMARY_SYSTEM_PROMPT = """
Kamu adalah asisten guru yang merangkum rancangan pembelajaran intrakurikuler.
Gunakan hanya data yang tersedia. Jangan mengarang data kosong.
Tulis ringkasan dalam bahasa Indonesia yang rapi dan minta konfirmasi sebelum dokumen final dibuat.
""".strip()


DOCUMENT_SYSTEM_PROMPT = """
Kamu adalah penyusun dokumen intrakurikuler untuk guru.
Buat dokumen final lengkap dalam markdown berdasarkan data planning_state yang diberikan.
Jangan mengarang informasi yang tidak ada; jika data opsional kosong, tulis seperlunya sebagai catatan adaptasi.
""".strip()


def build_flow_intra_messages(
    *,
    user_message: str,
    current_stage: str,
    collected_fields: dict[str, Any],
    missing_fields: list[str],
    chat_history: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    context = {
        "workflow_type": "intrakurikuler",
        "current_stage": current_stage,
        "stage_labels": STAGE_LABELS,
        "required_fields_by_stage": INTRAKURIKULER_REQUIRED_FIELDS,
        "optional_fields_by_stage": INTRAKURIKULER_OPTIONAL_FIELDS,
        "field_labels": FIELD_LABELS,
        "collected_fields": collected_fields or {},
        "missing_fields": missing_fields or [],
        "chat_history_tail": (chat_history or [])[-10:],
        "stage_progression_policy": [
            "Stage tidak naik jika field wajib stage saat ini masih kosong.",
            "Stage 5 hanya aktif setelah stage 1 sampai 4 cukup lengkap.",
            "Generate dokumen hanya setelah ringkasan disetujui user.",
        ],
    }
    return [
        {"role": "system", "content": FLOW_INTRA_SYSTEM_PROMPT},
        {"role": "system", "content": json.dumps(context, ensure_ascii=False)},
        {"role": "user", "content": user_message},
    ]


def build_summary_messages(*, collected_fields: dict[str, Any], missing_fields: list[str]) -> list[dict[str, str]]:
    payload = {
        "collected_fields": collected_fields or {},
        "missing_fields": missing_fields or [],
        "required_sections": [
            "Konteks dasar pembelajaran",
            "Tujuan pembelajaran",
            "Rancangan kegiatan pembelajaran",
            "Asesmen dan unsur pendukung",
            "Catatan yang masih kurang",
            "Konfirmasi sebelum generate",
        ],
    }
    return [
        {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


def build_document_messages(*, collected_fields: dict[str, Any]) -> list[dict[str, str]]:
    payload = {
        "collected_fields": collected_fields or {},
        "required_document_sections": [
            "Identitas Pembelajaran",
            "Konteks dan Karakteristik Siswa",
            "Tujuan Pembelajaran",
            "Kompetensi/Capaian yang Diharapkan",
            "Pendekatan, Model, dan Metode Pembelajaran",
            "Kegiatan Pembuka",
            "Kegiatan Inti",
            "Kegiatan Penutup",
            "Strategi Diferensiasi",
            "Asesmen",
            "Indikator Keberhasilan",
            "Media Pembelajaran",
            "Sumber Belajar",
            "Refleksi Guru",
            "Refleksi Siswa",
        ],
    }
    return [
        {"role": "system", "content": DOCUMENT_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
