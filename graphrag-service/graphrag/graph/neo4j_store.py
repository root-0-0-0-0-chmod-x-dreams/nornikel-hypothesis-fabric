"""Neo4j graph backend."""

from __future__ import annotations

from typing import Any

from neo4j import GraphDatabase, Session

from graphrag.config import Neo4jConfig
from graphrag.constants import (
    DEFAULT_MAX_HOPS,
    DEFAULT_MAX_PATHS,
    DEFAULT_RELATION,
    NEO4J_ENTITY_LABEL,
)
from graphrag.models import GraphEdge, GraphNode, GraphPath


class Neo4jGraphStore:
    def __init__(self, config: Neo4jConfig) -> None:
        self._config = config
        self._driver = GraphDatabase.driver(
            config.uri,
            auth=(config.user, config.password),
        )

    @classmethod
    def from_env(cls) -> Neo4jGraphStore:
        return cls(Neo4jConfig.from_env())

    def close(self) -> None:
        self._driver.close()

    def _session(self) -> Session:
        return self._driver.session(database=self._config.database)

    def add_node(self, node: GraphNode) -> None:
        props: dict[str, Any] = {
            "node_id": node.node_id,
            "node_type": node.node_type,
            "label": node.label or node.node_id,
            **node.attributes,
        }
        cypher = f"""
        MERGE (n:{NEO4J_ENTITY_LABEL} {{node_id: $node_id}})
        SET n += $props
        """
        with self._session() as session:
            session.run(cypher, node_id=node.node_id, props=props)

    def add_edge(self, edge: GraphEdge) -> None:
        rel = _sanitize_rel_type(edge.relation)
        cypher = f"""
        MATCH (a:{NEO4J_ENTITY_LABEL} {{node_id: $source}})
        MATCH (b:{NEO4J_ENTITY_LABEL} {{node_id: $target}})
        MERGE (a)-[r:{rel}]->(b)
        SET r += $props
        """
        with self._session() as session:
            session.run(
                cypher,
                source=edge.source,
                target=edge.target,
                props=edge.attributes,
            )

    def has_node(self, node_id: str) -> bool:
        cypher = f"""
        MATCH (n:{NEO4J_ENTITY_LABEL} {{node_id: $node_id}})
        RETURN n LIMIT 1
        """
        with self._session() as session:
            record = session.run(cypher, node_id=node_id).single()

        return record is not None

    def get_node_attributes(self, node_id: str) -> dict | None:
        cypher = f"""
        MATCH (n:{NEO4J_ENTITY_LABEL} {{node_id: $node_id}})
        RETURN properties(n) AS props
        """
        with self._session() as session:
            record = session.run(cypher, node_id=node_id).single()

        if record is None:
            return None

        props = dict(record["props"])
        props.pop("node_id", None)

        return props

    def neighbors(
        self,
        node_id: str,
        *,
        relations: frozenset[str] | None = None,
    ) -> list[str]:
        if not self.has_node(node_id):
            return []

        rel_pattern = _relation_pattern(relations)
        cypher = f"""
        MATCH (n:{NEO4J_ENTITY_LABEL} {{node_id: $node_id}})
              -[{rel_pattern}]->(m:{NEO4J_ENTITY_LABEL})
        RETURN DISTINCT m.node_id AS node_id
        """
        with self._session() as session:
            records = session.run(cypher, node_id=node_id)

            return [str(record["node_id"]) for record in records]

    def get_edge_attributes(self, source: str, target: str) -> dict | None:
        cypher = f"""
        MATCH (a:{NEO4J_ENTITY_LABEL} {{node_id: $source}})
              -[r]->(b:{NEO4J_ENTITY_LABEL} {{node_id: $target}})
        RETURN properties(r) AS props
        LIMIT 1
        """
        with self._session() as session:
            record = session.run(cypher, source=source, target=target).single()

        if record is None:
            return None

        props = dict(record["props"] or {})

        return props

    def clear(self) -> None:
        cypher = f"MATCH (n:{NEO4J_ENTITY_LABEL}) DETACH DELETE n"
        with self._session() as session:
            session.run(cypher)

    def traverse(
        self,
        start_id: str,
        *,
        max_hops: int = DEFAULT_MAX_HOPS,
        max_paths: int = DEFAULT_MAX_PATHS,
        relations: frozenset[str] | None = None,
    ) -> tuple[list[GraphPath], list[str]]:
        if not self.has_node(start_id):
            return [], []

        rel_pattern = _relation_pattern(relations)
        path_cypher = f"""
        MATCH (start:{NEO4J_ENTITY_LABEL} {{node_id: $start_id}})
        MATCH path = (start)-[{rel_pattern}*1..{max_hops}]->(end)
        RETURN path
        LIMIT $max_paths
        """
        nodes_cypher = f"""
        MATCH (start:{NEO4J_ENTITY_LABEL} {{node_id: $start_id}})
        OPTIONAL MATCH (start)-[{rel_pattern}*1..{max_hops}]->(n)
        RETURN collect(DISTINCT start.node_id) +
               collect(DISTINCT n.node_id) AS node_ids
        """

        paths: list[GraphPath] = []
        node_ids: list[str] = [start_id]

        with self._session() as session:
            for record in session.run(
                path_cypher,
                start_id=start_id,
                max_paths=max_paths,
            ):
                graph_path = _path_from_neo4j(record["path"])
                if graph_path is not None:
                    paths.append(graph_path)

            node_record = session.run(nodes_cypher, start_id=start_id).single()
            if node_record is not None:
                node_ids = sorted(
                    {nid for nid in node_record["node_ids"] if nid is not None}
                )

        if not paths:
            paths = [GraphPath(nodes=[start_id], edges=[])]

        return paths[:max_paths], node_ids

    def add_nodes_bulk(self, nodes: list[GraphNode], *, batch_size: int = 500) -> None:
        for offset in range(0, len(nodes), batch_size):
            rows = []

            for node in nodes[offset : offset + batch_size]:
                props: dict[str, Any] = {
                    "node_id": node.node_id,
                    "node_type": node.node_type,
                    "label": node.label or node.node_id,
                    **node.attributes,
                }
                rows.append({"node_id": node.node_id, "props": props})

            cypher = f"""
            UNWIND $rows AS row
            MERGE (n:{NEO4J_ENTITY_LABEL} {{node_id: row.node_id}})
            SET n += row.props
            """
            with self._session() as session:
                session.run(cypher, rows=rows)

    def add_edges_bulk(self, edges: list[GraphEdge], *, batch_size: int = 500) -> None:
        grouped: dict[str, list[dict[str, Any]]] = {}

        for edge in edges:
            rel = _sanitize_rel_type(edge.relation)
            grouped.setdefault(rel, []).append(
                {
                    "source": edge.source,
                    "target": edge.target,
                    "props": edge.attributes,
                }
            )

        for rel, rows in grouped.items():
            for offset in range(0, len(rows), batch_size):
                batch = rows[offset : offset + batch_size]
                cypher = f"""
                UNWIND $rows AS row
                MATCH (a:{NEO4J_ENTITY_LABEL} {{node_id: row.source}})
                MATCH (b:{NEO4J_ENTITY_LABEL} {{node_id: row.target}})
                MERGE (a)-[r:{rel}]->(b)
                SET r += row.props
                """
                with self._session() as session:
                    session.run(cypher, rows=batch)


def _sanitize_rel_type(relation: str) -> str:
    cleaned = relation.strip().upper().replace(" ", "_")
    if not cleaned:
        return DEFAULT_RELATION

    return cleaned


def _relation_pattern(relations: frozenset[str] | None) -> str:
    if not relations:
        return ""

    rel_types = "|".join(_sanitize_rel_type(rel) for rel in sorted(relations))

    return rel_types


def _path_from_neo4j(path: Any) -> GraphPath | None:
    nodes = [node["node_id"] for node in path.nodes]
    edges: list[tuple[str, str, str]] = []

    for rel in path.relationships:
        rel_type = rel.type
        edges.append((rel.start_node["node_id"], rel_type, rel.end_node["node_id"]))

    if not nodes:
        return None

    return GraphPath(nodes=nodes, edges=edges)
