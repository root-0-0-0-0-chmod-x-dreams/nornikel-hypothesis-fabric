"""Infer budget tier from bucket value and intervention type when not provided."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from graphrag.graph.base import GraphStoreProtocol
from graphrag.ingestion.domain import is_coarse_class, is_fine_class, is_recoverable_form
from graphrag.ingestion.constraints import BUDGET_TIERS
from graphrag.loss_attribution import list_lossforms

TIER_LOW = "low"
TIER_MEDIUM = "medium"
TIER_HIGH = "high"

# Base intervention cost profile (before value scaling).
_INTERVENTION_PROFILE: dict[tuple[str, str], tuple[str, float]] = {
    ("closed_pnt_cp", "coarse"): (TIER_MEDIUM, 62.0),
    ("closed_pnt_cp", "fine"): (TIER_MEDIUM, 50.0),
    ("open_pnt_cp", "fine"): (TIER_LOW, 28.0),
    ("open_pnt_cp", "coarse"): (TIER_LOW, 35.0),
    ("millerite", "any"): (TIER_LOW, 32.0),
    ("pyrrhotite_impurity", "any"): (TIER_HIGH, 75.0),
    ("silicate_valleriite", "any"): (TIER_LOW, 5.0),
    ("pyrite", "any"): (TIER_LOW, 10.0),
}


@dataclass
class BudgetInference:
    budget_tier: str
    budget_score: float
    tonnes_at_stake: float
    value_rank: int | None
    value_total: int | None
    value_percentile: float
    tier_scores: dict[str, float]
    rationale: str
    inferred: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def infer_budget_tier(
    graph: GraphStoreProtocol,
    bucket_id: str | None,
    *,
    factory: str | None = None,
) -> BudgetInference | None:
    """Return recommended budget tier + numeric score for a LossForm bucket."""
    if not bucket_id or not graph.has_node(bucket_id):
        return _default_inference(factory=factory)

    attrs = graph.get_node_attributes(bucket_id) or {}
    factory_name = factory or attrs.get("factory")
    form_slug = str(attrs.get("mineral_form") or "")
    size_class = str(attrs.get("size_class") or "")
    metal = str(attrs.get("metal") or "")
    tonnes = float(attrs.get("tonnes") or 0)
    recoverable = bool(attrs.get("recoverable", is_recoverable_form(form_slug, metal)))

    if not recoverable:
        return BudgetInference(
            budget_tier=TIER_LOW,
            budget_score=8.0,
            tonnes_at_stake=tonnes,
            value_rank=None,
            value_total=None,
            value_percentile=0.0,
            tier_scores={TIER_LOW: 1.0, TIER_MEDIUM: 0.0, TIER_HIGH: 0.0},
            rationale=(
                "Форма потерь неизвлекаема флотацией — капзатратные интервенции не релевантны."
            ),
        )

    peers = [
        (record.bucket_id, record.tonnes)
        for record in list_lossforms(graph, factory=factory_name, recoverable_only=True)
    ]
    value_rank, value_total, value_percentile = _rank_tonnes(bucket_id, tonnes, peers)

    base_tier, base_score = _intervention_profile(form_slug, size_class)
    value_score = value_percentile * 100.0
    budget_score = round(min(100.0, 0.65 * value_score + 0.35 * base_score), 1)

    tier_scores = _tier_scores(budget_score, base_tier, value_percentile)
    budget_tier = max(tier_scores, key=tier_scores.get)  # type: ignore[arg-type]

    rationale = _build_rationale(
        tonnes=tonnes,
        metal=metal,
        form_slug=form_slug,
        size_class=size_class,
        value_rank=value_rank,
        value_total=value_total,
        value_percentile=value_percentile,
        base_tier=base_tier,
        budget_tier=budget_tier,
        budget_score=budget_score,
    )

    return BudgetInference(
        budget_tier=budget_tier,
        budget_score=budget_score,
        tonnes_at_stake=tonnes,
        value_rank=value_rank,
        value_total=value_total,
        value_percentile=round(value_percentile, 3),
        tier_scores=tier_scores,
        rationale=rationale,
    )


def resolve_budget_tier(
    graph: GraphStoreProtocol,
    bucket_id: str | None,
    *,
    factory: str | None = None,
    budget_tier: str | None = None,
) -> tuple[str | None, BudgetInference | None]:
    """Use explicit tier or infer from bucket; None tier if nothing to infer."""
    if budget_tier in BUDGET_TIERS:
        return budget_tier, None

    inference = infer_budget_tier(graph, bucket_id, factory=factory)

    if inference is None:
        return None, None

    return inference.budget_tier, inference


def _default_inference(*, factory: str | None) -> BudgetInference:
    _ = factory

    return BudgetInference(
        budget_tier=TIER_MEDIUM,
        budget_score=50.0,
        tonnes_at_stake=0.0,
        value_rank=None,
        value_total=None,
        value_percentile=0.5,
        tier_scores={TIER_LOW: 0.2, TIER_MEDIUM: 0.6, TIER_HIGH: 0.2},
        rationale="Bucket не указан — используем средний бюджет по умолчанию.",
    )


def _intervention_profile(form_slug: str, size_class: str) -> tuple[str, float]:
    size_bucket = "coarse" if is_coarse_class(size_class) else "fine" if is_fine_class(size_class) else "any"
    key = (form_slug, size_bucket)

    if key in _INTERVENTION_PROFILE:
        return _INTERVENTION_PROFILE[key]

    fallback = _INTERVENTION_PROFILE.get((form_slug, "any"))

    if fallback:
        return fallback

    return TIER_MEDIUM, 45.0


def _tier_scores(
    budget_score: float,
    base_tier: str,
    value_percentile: float,
) -> dict[str, float]:
    scores = {
        TIER_LOW: max(0.0, 1.0 - budget_score / 45.0),
        TIER_MEDIUM: max(0.0, 1.0 - abs(budget_score - 50.0) / 35.0),
        TIER_HIGH: max(0.0, (budget_score - 35.0) / 65.0),
    }

    scores[base_tier] += 0.15

    if value_percentile >= 0.85:
        scores[TIER_HIGH] += 0.25
    elif value_percentile >= 0.55:
        scores[TIER_MEDIUM] += 0.15
    else:
        scores[TIER_LOW] += 0.1

    total = sum(scores.values()) or 1.0

    return {tier: round(value / total, 3) for tier, value in scores.items()}


def _build_rationale(
    *,
    tonnes: float,
    metal: str,
    form_slug: str,
    size_class: str,
    value_rank: int | None,
    value_total: int | None,
    value_percentile: float,
    base_tier: str,
    budget_tier: str,
    budget_score: float,
) -> str:
    parts = [
        f"Резерв {tonnes:.0f} т {metal or 'металла'}",
        f"форма {form_slug}, класс {size_class}",
    ]

    if value_rank is not None and value_total:
        parts.append(f"ранг {value_rank}/{value_total} по фабрике (p={value_percentile:.0%})")

    parts.append(f"профиль интервенции ~{base_tier}")
    parts.append(f"→ budget={budget_tier}, score={budget_score:.0f}/100")

    return ". ".join(parts) + "."


def _rank_tonnes(
    bucket_id: str,
    tonnes: float,
    peers: list[tuple[str, float]],
) -> tuple[int | None, int | None, float]:
    if not peers:
        if tonnes >= 800:
            return 1, 1, 1.0

        if tonnes >= 300:
            return 1, 1, 0.65

        if tonnes >= 80:
            return 1, 1, 0.35

        return 1, 1, 0.15

    sorted_peers = sorted(peers, key=lambda item: -item[1])
    total = len(sorted_peers)
    rank = next(
        (index for index, (node_id, _) in enumerate(sorted_peers, start=1) if node_id == bucket_id),
        None,
    )

    if rank is None and tonnes > 0:
        sorted_peers.append((bucket_id, tonnes))
        sorted_peers.sort(key=lambda item: -item[1])
        total = len(sorted_peers)
        rank = next(
            index
            for index, (node_id, _) in enumerate(sorted_peers, start=1)
            if node_id == bucket_id
        )

    if rank is None:
        return None, total, 0.5

    percentile = 1.0 - (rank - 1) / max(total - 1, 1)

    return rank, total, percentile
