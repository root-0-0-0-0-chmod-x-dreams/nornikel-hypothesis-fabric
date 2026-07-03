from __future__ import annotations

import logging
import mimetypes
import sys
from pathlib import Path
from typing import Dict, Optional, Set

from .models import FileType

logger = logging.getLogger("data_processor")

TEXT_EXTENSIONS: Set[str] = {
    ".txt", ".md", ".rst", ".log", ".cfg", ".ini", ".toml", ".yaml", ".yml",
    ".conf", ".properties", ".env", ".sh", ".bash", ".zsh", ".fish",
    ".bat", ".cmd", ".ps1",
}

CODE_EXTENSIONS: Dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "jsx",
    ".tsx": "tsx",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".r": "r",
    ".sql": "sql",
    ".css": "css",
    ".scss": "scss",
    ".less": "less",
    ".html": "html",
    ".htm": "html",
    ".xml": "xml",
    ".svg": "xml",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".dockerfile": "dockerfile",
    ".makefile": "makefile",
    ".cmake": "cmake",
}

CSV_EXTENSIONS: Set[str] = {".csv", ".tsv"}

IMAGE_EXTENSIONS: Dict[str, FileType] = {
    ".png": FileType.IMAGE_PNG,
    ".jpg": FileType.IMAGE_JPG,
    ".jpeg": FileType.IMAGE_JPEG,
    ".gif": FileType.IMAGE_GIF,
    ".bmp": FileType.IMAGE_BMP,
    ".tiff": FileType.IMAGE_TIFF,
    ".tif": FileType.IMAGE_TIFF,
    ".webp": FileType.IMAGE_WEBP,
}

KNOWN_BINARY_EXTENSIONS: Set[str] = {
    ".exe", ".dll", ".so", ".dylib", ".bin", ".dat", ".pyc", ".pyo",
    ".class", ".o", ".obj", ".lib", ".a", ".zip", ".tar", ".gz", ".bz2",
    ".7z", ".rar", ".xz", ".lz", ".lz4", ".zst",
    ".mp3", ".wav", ".ogg", ".flac", ".aac", ".wma",
    ".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm",
    ".ttf", ".otf", ".woff", ".woff2", ".eot",
    ".ico", ".icns", ".cur",
    ".db", ".sqlite", ".sqlite3", ".mdb",
    ".pkl", ".pickle", ".joblib", ".h5", ".hdf5",
    ".pt", ".pth", ".onnx", ".pb", ".tflite",
}


def detect_file_type(filename: str, content_bytes: Optional[bytes] = None) -> FileType:
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        return FileType.PDF
    if suffix == ".docx":
        return FileType.DOCX
    if suffix == ".xlsx":
        return FileType.XLSX
    if suffix == ".xls":
        return FileType.XLS
    if suffix in CSV_EXTENSIONS:
        return FileType.CSV

    if suffix in IMAGE_EXTENSIONS:
        return IMAGE_EXTENSIONS[suffix]

    if suffix in CODE_EXTENSIONS:
        return FileType.CODE

    if suffix in TEXT_EXTENSIONS:
        return FileType.TEXT

    if suffix == ".json":
        return FileType.JSON
    if suffix == ".xml" or suffix == ".html" or suffix == ".htm":
        return FileType.XML if suffix == ".xml" else FileType.HTML

    if suffix in KNOWN_BINARY_EXTENSIONS:
        return FileType.BINARY

    if content_bytes:
        if _is_text_content(content_bytes):
            return FileType.TEXT
        return FileType.BINARY

    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type:
        if mime_type.startswith("text/"):
            return FileType.TEXT
        if mime_type.startswith("image/"):
            return FileType.BINARY
        if mime_type.startswith("application/"):
            return FileType.BINARY

    return FileType.TEXT


def _is_text_content(data: bytes, sample_size: int = 1024) -> bool:
    if not data:
        return True
    sample = data[:sample_size]
    if b"\x00" in sample:
        return False
    text_chars = sum(
        1 for b in sample
        if 32 <= b <= 126 or b in (9, 10, 13)
    )
    return text_chars / len(sample) > 0.9


def get_language_for_code(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return CODE_EXTENSIONS.get(suffix, "")
