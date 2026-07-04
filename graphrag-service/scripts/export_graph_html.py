#!/usr/bin/env python3
"""Export interactive HTML graph views."""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from graphrag.bootstrap import bootstrap
from graphrag.graph.networkx_store import NetworkXGraphStore
from graphrag.studio.graph_viz import VIEW_FILTERS, export_graph_html


def main() -> None:
    parser = argparse.ArgumentParser(description="Export GraphRAG graph to interactive HTML")
    parser.add_argument(
        "--view",
        choices=sorted(VIEW_FILTERS),
        default="literature",
        help="Graph slice (default: literature — passages + sources + catalog)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Export all views to output/graph/",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open generated HTML in browser",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output HTML path",
    )
    parser.add_argument(
        "--max-nodes",
        type=int,
        default=None,
        help="Cap nodes (useful for full view in browser)",
    )
    args = parser.parse_args()

    loaded = bootstrap()
    graph = loaded.graph

    if not isinstance(graph, NetworkXGraphStore):
        print("Reload with GRAPH_BACKEND=networkx for HTML export", file=sys.stderr)
        sys.exit(1)

    out_dir = Path("output/graph")
    views = list(VIEW_FILTERS) if args.all else [args.view]

    for view in views:
        path = args.output or out_dir / f"graph_{view}.html"
        if args.all:
            path = out_dir / f"graph_{view}.html"

        stats = export_graph_html(graph, path, view=view, max_nodes=args.max_nodes)
        print(f"Wrote {path} — {stats['nodes']} nodes, {stats['edges']} edges ({view})")

        if args.open and view == views[-1]:
            webbrowser.open(path.resolve().as_uri())


if __name__ == "__main__":
    main()
