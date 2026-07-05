"""Skip monolithic literature parse when chunked book dirs already exist."""

from __future__ import annotations

from pathlib import Path

BOOK_MD_SUBDIR = Path("Дополнительные материалы/md")


def chunked_book_slugs(data_root: Path) -> set[str]:
    books_root = data_root / BOOK_MD_SUBDIR

    if not books_root.is_dir():
        return set()

    slugs: set[str] = set()

    for book_dir in books_root.iterdir():
        if not book_dir.is_dir():
            continue

        if any(book_dir.glob("p*.md")):
            slugs.add(book_dir.name)

    return slugs


def literature_needs_parse(data_root: Path, literature_root: Path) -> bool:
    if not literature_root.is_dir():
        return False

    chunked = chunked_book_slugs(data_root)

    for path in sorted(literature_root.glob("*.md")):
        if path.name.startswith("_") or path.name.lower() == "readme.md":
            continue

        if path.stem not in chunked:
            return True

    return False
