"""Scheme and regulation image metadata chunks."""

from __future__ import annotations

from pathlib import Path

from graphrag.models import Chunk

SCHEME_NODE_HINTS: dict[str, list[str]] = {
    "Схема 5": ["equip_mshr", "equip_mshc", "equip_gc660", "process_comminution"],
    "Схема 6": ["equip_fpm", "process_flotation"],
    "Схема 3": ["process_flotation"],
    "Регламент 1": ["equip_fpm", "process_flotation"],
}


def _graph_nodes_for_file(path: Path) -> list[str]:
    for prefix, node_ids in SCHEME_NODE_HINTS.items():
        if path.stem.startswith(prefix):
            return node_ids

    return []


def image_to_chunk(path: Path, factory: str | None = None) -> Chunk:
    node_ids = _graph_nodes_for_file(path)
    hint = f" Связанные узлы графа: {', '.join(node_ids)}." if node_ids else ""

    return Chunk(
        chunk_id=f"image_{path.stem}",
        text=(
            f"Иллюстрация {path.name} из базы знаний Норникель.{hint} "
            "Детальный разбор — через VLM tool."
        ),
        summary=path.stem,
        source=path.name,
        factory=factory,
        chunk_type="scheme_caption",
        graph_node_ids=node_ids,
        metadata={"image_path": str(path)},
    )


def parse_image_files(paths: list[Path], factory: str | None = None) -> list[Chunk]:
    return [image_to_chunk(path, factory=factory) for path in paths]
