"""RabbitMQ RPC client for other microservices."""

from __future__ import annotations

import json
import uuid
from typing import Any

import pika

from graphrag.config import RabbitmqConfig
from graphrag.constants import (
    QUEUE_CHUNKS_TEXT,
    QUEUE_GRAPH_RAG_QUERY,
    QUEUE_INGEST_BOOTSTRAP,
    QUEUE_NL_CYPHER_QUERY,
)
from graphrag.messaging.broker import connect, declare_topology
from graphrag.messaging.schemas import (
    Envelope,
    MSG_CHUNK_UPSERT,
    MSG_GRAPH_RAG_QUERY,
    MSG_INGEST_BOOTSTRAP,
    MSG_INGEST_MARKDOWN,
    MSG_NL_CYPHER_QUERY,
    MSG_UNIFIED_QUERY,
    chunk_to_payload,
)
from graphrag.models import Chunk


class GraphRagMessagingClient:
    """Publish RPC requests to GraphRAG worker queues."""

    def __init__(self, config: RabbitmqConfig | None = None) -> None:
        self._config = config or RabbitmqConfig.from_env()
        self._connection = connect(self._config)
        self._channel = self._connection.channel()
        declare_topology(self._channel, exchange=self._config.exchange)

    def close(self) -> None:
        if self._connection.is_open:
            self._connection.close()

    def publish_chunk(self, chunk: Chunk, *, queue: str = QUEUE_CHUNKS_TEXT) -> None:
        self.publish(
            queue,
            Envelope(type=MSG_CHUNK_UPSERT, payload=chunk_to_payload(chunk)),
        )

    def request_bootstrap(self) -> None:
        self.publish(
            QUEUE_INGEST_BOOTSTRAP,
            Envelope(type=MSG_INGEST_BOOTSTRAP, payload={}),
        )

    def publish(self, queue: str, envelope: Envelope) -> None:
        self._channel.basic_publish(
            exchange="",
            routing_key=queue,
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
            ),
            body=envelope.to_json().encode("utf-8"),
        )

    def graphrag_query(
        self,
        question: str,
        *,
        retrieval_query: str | None = None,
        retrieval_queries: list[str] | None = None,
        hypotheses: list[dict[str, Any]] | None = None,
        graph_question: str | None = None,
        bucket_id: str | None = None,
        factory: str | None = None,
        budget_tier: str | None = None,
        constraints: list[str] | None = None,
        k_out: int = 8,
        include_external: bool = False,
        auto_bucket: bool = True,
        include_graph_analytics: bool = False,
        include_hypothesis_support: bool = True,
        use_graph: bool = True,
        max_hops: int | None = None,
        timeout: float = 60.0,
    ) -> dict[str, Any]:
        """Unified GraphRAG RPC: hybrid search + graph traverse + rerank (+ optional NL graph stats)."""
        payload: dict[str, Any] = {
            "question": question,
            "bucket_id": bucket_id,
            "factory": factory,
            "budget_tier": budget_tier,
            "k_out": k_out,
            "include_external": include_external,
            "auto_bucket": auto_bucket,
            "include_graph_analytics": include_graph_analytics,
            "include_hypothesis_support": include_hypothesis_support,
            "use_graph": use_graph,
        }

        if hypotheses:
            payload["hypotheses"] = hypotheses
        elif retrieval_queries:
            payload["retrieval_queries"] = retrieval_queries
        elif retrieval_query:
            payload["retrieval_query"] = retrieval_query
        elif graph_question:
            payload["graph_question"] = graph_question

        if max_hops is not None:
            payload["max_hops"] = max_hops

        if constraints:
            payload["constraints"] = constraints

        return self._rpc(
            queue=QUEUE_GRAPH_RAG_QUERY,
            message_type=MSG_UNIFIED_QUERY,
            payload=payload,
            timeout=timeout,
        )

    def ingest_markdown(
        self,
        markdown: str,
        *,
        source_path: str | None = None,
        source_url: str | None = None,
        factory: str | None = None,
        auto_link: bool = True,
        timeout: float = 120.0,
    ) -> dict[str, Any]:
        """Ingest raw MD (YAML frontmatter + body) into graph + Qdrant."""
        payload: dict[str, Any] = {
            "markdown": markdown,
            "auto_link": auto_link,
        }

        if source_path:
            payload["source_path"] = source_path

        if source_url:
            payload["source_url"] = source_url

        if factory:
            payload["factory"] = factory

        return self._rpc(
            queue=QUEUE_CHUNKS_TEXT,
            message_type=MSG_INGEST_MARKDOWN,
            payload=payload,
            timeout=timeout,
        )

    def graph_rag_query(
        self,
        question: str,
        *,
        bucket_id: str | None = None,
        factory: str | None = None,
        k_out: int = 8,
        timeout: float = 60.0,
    ) -> dict[str, Any]:
        return self.graphrag_query(
            question,
            bucket_id=bucket_id,
            factory=factory,
            k_out=k_out,
            auto_bucket=False,
            timeout=timeout,
        )

    def nl_cypher_ask(self, question: str, *, timeout: float = 60.0) -> dict[str, Any]:
        return self._rpc(
            queue=QUEUE_NL_CYPHER_QUERY,
            message_type=MSG_NL_CYPHER_QUERY,
            payload={"question": question},
            timeout=timeout,
        )

    def _rpc(
        self,
        *,
        queue: str,
        message_type: str,
        payload: dict[str, Any],
        timeout: float,
    ) -> dict[str, Any]:
        correlation_id = str(uuid.uuid4())
        reply_queue = self._channel.queue_declare(queue="", exclusive=True).method.queue
        envelope = Envelope(type=message_type, payload=payload)

        self._channel.basic_publish(
            exchange="",
            routing_key=queue,
            properties=pika.BasicProperties(
                reply_to=reply_queue,
                correlation_id=correlation_id,
                content_type="application/json",
            ),
            body=envelope.to_json().encode("utf-8"),
        )

        response: dict[str, Any] | None = None

        for method, props, body in self._channel.consume(
            reply_queue,
            inactivity_timeout=timeout,
        ):
            if method is None:
                break

            if props.correlation_id == correlation_id:
                response = json.loads(body.decode("utf-8"))
                self._channel.basic_ack(method.delivery_tag)
                break

            self._channel.basic_ack(method.delivery_tag)

        self._channel.cancel()

        if response is None:
            raise TimeoutError(f"RPC timeout on queue {queue} after {timeout}s")

        if not response.get("ok"):
            raise RuntimeError(response.get("error", "RPC failed"))

        return dict(response.get("payload") or {})
