from fastapi import APIRouter, Depends
from app.api.dependencies import rag_service
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag_service import RAGService
router=APIRouter(prefix="/api/v1/chat",tags=["Conversational RAG"])
@router.post("",response_model=ChatResponse)
async def chat(payload:ChatRequest,service:RAGService=Depends(rag_service)):
    answer,sources,booking,booking_id=await service.chat(payload.session_id,payload.message)
    return ChatResponse(session_id=payload.session_id,answer=answer,sources=sources,booking=booking,booking_id=booking_id)
