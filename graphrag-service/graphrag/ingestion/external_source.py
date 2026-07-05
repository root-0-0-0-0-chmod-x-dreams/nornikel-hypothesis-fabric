"""Ingest external web/PDF snippets into graph + vector store with chunked linking."""

from __future__ import annotations

from dataclasses import dataclass, field

from graphrag.constants import BOOK_CHUNK_GRANULARITY
from graphrag.ingestion.book_chunking import chunk_plain_text
from graphrag.ingestion.excel_parser import _slugify
from graphrag.ingestion.pdf_extractors import BookParagraph
from graphrag.ingestion.passage_wiring import wire_passages_incremental
from graphrag.ingestion.pdf_graph_linker import match_entities
from graphrag.models import Chunk, GraphEdge, GraphNode
from graphrag.schema import NodeType, RelationType


@dataclass
class ExternalIngestResult:
    chunks: list[Chunk]
    edges: list[GraphEdge] = field(default_factory=list)
    matched_entities: list[str] = field(default_factory=list)
    source_id: str = ""

    @property
    def chunk(self) -> Chunk:
        return self.chunks[0]


def ingest_external_source(
    *,
    text: str,
    title: str,
    source_url: str | None = None,
    summary: str = "",
    explicit_node_ids: list[str] | None = None,
    auto_link: bool = True,
    granularity: str = BOOK_CHUNK_GRANULARITY,
    nodes_by_id: dict[str, GraphNode] | None = None,
) -> ExternalIngestResult:
    """Create external chunks + EVIDENCED_BY edges to catalog entities."""
    nodes_by_id = nodes_by_id or {}
    source_id = _ensure_source(
        nodes_by_id,
        title=title,
        source_url=source_url,
    )
    source_slug = _slugify(title[:48])
    segments = chunk_plain_text(text, granularity, backend="external")

    if not segments:
        raise ValueError("External source text is empty")

    explicit = {node_id for node_id in (explicit_node_ids or []) if node_id}
    chunks: list[Chunk] = []
    edges: list[GraphEdge] = []
    edge_keys: set[tuple[str, str, str]] = set()
    all_matched: set[str] = set()

    for segment in segments:
        matched = set(explicit)

        if auto_link:
            matched |= match_entities(segment.text.lower())

        matched = {node_id for node_id in matched if node_id}
        all_matched |= matched

        chunk_id = _external_chunk_id(source_slug, segment)
        chunk = Chunk(
            chunk_id=chunk_id,
            text=segment.text,
            summary=summary or title,
            source=title,
            chunk_type="external_text",
            graph_node_ids=sorted({*matched, source_id}),
            external=True,
            source_url=source_url,
            metadata={
                "source_id": source_id,
                "auto_linked": auto_link,
                "granularity": segment.granularity,
                "paragraph_index": segment.paragraph_index,
                "element_type": segment.element_type,
            },
        )
        chunks.append(chunk)

        for entity_id in matched:
            if entity_id not in nodes_by_id:
                nodes_by_id[entity_id] = _placeholder_node(entity_id)

            key = (entity_id, RelationType.EVIDENCED_BY, source_id)

            if key in edge_keys:
                continue

            edge_keys.add(key)
            edges.append(
                GraphEdge(
                    entity_id,
                    source_id,
                    RelationType.EVIDENCED_BY,
                    attributes={
                        "chunk_id": chunk_id,
                        "paragraph_index": segment.paragraph_index,
                        "granularity": segment.granularity,
                        "external": True,
                        "source_url": source_url,
                    },
                )
            )

    return ExternalIngestResult(
        chunks=chunks,
        edges=edges,
        matched_entities=sorted(all_matched),
        source_id=source_id,
    )


def apply_external_ingest(
    graph,
    vectors,
    result: ExternalIngestResult,
) -> None:
    """Persist external ingest to graph + Qdrant/memory vectors."""
    if not result.chunks:
        return

    head = result.chunks[0]
    source_node = GraphNode(
        node_id=result.source_id,
        node_type=NodeType.SOURCE,
        label=head.source,
        attributes={
            "source_type": "external",
            "source_url": head.source_url,
            "source_file": head.source,
            "chunk_count": len(result.chunks),
        },
    )

    if not graph.has_node(result.source_id):
        graph.add_node(source_node)

    for edge in result.edges:
        if not graph.has_node(edge.source):
            graph.add_node(_placeholder_node(edge.source))

        graph.add_edge(edge)

    if hasattr(vectors, "upsert_many"):
        vectors.upsert_many(result.chunks)
    else:
        vectors.add_many(result.chunks)

    wire_passages_incremental(graph, result.chunks)


def _external_chunk_id(source_slug: str, segment: BookParagraph) -> str:
    return (
        f"external_{source_slug}_{segment.granularity}"
        f"_i{segment.paragraph_index}"
    )


def _ensure_source(
    nodes_by_id: dict[str, GraphNode],
    *,
    title: str,
    source_url: str | None,
) -> str:
    source_id = _slugify("source", "external", title)

    if source_id not in nodes_by_id:
        nodes_by_id[source_id] = GraphNode(
            node_id=source_id,
            node_type=NodeType.SOURCE,
            label=title,
            attributes={
                "source_file": title,
                "source_type": "external",
                "source_url": source_url,
            },
        )

    return source_id


def _placeholder_node(node_id: str) -> GraphNode:
    prefix = node_id.split("_", 1)[0]
    type_map = {
        "mech": NodeType.MECHANISM,
        "process": NodeType.PROCESS,
        "equip": NodeType.EQUIPMENT,
        "mineral": NodeType.MINERAL,
        "reagent": NodeType.REAGENT,
        "metal": NodeType.METAL,
    }

    return GraphNode(
        node_id=node_id,
        node_type=type_map.get(prefix, NodeType.MECHANISM),
        label=node_id,
        attributes={"catalog": True},
    )
