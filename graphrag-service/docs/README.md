# Документация GraphRAG (хакатон)

| Документ | О чём |
|----------|--------|
| [DATA_STORAGE.md](DATA_STORAGE.md) | Граф vs Qdrant, поля, chunk_type, metadata |
| [PROVENANCE.md](PROVENANCE.md) | Цитаты, страницы/ячейки, Swanson ABC |
| [INGESTION.md](INGESTION.md) | Пайплайн загрузки, **Excel→MD** формат |
| [IMPLEMENTATION.md](IMPLEMENTATION.md) | Статус фич в коде |
| [../graphrag/SCHEMA.md](../graphrag/SCHEMA.md) | Онтология, Cypher |
| [../graphrag/MESSAGING.md](../graphrag/MESSAGING.md) | RabbitMQ, RPC |

Быстрый старт: `make infra-up && make bootstrap && make gradio-studio`
