# Cypher-запросы для Neo4j Browser

Подключение: http://localhost:7474 · `neo4j` / `hypothesis2026`

Перед использованием: `make neo4j-seed`

## Быстрый просмотр (без Cypher)

```bash
make graph-html    # output/graph/graph_*.html
open output/graph/graph_literature.html
```

Или в Gradio Studio → вкладка **Graph Map**.

## full_graph.cypher

Показать **все** узлы и связи (включая bucket-ы без исходящих рёбер):

```cypher
MATCH (n:Entity)
OPTIONAL MATCH (n)-[r]->(m:Entity)
RETURN n, r, m;
```

## factory_subgraph.cypher

Компактный вид от фабрик (до 200 path):

```cypher
MATCH p=(f:Entity {node_type: 'Factory'})-[*1..6]->(x)
RETURN p LIMIT 200;
```

## passage_graph.cypher

Параграфы, источники, гипотезы и связи `PART_OF` / `NEXT_PASSAGE` / `SHARES_TOPIC` / `SUPPORTS_HYPOTHESIS` (лимит 500 path).

## literature_crosslinks.cypher

Связи **между книгами** через `RELATED_SOURCE` и `SHARES_TOPIC`.

## Полезные ad-hoc запросы

**H-01 цепочка:**
```cypher
MATCH p=(b:Entity {node_id: 'lossform_кгмк_+71_closed_pnt_cp_ni'})-[*1..4]->(x)
RETURN p;
```

**Топ-10 потерь Ni:**
```cypher
MATCH (n:Entity)
WHERE n.node_type = 'LossForm' AND n.metal = 'Ni'
RETURN n.label, n.tonnes, n.factory
ORDER BY n.tonnes DESC LIMIT 10;
```

**Без Cypher:** `python3 scripts/ask_graph.py -i`
