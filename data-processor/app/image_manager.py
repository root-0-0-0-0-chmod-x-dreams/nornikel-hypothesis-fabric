from __future__ import annotations

import logging
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import List, Optional

from .config import get_config

logger = logging.getLogger("data_processor")


class ImageManager:
    MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)", re.IGNORECASE)

    def __init__(self) -> None:
        self.config = get_config()
        self._images_dir = Path(self.config.images_dir)
        self._images_dir.mkdir(parents=True, exist_ok=True)
        self._ocr_reader = None

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
        return f"images/{unique_name}"

    def add_image_bytes(self, data: bytes, extension: str, prefix: str = "img") -> str:
        if not extension.startswith("."):
            extension = f".{extension}"
        unique_name = f"{prefix}_{uuid.uuid4().hex[:12]}{extension}"
        dest_path = self._images_dir / unique_name
        with open(dest_path, "wb") as f:
            f.write(data)
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

            img_ref = img_ref.strip().strip("<>")

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

    def _get_ocr_reader(self):
        if self._ocr_reader is not None:
            return self._ocr_reader

        import easyocr

        languages = [lang.strip() for lang in self.config.ocr_languages.split(",") if lang.strip()]
        if not languages:
            languages = ["ru", "en"]

        gpu = self.config.ocr_gpu_enabled
        self._ocr_reader = easyocr.Reader(languages, gpu=gpu)
        logger.info("ocr_reader_initialized", extra={"languages": languages, "gpu": gpu})
        return self._ocr_reader

    def _ocr_single_image(self, image_path: Path) -> str:
        try:
            reader = self._get_ocr_reader()
            result = reader.readtext(str(image_path), detail=0)
            if result:
                return " ".join(result)
            return ""
        except Exception as e:
            logger.warning("ocr_failed", extra={"image": str(image_path), "error": str(e)})
            return ""

    def apply_ocr_to_markdown(self, md_content: str) -> str:
        ocr_cache: dict[str, str] = {}

        def replace_with_ocr(match: re.Match) -> str:
            full = match.group(0)
            img_ref = match.group(2)
            img_ref = img_ref.strip().strip("<>")

            if img_ref.startswith(("http://", "https://", "data:")):
                return full

            if img_ref not in ocr_cache:
                img_path = self._images_dir / Path(img_ref).name
                if img_path.exists() and img_path.is_file():
                    ocr_text = self._ocr_single_image(img_path)
                    ocr_cache[img_ref] = ocr_text
                else:
                    ocr_cache[img_ref] = ""

            ocr_text = ocr_cache[img_ref]
            if ocr_text:
                return f"{full}\n\n{{OCR: {ocr_text}}}\n"
            return full

        return self.MD_IMAGE_RE.sub(replace_with_ocr, md_content)

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
