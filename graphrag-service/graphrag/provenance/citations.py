"""Structured citations from chunks and graph evidence edges."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from graphrag.models import Chunk
from graphrag.vector_protocol import VectorStoreProtocol

_PDF_CHUNK_RE = re.compile(r"^pdf_(?P<doc>.+)_p(?P<page>\d+)_(?P<part>\d+)$")


@dataclass
class Citation:
    source: str
    source_type: str
    chunk_id: str
    excerpt: str
    page: int | None = None
    paragraph_index: int | None = None
    excel_row: int | None = None
    excel_cell: str | None = None
    sheet: str | None = None
    source_url: str | None = None
    external: bool = False
    highlight: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = {key: value for key, value in asdict(self).items() if value not in (None, "", [])}
        payload["display_ref"] = self.display_ref()

        return payload

    def display_ref(self) -> str:
        parts = [self.source]

        if self.page is not None:
            parts.append(f"стр. {self.page}")

        if self.paragraph_index is not None:
            parts.append(f"§{self.paragraph_index + 1}")

        if self.excel_cell:
            parts.append(f"ячейка {self.excel_cell}")

        if self.source_url and self.source_type == "external":
            parts.append(self.source_url)

        if self.sheet:
            parts.append(f"лист «{self.sheet}»")

        return ", ".join(parts)


def citation_from_chunk(
    chunk: Chunk,
    *,
    highlight: str = "",
    excerpt_chars: int = 320,
) -> Citation:
    meta = chunk.metadata or {}
    source_type = _source_type(chunk.chunk_type)
    page = meta.get("page")
    paragraph_index = meta.get("paragraph_index")

    if paragraph_index is None:
        match = _PDF_CHUNK_RE.match(chunk.chunk_id)

        if match:
            page = page or int(match.group("page"))
            paragraph_index = int(match.group("part"))

    metal = meta.get("metal")
    excel_cell = meta.get("excel_cell_ni") if metal == "Ni" else meta.get("excel_cell_cu")
    if not excel_cell:
        excel_cell = meta.get("excel_cell")

    excerpt = chunk.text.strip()

    if len(excerpt) > excerpt_chars:
        excerpt = excerpt[: excerpt_chars - 1] + "…"

    return Citation(
        source=chunk.source or chunk.chunk_id,
        source_type=source_type,
        chunk_id=chunk.chunk_id,
        excerpt=excerpt,
        page=int(page) if page is not None else None,
        paragraph_index=int(paragraph_index) if paragraph_index is not None else None,
        excel_row=int(meta["excel_row"]) if meta.get("excel_row") else None,
        excel_cell=str(excel_cell) if excel_cell else None,
        sheet=str(meta["sheet"]) if meta.get("sheet") else None,
        source_url=chunk.source_url,
        external=chunk.external,
        highlight=highlight,
    )


def highlight_overlap(query: str, text: str, max_len: int = 120) -> str:
    query_tokens = {token for token in re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]+", query.lower()) if len(token) > 3}
    lowered = text.lower()

    for token in sorted(query_tokens, key=len, reverse=True):
        index = lowered.find(token)

        if index >= 0:
            start = max(0, index - 40)
            end = min(len(text), index + len(token) + 80)
            snippet = text[start:end].strip()

            if len(snippet) > max_len:
                snippet = snippet[: max_len - 1] + "…"

            return snippet

    return text[:max_len] + ("…" if len(text) > max_len else "")


def citation_for_chunk_id(
    vectors: VectorStoreProtocol,
    chunk_id: str,
    *,
    query: str = "",
) -> Citation | None:
    chunk = vectors.get(chunk_id)

    if chunk is None:
        return None

    highlight = highlight_overlap(query, chunk.text) if query else ""

    return citation_from_chunk(chunk, highlight=highlight)


def _source_type(chunk_type: str) -> str:
    mapping = {
        "excel_bucket": "excel",
        "pdf_text": "pdf",
        "book_text": "book",
        "scheme_caption": "scheme",
        "constraint_regulation": "regulation",
        "constraint_budget": "constraint",
        "constraint_example": "example",
        "external_text": "external",
    }

    return mapping.get(chunk_type, chunk_type)
