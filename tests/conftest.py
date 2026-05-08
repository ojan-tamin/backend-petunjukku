import os
import shutil
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_backend_petunjukku.sqlite3"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["DEBUG"] = "false"
os.environ["LLM_API_KEY"] = "test-openrouter-key"
os.environ["LLM_MODEL"] = "moonshotai/kimi-k2.5:nitro"

import app.models  # noqa: E402,F401
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.ai.dialogue_manager import build_assistant_message  # noqa: E402
from app.ai.document_generators import generate_intrakurikuler_document  # noqa: E402
from app.ai.interpreter import interpret_user_message  # noqa: E402
from app.ai.stage_manager import evaluate_state  # noqa: E402
from app.ai.summary import build_summary_text  # noqa: E402
from app.services.flow_intra_ai_service import FlowIntraTurnResult  # noqa: E402


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    upload_path = Path("uploads")
    if upload_path.exists():
        shutil.rmtree(upload_path)


@pytest.fixture
def client():
    return TestClient(app)


class FakeFlowIntraAIService:
    def __init__(self):
        self.turn_calls = 0
        self.summary_calls = 0
        self.document_calls = 0

    def process_turn(
        self,
        *,
        user_message,
        current_stage,
        collected_fields,
        missing_fields,
        chat_history=None,
    ):
        self.turn_calls += 1
        interpretation = interpret_user_message(
            workflow_type="intrakurikuler",
            current_stage=current_stage,
            current_fields=collected_fields or {},
            user_message=user_message,
        )
        evaluation = evaluate_state(
            workflow_type="intrakurikuler",
            current_stage=current_stage,
            fields=interpretation["collected_fields"],
            approved_summary=interpretation["approved_summary"],
            revision_requested=interpretation["revision_requested"],
        )
        assistant_message = build_assistant_message(
            workflow_type="intrakurikuler",
            current_stage=evaluation["next_stage"],
            updated_fields=interpretation["updated_fields"],
            collected_fields=interpretation["collected_fields"],
            missing_fields=evaluation["missing_fields"],
            completion_score=evaluation["completion_score"],
            is_ready_for_summary=evaluation["is_ready_for_summary"],
            is_ready_for_generation=evaluation["is_ready_for_generation"],
            approved_summary=interpretation["approved_summary"],
        )
        return FlowIntraTurnResult(
            updated_fields=interpretation["updated_fields"],
            collected_fields=interpretation["collected_fields"],
            missing_fields=evaluation["missing_fields"],
            current_stage=current_stage,
            next_stage=evaluation["next_stage"],
            completion_score=evaluation["completion_score"],
            is_ready_for_summary=evaluation["is_ready_for_summary"],
            is_ready_for_generation=evaluation["is_ready_for_generation"],
            assistant_message=assistant_message,
        )

    def generate_summary(self, *, collected_fields, missing_fields):
        self.summary_calls += 1
        return build_summary_text("intrakurikuler", collected_fields or {}, missing_fields or [])

    def generate_intrakurikuler_document(self, *, collected_fields):
        self.document_calls += 1
        return generate_intrakurikuler_document(collected_fields or {})


@pytest.fixture(autouse=True)
def mock_flow_intra_ai(monkeypatch):
    service = FakeFlowIntraAIService()
    monkeypatch.setattr(
        "app.services.message_service.get_flow_intra_ai_service",
        lambda: service,
    )
    return service
