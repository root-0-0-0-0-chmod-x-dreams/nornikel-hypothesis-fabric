from __future__ import annotations

import time
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .logger import get_logger
from .yandex_client import YandexLLMError

logger = get_logger()


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.monotonic()
        try:
            response = await call_next(request)
            elapsed = (time.monotonic() - start) * 1000
            logger.info(
                "request_completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round(elapsed, 1),
                },
            )
            return response
        except YandexLLMError as e:
            elapsed = (time.monotonic() - start) * 1000
            logger.warning(
                "llm_error_response",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "code": e.code,
                    "duration_ms": round(elapsed, 1),
                },
            )
            return JSONResponse(
                status_code=e.status,
                content={
                    "error": {
                        "code": e.code,
                        "message": str(e),
                    }
                },
            )
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            logger.exception(
                "unhandled_error",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(elapsed, 1),
                },
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Internal server error",
                    }
                },
            )
