from typing import Any

from pydantic import BaseModel, Field


class Metadata(BaseModel):
    title: str | None = None
    description: str | None = None
    author: str | None = None
    site_name: str | None = None
    language: str | None = None
    canonical_url: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    cookies: list[dict[str, Any]] = Field(default_factory=list)


class ExtractResponse(BaseModel):
    url: str
    title: str | None = None
    markdown: str
    text: str
    excerpt: str | None = None
    byline: str | None = None
    html: str
    metadata: Metadata
    status_code: int | None = None
