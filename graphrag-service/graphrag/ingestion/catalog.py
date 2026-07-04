"""Static catalog nodes (equipment, process, mechanism)."""

from __future__ import annotations

from graphrag.ingestion.domain import (
    EQUIPMENT_CATALOG,
    MECHANISM_CATALOG,
    PROCESS_CATALOG,
)
from graphrag.models import GraphNode


def build_catalog_nodes() -> list[GraphNode]:
    nodes: list[GraphNode] = []

    for node_id, label, node_type in (
        *EQUIPMENT_CATALOG,
        *PROCESS_CATALOG,
        *MECHANISM_CATALOG,
    ):
        nodes.append(
            GraphNode(
                node_id=node_id,
                node_type=node_type,
                label=label,
                attributes={"catalog": True},
            )
        )

    return nodes
