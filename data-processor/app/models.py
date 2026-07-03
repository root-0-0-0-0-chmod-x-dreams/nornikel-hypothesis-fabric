from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class FileType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    XLS = "xls"
    CSV = "csv"
    IMAGE_PNG = "png"
    IMAGE_JPG = "jpg"
    IMAGE_JPEG = "jpeg"
    IMAGE_GIF = "gif"
    IMAGE_BMP = "bmp"
    IMAGE_TIFF = "tiff"
    IMAGE_WEBP = "webp"
    CODE = "code"
    TEXT = "text"
    JSON = "json"
    XML = "xml"
    HTML = "html"
    BINARY = "binary"


class ConvertRequest(BaseModel):
    original_filename: str = Field(..., min_length=1)
    file_type: Optional[FileType] = None


class ConvertResult(BaseModel):
    success: bool
    original_filename: str
    file_type: str
    markdown_content: str = ""
    images_extracted: int = 0
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BatchConvertResult(BaseModel):
    total: int
    succeeded: int
    failed: int
    results: List[ConvertResult]


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    uptime_seconds: float
