"""PDF → structured paragraphs for book MD chunking (PyMuPDF / OpenDataLoader)."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import fitz

from graphrag.constants import PDF_CHUNK_CHARS, PDF_CHUNK_OVERLAP

BACKEND_PYMUPDF = "pymupdf"
BACKEND_PYMUPDF_BLOCKS = "pymupdf_blocks"
BACKEND_OPENDATALOADER = "opendataloader"

TEXT_ELEMENT_TYPES = frozenset({"paragraph", "heading", "list", "caption"})
_SKIP_MD_IMAGE_RE = re.compile(r"^!\[.*\]\(.*\)\s*$")
_PAGE_SPLIT_RE = re.compile(r"^---page-(\d+)---\s*$", re.MULTILINE)
_SPACED_LETTERS_RE = re.compile(r"(?:\b\w\s){4,}\w\b")


@dataclass
class BookParagraph:
    page: int
    paragraph_index: int
    text: str
    granularity: str = "paragraph"
    section: str | None = None
    element_type: str = "paragraph"
    backend: str = BACKEND_PYMUPDF


@dataclass
class ExtractionResult:
    paragraphs: list[BookParagraph]
    backend: str
    source_pdf: Path
    page_count: int = 0
    warnings: list[str] = field(default_factory=list)


def extract_pdf(
    pdf_path: Path,
    *,
    backend: str = BACKEND_OPENDATALOADER,
    work_dir: Path | None = None,
) -> ExtractionResult:
    if backend == BACKEND_OPENDATALOADER:
        return _extract_opendataloader(pdf_path, work_dir=work_dir)

    if backend == BACKEND_PYMUPDF_BLOCKS:
        return _extract_pymupdf_blocks(pdf_path)

    return _extract_pymupdf_text(pdf_path)


def java_available() -> bool:
    try:
        proc = subprocess.run(
            ["java", "-version"],
            capture_output=True,
            text=True,
            check=False,
        )

        return proc.returncode == 0
    except OSError:
        return False


def _extract_pymupdf_text(pdf_path: Path) -> ExtractionResult:
    document = fitz.open(pdf_path)
    paragraphs: list[BookParagraph] = []
    warnings: list[str] = []
    page_count = 0

    try:
        page_count = document.page_count

        for page_index in range(page_count):
            page = document.load_page(page_index)
            page_text = page.get_text("text")
            parts = _split_plain_text(page_text)

            for part_index, part in enumerate(parts):
                paragraphs.append(
                    BookParagraph(
                        page=page_index + 1,
                        paragraph_index=part_index,
                        text=part,
                        granularity="paragraph" if len(parts) > 1 else "page",
                        backend=BACKEND_PYMUPDF,
                    )
                )
    finally:
        document.close()

    return ExtractionResult(
        paragraphs=paragraphs,
        backend=BACKEND_PYMUPDF,
        source_pdf=pdf_path,
        page_count=page_count,
        warnings=warnings,
    )


def _extract_pymupdf_blocks(pdf_path: Path) -> ExtractionResult:
    document = fitz.open(pdf_path)
    paragraphs: list[BookParagraph] = []
    page_count = 0

    try:
        page_count = document.page_count

        for page_index in range(page_count):
            page = document.load_page(page_index)
            blocks = page.get_text("blocks", sort=True)
            part_index = 0

            for block in blocks:
                if len(block) < 7 or block[6] != 0:
                    continue

                text = _normalize_block_text(str(block[4]))

                if len(text) < 20:
                    continue

                paragraphs.append(
                    BookParagraph(
                        page=page_index + 1,
                        paragraph_index=part_index,
                        text=text,
                        granularity="paragraph",
                        backend=BACKEND_PYMUPDF_BLOCKS,
                    )
                )
                part_index += 1
    finally:
        document.close()

    return ExtractionResult(
        paragraphs=paragraphs,
        backend=BACKEND_PYMUPDF_BLOCKS,
        source_pdf=pdf_path,
        page_count=page_count,
    )


def _extract_opendataloader(pdf_path: Path, work_dir: Path | None) -> ExtractionResult:
    if not java_available():
        raise RuntimeError(
            "OpenDataLoader requires Java 11+. Install: brew install openjdk@17"
        )

    import opendataloader_pdf

    tmp_root = work_dir or pdf_path.parent / ".odl_cache"
    tmp_root.mkdir(parents=True, exist_ok=True)
    stem = pdf_path.stem
    json_path = tmp_root / f"{stem}.json"
    md_path = tmp_root / f"{stem}.md"

    if not json_path.is_file():
        opendataloader_pdf.convert(
            input_path=[str(pdf_path)],
            output_dir=str(tmp_root),
            format="markdown,json",
            markdown_page_separator="---page-%page-number%---",
            image_output="off",
            quiet=True,
        )

    warnings: list[str] = []
    page_count = 0
    paragraphs: list[BookParagraph] = []

    if json_path.is_file():
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        page_count = int(payload.get("number of pages") or 0)
        section = ""
        per_page_index: dict[int, int] = {}

        for element in _walk_odl_elements(payload.get("kids") or []):
            element_type = str(element.get("type") or "")

            if element_type not in TEXT_ELEMENT_TYPES:
                continue

            content = str(element.get("content") or "").strip()

            if not content or _looks_like_noise(content):
                continue

            page = int(element.get("page number") or 1)
            idx = per_page_index.get(page, 0)
            per_page_index[page] = idx + 1

            if element_type == "heading":
                section = _normalize_block_text(content)

            paragraphs.append(
                BookParagraph(
                    page=page,
                    paragraph_index=idx,
                    text=content,
                    granularity="heading" if element_type == "heading" else "paragraph",
                    section=section or None,
                    element_type=element_type,
                    backend=BACKEND_OPENDATALOADER,
                )
            )
    elif md_path.is_file():
        warnings.append("JSON missing; falling back to OpenDataLoader markdown split")
        raw_md = md_path.read_text(encoding="utf-8")
        page_count, paragraphs = _paragraphs_from_odl_markdown(raw_md)
    else:
        raise FileNotFoundError(f"OpenDataLoader produced no output for {pdf_path.name}")

    return ExtractionResult(
        paragraphs=paragraphs,
        backend=BACKEND_OPENDATALOADER,
        source_pdf=pdf_path,
        page_count=page_count,
        warnings=warnings,
    )


def _walk_odl_elements(nodes: list) -> Iterator[dict]:
    for node in nodes:
        if not isinstance(node, dict):
            continue

        yield node

        for child in node.get("kids") or []:
            if isinstance(child, dict):
                yield from _walk_odl_elements([child])
            elif isinstance(child, list):
                yield from _walk_odl_elements(child)


def _paragraphs_from_odl_markdown(raw_md: str) -> tuple[int, list[BookParagraph]]:
    paragraphs: list[BookParagraph] = []
    page = 1
    per_page_index: dict[int, int] = {}
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal page
        text = "\n".join(current_lines).strip()
        current_lines.clear()

        if not text or _looks_like_noise(text):
            return

        idx = per_page_index.get(page, 0)
        per_page_index[page] = idx + 1
        paragraphs.append(
            BookParagraph(
                page=page,
                paragraph_index=idx,
                text=text,
                granularity="paragraph",
                backend=BACKEND_OPENDATALOADER,
            )
        )

    for line in raw_md.splitlines():
        page_match = _PAGE_SPLIT_RE.match(line.strip())

        if page_match:
            flush()
            page = int(page_match.group(1))
            continue

        if _SKIP_MD_IMAGE_RE.match(line.strip()):
            continue

        if not line.strip():
            flush()
            continue

        cleaned = re.sub(r"^#+\s*", "", line).strip()

        if cleaned:
            current_lines.append(cleaned)

    flush()

    return max(per_page_index) if per_page_index else page, paragraphs


def _split_plain_text(text: str, chunk_size: int = PDF_CHUNK_CHARS, overlap: int = PDF_CHUNK_OVERLAP) -> list[str]:
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


def _normalize_block_text(text: str) -> str:
    collapsed = re.sub(r"\s+", " ", text).strip()
    de_spaced = re.sub(r"(?<=\S)\s(?=\S)", "", collapsed) if _SPACED_LETTERS_RE.search(collapsed) else collapsed

    return de_spaced.strip()


def _looks_like_noise(text: str) -> bool:
    lowered = text.lower()

    if len(text) < 8:
        return True

    if lowered.startswith("!["):
        return True

    if re.fullmatch(r"[\d\W]+", text):
        return True

    return False


def extraction_quality_metrics(result: ExtractionResult) -> dict[str, float | int]:
    texts = [paragraph.text for paragraph in result.paragraphs]
    total_chars = sum(len(text) for text in texts)
    spaced_hits = sum(1 for text in texts if _SPACED_LETTERS_RE.search(text))

    pages_with_text = {paragraph.page for paragraph in result.paragraphs}

    return {
        "paragraphs": len(result.paragraphs),
        "total_chars": total_chars,
        "avg_chars": round(total_chars / max(len(texts), 1), 1),
        "pages_with_text": len(pages_with_text),
        "page_count": result.page_count,
        "empty_pages": max(result.page_count - len(pages_with_text), 0),
        "spaced_letter_artifacts": spaced_hits,
        "min_para_chars": min((len(text) for text in texts), default=0),
        "max_para_chars": max((len(text) for text in texts), default=0),
    }


def clear_odl_cache(data_root: Path) -> None:
    cache = data_root / "Дополнительные материалы" / ".odl_cache"

    if cache.is_dir():
        shutil.rmtree(cache)
