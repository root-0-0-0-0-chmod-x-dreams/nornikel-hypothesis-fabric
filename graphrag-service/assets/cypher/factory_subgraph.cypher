// Компактный вид: фабрики → потери → таксономия → интервенции
MATCH p=(f:Entity {node_type: 'Factory'})-[:HAS_LOSS|RELATED_TO|IN_SIZECLASS|OF_MINERAL|CARRIES_METAL|EXPLAINED_BY|ADDRESSED_BY|USES_EQUIPMENT|EVIDENCED_BY*1..6]->(x)
RETURN p
LIMIT 200;
