"""RAG vs GraphRAG retrieval benchmark across book chunk granularities."""

from __future__ import annotations

import math
import statistics
from dataclasses import asdict, dataclass, field
from pathlib import Path

from graphrag.constants import BOOK_CHUNK_GRANULARITY
from graphrag.graph.networkx_store import NetworkXGraphStore
from graphrag.ingestion.book_chunking import ALL_GRANULARITIES, rechunk_paragraphs
from graphrag.ingestion.catalog import build_catalog_nodes
from graphrag.ingestion.constraints import build_constraint_chunks, build_factory_equipment_edges
from graphrag.ingestion.excel_parser import _slugify, parse_excel_file
from graphrag.ingestion.md_book_parser import _chunk_from_parts
from graphrag.ingestion.ontology_wiring import enrich_graph
from graphrag.ingestion.paths import EXCEL_SOURCES
from graphrag.ingestion.pdf_extractors import BookParagraph, ExtractionResult
from graphrag.ingestion.pdf_graph_linker import ensure_reagent_catalog_nodes, link_pdf_chunks_to_graph
from graphrag.models import Chunk, GraphRAGResult, RetrievedChunk
from graphrag.service import GraphRAGQueryService
from graphrag.vector_factory import create_vector_store

KGMK_CLOSED_PNT_NI = "lossform_кгмк_+71_closed_pnt_cp_ni"
DEFAULT_K = 12


@dataclass(frozen=True)
class EvalQuery:
    question: str
    relevance_keywords: tuple[str, ...]
    bucket_id: str | None = None
    factory: str | None = None


BENCHMARK_QUERIES: tuple[EvalQuery, ...] = (
    EvalQuery(
        "доизмельчение закрытого пентландита МШР",
        ("мшр", "измельч", "пентландит", "раскрыт"),
        bucket_id=KGMK_CLOSED_PNT_NI,
        factory="КГМК",
    ),
    EvalQuery(
        "флотация шламов класс -10",
        ("флотац", "шлам", "тонк"),
    ),
    EvalQuery(
        "активация миллерита сульфидом",
        ("миллерит", "сульфид", "активац"),
    ),
    EvalQuery(
        "раскрытие сростков пентландита",
        ("раскрыт", "сростк", "пентландит"),
    ),
    EvalQuery(
        "гидроциклон классификация пульпы",
        ("гидроциклон", "классиф", "циклон"),
    ),
    EvalQuery(
        "собиратель ПДН флотация никеля",
        ("пдн", "собирател", "флотац", "никел"),
    ),
)


@dataclass
class QueryMetrics:
    question: str
    book_hits: int
    relevant_book_hits: int
    recall_at_k: float
    precision_at_k: float
    mrr: float
    ndcg_at_k: float
    first_relevant_rank: int | None
    graph_book_hits: int = 0
    vector_book_hits: int = 0


@dataclass
class ModeMetrics:
    mode: str
    granularity: str
    k: int
    suite: str
    queries: list[QueryMetrics] = field(default_factory=list)

    @property
    def mean_recall(self) -> float:
        return _mean(self.queries, "recall_at_k")

    @property
    def mean_precision(self) -> float:
        return _mean(self.queries, "precision_at_k")

    @property
    def mean_mrr(self) -> float:
        return _mean(self.queries, "mrr")

    @property
    def mean_ndcg(self) -> float:
        return _mean(self.queries, "ndcg_at_k")

    @property
    def mean_book_hits(self) -> float:
        return _mean(self.queries, "book_hits")

    @property
    def mean_relevant_book_hits(self) -> float:
        return _mean(self.queries, "relevant_book_hits")

    @property
    def mean_graph_book_hits(self) -> float:
        return _mean(self.queries, "graph_book_hits")


@dataclass
class GranularityBenchmark:
    granularity: str
    bucket_rag: ModeMetrics
    bucket_graphrag: ModeMetrics
    literature_rag: ModeMetrics
    literature_full_rag: ModeMetrics
    bucket_graph_lift_recall: float


def _mean(rows: list[QueryMetrics], attr: str) -> float:
    if not rows:
        return 0.0

    return round(statistics.mean(getattr(row, attr) for row in rows), 3)


def is_book_chunk(chunk: RetrievedChunk | Chunk) -> bool:
    chunk_id = chunk.chunk_id if hasattr(chunk, "chunk_id") else ""

    return chunk_id.startswith("book_")


def is_relevant_book(chunk: RetrievedChunk | Chunk, query: EvalQuery) -> bool:
    if not is_book_chunk(chunk):
        return False

    text = chunk.text.lower()

    return any(keyword in text for keyword in query.relevance_keywords)


def score_result(result: GraphRAGResult, query: EvalQuery, *, k: int) -> QueryMetrics:
    top = result.chunks[:k]
    relevances = [1 if is_relevant_book(chunk, query) else 0 for chunk in top]
    book_hits = sum(1 for chunk in top if is_book_chunk(chunk))
    relevant_hits = sum(relevances)
    first_rank = next((index + 1 for index, rel in enumerate(relevances) if rel), None)

    graph_book = sum(
        1
        for chunk in top
        if is_book_chunk(chunk) and "graph" in chunk.retrieval_channel
    )
    vector_book = sum(
        1
        for chunk in top
        if is_book_chunk(chunk) and (
            "hybrid" in chunk.retrieval_channel
            or "dense" in chunk.retrieval_channel
            or "bm25" in chunk.retrieval_channel
        )
    )

    return QueryMetrics(
        question=query.question,
        book_hits=book_hits,
        relevant_book_hits=relevant_hits,
        recall_at_k=1.0 if relevant_hits > 0 else 0.0,
        precision_at_k=round(relevant_hits / max(book_hits, 1), 3) if book_hits else 0.0,
        mrr=round(1.0 / first_rank, 3) if first_rank else 0.0,
        ndcg_at_k=round(_ndcg(relevances), 3),
        first_relevant_rank=first_rank,
        graph_book_hits=graph_book,
        vector_book_hits=vector_book,
    )


def _ndcg(relevances: list[int]) -> float:
    if not relevances or not any(relevances):
        return 0.0

    dcg = sum(rel / math.log2(index + 2) for index, rel in enumerate(relevances))
    ideal = sorted(relevances, reverse=True)
    idcg = sum(rel / math.log2(index + 2) for index, rel in enumerate(ideal))

    return dcg / idcg if idcg else 0.0


def paragraphs_to_chunks(paragraphs: list[BookParagraph], book_meta: dict) -> list[Chunk]:
    path = Path(book_meta["source"])
    chunks: list[Chunk] = []

    for paragraph in paragraphs:
        meta = {
            **book_meta,
            "chunk_type": "book_text",
            "page": paragraph.page,
            "paragraph_index": paragraph.paragraph_index,
            "granularity": paragraph.granularity,
            "element_type": paragraph.element_type,
            "chunk_id": (
                f"book_{book_meta['doc_id']}_{paragraph.granularity}"
                f"_p{paragraph.page}_i{paragraph.paragraph_index}"
            ),
        }

        if paragraph.section:
            meta["section"] = paragraph.section

        chunk = _chunk_from_parts(path, meta, paragraph.text)

        if chunk is not None:
            chunks.append(chunk)

    return chunks


def load_base_kb() -> tuple[list, list, list[Chunk]]:
    nodes = list(build_catalog_nodes())
    edges: list = []
    chunks: list[Chunk] = []

    for factory, relative_path in EXCEL_SOURCES:
        from graphrag.ingestion.paths import DEFAULT_DATA_ROOT

        excel_path = DEFAULT_DATA_ROOT / relative_path

        if not excel_path.is_file():
            continue

        parsed = parse_excel_file(excel_path, factory)
        nodes.extend(parsed.nodes)
        edges.extend(parsed.edges)
        chunks.extend(parsed.chunks)

    nodes_by_id = {node.node_id: node for node in nodes}
    ensure_reagent_catalog_nodes(nodes_by_id)
    nodes = list(nodes_by_id.values())
    nodes, edges = enrich_graph(nodes, edges, chunks)
    nodes_by_id = {node.node_id: node for node in nodes}
    edges.extend(build_factory_equipment_edges(nodes_by_id))
    nodes = list(nodes_by_id.values())
    chunks.extend(build_constraint_chunks())

    return nodes, edges, chunks


def build_index(
    book_extractions: list[ExtractionResult],
    granularity: str,
) -> tuple[NetworkXGraphStore, GraphRAGQueryService]:
    nodes, edges, base_chunks = load_base_kb()
    book_chunks: list[Chunk] = []

    for extraction in book_extractions:
        paragraphs = rechunk_paragraphs(extraction.paragraphs, granularity)
        book_meta = {
            "doc_id": _slugify(extraction.source_pdf.stem),
            "title": extraction.source_pdf.stem,
            "source": extraction.source_pdf.name,
            "original_pdf": extraction.source_pdf.name,
            "extractor": extraction.backend,
            "granularity": granularity,
        }
        book_chunks.extend(paragraphs_to_chunks(paragraphs, book_meta))

    graph = NetworkXGraphStore()
    vectors = create_vector_store(VECTOR_BACKEND_MEMORY)
    nodes_by_id = {node.node_id: node for node in nodes}
    linked = link_pdf_chunks_to_graph(base_chunks + book_chunks, nodes_by_id)
    final_chunks = linked.chunks
    final_edges = edges + linked.edges

    for node in nodes_by_id.values():
        graph.add_node(node)

    seen = set()

    for edge in final_edges:
        key = (edge.source, edge.relation, edge.target)

        if key in seen:
            continue

        seen.add(key)
        graph.add_edge(edge)

    vectors.add_many(final_chunks)

    return graph, GraphRAGQueryService(graph, vectors)


def _book_hybrid_search(service: GraphRAGQueryService, question: str, *, k: int) -> list[RetrievedChunk]:
    """RAG on literature only — hybrid over book_text chunks."""
    vectors = service._vectors
    search_kwargs = {"k": k, "chunk_type": "book_text"}

    if hasattr(vectors, "hybrid_search"):
        hits = vectors.hybrid_search(question, **search_kwargs)
    else:
        hits = vectors.dense_search(question, **search_kwargs)

    chunks: list[RetrievedChunk] = []

    for chunk_id, score in hits:
        chunk = vectors.get(chunk_id)

        if chunk is None:
            continue

        chunks.append(
            RetrievedChunk(
                chunk_id=chunk_id,
                text=chunk.text,
                score=score,
                source=chunk.source,
                graph_node_ids=chunk.graph_node_ids,
                retrieval_channel="hybrid",
            )
        )

    return chunks


def run_bucket_mode(
    service: GraphRAGQueryService,
    *,
    mode: str,
    granularity: str,
    k: int,
) -> ModeMetrics:
    use_graph = mode == "graphrag"
    metrics = ModeMetrics(mode=mode, granularity=granularity, k=k, suite="bucket")
    bucket_queries = [query for query in BENCHMARK_QUERIES if query.bucket_id]

    for query in bucket_queries:
        result = service.query(
            query.question,
            bucket_id=query.bucket_id,
            factory=query.factory,
            k_out=k,
            use_graph=use_graph,
        )
        metrics.queries.append(score_result(result, query, k=k))

    return metrics


def run_literature_mode(
    service: GraphRAGQueryService,
    *,
    mode: str,
    granularity: str,
    k: int,
) -> ModeMetrics:
    metrics = ModeMetrics(mode=mode, granularity=granularity, k=k, suite="literature")
    literature_queries = [query for query in BENCHMARK_QUERIES if not query.bucket_id]

    for query in literature_queries:
        if mode == "rag":
            chunks = _book_hybrid_search(service, query.question, k=k)
            result = GraphRAGResult(
                question=query.question,
                bucket_id=None,
                graph_paths=[],
                node_ids=[],
                chunks=chunks,
            )
        elif mode == "full_rag":
            result = service.query(query.question, bucket_id=None, k_out=k, use_graph=False)
        else:
            result = service.query(query.question, bucket_id=None, k_out=k, use_graph=True)

        metrics.queries.append(score_result(result, query, k=k))

    return metrics


def run_mode(
    service: GraphRAGQueryService,
    *,
    mode: str,
    granularity: str,
    suite: str,
    k: int = DEFAULT_K,
) -> ModeMetrics:
    if suite == "bucket":
        return run_bucket_mode(service, mode=mode, granularity=granularity, k=k)

    return run_literature_mode(service, mode=mode, granularity=granularity, k=k)


def benchmark_granularity(
    book_extractions: list[ExtractionResult],
    granularity: str,
    *,
    k: int = DEFAULT_K,
) -> GranularityBenchmark:
    _, service = build_index(book_extractions, granularity)

    bucket_rag = run_mode(service, mode="rag", granularity=granularity, suite="bucket", k=k)
    bucket_graphrag = run_mode(service, mode="graphrag", granularity=granularity, suite="bucket", k=k)
    literature_rag = run_mode(service, mode="rag", granularity=granularity, suite="literature", k=k)
    literature_full_rag = run_mode(
        service, mode="full_rag", granularity=granularity, suite="literature", k=k
    )

    return GranularityBenchmark(
        granularity=granularity,
        bucket_rag=bucket_rag,
        bucket_graphrag=bucket_graphrag,
        literature_rag=literature_rag,
        literature_full_rag=literature_full_rag,
        bucket_graph_lift_recall=round(
            bucket_graphrag.mean_recall - bucket_rag.mean_recall,
            3,
        ),
    )


def benchmark_all_granularities(
    book_extractions: list[ExtractionResult],
    *,
    k: int = DEFAULT_K,
) -> list[GranularityBenchmark]:
    return [
        benchmark_granularity(book_extractions, granularity, k=k)
        for granularity in ALL_GRANULARITIES
    ]


def report_to_dict(reports: list[GranularityBenchmark]) -> dict:
    rows = []

    for item in reports:
        rows.append(
            {
                "granularity": item.granularity,
                "bucket": {
                    "rag": {
                        "recall@k": item.bucket_rag.mean_recall,
                        "mrr": item.bucket_rag.mean_mrr,
                        "relevant_hits": item.bucket_rag.mean_relevant_book_hits,
                        "book_hits": item.bucket_rag.mean_book_hits,
                    },
                    "graphrag": {
                        "recall@k": item.bucket_graphrag.mean_recall,
                        "mrr": item.bucket_graphrag.mean_mrr,
                        "relevant_hits": item.bucket_graphrag.mean_relevant_book_hits,
                        "book_hits": item.bucket_graphrag.mean_book_hits,
                        "graph_book_hits": item.bucket_graphrag.mean_graph_book_hits,
                    },
                    "graph_lift_recall": item.bucket_graph_lift_recall,
                },
                "literature": {
                    "rag_book_only": {
                        "recall@k": item.literature_rag.mean_recall,
                        "mrr": item.literature_rag.mean_mrr,
                        "ndcg@k": item.literature_rag.mean_ndcg,
                        "relevant_hits": item.literature_rag.mean_relevant_book_hits,
                    },
                    "full_corpus_rag": {
                        "recall@k": item.literature_full_rag.mean_recall,
                        "book_hits": item.literature_full_rag.mean_book_hits,
                        "relevant_hits": item.literature_full_rag.mean_relevant_book_hits,
                    },
                },
            }
        )

    best_lit_rag = max(reports, key=lambda item: item.literature_rag.mean_recall)
    best_bucket_gr = max(reports, key=lambda item: item.bucket_graphrag.mean_relevant_book_hits)

    return {
        "k": DEFAULT_K,
        "queries": [asdict(query) for query in BENCHMARK_QUERIES],
        "results": rows,
        "best_literature_rag_granularity": best_lit_rag.granularity,
        "best_bucket_graphrag_granularity": best_bucket_gr.granularity,
    }
