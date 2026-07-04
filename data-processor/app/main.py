from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI

from app.config import get_config
from app.logger import setup_logging
from app.router import router

config = get_config()
setup_logging(config.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger = logging.getLogger("data_processor")
    logger.info("service_starting", extra={"host": config.host, "port": config.port})
    Path(config.images_dir).mkdir(parents=True, exist_ok=True)
    Path(config.uploads_dir).mkdir(parents=True, exist_ok=True)
    Path(config.output_dir).mkdir(parents=True, exist_ok=True)
    yield
    logger.info("service_stopped")


app = FastAPI(
    title="Data Processor — File-to-Markdown Converter",
    description="Converts PDF, DOCX, XLSX, XLS, CSV, images, code and text files to Markdown format",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(router)
