# Статус реализации (актуально на код в `graphrag/`)

Сверка архитектурных документов с тем, что **уже работает** в репозитории.

## Сводка

| Компонент | Статус | Где в коде |
|-----------|--------|------------|
| Парсер Excel → LossForm | ✅ | `ingestion/excel_parser.py` |
| PDF → текстовые чанки | ✅ | `ingestion/pdf_parser.py` |
| PNG → caption-чанки | ✅ | `ingestion/schemes.py` |
| Каталог Equipment/Process/Mechanism | ✅ | `ingestion/catalog.py`, `domain.py` |
| Онтология (Factory, Size, Mineral, Metal, Source) | ✅ | `ingestion/ontology_wiring.py` |
| Граф networkx | ✅ | `graph/networkx_store.py` |
| Граф Neo4j + Docker | ✅ | `graph/neo4j_store.py`, `docker-compose.yml` |
| VectorStore (memory fallback) | ✅ | `vector_store.py` |
| **Qdrant** dense + BM25 sparse | ✅ | `qdrant_store.py` + `sparse_embeddings.py`, `docker-compose` |
| RRF fusion + overlap rerank | ✅ | `fusion.py` |
| **Query expansion** (domain synonyms) | ✅ | `query_expansion.py` |
| **Bucket context enrichment** | ✅ | `retrieval_context.py` |
| **Qdrant hybrid** (dense+BM25 server RRF) | ✅ | `qdrant_store.hybrid_search` |
| **Weighted RRF** + graph boost | ✅ | `service.py` |
| **Graph-overlap rerank** + **MMR** diversity | ✅ | `fusion.py` |
| GraphRAGQueryService | ✅ | `service.py` |
| Text-to-Cypher (русский) | ✅ | `nl_cypher/`, `scripts/ask_graph.py` |
| Neo4j smoke checks | ✅ | `scripts/check_neo4j.py` |
| Qdrant smoke check | ✅ | `scripts/check_qdrant.py` |
| RabbitMQ worker + RPC | ✅ | `graphrag/messaging/`, `scripts/rmq_worker.py` |
| **Unified GraphRAG RPC** (`graphrag.query`) | ✅ | `unified_query.py` — hybrid + graph + rerank для LLM Service |
| **Auto session context** | ✅ | `session_context.py` — bucket, budget, constraints, agent_role |
| **Gradio Studio** | ✅ | `scripts/gradio_studio.py` — `make gradio-studio` |
| **Provenance / Citation** | ✅ | `provenance/citations.py` — page, §, excel cell |
| **Swanson ABC evidence** | ✅ | `provenance/abc_evidence.py` → `GraphRAGResult.abc_evidence` |
| **Factory constraints** | ✅ | `ingestion/constraints.py` — budget, HAS_EQUIPMENT |
| **External sources ingest** | ✅ | `ingestion/external_source.py`, RMQ `external.ingest` |
| **MD books (OpenDataLoader)** | ✅ | `pdf_extractors.py`, `book_chunking.py`, `make pdf-to-md` |
| **MD bucket input** | ✅ | `ingestion/md_parser.py`, `make excel-to-md` |
| ColQwen / late interaction PNG | ⏳ | VLM at query time (12 схем) |
| MCP tool wrapper | ⏳ | `GraphRAGQueryService` готов, обёртка — нет |
| Multi-agent / Dual Judge | ⏳ | в `какатон.md`, не в коде |
| Expert Studio UI | ⏳ | — |
| Web / novelty retrieval | ⏳ | — |
| VLM triplets из PDF | ⏳ | PDF только в векторку |

## Цифры после `make bootstrap` (книги: paragraph + GraphRAG)

```
nodes:              ~277
edges:              ~1550
chunks:             ~4900  (excel + ~4849 book paragraph + constraints)
book_granularity:   paragraph
book_chunks:        ~4849
pdf_linked_chunks:  ~2000+
literature_edges:   ~40
loss_forms:         214
```

Книги: OpenDataLoader → atoms → **`paragraph`** чанки (бенчмарк RAG/GraphRAG).  
GraphRAG на bucket-пути тянет литературу через graph channel (`EVIDENCED_BY`).

## GraphRAG Query — реализованный поток

Соответствует [08_graph_rag_query.md](../assets/diagrams/08_graph_rag_query.md). Детали хранения: [DATA_STORAGE.md](DATA_STORAGE.md), цитаты: [PROVENANCE.md](PROVENANCE.md).

```
graph_rag_query(question, bucket_id?, factory?, budget_tier?)
  ├─ traverse INTERVENTION_RELATIONS (ABC)
  ├─ filter equipment по Factory (constraints)
  ├─ graph / hybrid / constraint channels → weighted RRF
  ├─ rerank + MMR
  ├─ chunks[].citation (page, cell, excerpt)
  └─ abc_evidence (Swanson hops + discovery_note)
```

**Принцип:** таксономия (Factory, Metal, Size…) — в графе для Browser, **не** в retrieval. PDF связывается **точечно**: `pdf_graph_linker` матчит ключевые слова в чанке → `graph_node_ids` + `EVIDENCED_BY` к `Source`. На ABC-пути граф подтягивает релевантные страницы литературы, не «все PDF → все механизмы».

## Граф — что связано

Каждый LossForm подключён через `ontology_wiring`:

```
Factory --HAS_LOSS--> LossForm --IN_SIZECLASS--> SizeClass
                              --OF_MINERAL--> Mineral
                              --CARRIES_METAL--> Metal
                              --RECOVERABLE|NON_RECOVERABLE--> Metal
                              --EVIDENCED_BY--> Source (Excel)
                              --EXPLAINED_BY--> Mechanism --> Process --> Equipment
```

PDF и схемы: узлы `Source` + `EVIDENCED_BY` — Excel/PNG через `ontology_wiring`, PDF через `pdf_graph_linker` (keyword → Mechanism/Process/Equipment/Mineral/Reagent).

## Что показать жюри (без кода)

1. **Neo4j Browser** — `assets/cypher/full_graph.cypher`
2. **`make demo`** — JSON с chunks + graph path H-01
3. **`ask_graph.py`** — «что делать с закрытым пентландитом +71 КГМК»
4. **`make neo4j-check`** — PASSED

## Документация

- [docs/README.md](README.md) — индекс
- [DATA_STORAGE.md](DATA_STORAGE.md) — граф + Qdrant, все поля
- [PROVENANCE.md](PROVENANCE.md) — цитаты, Swanson ABC
- [INGESTION.md](INGESTION.md) — пайплайн, Excel→MD

## Следующие шаги (приоритет)

1. MCP `graph_rag_query` для Agent-1
2. Yandex `text-search-doc` вместо TF-IDF
3. Loss-Attribution orchestrator (top buckets → router)
4. VLM tool для PNG (без ColQwen на MVP)
5. Streamlit: дашборд + карточка с graph path
