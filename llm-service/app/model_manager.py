import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from .config import get_config
from .logger import get_logger
from .models import ModelInfo, ModelStatus

logger = get_logger()


@dataclass
class ModelEntry:
    info: ModelInfo
    failures: int = 0
    last_failure_at: Optional[float] = None
    rate_limit_until: Optional[float] = None


@dataclass
class ModelManager:
    config = get_config()
    _models: Dict[str, ModelEntry] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def register_model(
        self,
        model_id: str,
        display_name: str = "",
        max_tokens: int = 1000,
        supports_streaming: bool = True,
    ) -> None:
        self._models[model_id] = ModelEntry(
            info=ModelInfo(
                model_id=model_id,
                display_name=display_name or model_id,
                status=ModelStatus.UNKNOWN,
                max_tokens=max_tokens,
                supports_streaming=supports_streaming,
            )
        )
        logger.info("registered_model", extra={"model": model_id})

    def get_full_model_id(self, model_id: str) -> str:
        if model_id == self.config.deepseek_model or model_id.startswith("deepseek-"):
            return model_id
        return f"gpt://{self.config.yandex_folder_id}/{model_id}"

    def is_available(self, model_id: str) -> bool:
        entry = self._models.get(model_id)
        if entry is None:
            return False
        if entry.info.status == ModelStatus.AVAILABLE:
            return True
        if entry.info.status == ModelStatus.RATE_LIMITED:
            if entry.rate_limit_until and time.monotonic() > entry.rate_limit_until:
                entry.info.status = ModelStatus.UNKNOWN
                return True
            return False
        return False

    async def mark_available(self, model_id: str) -> None:
        async with self._lock:
            entry = self._models.get(model_id)
            if entry:
                entry.info.status = ModelStatus.AVAILABLE
                entry.info.last_checked_at = datetime.now(timezone.utc).isoformat()
                entry.failures = 0
                entry.rate_limit_until = None
                logger.debug("model_marked_available", extra={"model": model_id})

    async def mark_unavailable(self, model_id: str, reason: str = "") -> None:
        async with self._lock:
            entry = self._models.get(model_id)
            if entry:
                entry.info.status = ModelStatus.UNAVAILABLE
                entry.info.last_checked_at = datetime.now(timezone.utc).isoformat()
                entry.failures += 1
                entry.last_failure_at = time.monotonic()
                logger.warning(
                    "model_marked_unavailable",
                    extra={"model": model_id, "reason": reason},
                )

    async def mark_rate_limited(
        self, model_id: str, retry_after_seconds: float = 60.0
    ) -> None:
        async with self._lock:
            entry = self._models.get(model_id)
            if entry:
                entry.info.status = ModelStatus.RATE_LIMITED
                entry.info.last_checked_at = datetime.now(timezone.utc).isoformat()
                entry.rate_limit_until = time.monotonic() + retry_after_seconds
                entry.failures += 1
                logger.warning(
                    "model_rate_limited",
                    extra={
                        "model": model_id,
                        "retry_after": retry_after_seconds,
                    },
                )

    def get_available_models(self) -> list[ModelInfo]:
        return [
            entry.info
            for entry in self._models.values()
            if entry.info.status == ModelStatus.AVAILABLE
        ]

    def get_all_models(self) -> list[ModelInfo]:
        return [entry.info for entry in self._models.values()]

    async def check_health_for(self, model_id: str, test_fn: Callable) -> bool:
        try:
            await test_fn(model_id)
            await self.mark_available(model_id)
            return True
        except Exception as e:
            error_msg = str(e).lower()
            if "rate" in error_msg or "429" in error_msg:
                await self.mark_rate_limited(model_id)
            else:
                await self.mark_unavailable(model_id, reason=str(e)[:200])
            return False

    async def periodic_health_check(self, test_fn: Callable, interval: int = 60) -> None:
        while True:
            await asyncio.sleep(interval)
            for model_id, entry in list(self._models.items()):
                logger.debug("health_check_started", extra={"model": model_id})
                await self.check_health_for(model_id, test_fn)


_model_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager
