from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from .config import get_config
from .logger import get_logger
from .model_manager import get_model_manager
from .models import (
    ChatChoice,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    ModelInfo,
    QueueStatus,
    TokenUsage,
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
        version="1.1.0",
        uptime_seconds=round(time.monotonic() - _start_time, 1),
        models_count=len(mm._models),
        yandex_configured=cfg.is_configured,
        deepseek_configured=cfg.is_deepseek_configured,
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


def _serialize_content(content) -> str | list:
    if isinstance(content, str):
        return content
    parts = []
    for part in content:
        d = {"type": part.type}
        if part.type == "text":
            d["text"] = part.text
        elif part.type == "image_url" and part.image_url:
            d["image_url"] = {"url": part.image_url.url}
        parts.append(d)
    return parts


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    client = get_client()
    try:
        messages = [{"role": m.role, "content": _serialize_content(m.content)} for m in request.messages]
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
                ChatChoice(
                    index=0,
                    message={
                        "role": "assistant",
                        "content": result["text"],
                    },
                    finish_reason="stop",
                )
            ],
            usage=TokenUsage(
                prompt_tokens=result["usage"]["prompt_tokens"],
                completion_tokens=result["usage"]["completion_tokens"],
                total_tokens=result["usage"]["total_tokens"],
            ),
            created_at=result["created_at"],
        )
    except YandexLLMError as e:
        raise HTTPException(status_code=e.status, detail={"code": e.code, "message": str(e)})


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    client = get_client()

    async def event_stream():
        try:
            messages = [{"role": m.role, "content": _serialize_content(m.content)} for m in request.messages]
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


@router.post("/upload/image")
async def upload_image(file: UploadFile = File(...)):
    """Upload an image file, returns base64 data URI for use in /chat content parts."""
    if not file.filename:
        raise HTTPException(400, "Filename is required")

    content = await file.read()
    ext = Path(file.filename).suffix.lower().lstrip(".")
    mime_map = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif", "webp": "image/webp", "bmp": "image/bmp"}
    mime = mime_map.get(ext, "image/png")

    b64 = base64.b64encode(content).decode()
    url = f"data:{mime};base64,{b64}"

    return {
        "filename": file.filename,
        "mime_type": mime,
        "size_bytes": len(content),
        "image_url": url,
    }


@router.get("/images/{filename:path}")
async def serve_image(filename: str):
    """Serve a local image as base64 data URI for use in chat."""
    config = get_config()
    path = Path(filename)
    if not path.is_absolute():
        path = Path("/") / filename
    if not path.exists():
        raise HTTPException(404, f"Image not found: {filename}")

    content = path.read_bytes()
    ext = path.suffix.lower().lstrip(".")
    mime_map = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif", "webp": "image/webp"}
    mime = mime_map.get(ext, "image/png")

    b64 = base64.b64encode(content).decode()
    return {"filename": path.name, "mime_type": mime, "image_url": f"data:{mime};base64,{b64}"}
