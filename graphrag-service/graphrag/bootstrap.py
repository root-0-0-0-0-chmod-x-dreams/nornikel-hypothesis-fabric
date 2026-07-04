"""Production bootstrap: load real case data."""

from __future__ import annotations

from pathlib import Path

from graphrag.graph import create_graph_store
from graphrag.graph.base import GraphStoreProtocol
from graphrag.ingestion.pipeline import LoadedKnowledgeBase, load_knowledge_base
from graphrag.service import GraphRAGQueryService


def bootstrap(
    data_root: Path | None = None,
    graph_backend: str | None = None,
) -> LoadedKnowledgeBase:
    graph = create_graph_store(graph_backend)

    return load_knowledge_base(data_root=data_root, graph=graph)


def build_service(
    data_root: Path | None = None,
    graph: GraphStoreProtocol | None = None,
) -> GraphRAGQueryService:
    loaded = load_knowledge_base(data_root=data_root, graph=graph)

    return GraphRAGQueryService(loaded.graph, loaded.vectors)
