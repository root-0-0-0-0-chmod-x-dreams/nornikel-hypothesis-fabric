import logging
from typing import Optional

import httpx

from app.config import get_config

logger = logging.getLogger("hypothesis_factory")
config = get_config()


def search_and_extract(query: str, source: str = "scholar") -> str:
    """
    Search the internet and extract content.
    source: "scholar" (Google Scholar), "arxiv", or "web"
    Uses content-extraction service.
    """
    try:
        if source == "scholar":
            url = f"https://scholar.google.com/scholar?q={httpx.URL(query).path if '%' not in query else query}"
        elif source == "arxiv":
            url = f"https://arxiv.org/search/?query={query}&searchtype=all"
        else:
            url = query if query.startswith("http") else f"https://www.google.com/search?q={query}"

        with httpx.Client(timeout=60) as client:
            resp = client.post(
                f"{config.content_extraction_url}/api/v1/extract",
                json={"url": url, "format": "markdown"},
            )

            if resp.status_code == 200:
                data = resp.json()
                content = data.get("markdown", data.get("content", ""))
                if content:
                    return str(content)[:8000]

            elif resp.status_code == 404:
                # Try direct extraction
                resp2 = client.post(
                    f"{config.content_extraction_url}/extract",
                    json={"url": url},
                    timeout=60,
                )
                if resp2.status_code == 200:
                    data2 = resp2.json()
                    return str(data2.get("content", data2.get("text", "")))[:8000]

        return f"[search: no results from {source}]"

    except Exception as e:
        logger.warning("web_search_failed", extra={"source": source, "error": str(e)[:200]})
        return f"[search {source} unavailable: {str(e)[:200]}]"


def search_scholar(query: str) -> str:
    return search_and_extract(query, "scholar")


def search_arxiv(query: str) -> str:
    return search_and_extract(query, "arxiv")


def search_web(query: str) -> str:
    return search_and_extract(query, "web")
