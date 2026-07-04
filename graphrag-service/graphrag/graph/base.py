"""Graph store protocol."""

from __future__ import annotations

from typing import Protocol

from graphrag.models import GraphEdge, GraphNode, GraphPath


class GraphStoreProtocol(Protocol):
    def add_node(self, node: GraphNode) -> None: ...

    def add_edge(self, edge: GraphEdge) -> None: ...

    def has_node(self, node_id: str) -> bool: ...

    def get_node_attributes(self, node_id: str) -> dict | None: ...

    def neighbors(
        self,
        node_id: str,
        *,
        relations: frozenset[str] | None = None,
    ) -> list[str]: ...

    def get_edge_attributes(self, source: str, target: str) -> dict | None: ...

    def traverse(
        self,
        start_id: str,
        *,
        max_hops: int = 3,
        max_paths: int = 20,
        relations: frozenset[str] | None = None,
    ) -> tuple[list[GraphPath], list[str]]: ...

    def clear(self) -> None: ...
