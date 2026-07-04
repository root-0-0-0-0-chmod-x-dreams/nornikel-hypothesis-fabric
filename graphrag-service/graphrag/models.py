"""Data models for GraphRAG pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Chunk:
    """Text chunk stored in vector index."""

    chunk_id: str
    text: str
    summary: str = ""
    questions: list[str] = field(default_factory=list)
    source: str = ""
    factory: str | None = None
    section: str = ""
    chunk_type: str = "pdf_text"
    graph_node_ids: list[str] = field(default_factory=list)
    external: bool = False
    source_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def full_text_for_embed(self) -> str:
        parts = [self.text]
        if self.summary:
            parts.append(self.summary)
        if self.questions:
            parts.append(" ".join(self.questions))
        return "\n".join(parts)


@dataclass
class GraphNode:
    node_id: str
    node_type: str
    label: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    source: str
    target: str
    relation: str
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphPath:
    nodes: list[str]
    edges: list[tuple[str, str, str]]  # (source, relation, target)
    score: float = 1.0


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    score: float
    source: str = ""
    graph_node_ids: list[str] = field(default_factory=list)
    retrieval_channel: str = ""  # graph | dense | bm25 | fused
    citation: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphRAGResult:
    question: str
    bucket_id: str | None
    graph_paths: list[GraphPath]
    node_ids: list[str]
    chunks: list[RetrievedChunk]
    channel_hits: dict[str, int] = field(default_factory=dict)
    expanded_query: str | None = None
    abc_evidence: dict[str, Any] | None = None
    hypothesis_probe: list[dict[str, Any]] = field(default_factory=list)
