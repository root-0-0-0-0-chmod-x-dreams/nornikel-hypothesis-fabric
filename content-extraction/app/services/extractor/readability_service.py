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

        if self._is_wikipedia_page(page):
            return self._extract_wikipedia_article(page, soup)

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

    def _extract_wikipedia_article(self, page: RenderedPage, soup: BeautifulSoup) -> Article:
        content = soup.select_one("#mw-content-text .mw-parser-output")
        if content is None:
            document = Document(page.html)
            article_html = document.summary(html_partial=True)
            article_soup = BeautifulSoup(article_html, "html.parser")
            text = article_soup.get_text(" ", strip=True)
            excerpt = text[:280] if text else None
            return Article(title=document.short_title() or page.title, html=article_html, text=text, excerpt=excerpt, byline=None)

        for selector in (
            "style",
            "script",
            "noscript",
            "table.infobox",
            "table.navbox",
            "div.navbox",
            "table.vertical-navbox",
            "div.metadata",
            "div.mw-editsection",
            "table.toc",
            "div.toc",
            "ol.references",
            "div.reflist",
            "div.catlinks",
        ):
            for node in content.select(selector):
                node.decompose()

        text = content.get_text(" ", strip=True)
        excerpt = text[:280] if text else None
        return Article(title=page.title, html=str(content), text=text, excerpt=excerpt, byline=None)

    def _is_arxiv_page(self, page: RenderedPage) -> bool:
        parsed = urlparse(page.final_url or page.url)
        return parsed.netloc.endswith("arxiv.org") and parsed.path.startswith("/html/")

    def _is_wikipedia_page(self, page: RenderedPage) -> bool:
        parsed = urlparse(page.final_url or page.url)
        return parsed.netloc.endswith("wikipedia.org") and parsed.path.startswith("/wiki/")
