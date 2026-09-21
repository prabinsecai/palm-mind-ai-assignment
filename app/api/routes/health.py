from fastapi import APIRouter
from app.schemas.health import HealthResponse
router=APIRouter(tags=["Health"])
@router.get("/health",response_model=HealthResponse)
async def health(): return HealthResponse(status="ok")
