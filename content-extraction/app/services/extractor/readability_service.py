from __future__ import annotations

from dataclasses import dataclass

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
        document = Document(page.html)
        article_html = document.summary(html_partial=True)
        title = document.short_title() or page.title
        soup = BeautifulSoup(article_html, "html.parser")
        text = soup.get_text(" ", strip=True)
        excerpt = text[:280] if text else None
        byline = None
        return Article(title=title, html=article_html, text=text, excerpt=excerpt, byline=byline)
