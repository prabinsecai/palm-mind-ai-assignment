from uuid import UUID
from app.core.config import get_settings
from app.core.exceptions import FileTooLargeError
from app.services.document_parser import extract_text
from app.services.chunking import make_chunks
from app.repositories.document_repository import DocumentRepository
from app.infrastructure.openai_client import OpenAIService
from app.infrastructure.qdrant_store import QdrantStore

class IngestionService:
    def __init__(self, repo: DocumentRepository, llm: OpenAIService, qdrant: QdrantStore): self.repo=repo; self.llm=llm; self.qdrant=qdrant
    async def ingest(self, filename: str, content_type: str, data: bytes, strategy: str):
        settings=get_settings()
        if len(data)>settings.max_upload_bytes: raise FileTooLargeError("Uploaded file exceeds MAX_UPLOAD_BYTES")
        text=extract_text(filename,content_type,data); chunks=make_chunks(text,strategy)
        doc=await self.repo.create(filename,content_type,strategy,len(chunks))
        vectors=await self.llm.embed([c.text for c in chunks]); await self.qdrant.upsert(doc.id,filename,chunks,vectors)
        return doc
