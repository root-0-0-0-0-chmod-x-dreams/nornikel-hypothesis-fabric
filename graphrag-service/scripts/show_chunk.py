#!/usr/bin/env python3
"""Show full text for a chunk by chunk_id (from vector store or MD file)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from graphrag.bootstrap import bootstrap


def main() -> None:
    parser = argparse.ArgumentParser(description="Show paragraph text by chunk_id")
    parser.add_argument("chunk_id", help="e.g. book_geokniga_..._paragraph_p255_i2256")
    parser.add_argument("--json", action="store_true", help="Print metadata as JSON")
    args = parser.parse_args()

    loaded = bootstrap()
    chunk = loaded.vectors.get(args.chunk_id)

    if chunk is None:
        print(f"Chunk not found: {args.chunk_id}", file=sys.stderr)
        sys.exit(1)

    md_path = chunk.metadata.get("md_path")
    print(f"chunk_id:  {chunk.chunk_id}")
    print(f"source:    {chunk.source}")
    print(f"page:      {chunk.metadata.get('page')}")
    print(f"paragraph: {chunk.metadata.get('paragraph_index')}")
    print(f"section:   {chunk.section or chunk.metadata.get('section', '')}")
    if md_path:
        print(f"md_path:   {md_path}")
    print()
    print(chunk.text)

    if args.json:
        import json

        print()
        print(json.dumps(chunk.metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
