from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from app.image_manager import get_image_manager
from app.models import ConvertResult
from app.utils import FileType

logger = logging.getLogger("data_processor")


def convert_docx(file_path: Path, original_filename: str) -> ConvertResult:
    errors: List[str] = []
    warnings: List[str] = []

    try:
        from docx2md import do_convert

        md_text = do_convert(str(file_path), use_md_table=True)

        image_manager = get_image_manager()

        images_extracted = 0
        temp_dir = Path(tempfile.mkdtemp(prefix="docx_media_"))
        try:
            _extract_docx_images(file_path, temp_dir)
            if any(temp_dir.iterdir()):
                md_text, images_extracted = image_manager.rewrite_markdown_images(
                    md_content=md_text,
                    source_images_dir=temp_dir,
                    prefix="docx",
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        return ConvertResult(
            success=True,
            original_filename=original_filename,
            file_type=FileType.DOCX.value,
            markdown_content=md_text,
            images_extracted=images_extracted,
            warnings=warnings,
        )

    except ImportError:
        return ConvertResult(
            success=False,
            original_filename=original_filename,
            file_type=FileType.DOCX.value,
            errors=["docx2md not installed. Install: pip install docx2md"],
        )
    except Exception as e:
        logger.exception("docx_conversion_failed")
        errors.append(str(e))
        return ConvertResult(
            success=False,
            original_filename=original_filename,
            file_type=FileType.DOCX.value,
            errors=errors,
        )


def _extract_docx_images(docx_path: Path, output_dir: Path) -> int:
    try:
        import zipfile
        with zipfile.ZipFile(docx_path, "r") as z:
            image_entries = [
                name for name in z.namelist()
                if name.startswith("word/media/") and not name.endswith("/")
            ]
            for entry in image_entries:
                z.extract(entry, output_dir)
                extracted = output_dir / entry
                flat = output_dir / Path(entry).name
                if extracted != flat and extracted.exists():
                    shutil.move(str(extracted), str(flat))
            return len(image_entries)
    except Exception:
        return 0
