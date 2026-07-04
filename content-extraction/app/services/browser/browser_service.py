from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any
from urllib.parse import urlparse

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
        render_url = self._resolve_render_url(url)

        try:
            html, status_code, cookies, headers, title, final_url = await self._pool.render(render_url, timeout_ms)
            return RenderedPage(
                url=url,
                html=html,
                status_code=status_code,
                cookies=cookies,
                headers=headers,
                title=title,
                final_url=url if render_url != url else final_url,
            )
        except BrowserUnavailableError:
            raise
        except Exception as exc:  # pragma: no cover - Playwright/network failures are environment-dependent.
            raise PageLoadError(f"failed to render {url}") from exc

    def _resolve_render_url(self, url: str) -> str:
        stackprinter_url = self._stackprinter_url(url)
        return stackprinter_url or url

    def _stackprinter_url(self, url: str) -> str | None:
        parsed = urlparse(url)
        if parsed.netloc.lower() != "stackoverflow.com":
            return None

        match = re.match(r"^/questions/(?P<question_id>\d+)(?:/[^/?#]+)?$", parsed.path)
        if match is None:
            return None

        question_id = match.group("question_id")
        return (
            "https://stackoverflow.com/questions/"
            f"{question_id}/stackprinter?service=stackoverflow&language=en&hideAnswers=false&showAll=true&width=640"
        )
