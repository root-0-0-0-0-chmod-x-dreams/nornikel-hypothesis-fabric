import json, uuid, time, logging
from typing import Optional

import pika

from app.config import get_config

logger = logging.getLogger("hypothesis_factory")
config = get_config()


def query_vector_db(query_text: str, top_k: int = 10) -> list[dict]:
    """Query the vector database via RabbitMQ RPC (graph_rag_query queue)."""
    request_id = str(uuid.uuid4())
    connection = None
    channel = None
    callback_result = None

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

        def on_response(ch, method, props, body):
            nonlocal callback_result
            try:
                callback_result = json.loads(body.decode())
            except json.JSONDecodeError:
                callback_result = {"error": "invalid_response", "raw": body.decode()[:500]}

        channel.basic_consume(
            queue=callback_queue,
            on_message_callback=on_response,
            auto_ack=True,
        )

        payload = {
            "request_id": request_id,
            "query": query_text,
            "top_k": top_k,
        }

        channel.basic_publish(
            exchange="",
            routing_key="graph_rag_query",
            properties=pika.BasicProperties(
                reply_to=callback_queue,
                correlation_id=request_id,
            ),
            body=json.dumps(payload, ensure_ascii=False),
        )

        deadline = time.time() + 15
        while callback_result is None and time.time() < deadline:
            connection.process_data_events(time_limit=1)

        if callback_result is None:
            logger.warning("rabbitmq_timeout", extra={"request_id": request_id})
            return [{"status": "no_response", "message": "Vector DB query timed out"}]

        if "error" in callback_result:
            logger.warning("rabbitmq_error", extra={"error": callback_result.get("error")})
            return [{"status": "error", "message": callback_result.get("error", "Unknown")}]

        return callback_result if isinstance(callback_result, list) else [callback_result]

    except Exception as e:
        logger.warning("rabbitmq_unavailable", extra={"error": str(e)[:200]})
        return [{"status": "unavailable", "message": f"Vector DB not reachable: {str(e)[:200]}"}]
    finally:
        try:
            if channel and channel.is_open:
                channel.close()
            if connection and connection.is_open:
                connection.close()
        except Exception:
            pass
