"""RRF fusion, graph-aware rerank, and MMR diversity."""

from __future__ import annotations

from collections import defaultdict

from graphrag.constants import (
    GRAPH_OVERLAP_RERANK_WEIGHT,
    MMR_LAMBDA,
    RERANK_OVERLAP_WEIGHT,
    RRF_K,
)
from graphrag.embeddings import tokenize
from graphrag.models import Chunk


def rrf_fuse(
    rankings: list[list[str]],
    *,
    rrf_k: int = RRF_K,
    top_n: int | None = None,
) -> list[tuple[str, float]]:
    return weighted_rrf_fuse(
        [(ranking, 1.0) for ranking in rankings],
        rrf_k=rrf_k,
        top_n=top_n,
    )


def weighted_rrf_fuse(
    weighted_rankings: list[tuple[list[str], float]],
    *,
    rrf_k: int = RRF_K,
    top_n: int | None = None,
) -> list[tuple[str, float]]:
    scores: dict[str, float] = defaultdict(float)

    for ranking, weight in weighted_rankings:
        if not ranking or weight <= 0:
            continue

        for rank, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] += weight / (rrf_k + rank)

    fused = sorted(scores.items(), key=lambda item: -item[1])

    if top_n is not None:
        return fused[:top_n]

    return fused


def rerank_by_overlap(
    query: str,
    candidates: list[tuple[str, float]],
    texts: dict[str, str],
    top_n: int,
) -> list[tuple[str, float]]:
    query_tokens = set(tokenize(query))

    if not query_tokens:
        return candidates[:top_n]

    rescored: list[tuple[str, float]] = []

    for chunk_id, rrf_score in candidates:
        doc_tokens = set(tokenize(texts.get(chunk_id, "")))
        overlap = len(query_tokens & doc_tokens) / max(len(query_tokens), 1)
        rescored.append((chunk_id, rrf_score + RERANK_OVERLAP_WEIGHT * overlap))

    rescored.sort(key=lambda item: -item[1])

    return rescored[:top_n]


def rerank_with_graph_overlap(
    candidates: list[tuple[str, float]],
    chunks: dict[str, Chunk],
    retrieval_nodes: list[str],
    *,
    weight: float = GRAPH_OVERLAP_RERANK_WEIGHT,
) -> list[tuple[str, float]]:
    if not retrieval_nodes:
        return candidates

    node_set = set(retrieval_nodes)
    rescored: list[tuple[str, float]] = []

    for chunk_id, score in candidates:
        chunk = chunks.get(chunk_id)
        overlap = 0.0

        if chunk is not None and chunk.graph_node_ids:
            overlap = len(node_set & set(chunk.graph_node_ids)) / max(
                len(node_set),
                1,
            )

        rescored.append((chunk_id, score + weight * overlap))

    rescored.sort(key=lambda item: -item[1])

    return rescored


def mmr_select(
    candidates: list[tuple[str, float]],
    texts: dict[str, str],
    *,
    top_n: int,
    lambda_mult: float = MMR_LAMBDA,
) -> list[tuple[str, float]]:
    """Token-Jaccard MMR to diversify near-duplicate PDF chunks."""
    if len(candidates) <= top_n:
        return candidates[:top_n]

    token_cache = {cid: set(tokenize(texts.get(cid, ""))) for cid, _ in candidates}
    selected: list[tuple[str, float]] = []
    remaining = list(candidates)

    while remaining and len(selected) < top_n:
        best_index = 0
        best_score = float("-inf")

        for index, (chunk_id, relevance) in enumerate(remaining):
            if not selected:
                mmr_score = relevance
            else:
                max_sim = max(
                    _jaccard(token_cache[chunk_id], token_cache[picked_id])
                    for picked_id, _ in selected
                )
                mmr_score = lambda_mult * relevance - (1.0 - lambda_mult) * max_sim

            if mmr_score > best_score:
                best_score = mmr_score
                best_index = index

        selected.append(remaining.pop(best_index))

    return selected


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0

    union = left | right

    if not union:
        return 0.0

    return len(left & right) / len(union)
