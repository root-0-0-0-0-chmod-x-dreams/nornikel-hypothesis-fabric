"""RabbitMQ worker entrypoint for GraphRAG microservice."""

from __future__ import annotations

import json
import logging
from typing import Any

import pika
from pika.adapters.blocking_connection import BlockingChannel

from graphrag.config import RabbitmqConfig
from graphrag.constants import (
    QUEUE_CHUNKS_SCHEME,
    QUEUE_CHUNKS_TEXT,
    QUEUE_GRAPH_RAG_QUERY,
    QUEUE_GRAPH_TRIPLETS,
    QUEUE_INGEST_BOOTSTRAP,
    QUEUE_NL_CYPHER_QUERY,
)
from graphrag.messaging.broker import connect, declare_topology
from graphrag.messaging.handlers import MessageHandler, MessageHandlerContext
from graphrag.messaging.schemas import Envelope

logger = logging.getLogger(__name__)

_RPC_QUEUES = {QUEUE_GRAPH_RAG_QUERY, QUEUE_NL_CYPHER_QUERY}
_INGEST_QUEUES = {
    QUEUE_CHUNKS_TEXT,
    QUEUE_CHUNKS_SCHEME,
    QUEUE_GRAPH_TRIPLETS,
    QUEUE_INGEST_BOOTSTRAP,
}


class GraphRagWorker:
    def __init__(self, handler: MessageHandler | None = None) -> None:
        self._config = RabbitmqConfig.from_env()
        self._handler = handler or MessageHandler(MessageHandlerContext.create())
        self._connection = connect(self._config)
        self._channel = self._connection.channel()
        declare_topology(self._channel, exchange=self._config.exchange)
        self._channel.basic_qos(prefetch_count=1)

    def run(self) -> None:
        for queue_name in sorted(_RPC_QUEUES | _INGEST_QUEUES):
            self._channel.basic_consume(
                queue=queue_name,
                on_message_callback=self._on_message,
            )
            logger.info("listening on %s", queue_name)

        logger.info("GraphRAG worker ready (exchange=%s)", self._config.exchange)
        self._channel.start_consuming()

    def stop(self) -> None:
        if self._channel.is_open:
            self._channel.stop_consuming()

        if self._connection.is_open:
            self._connection.close()

    def _on_message(
        self,
        channel: BlockingChannel,
        method: pika.spec.Basic.Deliver,
        properties: pika.BasicProperties,
        body: bytes,
    ) -> None:
        envelope = Envelope.from_json(body)
        response = self._handler.handle(envelope)
        self._maybe_reply(channel, properties, response)
        channel.basic_ack(delivery_tag=method.delivery_tag)

    @staticmethod
    def _maybe_reply(
        channel: BlockingChannel,
        properties: pika.BasicProperties,
        response: dict[str, Any],
    ) -> None:
        if not properties.reply_to:
            return

        channel.basic_publish(
            exchange="",
            routing_key=properties.reply_to,
            properties=pika.BasicProperties(
                correlation_id=properties.correlation_id,
                content_type="application/json",
            ),
            body=json.dumps(response, ensure_ascii=False).encode("utf-8"),
        )


def run_worker() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    worker = GraphRagWorker()

    try:
        worker.run()
    except KeyboardInterrupt:
        logger.info("shutting down")
        worker.stop()
