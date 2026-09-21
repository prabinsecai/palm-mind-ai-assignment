from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.infrastructure.openai_client import OpenAIService
from app.infrastructure.qdrant_store import QdrantStore
from app.infrastructure.redis_memory import ChatMemory
from app.repositories.document_repository import DocumentRepository
from app.repositories.booking_repository import BookingRepository
from app.services.ingestion_service import IngestionService
from app.services.rag_service import RAGService

def get_qdrant(request: Request) -> QdrantStore: return request.app.state.qdrant

def get_llm(request: Request) -> OpenAIService: return request.app.state.llm

def get_memory(request: Request) -> ChatMemory: return request.app.state.memory

def ingestion_service(db: AsyncSession=Depends(get_db), llm:OpenAIService=Depends(get_llm), qdrant:QdrantStore=Depends(get_qdrant)) -> IngestionService:
    return IngestionService(DocumentRepository(db),llm,qdrant)

def rag_service(db: AsyncSession=Depends(get_db), llm:OpenAIService=Depends(get_llm), qdrant:QdrantStore=Depends(get_qdrant), memory:ChatMemory=Depends(get_memory)) -> RAGService:
    return RAGService(llm,qdrant,memory,BookingRepository(db))
