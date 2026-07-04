"""Link PDF chunks to graph entities by domain keyword matching (NER-lite)."""

from __future__ import annotations

from dataclasses import dataclass

from graphrag.ingestion.excel_parser import _slugify
from graphrag.models import Chunk, GraphEdge, GraphNode
from graphrag.schema import NodeType, RelationType

# node_id -> lowercase keyword triggers (must appear in chunk text)
EQUIPMENT_HINTS: dict[str, tuple[str, ...]] = {
    "equip_mshr": ("мшр", "шаровая мельница", "доизмельч"),
    "equip_mshc": ("мшц", "цилиндрическ"),
    "equip_gc660": ("гц-660", "гц 660", "гидроциклон", "циклон"),
    "equip_fpm": ("фпм", "флотомашин", "флотацион"),
    "equip_kmd": ("кмд", "дробил", "щель"),
    "equip_nelson": ("нельсон", "nelson", "концентратор"),
}

MECHANISM_HINTS: dict[str, tuple[str, ...]] = {
    "mech_liberation": (
        "раскрыт",
        "сростк",
        "закрыт",
        "включен",
        "включён",
        "либерац",
    ),
    "mech_slime_recovery": ("шлам", "тонк", "минус 10", "-10", "колонн"),
    "mech_millerite_activation": ("миллерит", "активац", "сульфид"),
}

PROCESS_HINTS: dict[str, tuple[str, ...]] = {
    "process_comminution": ("измельч", "помол", "дроблен"),
    "process_classification": ("классиф", "гидроциклон", "спирал"),
    "process_flotation": ("флотац", "пен", "концентрат"),
    "process_slime_flotation": ("флотац шлам", "шламов", "тонкого"),
}

MINERAL_HINTS: dict[str, tuple[str, ...]] = {
    "mineral_open_pnt_cp": ("раскрыт", "пентландит", "открыт"),
    "mineral_closed_pnt_cp": ("закрыт", "пентландит", "включен", "включён"),
    "mineral_millerite": ("миллерит",),
    "mineral_pyrrhotite_impurity": ("пирротин", "примесь"),
    "mineral_silicate_valleriite": ("силикат", "валлериит"),
    "mineral_pyrite": ("пирит",),
}

REAGENT_HINTS: dict[str, tuple[str, ...]] = {
    "reagent_pdn": ("пдн", "пентанол"),
    "reagent_af": ("аф ", "аф-", "собирател"),
    "reagent_nas": ("na2s", "сульфид натр", "сернист"),
    "reagent_taf": ("таф", "taf"),
}

METAL_HINTS: dict[str, tuple[str, ...]] = {
    "metal_ni": ("никел", "элемент 28", "ni "),
    "metal_cu": ("мед", "элемент 29", "cu ", "халькопирит"),
}

LITERATURE_CHUNK_TYPES = frozenset({"pdf_text", "book_text"})


@dataclass
class PdfGraphLinkResult:
    chunks: list[Chunk]
    edges: list[GraphEdge]
    linked_chunks: int
    literature_edges: int


def link_pdf_chunks_to_graph(
    chunks: list[Chunk],
    nodes_by_id: dict[str, GraphNode],
) -> PdfGraphLinkResult:
    """Tag PDF chunks with graph_node_ids and add EVIDENCED_BY edges."""
    updated: list[Chunk] = []
    edges: list[GraphEdge] = []
    edge_keys: set[tuple[str, str, str]] = set()
    linked_chunks = 0
    literature_edges = 0

    for chunk in chunks:
        if chunk.chunk_type not in LITERATURE_CHUNK_TYPES:
            updated.append(chunk)
            continue

        matched = match_entities(chunk.text.lower())
        if not matched:
            updated.append(chunk)
            continue

        linked_chunks += 1
        source_id = _ensure_literature_source(nodes_by_id, chunk)
        page = chunk.metadata.get("page")

        enriched = Chunk(
            chunk_id=chunk.chunk_id,
            text=chunk.text,
            summary=chunk.summary,
            questions=chunk.questions,
            source=chunk.source,
            factory=chunk.factory,
            section=chunk.section,
            chunk_type=chunk.chunk_type,
            graph_node_ids=sorted(set(chunk.graph_node_ids) | matched),
            external=chunk.external,
            source_url=chunk.source_url,
            metadata={**chunk.metadata, "graph_entities": sorted(matched)},
        )
        updated.append(enriched)

        for entity_id in matched:
            if entity_id not in nodes_by_id:
                continue

            key = (entity_id, RelationType.EVIDENCED_BY, source_id)
            if key in edge_keys:
                continue

            edge_keys.add(key)
            edges.append(
                GraphEdge(
                    entity_id,
                    source_id,
                    RelationType.EVIDENCED_BY,
                    attributes={
                        "page": page,
                        "chunk_id": chunk.chunk_id,
                        "paragraph_index": chunk.metadata.get("paragraph_index"),
                        "granularity": chunk.metadata.get("granularity"),
                    },
                )
            )
            literature_edges += 1

    return PdfGraphLinkResult(
        chunks=updated,
        edges=edges,
        linked_chunks=linked_chunks,
        literature_edges=literature_edges,
    )


def match_entities(text_lower: str) -> set[str]:
    matched: set[str] = set()

    for hint_map in (
        EQUIPMENT_HINTS,
        MECHANISM_HINTS,
        PROCESS_HINTS,
        MINERAL_HINTS,
        REAGENT_HINTS,
        METAL_HINTS,
    ):
        for node_id, keywords in hint_map.items():
            if any(keyword in text_lower for keyword in keywords):
                matched.add(node_id)

    return matched


def _ensure_literature_source(nodes_by_id: dict[str, GraphNode], chunk: Chunk) -> str:
    source_kind = "book" if chunk.chunk_type == "book_text" else "pdf"
    source_id = _slugify("source", source_kind, chunk.source)

    if source_id not in nodes_by_id:
        nodes_by_id[source_id] = GraphNode(
            node_id=source_id,
            node_type=NodeType.SOURCE,
            label=chunk.source,
            attributes={
                "source_file": chunk.source,
                "source_type": source_kind,
                "doc_id": chunk.metadata.get("doc_id"),
                "title": chunk.metadata.get("title"),
                "author": chunk.metadata.get("author"),
            },
        )

    return source_id


def _ensure_pdf_source(nodes_by_id: dict[str, GraphNode], chunk: Chunk) -> str:
    return _ensure_literature_source(nodes_by_id, chunk)


def ensure_reagent_catalog_nodes(nodes_by_id: dict[str, GraphNode]) -> None:
    """Add reagent nodes referenced by PDF linker."""
    labels = {
        "reagent_pdn": "ПДН-11 (собиратель)",
        "reagent_af": "Af (собиратель)",
        "reagent_nas": "Na2S (сульфидатор)",
        "reagent_taf": "ТАФ-7",
    }

    for node_id, label in labels.items():
        if node_id in nodes_by_id:
            continue

        nodes_by_id[node_id] = GraphNode(
            node_id=node_id,
            node_type=NodeType.REAGENT,
            label=label,
            attributes={"catalog": True},
        )
