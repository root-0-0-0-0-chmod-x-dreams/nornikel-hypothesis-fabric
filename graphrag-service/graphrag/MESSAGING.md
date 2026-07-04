# GraphRAG ↔ RabbitMQ

Микросервис GraphRAG слушает очереди из [07_storage_internals.md](../assets/diagrams/07_storage_internals.md).

## Инфра

```bash
make infra-up          # rabbitmq + qdrant + neo4j
make bootstrap         # первичная загрузка кейса
make rmq-worker        # worker (отдельный терминал)
make rmq-query         # RPC smoke test
```

**Management UI:** http://localhost:15672 — `hypothesis` / `hypothesis2026`

## Очереди

| Очередь | Назначение | Тип сообщения |
|---------|------------|---------------|
| `chunks_text` | сырой MD → graph + Qdrant | `ingest.markdown` |
| `chunks_text` | текстовый чанк → Qdrant | `chunk.upsert` |
| `chunks_scheme` | caption схемы → Qdrant | `chunk.upsert` |
| `graph_triplets` | S-P-O → граф | `graph.triplet` |
| `graph_rag_query` | RPC retrieval (legacy alias) | `graph_rag.query` |
| `graph_rag_query` | **Unified RPC** (recommended) | `graphrag.query` |
| `nl_cypher_query` | RPC NL→Cypher | `nl_cypher.ask` |
| `chunks_text` | внешний текст → Qdrant + граф | `external.ingest` |
| `ingest_bootstrap` | полный reload кейса | `ingest.bootstrap` |

Exchange: `hypothesis.factory` (topic), routing key = имя очереди.

## Unified query (`graphrag.query`)

Один RPC для LLM Service / агентов: граф → hybrid (dense+BM25) → constraints → weighted RRF → rerank → MMR → citations + abc_evidence. Опционально NL graph analytics.

```json
{
  "type": "graphrag.query",
  "payload": {
    "question": "что делать с закрытым пентландитом +71 на КГМК?",
    "retrieval_queries": [
      "доизмельчение закрытого пентландита МШР",
      "флотация шламов пентландита",
      "реагентная активация сульфидов"
    ],
    "hypotheses": [
      {"id": "h1", "label": "доизмельчение", "retrieval_query": "доизмельчение закрытого пентландита МШР"},
      {"id": "h2", "label": "флотация", "retrieval_query": "флотация шламов пентландита"}
    ],
    "bucket_id": "lossform_кгмк_+71_closed_pnt_cp_ni",
    "factory": "КГМК",
    "budget_tier": "medium",
    "k_out": 8,
    "auto_bucket": true,
    "include_graph_analytics": false,
    "use_graph": true
  }
}
```

| Поле | Кто заполняет | Назначение |
|------|---------------|------------|
| `question` | LLM Service | Исходная цель пользователя |
| `retrieval_query` / `graph_question` | LLM Service | Одна перефраза (legacy) |
| `retrieval_queries` / `graph_questions` | LLM Service | Несколько перефраз → multi-hypothesis RRF |
| `hypotheses` | LLM Service | Структурированные гипотезы `{id, label, retrieval_query}` |
| `bucket_id`, `factory` | LLM Service или `auto_bucket` | Контекст LossForm |
| `budget_tier` | LLM Service или **auto** | Фильтр constraints; если `null` — GraphRAG infer по tonnes + тип интервенции |
| `include_graph_analytics` | LLM Service | NL→Cypher stats (Neo4j если доступен) |

Legacy `graph_rag.query` обрабатывается тем же handler (без auto_bucket по умолчанию в клиенте).

## Формат сообщения (legacy)

```json
{
  "type": "graph_rag.query",
  "payload": {
    "question": "доизмельчение закрытого пентландита МШР",
    "bucket_id": "lossform_кгмк_+71_closed_pnt_cp_ni",
    "factory": "КГМК",
    "k_out": 8
  }
}
```

RPC: клиент ставит `reply_to` + `correlation_id`; worker отвечает:

```json
{"ok": true, "payload": { "... GraphRAG result ..." }}
```

## Клиент для других микросервисов (агенты, чанкер)

```python
from graphrag.messaging import GraphRagMessagingClient
from graphrag.models import Chunk

client = GraphRagMessagingClient()

# Ingest от чанкера
client.publish_chunk(Chunk(
    chunk_id="pdf_foo_p1_0",
    text="...",
    source="book.pdf",
    chunk_type="pdf_text",
    graph_node_ids=["mech_liberation"],
))

# Unified GraphRAG от LLM Service / Agent-1
result = client.graphrag_query(
    question="что делать с закрытым пентландитом +71 на КГМК?",
    hypotheses=[
        {"id": "h1", "label": "доизмельчение", "retrieval_query": "доизмельчение закрытого пентландита МШР"},
        {"id": "h2", "label": "флотация", "retrieval_query": "флотация шламов пентландита"},
    ],
    bucket_id="lossform_кгмк_+71_closed_pnt_cp_ni",
    factory="КГМК",
    k_out=8,
)
# result["hypotheses"] — per-hypothesis supporting_chunks + probe_top_chunks
# result["retrieval_queries"] — все перефразы, result["chunks"] — fused top-k

# Legacy alias
result = client.graph_rag_query(
    "доизмельчение МШР",
    bucket_id="lossform_кгмк_+71_closed_pnt_cp_ni",
    factory="КГМК",
)

# NL graph от UI
answer = client.nl_cypher_ask("топ потерь никеля на КГМК")

# Внешний источник (почанково → граф + Qdrant)
# RMQ type: external.ingest — текст режется по абзацам (granularity: paragraph)
# Каждый chunk: external_text + graph_node_ids + EVIDENCED_BY → Source(external)

client.close()
```

## Env

```bash
export RABBITMQ_URL=amqp://hypothesis:hypothesis2026@localhost:5672/
export RABBITMQ_EXCHANGE=hypothesis.factory
export VECTOR_BACKEND=qdrant
export QDRANT_URL=http://localhost:6333
export GRAPH_BACKEND=networkx   # или neo4j для nl_cypher
```
