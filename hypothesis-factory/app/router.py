from __future__ import annotations

import json
import logging
import time
import asyncio
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Callable

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.orchestrator import process_request
from app.config import get_config
from app.api_mapper import hypothesis_to_api, roadmap_from_hypothesis
from app.mcp.vector_db import get_chunk_by_id
from app.context import get_kb_documents, collect_retrieved_paragraphs
from app.kb_catalog import resolve_document_path
from app.kb_preview import build_preview_payload_async, resolve_asset_path

router = APIRouter(prefix="/api/v1")
logger = logging.getLogger("hypothesis_factory")
_start_time = time.monotonic()
config = get_config()

# In-memory cache for roadmap lookups (request_id → validated hypotheses)
_last_generation: dict = {}


class GenerateJsonRequest(BaseModel):
    query: str
    maxHypotheses: int = Field(default=2, alias="maxHypotheses")
    agentCycleDepth: int = Field(default=2, alias="agentCycleDepth")
    documentIds: list[str] | None = None

    model_config = {"populate_by_name": True}


class RoadmapJsonRequest(BaseModel):
    availableEquipment: list[str] | None = None
    availableMaterials: list[str] | None = None
    timeConstraint: str | None = None
    budgetConstraint: str | None = None


class FeedbackJsonRequest(BaseModel):
    status: str
    notes: str | None = None
    actualResults: str | None = None


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
        if result.get("success"):
            validated = result.get("validated") or []
            for i, hyp in enumerate(validated):
                hyp.setdefault("id", f"h{i + 1}")
            _last_generation.clear()
            _last_generation["hypotheses"] = {h["id"]: h for h in validated}
            _last_generation["at"] = datetime.now(timezone.utc).isoformat()
        return result
    except Exception as e:
        logger.exception("generation_failed")
        raise HTTPException(500, str(e))


@router.get("/context/documents")
async def get_context_documents():
    """Pinned knowledge-base documents (GraphRAG + Qdrant)."""
    return {"documents": get_kb_documents()}


@router.get("/context/documents/{doc_id}/content")
async def get_context_document_content(doc_id: str):
    """Markdown preview for a knowledge-base document."""
    try:
        return await build_preview_payload_async(doc_id)
    except FileNotFoundError:
        raise HTTPException(404, f"Document not found: {doc_id}")
    except Exception as exc:
        logger.exception("kb_preview_failed doc_id=%s", doc_id)
        raise HTTPException(500, str(exc)[:500])


@router.get("/context/documents/{doc_id}/file")
async def get_context_document_file(doc_id: str):
    """Download original KB file (xlsx, docx, etc.)."""
    path = resolve_document_path(doc_id)
    if path is None or not path.is_file():
        raise HTTPException(404, f"File not found: {doc_id}")
    media_type, _ = mimetypes.guess_type(path.name)
    return FileResponse(path, media_type=media_type or "application/octet-stream", filename=path.name)


@router.get("/context/documents/{doc_id}/assets/{filename}")
async def get_context_document_asset(doc_id: str, filename: str):
    """Serve scheme/regulation images referenced from markdown previews."""
    path = resolve_asset_path(doc_id, filename)
    if path is None:
        raise HTTPException(404, f"Asset not found: {filename}")
    media_type, _ = mimetypes.guess_type(path.name)
    return FileResponse(path, media_type=media_type or "application/octet-stream")


@router.get("/sources/chunks/{chunk_id}")
async def get_source_chunk(chunk_id: str):
    """Return paragraph/chunk text and citation for source links in the UI."""
    payload = get_chunk_by_id(chunk_id)
    if not payload:
        raise HTTPException(404, f"Chunk not found: {chunk_id}")
    citation = payload.get("citation") or {}
    return {
        "chunkId": payload.get("chunk_id"),
        "text": payload.get("text", ""),
        "source": payload.get("source", ""),
        "citation": citation,
        "displayRef": citation.get("display_ref") or payload.get("source") or chunk_id,
        "page": citation.get("page"),
        "paragraphIndex": citation.get("paragraph_index"),
    }


@router.get("/reports/{filename}")
async def get_report(filename: str):
    """Download a generated report."""
    path = Path(config.reports_dir) / filename
    if not path.exists():
        raise HTTPException(404, f"Report not found: {filename}")
    return PlainTextResponse(path.read_text(encoding="utf-8"), media_type="text/markdown")


async def _run_generation_json(
    req: GenerateJsonRequest,
    on_progress: Callable[[dict], None] | None = None,
) -> dict:
    result = await process_request(
        query=req.query,
        documents=[],
        analysis_data="",
        num_hypotheses=req.maxHypotheses,
        max_iterations=req.agentCycleDepth,
        on_progress=on_progress,
    )
    if not result.get("success"):
        raise HTTPException(500, result.get("error", "Generation failed"))

    validated = result.get("validated") or []
    for i, hyp in enumerate(validated):
        hyp.setdefault("id", f"h{i + 1}")

    _last_generation.clear()
    _last_generation["hypotheses"] = {h["id"]: h for h in validated}
    _last_generation["at"] = datetime.now(timezone.utc).isoformat()

    hypotheses = [hypothesis_to_api(h, i) for i, h in enumerate(validated)]
    global_sources = result.get("global_knowledge_sources") or []
    return {
        "query": req.query,
        "hypotheses": hypotheses,
        "contextDocuments": get_kb_documents(),
        "retrievedParagraphs": collect_retrieved_paragraphs(validated, global_sources),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/hypotheses/generate")
async def generate_hypotheses_json(req: GenerateJsonRequest):
    """Frontend contract: structured hypotheses JSON."""
    return await _run_generation_json(req)


@router.post("/hypotheses/generate/stream")
async def generate_hypotheses_stream(req: GenerateJsonRequest):
    """SSE stream with real pipeline progress."""

    async def event_stream():
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def on_progress(event: dict) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, event)

        async def run_pipeline() -> None:
            try:
                payload = await _run_generation_json(req, on_progress=on_progress)
                await queue.put({"type": "_result", "payload": payload})
            except Exception as exc:
                logger.exception("stream_generation_failed")
                await queue.put({"type": "error", "message": str(exc)[:500]})
            finally:
                await queue.put(None)

        task = asyncio.create_task(run_pipeline())
        yield ": connected\n\n"

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=5.0)
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
                continue

            if event is None:
                break

            if event.get("type") == "_result":
                payload = event["payload"]
                hypotheses = payload.get("hypotheses") or []

                for hyp in hypotheses:
                    yield f"data: {json.dumps({'type': 'hypothesis', 'hypothesis': hyp}, ensure_ascii=False)}\n\n"

                yield f"data: {json.dumps({'type': 'done', 'total': len(hypotheses), **payload}, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
                break

            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        await task

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/hypotheses/{hypothesis_id}/roadmap")
async def get_hypothesis_roadmap(hypothesis_id: str, _req: RoadmapJsonRequest | None = None):
    hyp_map = _last_generation.get("hypotheses") or {}
    raw = hyp_map.get(hypothesis_id)
    if not raw:
        raise HTTPException(404, f"Hypothesis not found: {hypothesis_id}. Run /hypotheses/generate first.")
    return roadmap_from_hypothesis(raw, hypothesis_id)


@router.post("/hypotheses/{hypothesis_id}/feedback")
async def submit_hypothesis_feedback(hypothesis_id: str, req: FeedbackJsonRequest):
    return {
        "hypothesisId": hypothesis_id,
        "status": req.status,
        "recordedAt": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/history")
async def get_history(limit: int = 20, offset: int = 0, status: str | None = None):
    hyp_map = _last_generation.get("hypotheses") or {}
    items = [
        {
            "id": h["id"],
            "title": h.get("title", ""),
            "query": "",
            "novelty": hypothesis_to_api(h, i)["novelty"],
            "confidence": hypothesis_to_api(h, i).get("confidence", 0),
            "feedbackStatus": None,
            "createdAt": _last_generation.get("at") or datetime.now(timezone.utc).isoformat(),
        }
        for i, h in enumerate(hyp_map.values())
    ]
    return {"items": items[offset : offset + limit], "total": len(items), "limit": limit, "offset": offset}

