from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Callable, Dict

from app.models import ConvertResult, FileType
from app.utils import detect_file_type

from .docx_converter import convert_docx
from .excel_converter import convert_xls, convert_xlsx
from .image_converter import convert_image
from .pdf_converter import convert_pdf
from .text_converter import (
    convert_binary,
    convert_code,
    convert_csv,
    convert_html,
    convert_text,
)

logger = logging.getLogger("data_processor")

ConvertFunc = Callable[[Path, str], ConvertResult]

CONVERTER_REGISTRY: Dict[FileType, ConvertFunc] = {
    FileType.PDF: convert_pdf,
    FileType.DOCX: convert_docx,
    FileType.XLSX: convert_xlsx,
    FileType.XLS: convert_xls,
    FileType.CSV: convert_csv,
    FileType.IMAGE_PNG: convert_image,
    FileType.IMAGE_JPG: convert_image,
    FileType.IMAGE_JPEG: convert_image,
    FileType.IMAGE_GIF: convert_image,
    FileType.IMAGE_BMP: convert_image,
    FileType.IMAGE_TIFF: convert_image,
    FileType.IMAGE_WEBP: convert_image,
    FileType.CODE: convert_code,
    FileType.TEXT: convert_text,
    FileType.JSON: convert_text,
    FileType.XML: convert_text,
    FileType.HTML: convert_html,
    FileType.BINARY: convert_binary,
}


def get_converter(file_type: FileType) -> ConvertFunc | None:
    return CONVERTER_REGISTRY.get(file_type)


async def convert_file(file_path: Path, original_filename: str) -> ConvertResult:
    file_type = detect_file_type(original_filename)
    logger.info(
        "converting_file",
        extra={"original_filename": original_filename, "detected_type": file_type.value},
    )

    converter = get_converter(file_type)
    if converter is None:
        logger.warning("no_converter", extra={"type": file_type.value})
        return ConvertResult(
            success=False,
            original_filename=original_filename,
            file_type=file_type.value,
            errors=[f"No converter for file type: {file_type.value}"],
        )

    try:
        result = await asyncio.to_thread(converter, file_path, original_filename)
        if isinstance(result, ConvertResult):
            return result
        logger.error("unexpected_converter_result", extra={"type": str(type(result))})
        return ConvertResult(
            success=False,
            original_filename=original_filename,
            file_type=file_type.value,
            errors=["Converter returned unexpected result type"],
        )
    except Exception as e:
        logger.exception("converter_failed")
        return ConvertResult(
            success=False,
            original_filename=original_filename,
            file_type=file_type.value,
            errors=[str(e)],
        )
