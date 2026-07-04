"""Wire text passages (chunks) into the graph with cross-source topical links."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from graphrag.ingestion.excel_parser import _slugify
from graphrag.ingestion.pdf_graph_linker import _ensure_literature_source
from graphrag.models import Chunk, GraphEdge, GraphNode
from graphrag.schema import NodeType, RelationType

PASSAGE_CHUNK_TYPES = frozenset(
    {
        "book_text",
        "pdf_text",
        "external_text",
        "constraint_regulation",
        "constraint_example",
    }
)

CATALOG_ENTITY_PREFIXES = (
    "mech_",
    "process_",
    "equip_",
    "reagent_",
    "mineral_",
    "metal_",
)

MIN_SHARED_ENTITIES_FOR_TOPIC = 2
MAX_TOPIC_NEIGHBORS_PER_PASSAGE = 10
MAX_ENTITY_FREQUENCY_FOR_TOPIC = 350
MIN_SHARED_FOR_HYPOTHESIS_SUPPORT = 1


@dataclass
class PassageWireResult:
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    passage_count: int
    topic_edges: int
    sequence_edges: int
    hypothesis_links: int
    source_links: int


def wire_passages(
    nodes: list[GraphNode],
    edges: list[GraphEdge],
    chunks: list[Chunk],
) -> PassageWireResult:
    """Create Passage nodes and inter-chunk / inter-source graph links."""
    nodes_by_id = {node.node_id: node for node in nodes}
    edge_keys = {(edge.source, edge.relation, edge.target) for edge in edges}
    new_edges: list[GraphEdge] = []

    passage_chunks = [chunk for chunk in chunks if chunk.chunk_type in PASSAGE_CHUNK_TYPES]
    passage_ids: list[str] = []
    passage_entities: dict[str, set[str]] = {}
    passage_source: dict[str, str] = {}
    hypotheses: dict[str, set[str]] = {}

    for chunk in passage_chunks:
        passage_id = passage_node_id(chunk.chunk_id)
        source_id = _resolve_source_id(nodes_by_id, chunk)
        entities = _catalog_entities(chunk)

        nodes_by_id[passage_id] = GraphNode(
            node_id=passage_id,
            node_type=NodeType.PASSAGE,
            label=_passage_label(chunk),
            attributes={
                "chunk_id": chunk.chunk_id,
                "chunk_type": chunk.chunk_type,
                "source": chunk.source,
                "source_id": source_id,
                "doc_id": chunk.metadata.get("doc_id"),
                "page": chunk.metadata.get("page"),
                "paragraph_index": chunk.metadata.get("paragraph_index"),
                "granularity": chunk.metadata.get("granularity"),
                "factory": chunk.factory,
                "external": chunk.external,
                "source_url": chunk.source_url,
                "section": chunk.section or chunk.metadata.get("section"),
                "excerpt": chunk.text[:320].replace("\n", " "),
                "md_path": chunk.metadata.get("md_path"),
            },
        )

        passage_ids.append(passage_id)
        passage_entities[passage_id] = entities
        passage_source[passage_id] = source_id

        _add_edge(new_edges, edge_keys, passage_id, source_id, RelationType.PART_OF)

        for entity_id in entities:
            if entity_id in nodes_by_id:
                _add_edge(
                    new_edges,
                    edge_keys,
                    passage_id,
                    entity_id,
                    RelationType.MENTIONS,
                    attributes={"chunk_id": chunk.chunk_id},
                )

        if chunk.chunk_type == "constraint_example":
            hypothesis_id = _ensure_example_hypothesis(
                nodes_by_id,
                chunk,
                passage_id,
                new_edges,
                edge_keys,
            )
            hypotheses[hypothesis_id] = entities

    sequence_edges = _wire_reading_order(
        passage_chunks,
        passage_source,
        new_edges,
        edge_keys,
    )
    topic_edges, source_links = _wire_topic_links(
        passage_ids,
        passage_entities,
        passage_source,
        new_edges,
        edge_keys,
    )
    hypothesis_links = _wire_hypothesis_support(
        passage_ids,
        passage_entities,
        hypotheses,
        new_edges,
        edge_keys,
    )

    return PassageWireResult(
        nodes=list(nodes_by_id.values()),
        edges=[*edges, *new_edges],
        passage_count=len(passage_ids),
        topic_edges=topic_edges,
        sequence_edges=sequence_edges,
        hypothesis_links=hypothesis_links,
        source_links=source_links,
    )


def wire_passages_incremental(
    graph,
    chunks: list[Chunk],
) -> PassageWireResult:
    """Add passage nodes/edges for newly ingested chunks (external ingest, RMQ)."""
    passage_chunks = [chunk for chunk in chunks if chunk.chunk_type in PASSAGE_CHUNK_TYPES]
    if not passage_chunks:
        return PassageWireResult([], [], 0, 0, 0, 0, 0)

    nodes_by_id: dict[str, GraphNode] = {}
    passage_entities, passage_source = _load_passage_index_from_graph(graph)

    for node_id, entities in passage_entities.items():
        attrs = graph.get_node_attributes(node_id) or {}
        nodes_by_id[node_id] = GraphNode(
            node_id=node_id,
            node_type=NodeType.PASSAGE,
            label=attrs.get("label", node_id),
            attributes={
                key: value for key, value in attrs.items() if key not in {"node_type", "label"}
            },
        )

    edge_keys: set[tuple[str, str, str]] = set()
    new_edges: list[GraphEdge] = []
    new_passage_ids: list[str] = []
    hypotheses = _load_hypothesis_entities(graph, nodes_by_id)

    for chunk in passage_chunks:
        passage_id = passage_node_id(chunk.chunk_id)
        if graph.has_node(passage_id):
            continue

        source_id = _resolve_source_id(nodes_by_id, chunk)
        entities = _catalog_entities(chunk)

        passage_node = GraphNode(
            node_id=passage_id,
            node_type=NodeType.PASSAGE,
            label=_passage_label(chunk),
            attributes={
                "chunk_id": chunk.chunk_id,
                "chunk_type": chunk.chunk_type,
                "source": chunk.source,
                "source_id": source_id,
                "doc_id": chunk.metadata.get("doc_id"),
                "page": chunk.metadata.get("page"),
                "paragraph_index": chunk.metadata.get("paragraph_index"),
                "granularity": chunk.metadata.get("granularity"),
                "factory": chunk.factory,
                "external": chunk.external,
                "source_url": chunk.source_url,
                "section": chunk.section or chunk.metadata.get("section"),
                "excerpt": chunk.text[:320].replace("\n", " "),
                "md_path": chunk.metadata.get("md_path"),
            },
        )
        nodes_by_id[passage_id] = passage_node
        graph.add_node(passage_node)

        passage_entities[passage_id] = entities
        passage_source[passage_id] = source_id
        new_passage_ids.append(passage_id)

        part_of = GraphEdge(passage_id, source_id, RelationType.PART_OF)
        graph.add_edge(part_of)
        new_edges.append(part_of)

        for entity_id in entities:
            if not graph.has_node(entity_id):
                continue

            mention = GraphEdge(
                passage_id,
                entity_id,
                RelationType.MENTIONS,
                attributes={"chunk_id": chunk.chunk_id},
            )
            graph.add_edge(mention)
            new_edges.append(mention)

    sequence_edges = _wire_reading_order(
        passage_chunks,
        passage_source,
        new_edges,
        edge_keys,
        graph=graph,
    )
    topic_edges, source_links = _wire_topic_links(
        new_passage_ids,
        passage_entities,
        passage_source,
        new_edges,
        edge_keys,
        graph=graph,
    )
    hypothesis_links = _wire_hypothesis_support(
        new_passage_ids,
        passage_entities,
        hypotheses,
        new_edges,
        edge_keys,
        graph=graph,
    )

    return PassageWireResult(
        nodes=list(nodes_by_id.values()),
        edges=new_edges,
        passage_count=len(new_passage_ids),
        topic_edges=topic_edges,
        sequence_edges=sequence_edges,
        hypothesis_links=hypothesis_links,
        source_links=source_links,
    )


def passage_node_id(chunk_id: str) -> str:
    return f"passage_{chunk_id}"


def _passage_label(chunk: Chunk) -> str:
    page = chunk.metadata.get("page")
    paragraph_index = chunk.metadata.get("paragraph_index")
    bits = [chunk.source[:48] if chunk.source else chunk.chunk_id[:32]]

    if page is not None:
        bits.append(f"p.{page}")

    if paragraph_index is not None:
        bits.append(f"§{paragraph_index}")

    return " · ".join(bits)


def _catalog_entities(chunk: Chunk) -> set[str]:
    return {
        node_id
        for node_id in chunk.graph_node_ids
        if node_id.startswith(CATALOG_ENTITY_PREFIXES)
    }


def _resolve_source_id(nodes_by_id: dict[str, GraphNode], chunk: Chunk) -> str:
    if chunk.chunk_type in {"book_text", "pdf_text"}:
        return _ensure_literature_source(nodes_by_id, chunk)

    if chunk.chunk_type == "external_text":
        source_id = chunk.metadata.get("source_id")
        if source_id:
            return str(source_id)

        return _slugify("source", "external", chunk.source)

    if chunk.chunk_type == "constraint_example":
        return _ensure_constraint_source(
            nodes_by_id,
            "examples",
            "constraints/examples",
        )

    if chunk.chunk_type == "constraint_regulation":
        return _ensure_constraint_source(
            nodes_by_id,
            "regulation",
            chunk.source or "constraints/regulation",
        )

    return _slugify("source", chunk.chunk_type, chunk.source or chunk.chunk_id)


def _ensure_constraint_source(
    nodes_by_id: dict[str, GraphNode],
    kind: str,
    label: str,
) -> str:
    source_id = _slugify("source", "constraint", kind)

    if source_id not in nodes_by_id:
        nodes_by_id[source_id] = GraphNode(
            node_id=source_id,
            node_type=NodeType.SOURCE,
            label=label,
            attributes={
                "source_file": label,
                "source_type": "constraint",
                "constraint_kind": kind,
            },
        )

    return source_id


def _ensure_example_hypothesis(
    nodes_by_id: dict[str, GraphNode],
    chunk: Chunk,
    passage_id: str,
    edges: list[GraphEdge],
    edge_keys: set[tuple[str, str, str]],
) -> str:
    hypothesis_id = _slugify("hypothesis", chunk.chunk_id)
    source_id = _resolve_source_id(nodes_by_id, chunk)

    if hypothesis_id not in nodes_by_id:
        nodes_by_id[hypothesis_id] = GraphNode(
            node_id=hypothesis_id,
            node_type=NodeType.HYPOTHESIS,
            label=chunk.summary or chunk.text[:72],
            attributes={
                "claim": chunk.text,
                "factory": chunk.factory,
                "budget_tier": chunk.metadata.get("budget_tier"),
                "chunk_id": chunk.chunk_id,
                "example": True,
            },
        )

    _add_edge(edges, edge_keys, hypothesis_id, passage_id, RelationType.HAS_PASSAGE)
    _add_edge(edges, edge_keys, hypothesis_id, source_id, RelationType.EVIDENCED_BY)

    return hypothesis_id


def _wire_reading_order(
    chunks: list[Chunk],
    passage_source: dict[str, str],
    edges: list[GraphEdge],
    edge_keys: set[tuple[str, str, str]],
    *,
    graph=None,
) -> int:
    groups: dict[tuple[str, str], list[Chunk]] = defaultdict(list)

    for chunk in chunks:
        passage_id = passage_node_id(chunk.chunk_id)
        source_id = passage_source.get(passage_id) or str(chunk.metadata.get("source_id") or "")
        doc_key = str(chunk.metadata.get("doc_id") or chunk.source or source_id)
        groups[(source_id, doc_key)].append(chunk)

    added = 0

    for group_chunks in groups.values():
        ordered = sorted(
            group_chunks,
            key=lambda chunk: (
                int(chunk.metadata.get("page") or 0),
                int(chunk.metadata.get("paragraph_index") or 0),
                chunk.chunk_id,
            ),
        )

        for left, right in zip(ordered, ordered[1:], strict=False):
            before = passage_node_id(left.chunk_id)
            after = passage_node_id(right.chunk_id)
            attrs = {
                "page": right.metadata.get("page"),
                "paragraph_index": right.metadata.get("paragraph_index"),
            }
            _add_edge(
                edges,
                edge_keys,
                before,
                after,
                RelationType.NEXT_PASSAGE,
                attributes=attrs,
            )
            if graph is not None:
                graph.add_edge(GraphEdge(before, after, RelationType.NEXT_PASSAGE, attributes=attrs))
            added += 1

    return added


def _wire_topic_links(
    passage_ids: list[str],
    passage_entities: dict[str, set[str]],
    passage_source: dict[str, str],
    edges: list[GraphEdge],
    edge_keys: set[tuple[str, str, str]],
    *,
    graph=None,
) -> tuple[int, int]:
    entity_freq: dict[str, int] = defaultdict(int)

    for entities in passage_entities.values():
        for entity_id in entities:
            entity_freq[entity_id] += 1

    entity_to_passages: dict[str, list[str]] = defaultdict(list)

    for passage_id, entities in passage_entities.items():
        for entity_id in entities:
            if entity_freq[entity_id] <= MAX_ENTITY_FREQUENCY_FOR_TOPIC:
                entity_to_passages[entity_id].append(passage_id)

    topic_added = 0
    source_pairs: dict[tuple[str, str], int] = defaultdict(int)

    for passage_id in passage_ids:
        entities = passage_entities.get(passage_id, set())
        if not entities:
            continue

        scores: dict[str, int] = defaultdict(int)
        shared_with: dict[str, set[str]] = defaultdict(set)

        for entity_id in entities:
            if entity_freq[entity_id] > MAX_ENTITY_FREQUENCY_FOR_TOPIC:
                continue

            for other_id in entity_to_passages[entity_id]:
                if other_id == passage_id:
                    continue

                scores[other_id] += 1
                shared_with[other_id].add(entity_id)

        ranked = sorted(
            (
                (other_id, count)
                for other_id, count in scores.items()
                if count >= MIN_SHARED_ENTITIES_FOR_TOPIC
            ),
            key=lambda item: (-item[1], item[0]),
        )[:MAX_TOPIC_NEIGHBORS_PER_PASSAGE]

        for other_id, count in ranked:
            left, right = sorted((passage_id, other_id))
            attrs = {
                "shared_count": count,
                "shared_entities": sorted(shared_with[other_id]),
            }
            _add_edge(
                edges,
                edge_keys,
                left,
                right,
                RelationType.SHARES_TOPIC,
                attributes=attrs,
            )
            if graph is not None:
                graph.add_edge(GraphEdge(left, right, RelationType.SHARES_TOPIC, attributes=attrs))

            topic_added += 1

            src_a = passage_source.get(passage_id)
            src_b = passage_source.get(other_id)
            if src_a and src_b and src_a != src_b:
                source_pairs[tuple(sorted((src_a, src_b)))] += 1

    source_added = 0

    for (left, right), count in source_pairs.items():
        attrs = {"shared_topic_passages": count}
        _add_edge(
            edges,
            edge_keys,
            left,
            right,
            RelationType.RELATED_SOURCE,
            attributes=attrs,
        )
        if graph is not None:
            graph.add_edge(GraphEdge(left, right, RelationType.RELATED_SOURCE, attributes=attrs))
        source_added += 1

    return topic_added, source_added


def _wire_hypothesis_support(
    passage_ids: list[str],
    passage_entities: dict[str, set[str]],
    hypotheses: dict[str, set[str]],
    edges: list[GraphEdge],
    edge_keys: set[tuple[str, str, str]],
    *,
    graph=None,
) -> int:
    if not hypotheses:
        return 0

    added = 0
    example_passage_ids = {
        passage_id
        for passage_id in passage_ids
        if passage_id.startswith("passage_constraint_example")
    }

    for passage_id in passage_ids:
        if passage_id in example_passage_ids:
            continue

        entities = passage_entities.get(passage_id, set())
        if not entities:
            continue

        for hypothesis_id, hyp_entities in hypotheses.items():
            shared = entities & hyp_entities
            if len(shared) < MIN_SHARED_FOR_HYPOTHESIS_SUPPORT:
                continue

            attrs = {"shared_entities": sorted(shared)}
            _add_edge(
                edges,
                edge_keys,
                passage_id,
                hypothesis_id,
                RelationType.SUPPORTS_HYPOTHESIS,
                attributes=attrs,
            )
            if graph is not None:
                graph.add_edge(
                    GraphEdge(
                        passage_id,
                        hypothesis_id,
                        RelationType.SUPPORTS_HYPOTHESIS,
                        attributes=attrs,
                    )
                )
            added += 1

    return added


def _load_passage_index_from_graph(graph) -> tuple[dict[str, set[str]], dict[str, str]]:
    passage_entities: dict[str, set[str]] = {}
    passage_source: dict[str, str] = {}

    if not hasattr(graph, "_graph"):
        return passage_entities, passage_source

    for node_id, data in graph._graph.nodes(data=True):
        if data.get("node_type") != NodeType.PASSAGE:
            continue

        entities = {
            target
            for target in graph._graph.successors(node_id)
            if graph._graph.edges[node_id, target].get("relation") == RelationType.MENTIONS
        }
        passage_entities[node_id] = entities
        passage_source[node_id] = str(data.get("source_id") or "")

    return passage_entities, passage_source


def _load_hypothesis_entities(
    graph,
    nodes_by_id: dict[str, GraphNode],
) -> dict[str, set[str]]:
    hypotheses: dict[str, set[str]] = {}

    if not hasattr(graph, "_graph"):
        return hypotheses

    for node_id, data in graph._graph.nodes(data=True):
        if data.get("node_type") != NodeType.HYPOTHESIS:
            continue

        nodes_by_id[node_id] = GraphNode(
            node_id=node_id,
            node_type=NodeType.HYPOTHESIS,
            label=data.get("label", node_id),
            attributes={
                key: value for key, value in data.items() if key not in {"node_type", "label"}
            },
        )

        entities = {
            target
            for target in graph._graph.successors(node_id)
            if graph._graph.edges[node_id, target].get("relation") == RelationType.HAS_PASSAGE
        }

        for passage_id in entities:
            passage_entities = {
                target
                for target in graph._graph.successors(passage_id)
                if graph._graph.edges[passage_id, target].get("relation") == RelationType.MENTIONS
            }
            hypotheses[node_id] = passage_entities
            break

    return hypotheses


def _add_edge(
    edges: list[GraphEdge],
    edge_keys: set[tuple[str, str, str]],
    source: str,
    target: str,
    relation: str,
    *,
    attributes: dict | None = None,
) -> None:
    key = (source, relation, target)

    if key in edge_keys:
        return

    edge_keys.add(key)
    edges.append(GraphEdge(source, target, relation, attributes=attributes or {}))
