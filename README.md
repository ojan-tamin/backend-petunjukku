# Petunjukku Backend

Backend API untuk aplikasi Petunjukku yang dibangun dengan FastAPI, SQLAlchemy, PostgreSQL, dan Alembic.

Dokumentasi ini menjelaskan gambaran codebase, struktur folder, alur request, model data, endpoint yang tersedia, dan cara menjalankan proyek.

## Ringkasan

Project ini adalah backend untuk workflow penyusunan dokumen pembelajaran. Saat ini fondasi utama yang sudah aktif adalah:

- autentikasi user dengan JWT
- pembuatan akun dan login
- pembuatan dan pengambilan studio session
- inisialisasi planning state berdasarkan tipe dokumen

Selain itu, codebase juga sudah menyiapkan model untuk:

- pesan percakapan studio
- hasil dokumen yang digenerate
- rekaman audio dan transkripsi
- log interaksi AI

Artinya, arsitektur domain sudah disiapkan untuk fitur yang lebih besar, walaupun route yang aktif masih fokus di auth dan session.

## Stack Teknologi

- FastAPI untuk HTTP API
- SQLAlchemy 2.x untuk ORM
- PostgreSQL sebagai database utama
- Alembic untuk migrasi schema
- Pydantic Settings untuk konfigurasi environment
- `python-jose` untuk JWT
- `passlib` dengan bcrypt untuk hashing password

## Struktur Folder

```text
.
├── alembic/              # konfigurasi dan file migrasi database
├── app/
│   ├── core/             # config, security, dependency injection
│   ├── db/               # SQLAlchemy base dan session
│   ├── models/           # model ORM / tabel database
│   ├── routes/           # endpoint FastAPI
│   ├── schemas/          # schema request dan response
│   ├── services/         # business logic
│   └── main.py           # entry point aplikasi
├── .env                  # environment variables lokal
├── requirements.txt      # dependency Python
└── test.py               # helper kecil untuk cek metadata model
```

## Arsitektur Singkat

Pola codebase mengikuti pembagian tanggung jawab yang cukup bersih:

- `routes` menangani HTTP request/response
- `schemas` memvalidasi payload input dan output
- `services` menyimpan business logic
- `models` merepresentasikan tabel dan relasi database
- `core` menyimpan konfigurasi, auth, dan dependencies
- `db` menyimpan inisialisasi base dan session SQLAlchemy

Alur umumnya:

1. Request masuk ke route FastAPI.
2. FastAPI memvalidasi body/query lewat schema Pydantic.
3. Route memanggil service.
4. Service membaca/menulis data lewat SQLAlchemy session.
5. Response dikembalikan memakai schema response.

## Entry Point Aplikasi

File utama aplikasi ada di `app/main.py`.

Tanggung jawabnya:

- membuat instance FastAPI
- memasang router `auth` dan `studio_sessions`
- menyediakan endpoint health check

Endpoint dasar yang tersedia dari file ini:

- `GET /`
- `GET /health`
- `GET /health/db`

## Konfigurasi Environment

Konfigurasi dibaca dari `.env` melalui `app/core/config.py`.

Variabel yang dipakai saat ini:

- `APP_NAME`
- `APP_ENV`
- `DEBUG`
- `DATABASE_URL`
- `SECRET_KEY`
- `ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`

Contoh `.env` lokal:

```env
APP_NAME=Petunjukku Backend
APP_ENV=development
DEBUG=true
DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/petunjukku_db
SECRET_KEY=change-this-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

## Database Layer

### SQLAlchemy Base

`app/db/base.py` mendefinisikan `Base` sebagai parent untuk semua model ORM.

### Session dan Engine

`app/db/session.py` membuat:

- `engine` dari `settings.database_url`
- `SessionLocal` untuk dipakai pada setiap request

### Dependency Database

`app/core/dependencies.py` menyediakan `get_db()` yang:

- membuka database session saat request dimulai
- menutup session setelah request selesai

## Authentication

Sistem auth memakai JWT bearer token.

Komponen utamanya:

- `app/core/security.py`
- `app/core/dependencies.py`
- `app/routes/auth.py`
- `app/services/auth_service.py`

### Cara Kerja

#### Register

1. Client mengirim data user ke `POST /auth/register`.
2. Route mengecek apakah email sudah terdaftar.
3. Password di-hash dengan bcrypt.
4. User baru disimpan ke tabel `users`.

#### Login

1. Client mengirim email dan password ke `POST /auth/login`.
2. Service mencari user berdasarkan email.
3. Password plaintext diverifikasi terhadap `password_hash`.
4. Jika valid, backend membuat JWT access token.
5. Token dikembalikan dalam response.

#### Get Current User

1. Client mengirim bearer token.
2. Dependency `get_current_user()` mendecode JWT.
3. Nilai `sub` pada token dipakai sebagai `user_id`.
4. User diambil dari database.
5. Jika token invalid atau user tidak ada, request ditolak dengan `401`.

## Studio Session

Studio session adalah unit kerja utama untuk proses penyusunan dokumen.

Route yang tersedia:

- `POST /studio/sessions`
- `GET /studio/sessions`
- `GET /studio/sessions/{session_id}`

Semua route ini membutuhkan user yang sudah login.

### Cara Kerja Pembuatan Session

Saat user membuat session baru:

1. Backend menerima `title` dan `document_type`.
2. Service menentukan `current_stage` awal berdasarkan tipe dokumen.
3. Record baru dibuat di tabel `studio_sessions`.
4. Backend langsung membuat `planning_states` untuk session tersebut.
5. `state_data` awal diisi sesuai workflow tipe dokumen.

### Tipe Dokumen

Saat ini ada dua tipe dokumen:

- `intrakurikuler`
- `pjbl`

### Initial Stage

Initial stage ditentukan oleh `get_initial_stage()`:

- `intrakurikuler` -> `intra_stage_1_learning_brief`
- `pjbl` -> `pjbl_stage_1_identity_context`

### Initial Planning State

`planning_state.state_data` berbentuk JSONB dan berisi struktur workflow.

Contoh field tingkat atas untuk `intrakurikuler`:

- `meta`
- `learning_brief`
- `curriculum`
- `classroom_context`
- `problem_definition`
- `strategy`

Contoh field tingkat atas untuk `pjbl`:

- `meta`
- `identity_context`
- `goals_driving_question`
- `project_execution`
- `assessment_guardrails`
- `resources_finalize`

## Model Data

Berikut model yang ada di codebase.

### 1. User

Tabel: `users`

Menyimpan data akun:

- `id`
- `full_name`
- `email`
- `password_hash`
- `school_name`
- `role`
- `created_at`
- `updated_at`

Relasi:

- satu user punya banyak `studio_sessions`
- satu user punya banyak `generated_documents`

### 2. StudioSession

Tabel: `studio_sessions`

Menyimpan container utama aktivitas user:

- `id`
- `user_id`
- `title`
- `document_type`
- `current_stage`
- `status`
- `completion_score`
- `last_message_at`
- `created_at`
- `updated_at`

Relasi:

- milik satu `user`
- punya banyak `messages`
- punya satu `planning_state`
- punya banyak `generated_documents`
- punya banyak `audio_records`
- punya banyak `ai_logs`

### 3. PlanningState

Tabel: `planning_states`

Menyimpan state progres workflow per session:

- `session_id`
- `document_type`
- `state_data` dalam format JSONB
- `completion_score`
- `is_ready_for_summary`
- `is_ready_for_generation`
- `version`

Karena memakai JSONB, struktur state bisa fleksibel tanpa perlu banyak tabel tambahan.

### 4. StudioMessage

Tabel: `studio_messages`

Disiapkan untuk menyimpan percakapan dalam sebuah session:

- `sender_type`
- `message_type`
- `message_text`
- `sequence_number`

Ada unique constraint pada kombinasi:

- `session_id`
- `sequence_number`

Ini mencegah urutan pesan ganda dalam satu session.

### 5. GeneratedDocument

Tabel: `generated_documents`

Disiapkan untuk menyimpan hasil dokumen yang dibentuk dari planning state:

- `content_json`
- `content_markdown`
- `status`
- `version`
- `generated_from_state_version`

### 6. AudioRecord

Tabel: `audio_records`

Disiapkan untuk upload audio, penyimpanan metadata file, dan hasil transkripsi:

- `file_path`
- `mime_type`
- `duration_seconds`
- `transcript_text`
- `transcription_status`

### 7. AILog

Tabel: `ai_logs`

Disiapkan untuk audit/logging proses AI:

- `step_name`
- `model_name`
- `prompt_text`
- `response_text`
- `input_payload`
- `output_payload`
- `latency_ms`

Model ini berguna untuk observability, debugging, dan pelacakan output AI.

## Enum Domain

Beberapa enum penting yang dipakai:

### `DocumentTypeEnum`

- `intrakurikuler`
- `pjbl`

### `SessionStatusEnum`

- `active`
- `review`
- `completed`
- `archived`

### `SenderTypeEnum`

- `user`
- `assistant`
- `system`

### `MessageTypeEnum`

- `text`
- `voice_transcript`
- `summary`
- `revision_note`

### `DocumentStatusEnum`

- `draft`
- `final`
- `revised`

### `TranscriptionStatusEnum`

- `pending`
- `success`
- `failed`

## Schema Request dan Response

Schema Pydantic ada di folder `app/schemas`.

### Auth Schema

- `UserCreate` untuk register
- `UserLogin` untuk login
- `UserResponse` untuk response data user
- `TokenResponse` untuk JWT response

### Studio Session Schema

- `StudioSessionCreate` untuk membuat session
- `StudioSessionResponse` untuk response data session

Schema response memakai `from_attributes = True`, jadi object ORM SQLAlchemy bisa langsung di-serialize ke response Pydantic.

## Endpoint API

### Health

#### `GET /`

Mengembalikan pesan sederhana bahwa backend berjalan.

#### `GET /health`

Mengembalikan:

- status app
- nama aplikasi
- environment

#### `GET /health/db`

Menjalankan query `SELECT 1` untuk memastikan database bisa diakses.

### Auth

#### `POST /auth/register`

Request body:

```json
{
  "full_name": "Budi Santoso",
  "email": "budi@example.com",
  "password": "secret123",
  "school_name": "SMA Nusantara"
}
```

Response:

- data user yang berhasil dibuat

#### `POST /auth/login`

Request body:

```json
{
  "email": "budi@example.com",
  "password": "secret123"
}
```

Response:

```json
{
  "access_token": "jwt-token",
  "token_type": "bearer"
}
```

#### `GET /auth/me`

Header:

```http
Authorization: Bearer <access_token>
```

Response:

- data user saat ini

### Studio Sessions

#### `POST /studio/sessions`

Header:

```http
Authorization: Bearer <access_token>
```

Request body:

```json
{
  "title": "RPP IPA Kelas 7",
  "document_type": "intrakurikuler"
}
```

Response:

- data session yang baru dibuat

#### `GET /studio/sessions`

Mengambil semua session milik user yang sedang login, diurutkan dari `updated_at` terbaru.

#### `GET /studio/sessions/{session_id}`

Mengambil detail satu session milik user. Jika session tidak ditemukan atau bukan milik user, backend mengembalikan `404`.

## Migrasi Database

Migrasi database dikelola lewat Alembic.

File penting:

- `alembic/env.py`
- `alembic.ini`
- `alembic/versions/28d77849332c_create_initial_tables.py`

`alembic/env.py` melakukan dua hal penting:

- memuat semua model agar metadata terbaca
- mengambil `DATABASE_URL` dari `.env`

Migrasi awal membuat tabel:

- `users`
- `studio_sessions`
- `planning_states`
- `studio_messages`
- `generated_documents`
- `audio_records`
- `ai_logs`

## Cara Menjalankan Project

### 1. Buat virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependency

```bash
pip install -r requirements.txt
```

### 3. Siapkan PostgreSQL

Buat database sesuai `DATABASE_URL`, misalnya:

```text
petunjukku_db
```

### 4. Jalankan migrasi

```bash
alembic upgrade head
```

### 5. Jalankan server

```bash
uvicorn app.main:app --reload
```

Jika berhasil, API biasanya tersedia di:

- `http://127.0.0.1:8000`
- docs Swagger: `http://127.0.0.1:8000/docs`

## Status Implementasi Saat Ini

Fitur yang sudah aktif:

- auth register
- auth login
- current user
- create session
- list session
- get session detail

Fitur yang modelnya sudah ada tetapi route/service lengkapnya belum terlihat dipakai:

- manajemen chat/message
- upload audio dan transkripsi
- generasi dokumen
- logging proses AI
- update planning state per tahap

## Catatan Teknis

- Codebase ini sangat bergantung pada PostgreSQL karena memakai tipe `JSONB` dan `UUID` PostgreSQL.
- `requirements.txt` saat ini berisi banyak dependency yang tampaknya tidak relevan langsung dengan backend FastAPI ini, jadi bisa dipertimbangkan untuk dirapikan.
- Belum ada suite testing yang jelas untuk API atau service layer.
- Saat register, role user masih diset statis menjadi `teacher`.

## Saran Pengembangan Selanjutnya

- tambah `README` khusus setup development dan deployment
- tambah dokumentasi ERD atau diagram relasi tabel
- tambah endpoint untuk chat/message dan update planning state
- tambah test untuk auth dan studio session
- rapikan dependency project agar lebih fokus

## Referensi File Penting

- `app/main.py`
- `app/core/config.py`
- `app/core/security.py`
- `app/core/dependencies.py`
- `app/db/base.py`
- `app/db/session.py`
- `app/routes/auth.py`
- `app/routes/studio_sessions.py`
- `app/services/auth_service.py`
- `app/services/session_service.py`
- `app/models/`
- `alembic/env.py`

