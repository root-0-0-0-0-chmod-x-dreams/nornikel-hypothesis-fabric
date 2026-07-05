# GraphRAG Service

Hybrid retrieval + knowledge graph microservice for Hypothesis Factory. Exposes RabbitMQ RPC (`graphrag.query`) for LLM Service and agents.

## Quick start

```bash
cp .env.example .env
make install
make infra-up          # rabbitmq + qdrant + neo4j
make bootstrap         # load case data into Qdrant + in-memory graph
make rmq-worker        # separate terminal
make rmq-query         # smoke test
make test
```

Case data: bundled in `data/case` (Excel) + `data/literature` (book MD). Refresh from hackathon case:

```bash
make sync-data       # copy Excel + md/md → data/
make bootstrap       # Qdrant + graph
```

Override path: `GRAPHRAG_DATA_ROOT`. Default picks `data/case` if present.

## Docker

```bash
cp .env.example .env
docker compose up -d              # infra + worker
docker compose run --rm graphrag-worker python3 scripts/bootstrap_kb.py  # one-off bootstrap
```

Bootstrap is typically run on the host (needs case files mounted or `GRAPHRAG_DATA_ROOT`).

## RPC contract

See [graphrag/MESSAGING.md](graphrag/MESSAGING.md) for queue names and `graphrag.query` payload.

Minimal request from LLM Service:

```json
{
  "question": "...",
  "hypotheses": [{"id": "h1", "label": "...", "retrieval_query": "..."}],
  "constraints": [],
  "k_out": 8
}
```

GraphRAG auto-resolves `bucket_id`, `factory`, `budget_tier`, `agent_role`, and `constraints` when omitted.

## Layout

| Path | Role |
|------|------|
| `graphrag/` | Core library (retrieval, graph, messaging, ingestion) |
| `scripts/` | CLI: worker, bootstrap, checks, demo |
| `tests/` | pytest suite |
| `assets/cypher/` | Neo4j seed queries |
| `docs/` | Implementation and data docs |
