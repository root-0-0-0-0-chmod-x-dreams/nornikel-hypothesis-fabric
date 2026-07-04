"""Wire taxonomy hubs and provenance — separate from intervention retrieval path."""

from __future__ import annotations

from graphrag.ingestion.domain import (
    CATALOG_MECHANISM_PROCESS,
    CATALOG_PROCESS_EQUIPMENT,
    FORM_LABEL_BY_SLUG,
)
from graphrag.ingestion.excel_parser import _slugify
from graphrag.models import Chunk, GraphEdge, GraphNode
from graphrag.schema import NodeType, RelationType

_METAL_LABELS = {"Ni": "Никель (Ni)", "Cu": "Медь (Cu)"}


def enrich_graph(
    nodes: list[GraphNode],
    edges: list[GraphEdge],
    chunks: list[Chunk],
) -> tuple[list[GraphNode], list[GraphEdge]]:
    """Add taxonomy + provenance for Browser; retrieval uses INTERVENTION_RELATIONS only."""
    nodes_by_id = {node.node_id: node for node in nodes}
    edge_keys = {(edge.source, edge.relation, edge.target) for edge in edges}
    new_edges: list[GraphEdge] = []

    loss_forms = [node for node in nodes if node.node_type == NodeType.LOSS_FORM]

    for loss_form in loss_forms:
        attrs = loss_form.attributes
        factory = str(attrs["factory"])
        size_class = str(attrs["size_class"])
        form_slug = str(attrs["mineral_form"])
        metal = str(attrs["metal"])
        source_file = str(attrs.get("source_file", ""))

        factory_id = _ensure_factory(nodes_by_id, factory)
        size_id = _ensure_size_class(nodes_by_id, size_class)
        mineral_id = _ensure_mineral(nodes_by_id, form_slug)
        metal_id = _ensure_metal(nodes_by_id, metal)

        _add_edge(
            new_edges,
            edge_keys,
            factory_id,
            loss_form.node_id,
            RelationType.HAS_LOSS,
        )
        _add_edge(
            new_edges,
            edge_keys,
            loss_form.node_id,
            size_id,
            RelationType.IN_SIZECLASS,
        )
        _add_edge(
            new_edges,
            edge_keys,
            loss_form.node_id,
            mineral_id,
            RelationType.OF_MINERAL,
        )
        _add_edge(
            new_edges,
            edge_keys,
            loss_form.node_id,
            metal_id,
            RelationType.CARRIES_METAL,
        )
        _add_edge(
            new_edges,
            edge_keys,
            factory_id,
            size_id,
            RelationType.RELATED_TO,
        )

        if source_file:
            source_id = _ensure_source(
                nodes_by_id,
                source_file,
                source_type="excel",
            )
            _add_edge(
                new_edges,
                edge_keys,
                loss_form.node_id,
                source_id,
                RelationType.EVIDENCED_BY,
            )

        if attrs.get("recoverable"):
            _add_edge(
                new_edges,
                edge_keys,
                loss_form.node_id,
                metal_id,
                RelationType.RECOVERABLE,
            )
        else:
            _add_edge(
                new_edges,
                edge_keys,
                loss_form.node_id,
                metal_id,
                RelationType.NON_RECOVERABLE,
            )

    for process_id, equipment_id in CATALOG_PROCESS_EQUIPMENT:
        _add_edge(
            new_edges,
            edge_keys,
            process_id,
            equipment_id,
            RelationType.USES_EQUIPMENT,
        )

    for mechanism_id, process_id in CATALOG_MECHANISM_PROCESS:
        _add_edge(
            new_edges,
            edge_keys,
            mechanism_id,
            process_id,
            RelationType.RELATED_MECHANISM,
        )

    for chunk in chunks:
        if chunk.chunk_type != "scheme_caption":
            continue

        source_id = _ensure_source(
            nodes_by_id,
            chunk.source,
            source_type="scheme",
            image_path=chunk.metadata.get("image_path"),
        )
        for node_id in chunk.graph_node_ids:
            if node_id in nodes_by_id:
                _add_edge(
                    new_edges,
                    edge_keys,
                    node_id,
                    source_id,
                    RelationType.EVIDENCED_BY,
                )

    return list(nodes_by_id.values()), [*edges, *new_edges]


def _ensure_factory(nodes_by_id: dict[str, GraphNode], factory: str) -> str:
    node_id = _slugify("factory", factory)
    if node_id not in nodes_by_id:
        nodes_by_id[node_id] = GraphNode(
            node_id=node_id,
            node_type=NodeType.FACTORY,
            label=factory,
            attributes={"factory": factory},
        )

    return node_id


def _ensure_size_class(nodes_by_id: dict[str, GraphNode], size_class: str) -> str:
    node_id = _slugify("size", size_class)
    if node_id not in nodes_by_id:
        nodes_by_id[node_id] = GraphNode(
            node_id=node_id,
            node_type=NodeType.SIZE_CLASS,
            label=size_class,
            attributes={"size_class": size_class},
        )

    return node_id


def _ensure_mineral(nodes_by_id: dict[str, GraphNode], form_slug: str) -> str:
    node_id = _slugify("mineral", form_slug)
    if node_id not in nodes_by_id:
        nodes_by_id[node_id] = GraphNode(
            node_id=node_id,
            node_type=NodeType.MINERAL,
            label=FORM_LABEL_BY_SLUG.get(form_slug, form_slug),
            attributes={"mineral_form": form_slug},
        )

    return node_id


def _ensure_metal(nodes_by_id: dict[str, GraphNode], metal: str) -> str:
    node_id = _slugify("metal", metal)
    if node_id not in nodes_by_id:
        nodes_by_id[node_id] = GraphNode(
            node_id=node_id,
            node_type=NodeType.METAL,
            label=_METAL_LABELS.get(metal, metal),
            attributes={"metal": metal},
        )

    return node_id


def _ensure_source(
    nodes_by_id: dict[str, GraphNode],
    source_file: str,
    *,
    source_type: str,
    doc_id: str | None = None,
    image_path: str | None = None,
) -> str:
    node_id = _slugify("source", source_type, source_file)
    if node_id not in nodes_by_id:
        nodes_by_id[node_id] = GraphNode(
            node_id=node_id,
            node_type=NodeType.SOURCE,
            label=source_file,
            attributes={
                "source_file": source_file,
                "source_type": source_type,
                "doc_id": doc_id,
                "image_path": image_path,
            },
        )

    return node_id


def _add_edge(
    edges: list[GraphEdge],
    edge_keys: set[tuple[str, str, str]],
    source: str,
    target: str,
    relation: str,
) -> None:
    key = (source, relation, target)

    if key in edge_keys:
        return

    edge_keys.add(key)
    edges.append(GraphEdge(source, target, relation))
