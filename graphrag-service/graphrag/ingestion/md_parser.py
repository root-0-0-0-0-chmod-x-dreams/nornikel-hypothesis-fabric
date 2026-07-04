"""Parse Markdown bucket files (YAML frontmatter) into graph + vector chunks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from graphrag.constants import METAL_NI
from graphrag.ingestion.domain import intervention_edges_for_bucket, is_recoverable_form
from graphrag.ingestion.excel_parser import _slugify
from graphrag.ingestion.md_frontmatter import split_frontmatter
from graphrag.models import Chunk, GraphEdge, GraphNode
from graphrag.schema import NodeType


@dataclass
class MdParseResult:
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    chunks: list[Chunk]


def parse_md_buckets(data_root: Path) -> MdParseResult:
    """Load bucket MD only from md/buckets/**/*.md."""
    paths = sorted(data_root.glob("md/buckets/**/*.md"))

    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    chunks: list[Chunk] = []

    for path in paths:
        parsed = parse_md_bucket_file(path)

        if parsed is None:
            continue

        nodes.append(parsed.node)
        edges.extend(parsed.edges)
        chunks.append(parsed.chunk)

    return MdParseResult(nodes=nodes, edges=edges, chunks=chunks)


def parse_md_bucket_file(path: Path) -> _MdBucket | None:
    raw = path.read_text(encoding="utf-8")
    meta, body = split_frontmatter(raw)

    if not meta.get("factory") and meta.get("chunk_type") != "excel_bucket":
        return None

    factory = str(meta.get("factory") or "")
    size_class = str(meta.get("size_class") or "")
    mineral_form = str(meta.get("mineral_form") or "")
    metal = str(meta.get("metal") or METAL_NI)
    tonnes = float(meta.get("tonnes") or 0)
    recoverable = bool(meta.get("recoverable", is_recoverable_form(mineral_form, metal)))

    node_id = str(
        meta.get("graph_node_id")
        or meta.get("node_id")
        or _slugify("lossform", factory, size_class, mineral_form, metal)
    )
    chunk_id = str(meta.get("chunk_id") or f"excel_{node_id}")
    form_label = mineral_form.replace("_", " ")

    node = GraphNode(
        node_id=node_id,
        node_type=NodeType.LOSS_FORM,
        label=str(meta.get("title") or f"{factory} {size_class} {form_label} {metal}"),
        attributes={
            "factory": factory,
            "size_class": size_class,
            "mineral_form": mineral_form,
            "metal": metal,
            "tonnes": round(tonnes, 2),
            "recoverable": recoverable,
            "source_file": str(meta.get("source") or path.name),
            "md_path": str(path),
        },
    )

    graph_node_ids = list(meta.get("graph_node_ids") or [node_id])
    metadata = {
        key: meta[key]
        for key in (
            "sheet",
            "excel_row",
            "excel_cell_ni",
            "excel_cell_cu",
            "metal",
        )
        if key in meta
    }
    metadata["md_path"] = str(path)

    chunk = Chunk(
        chunk_id=chunk_id,
        text=body or _default_bucket_text(node.attributes),
        summary=str(meta.get("summary") or node.label),
        source=str(meta.get("source") or path.name),
        factory=factory or None,
        chunk_type=str(meta.get("chunk_type") or "excel_bucket"),
        graph_node_ids=graph_node_ids,
        metadata=metadata,
    )

    edge_list: list[GraphEdge] = []

    for source, relation, target in intervention_edges_for_bucket(
        bucket_node_id=node_id,
        form_slug=mineral_form,
        size_class=size_class,
        metal=metal,
        recoverable=recoverable,
    ):
        edge_list.append(GraphEdge(source, target, relation))

    return _MdBucket(node=node, edges=edge_list, chunk=chunk)


@dataclass
class _MdBucket:
    node: GraphNode
    edges: list[GraphEdge]
    chunk: Chunk


def _default_bucket_text(attrs: dict) -> str:
    return (
        f"Фабрика {attrs.get('factory')}. Класс {attrs.get('size_class')}. "
        f"Форма: {attrs.get('mineral_form')}. Потери {attrs.get('metal')}: "
        f"{attrs.get('tonnes')} т. Извлекаемо: {'да' if attrs.get('recoverable') else 'нет'}."
    )
