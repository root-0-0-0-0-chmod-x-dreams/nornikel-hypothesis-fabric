from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.browser_pool import BrowserPool
from app.core.config import Settings
from app.exceptions import BrowserUnavailableError, PageLoadError


@dataclass(slots=True)
class RenderedPage:
    url: str
    html: str
    status_code: int | None
    cookies: list[dict[str, Any]] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    title: str | None = None
    final_url: str | None = None


class BrowserService:
    def __init__(self, pool: BrowserPool, settings: Settings) -> None:
        self._pool = pool
        self._settings = settings

    async def render(self, url: str) -> RenderedPage:
        timeout_ms = self._settings.page_timeout * 1000

        try:
            html, status_code, cookies, headers, title, final_url = await self._pool.render(url, timeout_ms)
            return RenderedPage(
                url=url,
                html=html,
                status_code=status_code,
                cookies=cookies,
                headers=headers,
                title=title,
                final_url=final_url,
            )
        except BrowserUnavailableError:
            raise
        except Exception as exc:  # pragma: no cover - Playwright/network failures are environment-dependent.
            raise PageLoadError(f"failed to render {url}") from exc
