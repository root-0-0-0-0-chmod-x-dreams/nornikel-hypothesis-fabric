"""Convert monolithic literature MD into per-paragraph chunked MD directories."""

from __future__ import annotations

import json
from pathlib import Path

from graphrag.ingestion.excel_parser import _slugify
from graphrag.ingestion.md_monolithic_parser import _split_pages, _split_paragraphs


def frontmatter(meta: dict) -> str:
    lines = [f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in meta.items()]
    return "---\n" + "\n".join(lines) + "\n---\n"


def write_monolithic_to_chunked_dir(monolithic_path: Path, out_root: Path) -> int:
    """Write OpenDataLoader-style chunk files from monolithic OCR/export MD."""
    raw = monolithic_path.read_text(encoding="utf-8").strip()

    if not raw:
        return 0

    doc_id = _slugify(monolithic_path.stem)
    source_pdf = monolithic_path.stem.replace("_", "-") + ".pdf"
    title = monolithic_path.stem

    for line in raw.splitlines()[:8]:
        stripped = line.strip()

        if stripped.startswith("# "):
            title = stripped.lstrip("# ").strip()

        if stripped.startswith("Источник:"):
            source_pdf = stripped.split(":", 1)[1].strip().strip("`")

    book_dir = out_root / doc_id
    book_dir.mkdir(parents=True, exist_ok=True)

    book_meta = {
        "doc_id": doc_id,
        "title": title,
        "source": source_pdf,
        "original_pdf": source_pdf,
        "original_format": "pdf",
        "extractor": "monolithic_md",
        "granularity": "paragraph",
    }

    (book_dir / "_book.meta.md").write_text(frontmatter(book_meta) + "\n", encoding="utf-8")

    written = 0
    paragraph_index = 0

    for page, page_text in _split_pages(raw):
        for paragraph in _split_paragraphs(page_text):
            paragraph_index += 1
            chunk_meta = {
                **book_meta,
                "chunk_type": "book_text",
                "page": page,
                "paragraph_index": paragraph_index,
                "granularity": "paragraph",
                "element_type": "paragraph",
                "chunk_id": f"book_{doc_id}_paragraph_p{page}_i{paragraph_index}",
            }
            filename = f"p{page:03d}_para_{paragraph_index:03d}.md"
            (book_dir / filename).write_text(
                frontmatter(chunk_meta) + paragraph.strip() + "\n",
                encoding="utf-8",
            )
            written += 1

    return written


def chunked_dir_needs_rebuild(book_dir: Path, *, min_chunks: int = 10) -> bool:
    if not book_dir.is_dir():
        return True

    chunk_files = [
        path
        for path in book_dir.glob("*.md")
        if not path.name.startswith("_")
    ]

    return len(chunk_files) < min_chunks
