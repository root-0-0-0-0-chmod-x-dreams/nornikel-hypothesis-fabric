"""Helpers for Gradio studio."""

from __future__ import annotations

from typing import Any

from graphrag.config import QdrantConfig, RabbitmqConfig
from graphrag.constants import RETRIEVAL_NODE_PREFIXES
from graphrag.graph.base import GraphStoreProtocol
from graphrag.graph.networkx_store import NetworkXGraphStore
from graphrag.models import Chunk
from graphrag.vector_protocol import VectorStoreProtocol


def iter_nodes(graph: GraphStoreProtocol, *, node_type: str | None = None):
    if isinstance(graph, NetworkXGraphStore):
        for node_id, data in graph._graph.nodes(data=True):
            if node_type is None or data.get("node_type") == node_type:
                yield node_id, dict(data)

        return

    if hasattr(graph, "_graph"):
        for node_id, data in graph._graph.nodes(data=True):
            if node_type is None or data.get("node_type") == node_type:
                yield node_id, dict(data)


def loss_form_choices(graph: GraphStoreProtocol) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []

    for node_id, data in iter_nodes(graph, node_type="LossForm"):
        factory = data.get("factory", "?")
        size_class = data.get("size_class", "?")
        form = data.get("mineral_form", "?")
        metal = data.get("metal", "?")
        tonnes = float(data.get("tonnes", 0) or 0)
        recoverable = "✓" if data.get("recoverable") else "✗"
        label = (
            f"{factory} | {size_class} | {form} | {metal} | "
            f"{tonnes:.0f}т | izv:{recoverable}"
        )
        rows.append((label, node_id))

    rows.sort(key=lambda item: item[0])

    return rows


def factories(graph: GraphStoreProtocol) -> list[str]:
    values = {
        str(data.get("factory"))
        for _, data in iter_nodes(graph, node_type="LossForm")
        if data.get("factory")
    }

    return sorted(values)


def node_row(graph: GraphStoreProtocol, node_id: str) -> list[list[Any]]:
    if not graph.has_node(node_id):
        return [["—", "node not found"]]

    attrs = graph.get_node_attributes(node_id) or {}

    return [
        ["node_id", node_id],
        ["node_type", attrs.get("node_type", "")],
        ["label", attrs.get("label", "")],
        *[
            [key, value]
            for key, value in sorted(attrs.items())
            if key not in {"node_type", "label"}
        ],
    ]


def neighbors_table(
    graph: GraphStoreProtocol,
    node_id: str,
    *,
    direction: str = "out",
) -> list[list[Any]]:
    if not isinstance(graph, NetworkXGraphStore):
        return [["—", "neighbor table needs networkx backend"]]

    rows: list[list[Any]] = []

    if direction in {"out", "both"}:
        for nxt in graph._graph.successors(node_id):
            rel = graph._graph.edges[node_id, nxt].get("relation", "")
            rows.append([node_id, rel, nxt, "out"])

    if direction in {"in", "both"}:
        for src in graph._graph.predecessors(node_id):
            rel = graph._graph.edges[src, node_id].get("relation", "")
            rows.append([src, rel, node_id, "in"])

    return rows or [["—", "—", "no edges", "—"]]


def chunks_for_nodes(
    vectors: VectorStoreProtocol,
    node_ids: list[str],
    *,
    limit: int = 30,
) -> list[list[Any]]:
    hits = vectors.fetch_by_graph_nodes(node_ids, k=limit)
    rows: list[list[Any]] = []

    for chunk_id, score in hits:
        chunk = vectors.get(chunk_id)

        if chunk is None:
            continue

        rows.append(
            [
                chunk_id,
                f"{score:.3f}",
                chunk.chunk_type,
                chunk.source,
                chunk.factory or "",
                ", ".join(chunk.graph_node_ids[:5]),
                chunk.text[:200].replace("\n", " "),
            ]
        )

    return rows or [["—", "—", "—", "—", "—", "—", "no hits"]]


def chunk_search_rows(
    vectors: VectorStoreProtocol,
    query: str,
    mode: str,
    *,
    factory: str | None,
    k: int,
) -> list[list[Any]]:
    if not query.strip():
        return []

    searchers = {
        "hybrid": lambda: vectors.hybrid_search(query, k=k, factory=factory or None)
        if hasattr(vectors, "hybrid_search")
        else [],
        "dense": lambda: vectors.dense_search(query, k=k, factory=factory or None),
        "bm25": lambda: vectors.bm25_search(query, k=k, factory=factory or None),
    }
    hits = searchers.get(mode, searchers["hybrid"])()
    rows: list[list[Any]] = []

    for chunk_id, score in hits:
        chunk = vectors.get(chunk_id)

        if chunk is None:
            continue

        rows.append(
            [
                chunk_id,
                f"{score:.4f}",
                chunk.chunk_type,
                chunk.source,
                chunk.factory or "",
                chunk.text[:250].replace("\n", " "),
            ]
        )

    return rows


def infra_status() -> list[list[str]]:
    rows: list[list[str]] = []

    qcfg = QdrantConfig.from_env()

    try:
        from graphrag.qdrant_store import _create_qdrant_client

        client = _create_qdrant_client(qcfg.url)
        exists = client.collection_exists(qcfg.collection)
        points = client.get_collection(qcfg.collection).points_count if exists else 0
        rows.append(["Qdrant", qcfg.url, "ok", str(points)])
    except Exception as exc:  # noqa: BLE001
        rows.append(["Qdrant", qcfg.url, "error", str(exc)])

    try:
        rcfg = RabbitmqConfig.from_env()
        from graphrag.messaging.broker import connect

        conn = connect(rcfg)
        conn.close()
        rows.append(["RabbitMQ", rcfg.url, "ok", rcfg.exchange])
    except Exception as exc:  # noqa: BLE001
        rows.append(["RabbitMQ", RabbitmqConfig.from_env().url, "error", str(exc)])

    try:
        from graphrag.config import Neo4jConfig
        from neo4j import GraphDatabase

        ncfg = Neo4jConfig.from_env()
        driver = GraphDatabase.driver(
            ncfg.uri,
            auth=(ncfg.user, ncfg.password),
        )
        with driver.session(database=ncfg.database) as session:
            session.run("RETURN 1").single()
        driver.close()
        rows.append(["Neo4j", ncfg.uri, "ok", "bolt alive"])
    except Exception as exc:  # noqa: BLE001
        rows.append(["Neo4j", "bolt://localhost:7687", "error", str(exc)])

    return rows


def retrieval_node_labels(graph: GraphStoreProtocol) -> list[str]:
    labels: list[str] = []

    for prefix in RETRIEVAL_NODE_PREFIXES:
        for node_id, data in iter_nodes(graph):
            if node_id.startswith(prefix):
                labels.append(f"{node_id} — {data.get('label', '')}")

    return sorted(set(labels))[:200]
