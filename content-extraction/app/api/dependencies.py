from fastapi import Request

from app.services.extract_service import ExtractService


def get_extract_service(request: Request) -> ExtractService:
    return request.app.state.extract_service
