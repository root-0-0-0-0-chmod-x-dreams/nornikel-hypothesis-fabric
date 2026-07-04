# graphrag

GraphRAG MVP: **VectorStore** + **Graph** (networkx / Neo4j) + **GraphRAGQueryService** + **text-to-Cypher**.

Данные — из файлов кейса (`Задача 1. Фабрика гипотез/`), без синтетического seed.

Полный статус: [docs/IMPLEMENTATION.md](../docs/IMPLEMENTATION.md) · Схема графа: [SCHEMA.md](SCHEMA.md)

## Быстрый старт

```bash
pip install -r requirements.txt
make bootstrap   # ~273 nodes, ~1400 edges, ~1813 chunks
make test
make demo        # GraphRAG H-01: КГМК +71 closed Pnt Ni
```

## Neo4j + Browser

```bash
make neo4j-up
make neo4j-seed
make neo4j-check
# http://localhost:7474  neo4j / hypothesis2026
# Запрос «всё»: assets/cypher/full_graph.cypher
```

## Все make-цели

| Цель | Действие |
|------|----------|
| `install` | pip install -r requirements.txt |
| `bootstrap` | Загрузка кейса, print stats |
| `demo` | GraphRAG JSON на реальном bucket |
| `test` | pytest |
| `neo4j-up` | docker compose up -d |
| `neo4j-seed` | Залить граф в Neo4j |
| `neo4j-check` | Cypher smoke + assertions |
| `ask-graph` | Примеры text-to-Cypher |
| `format` / `lint` | black, isort, flake8, pylint |

## Скрипты

| Скрипт | Пример |
|--------|--------|
| `scripts/bootstrap_kb.py` | `make bootstrap` |
| `scripts/demo_graph_rag.py` | `make demo` |
| `scripts/seed_neo4j.py` | `make neo4j-seed` |
| `scripts/check_neo4j.py` | `make neo4j-check` / `--json` |
| `scripts/ask_graph.py` | `python3 scripts/ask_graph.py -i` |

## Text-to-Cypher

Пользователь пишет по-русски — шаблоны строят безопасный read-only Cypher:

```bash
python3 scripts/ask_graph.py "где больше всего теряется никель на КГМК"
python3 scripts/ask_graph.py "что делать с закрытым пентландитом в классе +71 на КГМК" --cypher
python3 scripts/ask_graph.py --examples
```

Intents: `stats`, `top_losses`, `intervention_path`, `factory_breakdown`, `recoverable_losses`, `search_nodes`, `list_by_type`.

## GraphRAG Query API

```python
from graphrag.bootstrap import bootstrap, build_service

loaded = bootstrap()
print(loaded.stats)

svc = build_service()
result = svc.query(
    "доизмельчение МШР",
    bucket_id="lossform_кгмк_+71_closed_pnt_cp_ni",
    factory="КГМК",
    k_out=5,
)
# result.node_ids, result.chunks, result.channel_hits
```

Поток: `graph traverse` → `fetch_by_graph_nodes` → `dense` + `BM25` → `RRF` → `rerank`.

## NL Graph API

```python
from graphrag.nl_cypher import NLGraphQueryService

svc = NLGraphQueryService()
answer = svc.ask("топ потерь никеля на КГМК")
print(answer.answer)
print(answer.cypher)
svc.close()
```

## Структура

```
graphrag/
  bootstrap.py          # entry: load case files
  constants.py / config.py / schema.py / models.py
  ingestion/
    excel_parser.py     # LossForm
    pdf_parser.py       # PDF chunks
    schemes.py          # PNG captions
    catalog.py          # Equipment / Process / Mechanism
    ontology_wiring.py  # Factory, Size, Mineral, Metal, Source
    pipeline.py
  graph/
    networkx_store.py   # dev / tests
    neo4j_store.py      # prod / Browser
  qdrant_store.py       # Qdrant: dense + BM25 sparse (default)
  vector_store.py       # fallback in-memory TF-IDF + BM25
  sparse_embeddings.py  # fastembed Qdrant/bm25 → sparse vectors
  embeddings.py / fusion.py
  service.py            # GraphRAGQueryService
  nl_cypher/            # text-to-Cypher
```

## Env

```bash
export GRAPH_BACKEND=neo4j          # default: networkx
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=hypothesis2026
```

## Диаграммы

- [08_graph_rag_query.md](../assets/diagrams/08_graph_rag_query.md) — эталон query-блока
- [07_storage_internals.md](../assets/diagrams/07_storage_internals.md) — vector + graph
- [05_agent_interaction.md](../assets/diagrams/05_agent_interaction.md) — агенты
