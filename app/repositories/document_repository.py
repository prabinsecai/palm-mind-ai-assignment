from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Document
class DocumentRepository:
    def __init__(self, db: AsyncSession): self.db=db
    async def create(self, filename: str, content_type: str, strategy: str, chunks: int) -> Document:
        obj=Document(filename=filename, content_type=content_type, chunking_strategy=strategy, chunk_count=chunks); self.db.add(obj); await self.db.commit(); await self.db.refresh(obj); return obj
