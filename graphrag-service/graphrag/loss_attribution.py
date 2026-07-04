"""Loss-Attribution: resolve LossForm buckets from graph data."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from graphrag.graph.base import GraphStoreProtocol
from graphrag.nl_cypher.models import ParsedQuery, QueryIntent
from graphrag.nl_cypher.parser import build_bucket_id


@dataclass
class LossFormRecord:
    bucket_id: str
    tonnes: float
    factory: str | None = None
    metal: str | None = None
    mineral_form: str | None = None
    size_class: str | None = None
    recoverable: bool = True

    @classmethod
    def from_attrs(cls, bucket_id: str, attrs: dict[str, Any]) -> LossFormRecord:
        return cls(
            bucket_id=bucket_id,
            tonnes=float(attrs.get("tonnes") or 0),
            factory=attrs.get("factory"),
            metal=attrs.get("metal"),
            mineral_form=attrs.get("mineral_form"),
            size_class=attrs.get("size_class"),
            recoverable=bool(attrs.get("recoverable", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def list_lossforms(
    graph: GraphStoreProtocol,
    *,
    factory: str | None = None,
    metal: str | None = None,
    recoverable_only: bool = True,
) -> list[LossFormRecord]:
    if hasattr(graph, "_graph"):
        return _from_networkx(graph._graph, factory=factory, metal=metal, recoverable_only=recoverable_only)

    if hasattr(graph, "_session"):
        return _from_neo4j(graph, factory=factory, metal=metal, recoverable_only=recoverable_only)

    return []


def top_lossform(
    graph: GraphStoreProtocol,
    *,
    factory: str | None = None,
    metal: str | None = None,
    recoverable_only: bool = True,
) -> LossFormRecord | None:
    candidates = list_lossforms(
        graph,
        factory=factory,
        metal=metal,
        recoverable_only=recoverable_only,
    )

    if not candidates:
        return None

    return max(candidates, key=lambda item: item.tonnes)


def resolve_bucket_id(
    graph: GraphStoreProtocol,
    parsed: ParsedQuery,
    *,
    bucket_id: str | None = None,
    auto_bucket: bool = True,
) -> tuple[str | None, dict[str, Any]]:
    if bucket_id:
        return bucket_id, {"method": "explicit", "bucket_id": bucket_id}

    if auto_bucket:
        slug = build_bucket_id(parsed)

        if slug and graph.has_node(slug):
            return slug, {
                "method": "slug",
                "bucket_id": slug,
                "parsed_factory": parsed.factory,
                "parsed_metal": parsed.metal,
                "parsed_size_class": parsed.size_class,
                "parsed_form_slug": parsed.form_slug,
            }

    top = top_lossform(
        graph,
        factory=parsed.factory,
        metal=parsed.metal,
        recoverable_only=True,
    )

    if top is None and parsed.factory:
        top = top_lossform(graph, factory=parsed.factory, recoverable_only=True)

    if top is None:
        top = top_lossform(graph, recoverable_only=True)

    if top is None:
        return None, {"method": "none"}

    return top.bucket_id, {
        "method": "loss_attribution_top",
        "bucket_id": top.bucket_id,
        "tonnes": top.tonnes,
        "factory": top.factory,
        "metal": top.metal,
        "mineral_form": top.mineral_form,
        "size_class": top.size_class,
    }


def top_lossforms(
    graph: GraphStoreProtocol,
    *,
    factory: str | None = None,
    metal: str | None = None,
    limit: int = 5,
) -> list[LossFormRecord]:
    items = list_lossforms(graph, factory=factory, metal=metal, recoverable_only=True)
    items.sort(key=lambda item: -item.tonnes)

    return items[:limit]


def is_loss_attribution_intent(intent: QueryIntent) -> bool:
    return intent in {
        QueryIntent.TOP_LOSSES,
        QueryIntent.RECOVERABLE_LOSSES,
        QueryIntent.FACTORY_BREAKDOWN,
        QueryIntent.STATS,
    }


def _from_networkx(
    nx_graph: Any,
    *,
    factory: str | None,
    metal: str | None,
    recoverable_only: bool,
) -> list[LossFormRecord]:
    items: list[LossFormRecord] = []

    for node_id, data in nx_graph.nodes(data=True):
        if not str(node_id).startswith("lossform_"):
            continue

        if data.get("node_type") not in (None, "LossForm"):
            continue

        if factory and data.get("factory") != factory:
            continue

        if metal and data.get("metal") != metal:
            continue

        if recoverable_only and not data.get("recoverable"):
            continue

        tonnes = float(data.get("tonnes") or 0)

        if tonnes <= 0:
            continue

        items.append(LossFormRecord.from_attrs(str(node_id), dict(data)))

    return items


def _from_neo4j(
    graph: Any,
    *,
    factory: str | None,
    metal: str | None,
    recoverable_only: bool,
) -> list[LossFormRecord]:
    from graphrag.constants import NEO4J_ENTITY_LABEL

    cypher = f"""
    MATCH (n:{NEO4J_ENTITY_LABEL})
    WHERE n.node_id STARTS WITH 'lossform_'
      AND coalesce(n.tonnes, 0) > 0
      AND ($factory IS NULL OR n.factory = $factory)
      AND ($metal IS NULL OR n.metal = $metal)
      AND ($recoverable_only = false OR coalesce(n.recoverable, false) = true)
    RETURN n {{ .* }} AS node
    ORDER BY n.tonnes DESC
    """

    with graph._session() as session:
        rows = session.run(
            cypher,
            factory=factory,
            metal=metal,
            recoverable_only=recoverable_only,
        )

        items: list[LossFormRecord] = []

        for row in rows:
            node = dict(row["node"])
            bucket_id = str(node.pop("node_id"))
            items.append(LossFormRecord.from_attrs(bucket_id, node))

        return items
