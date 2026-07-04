# Схема графа (Neo4j / GraphRAG)

Актуальная онтология и Cypher для Browser. Статус кода: [docs/IMPLEMENTATION.md](../docs/IMPLEMENTATION.md).

## Масштаб (после `make neo4j-seed`)

| Метрика | Значение |
|---------|----------|
| Узлов | ~273 |
| Рёбер | ~1400 |
| LossForm | 214 |
| Изолированных узлов | ≤15 |

---

## Граф vs векторка

| Данные | Граф | Qdrant (`hypothesis_text_chunks`) |
|--------|------|-----------------------------------|
| Excel bucket | `LossForm` + таксономия + ABC | `excel_bucket` chunk + metadata row/cell |
| Excel MD (план) | то же | frontmatter → тот же `chunk_type` |
| PDF абзац | `Source` + `EVIDENCED_BY` | `pdf_text` + `page`, `paragraph_index` |
| PNG схема | `Source` + `EVIDENCED_BY` | `scheme_caption` |
| Регламент / примеры | `HAS_EQUIPMENT` | `constraint_regulation`, `constraint_example` |
| Внешний текст | `EVIDENCED_BY` | `external_text` |
| Каталог | `Equipment`, `Process`, `Mechanism` | — |

**Правило:** граф = структура, id, provenance. Текст — в Qdrant. См. [docs/DATA_STORAGE.md](../docs/DATA_STORAGE.md).

---

## Узлы

См. `graphrag/schema.py` → `NodeType`. В Neo4j все с label `Entity` + property `node_type`.

| node_type | Откуда | node_id пример | Обязательные props |
|-----------|--------|----------------|-------------------|
| `LossForm` | Excel | `lossform_кгмк_+71_closed_pnt_cp_ni` | `factory`, `size_class`, `mineral_form`, `metal`, `tonnes`, `recoverable` |
| `Factory` | ontology_wiring | `factory_кгмк` | `factory` |
| `SizeClass` | ontology_wiring | `size_+71` | `size_class` |
| `Mineral` | ontology_wiring | `mineral_closed_pnt_cp` | `mineral_form` |
| `Metal` | ontology_wiring | `metal_ni` | `metal` |
| `Mechanism` | catalog | `mech_liberation` | `label`, `catalog` |
| `Process` | catalog | `process_comminution` | `label`, `catalog` |
| `Equipment` | catalog | `equip_mshr` | `label`, `catalog` |
| `Reagent` | pdf_graph_linker | `reagent_pdn` | `label`, `catalog` |
| `Source` | ontology_wiring / pdf_graph_linker | `source_pdf_глембоцкий_флотация_pdf` | `source_file`, `source_type` |
| `Hypothesis` | агент (план) | — | `claim`, `scores` |
| `Intervention` | агент (план) | — | `label`, `status` |

`node_id` строится через Unicode-slugify (`graphrag/ingestion/excel_parser.py`): кириллица фабрики сохраняется.

---

## Рёбра

См. `graphrag/schema.py` → `RelationType`.

### Таксономия (каждый LossForm)

```
Factory --HAS_LOSS--> LossForm
Factory --RELATED_TO--> SizeClass
LossForm --IN_SIZECLASS--> SizeClass
LossForm --OF_MINERAL--> Mineral
LossForm --CARRIES_METAL--> Metal
LossForm --RECOVERABLE|NON_RECOVERABLE--> Metal
LossForm --EVIDENCED_BY--> Source
```

### Swanson ABC (извлекаемые bucket-ы)

```
LossForm --EXPLAINED_BY--> Mechanism
Mechanism --ADDRESSED_BY--> Process
Mechanism --RELATED_MECHANISM--> Process
Process --USES_EQUIPMENT--> Equipment
Factory --HAS_EQUIPMENT--> Equipment
```

### Provenance + Swanson ABC

```
Mechanism|Process|Equipment --EVIDENCED_BY--> Source (attrs: page, chunk_id)
```

Ответ GraphRAG: `abc_evidence.hops[]` — цитаты на каждый hop A→B, B→C. См. [docs/PROVENANCE.md](../docs/PROVENANCE.md).

### План (агенты, не в ingestion)

```
Intervention --TARGETS--> LossForm
Intervention --PROPOSES_CHANGE--> Process
Hypothesis --EVIDENCED_BY--> Source
```

---

## Цепочка H-01

```
lossform_кгмк_+71_closed_pnt_cp_ni (2088 т Ni, recoverable)
  --EXPLAINED_BY--> mech_liberation
  --ADDRESSED_BY--> process_comminution
  --USES_EQUIPMENT--> equip_mshr, equip_gc660
```

Cypher:

```cypher
MATCH p=(b:Entity {node_id: 'lossform_кгмк_+71_closed_pnt_cp_ni'})-[*1..4]->(x)
RETURN p;
```

---

## Neo4j

```bash
make neo4j-up
make neo4j-seed
make neo4j-check
```

| Параметр | Значение |
|----------|----------|
| Browser | http://localhost:7474 |
| Bolt | `bolt://localhost:7687` |
| Auth | `neo4j` / `hypothesis2026` |

### Показать всё

```cypher
MATCH (n:Entity)
OPTIONAL MATCH (n)-[r]->(m:Entity)
RETURN n, r, m;
```

Файл: `assets/cypher/full_graph.cypher`

### По фабрикам (компактнее)

```cypher
MATCH p=(f:Entity {node_type: 'Factory'})-[*1..6]->(x)
RETURN p LIMIT 200;
```

Файл: `assets/cypher/factory_subgraph.cypher`

### Топ потерь Ni

```cypher
MATCH (n:Entity)
WHERE n.node_type = 'LossForm' AND n.metal = 'Ni'
RETURN n.label, n.tonnes, n.recoverable, n.factory
ORDER BY n.tonnes DESC LIMIT 10;
```

### Статистика по типам

```cypher
MATCH (n:Entity)
RETURN n.node_type AS type, count(*) AS cnt
ORDER BY cnt DESC;
```

---

## Без Cypher (text-to-Cypher)

```bash
python3 scripts/ask_graph.py "где больше всего теряется никель на КГМК"
python3 scripts/ask_graph.py "что делать с закрытым пентландитом в классе +71 на КГМК"
python3 scripts/ask_graph.py -i
```

---

## Конфиг

- `graphrag/constants.py` — лимиты retrieval, Neo4j defaults
- `graphrag/config.py` — `AppConfig.from_env()`
- `GRAPH_BACKEND=networkx|neo4j`

## Модули ingestion

| Файл | Роль |
|------|------|
| `excel_parser.py` | LossForm + intervention edges |
| `md_parser.py` | ✅ MD buckets из `md/buckets/` (входные данные) |
| `constraints.py` | регламенты, budget, HAS_EQUIPMENT |
| `external_source.py` | внешние источники |
| `pdf_parser.py` | PDF chunks |
| `pdf_graph_linker.py` | keyword → graph_node_ids + EVIDENCED_BY |
| `schemes.py` | PNG metadata + graph_node hints |
| `catalog.py` | Статический каталог |
| `ontology_wiring.py` | Таксономия + Source + плотность графа |
| `pipeline.py` | Orchestrator загрузки |
