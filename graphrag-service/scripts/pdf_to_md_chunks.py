#!/usr/bin/env python3
"""Convert literature PDFs to chunked Markdown under Дополнительные материалы/md/."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from graphrag.constants import BOOK_CHUNK_GRANULARITY, BOOK_EXTRACTOR_BACKEND
from graphrag.ingestion.book_chunking import ALL_GRANULARITIES
from graphrag.ingestion.md_book_writer import write_book_md_chunks
from graphrag.ingestion.paths import PDF_GLOB, resolve_data_root
from graphrag.ingestion.pdf_extractors import (
    BACKEND_OPENDATALOADER,
    BACKEND_PYMUPDF,
    BACKEND_PYMUPDF_BLOCKS,
    clear_odl_cache,
    extract_pdf,
    java_available,
)


def _default_backend() -> str:
    if BOOK_EXTRACTOR_BACKEND == BACKEND_OPENDATALOADER and java_available():
        return BACKEND_OPENDATALOADER

    return BACKEND_PYMUPDF


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=None)
    parser.add_argument("--pdf", type=Path, default=None, help="Single PDF path")
    parser.add_argument("--title", type=str, default=None)
    parser.add_argument("--author", type=str, default=None)
    parser.add_argument(
        "--backend",
        choices=[BACKEND_OPENDATALOADER, BACKEND_PYMUPDF, BACKEND_PYMUPDF_BLOCKS],
        default=_default_backend(),
        help=f"PDF extractor (default: {_default_backend()})",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove existing md/ output and OpenDataLoader cache before export",
    )
    parser.add_argument(
        "--granularity",
        choices=list(ALL_GRANULARITIES),
        default=BOOK_CHUNK_GRANULARITY,
        help=f"Chunk granularity for MD export (default: {BOOK_CHUNK_GRANULARITY})",
    )
    args = parser.parse_args()

    data_root = resolve_data_root(args.data_root)
    out_root = data_root / "Дополнительные материалы" / "md"
    work_dir = data_root / "Дополнительные материалы" / ".odl_cache"

    if args.clean and out_root.is_dir():
        shutil.rmtree(out_root)

    if args.clean and args.backend == BACKEND_OPENDATALOADER:
        clear_odl_cache(data_root)

    if args.pdf:
        pdf_paths = [args.pdf]
    else:
        pdf_paths = sorted(data_root.glob(PDF_GLOB))

    if not pdf_paths:
        raise SystemExit(f"No PDFs found under {data_root / PDF_GLOB}")

    if args.backend == BACKEND_OPENDATALOADER and not java_available():
        raise SystemExit(
            "OpenDataLoader requires Java 11+. Install: brew install openjdk@17"
        )

    total = 0

    if args.backend == BACKEND_OPENDATALOADER and len(pdf_paths) > 1:
        import opendataloader_pdf

        opendataloader_pdf.convert(
            input_path=[str(path) for path in pdf_paths],
            output_dir=str(work_dir),
            format="markdown,json",
            markdown_page_separator="---page-%page-number%---",
            image_output="off",
            quiet=True,
        )

    for pdf_path in pdf_paths:
        result = extract_pdf(
            pdf_path,
            backend=args.backend,
            work_dir=work_dir,
        )
        count = write_book_md_chunks(
            result,
            out_root,
            title=args.title,
            author=args.author,
            granularity=args.granularity,
        )
        print(
            f"{pdf_path.name}: {count} chunks ({result.backend}/{args.granularity}) "
            f"-> {out_root / pdf_path.stem}"
        )
        total += count

    print(f"Wrote {total} MD chunks to {out_root} via {args.backend}")


if __name__ == "__main__":
    main()
