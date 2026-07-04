"""Parse monolithic literature MD (PyMuPDF/OCR export with ## Страница N)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from graphrag.ingestion.excel_parser import _slugify
from graphrag.models import Chunk

_PAGE_HEADING_RE = re.compile(r"^##\s+Страница\s+(\d+)\s*$", re.MULTILINE)


@dataclass
class MonolithicParseResult:
    chunks: list[Chunk]
    books: list[str]


def parse_literature_md(literature_root: Path) -> MonolithicParseResult:
    """Load *.md from service data/literature/ (one file = one book)."""
    if not literature_root.is_dir():
        return MonolithicParseResult(chunks=[], books=[])

    chunks: list[Chunk] = []
    books: list[str] = []

    for path in sorted(literature_root.glob("*.md")):
        if path.name.startswith("_") or path.name.lower() == "readme.md":
            continue

        book_chunks = _parse_monolithic_file(path)
        chunks.extend(book_chunks)

        if book_chunks:
            books.append(path.stem)

    return MonolithicParseResult(chunks=chunks, books=sorted(books))


def _parse_monolithic_file(path: Path) -> list[Chunk]:
    raw = path.read_text(encoding="utf-8").strip()

    if not raw:
        return []

    doc_id = _slugify(path.stem)
    source_pdf = path.stem.replace("_", "-") + ".pdf"
    title = path.stem

    for line in raw.splitlines()[:8]:
        stripped = line.strip()

        if stripped.startswith("# "):
            title = stripped.lstrip("# ").strip()

        if stripped.startswith("Источник:"):
            source_pdf = stripped.split(":", 1)[1].strip().strip("`")

    sections = _split_pages(raw)
    chunks: list[Chunk] = []
    paragraph_index = 0

    for page, page_text in sections:
        for paragraph in _split_paragraphs(page_text):
            paragraph_index += 1
            chunk_id = f"book_{doc_id}_p{page:03d}_para_{paragraph_index:04d}"
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    text=paragraph,
                    summary=title,
                    source=source_pdf,
                    section=f"Страница {page}",
                    chunk_type="book_text",
                    graph_node_ids=[],
                    metadata={
                        "doc_id": doc_id,
                        "title": title,
                        "source": source_pdf,
                        "original_format": "pdf",
                        "extractor": "monolithic_md",
                        "page": page,
                        "paragraph_index": paragraph_index,
                        "granularity": "paragraph",
                        "md_path": str(path),
                    },
                )
            )

    return chunks


def _split_pages(raw: str) -> list[tuple[int, str]]:
    matches = list(_PAGE_HEADING_RE.finditer(raw))

    if not matches:
        return [(1, raw)]

    sections: list[tuple[int, str]] = []

    for index, match in enumerate(matches):
        page = int(match.group(1))
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
        text = raw[start:end].strip()

        if text:
            sections.append((page, text))

    return sections


def _split_paragraphs(text: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    merged: list[str] = []

    for part in parts:
        if merged and len(part) < 80 and not part.endswith((".", "!", "?", "»", "\"")):
            merged[-1] = f"{merged[-1]}\n{part}"
            continue

        merged.append(part)

    return merged
