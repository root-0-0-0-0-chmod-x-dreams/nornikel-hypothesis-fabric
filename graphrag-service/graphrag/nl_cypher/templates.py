"""Cypher templates for NL graph queries."""

from __future__ import annotations

from typing import Any

from graphrag.constants import INTERVENTION_RELATIONS, NEO4J_ENTITY_LABEL
from graphrag.nl_cypher.models import ParsedQuery, QueryIntent


def build_cypher(
    parsed: ParsedQuery, *, bucket_id: str | None = None
) -> tuple[str, dict[str, Any]]:
    builders = {
        QueryIntent.STATS: _stats,
        QueryIntent.FACTORY_BREAKDOWN: _factory_breakdown,
        QueryIntent.TOP_LOSSES: _top_losses,
        QueryIntent.BUCKET_LOOKUP: _bucket_lookup,
        QueryIntent.INTERVENTION_PATH: _intervention_path,
        QueryIntent.SEARCH_NODES: _search_nodes,
        QueryIntent.LIST_BY_TYPE: _list_by_type,
        QueryIntent.RECOVERABLE_LOSSES: _recoverable_losses,
        QueryIntent.LITERATURE_EVIDENCE: _literature_evidence,
        QueryIntent.NEIGHBORS: _neighbors,
        QueryIntent.EDGE_STATS: _edge_stats,
        QueryIntent.PROCESS_EQUIPMENT: _process_equipment,
    }
    builder = builders[parsed.intent]

    return builder(parsed, bucket_id=bucket_id)


def _stats(
    _parsed: ParsedQuery, *, bucket_id: str | None = None
) -> tuple[str, dict[str, Any]]:
    _ = bucket_id
    cypher = f"""
    MATCH (n:{NEO4J_ENTITY_LABEL})
    WITH count(n) AS nodes
    MATCH ()-[r]->()
    WITH nodes, count(r) AS edges
    MATCH (lf:{NEO4J_ENTITY_LABEL})
    WHERE lf.node_type = 'LossForm'
    RETURN nodes, edges, count(lf) AS loss_forms
    """
    return cypher, {}


def _factory_breakdown(
    _parsed: ParsedQuery, *, bucket_id: str | None = None
) -> tuple[str, dict[str, Any]]:
    _ = bucket_id
    cypher = f"""
    MATCH (n:{NEO4J_ENTITY_LABEL})
    WHERE n.node_type = 'LossForm'
    RETURN n.factory AS factory,
           count(*) AS buckets,
           round(sum(n.tonnes), 1) AS total_tonnes
    ORDER BY total_tonnes DESC
    """
    return cypher, {}


def _top_losses(
    parsed: ParsedQuery, *, bucket_id: str | None = None
) -> tuple[str, dict[str, Any]]:
    _ = bucket_id
    filters = ["n.node_type = 'LossForm'"]
    params: dict[str, Any] = {"limit": parsed.limit}

    if parsed.factory:
        filters.append("n.factory = $factory")
        params["factory"] = parsed.factory

    if parsed.metal:
        filters.append("n.metal = $metal")
        params["metal"] = parsed.metal

    if parsed.form_slug:
        filters.append("n.mineral_form = $form_slug")
        params["form_slug"] = parsed.form_slug

    if parsed.size_class:
        filters.append("n.size_class = $size_class")
        params["size_class"] = parsed.size_class

    where_clause = " AND ".join(filters)
    cypher = f"""
    MATCH (n:{NEO4J_ENTITY_LABEL})
    WHERE {where_clause}
    RETURN n.node_id AS node_id,
           n.label AS label,
           n.tonnes AS tonnes,
           n.recoverable AS recoverable
    ORDER BY n.tonnes DESC
    LIMIT $limit
    """
    return cypher, params


def _bucket_lookup(
    parsed: ParsedQuery, *, bucket_id: str | None = None
) -> tuple[str, dict[str, Any]]:
    if bucket_id:
        cypher = f"""
        MATCH (n:{NEO4J_ENTITY_LABEL})
        WHERE n.node_type = 'LossForm' AND n.node_id = $bucket_id
        RETURN n.node_id AS node_id,
               n.label AS label,
               n.tonnes AS tonnes,
               n.recoverable AS recoverable,
               n.factory AS factory,
               n.size_class AS size_class,
               n.mineral_form AS mineral_form,
               n.metal AS metal
        """
        return cypher, {"bucket_id": bucket_id}

    return _top_losses(parsed, bucket_id=bucket_id)


def _intervention_path(
    parsed: ParsedQuery, *, bucket_id: str | None = None
) -> tuple[str, dict[str, Any]]:
    if not bucket_id:
        return _top_losses(parsed, bucket_id=bucket_id)

    rel_types = "|".join(sorted(INTERVENTION_RELATIONS))
    cypher = f"""
    MATCH (b:{NEO4J_ENTITY_LABEL} {{node_id: $bucket_id}})
    OPTIONAL MATCH p=(b)-[:{rel_types}*1..4]->(m:{NEO4J_ENTITY_LABEL})
    RETURN b.node_id AS bucket_id,
           b.label AS bucket_label,
           b.tonnes AS tonnes,
           b.recoverable AS recoverable,
           [node IN nodes(p) | node.node_id] AS path_nodes,
           [rel IN relationships(p) | type(rel)] AS path_rels,
           m.node_id AS target_id,
           m.node_type AS target_type,
           m.label AS target_label
    ORDER BY size(path_nodes)
    """
    return cypher, {"bucket_id": bucket_id}


def _search_nodes(
    parsed: ParsedQuery, *, bucket_id: str | None = None
) -> tuple[str, dict[str, Any]]:
    _ = bucket_id
    search = parsed.search_text or parsed.question
    cypher = f"""
    MATCH (n:{NEO4J_ENTITY_LABEL})
    WHERE toLower(n.label) CONTAINS toLower($search)
       OR toLower(n.node_id) CONTAINS toLower($search)
    RETURN n.node_id AS node_id,
           n.node_type AS node_type,
           n.label AS label
    ORDER BY n.node_type, n.label
    LIMIT $limit
    """
    return cypher, {"search": search, "limit": parsed.limit}


def _list_by_type(
    parsed: ParsedQuery, *, bucket_id: str | None = None
) -> tuple[str, dict[str, Any]]:
    _ = bucket_id
    node_type = parsed.node_type or "Equipment"
    cypher = f"""
    MATCH (n:{NEO4J_ENTITY_LABEL})
    WHERE n.node_type = $node_type
    RETURN n.node_id AS node_id, n.label AS label
    ORDER BY n.label
    LIMIT $limit
    """
    return cypher, {"node_type": node_type, "limit": parsed.limit}


def _recoverable_losses(
    parsed: ParsedQuery, *, bucket_id: str | None = None
) -> tuple[str, dict[str, Any]]:
    _ = bucket_id
    filters = ["n.node_type = 'LossForm'", "n.recoverable = true"]
    params: dict[str, Any] = {"limit": parsed.limit}

    if parsed.factory:
        filters.append("n.factory = $factory")
        params["factory"] = parsed.factory

    if parsed.metal:
        filters.append("n.metal = $metal")
        params["metal"] = parsed.metal

    where_clause = " AND ".join(filters)
    cypher = f"""
    MATCH (n:{NEO4J_ENTITY_LABEL})
    WHERE {where_clause}
    RETURN n.node_id AS node_id,
           n.label AS label,
           n.tonnes AS tonnes
    ORDER BY n.tonnes DESC
    LIMIT $limit
    """
    return cypher, params


def _literature_evidence(
    parsed: ParsedQuery, *, bucket_id: str | None = None
) -> tuple[str, dict[str, Any]]:
    _ = bucket_id
    entity = parsed.entity_id or parsed.search_text or "mech_liberation"
    cypher = f"""
    MATCH (e:{NEO4J_ENTITY_LABEL})
    WHERE e.node_id = $entity_id
       OR toLower(e.label) CONTAINS toLower($entity_id)
    MATCH (e)-[r:EVIDENCED_BY]->(s:{NEO4J_ENTITY_LABEL})
    WHERE s.node_type = 'Source'
    RETURN e.node_id AS entity_id,
           e.label AS entity_label,
           s.node_id AS source_id,
           s.label AS source_label,
           s.source_file AS source_file,
           r.page AS page,
           r.chunk_id AS chunk_id
    ORDER BY s.label
    LIMIT $limit
    """
    return cypher, {"entity_id": entity, "limit": parsed.limit}


def _neighbors(
    parsed: ParsedQuery, *, bucket_id: str | None = None
) -> tuple[str, dict[str, Any]]:
    node_id = parsed.entity_id or bucket_id or parsed.search_text

    if not node_id:
        return _search_nodes(parsed, bucket_id=bucket_id)

    cypher = f"""
    MATCH (n:{NEO4J_ENTITY_LABEL} {{node_id: $node_id}})
    OPTIONAL MATCH (n)-[r_out]->(out:{NEO4J_ENTITY_LABEL})
    RETURN n.node_id AS center_id,
           n.label AS center_label,
           type(r_out) AS relation,
           out.node_id AS neighbor_id,
           out.node_type AS neighbor_type,
           out.label AS neighbor_label,
           'out' AS direction
    UNION
    MATCH (n:{NEO4J_ENTITY_LABEL} {{node_id: $node_id}})
    MATCH (in:{NEO4J_ENTITY_LABEL})-[r_in]->(n)
    RETURN n.node_id AS center_id,
           n.label AS center_label,
           type(r_in) AS relation,
           in.node_id AS neighbor_id,
           in.node_type AS neighbor_type,
           in.label AS neighbor_label,
           'in' AS direction
    LIMIT $limit
    """
    return cypher, {"node_id": node_id, "limit": parsed.limit}


def _edge_stats(
    _parsed: ParsedQuery, *, bucket_id: str | None = None
) -> tuple[str, dict[str, Any]]:
    _ = bucket_id
    cypher = """
    MATCH ()-[r]->()
    RETURN type(r) AS relation, count(*) AS edges
    ORDER BY edges DESC
    """
    return cypher, {}


def _process_equipment(
    parsed: ParsedQuery, *, bucket_id: str | None = None
) -> tuple[str, dict[str, Any]]:
    _ = bucket_id
    process_id = (
        parsed.entity_id if parsed.entity_id and parsed.entity_id.startswith("process_") else None
    )
    search = process_id or parsed.search_text or "измельч"

    cypher = f"""
    MATCH (p:{NEO4J_ENTITY_LABEL})
    WHERE p.node_type = 'Process'
      AND (p.node_id = $search OR toLower(p.label) CONTAINS toLower($search))
    MATCH (p)-[:USES_EQUIPMENT|ADDRESSED_BY*0..2]-(e:{NEO4J_ENTITY_LABEL})
    WHERE e.node_type = 'Equipment'
    RETURN DISTINCT p.node_id AS process_id,
           p.label AS process_label,
           e.node_id AS equipment_id,
           e.label AS equipment_label
    ORDER BY process_label, equipment_label
    LIMIT $limit
    """
    return cypher, {"search": search, "limit": parsed.limit}
