from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from .config import get_config
from .logger import get_logger
from .model_manager import get_model_manager
from .models import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    ModelInfo,
    QueueStatus,
)
from .queue import get_queue
from .yandex_client import get_client, YandexLLMError

router = APIRouter(prefix="/api/v1")
logger = get_logger()
_start_time = time.monotonic()


@router.get("/health", response_model=HealthResponse)
async def health():
    mm = get_model_manager()
    cfg = get_config()
    return HealthResponse(
        status="ok",
        version="1.0.0",
        uptime_seconds=round(time.monotonic() - _start_time, 1),
        models_count=len(mm._models),
        yandex_configured=cfg.is_configured,
    )


@router.get("/models", response_model=list[ModelInfo])
async def list_models(
    status: Optional[str] = Query(None, pattern="^(available|unavailable|rate_limited|unknown)$"),
):
    mm = get_model_manager()
    all_models = mm.get_all_models()
    if status:
        all_models = [m for m in all_models if m.status.value == status]
    return all_models


@router.get("/queue/status", response_model=QueueStatus)
async def queue_status():
    mm = get_model_manager()
    q = get_queue()
    available = [m.model_id for m in mm.get_available_models()]
    unavailable = [
        m.model_id
        for m in mm.get_all_models()
        if m.status.value in ("unavailable", "rate_limited")
    ]
    return QueueStatus(
        queue_size=q.queue_size,
        active_requests=q.active_requests,
        max_concurrent=q.max_concurrent,
        models_available=available,
        models_unavailable=unavailable,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    client = get_client()
    try:
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        result = await client.chat(
            messages=messages,
            model_id=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            priority=request.priority,
            metadata=request.metadata,
        )
        return ChatResponse(
            request_id=result["request_id"],
            model=result["model"],
            choices=[
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": result["text"],
                    },
                    "finish_reason": "stop",
                }
            ],
            usage={
                "prompt_tokens": result["usage"]["prompt_tokens"],
                "completion_tokens": result["usage"]["completion_tokens"],
                "total_tokens": result["usage"]["total_tokens"],
            },
            created_at=result["created_at"],
        )
    except YandexLLMError as e:
        raise HTTPException(status_code=e.status, detail={"code": e.code, "message": str(e)})


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    client = get_client()

    async def event_stream():
        try:
            messages = [{"role": m.role, "content": m.content} for m in request.messages]
            async for chunk in client.chat_stream(
                messages=messages,
                model_id=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                priority=request.priority,
            ):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except YandexLLMError as e:
            yield f"data: {{\"error\": \"{e}\"}}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
