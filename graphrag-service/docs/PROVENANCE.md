# Provenance: цитаты и Swanson ABC

Код: `graphrag/provenance/`.

## Зачем

Жюри ждёт:
1. **Не просто имя файла**, а страница / абзац / ячейка Excel.
2. **Swanson ABC** — A→B в одном источнике, B→C в другом, **A→C выведено**, ни один документ не содержит цепочку целиком.

---

## Citation (структурированная цитата)

Каждый retrieval-hit и hop ABC несёт `Citation`:

| поле | пример |
|------|--------|
| `source` | `Глембоцкий-Классен.pdf` |
| `source_type` | `pdf` / `excel` / `scheme` / `regulation` / `external` |
| `chunk_id` | `pdf_глембоцкий_p12_0` |
| `page` | `12` |
| `paragraph_index` | `2` → отображается как **§3** |
| `excel_row` | `47` |
| `excel_cell` | `E47` |
| `sheet` | `Лист1` |
| `excerpt` | фрагмент текста (до 320 символов) |
| `highlight` | overlap с запросом |
| `display_ref` | `Глембоцкий.pdf, стр. 12, §3` |

API: `RetrievedChunk.citation`, RabbitMQ `graph_rag.query` → `chunks[].citation`.

---

## Swanson ABC — `abc_evidence`

В `GraphRAGResult.abc_evidence`:

```json
{
  "bucket_id": "lossform_кгмк_+71_closed_pnt_cp_ni",
  "bucket_label": "КГМК +71 …",
  "discovery_note": "Связь … собрана из 3 источников; ни один документ не содержит цепочку целиком (Swanson ABC).",
  "source_count": 3,
  "unique_sources": ["Хвосты КГМК.xlsx", "Глембоцкий.pdf", "Схема 5.png"],
  "hops": [
    {
      "hop": "A→B",
      "from_id": "lossform_…",
      "to_id": "mech_liberation",
      "relation": "EXPLAINED_BY",
      "inferred": false,
      "citations": [
        { "source": "Хвосты КГМК.xlsx", "excel_cell": "E47", "excerpt": "2088 т Ni…" },
        { "source": "Глембоцкий.pdf", "page": 84, "excerpt": "раскрытие закрытого пентландита…" }
      ]
    },
    {
      "hop": "B→C",
      "from_id": "mech_liberation",
      "to_id": "equip_mshr",
      "relation": "ADDRESSED_BY",
      "inferred": true,
      "citations": [
        { "source": "Схема 5.png", "excerpt": "МШР 3.2×3.8…" }
      ]
    }
  ]
}
```

- **hop 1** — факт из Excel + литература на механизм.
- **hop 2+** — `inferred: true` — связь собрана графом, источники на промежуточные узлы.

---

## Откуда берутся данные для цитат

| Источник | Как попадает в Citation |
|----------|-------------------------|
| Excel | `metadata.excel_row/cell` + chunk `excel_{lossform_id}` |
| PDF | `metadata.page`, `paragraph_index`; edge `EVIDENCED_BY.chunk_id` |
| PNG | `scheme_caption` + `EVIDENCED_BY` на Equipment |
| Constraints | `constraint_*` chunks в constraint-channel |

---

## Демо для питча (H-01)

**Вопрос:** закрытый пентландит +71 КГМК, доизмельчение  
**Bucket:** `lossform_кгмк_+71_closed_pnt_cp_ni`

| Hop | Узлы | Источники |
|-----|------|-----------|
| A→B | LossForm → mech_liberation | Excel E*, Глембоцкий стр. * |
| B→C | mech_liberation → process_comminution → equip_mshr | Схема 5, регламент |

Gradio → GraphRAG Query → блок **Swanson ABC** в meta.

---

## Карточка гипотезы (целевой формат)

```yaml
evidence_chain:
  - type: excel
    ref: "Хвосты КГМК.xlsx, E47"
    supports: "A"
  - type: pdf
    ref: "Глембоцкий, стр. 84, §2"
    supports: "A→B"
  - type: scheme
    ref: "Схема 5 — МШР"
    supports: "B→C"
discovery: "A→C inferred (Swanson ABC)"
```

Сборка из `abc_evidence` + top chunks — следующий шаг для Hypothesis Factory.
