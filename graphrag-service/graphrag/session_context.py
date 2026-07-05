"""Auto-resolve bucket, budget, constraints and agent role inside GraphRAG."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from graphrag.budget_inference import resolve_budget_tier
from graphrag.graph.base import GraphStoreProtocol
from graphrag.ingestion.constraints import BUDGET_TIERS, FACTORY_EQUIPMENT, REGULATION_CHUNKS
from graphrag.ingestion.domain import is_coarse_class, is_fine_class
from graphrag.loss_attribution import (
    is_loss_attribution_intent,
    resolve_bucket_id,
    top_lossforms,
)
from graphrag.nl_cypher.models import ParsedQuery
from graphrag.nl_cypher.parser import parse_question

AGENT_COMMINUTION = "Comminution"
AGENT_FLOTATION = "Flotation"
AGENT_REAGENT = "Reagent"
AGENT_LOSS_ATTRIBUTION = "LossAttribution"
AGENT_GENERAL = "General"


@dataclass
class SessionContext:
    bucket_id: str | None
    factory: str | None
    budget_tier: str | None
    agent_role: str
    constraints: dict[str, Any] = field(default_factory=dict)
    bucket_resolution: dict[str, Any] = field(default_factory=dict)
    budget_inference: dict[str, Any] | None = None
    top_buckets: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def resolve_session_context(
    graph: GraphStoreProtocol,
    question: str,
    *,
    bucket_id: str | None = None,
    factory: str | None = None,
    budget_tier: str | None = None,
    user_constraints: list[str] | None = None,
    auto_bucket: bool = True,
) -> SessionContext:
    parsed = parse_question(question)
    resolved_bucket, bucket_resolution = resolve_bucket_id(
        graph,
        parsed,
        bucket_id=bucket_id,
        auto_bucket=auto_bucket,
    )
    resolved_factory = factory or parsed.factory

    if resolved_factory is None and resolved_bucket and graph.has_node(resolved_bucket):
        attrs = graph.get_node_attributes(resolved_bucket) or {}
        resolved_factory = attrs.get("factory")

    bucket_attrs = graph.get_node_attributes(resolved_bucket) if resolved_bucket else None

    resolved_budget, budget_inference_obj = resolve_budget_tier(
        graph,
        resolved_bucket,
        factory=resolved_factory,
        budget_tier=budget_tier,
    )

    agent_role = route_agent_role(parsed, bucket_attrs)
    constraints = build_constraints_context(
        factory=resolved_factory,
        budget_tier=resolved_budget,
        user_constraints=user_constraints,
    )
    top_buckets = [
        record.to_dict()
        for record in top_lossforms(
            graph,
            factory=resolved_factory,
            metal=parsed.metal,
            limit=5,
        )
    ]

    return SessionContext(
        bucket_id=resolved_bucket,
        factory=resolved_factory,
        budget_tier=resolved_budget,
        agent_role=agent_role,
        constraints=constraints,
        bucket_resolution=bucket_resolution,
        budget_inference=budget_inference_obj.to_dict() if budget_inference_obj else None,
        top_buckets=top_buckets,
    )


def route_agent_role(
    parsed: ParsedQuery,
    bucket_attrs: dict[str, Any] | None,
) -> str:
    if is_loss_attribution_intent(parsed.intent):
        return AGENT_LOSS_ATTRIBUTION

    if not bucket_attrs:
        return AGENT_GENERAL

    form_slug = str(bucket_attrs.get("mineral_form") or "")
    size_class = str(bucket_attrs.get("size_class") or "")

    if form_slug == "closed_pnt_cp" and is_coarse_class(size_class):
        return AGENT_COMMINUTION

    if form_slug == "open_pnt_cp" and is_fine_class(size_class):
        return AGENT_FLOTATION

    if form_slug == "millerite":
        return AGENT_REAGENT

    if form_slug in {"pyrrhotite_impurity", "pyrite"}:
        return AGENT_GENERAL

    return AGENT_GENERAL


def build_constraints_context(
    *,
    factory: str | None,
    budget_tier: str | None,
    user_constraints: list[str] | None = None,
) -> dict[str, Any]:
    items: list[str] = []
    allowed_equipment = sorted(FACTORY_EQUIPMENT.get(factory or "", []))

    if budget_tier in BUDGET_TIERS:
        items.append(BUDGET_TIERS[budget_tier])

    if allowed_equipment:
        items.append(f"Доступное оборудование на {factory}: {', '.join(allowed_equipment)}")

    for regulation in REGULATION_CHUNKS:
        reg_factory = regulation.get("factory")

        if reg_factory not in (factory, None):
            continue

        items.append(regulation["text"])

    if user_constraints:
        items.extend(str(item).strip() for item in user_constraints if str(item).strip())

    return {
        "items": items,
        "allowed_equipment": allowed_equipment,
        "budget_tier": budget_tier,
        "factory": factory,
    }
