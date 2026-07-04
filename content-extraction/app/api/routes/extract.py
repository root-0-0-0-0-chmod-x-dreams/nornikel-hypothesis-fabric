from fastapi import APIRouter, Depends

from app.api.dependencies import get_extract_service
from app.schemas.request import ExtractRequest
from app.schemas.response import ExtractResponse
from app.services.extract_service import ExtractService

router = APIRouter(tags=["extract"])


@router.post("/extract", response_model=ExtractResponse)
async def extract_article(
    request: ExtractRequest,
    service: ExtractService = Depends(get_extract_service),
) -> ExtractResponse:
    return await service.extract(str(request.url))
