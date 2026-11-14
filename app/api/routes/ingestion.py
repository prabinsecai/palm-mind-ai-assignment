from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.api.dependencies import ingestion_service
from app.core.config import get_settings
from app.core.exceptions import FileTooLargeError
from app.schemas.document import ChunkingStrategy, IngestionResponse
from app.services.ingestion_service import IngestionService

router = APIRouter(prefix="/api/v1/documents", tags=["Document Ingestion"])


@router.post(
    "/ingest",
    response_model=IngestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest(
    file: UploadFile = File(...),
    chunking_strategy: ChunkingStrategy = Form(ChunkingStrategy.recursive),
    service: IngestionService = Depends(ingestion_service),
) -> IngestionResponse:
    max_upload_bytes = get_settings().max_upload_bytes
    data = await file.read(max_upload_bytes + 1)
    if len(data) > max_upload_bytes:
        raise FileTooLargeError("Uploaded file exceeds MAX_UPLOAD_BYTES")
    document = await service.ingest(
        file.filename or "upload",
        file.content_type or "application/octet-stream",
        data,
        chunking_strategy.value,
    )
    return IngestionResponse(
        document_id=document.id,
        filename=document.filename,
        chunks_created=document.chunk_count,
        chunking_strategy=chunking_strategy,
    )
