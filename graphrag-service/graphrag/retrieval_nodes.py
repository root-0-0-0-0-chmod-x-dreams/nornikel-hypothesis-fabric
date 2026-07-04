"""Filter and expand graph node ids used for GraphRAG retrieval."""

from __future__ import annotations

from graphrag.constants import EVIDENCE_RELATIONS, RETRIEVAL_NODE_PREFIXES
from graphrag.graph.base import GraphStoreProtocol
from graphrag.ingestion.excel_parser import _slugify


def filter_retrieval_node_ids(node_ids: list[str]) -> list[str]:
    """Keep only node ids that map to indexed text chunks."""
    return [
        node_id
        for node_id in node_ids
        if node_id.startswith(RETRIEVAL_NODE_PREFIXES)
    ]


def expand_retrieval_nodes(
    graph: GraphStoreProtocol,
    bucket_id: str | None,
    intervention_nodes: list[str],
) -> list[str]:
    """ABC path + mineral of bucket + entities with literature evidence on-path."""
    nodes: set[str] = set(filter_retrieval_node_ids(intervention_nodes))

    if bucket_id and graph.has_node(bucket_id):
        attrs = graph.get_node_attributes(bucket_id) or {}
        form_slug = attrs.get("mineral_form")

        if form_slug:
            nodes.add(_slugify("mineral", str(form_slug)))

    for node_id in list(nodes):
        for neighbor in graph.neighbors(node_id, relations=EVIDENCE_RELATIONS):
            if neighbor.startswith("source_"):
                continue

            if neighbor.startswith(
                ("mech_", "process_", "equip_", "mineral_", "reagent_")
            ):
                nodes.add(neighbor)

    return sorted(nodes)
