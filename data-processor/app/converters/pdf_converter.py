from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from docling.document_converter import DocumentConverter

from app.image_manager import get_image_manager
from app.models import ConvertResult
from app.utils import FileType

logger = logging.getLogger("data_processor")


def convert_pdf(file_path: Path, original_filename: str) -> ConvertResult:
    errors: List[str] = []
    warnings: List[str] = []

    try:
        converter = DocumentConverter()
        result = converter.convert(str(file_path))
        md_text = result.document.export_to_markdown()

        image_manager = get_image_manager()

        doc_images_dir = file_path.parent / file_path.stem
        images_extracted = 0

        if doc_images_dir.exists() and doc_images_dir.is_dir():
            md_text, images_extracted = image_manager.rewrite_markdown_images(
                md_content=md_text,
                source_images_dir=doc_images_dir,
                prefix="pdf",
            )
            shutil.rmtree(doc_images_dir, ignore_errors=True)

        return ConvertResult(
            success=True,
            original_filename=original_filename,
            file_type=FileType.PDF.value,
            markdown_content=md_text,
            images_extracted=images_extracted,
            warnings=warnings,
            metadata={"pages": getattr(result.document, "num_pages", None)},
        )

    except ImportError:
        _fallback = _try_pdf_fallback(file_path, original_filename)
        if _fallback:
            return _fallback
        return ConvertResult(
            success=False,
            original_filename=original_filename,
            file_type=FileType.PDF.value,
            errors=["docling not installed. Install: pip install docling"],
        )
    except Exception as e:
        logger.exception("pdf_conversion_failed")
        errors.append(str(e))
        return ConvertResult(
            success=False,
            original_filename=original_filename,
            file_type=FileType.PDF.value,
            errors=errors,
        )


def _try_pdf_fallback(file_path: Path, original_filename: str) -> ConvertResult | None:
    try:
        import fitz
        doc = fitz.open(str(file_path))
        md_parts = []
        image_manager = get_image_manager()
        images_extracted = 0

        for page_num, page in enumerate(doc, 1):
            md_parts.append(f"\n## Page {page_num}\n")
            md_parts.append(page.get_text())

            for img_index, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                base_image = doc.extract_image(xref)
                if base_image:
                    img_bytes = base_image["image"]
                    ext = base_image["ext"]
                    ref = image_manager.add_image_bytes(img_bytes, ext, "pdf")
                    images_extracted += 1
                    md_parts.append(f"![page_{page_num}_img_{img_index}]({ref})\n")

        doc.close()
        return ConvertResult(
            success=True,
            original_filename=original_filename,
            file_type=FileType.PDF.value,
            markdown_content="\n".join(md_parts),
            images_extracted=images_extracted,
            metadata={"pages": page_num},
        )
    except ImportError:
        return None
