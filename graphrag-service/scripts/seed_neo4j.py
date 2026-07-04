#!/usr/bin/env python3
"""Seed Neo4j from production case data."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from graphrag.bootstrap import bootstrap
from graphrag.constants import GRAPH_BACKEND_NEO4J


def main() -> None:
    loaded = bootstrap(graph_backend=GRAPH_BACKEND_NEO4J)
    graph = loaded.graph

    try:
        print("Neo4j loaded:", loaded.stats)
        print("Browser: http://localhost:7474")
    finally:
        if hasattr(graph, "close"):
            graph.close()


if __name__ == "__main__":
    main()
