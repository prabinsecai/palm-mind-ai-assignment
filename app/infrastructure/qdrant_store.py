from uuid import UUID
from qdrant_client import AsyncQdrantClient, models
from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError

class QdrantStore:
    def __init__(self) -> None:
        s=get_settings(); self.collection=s.qdrant_collection; self.client=AsyncQdrantClient(url=s.qdrant_url); self.dim=s.embedding_dimensions

    async def ensure_collection(self) -> None:
        try:
            if not await self.client.collection_exists(self.collection):
                await self.client.create_collection(self.collection, vectors_config=models.VectorParams(size=self.dim, distance=models.Distance.COSINE))
        except Exception as exc: raise ExternalServiceError("Qdrant collection initialization failed") from exc

    async def upsert(self, document_id: UUID, filename: str, chunks: list, embeddings: list[list[float]]) -> None:
        points=[]
        for chunk, vector in zip(chunks, embeddings):
            points.append(models.PointStruct(id=str(UUID(int=(document_id.int + chunk.index) % (2**128))), vector=vector,
                payload={"document_id":str(document_id),"filename":filename,"chunk_index":chunk.index,"text":chunk.text}))
        try: await self.client.upsert(collection_name=self.collection, points=points, wait=True)
        except Exception as exc: raise ExternalServiceError("Qdrant upsert failed") from exc

    async def search(self, vector: list[float], limit: int) -> list[dict]:
        try:
            result=await self.client.query_points(collection_name=self.collection, query=vector, limit=limit, with_payload=True)
            return [{"document_id":p.payload["document_id"],"filename":p.payload["filename"],"chunk_index":p.payload["chunk_index"],"text":p.payload["text"],"score":float(p.score)} for p in result.points]
        except Exception as exc: raise ExternalServiceError("Qdrant search failed") from exc
