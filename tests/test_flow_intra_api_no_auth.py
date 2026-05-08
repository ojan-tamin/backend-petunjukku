"""End-to-end API test for Flow Intra with OpenRouter, bypassing register/login.

Run from project root:
    PYTHONPATH=. python scripts/test_flow_intra_api_no_auth.py

This uses FastAPI TestClient and overrides only get_current_user for this process.
It still exercises /sessions and /sessions/{id}/messages with the real OpenRouter-backed
FlowIntraAIService. Do not import this script in production.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from uuid import uuid4

# Use an isolated SQLite DB for this no-auth test so an old local DB schema cannot interfere.
TEST_DB_PATH = Path("dev_flow_intra_no_auth.sqlite3")
os.environ["DATABASE_URL"] = f"sqlite:///./{TEST_DB_PATH}"

from fastapi.testclient import TestClient

import app.models  # noqa: F401
from app.core import dependencies
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.user import User


def get_or_create_dev_user() -> User:
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "dev-flow-intra@example.com").first()
        if not user:
            user = User(
                id=uuid4(),
                full_name="Dev Guru Flow Intra",
                email="dev-flow-intra@example.com",
                hashed_password="dev-bypass-auth",
                school_name="Sekolah Dev",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user
    finally:
        db.close()


def main() -> int:
    dev_user = get_or_create_dev_user()

    def override_current_user():
        return dev_user

    app.dependency_overrides[dependencies.get_current_user] = override_current_user
    client = TestClient(app)

    print("=== Flow Intra API test: bypass auth dependency, no register/login ===")
    session_response = client.post(
        "/sessions",
        json={"title": "Uji Flow Intra OpenRouter", "document_type": "intrakurikuler"},
    )
    print("CREATE SESSION STATUS:", session_response.status_code)
    print(session_response.text[:1000])
    if session_response.status_code != 201:
        return 1

    session_id = session_response.json()["id"]
    messages = [
        "Saya mengajar jenjang SMP kelas 7, mata pelajaran IPA, topik ekosistem, durasi 2 JP. Siswa heterogen dan sekolah punya taman kecil untuk observasi.",
        "Tujuan pembelajaran: siswa dapat menjelaskan komponen biotik dan abiotik dalam ekosistem. Kompetensi yang diharapkan adalah menganalisis hubungan antar makhluk hidup dan lingkungan.",
        "Gunakan model problem based learning. Pembuka dengan apersepsi gambar ekosistem. Inti: diskusi kelompok dan observasi taman sekolah. Penutup: refleksi, kesimpulan, dan exit ticket. Metodenya diskusi, observasi, dan presentasi singkat.",
        "Asesmen formatif berupa observasi diskusi, kuis singkat, dan exit ticket. Indikator keberhasilan: siswa dapat membedakan komponen biotik-abiotik dan menjelaskan satu contoh rantai makanan. Media gambar ekosistem dan lembar kerja. Sumber belajar buku IPA kelas 7 dan lingkungan sekolah.",
        "Setuju, rancangan sudah sesuai. Lanjut generate dokumen.",
    ]

    for index, text in enumerate(messages, start=1):
        print("\n" + "=" * 72)
        print(f"SEND TURN {index}")
        response = client.post(f"/sessions/{session_id}/messages", json={"content": text})
        print("STATUS:", response.status_code)
        try:
            payload = response.json()
            print(json.dumps(payload, ensure_ascii=False, indent=2)[:3000])
        except Exception:
            print(response.text[:3000])
        if response.status_code != 201:
            return 2

    print("\nSUMMARY:")
    summary_response = client.get(f"/sessions/{session_id}/summary")
    print("STATUS:", summary_response.status_code)
    print(summary_response.text[:3000])

    print("\nGENERATE:")
    generate_response = client.post(f"/sessions/{session_id}/generate")
    print("STATUS:", generate_response.status_code)
    print(generate_response.text[:3000])

    return 0 if generate_response.status_code == 200 else 3


if __name__ == "__main__":
    raise SystemExit(main())
