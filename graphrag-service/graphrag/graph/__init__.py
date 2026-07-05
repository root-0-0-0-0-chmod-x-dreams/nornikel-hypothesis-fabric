"""Graph store factory."""

from __future__ import annotations

from graphrag.config import AppConfig, Neo4jConfig
from graphrag.constants import GRAPH_BACKEND_NEO4J
from graphrag.graph.base import GraphStoreProtocol
from graphrag.graph.neo4j_store import Neo4jGraphStore
from graphrag.graph.networkx_store import NetworkXGraphStore


def create_graph_store(
    backend: str | None = None,
    *,
    neo4j_config: Neo4jConfig | None = None,
) -> GraphStoreProtocol:
    config = AppConfig.from_env()
    selected = backend or config.graph_backend

    if selected == GRAPH_BACKEND_NEO4J:
        if neo4j_config is not None:
            return Neo4jGraphStore(neo4j_config)

        return Neo4jGraphStore.from_env()

    return NetworkXGraphStore()
