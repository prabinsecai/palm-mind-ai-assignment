from dataclasses import dataclass
from uuid import UUID

from qdrant_client import AsyncQdrantClient, models

from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError, InvalidInputError
from app.services.chunking import Chunk


@dataclass(frozen=True)
class SearchHit:
    document_id: UUID
    filename: str
    chunk_index: int
    text: str
    score: float


class QdrantStore:
    def __init__(self) -> None:
        settings = get_settings()
        self.collection = settings.qdrant_collection
        self.client = AsyncQdrantClient(url=settings.qdrant_url)
        self.dim = settings.embedding_dimensions

    async def ensure_collection(self) -> None:
        try:
            if not await self.client.collection_exists(self.collection):
                await self.client.create_collection(
                    self.collection,
                    vectors_config=models.VectorParams(
                        size=self.dim,
                        distance=models.Distance.COSINE,
                    ),
                )
        except Exception as exc:
            raise ExternalServiceError("Qdrant collection initialization failed") from exc

    async def upsert(
        self,
        document_id: UUID,
        filename: str,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> None:
        if len(chunks) != len(embeddings):
            raise InvalidInputError("Each document chunk must have one embedding")
        points: list[models.PointStruct] = []
        for chunk, vector in zip(chunks, embeddings):
            points.append(
                models.PointStruct(
                    id=str(UUID(int=(document_id.int + chunk.index) % (2**128))),
                    vector=vector,
                    payload={
                        "document_id": str(document_id),
                        "filename": filename,
                        "chunk_index": chunk.index,
                        "text": chunk.text,
                    },
                )
            )
        try:
            await self.client.upsert(
                collection_name=self.collection,
                points=points,
                wait=True,
            )
        except Exception as exc:
            raise ExternalServiceError("Qdrant upsert failed") from exc

    async def delete_document(self, document_id: UUID) -> None:
        try:
            await self.client.delete(
                collection_name=self.collection,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="document_id",
                                match=models.MatchValue(value=str(document_id)),
                            )
                        ]
                    )
                ),
                wait=True,
            )
        except Exception as exc:
            raise ExternalServiceError("Qdrant document cleanup failed") from exc

    async def search(self, vector: list[float], limit: int) -> list[SearchHit]:
        try:
            result = await self.client.query_points(
                collection_name=self.collection,
                query=vector,
                limit=limit,
                with_payload=True,
            )
            hits: list[SearchHit] = []
            for point in result.points:
                payload = point.payload or {}
                hits.append(
                    SearchHit(
                        document_id=UUID(str(payload["document_id"])),
                        filename=str(payload["filename"]),
                        chunk_index=int(payload["chunk_index"]),
                        text=str(payload["text"]),
                        score=float(point.score or 0.0),
                    )
                )
            return hits
        except Exception as exc:
            raise ExternalServiceError("Qdrant search failed") from exc
