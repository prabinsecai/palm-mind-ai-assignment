from uuid import UUID

import pytest

from app.services.ingestion_service import IngestionService


class FakeRepository:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.created_ids: list[UUID] = []

    async def create(
        self,
        document_id: UUID,
        filename: str,
        content_type: str,
        strategy: str,
        chunks: int,
    ) -> object:
        if self.should_fail:
            raise RuntimeError("database commit failed")
        self.created_ids.append(document_id)
        return type(
            "Document",
            (),
            {"id": document_id, "filename": filename, "chunk_count": chunks},
        )()


class FakeLLM:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if self.should_fail:
            raise RuntimeError("embedding failed")
        return [[0.1] for _ in texts]


class FakeQdrant:
    def __init__(self) -> None:
        self.upserted_ids: list[UUID] = []
        self.deleted_ids: list[UUID] = []

    async def upsert(self, document_id, filename, chunks, embeddings) -> None:
        self.upserted_ids.append(document_id)

    async def delete_document(self, document_id: UUID) -> None:
        self.deleted_ids.append(document_id)


def text_document() -> bytes:
    return b"Content used for a short ingestion test. " * 20


@pytest.mark.asyncio
async def test_embedding_failure_does_not_create_document_row() -> None:
    repository = FakeRepository()
    qdrant = FakeQdrant()
    service = IngestionService(repository, FakeLLM(should_fail=True), qdrant)

    with pytest.raises(RuntimeError, match="embedding failed"):
        await service.ingest("sample.txt", "text/plain", text_document(), "fixed")

    assert repository.created_ids == []
    assert qdrant.upserted_ids == []


@pytest.mark.asyncio
async def test_database_commit_failure_cleans_up_qdrant_points() -> None:
    repository = FakeRepository(should_fail=True)
    qdrant = FakeQdrant()
    service = IngestionService(repository, FakeLLM(), qdrant)

    with pytest.raises(RuntimeError, match="database commit failed"):
        await service.ingest("sample.txt", "text/plain", text_document(), "fixed")

    assert len(qdrant.upserted_ids) == 1
    assert qdrant.deleted_ids == qdrant.upserted_ids
