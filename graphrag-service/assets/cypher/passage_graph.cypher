// Литературный слой: параграфы, источники, гипотезы, связи между чанками
// Рекомендуется для просмотра passage_wiring (не весь граф сразу)

MATCH (p:Entity {node_type: 'Passage'})
OPTIONAL MATCH (p)-[r1:PART_OF|NEXT_PASSAGE|MENTIONS|SHARES_TOPIC|SUPPORTS_HYPOTHESIS]->(x:Entity)
OPTIONAL MATCH (p)<-[r2:HAS_PASSAGE|SUPPORTS_HYPOTHESIS]-(y:Entity)
RETURN p, r1, x, r2, y
LIMIT 500;
