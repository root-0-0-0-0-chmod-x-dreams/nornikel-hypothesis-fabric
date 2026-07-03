from __future__ import annotations

from dataclasses import dataclass, field

from bs4 import BeautifulSoup
from markdownify import markdownify as to_markdown

from app.services.extractor.readability_service import Article


@dataclass(slots=True)
class MarkdownDocument:
    markdown: str
    headings: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)


class MarkdownService:
    def convert(self, article: Article) -> MarkdownDocument:
        markdown = to_markdown(article.html, heading_style="ATX", strip=["script", "style"])
        soup = BeautifulSoup(article.html, "html.parser")
        headings = [heading.get_text(" ", strip=True) for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])]
        images = [image.get("src", "") for image in soup.find_all("img") if image.get("src")]
        links = [link.get("href", "") for link in soup.find_all("a") if link.get("href")]
        return MarkdownDocument(markdown=markdown.strip(), headings=headings, images=images, links=links)
