from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from .config import get_config
from .logger import get_logger, setup_logging
from .middleware import ErrorHandlingMiddleware
from .model_manager import get_model_manager
from .router import router
from .yandex_client import get_client

config = get_config()
logger = setup_logging(config.log_level, config.log_format)

DEFAULT_MODELS = {
    "aliceai-llm": {"display_name": "Alice AI LLM", "max_tokens": 1500},
    "yandexgpt": {"display_name": "YandexGPT", "max_tokens": 2000},
    "yandexgpt-lite": {"display_name": "YandexGPT Lite", "max_tokens": 1500},
}


def _register_default_models() -> None:
    mm = get_model_manager()
    for model_id, params in DEFAULT_MODELS.items():
        mm.register_model(
            model_id=model_id,
            display_name=params["display_name"],
            max_tokens=params["max_tokens"],
            supports_streaming=True,
        )
    if config.is_deepseek_configured:
        mm.register_model(
            model_id=config.deepseek_model,
            display_name="DeepSeek V4 Flash",
            max_tokens=2000,
            supports_streaming=True,
        )


async def _initial_health_check() -> None:
    if not config.has_any_provider:
        logger.warning("no_llm_provider_configured")
        return

    mm = get_model_manager()
    client = get_client()
    logger.info("running_initial_health_check")
    for model_id in list(mm._models.keys()):
        ok = await client.probe_model(model_id)
        if ok:
            await mm.mark_available(model_id)
        else:
            await mm.mark_unavailable(model_id, reason="initial_probe_failed")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("service_starting", extra={"host": config.host, "port": config.port})
    _register_default_models()
    await _initial_health_check()

    mm = get_model_manager()
    client = get_client()
    health_task = asyncio.create_task(
        mm.periodic_health_check(
            test_fn=client.probe_model,
            interval=config.health_check_interval,
        )
    )

    yield

    health_task.cancel()
    try:
        await health_task
    except asyncio.CancelledError:
        pass
    logger.info("service_stopped")


app = FastAPI(
    title="LLM Service — Yandex Model Gateway",
    description="FastAPI gateway for Yandex AI Studio models via OpenAI-compatible API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(ErrorHandlingMiddleware)
app.include_router(router)
