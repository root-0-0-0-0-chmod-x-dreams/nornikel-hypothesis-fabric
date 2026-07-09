"""Real-time progress events for SSE streaming."""

from __future__ import annotations

import threading
import time
from typing import Any, Callable


class ProgressEmitter:
    def __init__(self, on_event: Callable[[dict[str, Any]], None] | None = None) -> None:
        self._on_event = on_event
        self._started = time.monotonic()
        self._step_counter = 0
        self._lock = threading.Lock()

    def elapsed(self) -> float:
        return round(time.monotonic() - self._started, 1)

    def emit(self, event: dict[str, Any]) -> None:
        if not self._on_event:
            return
        with self._lock:
            event.setdefault("elapsedSeconds", self.elapsed())
            self._on_event(event)

    def progress(
        self,
        stage: str,
        *,
        current: int | None = None,
        total: int | None = None,
        message: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {"type": "progress", "stage": stage}
        if current is not None:
            payload["current"] = current
        if total is not None:
            payload["total"] = total
        if message:
            payload["message"] = message
        self.emit(payload)

    def agent_step(
        self,
        *,
        agent: str,
        title: str,
        summary: str,
        detail: str = "",
        status: str = "running",
        step_id: str | None = None,
    ) -> str:
        with self._lock:
            sid = step_id or f"s{self._step_counter + 1}"
            if step_id is None:
                self._step_counter += 1
        self.emit(
            {
                "type": "agent_step",
                "step": {
                    "id": sid,
                    "agent": agent,
                    "title": title,
                    "summary": summary,
                    "detail": detail,
                    "timestamp": self.elapsed(),
                    "status": status,
                },
            }
        )
        return sid
