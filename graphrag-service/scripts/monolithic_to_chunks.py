#!/usr/bin/env python3
"""Split monolithic literature MD into paragraph chunk directories."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from graphrag.ingestion.md_monolithic_writer import (
    chunked_dir_needs_rebuild,
    write_monolithic_to_chunked_dir,
)
from graphrag.ingestion.paths import LITERATURE_MD_ROOT, resolve_literature_root

BOOK_MD_SUBDIR = Path("Дополнительные материалы/md")


def _chunked_root(data_root: Path) -> Path:
    return data_root / BOOK_MD_SUBDIR


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Case root (default: bundled data/case)",
    )
    parser.add_argument(
        "--monolithic-dir",
        type=Path,
        default=None,
        help="Monolithic MD source (default: data/literature)",
    )
    parser.add_argument(
        "--book",
        action="append",
        dest="books",
        help="Only rebuild this book slug (repeatable)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild even if chunk dir looks populated",
    )
    args = parser.parse_args()

    from graphrag.ingestion.paths import BUNDLED_CASE_ROOT, resolve_data_root

    data_root = args.data_root or resolve_data_root(BUNDLED_CASE_ROOT if BUNDLED_CASE_ROOT.is_dir() else None)
    monolithic_dir = args.monolithic_dir or resolve_literature_root()
    out_root = _chunked_root(data_root)
    out_root.mkdir(parents=True, exist_ok=True)

    sources = sorted(monolithic_dir.glob("*.md"))

    if args.books:
        allowed = set(args.books)
        sources = [path for path in sources if path.stem in allowed]

    if not sources:
        raise SystemExit(f"No monolithic MD in {monolithic_dir}")

    total = 0

    for path in sources:
        if path.name.lower() == "readme.md":
            continue

        book_dir = out_root / path.stem

        if not args.force and not chunked_dir_needs_rebuild(book_dir):
            print(f"skip {path.stem}: {len(list(book_dir.glob('p*.md')))} chunks exist")
            continue

        if book_dir.exists():
            for old in book_dir.glob("p*.md"):
                old.unlink()

        count = write_monolithic_to_chunked_dir(path, out_root)
        print(f"wrote {count} chunks → {book_dir}")
        total += count

    print(f"done: {total} chunks")


if __name__ == "__main__":
    main()
