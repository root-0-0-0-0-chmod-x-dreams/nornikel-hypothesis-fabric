from __future__ import annotations

import logging
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse

from app.config import get_config
from app.converters.registry import convert_file
from app.image_manager import get_image_manager
from app.models import (
    BatchConvertResult,
    ConvertResult,
    HealthResponse,
)

router = APIRouter(prefix="/api/v1")
logger = logging.getLogger("data_processor")
_start_time = time.monotonic()
config = get_config()


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        version="1.0.0",
        uptime_seconds=round(time.monotonic() - _start_time, 1),
    )


@router.post("/convert", response_model=ConvertResult)
async def convert(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "Filename is required")

    content = await file.read()
    if len(content) > config.max_file_size_bytes:
        raise HTTPException(
            413,
            f"File too large. Maximum size: {config.max_file_size_mb} MB",
        )

    upload_dir = Path(config.uploads_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    temp_path = upload_dir / f"{uuid.uuid4().hex}_{file.filename}"

    try:
        temp_path.write_bytes(content)
        result = await convert_file(temp_path, file.filename)
        return result
    finally:
        temp_path.unlink(missing_ok=True)


@router.post("/convert/batch", response_model=BatchConvertResult)
async def convert_batch(files: List[UploadFile] = File(...)):
    if len(files) > 50:
        raise HTTPException(400, "Maximum 50 files per batch")

    upload_dir = Path(config.uploads_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    results: List[ConvertResult] = []
    temp_paths: List[Path] = []

    for file in files:
        if not file.filename:
            continue
        content = await file.read()
        if len(content) > config.max_file_size_bytes:
            results.append(ConvertResult(
                success=False,
                original_filename=file.filename,
                file_type="unknown",
                errors=[f"File too large. Max: {config.max_file_size_mb} MB"],
            ))
            continue

        temp_path = upload_dir / f"{uuid.uuid4().hex}_{file.filename}"
        temp_path.write_bytes(content)
        temp_paths.append(temp_path)
        result = await convert_file(temp_path, file.filename)
        results.append(result)

    for p in temp_paths:
        p.unlink(missing_ok=True)

    succeeded = sum(1 for r in results if r.success)
    return BatchConvertResult(
        total=len(results),
        succeeded=succeeded,
        failed=len(results) - succeeded,
        results=results,
    )


@router.get("/convert/{filename:path}/raw", response_class=PlainTextResponse)
async def get_converted_raw(filename: str):
    content = await _lookup_converted(filename)
    if content is None:
        raise HTTPException(404, f"Converted file not found: {filename}")
    return content


async def _lookup_converted(filename: str) -> str | None:
    output_dir = Path(config.output_dir)
    for md_file in output_dir.glob("*.md"):
        if md_file.stem in filename or filename in md_file.stem:
            return md_file.read_text(encoding="utf-8")
    return None
