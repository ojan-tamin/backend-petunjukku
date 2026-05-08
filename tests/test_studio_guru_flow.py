from __future__ import annotations

from app.ai.llm_client import LLMClient
from app.core.config import Settings
from app.services.flow_intra_ai_service import FlowIntraAIInvalidOutputError, FlowIntraAIService


def register_and_login(client, email: str = "guru@example.com") -> dict:
    register_response = client.post(
        "/auth/register",
        json={
            "full_name": "Guru Petunjukku",
            "email": email,
            "password": "secret123",
            "school_name": "SMP Nusantara",
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={"email": email, "password": "secret123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_session(client, headers: dict, document_type: str = "intrakurikuler") -> str:
    response = client.post(
        "/sessions",
        headers=headers,
        json={"title": "RPP IPA Kelas 7", "document_type": document_type},
    )
    assert response.status_code == 201
    return response.json()["id"]


def send_message(client, headers: dict, session_id: str, content: str) -> dict:
    response = client.post(
        f"/sessions/{session_id}/messages",
        headers=headers,
        json={"content": content},
    )
    assert response.status_code == 201
    return response.json()


def test_register_login_and_me(client):
    headers = register_and_login(client)
    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 200
    assert response.json()["email"] == "guru@example.com"


def test_intrakurikuler_chat_summary_generate_and_documents(client, mock_flow_intra_ai):
    headers = register_and_login(client)
    session_id = create_session(client, headers)

    first = send_message(
        client,
        headers,
        session_id,
        "Saya mengajar SMP kelas 7 mapel IPA topik ekosistem durasi 2 JP. Siswanya heterogen.",
    )
    assert first["current_stage"] == "stage_2"

    second = send_message(
        client,
        headers,
        session_id,
        "Tujuan pembelajaran siswa dapat menjelaskan komponen ekosistem. Kompetensi yang diharapkan mampu menganalisis hubungan makhluk hidup.",
    )
    assert second["current_stage"] == "stage_3"

    third = send_message(
        client,
        headers,
        session_id,
        "Model pembelajaran problem based learning. Kegiatan pembuka apersepsi gambar, kegiatan inti diskusi kelompok observasi, kegiatan penutup refleksi dan kesimpulan.",
    )
    assert third["current_stage"] == "stage_4"

    fourth = send_message(
        client,
        headers,
        session_id,
        "Asesmen formatif observasi dan kuis. Indikator keberhasilan siswa menjelaskan rantai makanan. Media pembelajaran gambar ekosistem. Sumber belajar buku IPA dan lingkungan sekolah.",
    )
    assert fourth["current_stage"] == "stage_5"
    assert fourth["is_ready_for_summary"] is True
    assert fourth["is_ready_for_generation"] is False

    blocked = client.post(f"/sessions/{session_id}/generate", headers=headers)
    assert blocked.status_code == 403

    summary_response = client.get(f"/sessions/{session_id}/summary", headers=headers)
    assert summary_response.status_code == 200
    assert "Konteks dasar pembelajaran" in summary_response.json()["summary"]

    approved = send_message(
        client,
        headers,
        session_id,
        "Setuju, sudah sesuai, lanjut generate dokumen.",
    )
    assert approved["is_ready_for_generation"] is True

    generated = client.post(f"/sessions/{session_id}/generate", headers=headers)
    assert generated.status_code == 200
    generated_payload = generated.json()
    assert generated_payload["document_type"] == "intrakurikuler"
    assert "Identitas Pembelajaran" in generated_payload["content"]

    documents = client.get("/documents", headers=headers)
    assert documents.status_code == 200
    assert len(documents.json()) == 1

    session_documents = client.get(f"/sessions/{session_id}/documents", headers=headers)
    assert session_documents.status_code == 200
    assert session_documents.json()[0]["title"] == generated_payload["title"]

    messages = client.get(f"/sessions/{session_id}/messages", headers=headers)
    assert messages.status_code == 200
    assert [message["role"] for message in messages.json()].count("user") == 5
    assert [message["role"] for message in messages.json()].count("assistant") == 5
    assert mock_flow_intra_ai.turn_calls == 5
    assert mock_flow_intra_ai.summary_calls == 0
    assert mock_flow_intra_ai.document_calls == 0


def test_llm_config_uses_project_a_openrouter_defaults(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setenv("ORCHESTRATION_CHAT_MODEL", "moonshotai/kimi-k2.5:nitro")
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    cfg = Settings()
    client = LLMClient(
        provider=cfg.llm_provider,
        model=cfg.llm_model,
        api_key=cfg.llm_api_key,
        base_url=cfg.llm_base_url,
    )

    assert cfg.llm_provider == "openrouter"
    assert cfg.llm_model == "moonshotai/kimi-k2.5:nitro"
    assert client.base_url == "https://openrouter.ai/api/v1"


class BrokenFlowIntraAIService:
    def process_turn(self, **_kwargs):
        raise FlowIntraAIInvalidOutputError("Invalid JSON from test LLM")


def test_invalid_llm_output_returns_clean_error_without_state_update(client, monkeypatch):
    headers = register_and_login(client, "broken-llm@example.com")
    session_id = create_session(client, headers)
    monkeypatch.setattr(
        "app.services.message_service.get_flow_intra_ai_service",
        lambda: BrokenFlowIntraAIService(),
    )

    response = client.post(
        f"/sessions/{session_id}/messages",
        headers=headers,
        json={"content": "Saya mengajar Matematika kelas 5 tentang pecahan selama 2 JP."},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "AI Flow Intra returned invalid structured output"

    detail = client.get(f"/sessions/{session_id}", headers=headers)
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["planning_state"]["current_stage"] == "stage_1"
    assert payload["planning_state"]["completion_score"] == 0
    assert payload["messages"] == []


class InvalidJSONLLMClient:
    def generate(self, *_args, **_kwargs):
        return "Saya akan bantu Bapak/Ibu, tetapi ini bukan JSON."


def test_flow_intra_falls_back_when_llm_returns_non_json():
    service = FlowIntraAIService(llm_client=InvalidJSONLLMClient())

    result = service.process_turn(
        user_message="Saya mengajar SMP kelas 7 mapel IPA topik ekosistem durasi 2 JP.",
        current_stage="stage_1",
        collected_fields={},
        missing_fields=[],
        chat_history=[],
    )

    assert result.next_stage == "stage_2"
    assert result.collected_fields["education_level"] == "SMP/MTs"
    assert result.collected_fields["grade_level"] == "Kelas 7"
    assert "Kelengkapan sementara" in result.assistant_message


class IrrelevantJSONLLMClient:
    def generate(self, *_args, **_kwargs):
        return '{"updated_fields": {}, "assistant_message": "bebas di luar format"}'


def test_flow_intra_asks_again_when_user_answer_is_irrelevant():
    service = FlowIntraAIService(llm_client=IrrelevantJSONLLMClient())

    result = service.process_turn(
        user_message="Saya kurang paham.",
        current_stage="stage_1",
        collected_fields={},
        missing_fields=["education_level", "grade_level", "subject_or_theme"],
        chat_history=[],
    )

    assert result.next_stage == "stage_1"
    assert result.collected_fields == {}
    assert "belum memuat informasi" in result.assistant_message
    assert "jenjang pendidikan" in result.assistant_message


def test_user_cannot_access_other_users_session(client):
    owner_headers = register_and_login(client, "owner@example.com")
    other_headers = register_and_login(client, "other@example.com")
    session_id = create_session(client, owner_headers)

    response = client.get(f"/sessions/{session_id}", headers=other_headers)
    assert response.status_code == 404

    message_response = client.post(
        f"/sessions/{session_id}/messages",
        headers=other_headers,
        json={"content": "Saya mencoba akses session orang lain."},
    )
    assert message_response.status_code == 404


def test_pjbl_document_generation(client):
    headers = register_and_login(client, "pjbl@example.com")
    session_id = create_session(client, headers, "pjbl")

    response = send_message(
        client,
        headers,
        session_id,
        "Identitas proyek kelas 8 IPS. Topik proyek pengelolaan sampah sekolah. "
        "Tujuan proyek siswa membuat solusi pemilahan sampah. "
        "Pertanyaan pemantik bagaimana sekolah mengurangi sampah plastik. "
        "Produk akhir kampanye dan tempat pilah sampah. "
        "Langkah kegiatan proyek observasi, riset, desain, presentasi. "
        "Jadwal 4 minggu. Peran siswa peneliti, desainer, presenter. "
        "Asesmen proyek portofolio dan presentasi. Rubrik penilaian kolaborasi dan dampak. "
        "Refleksi siswa menulis pembelajaran dan tindak lanjut.",
    )
    assert response["is_ready_for_summary"] is True
    assert response["is_ready_for_generation"] is False

    approved = send_message(client, headers, session_id, "Setuju, lanjut generate dokumen.")
    assert approved["is_ready_for_generation"] is True

    generated = client.post(f"/sessions/{session_id}/generate", headers=headers)
    assert generated.status_code == 200
    assert generated.json()["document_type"] == "pjbl"
    assert "Pertanyaan Pemantik" in generated.json()["content"]


def test_audio_upload_saves_metadata_and_processes_transcript(client):
    headers = register_and_login(client, "audio@example.com")
    session_id = create_session(client, headers)

    response = client.post(
        f"/sessions/{session_id}/audio",
        headers=headers,
        files={"file": ("voice.wav", b"fake audio", "audio/wav")},
        data={"transcript": "Saya mengajar SMP kelas 7 mapel IPA topik ekosistem durasi 2 JP."},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["audio_record"]["transcription_status"] == "success"
    assert payload["chat_response"]["session_id"] == session_id
