from __future__ import annotations

import logging
import tempfile
import time
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile, Query

from .config import get_config
from .llm_analyzer import analyze_with_llm, check_llm_available
from .models import AnalysisResult, AnalysisRow, HealthResponse, LLMStatus
from .parser import parse_excel

router = APIRouter(prefix="/api/v1")
logger = logging.getLogger("manual_analysis")
_start_time = time.monotonic()
config = get_config()


@router.get("/health", response_model=HealthResponse)
async def health():
    llm_ok, llm_error = await check_llm_available()
    return HealthResponse(
        status="ok",
        version="1.0.0",
        uptime_seconds=round(time.monotonic() - _start_time, 1),
        llm=LLMStatus(
            available=llm_ok,
            url=config.llm_service_url,
            model=config.llm_model,
            error=llm_error,
        ),
    )


@router.post("/analyze", response_model=AnalysisResult)
async def analyze(
    file: UploadFile = File(...),
    use_llm: bool = Query(default=True),
):
    if not file.filename:
        raise HTTPException(400, "Filename is required")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".xlsx", ".xls"):
        raise HTTPException(400, f"Unsupported format: {suffix}. Use .xlsx or .xls")

    content = await file.read()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        if use_llm and config.llm_enabled:
            llm_ok, _ = await check_llm_available()
            if llm_ok:
                try:
                    rows = await analyze_with_llm(tmp_path)
                    if rows:
                        return AnalysisResult(
                            success=True,
                            source_file=file.filename,
                            method="llm",
                            rows=rows,
                        )
                except Exception as e:
                    logger.warning("llm_failed_fallback", extra={"error": str(e)})

        rows = parse_excel(tmp_path)
        return AnalysisResult(
            success=True,
            source_file=file.filename,
            method="deterministic",
            rows=rows,
        )

    except Exception as e:
        logger.exception("analysis_failed")
        raise HTTPException(500, str(e))
    finally:
        tmp_path.unlink(missing_ok=True)
