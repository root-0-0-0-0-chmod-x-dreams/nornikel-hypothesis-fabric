"""GraphRAG query orchestrator."""

from __future__ import annotations

from typing import Any

from graphrag.budget_inference import resolve_budget_tier
from graphrag.constants import (
    CHANNEL_BM25,
    CHANNEL_CONSTRAINT,
    CHANNEL_DENSE,
    CHANNEL_FUSED,
    CHANNEL_GRAPH,
    CHANNEL_HYBRID,
    DEFAULT_K_BM25,
    DEFAULT_K_DENSE,
    DEFAULT_K_GRAPH,
    DEFAULT_K_HYBRID,
    DEFAULT_K_OUT,
    DEFAULT_MAX_HOPS,
    FUSION_CANDIDATE_MULTIPLIER,
    INTERVENTION_RELATIONS,
    RRF_WEIGHT_BM25,
    RRF_WEIGHT_CONSTRAINT,
    RRF_WEIGHT_DENSE,
    RRF_WEIGHT_GRAPH,
    RRF_WEIGHT_GRAPH_REPEAT,
    RRF_WEIGHT_HYBRID,
)
from graphrag.fusion import (
    mmr_select,
    rerank_by_overlap,
    rerank_with_graph_overlap,
    weighted_rrf_fuse,
)
from graphrag.graph.base import GraphStoreProtocol
from graphrag.models import Chunk, GraphRAGResult, RetrievedChunk
from graphrag.ingestion.constraints import filter_nodes_by_factory_equipment
from graphrag.provenance.abc_evidence import build_abc_evidence_chain
from graphrag.provenance.citations import citation_from_chunk, highlight_overlap
from graphrag.retrieval_context import build_enriched_query
from graphrag.retrieval_nodes import expand_retrieval_nodes
from graphrag.vector_protocol import VectorStoreProtocol


class GraphRAGQueryService:
    def __init__(self, graph: GraphStoreProtocol, vectors: VectorStoreProtocol) -> None:
        self._graph = graph
        self._vectors = vectors

    def query(
        self,
        question: str,
        *,
        bucket_id: str | None = None,
        factory: str | None = None,
        retrieval_query: str | None = None,
        retrieval_queries: list[str] | None = None,
        k_dense: int = DEFAULT_K_DENSE,
        k_bm25: int = DEFAULT_K_BM25,
        max_hops: int = DEFAULT_MAX_HOPS,
        k_out: int = DEFAULT_K_OUT,
        include_external: bool = False,
        budget_tier: str | None = None,
        use_graph: bool = True,
    ) -> GraphRAGResult:
        graph_paths, node_ids = self._traverse_graph(bucket_id, max_hops) if use_graph else ([], [])
        retrieval_nodes = (
            expand_retrieval_nodes(self._graph, bucket_id, node_ids) if use_graph else []
        )
        factory_name = factory or self._factory_from_bucket(bucket_id)
        retrieval_nodes = filter_nodes_by_factory_equipment(retrieval_nodes, factory_name)
        resolved_budget, _budget_inference = resolve_budget_tier(
            self._graph,
            bucket_id,
            factory=factory_name,
            budget_tier=budget_tier,
        )
        budget_tier = resolved_budget
        active_queries = self._resolve_retrieval_queries(
            question,
            retrieval_query=retrieval_query,
            retrieval_queries=retrieval_queries,
            bucket_id=bucket_id,
            retrieval_nodes=retrieval_nodes,
            factory=factory_name,
            budget_tier=budget_tier,
        )
        enriched_query = " | ".join(active_queries)
        external_filter = None if include_external else False

        graph_hits = (
            self._vectors.fetch_by_graph_nodes(
                retrieval_nodes,
                factory=factory_name,
                k=DEFAULT_K_GRAPH,
            )
            if use_graph and retrieval_nodes
            else []
        )
        channel_map: dict[str, set[str]] = {}
        weighted_rankings: list[tuple[list[str], float]] = []
        hypothesis_probe: list[dict[str, Any]] = []

        if use_graph and graph_hits:
            graph_ranking = [chunk_id for chunk_id, _ in graph_hits]
            weighted_rankings.append((graph_ranking, RRF_WEIGHT_GRAPH))

            if bucket_id:
                weighted_rankings.append(
                    (graph_ranking, RRF_WEIGHT_GRAPH_REPEAT),
                )

            self._tag_graph_channels(channel_map, graph_ranking)

        for index, query_text in enumerate(active_queries):
            vector_rankings, partial_map, probe_hits = self._vector_rankings(
                question=query_text,
                factory=factory_name,
                external=external_filter,
                budget_tier=budget_tier,
                k_dense=k_dense,
                k_bm25=k_bm25,
                include_constraints=index == 0,
            )
            weighted_rankings.extend(vector_rankings)
            self._merge_channel_map(channel_map, partial_map)

            if len(active_queries) > 1 and probe_hits:
                hypothesis_probe.append(
                    {
                        "index": index,
                        "retrieval_query": query_text,
                        "top_chunks": [
                            {"chunk_id": chunk_id, "score": score}
                            for chunk_id, score in probe_hits[:5]
                        ],
                    }
                )

        fused = weighted_rrf_fuse(
            weighted_rankings,
            top_n=k_out * FUSION_CANDIDATE_MULTIPLIER,
        )
        chunks_map = self._chunks_map(fused)
        reranked = rerank_with_graph_overlap(
            fused,
            chunks_map,
            retrieval_nodes,
        ) if use_graph else rerank_by_overlap(
            enriched_query,
            fused,
            self._vector_texts(chunks_map),
            top_n=k_out * FUSION_CANDIDATE_MULTIPLIER,
        )
        if use_graph:
            reranked = rerank_by_overlap(
                enriched_query,
                reranked,
                self._vector_texts(chunks_map),
                top_n=k_out * FUSION_CANDIDATE_MULTIPLIER,
            )
        reranked = mmr_select(
            reranked,
            self._vector_texts(chunks_map),
            top_n=k_out,
        )

        if bucket_id:
            reranked = self._pin_bucket_chunk(bucket_id, reranked)

        chunks = self._build_retrieved_chunks(reranked, channel_map, enriched_query)
        abc_chain = (
            build_abc_evidence_chain(
                self._graph,
                self._vectors,
                bucket_id,
                graph_paths,
                question=question,
            )
            if use_graph
            else None
        )

        return GraphRAGResult(
            question=question,
            bucket_id=bucket_id,
            graph_paths=graph_paths,
            node_ids=retrieval_nodes,
            chunks=chunks,
            channel_hits=self._channel_hits(channel_map),
            expanded_query=enriched_query,
            abc_evidence=abc_chain.to_dict() if abc_chain else None,
            hypothesis_probe=hypothesis_probe,
        )

    def _vector_rankings(
        self,
        *,
        question: str,
        factory: str | None,
        external: bool | None,
        budget_tier: str | None,
        k_dense: int,
        k_bm25: int,
        include_constraints: bool = True,
    ) -> tuple[list[tuple[list[str], float]], dict[str, set[str]], list[tuple[str, float]]]:
        channel_map: dict[str, set[str]] = {}
        weighted: list[tuple[list[str], float]] = []
        probe_hits: list[tuple[str, float]] = []

        if include_constraints and hasattr(self._vectors, "fetch_by_chunk_types"):
            constraint_hits = self._vectors.fetch_by_chunk_types(
                (
                    "constraint_regulation",
                    "constraint_example",
                    "constraint_budget",
                ),
                factory=factory,
                budget_tier=budget_tier,
                k=20,
            )
            constraint_ranking = [chunk_id for chunk_id, _ in constraint_hits]

            if constraint_ranking:
                weighted.append((constraint_ranking, RRF_WEIGHT_CONSTRAINT))
                self._mark_channel(channel_map, constraint_ranking, CHANNEL_CONSTRAINT)

        if hasattr(self._vectors, "hybrid_search"):
            hybrid_hits = self._vectors.hybrid_search(
                question,
                k=DEFAULT_K_HYBRID,
                factory=factory,
                external=external,
            )
            probe_hits = hybrid_hits
            hybrid_ranking = [chunk_id for chunk_id, _ in hybrid_hits]

            if hybrid_ranking:
                weighted.append((hybrid_ranking, RRF_WEIGHT_HYBRID))
                self._mark_channel(channel_map, hybrid_ranking, CHANNEL_HYBRID)

            return weighted, channel_map, probe_hits

        dense_hits = self._vectors.dense_search(
            question,
            k=k_dense,
            factory=factory,
            external=external,
        )
        bm25_hits = self._vectors.bm25_search(
            question,
            k=k_bm25,
            factory=factory,
            external=external,
        )
        dense_ranking = [chunk_id for chunk_id, _ in dense_hits]
        bm25_ranking = [chunk_id for chunk_id, _ in bm25_hits]

        if dense_ranking:
            weighted.append((dense_ranking, RRF_WEIGHT_DENSE))
            self._mark_channel(channel_map, dense_ranking, CHANNEL_DENSE)

        if bm25_ranking:
            weighted.append((bm25_ranking, RRF_WEIGHT_BM25))
            self._mark_channel(channel_map, bm25_ranking, CHANNEL_BM25)

        probe_hits = dense_hits[:5] if dense_hits else bm25_hits[:5]

        return weighted, channel_map, probe_hits

    def _resolve_retrieval_queries(
        self,
        question: str,
        *,
        retrieval_query: str | None,
        retrieval_queries: list[str] | None,
        bucket_id: str | None,
        retrieval_nodes: list[str],
        factory: str | None,
        budget_tier: str | None,
    ) -> list[str]:
        explicit = [
            query.strip()
            for query in (retrieval_queries or [])
            if query and str(query).strip()
        ]

        if retrieval_query and retrieval_query.strip():
            explicit.insert(0, retrieval_query.strip())

        if explicit:
            return list(dict.fromkeys(explicit))

        enriched = build_enriched_query(
            question,
            self._graph,
            bucket_id,
            retrieval_nodes,
            factory=factory,
            budget_tier=budget_tier,
        )

        return [enriched]

    @staticmethod
    def _merge_channel_map(
        target: dict[str, set[str]],
        partial: dict[str, set[str]],
    ) -> None:
        for chunk_id, channels in partial.items():
            target.setdefault(chunk_id, set()).update(channels)

    def probe_hypothesis_support(
        self,
        retrieval_queries: list[str],
        *,
        factory: str | None,
        include_external: bool = False,
        k_probe: int = 5,
    ) -> list[dict[str, Any]]:
        """Lightweight per-hypothesis top chunks for LLM hypothesis drafting."""
        external_filter = None if include_external else False
        support: list[dict[str, Any]] = []

        for index, query_text in enumerate(retrieval_queries):
            hits: list[tuple[str, float]] = []

            if hasattr(self._vectors, "hybrid_search"):
                hits = self._vectors.hybrid_search(
                    query_text,
                    k=k_probe,
                    factory=factory,
                    external=external_filter,
                )
            else:
                dense = self._vectors.dense_search(
                    query_text,
                    k=k_probe,
                    factory=factory,
                    external=external_filter,
                )
                hits = dense

            support.append(
                {
                    "index": index,
                    "retrieval_query": query_text,
                    "top_chunks": [
                        {"chunk_id": chunk_id, "score": score}
                        for chunk_id, score in hits
                    ],
                }
            )

        return support

    def _traverse_graph(
        self,
        bucket_id: str | None,
        max_hops: int,
    ) -> tuple[list, list[str]]:
        if not bucket_id or not self._graph.has_node(bucket_id):
            return [], []

        return self._graph.traverse(
            bucket_id,
            max_hops=max_hops,
            relations=INTERVENTION_RELATIONS,
        )

    def _factory_from_bucket(self, bucket_id: str | None) -> str | None:
        if not bucket_id or not self._graph.has_node(bucket_id):
            return None

        attrs = self._graph.get_node_attributes(bucket_id) or {}
        factory = attrs.get("factory")

        return str(factory) if factory else None

    def _pin_bucket_chunk(
        self,
        bucket_id: str,
        reranked: list[tuple[str, float]],
    ) -> list[tuple[str, float]]:
        """Always surface the target LossForm excel row for hypothesis grounding."""
        chunk_id = f"excel_{bucket_id}"

        if self._vectors.get(chunk_id) is None:
            return reranked

        rest = [(cid, score) for cid, score in reranked if cid != chunk_id]

        return [(chunk_id, 1.0), *rest]

    @staticmethod
    def _mark_channel(
        channel_map: dict[str, set[str]],
        ranking: list[str],
        channel: str,
    ) -> None:
        for chunk_id in ranking:
            channel_map.setdefault(chunk_id, set()).add(channel)

    @staticmethod
    def _tag_graph_channels(
        channel_map: dict[str, set[str]],
        graph_ranking: list[str],
    ) -> None:
        for chunk_id in graph_ranking:
            channel_map.setdefault(chunk_id, set()).add(CHANNEL_GRAPH)

    @staticmethod
    def _channel_hits(channel_map: dict[str, set[str]]) -> dict[str, int]:
        hits = {
            CHANNEL_GRAPH: 0,
            CHANNEL_DENSE: 0,
            CHANNEL_BM25: 0,
            CHANNEL_HYBRID: 0,
            CHANNEL_CONSTRAINT: 0,
        }

        for channels in channel_map.values():
            for channel in channels:
                if channel in hits:
                    hits[channel] += 1

        return hits

    def _chunks_map(
        self,
        candidates: list[tuple[str, float]],
    ) -> dict[str, Chunk]:
        chunks: dict[str, Chunk] = {}

        for chunk_id, _score in candidates:
            chunk = self._vectors.get(chunk_id)

            if chunk is not None:
                chunks[chunk_id] = chunk

        return chunks

    def _vector_texts(self, chunks: dict[str, Chunk]) -> dict[str, str]:
        return {chunk_id: chunk.full_text_for_embed() for chunk_id, chunk in chunks.items()}

    def _build_retrieved_chunks(
        self,
        reranked: list[tuple[str, float]],
        channel_map: dict[str, set[str]],
        enriched_query: str,
    ) -> list[RetrievedChunk]:
        chunks: list[RetrievedChunk] = []

        for chunk_id, score in reranked:
            chunk = self._vectors.get(chunk_id)

            if chunk is None:
                continue

            channels = channel_map.get(chunk_id, set())
            retrieval_channel = (
                "+".join(sorted(channels)) if channels else CHANNEL_FUSED
            )
            highlight = highlight_overlap(enriched_query, chunk.text)
            citation = citation_from_chunk(chunk, highlight=highlight)

            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    text=chunk.text,
                    score=score,
                    source=chunk.source,
                    graph_node_ids=chunk.graph_node_ids,
                    retrieval_channel=retrieval_channel,
                    citation=citation.to_dict(),
                )
            )

        return chunks
