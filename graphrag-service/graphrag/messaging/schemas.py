"""RabbitMQ message types and (de)serialization."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from graphrag.models import Chunk, GraphRAGResult, RetrievedChunk


MSG_CHUNK_UPSERT = "chunk.upsert"
MSG_GRAPH_TRIPLET = "graph.triplet"
MSG_GRAPH_RAG_QUERY = "graph_rag.query"
MSG_UNIFIED_QUERY = "graphrag.query"
MSG_NL_CYPHER_QUERY = "nl_cypher.ask"
MSG_EXTERNAL_INGEST = "external.ingest"
MSG_INGEST_MARKDOWN = "ingest.markdown"
MSG_INGEST_BOOTSTRAP = "ingest.bootstrap"


@dataclass
class Envelope:
    type: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps({"type": self.type, "payload": self.payload}, ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str | bytes) -> Envelope:
        data = json.loads(raw)

        return cls(type=str(data["type"]), payload=dict(data.get("payload") or {}))


def chunk_from_payload(payload: dict[str, Any]) -> Chunk:
    return Chunk(
        chunk_id=str(payload["chunk_id"]),
        text=str(payload.get("text", "")),
        summary=str(payload.get("summary", "")),
        questions=list(payload.get("questions") or []),
        source=str(payload.get("source", "")),
        factory=payload.get("factory"),
        section=str(payload.get("section", "")),
        chunk_type=str(payload.get("chunk_type", "pdf_text")),
        graph_node_ids=list(payload.get("graph_node_ids") or []),
        external=bool(payload.get("external", False)),
        source_url=payload.get("source_url"),
        metadata=dict(payload.get("metadata") or {}),
    )


def chunk_to_payload(chunk: Chunk) -> dict[str, Any]:
    return {
        "chunk_id": chunk.chunk_id,
        "text": chunk.text,
        "summary": chunk.summary,
        "questions": chunk.questions,
        "source": chunk.source,
        "factory": chunk.factory,
        "section": chunk.section,
        "chunk_type": chunk.chunk_type,
        "graph_node_ids": chunk.graph_node_ids,
        "external": chunk.external,
        "source_url": chunk.source_url,
        "metadata": chunk.metadata,
    }


def graph_rag_result_to_dict(result: GraphRAGResult) -> dict[str, Any]:
    return {
        "question": result.question,
        "bucket_id": result.bucket_id,
        "expanded_query": result.expanded_query,
        "node_ids": result.node_ids,
        "channel_hits": result.channel_hits,
        "chunks": [
            {
                "chunk_id": chunk.chunk_id,
                "text": chunk.text,
                "score": chunk.score,
                "source": chunk.source,
                "graph_node_ids": chunk.graph_node_ids,
                "retrieval_channel": chunk.retrieval_channel,
                "citation": chunk.citation,
            }
            for chunk in result.chunks
        ],
        "abc_evidence": result.abc_evidence,
        "graph_paths": [
            {
                "nodes": path.nodes,
                "edges": [
                    {"source": source, "relation": relation, "target": target}
                    for source, relation, target in path.edges
                ],
                "score": path.score,
            }
            for path in result.graph_paths
        ],
    }


def ok_response(payload: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "payload": payload}


def err_response(message: str, *, detail: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"ok": False, "error": message}

    if detail:
        body["detail"] = detail

    return body
