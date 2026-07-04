#!/usr/bin/env python3
"""Export Excel LossForm buckets to Markdown with YAML frontmatter (provenance-ready)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from graphrag.ingestion.excel_parser import EXCEL_SOURCES, parse_excel_file
from graphrag.ingestion.paths import resolve_data_root


def _frontmatter(node_id: str, chunk_meta: dict, node_attrs: dict, graph_node_ids: list[str]) -> str:
    payload = {
        "chunk_id": chunk_meta["chunk_id"],
        "node_id": node_id,
        "chunk_type": "excel_bucket",
        "factory": node_attrs["factory"],
        "source": chunk_meta["source"],
        "sheet": chunk_meta.get("sheet"),
        "excel_row": chunk_meta.get("excel_row"),
        "excel_cell_ni": chunk_meta.get("excel_cell_ni"),
        "excel_cell_cu": chunk_meta.get("excel_cell_cu"),
        "graph_node_ids": graph_node_ids,
        "metal": node_attrs["metal"],
        "tonnes": node_attrs["tonnes"],
        "recoverable": node_attrs["recoverable"],
        "mineral_form": node_attrs["mineral_form"],
        "size_class": node_attrs["size_class"],
    }

    lines = [f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in payload.items()]

    return "\n".join(lines)


def export_factory(factory: str, data_root: Path, out_dir: Path) -> int:
    relative = next((path for fac, path in EXCEL_SOURCES if fac == factory), None)

    if relative is None:
        raise SystemExit(f"Unknown factory: {factory}")

    excel_path = data_root / relative
    parsed = parse_excel_file(excel_path, factory)
    factory_dir = out_dir / factory.replace(" ", "_")
    factory_dir.mkdir(parents=True, exist_ok=True)
    chunks_by_id = {chunk.chunk_id: chunk for chunk in parsed.chunks}
    written = 0

    for node in parsed.nodes:
        chunk = chunks_by_id.get(f"excel_{node.node_id}")

        if chunk is None:
            continue

        meta = {
            "chunk_id": chunk.chunk_id,
            "source": chunk.source,
            "node_id": node.node_id,
            **chunk.metadata,
        }
        body = (
            f"# {node.label}\n\n"
            f"{chunk.text}\n\n"
            f"## Метаданные графа\n\n"
            f"- `node_id`: `{node.node_id}`\n"
            f"- recoverable: **{node.attributes.get('recoverable')}**\n"
        )
        front = _frontmatter(node.node_id, meta, node.attributes, chunk.graph_node_ids)
        path = factory_dir / f"{node.node_id}.md"
        path.write_text(f"---\n{front}\n---\n\n{body}", encoding="utf-8")
        written += 1

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Excel buckets to Markdown")
    parser.add_argument("--factory", action="append", help="КГМК, ТОФ, … (default: all)")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("Задача 1. Фабрика гипотез/Задача 1/md/buckets"),
        help="Output directory for .md files",
    )
    parser.add_argument("--data-root", type=Path, default=None)
    args = parser.parse_args()

    data_root = resolve_data_root(args.data_root)
    factories = args.factory or [fac for fac, _ in EXCEL_SOURCES]
    total = 0

    for factory in factories:
        count = export_factory(factory, data_root, args.out)
        print(f"{factory}: {count} markdown files → {args.out}")
        total += count

    print(f"Total: {total} files")


if __name__ == "__main__":
    main()
