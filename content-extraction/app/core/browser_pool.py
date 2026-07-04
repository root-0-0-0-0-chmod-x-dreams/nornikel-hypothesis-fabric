from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import logging
from collections.abc import AsyncIterator
import sys
import threading

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from app.core.config import Settings
from app.exceptions import BrowserUnavailableError

logger = logging.getLogger(__name__)


class BrowserPool:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._pages: asyncio.Queue[Page] = asyncio.Queue(maxsize=settings.max_pages)
        self._initializing = asyncio.Lock()
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ready = threading.Event()
        self._startup_error: BaseException | None = None
        self._closing = False

    async def initialize(self) -> None:
        if self.is_ready():
            return

        async with self._initializing:
            if self.is_ready():
                return

            if self._thread is None or not self._thread.is_alive():
                self._ready.clear()
                self._startup_error = None
                self._closing = False
                self._thread = threading.Thread(target=self._thread_main, name="browser-pool", daemon=True)
                self._thread.start()

        await self._wait_until_ready()

    def _thread_main(self) -> None:
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(self._bootstrap())
            self._ready.set()
            loop.run_forever()
        except BaseException as exc:  # pragma: no cover - thread startup failures are environment-specific.
            self._startup_error = exc
            self._ready.set()
        finally:
            try:
                if not loop.is_closed():
                    loop.run_until_complete(self._shutdown())
            except Exception:
                pass
            finally:
                try:
                    loop.close()
                finally:
                    self._loop = None

    async def _bootstrap(self) -> None:
        self._playwright = await async_playwright().start()

        try:
            launch_args = ["--disable-blink-features=AutomationControlled"] if self._settings.stealth else []
            self._browser = await self._playwright.chromium.launch(
                headless=self._settings.headless,
                args=launch_args,
            )
            self._context = await self._browser.new_context(
                user_agent=self._settings.user_agent,
                viewport={"width": 1365, "height": 900},
                ignore_https_errors=True,
            )

            for _ in range(self._settings.max_pages):
                await self._pages.put(await self._context.new_page())

            logger.info("browser pool initialized with %s pages", self._settings.max_pages)
        except Exception:
            await self._shutdown()
            raise

    async def _wait_until_ready(self) -> None:
        await asyncio.to_thread(self._ready.wait)
        if self._startup_error is not None:
            raise BrowserUnavailableError("browser pool failed to initialize") from self._startup_error

    def is_ready(self) -> bool:
        return (
            self._ready.is_set()
            and self._startup_error is None
            and self._browser is not None
            and self._context is not None
            and self._browser.is_connected()
        )

    async def ensure_ready(self) -> None:
        await self.initialize()

    async def render(self, url: str, timeout_ms: int) -> tuple[str, int | None, list[dict[str, object]], dict[str, str], str | None, str | None]:
        await self.ensure_ready()

        if self._loop is None:
            raise BrowserUnavailableError("browser pool is not initialized")

        future = asyncio.run_coroutine_threadsafe(self._render(url, timeout_ms), self._loop)
        return await asyncio.wrap_future(future)

    async def _render(self, url: str, timeout_ms: int) -> tuple[str, int | None, list[dict[str, object]], dict[str, str], str | None, str | None]:
        if self._browser is None or self._context is None:
            raise BrowserUnavailableError("browser pool is not initialized")

        page = await self._pages.get()
        try:
            if page.is_closed():
                page = await self._context.new_page()

            response = await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            try:
                await page.wait_for_load_state("networkidle", timeout=min(5000, timeout_ms))
            except Exception:
                pass

            try:
                html = await page.content()
                if self._has_security_interstitial(html):
                    await page.wait_for_function(
                        """
                        () => {
                            const text = document.body ? document.body.innerText : '';
                            return !text.includes('Performing security verification')
                                && !text.includes('Verification successful. Waiting for')
                                && !text.includes('Enable JavaScript and cookies to continue')
                                && !text.includes('Just a moment...');
                        }
                        """,
                        timeout=min(timeout_ms, 15000),
                    )
            except Exception:
                pass

            html = await page.content()
            title = await page.title()
            cookies = await page.context.cookies(page.url)
            headers = response.headers if response is not None else {}
            status_code = response.status if response is not None else None

            return html, status_code, cookies, headers, title or None, page.url
        finally:
            if self._context is None:
                return

            if page.is_closed():
                replacement = await self._context.new_page()
                await self._pages.put(replacement)
                return

            try:
                await page.goto("about:blank", wait_until="load", timeout=5000)
            except Exception:
                await page.close()
                replacement = await self._context.new_page()
                await self._pages.put(replacement)
            else:
                await self._pages.put(page)

    def _has_security_interstitial(self, html: str) -> bool:
        return (
            "Performing security verification" in html
            or "Verification successful. Waiting for" in html
            or "Enable JavaScript and cookies to continue" in html
            or "Just a moment..." in html
        )

    async def _shutdown(self) -> None:
        self._closing = True

        while not self._pages.empty():
            page = await self._pages.get()
            if not page.is_closed():
                await page.close()

        if self._context is not None:
            await self._context.close()
            self._context = None

        if self._browser is not None:
            await self._browser.close()
            self._browser = None

        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None

    async def close(self) -> None:
        if self._loop is None:
            return

        if not self._closing:
            future = asyncio.run_coroutine_threadsafe(self._shutdown(), self._loop)
            await asyncio.wrap_future(future)

        self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None:
            await asyncio.to_thread(self._thread.join, 5)
        self._thread = None
        self._ready.clear()
