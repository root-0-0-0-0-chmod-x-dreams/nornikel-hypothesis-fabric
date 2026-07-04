"""RabbitMQ connection and topology."""

from __future__ import annotations

from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from pika.adapters.blocking_connection import BlockingConnection

ALL_QUEUES = (
    QUEUE_CHUNKS_TEXT,
    QUEUE_CHUNKS_SCHEME,
    QUEUE_GRAPH_TRIPLETS,
    QUEUE_GRAPH_RAG_QUERY,
    QUEUE_NL_CYPHER_QUERY,
    QUEUE_INGEST_BOOTSTRAP,
)


def connect(config: RabbitmqConfig | None = None) -> BlockingConnection:
    cfg = config or RabbitmqConfig.from_env()
    params = pika.URLParameters(cfg.url)
    params.heartbeat = 600
    params.blocked_connection_timeout = 300

    return pika.BlockingConnection(params)


def declare_topology(
    channel: BlockingChannel,
    *,
    exchange: str | None = None,
) -> None:
    exchange_name = exchange or RabbitmqConfig.from_env().exchange
    channel.exchange_declare(
        exchange=exchange_name,
        exchange_type="topic",
        durable=True,
    )

    for queue_name in ALL_QUEUES:
        channel.queue_declare(queue=queue_name, durable=True)
        channel.queue_bind(
            exchange=exchange_name,
            queue=queue_name,
            routing_key=queue_name,
        )
