"""Re-chunk book atoms (OpenDataLoader paragraphs) at different granularities."""

from __future__ import annotations

import re
from dataclasses import replace

from graphrag.constants import PDF_CHUNK_CHARS, PDF_CHUNK_OVERLAP
from graphrag.ingestion.pdf_extractors import BookParagraph

GRANULARITY_SENTENCE = "sentence"
GRANULARITY_PARAGRAPH = "paragraph"
GRANULARITY_PAGE = "page"
GRANULARITY_SECTION = "section"
GRANULARITY_WINDOW = "window"

ALL_GRANULARITIES = (
    GRANULARITY_SENTENCE,
    GRANULARITY_PARAGRAPH,
    GRANULARITY_PAGE,
    GRANULARITY_SECTION,
    GRANULARITY_WINDOW,
)

_SENTENCE_SPLIT_RE = re.compile(
    r"(?<=[.!?…])\s+(?=[«\"А-ЯA-Z0-9])|(?<=\.)\s*\n+\s*(?=[А-ЯA-Z])"
)
_MIN_SENTENCE_CHARS = 40


def rechunk_paragraphs(
    atoms: list[BookParagraph],
    granularity: str,
    *,
    window_size: int = PDF_CHUNK_CHARS,
    window_overlap: int = PDF_CHUNK_OVERLAP,
) -> list[BookParagraph]:
    if granularity == GRANULARITY_PARAGRAPH:
        return _chunk_paragraph(atoms)

    if granularity == GRANULARITY_SENTENCE:
        return _chunk_sentence(atoms)

    if granularity == GRANULARITY_PAGE:
        return _chunk_page(atoms)

    if granularity == GRANULARITY_SECTION:
        return _chunk_section(atoms)

    if granularity == GRANULARITY_WINDOW:
        return _chunk_window(atoms, window_size=window_size, overlap=window_overlap)

    raise ValueError(f"Unknown granularity: {granularity}")


def _body_atoms(atoms: list[BookParagraph]) -> list[BookParagraph]:
    """Paragraph-like units; headings only carry section context."""
    body: list[BookParagraph] = []

    for atom in atoms:
        if atom.element_type == "heading":
            continue

        body.append(atom)

    return body


def _chunk_paragraph(atoms: list[BookParagraph]) -> list[BookParagraph]:
    chunks: list[BookParagraph] = []

    for atom in _body_atoms(atoms):
        chunks.append(
            replace(
                atom,
                granularity=GRANULARITY_PARAGRAPH,
                paragraph_index=len(chunks),
            )
        )

    return chunks


def _chunk_sentence(atoms: list[BookParagraph]) -> list[BookParagraph]:
    chunks: list[BookParagraph] = []
    sentence_counter = 0

    for atom in _body_atoms(atoms):
        sentences = _split_sentences(atom.text)

        for sentence_index, sentence in enumerate(sentences):
            chunks.append(
                BookParagraph(
                    page=atom.page,
                    paragraph_index=atom.paragraph_index,
                    text=sentence,
                    granularity=GRANULARITY_SENTENCE,
                    section=atom.section,
                    element_type="sentence",
                    backend=atom.backend,
                )
            )
            sentence_counter += 1

    for index, chunk in enumerate(chunks):
        chunk.paragraph_index = index

    return chunks


def _chunk_page(atoms: list[BookParagraph]) -> list[BookParagraph]:
    by_page: dict[int, list[str]] = {}
    section_by_page: dict[int, str | None] = {}

    for atom in _body_atoms(atoms):
        by_page.setdefault(atom.page, []).append(atom.text.strip())

        if atom.section:
            section_by_page[atom.page] = atom.section

    chunks: list[BookParagraph] = []

    for page in sorted(by_page):
        text = "\n\n".join(by_page[page]).strip()

        if not text:
            continue

        chunks.append(
            BookParagraph(
                page=page,
                paragraph_index=0,
                text=text,
                granularity=GRANULARITY_PAGE,
                section=section_by_page.get(page),
                element_type="page",
                backend=atoms[0].backend if atoms else "rechunk",
            )
        )

    return chunks


def _chunk_section(atoms: list[BookParagraph]) -> list[BookParagraph]:
    chunks: list[BookParagraph] = []
    buffer: list[str] = []
    current_section: str | None = None
    start_page = 1
    paragraph_index = 0

    def flush() -> None:
        nonlocal paragraph_index, start_page

        text = "\n\n".join(buffer).strip()
        buffer.clear()

        if not text:
            return

        chunks.append(
            BookParagraph(
                page=start_page,
                paragraph_index=paragraph_index,
                text=text,
                granularity=GRANULARITY_SECTION,
                section=current_section,
                element_type="section",
                backend=atoms[0].backend if atoms else "rechunk",
            )
        )
        paragraph_index += 1

    for atom in atoms:
        if atom.element_type == "heading":
            flush()
            current_section = atom.text
            start_page = atom.page
            continue

        if not buffer:
            start_page = atom.page

        buffer.append(atom.text.strip())

    flush()

    return chunks


def _chunk_window(
    atoms: list[BookParagraph],
    *,
    window_size: int,
    overlap: int,
) -> list[BookParagraph]:
    ordered = _body_atoms(atoms)

    if not ordered:
        return []

    full_text = "\n\n".join(atom.text.strip() for atom in ordered)
    parts = _split_window(full_text, window_size, overlap)
    chunks: list[BookParagraph] = []
    cursor = 0

    for index, part in enumerate(parts):
        char_start = full_text.find(part, cursor)
        char_end = char_start + len(part) if char_start >= 0 else None
        cursor = max(char_start, 0)
        page = _page_for_offset(ordered, char_start)
        section = _section_for_offset(ordered, char_start)

        chunks.append(
            BookParagraph(
                page=page,
                paragraph_index=index,
                text=part,
                granularity=GRANULARITY_WINDOW,
                section=section,
                element_type="window",
                backend=ordered[0].backend,
            )
        )

    return chunks


def _split_sentences(text: str) -> list[str]:
    raw = [part.strip() for part in _SENTENCE_SPLIT_RE.split(text) if part.strip()]

    if not raw:
        return [text.strip()] if text.strip() else []

    merged: list[str] = []
    buffer = ""

    for part in raw:
        candidate = f"{buffer} {part}".strip() if buffer else part

        if len(candidate) < _MIN_SENTENCE_CHARS and merged:
            merged[-1] = f"{merged[-1]} {candidate}".strip()
        elif len(candidate) < _MIN_SENTENCE_CHARS:
            buffer = candidate
        else:
            if buffer:
                candidate = f"{buffer} {candidate}".strip()
                buffer = ""

            merged.append(candidate)

    if buffer:
        if merged:
            merged[-1] = f"{merged[-1]} {buffer}".strip()
        else:
            merged.append(buffer)

    return merged


def _split_window(text: str, chunk_size: int, overlap: int) -> list[str]:
    cleaned = text.strip()

    if not cleaned:
        return []

    chunks: list[str] = []
    start = 0

    while start < len(cleaned):
        end = min(start + chunk_size, len(cleaned))
        chunks.append(cleaned[start:end].strip())
        start += chunk_size - overlap

    return [chunk for chunk in chunks if chunk]


def _page_for_offset(atoms: list[BookParagraph], offset: int) -> int:
    cursor = 0

    for atom in atoms:
        piece = atom.text.strip()
        start = cursor
        end = cursor + len(piece)
        cursor = end + 2

        if offset <= end:
            return atom.page

    return atoms[-1].page


def _section_for_offset(atoms: list[BookParagraph], offset: int) -> str | None:
    cursor = 0
    last_section: str | None = None

    for atom in atoms:
        piece = atom.text.strip()
        end = cursor + len(piece)
        cursor = end + 2

        if atom.section:
            last_section = atom.section

        if offset <= end:
            return last_section

    return last_section


def chunk_size_stats(chunks: list[BookParagraph]) -> dict[str, float | int]:
    sizes = sorted(len(chunk.text) for chunk in chunks)

    if not sizes:
        return {
            "chunks": 0,
            "total_chars": 0,
            "avg_chars": 0,
            "p50_chars": 0,
            "p95_chars": 0,
            "min_chars": 0,
            "max_chars": 0,
        }

    total = sum(sizes)
    p50 = sizes[len(sizes) // 2]
    p95 = sizes[int(len(sizes) * 0.95)]

    return {
        "chunks": len(sizes),
        "total_chars": total,
        "avg_chars": round(total / len(sizes), 1),
        "p50_chars": p50,
        "p95_chars": p95,
        "min_chars": sizes[0],
        "max_chars": sizes[-1],
    }


def chunk_plain_text(
    text: str,
    granularity: str = GRANULARITY_PARAGRAPH,
    *,
    backend: str = "external",
) -> list[BookParagraph]:
    """Split arbitrary plain text (web/PDF paste) into retrieval chunks."""
    cleaned = text.strip()

    if not cleaned:
        return []

    blocks = [part.strip() for part in re.split(r"\n\s*\n+", cleaned) if part.strip()]

    if not blocks:
        blocks = [line.strip() for line in cleaned.splitlines() if line.strip()]

    if not blocks:
        return []

    atoms = [
        BookParagraph(
            page=1,
            paragraph_index=index,
            text=block,
            granularity="paragraph",
            backend=backend,
        )
        for index, block in enumerate(blocks)
    ]

    return rechunk_paragraphs(atoms, granularity)
