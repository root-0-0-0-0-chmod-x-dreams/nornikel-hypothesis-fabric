#!/usr/bin/env python3
"""Normalize image links in scheme/regulation Markdown files."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "nornikel-hypothesis-fabric" / "graphrag-service"))

from graphrag.ingestion.md_frontmatter import split_frontmatter
from graphrag.ingestion.md_image_refs import IMAGE_MD_RE

CASE_SCHEME_DIR = "Схемы флотации"
CASE_REGULATION_DIR = "Регламенты"
CASE_TASK_SUBPATH = Path("Задача 1. Фабрика гипотез") / "Задача 1"
REGULATION_MARKERS = ("Регламент", "оборудования", "Типичный")


def _kind(stem: str) -> str:
    if any(marker in stem for marker in REGULATION_MARKERS):
        return "regulation"

    return "scheme"


def _png_path(stem: str, *, hackathon_root: Path) -> Path:
    subdir = CASE_REGULATION_DIR if _kind(stem) == "regulation" else CASE_SCHEME_DIR

    return hackathon_root / CASE_TASK_SUBPATH / subdir / f"{stem}.png"


def _alt_for(path: Path, meta: dict) -> str:
    return str(meta.get("title") or path.stem)


def _replace_first_image(raw: str, *, alt: str, ref: str) -> str:
    if not IMAGE_MD_RE.search(raw):
        return raw

    return IMAGE_MD_RE.sub(f"![{alt}]({ref})", raw, count=1)


def fix_bundled_file(path: Path) -> bool:
    raw = path.read_text(encoding="utf-8")
    meta, _body = split_frontmatter(raw)
    alt = _alt_for(path, meta)
    ref = f"./{path.stem}.png"
    new_raw = _replace_first_image(raw, alt=alt, ref=ref)

    if new_raw == raw:
        return False

    path.write_text(new_raw, encoding="utf-8")

    return True


def fix_pics_to_md_file(path: Path, *, hackathon_root: Path) -> bool:
    raw = path.read_text(encoding="utf-8")
    meta, _body = split_frontmatter(raw)
    png = _png_path(path.stem, hackathon_root=hackathon_root)

    if not png.is_file():
        raise FileNotFoundError(png)

    alt = _alt_for(path, meta)
    ref = os.path.relpath(png, start=path.parent).replace("\\", "/")
    new_raw = _replace_first_image(raw, alt=alt, ref=ref)

    if new_raw == raw:
        return False

    path.write_text(new_raw, encoding="utf-8")

    return True


def fix_bundled_dir(data_case: Path) -> int:
    changed = 0

    for subdir in (CASE_SCHEME_DIR, CASE_REGULATION_DIR):
        directory = data_case / subdir

        if not directory.is_dir():
            continue

        for path in sorted(directory.glob("*.md")):
            if fix_bundled_file(path):
                changed += 1

    return changed


def fix_pics_to_md(pics_dir: Path, hackathon_root: Path) -> int:
    changed = 0

    if not pics_dir.is_dir():
        return 0

    for path in sorted(pics_dir.glob("*.md")):
        if fix_pics_to_md_file(path, hackathon_root=hackathon_root):
            changed += 1

    return changed


def main() -> int:
    hackathon_root = Path(__file__).resolve().parents[1]
    service_root = hackathon_root / "nornikel-hypothesis-fabric" / "graphrag-service"
    data_case = service_root / "data" / "case"
    pics_dir = hackathon_root / "pics-to-md"

    if len(sys.argv) > 1:
        data_case = Path(sys.argv[1])

    print(f"Updated bundled MD: {fix_bundled_dir(data_case)}")
    print(f"Updated pics-to-md: {fix_pics_to_md(pics_dir, hackathon_root)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
