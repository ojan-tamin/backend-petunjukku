"""Minimal runtime smoke verification for the backend foundation."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from app.main import app
from app.db.session import database_healthcheck, get_engine
from app.services.local_llm_service import LocalLLMService
from app.services.session_service import list_workflow_summaries, load_stage_definitions

EXPECTED_TABLES = {
    "users",
    "studio_sessions",
    "planning_states",
    "studio_messages",
    "generated_documents",
    "audio_records",
    "ai_logs",
}
EXPECTED_ROUTES = {
    "/",
    "/health",
    "/health/ready",
    "/api/v1/auth/health",
    "/api/v1/local-llm/status",
    "/api/v1/local-llm/chat",
    "/api/v1/studio-sessions/health",
    "/api/v1/studio-sessions/workflows",
    "/api/v1/studio-sessions/workflows/{workflow_type}",
    "/api/v1/studio-sessions/preview",
    "/api/v1/studio-sessions",
    "/api/v1/studio-sessions/{session_id}",
    "/api/v1/studio-sessions/{session_id}/planning-state",
    "/api/v1/studio-sessions/{session_id}/finalize",
}

PJBL_STAGE_1_FIELDS = {
    "education_level": "SMP",
    "phase": "D",
    "grade_level": "Kelas 8",
    "subject_or_theme": "IPA Terpadu",
    "topic": "Pengelolaan Sampah Sekolah",
    "duration": "4 minggu",
    "school_context": "Sekolah memiliki bank sampah sederhana dan area kantin aktif.",
    "student_characteristics": [
        "Siswa terbiasa kerja kelompok",
        "Perlu penguatan observasi lapangan",
    ],
    "project_theme": "Sekolah minim sampah",
}
PJBL_STAGE_2_FIELDS = {
    "problem_context": "Volume sampah plastik di area kantin meningkat setiap minggu.",
    "project_objectives": [
        "Menganalisis sumber sampah utama",
        "Merancang solusi pengurangan sampah plastik",
    ],
    "target_competencies": [
        "Bernalar kritis",
        "Kolaborasi",
        "Komunikasi ilmiah",
    ],
    "character_values": ["Gotong royong", "Tanggung jawab"],
    "six_c_elements": [
        "Critical thinking",
        "Collaboration",
        "Citizenship",
    ],
}
PJBL_STAGE_3_FIELDS = {
    "project_title": "Sekolah Minim Sampah Plastik",
    "driving_question": "Bagaimana siswa dapat menurunkan sampah plastik kantin secara terukur?",
    "project_stages": [
        "Observasi kondisi awal",
        "Analisis data sampah",
        "Desain kampanye dan prototipe solusi",
        "Presentasi hasil",
    ],
    "grouping_strategy": "Kelompok 4-5 siswa dengan peran campuran.",
    "student_roles": [
        "Ketua tim",
        "Pencatat data",
        "Desainer kampanye",
        "Presenter",
    ],
    "final_product": "Proposal aksi sekolah dan media kampanye pengurangan sampah.",
}
PJBL_STAGE_4_FIELDS = {
    "assessment_focus": [
        "Kualitas analisis data",
        "Kualitas solusi",
        "Kolaborasi tim",
    ],
    "assessment_rubric": {
        "analisis": "Akurat, berbasis data, dan relevan dengan konteks sekolah",
        "solusi": "Realistis, kreatif, dan dapat diterapkan",
    },
    "process_indicators": [
        "Mampu mengumpulkan data lapangan",
        "Mampu membagi tugas secara adil",
    ],
    "product_indicators": [
        "Proposal memuat langkah aksi yang jelas",
        "Media kampanye mudah dipahami",
    ],
    "resources_needed": [
        "Data observasi",
        "Akses area kantin",
        "Contoh media kampanye",
    ],
    "tools_materials": [
        "Timbangan sederhana",
        "Spreadsheet",
        "Canva",
    ],
    "teacher_facilitation_plan": "Guru memfasilitasi observasi, validasi ide, dan refleksi mingguan.",
    "reflection_prompt": "Apa perubahan kebiasaan yang paling realistis untuk diterapkan di sekolah?",
    "follow_up_plan": "Hasil proyek dibawa ke rapat OSIS dan dipantau selama 1 bulan.",
}


def main() -> int:
    if not database_healthcheck():
        raise SystemExit("Database connectivity failed.")

    engine = get_engine()
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    missing_tables = EXPECTED_TABLES - tables
    if missing_tables:
        raise SystemExit(f"Missing expected tables: {sorted(missing_tables)}")

    definitions = load_stage_definitions()
    summaries = list_workflow_summaries()
    route_paths = {route.path for route in app.routes}
    missing_routes = EXPECTED_ROUTES - route_paths
    if missing_routes:
        raise SystemExit(f"Missing expected routes: {sorted(missing_routes)}")

    client = TestClient(app)
    local_llm_status_response = client.get("/api/v1/local-llm/status")
    if local_llm_status_response.status_code != 200:
        raise SystemExit(
            f"Local LLM status endpoint failed: {local_llm_status_response.status_code}"
        )
    local_llm_status_payload = local_llm_status_response.json()
    required_status_fields = {
        "status",
        "enabled",
        "backend",
        "provider",
        "model_path",
        "device",
        "gpu_path_active",
        "load_success",
        "model_format",
        "directml_viable",
        "fallback_required",
    }
    missing_status_fields = required_status_fields - set(local_llm_status_payload)
    if missing_status_fields:
        raise SystemExit(
            f"Local LLM status payload is missing fields: {sorted(missing_status_fields)}"
        )

    if local_llm_status_payload["backend"] == "llama-cpp":
        local_llm_chat_response = client.post(
            "/api/v1/local-llm/chat",
            json={
                "message": "Halo, jawab singkat dalam bahasa Indonesia.",
                "system_prompt": "Jawab dalam satu kalimat.",
            },
        )
        if local_llm_chat_response.status_code != 200:
            raise SystemExit(
                f"Local LLM chat endpoint failed: {local_llm_chat_response.status_code}"
            )
        local_llm_chat_payload = local_llm_chat_response.json()
        if not local_llm_chat_payload.get("load_success"):
            raise SystemExit(
                f"Local LLM chat did not load successfully: {local_llm_chat_payload.get('load_error')}"
            )
        if not str(local_llm_chat_payload.get("answer") or "").strip():
            raise SystemExit("Local LLM chat returned an empty answer.")

    create_session_response = client.post(
        "/api/v1/studio-sessions",
        json={
            "title": "PjBL Sampah Sekolah",
            "workflow_type": "pjbl",
            "user_email": "smoke.teacher@local",
            "user_display_name": "Smoke Teacher",
        },
    )
    if create_session_response.status_code != 200:
        raise SystemExit(
            f"Studio session creation failed: {create_session_response.status_code} {create_session_response.text}"
        )
    created_session = create_session_response.json()
    session_id = created_session["id"]

    stage_1_response = client.patch(
        f"/api/v1/studio-sessions/{session_id}/planning-state",
        json={"collected_fields": PJBL_STAGE_1_FIELDS},
    )
    if stage_1_response.status_code != 200:
        raise SystemExit(
            f"PJBL stage 1 update failed: {stage_1_response.status_code} {stage_1_response.text}"
        )
    stage_1_payload = stage_1_response.json()
    if stage_1_payload["planning_state"]["current_stage"] != "pjbl_objective_alignment":
        raise SystemExit("PJBL stage progression did not advance to stage 2.")

    stage_2_response = client.patch(
        f"/api/v1/studio-sessions/{session_id}/planning-state",
        json={"collected_fields": PJBL_STAGE_2_FIELDS},
    )
    if stage_2_response.status_code != 200:
        raise SystemExit(
            f"PJBL stage 2 update failed: {stage_2_response.status_code} {stage_2_response.text}"
        )
    stage_2_payload = stage_2_response.json()
    if stage_2_payload["planning_state"]["current_stage"] != "pjbl_project_design":
        raise SystemExit("PJBL stage progression did not advance to stage 3.")

    stage_3_response = client.patch(
        f"/api/v1/studio-sessions/{session_id}/planning-state",
        json={"collected_fields": PJBL_STAGE_3_FIELDS},
    )
    if stage_3_response.status_code != 200:
        raise SystemExit(
            f"PJBL stage 3 update failed: {stage_3_response.status_code} {stage_3_response.text}"
        )
    stage_3_payload = stage_3_response.json()
    if stage_3_payload["planning_state"]["current_stage"] != "pjbl_assessment_and_support":
        raise SystemExit("PJBL stage progression did not advance to stage 4.")
    if not stage_3_payload["planning_state"]["is_ready_for_summary"]:
        raise SystemExit("PJBL summary readiness should be true after stage 3.")
    if stage_3_payload["planning_state"]["is_ready_for_generation"]:
        raise SystemExit("PJBL generation readiness should still be false before stage 4.")

    stage_4_response = client.patch(
        f"/api/v1/studio-sessions/{session_id}/planning-state",
        json={"collected_fields": PJBL_STAGE_4_FIELDS},
    )
    if stage_4_response.status_code != 200:
        raise SystemExit(
            f"PJBL stage 4 update failed: {stage_4_response.status_code} {stage_4_response.text}"
        )
    stage_4_payload = stage_4_response.json()
    planning_state = stage_4_payload["planning_state"]
    if planning_state["current_stage"] != "pjbl_finalization":
        raise SystemExit("PJBL stage progression did not advance to finalization.")
    if not planning_state["is_ready_for_generation"]:
        raise SystemExit("PJBL generation readiness should be true after stage 4.")
    if planning_state["completion_score"] != 100:
        raise SystemExit("PJBL completion score should reach 100 after all required fields are filled.")

    finalize_response = client.post(f"/api/v1/studio-sessions/{session_id}/finalize")
    if finalize_response.status_code != 200:
        raise SystemExit(
            f"Studio session finalization failed: {finalize_response.status_code} {finalize_response.text}"
        )
    finalization_payload = finalize_response.json()
    generated_document = finalization_payload["generated_document"]
    if generated_document["kind"] != "project_plan":
        raise SystemExit("Finalization should create a project_plan generated document for PJBL.")
    if generated_document["generated_from_state_version"] != planning_state["version"]:
        raise SystemExit("Generated document should capture the planning state version used for finalization.")
    if not finalization_payload["session"]["generated_documents"]:
        raise SystemExit("Finalized session should include at least one generated document.")

    local_llm_service = LocalLLMService()
    local_llm_inspection = local_llm_service.get_status()

    print(f"App title: {app.title}")
    print(f"Workflow contract version: {definitions.get('version')}")
    print(f"Loaded workflows: {[summary['workflow_type'].value for summary in summaries]}")
    print(f"Discovered tables: {sorted(tables)}")
    print(f"Discovered routes: {sorted(route_paths)}")
    print(
        "Local LLM runtime: "
        f"backend={local_llm_inspection['backend']}, "
        f"provider={local_llm_inspection['provider']}, "
        f"format={local_llm_inspection['model_format']}, "
        f"directml_viable={local_llm_inspection['directml_viable']}"
    )
    print(
        "PJBL finalization smoke: "
        f"session_id={session_id}, "
        f"current_stage={planning_state['current_stage']}, "
        f"generated_document_version={generated_document['version']}"
    )
    print("Smoke check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
