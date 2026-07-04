"""Enrich retrieval queries with graph/bucket context (HyDE-lite)."""

from __future__ import annotations

from graphrag.graph.base import GraphStoreProtocol
from graphrag.ingestion.domain import FORM_LABEL_BY_SLUG
from graphrag.query_expansion import expand_query, mineral_label


def build_enriched_query(
    question: str,
    graph: GraphStoreProtocol,
    bucket_id: str | None,
    retrieval_nodes: list[str] | None = None,
    *,
    factory: str | None = None,
    budget_tier: str | None = None,
) -> str:
    """Question + bucket attrs + on-path entity labels for dense/hybrid search."""
    parts = [question.strip()]

    if factory:
        parts.append(factory)

    if budget_tier:
        parts.append(f"бюджет {budget_tier}")

    if bucket_id and graph.has_node(bucket_id):
        attrs = graph.get_node_attributes(bucket_id) or {}
        factory = attrs.get("factory")
        size_class = attrs.get("size_class")
        form_slug = attrs.get("mineral_form")
        metal = attrs.get("metal")

        if factory:
            parts.append(str(factory))

        if size_class:
            parts.append(f"класс {size_class}")

        if form_slug:
            parts.append(mineral_label(str(form_slug)))

        if metal:
            parts.append("никель" if str(metal) == "Ni" else "медь")

    for node_id in retrieval_nodes or []:
        label = _node_label(graph, node_id)

        if label:
            parts.append(label)

    merged = " ".join(part for part in parts if part)

    return expand_query(merged)


def _node_label(graph: GraphStoreProtocol, node_id: str) -> str:
    if not graph.has_node(node_id):
        return ""

    attrs = graph.get_node_attributes(node_id) or {}
    label = attrs.get("label")

    if label:
        return str(label)

    if node_id.startswith("mineral_"):
        slug = node_id.removeprefix("mineral_")

        return FORM_LABEL_BY_SLUG.get(slug, slug.replace("_", " "))

    return ""
