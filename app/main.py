from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import chat, health, ingestion
from app.core.config import get_settings
from app.core.exceptions import (
    EmptyDocumentError,
    FileTooLargeError,
    PalmMindError,
    UnsupportedFileTypeError,
)
from app.core.logging import configure_logging
from app.database.session import dispose_database_engine
from app.infrastructure.openai_client import OpenAIService
from app.infrastructure.qdrant_store import QdrantStore
from app.infrastructure.redis_memory import ChatMemory


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    app.state.llm = OpenAIService()
    app.state.qdrant = QdrantStore()
    app.state.memory = ChatMemory()
    try:
        await app.state.qdrant.ensure_collection()
        yield
    finally:
        await app.state.llm.client.close()
        await app.state.qdrant.client.close()
        await app.state.memory.redis.aclose()
        await dispose_database_engine()


app = FastAPI(
    title=get_settings().app_name,
    version="1.0.0",
    description="Document ingestion and conversational RAG backend for Palm Mind AI.",
    lifespan=lifespan,
)
app.include_router(health.router)
app.include_router(ingestion.router)
app.include_router(chat.router)


@app.exception_handler(FileTooLargeError)
async def file_too_large(_: Request, exc: FileTooLargeError) -> JSONResponse:
    return JSONResponse(status_code=413, content={"detail": str(exc)})


@app.exception_handler(UnsupportedFileTypeError)
async def unsupported_file(_: Request, exc: UnsupportedFileTypeError) -> JSONResponse:
    return JSONResponse(status_code=415, content={"detail": str(exc)})


@app.exception_handler(EmptyDocumentError)
async def empty_document(_: Request, exc: EmptyDocumentError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(PalmMindError)
async def palm_mind_error(_: Request, exc: PalmMindError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})
