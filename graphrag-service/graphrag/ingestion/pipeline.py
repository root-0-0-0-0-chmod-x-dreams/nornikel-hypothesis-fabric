"""Load customer knowledge base into graph + vector store."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from graphrag.graph.base import GraphStoreProtocol
from graphrag.graph.networkx_store import NetworkXGraphStore
from graphrag.ingestion.catalog import build_catalog_nodes
from graphrag.ingestion.constraints import (
    build_constraint_chunks,
    build_factory_equipment_edges,
)
from graphrag.ingestion.excel_parser import _slugify, parse_excel_file
from graphrag.ingestion.md_book_parser import parse_md_books
from graphrag.ingestion.md_monolithic_parser import parse_literature_md
from graphrag.ingestion.md_parser import parse_md_buckets
from graphrag.ingestion.pdf_graph_linker import (
    ensure_reagent_catalog_nodes,
    link_pdf_chunks_to_graph,
)
from graphrag.ingestion.ontology_wiring import enrich_graph
from graphrag.ingestion.passage_wiring import wire_passages
from graphrag.ingestion.paths import (
    DEFAULT_DATA_ROOT,
    EXCEL_SOURCES,
    resolve_data_root,
    resolve_literature_root,
)
from graphrag.ingestion.pdf_parser import parse_pdf_file
from graphrag.ingestion.schemes import parse_image_files
from graphrag.constants import BOOK_CHUNK_GRANULARITY
from graphrag.schema import NodeType
from graphrag.vector_factory import create_vector_store
from graphrag.vector_protocol import VectorStoreProtocol


@dataclass
class LoadedKnowledgeBase:
    graph: GraphStoreProtocol
    vectors: VectorStoreProtocol
    stats: dict[str, int] = field(default_factory=dict)


class KnowledgeBaseLoader:
    def __init__(self, data_root: Path | None = None) -> None:
        self._data_root = resolve_data_root(data_root)

    def load(
        self,
        graph: GraphStoreProtocol | None = None,
        vectors: VectorStoreProtocol | None = None,
        *,
        reload_vectors: bool | None = None,
    ) -> LoadedKnowledgeBase:
        store = graph or NetworkXGraphStore()
        vector_store = vectors or create_vector_store()
        should_reload_vectors = (
            reload_vectors
            if reload_vectors is not None
            else not _qdrant_has_indexed_data(vector_store)
        )

        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        chunks: list[Chunk] = []

        nodes.extend(build_catalog_nodes())

        md_result = parse_md_buckets(self._data_root)

        if md_result.chunks:
            nodes.extend(md_result.nodes)
            edges.extend(md_result.edges)
            chunks.extend(md_result.chunks)
        else:
            for factory, relative_path in EXCEL_SOURCES:
                excel_path = self._data_root / relative_path

                if not excel_path.is_file():
                    continue

                parsed = parse_excel_file(excel_path, factory)
                nodes.extend(parsed.nodes)
                edges.extend(parsed.edges)
                chunks.extend(parsed.chunks)

        book_result = parse_md_books(self._data_root)
        chunks.extend(book_result.chunks)
        books = list(book_result.books)

        loaded_doc_ids = {
            str(chunk.metadata.get("doc_id"))
            for chunk in book_result.chunks
            if chunk.metadata.get("doc_id")
        }

        literature_result = parse_literature_md(resolve_literature_root())

        if literature_result.chunks:
            for chunk in literature_result.chunks:
                doc_id = str(chunk.metadata.get("doc_id") or "")

                if doc_id and doc_id in loaded_doc_ids:
                    continue

                chunks.append(chunk)

            books = sorted(
                set(books)
                | {
                    book
                    for book in literature_result.books
                    if _slugify(book) not in loaded_doc_ids
                }
            )

        if book_result.chunks or literature_result.chunks:
            pdf_paths: list[Path] = []
        else:
            pdf_paths = sorted(self._data_root.glob("Дополнительные материалы/*.pdf"))

        for pdf_path in pdf_paths:
            chunks.extend(parse_pdf_file(pdf_path))

        scheme_paths = sorted(self._data_root.glob("Схемы флотации/*.png"))
        scheme_paths += sorted(self._data_root.glob("Схемы флотации/*.PNG"))
        chunks.extend(parse_image_files(scheme_paths))

        regulation_paths = sorted(self._data_root.glob("Регламенты/*.png"))
        chunks.extend(parse_image_files(regulation_paths))

        nodes_by_id = {node.node_id: node for node in nodes}
        ensure_reagent_catalog_nodes(nodes_by_id)
        pdf_links = link_pdf_chunks_to_graph(chunks, nodes_by_id)
        chunks = pdf_links.chunks
        edges.extend(pdf_links.edges)
        nodes = list(nodes_by_id.values())

        nodes, edges = enrich_graph(nodes, edges, chunks)

        nodes_by_id = {node.node_id: node for node in nodes}
        edges.extend(build_factory_equipment_edges(nodes_by_id))
        nodes = list(nodes_by_id.values())
        chunks.extend(build_constraint_chunks())

        passage_result = wire_passages(nodes, edges, chunks)
        nodes = passage_result.nodes
        edges = passage_result.edges

        self._apply_to_stores(
            store,
            vector_store,
            nodes,
            edges,
            chunks,
            reload_vectors=should_reload_vectors,
        )

        return LoadedKnowledgeBase(
            graph=store,
            vectors=vector_store,
            stats={
                "nodes": len(nodes),
                "edges": len(edges),
                "chunks": len(chunks),
                "loss_forms": sum(
                    1 for node in nodes if node.node_type == NodeType.LOSS_FORM
                ),
                "pdf_linked_chunks": pdf_links.linked_chunks,
                "literature_edges": pdf_links.literature_edges,
                "constraint_chunks": sum(
                    1
                    for chunk in chunks
                    if chunk.chunk_type.startswith("constraint_")
                ),
                "md_buckets": sum(
                    1 for chunk in chunks if chunk.metadata.get("md_path") and chunk.chunk_type == "excel_bucket"
                ),
                "book_chunks": sum(1 for chunk in chunks if chunk.chunk_type == "book_text"),
                "book_granularity": (
                    next(
                        (
                            chunk.metadata.get("granularity")
                            for chunk in chunks
                            if chunk.chunk_type == "book_text"
                        ),
                        BOOK_CHUNK_GRANULARITY,
                    )
                ),
                "books": books,
                "passage_nodes": passage_result.passage_count,
                "passage_topic_edges": passage_result.topic_edges,
                "passage_sequence_edges": passage_result.sequence_edges,
                "hypothesis_literature_links": passage_result.hypothesis_links,
                "related_source_edges": passage_result.source_links,
            },
        )

    @staticmethod
    def _apply_to_stores(
        graph: GraphStoreProtocol,
        vectors: VectorStoreProtocol,
        nodes: list[GraphNode],
        edges: list[GraphEdge],
        chunks: list[Chunk],
        *,
        reload_vectors: bool = True,
    ) -> None:
        if hasattr(graph, "clear"):
            graph.clear()

        if reload_vectors and hasattr(vectors, "clear"):
            vectors.clear()

        for node in nodes:
            graph.add_node(node)

        seen_edges: set[tuple[str, str, str]] = set()

        for edge in edges:
            key = (edge.source, edge.relation, edge.target)

            if key in seen_edges:
                continue

            seen_edges.add(key)
            graph.add_edge(edge)

        if reload_vectors:
            vectors.add_many(chunks)


def load_knowledge_base(
    data_root: Path | None = None,
    graph: GraphStoreProtocol | None = None,
    vectors: VectorStoreProtocol | None = None,
    *,
    reload_vectors: bool | None = None,
) -> LoadedKnowledgeBase:
    loader = KnowledgeBaseLoader(data_root or DEFAULT_DATA_ROOT)

    return loader.load(graph=graph, vectors=vectors, reload_vectors=reload_vectors)


def _qdrant_has_indexed_data(vector_store: VectorStoreProtocol, *, min_points: int = 100) -> bool:
    client = getattr(vector_store, "_client", None)
    collection = getattr(vector_store, "_collection", None)

    if client is None or collection is None:
        return False

    if not client.collection_exists(collection):
        return False

    return int(client.get_collection(collection).points_count) >= min_points
