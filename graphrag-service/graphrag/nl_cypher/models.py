"""Models for NL graph queries."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class QueryIntent(StrEnum):
    STATS = "stats"
    FACTORY_BREAKDOWN = "factory_breakdown"
    TOP_LOSSES = "top_losses"
    BUCKET_LOOKUP = "bucket_lookup"
    INTERVENTION_PATH = "intervention_path"
    SEARCH_NODES = "search_nodes"
    LIST_BY_TYPE = "list_by_type"
    RECOVERABLE_LOSSES = "recoverable_losses"
    LITERATURE_EVIDENCE = "literature_evidence"
    NEIGHBORS = "neighbors"
    EDGE_STATS = "edge_stats"
    PROCESS_EQUIPMENT = "process_equipment"


@dataclass
class ParsedQuery:
    intent: QueryIntent
    question: str
    factory: str | None = None
    metal: str | None = None
    form_slug: str | None = None
    size_class: str | None = None
    node_type: str | None = None
    search_text: str | None = None
    entity_id: str | None = None
    limit: int = 10


@dataclass
class NLQueryResult:
    question: str
    intent: str
    cypher: str
    params: dict[str, Any]
    rows: list[dict[str, Any]]
    answer: str
    bucket_id: str | None = None
    hints: list[str] = field(default_factory=list)
