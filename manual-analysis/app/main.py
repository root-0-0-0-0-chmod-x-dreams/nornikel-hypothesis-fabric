from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.config import get_config
from app.logger import setup_logging
from app.router import router

config = get_config()
setup_logging(config.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    import logging
    logger = logging.getLogger("manual_analysis")
    logger.info("service_starting", extra={"host": config.host, "port": config.port})
    yield
    logger.info("service_stopped")


app = FastAPI(
    title="Manual Analysis — Tailings Loss Analyzer",
    description="Converts flotation tailings Excel data into structured loss analysis (CSV template)",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(router)
