from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from readability import Document

from app.services.browser.browser_service import RenderedPage


@dataclass(slots=True)
class Article:
    title: str | None
    html: str
    text: str
    excerpt: str | None
    byline: str | None


class ReadabilityService:
    def extract(self, page: RenderedPage) -> Article:
        soup = BeautifulSoup(page.html, "html.parser")

        if self._is_arxiv_page(page):
            article = soup.find("article")
            if article is not None:
                text = article.get_text(" ", strip=True)
                excerpt = text[:280] if text else None
                title = page.title
                return Article(title=title, html=str(article), text=text, excerpt=excerpt, byline=None)

        document = Document(page.html)
        article_html = document.summary(html_partial=True)
        title = document.short_title() or page.title
        article_soup = BeautifulSoup(article_html, "html.parser")
        text = article_soup.get_text(" ", strip=True)
        excerpt = text[:280] if text else None
        byline = None
        return Article(title=title, html=article_html, text=text, excerpt=excerpt, byline=byline)

    def _is_arxiv_page(self, page: RenderedPage) -> bool:
        parsed = urlparse(page.final_url or page.url)
        return parsed.netloc.endswith("arxiv.org") and parsed.path.startswith("/html/")
