from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path
from typing import List

import opendataloader_pdf

from app.image_manager import get_image_manager
from app.models import ConvertResult
from app.utils import FileType

logger = logging.getLogger("data_processor")


def convert_pdf(file_path: Path, original_filename: str) -> ConvertResult:
    errors: List[str] = []
    warnings: List[str] = []

    try:
        temp_output_dir = Path(tempfile.mkdtemp(prefix="odl_output_"))
        try:
            opendataloader_pdf.convert(
                input_path=[str(file_path)],
                output_dir=str(temp_output_dir),
                format="markdown",
                image_output="external",
                image_format="jpeg",
            )

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
                    errors=["No markdown output produced by opendataloader"],
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

    except ImportError:
        return ConvertResult(
            success=False,
            original_filename=original_filename,
            file_type=FileType.PDF.value,
            errors=[
                "opendataloader-pdf not installed. Install: pip install opendataloader-pdf"
            ],
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
