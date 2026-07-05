from __future__ import annotations

import base64
import logging
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse

from app.orchestrator import process_request
from app.config import get_config

router = APIRouter(prefix="/api/v1")
logger = logging.getLogger("hypothesis_factory")
_start_time = time.monotonic()
config = get_config()


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "uptime_seconds": round(time.monotonic() - _start_time, 1),
        "services": {
            "llm": config.llm_service_url,
            "vector_db": f"amqp://{config.rabbitmq_host}:{config.rabbitmq_port}",
            "content_extraction": config.content_extraction_url,
        },
    }


@router.post("/generate")
async def generate(
    query: str = Form(..., description="Запрос пользователя"),
    analysis_data: str = Form(default="", description="CSV/текст анализа потерь"),
    document_files: list[UploadFile] = File(default=[]),
    num_hypotheses: int = Form(default=0, description="Количество гипотез (0 = default)"),
):
    """
    Generate hypotheses from query + analysis data + optional documents/images.
    Returns validated hypotheses with final report.
    """
    documents = []
    image_paths = []

    # Process uploaded files
    for f in (document_files or []):
        if not f.filename:
            continue
        content = await f.read()
        ext = Path(f.filename).suffix.lower()

        if ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"):
            # Save image to temp for VLM processing
            img_path = Path(config.reports_dir) / f"upload_{f.filename}"
            img_path.parent.mkdir(parents=True, exist_ok=True)
            img_path.write_bytes(content)
            image_paths.append(str(img_path))
        else:
            # Treat as document
            documents.append(content.decode("utf-8", errors="replace")[:10000])

    num = num_hypotheses if num_hypotheses > 0 else None

    try:
        result = await process_request(
            query=query,
            documents=documents,
            analysis_data=analysis_data,
            image_paths=image_paths if image_paths else None,
            num_hypotheses=num,
        )
        return result
    except Exception as e:
        logger.exception("generation_failed")
        raise HTTPException(500, str(e))


@router.get("/reports/{filename}")
async def get_report(filename: str):
    """Download a generated report."""
    path = Path(config.reports_dir) / filename
    if not path.exists():
        raise HTTPException(404, f"Report not found: {filename}")
    return PlainTextResponse(path.read_text(encoding="utf-8"), media_type="text/markdown")
