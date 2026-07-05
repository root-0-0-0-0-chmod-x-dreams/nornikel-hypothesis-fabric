
MATCH (n:Entity)
OPTIONAL MATCH (n)-[r]->(m:Entity)
RETURN n, r, m;
