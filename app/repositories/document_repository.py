from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Document


class DocumentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        document_id: UUID,
        filename: str,
        content_type: str,
        strategy: str,
        chunks: int,
    ) -> Document:
        document = Document(
            id=document_id,
            filename=filename,
            content_type=content_type,
            chunking_strategy=strategy,
            chunk_count=chunks,
        )
        self.db.add(document)
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        await self.db.refresh(document)
        return document
