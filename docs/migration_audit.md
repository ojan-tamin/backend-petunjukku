# 1. Overview of old architecture

The old `PetunjukKU` repository is a working but highly mixed monorepo. At the top level it combines backend code, a full frontend, deployment assets, scripts, data folders, generated artifacts, documentation, and environment-specific operational helpers. The backend code under `app/` is itself split between API routers, orchestration services, persistence helpers, prompt assets, and several experimental or duplicated modules.

Top-level folders observed during audit:

- `.agent`, `.cursor`, `.github`, `.pip-cache`, `.playwright-cli`, `.tmp`, `.venv`
- `alembic`, `app`, `assets`, `config`, `data`, `deploy`, `docs`, `frontend`, `logs`, `miscelaneous`, `presentations`, `public`, `scripts`, `tests`

Backend entry and routing observations:

- FastAPI routers are assembled in `app/api/v1/router.py`
- health and feature endpoints live across `app/api/v1/endpoints/*`
- deployment scripts still reference `uvicorn app.main:app`
- `app/main.py` is not present in the audited tree, which indicates entrypoint drift

Architecture characteristics:

- the route layer is broad and feature-heavy
- orchestration, persistence, and AI logic are tightly coupled
- Studio-related behavior is spread across `app/services/studio/*`, `app/services/orchestration/*`, `app/services/kina_chat/*`, and multiple API endpoint modules
- the repository contains duplicate suffixed files such as `router 2.py`, `router 3.py`, `router 4.py`, `memory 2.py`, and `school 2.py`

The old repository is useful as a source of domain boundaries, but not as a backend foundation to continue directly.

# 2. Important dependencies found

Important dependencies from `pyproject.toml` and the audited runtime code:

- `fastapi`, `uvicorn[standard]`
- `pydantic`, `pydantic-settings`
- `sqlalchemy`, `psycopg[binary]`, `alembic`
- `httpx`
- `google-genai`
- `google-cloud-firestore`
- `PyMuPDF`
- `sse-starlette`
- `python-docx`, `weasyprint`, `markdown`
- `neo4j`, `chromadb`, `redis`
- `apscheduler`

This dependency profile shows the old backend had already grown into a multi-system runtime with AI, document generation, streaming, memory systems, and several persistence mechanisms.

# 3. Environment variables found

The old repository has an oversized environment surface. `app/core/config.py` defines a very large settings object, `.env.example` adds many operational toggles, and a few modules still read environment variables directly with `os.getenv`.

Core/runtime variables:

- `ENV`
- `APP_NAME`
- `ALLOWED_ORIGINS`
- `ALLOW_LOCALHOST_ORIGINS`
- `TRUSTED_HOSTS`
- `ENABLE_API_DOCS`
- `ENABLE_TEST_ENDPOINTS`

AI/provider variables:

- `OPENROUTER_API_KEY`
- `OPENROUTER_BASE_URL`
- `OPENROUTER_MODEL`
- `OPENROUTER_HTTP_REFERER`
- `GEMINI_API_KEY`
- `GEMINI_MODEL_ID`
- `GOOGLE_MAPS_API_KEY`

Persistence and database variables:

- `DATABASE_URL`
- `DB_TUNNEL_LOCAL_PORT`
- `DATABASE_POOL_SIZE`
- `DATABASE_MAX_OVERFLOW`
- `DATABASE_POOL_TIMEOUT_SECONDS`
- `DATABASE_CONNECT_TIMEOUT_SECONDS`
- `DATABASE_ECHO`
- `STUDIO_PERSISTENCE_BACKEND`
- `STUDIO_VOICE_SESSION_ALLOW_MEMORY`
- `STUDIO_VOICE_REQUIRE_REDIS_FOR_POSTGRES`
- direct lookup: `DATABASE_PREFER_IPV4`

Firebase/auth variables:

- `FIREBASE_PROJECT_ID`
- `FIREBASE_API_KEY`
- `FIREBASE_AUTH_DOMAIN`
- `FIREBASE_STORAGE_BUCKET`
- `FIREBASE_SERVICE_ACCOUNT_JSON`
- `FIREBASE_SERVICE_ACCOUNT_FILE`
- `AUTH_ENFORCEMENT_MODE`
- `AUTH_ENFORCEMENT_DATE`
- `ALLOW_LEGACY_USER_ID_FALLBACK`

Memory and collaboration variables:

- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`
- `CHROMA_HOST`
- `CHROMA_PORT`
- `REDIS_URL`
- `STEP2_COLLAB_REDIS_URL`

The main problem is not that the variables exist individually. It is that provider tuning, tunnel operations, feature flags, memory topology, auth rollout, and local developer behavior are all mixed into one configuration surface.

# 4. Database layer summary

The old database layer is centered on:

- `app/db/base.py`
- `app/db/session.py`
- `app/db/models/studio.py`
- `app/services/orchestration/postgres_store.py`
- Alembic revisions under `alembic/versions/`

What is worth preserving:

- SQLAlchemy is used as the relational foundation
- the `studio.py` models establish meaningful domain boundaries for user profiles, projects, threads, and messages
- the session helper supports both SQLite and PostgreSQL-style usage patterns

What is problematic:

- the relational layer is only one persistence option among Firestore, Redis, and in-memory paths
- `alembic/env.py` imports `app.core.settings.get_settings`, but the active settings file in the repository is `app/core/config.py`
- database behavior is mixed with Tencent tunnel and operator-specific local development concerns
- API logic and persistence strategy are still entangled at the feature layer

# 5. AI-related module summary

AI-related logic is spread across several clusters:

- `app/services/llm/*` for provider access
- `app/services/kina_chat/*` for KINA chat orchestration and tools
- `app/services/kina_runtime/*` for continuity, memory, and observability helpers
- `app/services/studio/*` for Studio behavior and PJBL-specific flows
- `app/services/pjbl_step1d/*` and `app/services/step5/*` for document generation and export
- `app/services/voice/*` plus voice endpoints for realtime and websocket flows
- prompt assets under `app/prompts/` and `app/core/prompts/`

Logic worth preserving conceptually:

- explicit workflow and stage semantics for `intrakurikuler` and `pjbl`
- clear separation between planning state and final document generation
- the need for durable session, message, and AI log persistence

Logic worth rewriting:

- provider-specific orchestration
- voice and websocket lifecycle code
- prompt-heavy behavior embedded in service modules
- mixed AI/tool/runtime coupling in the same feature surface

# 6. Keep / Refactor / Rewrite / Discard decisions

Keep:

- FastAPI as the backend framework
- SQLAlchemy and Alembic as the persistence foundation
- the domain boundaries of users, sessions, messages, planning state, generated documents, audio records, and AI logs
- the stage-oriented planning idea for `intrakurikuler` and `pjbl`

Refactor:

- configuration into a much smaller centralized settings object
- route composition into a narrow backend-only surface
- session initialization into a YAML contract-driven service
- the database layer into one clear engine and session center

Rewrite:

- the application entry point
- route structure for the new repository
- auth into an import-safe deferred boundary
- migration wiring so Alembic and runtime settings point to the same metadata

Discard:

- mixed default persistence behavior across Firestore, Redis, in-memory stores, and PostgreSQL
- old duplicate modules with numeric suffixes
- tunnel-heavy operator flags as part of the default runtime contract
- experimental service branches that are not required for the new foundation

# 7. Technical debt and anti-patterns

Technical debt and anti-patterns observed in the old repository:

- missing `app/main.py` despite deployment references to `uvicorn app.main:app`
- duplicate files with suffixes such as `router 2.py` and `memory 3.py`
- monolithic service sprawl across orchestration, Studio, KINA chat, memory, and voice features
- a single oversized settings object that mixes product flags, infra flags, provider tuning, and deployment behavior
- Alembic and runtime settings drift
- placeholder dependency code in `app/api/deps.py`
- repository shape that mixes frontend, backend, deployment, and generated assets in one foundation

These issues are structural enough that a clean rewrite is justified. The old repository is valuable as an audit source, not as the architecture to preserve.
