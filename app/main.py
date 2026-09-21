from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.core.exceptions import FileTooLargeError, UnsupportedFileTypeError, EmptyDocumentError
from app.api.routes import ingestion,chat,health
from app.core.config import get_settings
from app.core.exceptions import PalmMindError
from app.core.logging import configure_logging
from app.infrastructure.openai_client import OpenAIService
from app.infrastructure.qdrant_store import QdrantStore
from app.infrastructure.redis_memory import ChatMemory

logger=logging.getLogger(__name__)
@asynccontextmanager
async def lifespan(app:FastAPI):
    settings=get_settings(); configure_logging(settings.log_level)
    app.state.llm=OpenAIService(); app.state.qdrant=QdrantStore(); app.state.memory=ChatMemory()
    await app.state.qdrant.ensure_collection()
    yield
    await app.state.qdrant.client.close(); await app.state.memory.redis.aclose()

app=FastAPI(title=get_settings().app_name,version="1.0.0",description="Document ingestion and conversational RAG backend for Palm Mind AI.",lifespan=lifespan)
app.include_router(health.router); app.include_router(ingestion.router); app.include_router(chat.router)
@app.exception_handler(FileTooLargeError)
async def file_too_large(_:Request,exc:FileTooLargeError): return JSONResponse(status_code=413,content={"detail":str(exc)})

@app.exception_handler(UnsupportedFileTypeError)
async def unsupported_file(_:Request,exc:UnsupportedFileTypeError): return JSONResponse(status_code=415,content={"detail":str(exc)})

@app.exception_handler(EmptyDocumentError)
async def empty_document(_:Request,exc:EmptyDocumentError): return JSONResponse(status_code=422,content={"detail":str(exc)})

@app.exception_handler(PalmMindError)
async def palm_mind_error(_:Request,exc:PalmMindError): return JSONResponse(status_code=503,content={"detail":str(exc)})
@app.exception_handler(ValueError)
async def value_error(_:Request,exc:ValueError): return JSONResponse(status_code=400,content={"detail":str(exc)})
