"""Shared state for Gradio studio."""

from __future__ import annotations

from dataclasses import dataclass, field

from graphrag.ingestion.pipeline import LoadedKnowledgeBase, load_knowledge_base
from graphrag.nl_cypher.service import NLGraphQueryService
from graphrag.service import GraphRAGQueryService


@dataclass
class StudioState:
    loaded: LoadedKnowledgeBase | None = None
    graph_rag: GraphRAGQueryService | None = None
    nl_cypher: NLGraphQueryService | None = None
    last_error: str | None = None
    stats: dict[str, int] = field(default_factory=dict)

    def reload(self) -> str:
        try:
            if self.nl_cypher is not None:
                self.nl_cypher.close()
        except Exception:  # noqa: BLE001
            pass

        self.loaded = load_knowledge_base()
        self.graph_rag = GraphRAGQueryService(self.loaded.graph, self.loaded.vectors)
        self.last_error = None

        try:
            self.nl_cypher = NLGraphQueryService()
            neo4j_status = "ok"
        except Exception as exc:  # noqa: BLE001
            self.nl_cypher = None
            neo4j_status = f"unavailable ({exc})"

        self.stats = dict(self.loaded.stats)
        vectors = self.loaded.vectors

        return (
            f"Reloaded: {self.stats.get('nodes', 0)} nodes, "
            f"{self.stats.get('edges', 0)} edges, "
            f"{vectors.size} indexed chunks. Neo4j NL: {neo4j_status}."
        )


STATE = StudioState()
