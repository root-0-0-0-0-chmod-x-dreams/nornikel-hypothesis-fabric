"""Parse Markdown image links (![alt](path)) and resolve bundled image files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

IMAGE_MD_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
IMAGE_ONLY_RE = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", re.MULTILINE)
IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"})

BOOK_MD_SUBDIR = Path("Дополнительные материалы/md")
IMAGES_SUBDIR = Path("Дополнительные материалы/images")


@dataclass(frozen=True)
class MarkdownImageRef:
    alt: str
    ref_path: str


def extract_image_refs(text: str) -> list[MarkdownImageRef]:
    return [
        MarkdownImageRef(alt=alt.strip(), ref_path=ref_path.strip())
        for alt, ref_path in IMAGE_MD_RE.findall(text)
    ]


def is_image_only_body(text: str) -> bool:
    stripped = text.strip()

    if not stripped:
        return False

    if IMAGE_ONLY_RE.fullmatch(stripped):
        return True

    refs = extract_image_refs(stripped)

    if len(refs) != 1:
        return False

    without_images = IMAGE_MD_RE.sub("", stripped).strip()

    return not without_images


def primary_image_ref(text: str) -> MarkdownImageRef | None:
    stripped = text.strip()
    match = IMAGE_ONLY_RE.fullmatch(stripped)

    if match:
        return MarkdownImageRef(alt=match.group(1).strip(), ref_path=match.group(2).strip())

    refs = extract_image_refs(stripped)

    if len(refs) == 1 and is_image_only_body(stripped):
        return refs[0]

    return None


def strip_image_markdown(text: str) -> str:
    cleaned = IMAGE_MD_RE.sub("", text)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()


def _looks_like_image(path: str) -> bool:
    lowered = path.lower().split("?", 1)[0]

    return Path(lowered).suffix in IMAGE_EXTENSIONS


def normalize_image_ref(ref_path: str) -> str:
    """Normalize chunker paths like local-data\\Схемы флотации\\foo.png."""
    ref = ref_path.strip().strip('"').strip("'")
    ref = ref.replace("\\", "/")

    lowered = ref.lower()

    for prefix in ("local-data/", "local_data/"):
        if lowered.startswith(prefix):
            ref = ref[len(prefix) :]
            break

    return Path(ref).name if "/" in ref else ref


def resolve_image_path(
    md_path: Path,
    ref_path: str,
    *,
    data_root: Path | None = None,
) -> Path | None:
    ref = normalize_image_ref(ref_path)

    if not ref or ref.startswith(("http://", "https://", "data:")):
        return None

    if not _looks_like_image(ref):
        return None

    candidate = Path(ref)

    if candidate.is_absolute() and candidate.is_file():
        return candidate.resolve()

    md_dir = md_path.parent if md_path.suffix else md_path
    local = (md_dir / candidate).resolve()

    if local.is_file():
        return local

    if data_root is not None:
        materials = data_root / "Дополнительные материалы"
        search_roots = [
            materials / "images",
            materials / "md" / "images",
            materials,
            data_root / "Схемы флотации",
            data_root / "Регламенты",
        ]

        ref_name = Path(ref).name

        for root in search_roots:
            if not root.exists():
                continue

            direct = (root / ref).resolve()

            if direct.is_file():
                return direct

            by_name = next((path for path in root.rglob(ref_name) if path.is_file()), None)

            if by_name is not None:
                return by_name.resolve()

    return None


def relative_to_data_root(path: Path, data_root: Path) -> str | None:
    try:
        return str(path.resolve().relative_to(data_root.resolve()))
    except ValueError:
        return None
