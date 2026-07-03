from contextlib import asynccontextmanager
import asyncio
from typing import AsyncIterator

import sys

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.routes.health import router as health_router
from app.api.routes.extract import router as extract_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.browser_pool import BrowserPool
from app.exceptions import (
    BrowserUnavailableError,
    ExtractionError,
    InvalidURLError,
    PageLoadError,
)
from app.services.browser.browser_service import BrowserService
from app.services.extractor.readability_service import ReadabilityService
from app.services.extract_service import ExtractService
from app.services.markdown.markdown_service import MarkdownService
from app.services.metadata.metadata_service import MetadataService


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    settings = get_settings()
    browser_pool = BrowserPool(settings)
    browser_service = BrowserService(browser_pool, settings)
    extract_service = ExtractService(
        browser_service=browser_service,
        readability_service=ReadabilityService(),
        markdown_service=MarkdownService(),
        metadata_service=MetadataService(),
    )

    app.state.settings = settings
    app.state.browser_pool = browser_pool
    app.state.browser_service = browser_service
    app.state.extract_service = extract_service

    try:
        yield
    finally:
        await browser_pool.close()


app = FastAPI(title="Content Extraction Service", version="0.1.0", lifespan=lifespan)

app.include_router(health_router)
app.include_router(extract_router, prefix="/api/v1")


@app.exception_handler(InvalidURLError)
async def handle_invalid_url(_request, exc: InvalidURLError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc), "error": "invalid_url"})


@app.exception_handler(PageLoadError)
async def handle_page_load_error(_request, exc: PageLoadError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(exc), "error": "page_load_error"})


@app.exception_handler(BrowserUnavailableError)
async def handle_browser_unavailable(_request, exc: BrowserUnavailableError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc), "error": "browser_unavailable"})


@app.exception_handler(ExtractionError)
async def handle_extraction_error(_request, exc: ExtractionError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc), "error": "extraction_error"})
