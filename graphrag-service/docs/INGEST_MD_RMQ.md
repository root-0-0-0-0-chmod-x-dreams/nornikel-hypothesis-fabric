# Ingest сырого Markdown через RabbitMQ

Контракт для **внешнего сервиса** (data-processor, chunker, ETL): на вход GraphRAG приходит **только `.md`**, независимо от исходного формата (PDF, DOCX, Excel, CSV, HTML).

GraphRAG не конвертирует файлы — конвертация **до** нас. Мы парсим MD, кладём в **Qdrant** + **граф**, связываем с каталогом сущностей.

---

## Транспорт

| Параметр | Значение |
|----------|----------|
| Exchange | `hypothesis.factory` (topic) |
| Очередь | `chunks_text` |
| Тип сообщения | `ingest.markdown` |
| Ответ | RPC `{ "ok": true, "payload": { ... } }` |

Env worker:

```bash
RABBITMQ_URL=amqp://hypothesis:hypothesis2026@localhost:5672/
VECTOR_BACKEND=qdrant
QDRANT_URL=http://localhost:6333
```

---

## Запрос

```json
{
  "type": "ingest.markdown",
  "payload": {
    "markdown": "---\nchunk_type: book_text\n...\n---\nТекст абзаца…",
    "source_path": "uploads/report.pdf.md",
    "source_url": "https://optional/original-url",
    "factory": "КГМК",
    "auto_link": true
  }
}
```

| Поле | Обяз. | Описание |
|------|-------|----------|
| `markdown` | ✅ | Полный текст MD: YAML frontmatter + body |
| `source_path` | — | Имя/путь для provenance и `citation` (рекомендуется) |
| `source_url` | — | URL исходника (веб, S3 presigned, …) |
| `factory` | — | Принудительно проставить `factory` на все чанки |
| `auto_link` | — | Default `true`: keyword-link `graph_node_ids` + `EVIDENCED_BY` |

Алиасы: `content` вместо `markdown`, `filename` вместо `source_path`.

---

## Ответ

```json
{
  "ok": true,
  "payload": {
    "chunk_ids": ["book_report_p003_para1"],
    "chunk_count": 1,
    "nodes_added": 0,
    "edges_added": 3,
    "chunk_types": ["book_text"],
    "source_path": "uploads/report.pdf.md"
  }
}
```

| Поле | Смысл |
|------|-------|
| `chunk_ids` | ID чанков в Qdrant |
| `chunk_count` | Сколько чанков создано из одного MD |
| `nodes_added` | Новые узлы графа (LossForm для `excel_bucket`) |
| `edges_added` | Рёбра ABC / `EVIDENCED_BY` / passage wiring |
| `chunk_types` | Типы созданных чанков |

Ошибка: `{ "ok": false, "error": "markdown is required" }`.

---

## Python-клиент

```python
from graphrag.messaging import GraphRagMessagingClient

client = GraphRagMessagingClient()

md = Path("report.md").read_text(encoding="utf-8")

result = client.ingest_markdown(
    md,
    source_path="report.md",
    factory="КГМК",          # опционально
    auto_link=True,
)

print(result["chunk_ids"])
client.close()
```

---

## Формат Markdown

Общее правило: **YAML frontmatter** между `---` … `---`, дальше **body** (текст для embedding).

Parser: `graphrag/ingestion/md_frontmatter.py`.

### Тип 1 — литература / PDF / DOCX / HTML → `book_text`

Один абзац = один MD-файл (рекомендуется для streaming ingest).

```markdown
---
doc_id: glemb_flotation
source: Глембоцкий-Классен.pdf
title: Флотационные методы обогащения
original_format: pdf
page: 84
paragraph_index: 2
granularity: paragraph
section: "Раскрытие сростков"
chunk_type: book_text
chunk_id: book_glemb_flotation_p084_para_002
graph_node_ids: ["mech_liberation"]
factory: КГМК
---

Текст абзаца для retrieval…
```

| Frontmatter | Зачем |
|-------------|-------|
| `source` | Имя исходного файла → `citation.source` |
| `original_format` | `pdf`, `docx`, `xlsx`, `csv`, … — provenance |
| `page`, `paragraph_index` | Цитаты «стр. N, §M» |
| `section` | Заголовок раздела |
| `chunk_id` | Стабильный ID; если нет — генерируется |
| `graph_node_ids` | Явные связи с графом; если пусто — `auto_link` |
| `factory` | Фильтр retrieval по фабрике |

**Несколько чанков в одном файле** — разделитель `---chunk---`:

```markdown
---
doc_id: manual
source: manual.docx
chunk_type: book_text
page: 1
paragraph_index: 0
---
Первый абзац.

---chunk---

---
page: 1
paragraph_index: 1
---
Второй абзац.
```

---

### Тип 2 — Excel / CSV (LossForm bucket) → `excel_bucket`

Один bucket = один MD. Создаёт **узел LossForm** в графе + чанк + ABC-рёбра.

```markdown
---
chunk_id: excel_lossform_кгмк_+71_closed_pnt_cp_ni
node_id: lossform_кгмк_+71_closed_pnt_cp_ni
chunk_type: excel_bucket
factory: КГМК
source: Хвосты КГМК.xlsx
original_format: xlsx
sheet: Лист1
excel_row: 47
excel_cell_ni: E47
metal: Ni
tonnes: 2088
recoverable: true
mineral_form: closed_pnt_cp
size_class: "+71"
graph_node_ids: ["lossform_кгмк_+71_closed_pnt_cp_ni", "mech_liberation", "equip_mshr"]
---

# КГМК · +71 · Закрытый Pnt · Ni
Текст bucket для retrieval…
```

Обязательно для bucket: `factory` + поля LossForm **или** явный `chunk_type: excel_bucket`.

---

### Тип 3 — MD без frontmatter (fallback)

Если frontmatter нет — один чанк `book_text`, `doc_id` = stem из `source_path`.

Data-processor **лучше** всегда добавлять frontmatter (хотя бы `source`, `original_format`, `chunk_type`).

---

### Тип 4 — иллюстрация (PNG/JPG) → `md_image`

**Один чанк = одна ссылка на картинку** в body. Файлы лежат отдельно от MD (папка `images/` или `Схемы флотации/`).

```markdown
---
doc_id: glemb_flotation
source: Глембоцкий-Классен.pdf
title: Флотационные методы обогащения
original_format: pdf
page: 37
chunk_type: md_image
chunk_id: book_glemb_flotation_p037_image_001
summary: Схема флотационной линии
factory: КГМК
---

![Схема флотационной линии](../images/glemb_flotation/p037_scheme.png)
```

| Правило | Детали |
|---------|--------|
| Body | **Только** `![alt](path)` — одна ссылка, без текста вокруг |
| `summary` / alt | Текст для embedding (caption); если нет — берётся alt |
| `path` | Относительный от MD или имя файла; резолв в `Дополнительные материалы/images/`, `Схемы флотации/`, `Регламенты/` |
| Хранение | Байты PNG **не** в Qdrant — только `image_path`, `image_rel_path` в metadata |
| Смешанный чанк | Текст + картинка в одном файле → текстовый `book_text`, markdown-ссылка вырезается из body |

Авто-детект: если body — только `![…](…)`, тип `md_image` ставится даже без `chunk_type` в frontmatter.

**Layout данных:**

```
data/case/Дополнительные материалы/
  md/<book>/p037_image_001.md
  images/<book>/p037_scheme.png    # рекомендуемый путь для chunker
data/case/Схемы флотации/*.png      # legacy / общие схемы
```

---

## Что делает GraphRAG после приёма

1. Парсит frontmatter + body (`md_ingest.py`)
2. `excel_bucket` → узел LossForm + ABC edges
3. `book_text` / прочее → чанки без LossForm node
4. `md_image` → чанк с caption + путь к файлу; узел Source + `EVIDENCED_BY` (как `scheme_caption`)
5. `auto_link: true` → keyword match → `graph_node_ids`, `EVIDENCED_BY`
6. `upsert` в Qdrant (dense + BM25)
7. `wire_passages_incremental` — passage nodes в графе

После ingest документ **сразу** участвует в `graphrag.query`.

---

## Рекомендуемый пайплайн upstream

```
Любой файл → data-processor → markdown_content
                    ↓
              chunker (rules/LLM)
                    ↓
         MD с frontmatter (1 chunk = 1 файл или ---chunk---)
                    ↓
         RMQ ingest.markdown → GraphRAG worker
```

**data-processor** отдаёт plain MD — **chunker обязан**:
- порезать на абзацы/секции;
- **картинки — отдельные MD-файлы** с одной ссылкой `![alt](path)`, файлы в `images/`;
- добавить YAML (`source`, `page`, `original_format`, …);
- слать `ingest.markdown` **по файлу** или **по чанку**.

---

## Альтернатива: `chunk.upsert`

Если upstream сам мапит MD → JSON, можно слать готовые чанки без парсера:

```json
{
  "type": "chunk.upsert",
  "payload": {
    "chunk_id": "...",
    "text": "...",
    "source": "...",
    "chunk_type": "book_text",
    "factory": "КГМК",
    "graph_node_ids": [],
    "metadata": { "page": 84, "original_format": "pdf" }
  }
}
```

Минус: нет auto-link и LossForm graph wiring — всё нужно заполнить руками.

`ingest.markdown` — **предпочтительный** путь для сырого MD.

---

## Связь с query

Ingest **не возвращает** evidence для LLM. После ingest LLM Service вызывает:

```python
client.graphrag_query(question="...", hypotheses=[...])
```

См. [doca.md](../doca.md) — что приходит в ответе unified query.

---

## Примеры ошибок

| Ситуация | Результат |
|----------|-----------|
| Пустой `markdown` | `error: markdown is required` |
| Frontmatter есть, body пустой | `no chunks parsed from markdown` |
| Bucket без `factory` | парсится как `book_text`, не LossForm |
| Дубликат `chunk_id` | upsert перезапишет точку в Qdrant |

---

## Тесты

```bash
pytest tests/test_md_ingest.py tests/test_md_image_refs.py -q
```
