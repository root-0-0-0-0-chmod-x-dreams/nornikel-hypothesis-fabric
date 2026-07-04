"""Swanson ABC: A→B + B→C evidence chains with per-hop citations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from graphrag.constants import EVIDENCE_RELATIONS, INTERVENTION_RELATIONS
from graphrag.graph.base import GraphStoreProtocol
from graphrag.models import GraphPath
from graphrag.provenance.citations import Citation, citation_for_chunk_id, citation_from_chunk
from graphrag.vector_protocol import VectorStoreProtocol


@dataclass
class ABCHopEvidence:
    hop: str
    from_id: str
    from_label: str
    to_id: str
    to_label: str
    relation: str
    inferred: bool
    citations: list[Citation] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hop": self.hop,
            "from_id": self.from_id,
            "from_label": self.from_label,
            "to_id": self.to_id,
            "to_label": self.to_label,
            "relation": self.relation,
            "inferred": self.inferred,
            "citations": [citation.to_dict() for citation in self.citations],
        }


@dataclass
class ABCEvidenceChain:
    bucket_id: str
    bucket_label: str
    hops: list[ABCHopEvidence] = field(default_factory=list)
    discovery_note: str = ""
    source_count: int = 0
    unique_sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "bucket_id": self.bucket_id,
            "bucket_label": self.bucket_label,
            "hops": [hop.to_dict() for hop in self.hops],
            "discovery_note": self.discovery_note,
            "source_count": self.source_count,
            "unique_sources": self.unique_sources,
        }


def build_abc_evidence_chain(
    graph: GraphStoreProtocol,
    vectors: VectorStoreProtocol,
    bucket_id: str | None,
    graph_paths: list[GraphPath],
    *,
    question: str = "",
) -> ABCEvidenceChain | None:
    if not bucket_id or not graph.has_node(bucket_id):
        return None

    bucket_attrs = graph.get_node_attributes(bucket_id) or {}
    bucket_label = str(bucket_attrs.get("label") or bucket_id)
    primary_path = _pick_primary_path(graph_paths, bucket_id)
    hops: list[ABCHopEvidence] = []
    all_sources: set[str] = set()

    hop_names = ("A→B", "B→C", "C→D", "D→E")

    for index, (source_id, relation, target_id) in enumerate(primary_path.edges):
        hop_label = hop_names[index] if index < len(hop_names) else f"hop-{index + 1}"
        inferred = index >= 1
        citations: list[Citation] = []

        if source_id == bucket_id:
            excel = _bucket_excel_citation(vectors, bucket_id, question=question)

            if excel is not None:
                citations.append(excel)

        citations.extend(
            _citations_for_entity(graph, vectors, target_id, question=question)
        )
        citations = _dedupe_citations(citations)

        for citation in citations:
            all_sources.add(citation.source)

        hops.append(
            ABCHopEvidence(
                hop=hop_label,
                from_id=source_id,
                from_label=_node_label(graph, source_id),
                to_id=target_id,
                to_label=_node_label(graph, target_id),
                relation=relation,
                inferred=inferred,
                citations=citations,
            )
        )

    if not hops:
        excel = _bucket_excel_citation(vectors, bucket_id, question=question)

        if excel is not None:
            all_sources.add(excel.source)
            hops.append(
                ABCHopEvidence(
                    hop="A",
                    from_id=bucket_id,
                    from_label=bucket_label,
                    to_id=bucket_id,
                    to_label=bucket_label,
                    relation="BUCKET",
                    inferred=False,
                    citations=[excel],
                )
            )

    if len(hops) >= 2:
        discovery = (
            f"Связь «{hops[0].from_label}» → «{hops[-1].to_label}» собрана из "
            f"{len(all_sources)} источников; ни один документ не содержит цепочку целиком (Swanson ABC)."
        )
    elif hops:
        discovery = "Цепочка интервенции с привязкой к источникам по узлам графа."
    else:
        discovery = ""

    return ABCEvidenceChain(
        bucket_id=bucket_id,
        bucket_label=bucket_label,
        hops=hops,
        discovery_note=discovery,
        source_count=len(all_sources),
        unique_sources=sorted(all_sources),
    )


def _pick_primary_path(paths: list[GraphPath], bucket_id: str) -> GraphPath:
    if not paths:
        return GraphPath(nodes=[bucket_id], edges=[])

    intervention_paths = [
        path
        for path in paths
        if path.edges
        and all(relation in INTERVENTION_RELATIONS for _src, relation, _tgt in path.edges)
    ]

    if not intervention_paths:
        return paths[0]

    return max(intervention_paths, key=lambda path: len(path.edges))


def _bucket_excel_citation(
    vectors: VectorStoreProtocol,
    bucket_id: str,
    *,
    question: str,
) -> Citation | None:
    return citation_for_chunk_id(vectors, f"excel_{bucket_id}", query=question)


def _citations_for_entity(
    graph: GraphStoreProtocol,
    vectors: VectorStoreProtocol,
    entity_id: str,
    *,
    question: str,
) -> list[Citation]:
    citations: list[Citation] = []

    for source_id in graph.neighbors(entity_id, relations=EVIDENCE_RELATIONS):
        if not source_id.startswith("source_"):
            continue

        edge_attrs = graph.get_edge_attributes(entity_id, source_id) or {}
        source_attrs = graph.get_node_attributes(source_id) or {}
        chunk_id = edge_attrs.get("chunk_id")
        citation: Citation | None = None

        if chunk_id:
            citation = citation_for_chunk_id(vectors, str(chunk_id), query=question)

        if citation is None:
            label = str(
                source_attrs.get("label") or source_attrs.get("source_file") or source_id
            )
            citation = Citation(
                source=label,
                source_type=str(source_attrs.get("source_type") or "source"),
                chunk_id=str(chunk_id or source_id),
                excerpt=label,
                page=int(edge_attrs["page"]) if edge_attrs.get("page") else None,
                source_url=source_attrs.get("source_url"),
            )

        citations.append(citation)

    if entity_id.startswith("lossform_"):
        chunk = vectors.get(f"excel_{entity_id}")

        if chunk is not None:
            citations.append(citation_from_chunk(chunk))

    return citations


def _node_label(graph: GraphStoreProtocol, node_id: str) -> str:
    attrs = graph.get_node_attributes(node_id) or {}

    return str(attrs.get("label") or node_id)


def _dedupe_citations(citations: list[Citation]) -> list[Citation]:
    seen: set[str] = set()
    unique: list[Citation] = []

    for citation in citations:
        key = citation.chunk_id or citation.display_ref()

        if key in seen:
            continue

        seen.add(key)
        unique.append(citation)

    return unique
