"""NetworkX in-memory graph (dev / tests)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import networkx as nx

from graphrag.constants import DEFAULT_MAX_HOPS, DEFAULT_MAX_PATHS, DEFAULT_RELATION
from graphrag.models import GraphEdge, GraphNode, GraphPath


class NetworkXGraphStore:
    def __init__(self) -> None:
        self._graph = nx.DiGraph()

    def add_node(self, node: GraphNode) -> None:
        self._graph.add_node(
            node.node_id,
            node_type=node.node_type,
            label=node.label or node.node_id,
            **node.attributes,
        )

    def add_edge(self, edge: GraphEdge) -> None:
        self._graph.add_edge(
            edge.source,
            edge.target,
            relation=edge.relation,
            **edge.attributes,
        )

    def has_node(self, node_id: str) -> bool:
        return self._graph.has_node(node_id)

    def get_node_attributes(self, node_id: str) -> dict[str, Any] | None:
        if not self._graph.has_node(node_id):
            return None

        return dict(self._graph.nodes[node_id])

    def neighbors(
        self,
        node_id: str,
        *,
        relations: frozenset[str] | None = None,
    ) -> list[str]:
        if not self._graph.has_node(node_id):
            return []

        matched: list[str] = []

        for nxt in self._graph.successors(node_id):
            rel = self._graph.edges[node_id, nxt].get("relation", DEFAULT_RELATION)

            if relations is None or rel in relations:
                matched.append(nxt)

        return matched

    def get_edge_attributes(self, source: str, target: str) -> dict | None:
        if not self._graph.has_edge(source, target):
            return None

        return dict(self._graph.edges[source, target])

    def clear(self) -> None:
        self._graph.clear()

    def traverse(
        self,
        start_id: str,
        *,
        max_hops: int = DEFAULT_MAX_HOPS,
        max_paths: int = DEFAULT_MAX_PATHS,
        relations: frozenset[str] | None = None,
    ) -> tuple[list[GraphPath], list[str]]:
        if not self._graph.has_node(start_id):
            return [], []

        allowed = relations or None
        paths: list[GraphPath] = []
        visited_nodes: set[str] = {start_id}
        queue: list[tuple[str, list[str], list[tuple[str, str, str]]]] = [
            (start_id, [start_id], [])
        ]

        while queue and len(paths) < max_paths:
            node, node_path, edge_path = queue.pop(0)
            depth = len(node_path) - 1

            if depth >= max_hops:
                continue

            successors = list(self._graph.successors(node))

            if not successors and depth > 0:
                paths.append(GraphPath(nodes=node_path, edges=edge_path))

            for nxt in successors:
                rel = self._graph.edges[node, nxt].get("relation", DEFAULT_RELATION)

                if allowed is not None and rel not in allowed:
                    continue

                new_nodes = node_path + [nxt]
                new_edges = edge_path + [(node, rel, nxt)]
                visited_nodes.add(nxt)

                if depth + 1 >= max_hops or not list(self._graph.successors(nxt)):
                    paths.append(GraphPath(nodes=new_nodes, edges=new_edges))
                else:
                    queue.append((nxt, new_nodes, new_edges))

        if not paths:
            paths = [GraphPath(nodes=[start_id], edges=[])]

        return paths[:max_paths], sorted(visited_nodes)

    def add_nodes_bulk(self, nodes: list[GraphNode]) -> None:
        for node in nodes:
            self.add_node(node)

    def add_edges_bulk(self, edges: list[GraphEdge]) -> None:
        for edge in edges:
            self.add_edge(edge)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [
                {"id": node_id, **data}
                for node_id, data in self._graph.nodes(data=True)
            ],
            "edges": [
                {
                    "source": source,
                    "target": target,
                    "relation": data.get("relation", DEFAULT_RELATION),
                    **{key: value for key, value in data.items() if key != "relation"},
                }
                for source, target, data in self._graph.edges(data=True)
            ],
        }

    def save_json(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load_json(cls, path: str | Path) -> NetworkXGraphStore:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        store = cls()

        for raw_node in data.get("nodes", []):
            node_data = dict(raw_node)
            node_id = node_data.pop("id")
            label = node_data.pop("label", node_id)
            node_type = node_data.pop("node_type", "Unknown")
            store.add_node(
                GraphNode(
                    node_id=node_id,
                    node_type=node_type,
                    label=label,
                    attributes=node_data,
                )
            )

        for raw_edge in data.get("edges", []):
            edge_data = dict(raw_edge)
            store.add_edge(
                GraphEdge(
                    source=edge_data["source"],
                    target=edge_data["target"],
                    relation=edge_data.get("relation", DEFAULT_RELATION),
                    attributes={
                        key: value
                        for key, value in edge_data.items()
                        if key not in ("source", "target", "relation")
                    },
                )
            )

        return store
