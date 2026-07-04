"""Ingest raw Markdown (YAML frontmatter) from external services via RMQ."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from graphrag.ingestion.md_book_parser import parse_md_book_raw
from graphrag.ingestion.md_frontmatter import split_frontmatter
from graphrag.ingestion.md_parser import parse_md_bucket_raw
from graphrag.ingestion.passage_wiring import wire_passages_incremental
from graphrag.ingestion.pdf_graph_linker import link_pdf_chunks_to_graph
from graphrag.models import Chunk, GraphEdge, GraphNode


@dataclass
class MdIngestResult:
    chunks: list[Chunk] = field(default_factory=list)
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    source_path: str = ""

    @property
    def chunk_ids(self) -> list[str]:
        return [chunk.chunk_id for chunk in self.chunks]


def ingest_markdown_document(
    markdown: str,
    *,
    source_path: str | None = None,
    source_url: str | None = None,
    auto_link: bool = True,
    factory: str | None = None,
) -> MdIngestResult:
    """Parse one MD document into graph nodes/edges + vector chunks."""
    raw = markdown.strip()

    if not raw:
        raise ValueError("markdown is empty")

    label = source_path or "upload.md"
    meta, _body = split_frontmatter(raw)

    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    chunks: list[Chunk] = []

    bucket = parse_md_bucket_raw(raw, source_label=label)

    if bucket is not None:
        nodes.append(bucket.node)
        edges.extend(bucket.edges)
        chunks.append(bucket.chunk)
    else:
        chunks.extend(parse_md_book_raw(raw, source_label=label))

    if not chunks:
        raise ValueError("no chunks parsed from markdown; check frontmatter")

    if factory:
        for chunk in chunks:
            chunk.factory = factory

    if source_url:
        for chunk in chunks:
            chunk.source_url = source_url
            chunk.metadata.setdefault("source_url", source_url)

    if auto_link:
        nodes_by_id = {node.node_id: node for node in nodes}
        linked = link_pdf_chunks_to_graph(chunks, nodes_by_id)
        chunks = linked.chunks
        edges.extend(linked.edges)
        nodes = list(nodes_by_id.values())

    for chunk in chunks:
        chunk.metadata.setdefault("source_path", label)
        chunk.metadata.setdefault("original_format", meta.get("original_format"))

    return MdIngestResult(
        chunks=chunks,
        nodes=nodes,
        edges=edges,
        source_path=label,
    )


def apply_md_ingest(graph, vectors, result: MdIngestResult) -> None:
    """Persist parsed markdown into live graph + vector store."""
    for node in result.nodes:
        if not graph.has_node(node.node_id):
            graph.add_node(node)

    seen: set[tuple[str, str, str]] = set()

    for edge in result.edges:
        key = (edge.source, edge.relation, edge.target)

        if key in seen:
            continue

        seen.add(key)

        if not graph.has_node(edge.source):
            continue

        if not graph.has_node(edge.target):
            continue

        graph.add_edge(edge)

    if hasattr(vectors, "upsert_many"):
        vectors.upsert_many(result.chunks)
    else:
        vectors.add_many(result.chunks)

    wire_passages_incremental(graph, result.chunks)
