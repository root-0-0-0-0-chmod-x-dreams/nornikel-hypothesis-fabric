from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

from app.image_manager import get_image_manager
from app.models import ConvertResult
from app.utils import FileType

logger = logging.getLogger("data_processor")


def convert_image(file_path: Path, original_filename: str) -> ConvertResult:
    errors: List[str] = []
    warnings: List[str] = []

    try:
        image_manager = get_image_manager()
        ref = image_manager.add_image(file_path, prefix="img")
        alt_text = file_path.stem

        md_text = f"![{alt_text}]({ref})\n"

        return ConvertResult(
            success=True,
            original_filename=original_filename,
            file_type=_image_type_from_ext(file_path.suffix),
            markdown_content=md_text,
            images_extracted=1,
            metadata={"image_ref": ref},
            warnings=warnings,
        )

    except Exception as e:
        logger.exception("image_conversion_failed")
        errors.append(str(e))
        return ConvertResult(
            success=False,
            original_filename=original_filename,
            file_type=_image_type_from_ext(file_path.suffix),
            errors=errors,
        )


def _image_type_from_ext(suffix: str) -> str:
    mapping = {
        ".png": FileType.IMAGE_PNG.value,
        ".jpg": FileType.IMAGE_JPG.value,
        ".jpeg": FileType.IMAGE_JPEG.value,
        ".gif": FileType.IMAGE_GIF.value,
        ".bmp": FileType.IMAGE_BMP.value,
        ".tiff": FileType.IMAGE_TIFF.value,
        ".tif": FileType.IMAGE_TIFF.value,
        ".webp": FileType.IMAGE_WEBP.value,
    }
    return mapping.get(suffix.lower(), "image")
