from __future__ import annotations

from urllib.parse import urlparse

from app.exceptions import ExtractionError, InvalidURLError
from app.schemas.response import ExtractResponse
from app.services.browser.browser_service import BrowserService
from app.services.extractor.readability_service import ReadabilityService
from app.services.markdown.markdown_service import MarkdownService
from app.services.metadata.metadata_service import MetadataService


class ExtractService:
    def __init__(
        self,
        browser_service: BrowserService,
        readability_service: ReadabilityService,
        markdown_service: MarkdownService,
        metadata_service: MetadataService,
    ) -> None:
        self._browser_service = browser_service
        self._readability_service = readability_service
        self._markdown_service = markdown_service
        self._metadata_service = metadata_service

    async def extract(self, url: str) -> ExtractResponse:
        self._validate_url(url)

        try:
            rendered_page = await self._browser_service.render(url)
            article = self._readability_service.extract(rendered_page)
            markdown_document = self._markdown_service.convert(article)
            metadata = self._metadata_service.extract(rendered_page)
        except ExtractionError:
            raise
        except Exception as exc:  # pragma: no cover - depends on upstream services.
            raise ExtractionError("failed to extract content") from exc

        return ExtractResponse(
            url=rendered_page.final_url or rendered_page.url,
            title=article.title,
            markdown=markdown_document.markdown,
            text=article.text,
            byline=article.byline,
            html=article.html,
            metadata=metadata,
            status_code=rendered_page.status_code,
        )

    def _validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise InvalidURLError(f"invalid URL: {url}")
