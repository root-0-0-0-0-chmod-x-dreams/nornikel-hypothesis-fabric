from __future__ import annotations

import io
import logging
import re
import shutil
import tempfile
from pathlib import Path
from typing import List

from app.config import get_config
from app.image_manager import get_image_manager
from app.models import ConvertResult
from app.utils import FileType

logger = logging.getLogger("data_processor")

MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)", re.IGNORECASE)


def _ensure_java() -> None:
    import os

    java_home = os.environ.get("JAVA_HOME", "")
    if java_home:
        java_bin = os.path.join(java_home, "bin")
        if java_bin not in os.environ.get("PATH", ""):
            os.environ["PATH"] = os.pathsep.join([java_bin, os.environ.get("PATH", "")])

    candidates = [
        r"D:\java\jdk-21",
        r"C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot",
        r"C:\Program Files\Java\jdk-21",
    ]
    for candidate in candidates:
        java_exe = os.path.join(candidate, "bin", "java.exe")
        if os.path.exists(java_exe) and not java_home:
            os.environ["JAVA_HOME"] = candidate
            os.environ["PATH"] = os.pathsep.join([
                os.path.join(candidate, "bin"),
                os.environ.get("PATH", ""),
            ])
            logger.info("java_auto_detected", extra={"JAVA_HOME": candidate})
            break


def convert_pdf(file_path: Path, original_filename: str) -> ConvertResult:
    config = get_config()
    if config.pdf_library == "pymupdf":
        return _convert_pymupdf(file_path, original_filename)
    return _convert_opendataloader(file_path, original_filename)


def _convert_opendataloader(file_path: Path, original_filename: str) -> ConvertResult:
    errors: List[str] = []
    warnings: List[str] = []
    config = get_config()

    _ensure_java()

    try:
        import opendataloader_pdf
    except ImportError:
        return ConvertResult(
            success=False,
            original_filename=original_filename,
            file_type=FileType.PDF.value,
            errors=["opendataloader-pdf not installed. Install: pip install opendataloader-pdf"],
        )

    try:
        temp_output_dir = Path(tempfile.mkdtemp(prefix="odl_"))
        try:
            kwargs = {
                "input_path": [str(file_path)],
                "output_dir": str(temp_output_dir),
                "format": "markdown",
                "image_output": config.pdf_image_output,
                "image_format": config.pdf_image_format,
            }

            if config.pdf_hybrid_enabled:
                kwargs["hybrid"] = config.pdf_hybrid_backend
                kwargs["hybrid_url"] = config.pdf_hybrid_url
                kwargs["hybrid_mode"] = config.pdf_hybrid_mode
                kwargs["hybrid_fallback"] = True

            opendataloader_pdf.convert(**kwargs)

            md_candidate = temp_output_dir / f"{file_path.stem}.md"
            if not md_candidate.exists():
                md_files = list(temp_output_dir.glob("*.md"))
                if md_files:
                    md_candidate = md_files[0]

            if not md_candidate.exists():
                return ConvertResult(
                    success=False,
                    original_filename=original_filename,
                    file_type=FileType.PDF.value,
                    errors=["No markdown output produced"],
                )

            md_content = md_candidate.read_text(encoding="utf-8")

            image_manager = get_image_manager()
            images_extracted = 0

            images_dir = temp_output_dir / f"{file_path.stem}_images"
            if not images_dir.exists():
                images_dir = temp_output_dir / "images"

            if images_dir.exists() and images_dir.is_dir():
                md_content, images_extracted = image_manager.rewrite_markdown_images(
                    md_content=md_content,
                    source_images_dir=images_dir,
                    prefix="pdf",
                )

            if config.ocr_enabled and images_extracted > 0:
                md_content = image_manager.apply_ocr_to_markdown(
                    md_content=md_content,
                )

            return ConvertResult(
                success=True,
                original_filename=original_filename,
                file_type=FileType.PDF.value,
                markdown_content=md_content,
                images_extracted=images_extracted,
                warnings=warnings,
            )

        finally:
            shutil.rmtree(temp_output_dir, ignore_errors=True)

    except Exception as e:
        logger.exception("opendataloader_conversion_failed")
        errors.append(str(e))
        return ConvertResult(
            success=False,
            original_filename=original_filename,
            file_type=FileType.PDF.value,
            errors=errors,
        )


def _convert_pymupdf(file_path: Path, original_filename: str) -> ConvertResult:
    errors: List[str] = []
    warnings: List[str] = []
    config = get_config()

    try:
        import fitz
    except ImportError:
        return ConvertResult(
            success=False,
            original_filename=original_filename,
            file_type=FileType.PDF.value,
            errors=["PyMuPDF not installed. Install: pip install PyMuPDF"],
        )

    try:
        doc = fitz.open(str(file_path))
        image_manager = get_image_manager()
        images_extracted = 0
        md_parts: List[str] = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text("text")
            md_parts.append(page_text)
            md_parts.append("")

            if config.pdf_image_output == "off":
                continue

            image_list = page.get_images(full=True)
            for img_info in image_list:
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                if base_image:
                    image_bytes = base_image["image"]
                    ext = base_image["ext"]
                    ref = image_manager.add_image_bytes(image_bytes, ext, "pdf")
                    img_md = f"\n![PDF image {page_num + 1}]({ref})\n"
                    md_parts.append(img_md)
                    images_extracted += 1

        doc.close()
        md_content = "\n".join(md_parts)

        if config.ocr_enabled and images_extracted > 0:
            md_content = image_manager.apply_ocr_to_markdown(md_content=md_content)

        return ConvertResult(
            success=True,
            original_filename=original_filename,
            file_type=FileType.PDF.value,
            markdown_content=md_content,
            images_extracted=images_extracted,
            warnings=warnings,
        )

    except Exception as e:
        logger.exception("pymupdf_conversion_failed")
        errors.append(str(e))
        return ConvertResult(
            success=False,
            original_filename=original_filename,
            file_type=FileType.PDF.value,
            errors=errors,
        )
