# Bundled case data for GraphRAG bootstrap

| Path | Contents |
|------|----------|
| `case/Пример 1–4/` | Excel LossForm |
| `case/Дополнительные материалы/md/<book>/` | Paragraph-chunked literature (5 books, ~5775 chunks) |
| `literature/` | Monolithic book MD source (`## Страница N` format) |

Refresh from local hackathon case (optional):

```bash
make sync-data          # Excel + chunked dirs + monolithic literature
make literature-chunks  # only books without chunks (e.g. new monolithic)
make bootstrap          # Qdrant + in-memory graph
```

Bootstrap uses `data/case` automatically (override: `GRAPHRAG_DATA_ROOT`).
