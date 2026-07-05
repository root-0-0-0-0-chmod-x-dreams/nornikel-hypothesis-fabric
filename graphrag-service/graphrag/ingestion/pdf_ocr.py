"""PDF → Markdown via PyMuPDF text layer + EasyOCR for scanned pages."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import fitz
import numpy as np

from graphrag.ingestion.pdf_extractors import (
    BACKEND_PYMUPDF,
    BookParagraph,
    ExtractionResult,
    _SPACED_LETTERS_RE,
    _normalize_block_text,
    _split_plain_text,
)

if TYPE_CHECKING:
    import easyocr

BACKEND_EASYOCR = "easyocr"

_MIN_NATIVE_CHARS = 80
_MIN_ALPHA_RATIO = 0.35
_RENDER_ZOOM = 3.0
_OCR_LANGS = ("ru", "en")


@dataclass
class OcrConfig:
    langs: tuple[str, ...] = _OCR_LANGS
    render_zoom: float = _RENDER_ZOOM
    min_native_chars: int = _MIN_NATIVE_CHARS
    min_alpha_ratio: float = _MIN_ALPHA_RATIO
    gpu: bool | None = None
    paragraph: bool = True


@dataclass
class PageExtraction:
    page: int
    text: str
    method: str  # "native" | "ocr"
    confidence: float | None = None


@dataclass
class OcrDocumentResult:
    pages: list[PageExtraction]
    source_pdf: Path
    page_count: int
    native_pages: int = 0
    ocr_pages: int = 0
    warnings: list[str] = field(default_factory=list)


_reader: "easyocr.Reader | None" = None
_reader_key: tuple[tuple[str, ...], bool] | None = None


def default_gpu() -> bool:
    import torch

    return bool(torch.cuda.is_available() or torch.backends.mps.is_available())


def ocr_device_name(gpu: bool) -> str:
    import torch

    if not gpu:
        return "cpu"

    if torch.cuda.is_available():
        return "cuda"

    if torch.backends.mps.is_available():
        return "mps"

    return "cpu"


def _resolve_gpu(gpu: bool | None) -> bool:
    if gpu is None:
        return default_gpu()

    return gpu


def _get_reader(langs: tuple[str, ...], gpu: bool) -> "easyocr.Reader":
    global _reader, _reader_key

    key = (langs, gpu)

    if _reader is None or _reader_key != key:
        import easyocr

        _reader = easyocr.Reader(list(langs), gpu=gpu)
        _reader_key = key

    return _reader


def _alpha_ratio(text: str) -> float:
    if not text:
        return 0.0

    letters = sum(1 for ch in text if ch.isalpha())
    return letters / len(text)


def page_needs_ocr(text: str, *, config: OcrConfig) -> bool:
    stripped = text.strip()

    if len(stripped) < config.min_native_chars:
        return True

    if _SPACED_LETTERS_RE.search(stripped):
        return True

    if _alpha_ratio(stripped) < config.min_alpha_ratio:
        return True

    return False


def _preprocess_for_ocr(image: np.ndarray) -> np.ndarray:
    import cv2

    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    else:
        gray = image

    denoised = cv2.fastNlMeansDenoising(gray, h=8)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB)


def _page_to_image(page: fitz.Page, zoom: float) -> np.ndarray:
    matrix = fitz.Matrix(zoom, zoom)
    pixmap = page.get_pixmap(matrix=matrix, alpha=False)
    channels = pixmap.n

    image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.h, pixmap.w, channels)

    if channels == 4:
        image = image[:, :, :3]

    return _preprocess_for_ocr(image)


def _ocr_image(reader: "easyocr.Reader", image: np.ndarray, *, paragraph: bool) -> tuple[str, float]:
    results = reader.readtext(image, paragraph=paragraph, detail=1)

    if not results:
        return "", 0.0

    texts: list[str] = []
    confidences: list[float] = []

    for item in results:
        if not item:
            continue

        if isinstance(item[1], str):
            text = item[1].strip()
            confidence = float(item[2]) if len(item) > 2 else 1.0
        else:
            continue

        if text:
            texts.append(text)
            confidences.append(confidence)

    if not texts:
        return "", 0.0

    avg_conf = sum(confidences) / len(confidences)
    return "\n\n".join(texts), avg_conf


def _extract_native_text(page: fitz.Page) -> str:
    blocks = page.get_text("blocks", sort=True)
    parts: list[str] = []

    for block in blocks:
        if len(block) < 7 or block[6] != 0:
            continue

        text = _normalize_block_text(str(block[4]))

        if text:
            parts.append(text)

    if parts:
        return "\n\n".join(parts)

    return _normalize_block_text(page.get_text("text"))


def _extract_page(
    document: fitz.Document,
    page_index: int,
    *,
    cfg: OcrConfig,
    reader: "easyocr.Reader | None",
) -> tuple[PageExtraction, "easyocr.Reader | None", list[str]]:
    warnings: list[str] = []
    page = document.load_page(page_index)
    native_text = _extract_native_text(page)
    gpu = _resolve_gpu(cfg.gpu)

    if page_needs_ocr(native_text, config=cfg):
        if reader is None:
            reader = _get_reader(cfg.langs, gpu)

        image = _page_to_image(page, cfg.render_zoom)
        ocr_text, confidence = _ocr_image(reader, image, paragraph=cfg.paragraph)
        text = ocr_text.strip() or native_text.strip()
        method = "ocr"

        if confidence and confidence < 0.45:
            warnings.append(f"page {page_index + 1}: low OCR confidence ({confidence:.2f})")
    else:
        text = native_text.strip()
        method = "native"
        confidence = None

    return (
        PageExtraction(page=page_index + 1, text=text, method=method, confidence=confidence),
        reader,
        warnings,
    )


def iter_pdf_pages(
    pdf_path: Path,
    *,
    config: OcrConfig | None = None,
    page_range: tuple[int, int] | None = None,
    skip_until: int = 0,
):
    """Yield PageExtraction one page at a time (for incremental MD export)."""
    cfg = config or OcrConfig()
    document = fitz.open(pdf_path)
    reader: "easyocr.Reader | None" = None

    try:
        page_count = document.page_count
        start = (page_range[0] - 1) if page_range else 0
        end = page_range[1] if page_range else page_count
        start = max(start, 0)
        end = min(end, page_count)

        yield ("meta", page_count)

        for page_index in range(start, end):
            page_no = page_index + 1

            if page_no <= skip_until:
                continue

            page, reader, warnings = _extract_page(
                document,
                page_index,
                cfg=cfg,
                reader=reader,
            )

            for warning in warnings:
                yield ("warning", warning)

            yield ("page", page)
    finally:
        document.close()


def extract_pdf_pages(
    pdf_path: Path,
    *,
    config: OcrConfig | None = None,
    page_range: tuple[int, int] | None = None,
) -> OcrDocumentResult:
    cfg = config or OcrConfig()
    pages: list[PageExtraction] = []
    warnings: list[str] = []
    native_pages = 0
    ocr_pages = 0
    page_count = 0

    for kind, payload in iter_pdf_pages(pdf_path, config=cfg, page_range=page_range):
        if kind == "meta":
            page_count = int(payload)
        elif kind == "warning":
            warnings.append(str(payload))
        elif kind == "page":
            page = payload
            pages.append(page)

            if page.method == "ocr":
                ocr_pages += 1
            else:
                native_pages += 1

    return OcrDocumentResult(
        pages=pages,
        source_pdf=pdf_path,
        page_count=page_count,
        native_pages=native_pages,
        ocr_pages=ocr_pages,
        warnings=warnings,
    )


def _markdown_header(
    pdf_path: Path,
    page_count: int,
    *,
    title: str | None = None,
    native_pages: int = 0,
    ocr_pages: int = 0,
    device: str | None = None,
) -> str:
    heading = title or pdf_path.stem
    device_note = f", device: {device}" if device else ""
    lines = [
        f"# {heading}",
        "",
        f"Источник: `{pdf_path.name}`",
        f"Страниц: {page_count}",
        (
            "Извлечение: PyMuPDF + EasyOCR "
            f"(native: {native_pages}, OCR: {ocr_pages}{device_note})"
        ),
        "",
    ]
    return "\n".join(lines)


def page_to_markdown(page: PageExtraction) -> str:
    if not page.text.strip():
        return ""

    return f"## Страница {page.page}\n\n{page.text.strip()}\n"


def pages_to_markdown(result: OcrDocumentResult, *, title: str | None = None) -> str:
    device = ocr_device_name(_resolve_gpu(None)) if result.ocr_pages else None
    lines = [
        _markdown_header(
            result.source_pdf,
            result.page_count,
            title=title,
            native_pages=result.native_pages,
            ocr_pages=result.ocr_pages,
            device=device,
        ).rstrip(),
    ]

    for page in result.pages:
        block = page_to_markdown(page)

        if block:
            lines.append(block)

    return "\n".join(lines).rstrip() + "\n"


def ocr_result_to_extraction(result: OcrDocumentResult) -> ExtractionResult:
    paragraphs: list[BookParagraph] = []

    for page in result.pages:
        if not page.text.strip():
            continue

        parts = _split_plain_text(page.text)

        for part_index, part in enumerate(parts):
            paragraphs.append(
                BookParagraph(
                    page=page.page,
                    paragraph_index=part_index,
                    text=part,
                    granularity="paragraph" if len(parts) > 1 else "page",
                    backend=BACKEND_EASYOCR if page.method == "ocr" else BACKEND_PYMUPDF,
                )
            )

    return ExtractionResult(
        paragraphs=paragraphs,
        backend=BACKEND_EASYOCR,
        source_pdf=result.source_pdf,
        page_count=result.page_count,
        warnings=result.warnings,
    )


def write_full_markdown(
    result: OcrDocumentResult,
    out_path: Path,
    *,
    title: str | None = None,
) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(pages_to_markdown(result, title=title), encoding="utf-8")
    return out_path
