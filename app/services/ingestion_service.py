import asyncio
import logging
from uuid import uuid4

from app.core.config import get_settings
from app.core.exceptions import FileTooLargeError
from app.database.models import Document
from app.infrastructure.openai_client import OpenAIService
from app.infrastructure.qdrant_store import QdrantStore
from app.repositories.document_repository import DocumentRepository
from app.services.chunking import make_chunks
from app.services.document_parser import extract_text

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(
        self,
        repo: DocumentRepository,
        llm: OpenAIService,
        qdrant: QdrantStore,
    ) -> None:
        self.repo = repo
        self.llm = llm
        self.qdrant = qdrant

    async def ingest(
        self,
        filename: str,
        content_type: str,
        data: bytes,
        strategy: str,
    ) -> Document:
        settings = get_settings()
        if len(data) > settings.max_upload_bytes:
            raise FileTooLargeError("Uploaded file exceeds MAX_UPLOAD_BYTES")

        logger.info("Document ingestion started: filename=%s", filename)
        text = await asyncio.to_thread(extract_text, filename, content_type, data)
        chunks = make_chunks(text, strategy)
        embeddings = await self.llm.embed([chunk.text for chunk in chunks])
        document_id = uuid4()
        await self.qdrant.upsert(document_id, filename, chunks, embeddings)

        try:
            document = await self.repo.create(
                document_id,
                filename,
                content_type,
                strategy,
                len(chunks),
            )
        except Exception:
            try:
                await self.qdrant.delete_document(document_id)
            except Exception:
                logger.exception(
                    "Failed to clean up Qdrant points for document %s",
                    document_id,
                )
            raise

        logger.info(
            "Document ingestion finished: document_id=%s chunks=%d",
            document.id,
            len(chunks),
        )
        return document
