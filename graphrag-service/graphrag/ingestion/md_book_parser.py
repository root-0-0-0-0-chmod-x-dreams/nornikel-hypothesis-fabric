"""Parse book literature from Markdown chunks (Дополнительные материалы)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from graphrag.ingestion.excel_parser import _slugify
from graphrag.ingestion.md_frontmatter import split_chunk_blocks, split_frontmatter
from graphrag.models import Chunk

BOOK_MD_ROOT = "Дополнительные материалы/md"
GRANULARITY_VALUES = frozenset({"paragraph", "sentence", "page", "section", "window"})


@dataclass
class BookParseResult:
    chunks: list[Chunk]
    books: list[str]


def parse_md_books(data_root: Path) -> BookParseResult:
    """Load book chunks from Дополнительные материалы/md."""
    books_root = data_root / BOOK_MD_ROOT

    if not books_root.is_dir():
        return BookParseResult(chunks=[], books=[])

    chunks: list[Chunk] = []
    books: list[str] = []

    for book_dir in sorted(path for path in books_root.iterdir() if path.is_dir()):
        book_chunks = _parse_book_directory(book_dir)
        chunks.extend(book_chunks)

        if book_chunks:
            books.append(book_dir.name)

    for book_file in sorted(books_root.glob("*.md")):
        if book_file.name.startswith("_"):
            continue

        chunks.extend(_parse_multi_chunk_book_file(book_file))
        books.append(book_file.stem)

    return BookParseResult(chunks=chunks, books=sorted(set(books)))


def parse_md_book_chunk_file(path: Path, *, book_meta: dict | None = None) -> Chunk | None:
    return parse_md_book_chunk_raw(
        path.read_text(encoding="utf-8"),
        source_label=str(path),
        book_meta=book_meta,
    )


def parse_md_book_raw(raw: str, *, source_label: str = "upload.md") -> list[Chunk]:
    """Parse one MD document (single or multi-chunk) into book/general chunks."""
    meta, body = split_frontmatter(raw)
    book_meta = {
        "doc_id": meta.get("doc_id") or Path(source_label).stem,
        "title": meta.get("title") or Path(source_label).stem,
        "source": meta.get("source") or Path(source_label).name,
        **meta,
    }

    blocks = split_chunk_blocks(body)

    if not blocks:
        chunk = _chunk_from_parts(Path(source_label), book_meta, body)

        return [chunk] if chunk else []

    chunks: list[Chunk] = []

    for index, (block_meta, text) in enumerate(blocks):
        merged = {**book_meta, **block_meta}

        if "chunk_index" not in merged:
            merged["chunk_index"] = index

        chunk = _chunk_from_parts(Path(source_label), merged, text, suffix=str(index))

        if chunk is not None:
            chunks.append(chunk)

    return chunks


def parse_md_book_chunk_raw(
    raw: str,
    *,
    source_label: str = "upload.md",
    book_meta: dict | None = None,
) -> Chunk | None:
    meta, body = split_frontmatter(raw)
    merged = {**(book_meta or {}), **meta}

    if not body.strip():
        return None

    return _chunk_from_parts(Path(source_label), merged, body)


def _parse_book_directory(book_dir: Path) -> list[Chunk]:
    book_meta_path = book_dir / "_book.meta.md"

    if book_meta_path.is_file():
        book_meta, _ = split_frontmatter(book_meta_path.read_text(encoding="utf-8"))
    else:
        book_meta = {"doc_id": book_dir.name, "title": book_dir.name}

    chunks: list[Chunk] = []

    for path in sorted(book_dir.glob("*.md")):
        if path.name.startswith("_"):
            continue

        chunk = parse_md_book_chunk_file(path, book_meta=book_meta)

        if chunk is not None:
            chunks.append(chunk)

    return chunks


def _parse_multi_chunk_book_file(path: Path) -> list[Chunk]:
    raw = path.read_text(encoding="utf-8")
    book_meta, body = split_frontmatter(raw)
    book_meta.setdefault("doc_id", path.stem)
    book_meta.setdefault("title", path.stem)
    book_meta.setdefault("source", path.name)

    blocks = split_chunk_blocks(body)

    if not blocks:
        chunk = _chunk_from_parts(path, book_meta, body)

        return [chunk] if chunk else []

    chunks: list[Chunk] = []

    for index, (block_meta, text) in enumerate(blocks):
        merged = {**book_meta, **block_meta}

        if "chunk_index" not in merged:
            merged["chunk_index"] = index

        chunk = _chunk_from_parts(path, merged, text, suffix=str(index))

        if chunk is not None:
            chunks.append(chunk)

    return chunks


def _chunk_from_parts(
    path: Path,
    meta: dict,
    body: str,
    *,
    suffix: str | None = None,
) -> Chunk | None:
    text = body.strip()

    if not text:
        return None

    doc_id = str(meta.get("doc_id") or path.parent.name or path.stem)
    page = _optional_int(meta.get("page"))
    paragraph_index = _optional_int(meta.get("paragraph_index"))
    sentence_index = _optional_int(meta.get("sentence_index"))
    chunk_index = _optional_int(meta.get("chunk_index"))
    granularity = str(meta.get("granularity") or _infer_granularity(meta))

    chunk_id = str(
        meta.get("chunk_id")
        or _default_chunk_id(
            doc_id,
            page=page,
            paragraph_index=paragraph_index,
            sentence_index=sentence_index,
            chunk_index=chunk_index,
            suffix=suffix,
        )
    )

    source = str(meta.get("source") or meta.get("title") or doc_id)
    section = str(meta.get("section") or "")

    metadata = {
        "doc_id": doc_id,
        "title": meta.get("title"),
        "author": meta.get("author"),
        "page": page,
        "paragraph_index": paragraph_index,
        "sentence_index": sentence_index,
        "chunk_index": chunk_index,
        "granularity": granularity,
        "section": section or None,
        "md_path": str(path),
        "char_start": _optional_int(meta.get("char_start")),
        "char_end": _optional_int(meta.get("char_end")),
        "original_pdf": meta.get("original_pdf"),
    }
    metadata = {key: value for key, value in metadata.items() if value is not None}

    return Chunk(
        chunk_id=chunk_id,
        text=text,
        summary=str(meta.get("summary") or section or source),
        source=source,
        section=section,
        chunk_type=str(meta.get("chunk_type") or "book_text"),
        graph_node_ids=list(meta.get("graph_node_ids") or []),
        metadata=metadata,
    )


def _default_chunk_id(
    doc_id: str,
    *,
    page: int | None,
    paragraph_index: int | None,
    sentence_index: int | None,
    chunk_index: int | None,
    suffix: str | None,
) -> str:
    parts = ["book", _slugify(doc_id)]

    if page is not None:
        parts.append(f"p{page}")

    if paragraph_index is not None:
        parts.append(f"para{paragraph_index}")

    if sentence_index is not None:
        parts.append(f"sent{sentence_index}")

    if chunk_index is not None and paragraph_index is None:
        parts.append(f"c{chunk_index}")

    if suffix is not None and paragraph_index is None and chunk_index is None:
        parts.append(suffix)

    return "_".join(parts)


def _infer_granularity(meta: dict) -> str:
    if meta.get("sentence_index") is not None:
        return "sentence"

    if meta.get("paragraph_index") is not None:
        return "paragraph"

    if meta.get("page") is not None:
        return "page"

    return "paragraph"


def _optional_int(value) -> int | None:
    if value is None or value == "":
        return None

    return int(value)
