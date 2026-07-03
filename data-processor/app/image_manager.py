from __future__ import annotations

import logging
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Dict, Optional, Set

from .config import get_config

logger = logging.getLogger("data_processor")


class ImageManager:
    MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)", re.IGNORECASE)
    HTML_IMAGE_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', re.IGNORECASE)

    def __init__(self) -> None:
        self.config = get_config()
        self._images_dir = Path(self.config.images_dir)
        self._images_dir.mkdir(parents=True, exist_ok=True)

    @property
    def images_dir(self) -> Path:
        return self._images_dir

    def generate_unique_name(self, original_name: str, prefix: str = "img") -> str:
        suffix = Path(original_name).suffix.lower()
        if not suffix:
            suffix = ".png"
        return f"{prefix}_{uuid.uuid4().hex[:12]}{suffix}"

    def add_image(self, source_path: Path, prefix: str = "img") -> str:
        unique_name = self.generate_unique_name(source_path.name, prefix)
        dest_path = self._images_dir / unique_name
        if not dest_path.exists():
            shutil.copy2(source_path, dest_path)
            logger.debug("image_saved", extra={"src": str(source_path), "dest": str(dest_path)})
        return f"images/{unique_name}"

    def add_image_bytes(self, data: bytes, extension: str, prefix: str = "img") -> str:
        if not extension.startswith("."):
            extension = f".{extension}"
        unique_name = f"{prefix}_{uuid.uuid4().hex[:12]}{extension}"
        dest_path = self._images_dir / unique_name
        with open(dest_path, "wb") as f:
            f.write(data)
        logger.debug("image_bytes_saved", extra={"dest": str(dest_path), "size": len(data)})
        return f"images/{unique_name}"

    def rewrite_markdown_images(
        self,
        md_content: str,
        source_images_dir: Path,
        prefix: str = "img",
    ) -> tuple[str, int]:
        extracted = 0

        def replace_match(match: re.Match) -> str:
            nonlocal extracted
            alt_text = match.group(1)
            img_ref = match.group(2)

            if img_ref.startswith(("http://", "https://", "data:")):
                return match.group(0)

            source_img = source_images_dir / Path(img_ref).name
            candidates = list(source_images_dir.glob(f"{Path(img_ref).stem}.*"))
            if not candidates and source_img.exists():
                candidates = [source_img]

            if candidates:
                new_ref = self.add_image(candidates[0], prefix)
                extracted += 1
                return f"![{alt_text}]({new_ref})"

            logger.warning("image_not_found", extra={"ref": img_ref, "dir": str(source_images_dir)})
            return match.group(0)

        new_content = self.MD_IMAGE_RE.sub(replace_match, md_content)
        return new_content, extracted

    def list_images(self) -> list[str]:
        return [p.name for p in self._images_dir.glob("*") if p.is_file()]

    def get_image_count(self) -> int:
        return sum(1 for _ in self._images_dir.iterdir() if _.is_file())


_image_manager: Optional[ImageManager] = None


def get_image_manager() -> ImageManager:
    global _image_manager
    if _image_manager is None:
        _image_manager = ImageManager()
    return _image_manager
