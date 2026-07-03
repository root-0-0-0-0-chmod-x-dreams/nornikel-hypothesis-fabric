import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .config import get_config
from .logger import get_logger

logger = get_logger()


@dataclass
class RequestQueue:
    config = get_config()
    _semaphore: asyncio.Semaphore = field(init=False)
    _active_count: int = 0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def __post_init__(self) -> None:
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)

    async def acquire(self, priority: int = 0) -> bool:
        try:
            await asyncio.wait_for(
                self._semaphore.acquire(),
                timeout=self.config.request_timeout_seconds,
            )
            async with self._lock:
                self._active_count += 1
            logger.debug(
                "queue_slot_acquired",
                extra={
                    "active": self._active_count,
                    "max": self.config.max_concurrent_requests,
                    "priority": priority,
                },
            )
            return True
        except asyncio.TimeoutError:
            logger.warning(
                "queue_timeout",
                extra={
                    "timeout": self.config.request_timeout_seconds,
                    "queue_depth": self.queue_size,
                },
            )
            return False

    def release(self) -> None:
        self._semaphore.release()
        asyncio.ensure_future(self._decrement_active())

    async def _decrement_active(self) -> None:
        async with self._lock:
            self._active_count = max(0, self._active_count - 1)

    @property
    def queue_size(self) -> int:
        total = self.config.max_concurrent_requests
        available = self._semaphore._value
        return max(0, total - available)

    @property
    def active_requests(self) -> int:
        return self._active_count

    @property
    def max_concurrent(self) -> int:
        return self.config.max_concurrent_requests


_queue: Optional[RequestQueue] = None


def get_queue() -> RequestQueue:
    global _queue
    if _queue is None:
        _queue = RequestQueue()
    return _queue
