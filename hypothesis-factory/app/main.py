from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.config import get_config
from app.router import router

config = get_config()


def setup_logging(level: str = "INFO"):
    logger = logging.getLogger("hypothesis_factory")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    if logger.handlers:
        return logger
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JSONFormatter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger


class _JSONFormatter(logging.Formatter):
    def format(self, record):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            entry["exception"] = self.formatException(record.exc_info)
        for key in ("request_id", "count", "verdict", "score", "error"):
            if hasattr(record, key):
                entry[key] = getattr(record, key)
        return json.dumps(entry, ensure_ascii=False)


setup_logging(config.log_level)
logger = logging.getLogger("hypothesis_factory")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from pathlib import Path
    Path(config.reports_dir).mkdir(parents=True, exist_ok=True)
    logger.info("service_starting", extra={"host": config.host, "port": config.port})
    yield
    logger.info("service_stopped")


app = FastAPI(
    title="Hypothesis Factory — Multi-Agent RAG System",
    description="3-agent LLM system for generating and validating scientific hypotheses in mineral processing",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
)

app.include_router(router)
