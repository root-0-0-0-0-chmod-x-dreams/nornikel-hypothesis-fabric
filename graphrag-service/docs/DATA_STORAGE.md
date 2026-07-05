# Хранение данных: граф + векторка

Краткий справочник полей. Код: `graphrag/models.py`, `graphrag/qdrant_store.py`.

## Два слоя

| | **Граф** (Neo4j / NetworkX) | **Векторка** (Qdrant `hypothesis_text_chunks`) |
|---|-----------------------------|------------------------------------------------|
| Содержимое | Узлы, рёбра, атрибуты | Текст чанков |
| Текст | Нет | `text`, `summary` |
| Связь | `EVIDENCED_BY.chunk_id`, `page` | `graph_node_ids[]` |
| Поиск | traverse, NL→Cypher | dense + BM25 + hybrid |

**Мост:** `graph_node_ids` в чанке ↔ узлы графа; `EVIDENCED_BY` в графе ↔ `chunk_id` + страница.

---

## Граф — узлы (`Entity` + `node_type`)

| node_type | Ключевые props |
|-----------|----------------|
| `LossForm` | `factory`, `size_class`, `mineral_form`, `metal`, `tonnes`, `recoverable`, `source_file` |
| `Factory` | `factory` |
| `SizeClass` | `size_class` |
| `Mineral` | `mineral_form` |
| `Metal` | `metal` |
| `Mechanism`, `Process`, `Equipment`, `Reagent` | `label`, `catalog` |
| `Source` | `source_file`, `source_type`, `source_url` |

`node_id` пример: `lossform_кгмк_+71_closed_pnt_cp_ni`, `equip_mshr`.

---

## Граф — рёбра

| relation | смысл |
|----------|--------|
| `HAS_LOSS`, `IN_SIZECLASS`, `OF_MINERAL`, `CARRIES_METAL` | таксономия bucket |
| `RECOVERABLE` / `NON_RECOVERABLE` | физпотолок |
| `EXPLAINED_BY`, `ADDRESSED_BY`, `RELATED_MECHANISM` | Swanson ABC |
| `USES_EQUIPMENT` | Process → Equipment |
| `HAS_EQUIPMENT` | Factory → Equipment (регламент) |
| `EVIDENCED_BY` | Entity → Source (`page`, `chunk_id`, `external`) |

---

## Векторка — поля чанка (payload Qdrant)

| поле | тип | описание |
|------|-----|----------|
| `chunk_id` | str | уникальный id |
| `text` | str | тело для retrieval |
| `summary` | str | краткое описание |
| `source` | str | имя файла / заголовок |
| `factory` | str? | КГМК, ТОФ, НОФ вкр… |
| `chunk_type` | str | см. ниже |
| `graph_node_ids` | list[str] | мост к графу |
| `external` | bool | внешний источник |
| `metadata` | dict | ячейки Excel, page, budget_tier… |

**Векторы:** `dense` (TF-IDF, dim≈512), `bm25` (sparse).

---

## `chunk_type` — полный список

| chunk_type | источник |
|------------|----------|
| `excel_bucket` | Excel хвостов (или MD-экспорт, см. [INGESTION.md](INGESTION.md)) |
| `pdf_text` | PDF справочники (по абзацам) |
| `scheme_caption` | PNG схем / регламентов |
| `constraint_regulation` | выжимки регламентов |
| `constraint_budget` | tier low / medium / high |
| `constraint_example` | эталонные гипотезы |
| `external_text` | внешние источники (RMQ / Gradio) |

---

## `metadata` по типам

### Excel / excel_bucket

```json
{
  "sheet": "Лист1",
  "excel_row": 47,
  "excel_cell_ni": "E47",
  "excel_cell_cu": "G47",
  "metal": "Ni"
}
```

### PDF / pdf_text

```json
{
  "page": 12,
  "paragraph_index": 2,
  "doc_id": "глембоцкий_флотация"
}
```

### constraint_example

```json
{ "budget_tier": "low" }
```

### scheme_caption

```json
{ "image_path": "…/Схема 5.png" }
```

---

## Масштаб (после `make bootstrap`)

```
nodes:              ~277
edges:              ~1540
chunks (Qdrant):    ~1770+
loss_forms:         214
constraint_chunks:  ~11
```

---

## Связанные документы

- [PROVENANCE.md](PROVENANCE.md) — цитаты, Swanson ABC
- [INGESTION.md](INGESTION.md) — пайплайн, Excel→MD
- [../graphrag/SCHEMA.md](../graphrag/SCHEMA.md) — Cypher, онтология
