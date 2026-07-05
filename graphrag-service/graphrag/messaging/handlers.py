"""Handle RabbitMQ messages for GraphRAG microservice."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from graphrag.graph.base import GraphStoreProtocol
from graphrag.ingestion.external_source import apply_external_ingest, ingest_external_source
from graphrag.ingestion.md_ingest import apply_md_ingest, ingest_markdown_document
from graphrag.ingestion.graph_cache import invalidate_graph_cache
from graphrag.ingestion.pipeline import load_knowledge_base
from graphrag.messaging.schemas import (
    MSG_CHUNK_UPSERT,
    MSG_EXTERNAL_INGEST,
    MSG_GRAPH_RAG_QUERY,
    MSG_GRAPH_TRIPLET,
    MSG_INGEST_BOOTSTRAP,
    MSG_INGEST_MARKDOWN,
    MSG_NL_CYPHER_QUERY,
    MSG_UNIFIED_QUERY,
    Envelope,
    chunk_from_payload,
    err_response,
    ok_response,
)
from graphrag.models import GraphEdge, GraphNode
from graphrag.nl_cypher import NLGraphQueryService
from graphrag.service import GraphRAGQueryService
from graphrag.unified_query import (
    UnifiedGraphRAGService,
    unified_request_from_payload,
    unified_result_to_dict,
)
from graphrag.vector_protocol import VectorStoreProtocol

logger = logging.getLogger(__name__)


@dataclass
class MessageHandlerContext:
    graph: GraphStoreProtocol
    vectors: VectorStoreProtocol
    graph_rag: GraphRAGQueryService
    nl_cypher: NLGraphQueryService | None = None

    @classmethod
    def create(cls) -> MessageHandlerContext:
        loaded = load_knowledge_base()
        graph_rag = GraphRAGQueryService(loaded.graph, loaded.vectors)

        return cls(
            graph=loaded.graph,
            vectors=loaded.vectors,
            graph_rag=graph_rag,
            nl_cypher=None,
        )

    def reload(self) -> dict[str, int]:
        invalidate_graph_cache()
        loaded = load_knowledge_base(
            graph=self.graph,
            use_graph_cache=False,
        )
        self.vectors = loaded.vectors
        self.graph_rag = GraphRAGQueryService(loaded.graph, loaded.vectors)
        self.nl_cypher = None

        return loaded.stats

    def nl_cypher_service(self) -> NLGraphQueryService:
        if self.nl_cypher is None:
            self.nl_cypher = NLGraphQueryService()

        return self.nl_cypher


class MessageHandler:
    def __init__(self, ctx: MessageHandlerContext) -> None:
        self._ctx = ctx

    def handle(self, envelope: Envelope) -> dict:
        handlers = {
            MSG_CHUNK_UPSERT: self._handle_chunk_upsert,
            MSG_GRAPH_TRIPLET: self._handle_graph_triplet,
            MSG_GRAPH_RAG_QUERY: self._handle_unified_query,
            MSG_UNIFIED_QUERY: self._handle_unified_query,
            MSG_NL_CYPHER_QUERY: self._handle_nl_cypher_query,
            MSG_EXTERNAL_INGEST: self._handle_external_ingest,
            MSG_INGEST_MARKDOWN: self._handle_ingest_markdown,
            MSG_INGEST_BOOTSTRAP: self._handle_bootstrap,
        }
        handler = handlers.get(envelope.type)

        if handler is None:
            return err_response(f"unknown message type: {envelope.type}")

        try:
            return handler(envelope.payload)
        except Exception as exc:  # noqa: BLE001 — surface to RPC caller
            logger.exception("handler failed for %s", envelope.type)

            return err_response(str(exc))

    def _handle_chunk_upsert(self, payload: dict) -> dict:
        chunk = chunk_from_payload(payload)

        if hasattr(self._ctx.vectors, "upsert_many"):
            self._ctx.vectors.upsert_many([chunk])
        else:
            self._ctx.vectors.add_many([chunk])

        return ok_response({"chunk_id": chunk.chunk_id, "indexed": True})

    def _handle_graph_triplet(self, payload: dict) -> dict:
        subject = payload.get("subject") or {}
        object_node = payload.get("object") or {}
        relation = str(payload.get("predicate") or payload.get("relation", "RELATED_TO"))

        for node_payload in (subject, object_node):
            node = GraphNode(
                node_id=str(node_payload["node_id"]),
                node_type=str(node_payload.get("node_type", "Entity")),
                label=str(node_payload.get("label", node_payload["node_id"])),
                attributes=dict(node_payload.get("attributes") or {}),
            )
            self._ctx.graph.add_node(node)

        edge = GraphEdge(
            source=str(subject["node_id"]),
            target=str(object_node["node_id"]),
            relation=relation,
            attributes=dict(payload.get("attributes") or {}),
        )
        self._ctx.graph.add_edge(edge)

        return ok_response(
            {
                "source": edge.source,
                "relation": edge.relation,
                "target": edge.target,
            }
        )

    def _handle_unified_query(self, payload: dict) -> dict:
        unified = UnifiedGraphRAGService(
            self._ctx.graph,
            self._ctx.vectors,
            nl_cypher=self._ctx.nl_cypher,
        )
        request = unified_request_from_payload(payload)
        result = unified.query(request)

        return ok_response(unified_result_to_dict(result))

    def _handle_nl_cypher_query(self, payload: dict) -> dict:
        answer = self._ctx.nl_cypher_service().ask(str(payload["question"]))

        return ok_response(
            {
                "answer": answer.answer,
                "cypher": answer.cypher,
                "intent": answer.intent,
                "rows": answer.rows,
            }
        )

    def _handle_ingest_markdown(self, payload: dict) -> dict:
        markdown = str(payload.get("markdown") or payload.get("content") or "").strip()

        if not markdown:
            return err_response("markdown is required")

        result = ingest_markdown_document(
            markdown,
            source_path=payload.get("source_path") or payload.get("filename"),
            source_url=payload.get("source_url"),
            auto_link=bool(payload.get("auto_link", True)),
            factory=payload.get("factory"),
        )
        apply_md_ingest(self._ctx.graph, self._ctx.vectors, result)
        invalidate_graph_cache()
        self._ctx.graph_rag = GraphRAGQueryService(self._ctx.graph, self._ctx.vectors)

        chunk_types = sorted({chunk.chunk_type for chunk in result.chunks})

        return ok_response(
            {
                "chunk_ids": result.chunk_ids,
                "chunk_count": len(result.chunks),
                "nodes_added": len(result.nodes),
                "edges_added": len(result.edges),
                "chunk_types": chunk_types,
                "source_path": result.source_path,
            }
        )

    def _handle_external_ingest(self, payload: dict) -> dict:
        result = ingest_external_source(
            text=str(payload.get("text", "")),
            title=str(payload.get("title", "External source")),
            source_url=payload.get("source_url"),
            summary=str(payload.get("summary", "")),
            explicit_node_ids=list(payload.get("graph_node_ids") or []),
            auto_link=bool(payload.get("auto_link", True)),
            granularity=str(payload.get("granularity", "paragraph")),
        )
        apply_external_ingest(self._ctx.graph, self._ctx.vectors, result)
        invalidate_graph_cache()
        self._ctx.graph_rag = GraphRAGQueryService(self._ctx.graph, self._ctx.vectors)

        return ok_response(
            {
                "chunk_ids": [chunk.chunk_id for chunk in result.chunks],
                "chunk_id": result.chunks[0].chunk_id if result.chunks else None,
                "chunk_count": len(result.chunks),
                "source_id": result.source_id,
                "matched_entities": result.matched_entities,
                "edges": len(result.edges),
            }
        )

    def _handle_bootstrap(self, payload: dict) -> dict:
        _ = payload
        stats = self._ctx.reload()

        return ok_response({"stats": stats})
