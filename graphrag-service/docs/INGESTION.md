# Ingestion: входные данные → граф + Qdrant

**MD-файлы здесь — это входные данные кейса** (bucket-и из Excel), не документация проекта.  
Документация проекта: [README.md](README.md).

Оркестратор: `graphrag/ingestion/pipeline.py` → `make bootstrap`.

## Поток

```
Excel (.xlsx)  ──► LossForm nodes + excel_bucket chunks
PDF            ──► pdf_text chunks + pdf_graph_linker → EVIDENCED_BY
Books (MD)     ──► book_text chunks (почанково) + тот же linker
PNG схем/регл. ──► scheme_caption chunks
constraints.py ──► constraint_* chunks + HAS_EQUIPMENT
external (RMQ) ──► external_text + EVIDENCED_BY

         ├─► NetworkX / Neo4j (граф)
         └─► Qdrant (dense + bm25)
```

---

## Excel (сейчас)

- Парсер: `excel_parser.py`
- На каждый bucket (фабрика × класс × форма × металл):
  - узел `LossForm` в графе
  - чанк `excel_{lossform_id}` в Qdrant
  - рёбра ABC (если `recoverable`)
- **Provenance:** `metadata.sheet`, `excel_row`, `excel_cell_ni` / `excel_cell_cu`

---

## Excel → Markdown (входные данные)

Excel конвертируем в `.md` — **это источник для ingestion**, не docs.

### Экспорт из xlsx

```bash
make excel-to-md
```

→ `Задача 1/…/md/buckets/{factory}/{lossform_id}.md`

### Bootstrap

Если есть `md/buckets/**/*.md` — **pipeline читает MD**, Excel пропускается.  
Иначе fallback на `.xlsx` как раньше.

Парсер: `graphrag/ingestion/md_parser.py`

### Формат одного bucket-файла

`md/buckets/{factory}/{lossform_id}.md`:

```markdown
---
chunk_id: excel_lossform_кгмк_+71_closed_pnt_cp_ni
node_id: lossform_кгмк_+71_closed_pnt_cp_ni
chunk_type: excel_bucket
factory: КГМК
source: Хвосты КГМК.xlsx
sheet: Лист1
excel_row: 47
excel_cell_ni: E47
graph_node_ids: ["lossform_кгмк_+71_closed_pnt_cp_ni", "mech_liberation", "equip_mshr"]
metal: Ni
tonnes: 2088
recoverable: true
mineral_form: closed_pnt_cp
size_class: "+71"
---

# КГМК · +71 · Закрытый Pnt/Cp · Ni

Текст bucket для retrieval и цитат…
```

---

## PDF

- `pdf_parser.py` — по страницам, split по абзацам (`\n\n`)
- `chunk_id`: `pdf_{doc}_p{page}_{paragraph_index}`
- `pdf_graph_linker.py` — keyword → `graph_node_ids` + `EVIDENCED_BY`

**Если есть `Дополнительные материалы/md/`** — PDF не парсятся напрямую, берутся MD-чанки.

---

## Книги → Markdown (входные данные)

Литература из `Дополнительные материалы/*.pdf` конвертируется в почанковые MD:

```bash
make pdf-to-md          # OpenDataLoader (default, нужен Java 11+)
# или
python3 scripts/pdf_to_md_chunks.py --backend pymupdf
python3 scripts/compare_pdf_backends.py   # сравнение метрик
```

→ `Дополнительные материалы/md/{doc_id}/p084_para_002.md`

Парсер: `graphrag/ingestion/md_book_parser.py`  
`chunk_type`: `book_text` — те же `EVIDENCED_BY` и цитаты (стр., §, granularity).

### Формат одного чанка

```markdown
---
doc_id: glemb_flotation
source: Глембоцкий-Классен.pdf
title: Флотационные методы обогащения
page: 84
paragraph_index: 2
granularity: paragraph
section: "Раскрытие сростков"
chunk_type: book_text
---
Текст абзаца…
```

Мета книги целиком — `md/{doc_id}/_book.meta.md`.  
Альтернатива: один файл с разделителем `---chunk---` между блоками frontmatter+текст.

Гранулярность в metadata: `paragraph`, `sentence`, `page`, `section`, `window`.

### Сравнение гранулярности (RAG vs GraphRAG)

```bash
make compare-granularity
```

Метрики на 6 запросах, полный корпус (excel + constraints + все книги), k=12:

| | RAG recall | GraphRAG recall | Δ | комментарий |
|---|---|---|---|---|
| сравниваются `sentence` … `window` | hybrid-only | graph+hybrid | graph lift | см. вывод скрипта |

**RAG** = `use_graph=False` (только dense+bm25 hybrid + constraints).  
**GraphRAG** = graph channel + ABC path + повторный boost graph при bucket.

**Продакшен (внедрено):** OpenDataLoader + **`paragraph`** + GraphRAG — константа `BOOK_CHUNK_GRANULARITY` в `graphrag/constants.py`, `make pdf-to-md`.

- `schemes.py` — caption + `graph_node_ids` из `SCHEME_NODE_HINTS`
- VLM / ColPali — позже

---

## Constraints

- `constraints.py` — регламенты, budget tiers, эталонные гипотезы
- `Factory --HAS_EQUIPMENT--> Equipment`

---

## External

- Gradio tab / RabbitMQ `external.ingest`
- `external_source.py` — auto-link + `EVIDENCED_BY`

---

## Перезагрузка

```bash
make infra-up
make bootstrap      # Qdrant + networkx
make neo4j-seed     # Neo4j Browser
make gradio-studio  # UI
```
