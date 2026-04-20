# backend-petunjukku

`backend-petunjukku` is the rewritten FastAPI backend foundation for PetunjukKU. It is intentionally narrower than the old monorepo and limited to the concerns requested for this phase: application structure, configuration, database setup, migration readiness, YAML workflow contracts, and import-safe boundaries for future auth and session work.

## Scope of this phase

Included:

- FastAPI entry point in `app/main.py`
- centralized settings in `app/core/config.py`
- centralized database engine and session factory in `app/db/session.py`
- SQLAlchemy domain models for users, sessions, messages, planning state, documents, audio, and AI logs
- Alembic migration wiring and a baseline migration
- YAML AI workflow contracts for `intrakurikuler` and `pjbl`
- minimal auth and session route boundaries that are runnable now
- local LLM inspection and inference boundary under `app/routes/local_llm.py`

Deferred:

- production auth flow
- voice flow
- external AI provider integrations
- DirectML-ready ONNX Runtime GenAI model export for Gemma

## Project structure

```text
backend-petunjukku/
|-- alembic/
|   |-- env.py
|   |-- README
|   |-- script.py.mako
|   `-- versions/
|-- app/
|   |-- ai_contracts/
|   |-- core/
|   |-- db/
|   |-- models/
|   |-- routes/
|   |-- schemas/
|   |-- services/
|   |-- __init__.py
|   `-- main.py
|-- docs/
|-- .env.example
|-- .gitignore
|-- alembic.ini
|-- README.md
|-- requirements.txt
`-- test.py
```

## Setup

1. Create and activate a virtual environment.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2. Install dependencies.

```powershell
pip install -r requirements.txt
```

3. Create the local environment file.

```powershell
Copy-Item .env.example .env
```

The default configuration uses SQLite so the app can run immediately. For PostgreSQL, replace `DATABASE_URL` with a `postgresql+psycopg://...` DSN.

## Environment variables

Only variables used by the current implementation are included:

- `APP_NAME`
- `APP_ENV`
- `DEBUG`
- `API_V1_PREFIX`
- `DATABASE_URL`
- `SQL_ECHO`
- `CORS_ALLOW_ORIGINS`
- `LOCAL_LLM_ENABLED`
- `LOCAL_LLM_BACKEND`
- `LOCAL_LLM_PROVIDER`
- `LOCAL_LLM_MODEL_PATH`
- `LOCAL_LLM_DEVICE`
- `LOCAL_LLM_MAX_NEW_TOKENS`
- `LOCAL_LLM_TEMPERATURE`
- `LOCAL_LLM_TOP_P`

## Database and Alembic

Run the baseline migration:

```powershell
alembic upgrade head
```

Create a new migration after model changes:

```powershell
alembic revision --autogenerate -m "describe change"
```

Roll back one revision:

```powershell
alembic downgrade -1
```

## Running the app

```powershell
uvicorn app.main:app --reload
```

Useful endpoints:

- `GET /health`
- `GET /health/ready`
- `GET /api/v1/auth/health`
- `GET /api/v1/local-llm/status`
- `POST /api/v1/local-llm/chat`
- `GET /api/v1/studio-sessions/health`
- `GET /api/v1/studio-sessions/workflows`
- `GET /api/v1/studio-sessions/workflows/{workflow_type}`
- `POST /api/v1/studio-sessions/preview`
- `POST /api/v1/studio-sessions`
- `GET /api/v1/studio-sessions/{session_id}`
- `PATCH /api/v1/studio-sessions/{session_id}/planning-state`
- `POST /api/v1/studio-sessions/{session_id}/finalize`

## Local Gemma integration

The local LLM integration lives inside the existing backend structure:

- `app/core/config.py` centralizes all local runtime settings
- `app/core/dependencies.py` exposes `get_local_llm_service()`
- `app/services/local_llm_service.py` inspects the model path, chooses the runtime, and runs inference
- `app/routes/local_llm.py` exposes the status and chat endpoints
- `app/schemas/local_llm.py` defines the request and response contracts

### Runtime strategy used by this repo

The service always inspects the configured model path before it chooses a runtime:

- If the folder contains `genai_config.json` and compatible `.onnx` artifacts, the preferred path is `onnxruntime-genai` with `DirectML` when the matching DirectML package is installed.
- If the path points to a `.gguf` model, the service uses `llama-cpp-python` locally inside the FastAPI backend.
- If the folder contains Hugging Face `safetensors` weights, the service does not pretend DirectML is active. It falls back to a local `transformers` runtime with `optimum-quanto` int4 loading and disk offload.
- If a fallback runtime still cannot load the checkpoint, the API returns `load_success: false` and surfaces the actual load error instead of claiming GPU acceleration.

### Current local runtime in this project

This project environment now uses the requested local model in a quantized GGUF form that has been tested successfully:

- source model family: `gemma2-9b-cpt-sahabatai-v1-instruct`
- configured model path: `.local_llm_models/gemma2-9b-cpt-sahabatai-v1-instruct.Q4_K_M.gguf`
- runtime backend: `llama-cpp`
- provider: `cpu`
- `gpu_path_active`: `false`
- quantization: `Q4_K_M`
- tested result on this machine: the chat endpoint returns a real answer

### Original raw checkpoint audit

The original local checkpoint path that was inspected first was:

- `C:/Users/amrah/Documents/GitHub/gemma2-9b-cpt-sahabatai-v1-instruct`

Findings for the raw checkpoint:

- `genai_config.json` is not present
- `.onnx` model files are not present
- the folder contains sharded `safetensors`
- the checkpoint metadata reports about `18.48 GB` of model weights
- this is not DirectML-ready for ONNX Runtime GenAI in its current format
- on this `16 GB` Windows machine, loading it locally as raw `safetensors` is not safe

That original raw 9B checkpoint is still not runnable in this environment as-is. To make the requested model work end-to-end now, the project uses a local `GGUF` quantization of the same model family instead of the raw `safetensors` checkpoint.

### Configure the local model

Example PowerShell environment setup:

```powershell
$env:LOCAL_LLM_ENABLED = "true"
$env:LOCAL_LLM_BACKEND = "auto"
$env:LOCAL_LLM_PROVIDER = "auto"
$env:LOCAL_LLM_MODEL_PATH = "C:/Users/amrah/Documents/GitHub/backend-petunjukku/.local_llm_models/gemma2-9b-cpt-sahabatai-v1-instruct.Q4_K_M.gguf"
$env:LOCAL_LLM_DEVICE = "auto"
$env:LOCAL_LLM_MAX_NEW_TOKENS = "256"
$env:LOCAL_LLM_TEMPERATURE = "0.2"
$env:LOCAL_LLM_TOP_P = "0.9"
```

The tested install path for the Python runtime in this environment uses the Windows CPython 3.12 wheel from the official `abetlen/llama-cpp-python` releases. That dependency is already pinned in `requirements.txt` for this exact project environment.

### Download the working Gemma model

If the GGUF file is not already present, download the tested 9B quantized file into the project-local cache folder:

```powershell
@'
from huggingface_hub import hf_hub_download
from pathlib import Path

path = hf_hub_download(
    repo_id="gmonsoon/gemma2-9b-cpt-sahabatai-v1-instruct-GGUF",
    filename="gemma2-9b-cpt-sahabatai-v1-instruct.Q4_K_M.gguf",
    local_dir=str(Path(".local_llm_models").resolve()),
)
print(path)
'@ | .\.venv\Scripts\python -
```

### Test the integration

Inspect the resolved runtime without loading the model:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/local-llm/status"
```

Send a chat request:

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/local-llm/chat" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"message":"Jelaskan tujuan backend ini secara singkat.","system_prompt":"Jawab singkat."}'
```

Expected response shape:

```json
{
  "answer": "Saya adalah model bahasa yang dapat membantu menjawab pertanyaan dan memberikan informasi dalam bahasa Indonesia.",
  "backend": "llama-cpp",
  "provider": "cpu",
  "model_path": "C:/path/to/model",
  "device": "cpu",
  "gpu_path_active": false,
  "load_success": true,
  "model_format": "gguf",
  "fallback_required": true,
  "directml_viable": false,
  "load_error": null
}
```

### How to verify DirectML honestly

Use `GET /api/v1/local-llm/status` and inspect these fields:

- `directml_viable`: `true` only when the model path is an ONNX Runtime GenAI export with the expected artifacts
- `provider`: `directml` only when the service actually loaded a DirectML-capable ORT runtime
- `gpu_path_active`: `true` only when the active runtime confirms a GPU-backed execution path

If the current model is a GGUF file loaded through `llama-cpp-python`, the service should still report `directml_viable: false`, `provider: cpu`, and `gpu_path_active: false`.

### Fallback behavior

If DirectML is unavailable for the inspected model path, the backend keeps the same API contract and falls back to a local runtime:

- `llama-cpp` for GGUF
- `transformers` for Hugging Face `safetensors`

To make DirectML possible later, point `LOCAL_LLM_MODEL_PATH` to a real ONNX Runtime GenAI export that includes `genai_config.json` plus compatible ONNX artifacts, then install only the matching `onnxruntime-genai-directml` package in that environment.

## AI contracts

The current workflow contracts live in:

- `app/ai_contracts/stage_definitions.yaml`
- `app/ai_contracts/planning_state_example.yaml`

The session service reads these YAML files to validate workflows, expose stage metadata through the API, and derive the initial planning-state shape for future persisted sessions.

## Planning state and PJBL finalization

`PlanningState` stays hybrid by design:

- system fields remain real database columns: `workflow_type`, `current_stage`, `completion_score`, `is_ready_for_summary`, `is_ready_for_generation`, and `version`
- domain fields remain in `collected_fields` JSON
- `missing_fields` is recalculated from the YAML workflow contract on every planning update

The `pjbl` contract now supports these official field groups inside `collected_fields`:

- Stage 1: `education_level`, `phase`, `grade_level`, `subject_or_theme`, `topic`, `duration`, `school_context`, `student_characteristics`, `project_theme`
- Stage 2: `problem_context`, `project_objectives`, `target_competencies`, `character_values`, `six_c_elements`
- Stage 3: `project_title`, `driving_question`, `project_stages`, `grouping_strategy`, `student_roles`, `final_product`
- Stage 4: `assessment_focus`, `assessment_rubric`, `process_indicators`, `product_indicators`, `resources_needed`, `tools_materials`, `teacher_facilitation_plan`, `reflection_prompt`, `follow_up_plan`

The planning flow now works end-to-end:

1. `POST /api/v1/studio-sessions` creates a persisted `StudioSession` plus its initial `PlanningState`.
2. `PATCH /api/v1/studio-sessions/{session_id}/planning-state` merges new `collected_fields`, recalculates `missing_fields`, advances stage when ready, and updates readiness flags.
3. `POST /api/v1/studio-sessions/{session_id}/finalize` validates `is_ready_for_generation`, then writes a real `generated_documents` row linked to the session and user.

Example session creation:

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/studio-sessions" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"title":"PjBL Sampah Sekolah","workflow_type":"pjbl","user_email":"guru@local","user_display_name":"Guru Lokal"}'
```

Example planning update:

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/studio-sessions/<SESSION_ID>/planning-state" `
  -Method Patch `
  -ContentType "application/json" `
  -Body '{"collected_fields":{"education_level":"SMP","phase":"D","grade_level":"Kelas 8","subject_or_theme":"IPA","topic":"Sampah","duration":"4 minggu","school_context":"Sekolah urban","student_characteristics":["kolaboratif"],"project_theme":"Sekolah minim sampah"}}'
```

Example finalization:

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/studio-sessions/<SESSION_ID>/finalize" `
  -Method Post
```

The finalization response includes both the refreshed session and the newly created `generated_document`. For `pjbl`, the document kind is `project_plan`.

## Smoke verification

After running migrations:

```powershell
python test.py
```

The smoke script verifies:

- the FastAPI app imports cleanly
- database connectivity works
- the expected baseline tables exist
- workflow contracts load and validate
- the verification endpoints respond successfully
- the local LLM status endpoint responds with an inspection payload

## Migration documentation

- `docs/migration_audit.md`
- `docs/migration_notes.md`
