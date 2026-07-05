// Связи между книгами / источниками через общие темы (SHARES_TOPIC + RELATED_SOURCE)

MATCH (s1:Entity {node_type: 'Source'})-[rs:RELATED_SOURCE]-(s2:Entity {node_type: 'Source'})
OPTIONAL MATCH (a:Entity {node_type: 'Passage'})-[:PART_OF]->(s1)
OPTIONAL MATCH (b:Entity {node_type: 'Passage'})-[:PART_OF]->(s2)
OPTIONAL MATCH (a)-[t:SHARES_TOPIC]-(b)
RETURN s1, rs, s2, a, t, b
LIMIT 200;
