# Palm Mind AI — Hiring Assignment Backend

Production-ready FastAPI backend implementing the requested Palm Mind AI hiring workflow: document ingestion, vector RAG, multi-turn Redis memory, and LLM-assisted interview booking.

## Features

- **Document Ingestion API**: PDF/TXT upload, extraction, two selectable chunking strategies (`fixed`, `recursive`), embeddings, Qdrant persistence, PostgreSQL metadata.
- **Conversational RAG API**: custom retrieval + prompt construction; no `RetrievalQAChain`.
- **Redis multi-turn memory**: rolling conversation history with TTL.
- **LLM-assisted interview booking**: extracts name, email, date and time from booking requests, validates them with Pydantic, and persists bookings in PostgreSQL.
- Strong typing, Pydantic validation, structured application errors, logging, repository/service separation.
- Docker Compose for FastAPI, PostgreSQL, Redis and Qdrant.
- Swagger/OpenAPI at `/docs` and `/redoc`.
- Tests for APIs, validation and chunking.
- No FAISS, Chroma or UI.

## Architecture

```text
app/
├── api/                  # HTTP routes and dependency wiring
├── core/                 # settings, logging, exceptions
├── database/             # SQLAlchemy models/session
├── infrastructure/      # OpenAI, Qdrant and Redis adapters
├── repositories/        # PostgreSQL persistence
├── schemas/              # Pydantic request/response models
├── services/             # ingestion and RAG orchestration
└── main.py
alembic/                  # database migrations
tests/                    # automated tests
```

### Data flow

```text
PDF/TXT → extraction → chunking → OpenAI embeddings → Qdrant
                                      └──────────────→ PostgreSQL metadata

Chat → Redis history → embedding → Qdrant top-K → custom context prompt → LLM
  └──────────────────────────────────────────────────────────────→ Redis history

Booking request → LLM structured extraction → Pydantic validation → PostgreSQL
```

## Quick start with Docker

1. Copy configuration:

```bash
cp .env.example .env
```

2. Set `OPENAI_API_KEY` in `.env`.

3. Start everything:

```bash
docker compose up --build
```

4. Open Swagger:

- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`
- `http://localhost:8000/health`

## API 1 — Document ingestion

`POST /api/v1/documents/ingest`

Multipart fields:
- `file`: `.pdf` or `.txt`
- `chunking_strategy`: `fixed` or `recursive`

Example with curl:

```bash
curl -X POST http://localhost:8000/api/v1/documents/ingest \
  -F 'file=@./resume.pdf' \
  -F 'chunking_strategy=recursive'
```

The response returns the PostgreSQL document ID and number of chunks stored in Qdrant.

## API 2 — Conversational RAG

`POST /api/v1/chat`

```json
{
  "session_id": "candidate-001",
  "message": "What skills are required for this role?"
}
```

The same `session_id` retrieves prior turns from Redis.

## Interview booking

Send a clear booking request through the same chat endpoint, for example:

```json
{
  "session_id": "candidate-001",
  "message": "Please book my interview. My name is Jane Doe, email jane@example.com, on 2026-10-01 at 10:30."
}
```

The LLM extracts booking intent and fields. Pydantic validates email/date/time, and the validated booking is persisted to PostgreSQL. Duplicate email/date/time slots are idempotent.

The assistant never invents missing booking values; when fields are missing it asks the candidate to provide them.

## Local development

Python 3.11–3.13 is supported.

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

A local PostgreSQL, Redis and Qdrant instance must be available. Run migrations with:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

## Tests

The test suite uses FastAPI dependency overrides, so API tests do not require live OpenAI, Qdrant, Redis or PostgreSQL services.

```bash
pip install -e '.[test]'
pytest -q
```

## Production notes

- Store `.env` outside source control and use a secrets manager in deployment.
- Put TLS/authentication at the platform or gateway layer for public deployment.
- Qdrant and Redis are internal services in the supplied Compose setup.
- The application uses a bounded Redis conversation history and TTL to prevent unbounded memory growth.
- PostgreSQL schema is managed through Alembic.
