from fastapi import APIRouter, File, Form, UploadFile, status, Depends
from app.api.dependencies import ingestion_service
from app.schemas.document import ChunkingStrategy, IngestionResponse
from app.services.ingestion_service import IngestionService

router=APIRouter(prefix="/api/v1/documents",tags=["Document Ingestion"])
@router.post("/ingest",response_model=IngestionResponse,status_code=status.HTTP_201_CREATED)
async def ingest(file:UploadFile=File(...), chunking_strategy:ChunkingStrategy=Form(ChunkingStrategy.recursive), service:IngestionService=Depends(ingestion_service)):
    data=await file.read()
    doc=await service.ingest(file.filename or "upload",file.content_type or "application/octet-stream",data,chunking_strategy.value)
    return IngestionResponse(document_id=doc.id,filename=doc.filename,chunks_created=doc.chunk_count,chunking_strategy=chunking_strategy)
