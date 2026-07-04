"""In-memory vector store: dense + BM25 + graph_node filter."""

from __future__ import annotations

import numpy as np
from rank_bm25 import BM25Okapi

from graphrag.constants import DEFAULT_K_BM25, DEFAULT_K_DENSE, DEFAULT_K_HYBRID, RETRIEVAL_NODE_PREFIXES
from graphrag.embeddings import EmbeddingProvider, TfidfEmbeddingProvider, tokenize
from graphrag.fusion import weighted_rrf_fuse
from graphrag.models import Chunk


class VectorStore:
    def __init__(self, embedder: EmbeddingProvider | None = None) -> None:
        self._chunks: dict[str, Chunk] = {}
        self._embedder = embedder or TfidfEmbeddingProvider()
        self._embeddings: np.ndarray | None = None
        self._chunk_ids: list[str] = []
        self._bm25: BM25Okapi | None = None

    @property
    def size(self) -> int:
        return len(self._chunks)

    def add(self, chunk: Chunk) -> None:
        self._chunks[chunk.chunk_id] = chunk
        self._invalidate_indexes()

    def add_many(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return

        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk

        self._chunk_ids = list(self._chunks.keys())
        texts = [self._chunks[cid].full_text_for_embed() for cid in self._chunk_ids]
        tokenized = [tokenize(text) for text in texts]
        self._bm25 = BM25Okapi(tokenized)

        if isinstance(self._embedder, TfidfEmbeddingProvider):
            self._embedder.fit_corpus(texts)

        self._embeddings = self._embedder.embed(texts)

    def upsert_many(self, chunks: list[Chunk]) -> None:
        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk

        self._invalidate_indexes()
        self._ensure_indexes()

    def get(self, chunk_id: str) -> Chunk | None:
        return self._chunks.get(chunk_id)

    def _invalidate_indexes(self) -> None:
        self._embeddings = None
        self._bm25 = None

    def _ensure_indexes(self) -> None:
        if self._embeddings is not None and self._bm25 is not None:
            return

        if not self._chunks:
            self._chunk_ids = []
            self._embeddings = np.zeros((0, 1), dtype=np.float32)
            self._bm25 = BM25Okapi([["empty"]])

            return

        self._chunk_ids = list(self._chunks.keys())
        texts = [self._chunks[cid].full_text_for_embed() for cid in self._chunk_ids]
        tokenized = [tokenize(text) for text in texts]
        self._bm25 = BM25Okapi(tokenized)

        if isinstance(self._embedder, TfidfEmbeddingProvider):
            self._embedder.fit_corpus(texts)

        self._embeddings = self._embedder.embed(texts)

    def dense_search(
        self,
        query: str,
        *,
        k: int = DEFAULT_K_DENSE,
        factory: str | None = None,
        external: bool | None = None,
        chunk_type: str | None = None,
    ) -> list[tuple[str, float]]:
        self._ensure_indexes()

        if not self._chunk_ids or self._embeddings is None:
            return []

        query_vector = self._embedder.embed([query])[0]
        scores = self._embeddings @ query_vector

        return self._rank_with_filters(
            scores=scores,
            k=k,
            factory=factory,
            external=external,
            chunk_type=chunk_type,
        )

    def bm25_search(
        self,
        query: str,
        *,
        k: int = DEFAULT_K_BM25,
        factory: str | None = None,
        external: bool | None = None,
        chunk_type: str | None = None,
    ) -> list[tuple[str, float]]:
        self._ensure_indexes()

        if not self._chunk_ids or self._bm25 is None:
            return []

        query_tokens = tokenize(query)

        if not query_tokens:
            return []

        raw_scores = self._bm25.get_scores(query_tokens)

        return self._rank_with_filters(
            scores=raw_scores,
            k=k,
            factory=factory,
            external=external,
            chunk_type=chunk_type,
        )

    def hybrid_search(
        self,
        query: str,
        *,
        k: int = DEFAULT_K_HYBRID,
        factory: str | None = None,
        external: bool | None = None,
        chunk_type: str | None = None,
    ) -> list[tuple[str, float]]:
        dense = self.dense_search(
            query, k=k, factory=factory, external=external, chunk_type=chunk_type
        )
        bm25 = self.bm25_search(
            query, k=k, factory=factory, external=external, chunk_type=chunk_type
        )

        return weighted_rrf_fuse(
            [
                ([chunk_id for chunk_id, _ in dense], 1.0),
                ([chunk_id for chunk_id, _ in bm25], 1.0),
            ],
            top_n=k,
        )

    def fetch_by_graph_nodes(
        self,
        node_ids: list[str],
        *,
        factory: str | None = None,
        k: int | None = None,
    ) -> list[tuple[str, float]]:
        if not node_ids:
            return []

        node_set = {
            node_id
            for node_id in node_ids
            if node_id.startswith(RETRIEVAL_NODE_PREFIXES)
        }

        if not node_set:
            return []

        hits: list[tuple[str, float]] = []

        for chunk_id, chunk in self._chunks.items():
            if not self._passes_graph_factory_filter(chunk, factory):
                continue

            overlap = node_set & set(chunk.graph_node_ids)

            if overlap:
                hits.append((chunk_id, float(len(overlap))))

        hits.sort(key=lambda item: -item[1])

        if k is not None:
            return hits[:k]

        return hits

    def fetch_by_chunk_types(
        self,
        chunk_types: tuple[str, ...] | list[str],
        *,
        factory: str | None = None,
        budget_tier: str | None = None,
        k: int = 20,
    ) -> list[tuple[str, float]]:
        allowed = set(chunk_types)
        hits: list[tuple[str, float]] = []

        for chunk_id, chunk in self._chunks.items():
            if chunk.chunk_type not in allowed:
                continue

            if chunk.chunk_type == "constraint_budget":
                if budget_tier and chunk.metadata.get("budget_tier") != budget_tier:
                    continue
            elif factory and chunk.factory and chunk.factory != factory:
                continue

            if (
                chunk.chunk_type == "constraint_example"
                and budget_tier
                and chunk.metadata.get("budget_tier")
                and chunk.metadata.get("budget_tier") != budget_tier
            ):
                continue

            priority = 2.0 if chunk.chunk_type == "constraint_regulation" else 1.0
            hits.append((chunk_id, priority))

        hits.sort(key=lambda item: -item[1])

        return hits[:k]

    def texts_map(self) -> dict[str, str]:
        return {chunk_id: chunk.text for chunk_id, chunk in self._chunks.items()}

    def _rank_with_filters(
        self,
        *,
        scores: np.ndarray,
        k: int,
        factory: str | None,
        external: bool | None,
        chunk_type: str | None = None,
    ) -> list[tuple[str, float]]:
        ranked: list[tuple[str, float]] = []

        for index, chunk_id in enumerate(self._chunk_ids):
            chunk = self._chunks[chunk_id]

            if chunk_type is not None and chunk.chunk_type != chunk_type:
                continue

            if not self._passes_factory_filter(chunk, factory):
                continue

            if external is not None and chunk.external != external:
                continue

            ranked.append((chunk_id, float(scores[index])))

        ranked.sort(key=lambda item: -item[1])

        return ranked[:k]

    @staticmethod
    def _passes_factory_filter(chunk: Chunk, factory: str | None) -> bool:
        if factory and chunk.factory and chunk.factory != factory:
            return False

        return True

    @staticmethod
    def _passes_graph_factory_filter(chunk: Chunk, factory: str | None) -> bool:
        if not factory:
            return True

        if chunk.factory == factory:
            return True

        return chunk.chunk_type in {
            "pdf_text",
            "book_text",
            "external_text",
            "scheme_caption",
            "constraint_regulation",
            "constraint_example",
        }
