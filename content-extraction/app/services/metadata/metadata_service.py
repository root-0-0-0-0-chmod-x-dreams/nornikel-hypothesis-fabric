from __future__ import annotations

from bs4 import BeautifulSoup

from app.services.browser.browser_service import RenderedPage
from app.schemas.response import Metadata


class MetadataService:
    def extract(self, page: RenderedPage) -> Metadata:
        soup = BeautifulSoup(page.html, "html.parser")

        def meta(*names: str) -> str | None:
            for name in names:
                tag = soup.find("meta", attrs={"name": name}) or soup.find("meta", attrs={"property": name})
                if tag and tag.get("content"):
                    return tag["content"].strip()
            return None

        canonical_tag = soup.find("link", attrs={"rel": lambda value: value and "canonical" in value})
        language = soup.html.get("lang") if soup.html else None

        return Metadata(
            title=page.title,
            description=meta("description", "og:description", "twitter:description"),
            author=meta("author", "article:author", "og:author"),
            site_name=meta("og:site_name", "application-name"),
            language=language,
            canonical_url=canonical_tag.get("href") if canonical_tag else None,
            headers=page.headers,
            cookies=page.cookies,
        )
