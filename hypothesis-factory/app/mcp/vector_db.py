import json
import logging
import time
import uuid
from typing import Any

import pika

from app.config import get_config

logger = logging.getLogger("hypothesis_factory")
config = get_config()


def _rpc_call(envelope: dict[str, Any], *, timeout: float = 60) -> dict[str, Any]:
    request_id = str(uuid.uuid4())
    connection = None
    channel = None
    callback_result: dict[str, Any] | None = None

    try:
        credentials = pika.PlainCredentials(config.rabbitmq_user, config.rabbitmq_pass)
        parameters = pika.ConnectionParameters(
            host=config.rabbitmq_host,
            port=config.rabbitmq_port,
            credentials=credentials,
            connection_attempts=2,
            retry_delay=2,
        )
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        result_queue = channel.queue_declare(queue="", exclusive=True)
        callback_queue = result_queue.method.queue

        def on_response(_ch, _method, _props, body):
            nonlocal callback_result
            try:
                callback_result = json.loads(body.decode())
            except json.JSONDecodeError:
                callback_result = {"ok": False, "error": "invalid_response", "raw": body.decode()[:500]}

        channel.basic_consume(
            queue=callback_queue,
            on_message_callback=on_response,
            auto_ack=True,
        )

        channel.basic_publish(
            exchange="",
            routing_key="graph_rag_query",
            properties=pika.BasicProperties(
                reply_to=callback_queue,
                correlation_id=request_id,
                content_type="application/json",
            ),
            body=json.dumps(envelope, ensure_ascii=False),
        )

        deadline = time.time() + timeout
        while callback_result is None and time.time() < deadline:
            connection.process_data_events(time_limit=1)

        if callback_result is None:
            return {"ok": False, "error": "timeout"}

        return callback_result
    except Exception as e:
        logger.warning("graphrag_rpc_failed", extra={"error": str(e)[:200]})
        return {"ok": False, "error": str(e)[:200]}
    finally:
        try:
            if channel and channel.is_open:
                channel.close()
            if connection and connection.is_open:
                connection.close()
        except Exception:
            pass


def _chunks_from_response(response: dict[str, Any]) -> list[dict]:
    if not response.get("ok"):
        error = response.get("error", "GraphRAG RPC failed")
        return [{"status": "error", "message": error}]

    payload = response.get("payload") or {}
    chunks = payload.get("chunks") or []

    if not chunks:
        return [{"status": "empty", "message": "No chunks returned"}]

    return [
        {
            "chunk_id": chunk.get("chunk_id"),
            "text": chunk.get("text", ""),
            "content": chunk.get("text", ""),
            "source": chunk.get("source", ""),
            "score": chunk.get("score"),
            "citation": chunk.get("citation"),
        }
        for chunk in chunks
    ]


def query_vector_db(query_text: str, top_k: int = 10) -> list[dict]:
    """Query GraphRAG unified RPC (graph_rag_query queue)."""
    envelope = {
        "type": "graphrag.query",
        "payload": {
            "question": query_text,
            "retrieval_query": query_text,
            "k_out": top_k,
            "auto_bucket": True,
        },
    }
    response = _rpc_call(envelope)
    if not response.get("ok") and response.get("error") == "timeout":
        logger.warning("rabbitmq_timeout")
        return [{"status": "no_response", "message": "GraphRAG query timed out"}]
    return _chunks_from_response(response)


def get_chunk_by_id(chunk_id: str) -> dict[str, Any] | None:
    """Fetch a single chunk with citation by ID."""
    envelope = {
        "type": "chunk.get",
        "payload": {"chunk_id": chunk_id},
    }
    response = _rpc_call(envelope, timeout=30)
    if not response.get("ok"):
        return None
    return response.get("payload")
