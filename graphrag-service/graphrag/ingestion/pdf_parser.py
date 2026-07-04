"""PDF text extraction and chunking."""

from __future__ import annotations

import re
from pathlib import Path

import fitz

from graphrag.constants import PDF_CHUNK_CHARS, PDF_CHUNK_OVERLAP
from graphrag.models import Chunk


def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    cleaned = "\n".join(line.strip() for line in text.splitlines() if line.strip())

    if not cleaned:
        return []

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", cleaned) if part.strip()]

    if len(paragraphs) > 1:
        return paragraphs

    chunks: list[str] = []
    start = 0

    while start < len(cleaned):
        end = min(start + chunk_size, len(cleaned))
        chunks.append(cleaned[start:end])
        start += chunk_size - overlap

    return chunks


def parse_pdf_file(path: Path) -> list[Chunk]:
    document = fitz.open(path)
    chunks: list[Chunk] = []

    try:
        for page_index in range(document.page_count):
            page = document.load_page(page_index)
            page_text = page.get_text("text")

            for part_index, part in enumerate(
                _split_text(page_text, PDF_CHUNK_CHARS, PDF_CHUNK_OVERLAP)
            ):
                chunk_id = f"pdf_{path.stem}_p{page_index + 1}_{part_index}"
                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        text=part,
                        summary=path.stem,
                        source=path.name,
                        chunk_type="pdf_text",
                        metadata={
                            "page": page_index + 1,
                            "paragraph_index": part_index,
                            "doc_id": path.stem,
                        },
                    )
                )
    finally:
        document.close()

    return chunks
