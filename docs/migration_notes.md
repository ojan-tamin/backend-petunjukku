# 1. Why the new structure was chosen

The new repository follows the requested FastAPI-centered layout because it creates clean ownership boundaries without introducing unnecessary abstraction:

- `app/main.py` only assembles the application
- `app/core/` owns configuration, dependency helpers, and security utilities
- `app/db/` owns the SQLAlchemy base and session lifecycle
- `app/models/` keeps one model per file and preserves future domain growth
- `app/routes/` contains HTTP transport concerns only
- `app/services/` contains workflow and auth boundary logic
- `app/ai_contracts/` stores editable workflow definitions outside Python code

This structure is close to the target repository shape and directly addresses the old repository's sprawl.

# 2. Dependencies retained

Dependencies retained because they are necessary for the current foundation:

- `fastapi`
- `uvicorn`
- `SQLAlchemy`
- `alembic`
- `pydantic-settings`
- `psycopg`

These are the minimum libraries required to run the API, configure the app, manage the schema, and stay ready for PostgreSQL.

# 3. Dependencies removed

Dependencies removed because they belong to later feature phases or to the old repository's broader runtime:

- `google-genai`
- `google-cloud-firestore`
- `httpx`
- `PyMuPDF`
- `sse-starlette`
- `python-docx`
- `weasyprint`
- `markdown`
- `neo4j`
- `chromadb`
- `redis`
- `apscheduler`
- the intermediate local-LLM stack previously drafted in this new repository: `python-jose`, `transformers`, `accelerate`, `sentencepiece`, `torch`

Removing these keeps the foundation narrow and avoids locking the new repository to speculative runtime choices.

# 4. Dependencies added

Dependencies added or kept explicit for the rewritten foundation:

- `PyYAML` so workflow contracts are executable runtime artifacts
- `python-dotenv` so `.env` loading works consistently with `pydantic-settings`

No dedicated auth library was added because full auth implementation is intentionally deferred in this phase.

# 5. Why YAML was chosen for AI contracts

YAML was chosen because it is readable, diff-friendly, and explicit enough to describe workflow stages, required fields, and transitions without embedding the contract in Python code. It also fits the future use cases called out in the task: interpreting user input, checking field completeness, choosing the next question, and deciding the next stage transition.

In the rewritten foundation the YAML contract is operational, not decorative. The session service loads and validates it at runtime.

# 6. Old repository design problems

The old repository had several structural problems:

- backend, frontend, deployment, and generated assets lived in one operational root
- application entrypoint ownership had drifted
- route and service modules had become monolithic
- multiple persistence strategies coexisted in the same feature surface
- settings had grown into a large registry of feature flags and operator flags
- duplicate suffixed files showed repository churn and unclear ownership

These issues made the old backend unsuitable as a clean starting foundation.

# 7. New repository design decisions

Key decisions in the new repository:

- keep FastAPI and SQLAlchemy, but narrow the repo to backend-foundation responsibilities
- default to SQLite for immediate runnability while remaining PostgreSQL-ready through SQLAlchemy and Alembic
- keep the user, session, message, planning-state, document, audio, and AI-log model boundaries because they match the future scope
- make auth an import-safe deferred boundary instead of prematurely implementing business flow
- make the session layer read-only and contract-driven for now: health, workflow summaries, workflow detail, and session preview
- keep one baseline Alembic revision aligned with the rewritten metadata

This keeps the repository substantially aligned with the requested structure while leaving clear extension points for later work.

# 8. Intentionally deferred work

The following work is intentionally deferred:

- production auth flow and identity provider integration
- access and refresh token issuance
- persisted session creation and lifecycle APIs
- message persistence flow
- planning engine state mutation logic
- document generation and export logic
- voice ingestion and transcription flow
- external AI provider integration
- background jobs or queue infrastructure

The repository is prepared for these additions, but they are not implemented in this foundation phase.
