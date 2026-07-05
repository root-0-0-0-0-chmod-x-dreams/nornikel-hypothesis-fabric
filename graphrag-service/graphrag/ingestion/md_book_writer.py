"""Write book paragraphs as chunked Markdown files."""

from __future__ import annotations

import json
from pathlib import Path

from graphrag.constants import BOOK_CHUNK_GRANULARITY
from graphrag.ingestion.book_chunking import rechunk_paragraphs
from graphrag.ingestion.excel_parser import _slugify
from graphrag.ingestion.pdf_extractors import BookParagraph, ExtractionResult


def doc_id_from_pdf(path: Path) -> str:
    return _slugify(path.stem)


def frontmatter(meta: dict) -> str:
    lines = [f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in meta.items()]
    return "---\n" + "\n".join(lines) + "\n---\n"


def write_book_md_chunks(
    result: ExtractionResult,
    out_root: Path,
    *,
    title: str | None = None,
    author: str | None = None,
    granularity: str = BOOK_CHUNK_GRANULARITY,
) -> int:
    pdf_path = result.source_pdf
    doc_id = doc_id_from_pdf(pdf_path)
    book_dir = out_root / doc_id
    book_dir.mkdir(parents=True, exist_ok=True)

    paragraphs = rechunk_paragraphs(result.paragraphs, granularity)

    book_meta = {
        "doc_id": doc_id,
        "title": title or pdf_path.stem,
        "source": pdf_path.name,
        "original_pdf": pdf_path.name,
        "extractor": result.backend,
    }

    if author:
        book_meta["author"] = author

    book_meta["granularity"] = granularity

    (book_dir / "_book.meta.md").write_text(
        frontmatter(book_meta) + "\n",
        encoding="utf-8",
    )

    written = 0

    for paragraph in paragraphs:
        chunk_meta = {
            **book_meta,
            "chunk_type": "book_text",
            "page": paragraph.page,
            "paragraph_index": paragraph.paragraph_index,
            "granularity": paragraph.granularity,
            "element_type": paragraph.element_type,
            "chunk_id": _chunk_id(doc_id, paragraph),
        }

        if paragraph.section:
            chunk_meta["section"] = paragraph.section

        filename = f"p{paragraph.page:03d}_para_{paragraph.paragraph_index:03d}.md"
        (book_dir / filename).write_text(
            frontmatter(chunk_meta) + paragraph.text.strip() + "\n",
            encoding="utf-8",
        )
        written += 1

    return written


def _chunk_id(doc_id: str, paragraph: BookParagraph) -> str:
    parts = ["book", doc_id, paragraph.granularity, f"p{paragraph.page}", f"i{paragraph.paragraph_index}"]

    if paragraph.granularity == "heading":
        parts.append("h")

    return "_".join(parts)
