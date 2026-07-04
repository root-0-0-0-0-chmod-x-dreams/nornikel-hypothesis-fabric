#!/usr/bin/env python3
"""Verify Qdrant collection after bootstrap."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from graphrag.bootstrap import bootstrap
from graphrag.config import QdrantConfig
from graphrag.qdrant_store import _create_qdrant_client


def main() -> None:
    config = QdrantConfig.from_env()
    client = _create_qdrant_client(config.url)

    if not client.collection_exists(config.collection):
        print(f"Collection missing: {config.collection}")
        print("Run: make bootstrap  (with Qdrant up)")
        sys.exit(1)

    loaded = bootstrap()
    info = client.get_collection(config.collection)

    report = {
        "url": config.url,
        "collection": config.collection,
        "qdrant_points": info.points_count,
        "indexed_chunks": loaded.vectors.size,
        "bootstrap_chunks": loaded.stats.get("chunks"),
        "vector_backend": type(loaded.vectors).__name__,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if info.points_count != loaded.vectors.size:
        print("Warning: point count != indexed chunk count", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
