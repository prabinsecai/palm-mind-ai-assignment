from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ChunkingStrategy(str, Enum):
    fixed = "fixed"
    recursive = "recursive"


class IngestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    document_id: UUID
    filename: str
    chunks_created: int
    chunking_strategy: ChunkingStrategy
