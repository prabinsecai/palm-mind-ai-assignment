# Palm Mind AI — Hiring Assignment Backend

Production-ready FastAPI backend implementing the requested Palm Mind AI hiring workflow: document ingestion, vector-based RAG, multi-turn conversational memory, and LLM-assisted interview booking.

## Features

* **Document Ingestion API**

  * PDF/TXT upload
  * Text extraction
  * Two selectable chunking strategies: `fixed` and `recursive`
  * Embedding generation
  * Qdrant vector storage
  * PostgreSQL document metadata

* **Conversational RAG API**

  * Custom retrieval and context construction
  * Top-K semantic retrieval
  * Multi-turn conversation support
  * No `RetrievalQAChain`

* **Redis Conversation Memory**

  * Session-based conversation history
  * Per-session interview booking drafts
  * Configurable TTL
  * Bounded conversation history

* **LLM-Assisted Interview Booking**

  * Extracts candidate name, email, date and time
  * Pydantic validation
  * PostgreSQL persistence
  * Does not invent missing booking information

* Strong typing and Pydantic validation

* Structured application errors

* Repository/service separation

* Docker Compose environment

* Swagger/OpenAPI documentation

* Automated tests

* No FAISS

* No Chroma

* No UI

## Architecture

```text
app/
├── api/                 # HTTP routes and dependency wiring
├── core/                # Settings, logging and exceptions
├── database/            # SQLAlchemy models and database session
├── infrastructure/     # LLM, Qdrant and Redis adapters
├── repositories/        # PostgreSQL persistence
├── schemas/             # Pydantic request/response models
├── services/            # Ingestion and RAG orchestration
└── main.py

alembic/                 # Database migrations
tests/                   # Automated tests
```

## Data Flow

```text
PDF/TXT
   |
   v
Text Extraction
   |
   v
Chunking
   |
   v
Embedding Generation
   |
   +---------------------> Qdrant Vector Database
   |
   +---------------------> PostgreSQL Document Metadata


Chat Request
   |
   +---------------------> Redis Conversation History
   |
   v
Query Embedding
   |
   v
Qdrant Top-K Retrieval
   |
   v
Custom Context Construction
   |
   v
LLM Response
   |
   +---------------------> Redis Conversation History


Booking Request
   |
   v
LLM Structured Extraction + Redis Booking Draft
   |
   v
Validate and Request Missing Details
   |
   v
PostgreSQL Booking Persistence
```

## Technology Stack

| Component           | Technology            |
| ------------------- | --------------------- |
| Backend             | FastAPI               |
| Language            | Python 3.11–3.13      |
| Validation          | Pydantic              |
| Database            | PostgreSQL            |
| Vector Database     | Qdrant                |
| Conversation Memory | Redis                 |
| ORM                 | SQLAlchemy            |
| Migrations          | Alembic               |
| LLM / Embeddings    | OpenAI-compatible API |
| Containerization    | Docker Compose        |
| Testing             | Pytest                |

## Quick Start with Docker

### 1. Clone the repository

```bash
git clone https://github.com/prabinsecai/palm-mind-ai-assignment.git
cd palm-mind-ai-assignment
```

### 2. Create environment configuration

Linux/macOS:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Set `OPENAI_API_KEY` in `.env`. The default endpoint is OpenAI; set
`OPENAI_BASE_URL` only when using an OpenAI-compatible provider.

Do not commit `.env` or expose API credentials in source control.

### 3. Start the application

```bash
docker compose up --build
```

The Compose environment starts:

* FastAPI
* PostgreSQL
* Redis
* Qdrant

### 4. API Documentation

Swagger UI:

```text
http://localhost:8000/docs
```

ReDoc:

```text
http://localhost:8000/redoc
```

Health check:

```text
http://localhost:8000/health
```

## API 1 — Document Ingestion

### Endpoint

```text
POST /api/v1/documents/ingest
```

### Multipart Fields

| Field               | Description            |
| ------------------- | ---------------------- |
| `file`              | PDF or TXT document    |
| `chunking_strategy` | `fixed` or `recursive` |

### Example

```bash
curl -X POST http://localhost:8000/api/v1/documents/ingest \
  -F "file=@./resume.pdf" \
  -F "chunking_strategy=recursive"
```

The response returns the document ID and the number of chunks created.

Document metadata (including the chunk count and selected chunking strategy) is stored in PostgreSQL. Chunk text and its retrieval payload are stored in Qdrant; chunk text and chunk metadata are not stored in PostgreSQL.

## API 2 — Conversational RAG

### Endpoint

```text
POST /api/v1/chat
```

### Example Request

```json
{
  "session_id": "candidate-001",
  "message": "What skills are required for this role?"
}
```

The same `session_id` is used to retrieve previous conversation turns from Redis.

The RAG pipeline performs:

1. Query embedding
2. Vector similarity search
3. Top-K document retrieval
4. Context construction
5. LLM response generation
6. Conversation history persistence

## Interview Booking

Interview booking is handled through the same chat endpoint.

### Example Request

```json
{
  "session_id": "candidate-001",
  "message": "Please book my interview. My name is Jane Doe, email jane@example.com, on 2026-12-01 at 10:30."
}
```

The system:

1. Detects booking intent and extracts any details from each turn using the conversation history.
2. Stores collected name, email, date and time in a Redis draft scoped to the session. The draft
   expires using `CHAT_MEMORY_TTL_SECONDS`.
3. Validates provided fields and asks only for fields that are missing or invalid. Relative dates
   are resolved using the current date.
4. Persists the booking in PostgreSQL when all fields are valid, clears the Redis draft, and returns
   the booking information and ID.

Required booking fields:

* Candidate name
* Email
* Date
* Time

The system does not invent missing booking information. If a booking draft exists, later turns
continue that booking even when the candidate does not repeat the word “book.”

## Configuration

The default chat and embedding models are `gpt-4o-mini` and `text-embedding-3-small`, with
`EMBEDDING_DIMENSIONS=1536`. `OPENAI_BASE_URL` is optional and should be left unset when using
the official OpenAI endpoint. Chunk size and overlap are controlled by `CHUNK_SIZE` and
`CHUNK_OVERLAP`.

## Local Development

Python 3.11–3.13 is supported.

Create a virtual environment:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create environment configuration:

```bash
cp .env.example .env
```

For local development, PostgreSQL, Redis and Qdrant must be available.

Run database migrations:

```bash
alembic upgrade head
```

Start the API:

```bash
uvicorn app.main:app --reload
```

## Testing

The automated test suite covers API behavior, validation, chunking and service-level functionality.

Install test dependencies:

```bash
pip install -e ".[test]"
```

Run the test suite:

```bash
pytest -q
```

Current local verification:

```text
16 passed
```

The test suite uses dependency overrides for external services and does not require live LLM, Qdrant, Redis or PostgreSQL services for the automated API tests.

## Production Considerations

* Store environment secrets outside source control.
* Use a dedicated secrets manager for production credentials.
* Place authentication and TLS at the gateway or platform layer for public deployment.
* Keep Qdrant and Redis internal to the application network.
* Use Redis TTL and bounded conversation history to control memory growth.
* Manage PostgreSQL schema changes through Alembic migrations.
* Add authentication, rate limiting, observability and service-level monitoring before public production deployment.

## Assignment Constraints

This implementation intentionally avoids:

* FAISS
* Chroma
* `RetrievalQAChain`
* UI/frontend components

The project focuses on the requested backend architecture, document ingestion, embeddings, vector retrieval, custom RAG, conversational memory, structured interview booking and production-oriented service separation.
