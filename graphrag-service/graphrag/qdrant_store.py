"""Qdrant vector store: dense + BM25 sparse vectors in one collection."""

from __future__ import annotations

import uuid
from typing import Any

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    Fusion,
    FusionQuery,
    MatchValue,
    Modifier,
    PointStruct,
    Prefetch,
    SparseVectorParams,
    VectorParams,
)

from graphrag.config import QdrantConfig
from graphrag.constants import (
    DEFAULT_K_BM25,
    DEFAULT_K_DENSE,
    DEFAULT_K_HYBRID,
    QDRANT_DENSE_VECTOR_NAME,
    QDRANT_SPARSE_VECTOR_NAME,
    RETRIEVAL_NODE_PREFIXES,
)
from graphrag.embeddings import EmbeddingProvider, TfidfEmbeddingProvider
from graphrag.models import Chunk
from graphrag.sparse_embeddings import Bm25SparseEncoder

_POINT_NAMESPACE = uuid.UUID("a3f2c8e1-4b9d-4e2a-9f6c-1d8e7b0a4c2f")


def _point_id(chunk_id: str) -> uuid.UUID:
    return uuid.uuid5(_POINT_NAMESPACE, chunk_id)


def _create_qdrant_client(url: str) -> QdrantClient:
    if url == ":memory:":
        return QdrantClient(location=":memory:")

    return QdrantClient(url=url)


class QdrantVectorStore:
    def __init__(
        self,
        config: QdrantConfig | None = None,
        embedder: EmbeddingProvider | None = None,
        sparse_encoder: Bm25SparseEncoder | None = None,
    ) -> None:
        self._config = config or QdrantConfig.from_env()
        self._client = _create_qdrant_client(self._config.url)
        self._collection = self._config.collection
        self._embedder = embedder or TfidfEmbeddingProvider()
        self._sparse = sparse_encoder or Bm25SparseEncoder()
        self._chunks: dict[str, Chunk] = {}
        self._vector_dim: int | None = None

    @property
    def size(self) -> int:
        return len(self._chunks)

    def add_many(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return

        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk

        chunk_ids = list(self._chunks.keys())
        texts = [self._chunks[cid].full_text_for_embed() for cid in chunk_ids]

        if isinstance(self._embedder, TfidfEmbeddingProvider):
            self._embedder.fit_corpus(texts)

        dense_vectors = self._embedder.embed(texts)
        sparse_vectors = self._sparse.encode_documents(texts)
        self._ensure_collection(int(dense_vectors.shape[1]))
        self._upsert_vectors(chunk_ids, dense_vectors, sparse_vectors)

    def upsert_many(self, chunks: list[Chunk]) -> None:
        """Incremental upsert without wiping the collection."""
        if not chunks:
            return

        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk

        chunk_ids = [chunk.chunk_id for chunk in chunks]
        texts = [chunk.full_text_for_embed() for chunk in chunks]

        if isinstance(self._embedder, TfidfEmbeddingProvider):
            if not self._embedder._fitted:
                corpus = [
                    existing.full_text_for_embed()
                    for existing in self._chunks.values()
                ]
                self._embedder.fit_corpus(corpus)

        dense_vectors = self._embedder.embed(texts)
        sparse_vectors = self._sparse.encode_documents(texts)
        vector_dim = int(dense_vectors.shape[1])

        if self._vector_dim is None:
            if self._client.collection_exists(self._collection):
                info = self._client.get_collection(self._collection)
                vectors_cfg = info.config.params.vectors

                if isinstance(vectors_cfg, dict):
                    self._vector_dim = vectors_cfg[QDRANT_DENSE_VECTOR_NAME].size
                else:
                    self._vector_dim = vector_dim
            else:
                self._create_collection(vector_dim)
        elif self._vector_dim != vector_dim:
            raise ValueError(
                f"vector dim mismatch: collection={self._vector_dim}, chunk={vector_dim}"
            )

        self._upsert_vectors(chunk_ids, dense_vectors, sparse_vectors)

    def get(self, chunk_id: str) -> Chunk | None:
        if chunk_id in self._chunks:
            return self._chunks[chunk_id]

        point = self._client.retrieve(
            collection_name=self._collection,
            ids=[_point_id(chunk_id)],
            with_payload=True,
        )

        if not point:
            return None

        chunk = _chunk_from_payload(point[0].payload or {})

        if chunk is not None:
            self._chunks[chunk_id] = chunk

        return chunk

    def dense_search(
        self,
        query: str,
        *,
        k: int = DEFAULT_K_DENSE,
        factory: str | None = None,
        external: bool | None = None,
    ) -> list[tuple[str, float]]:
        if not self._chunks or self._vector_dim is None:
            return []

        query_vector = self._embedder.embed([query])[0].tolist()
        results = self._client.query_points(
            collection_name=self._collection,
            query=query_vector,
            using=QDRANT_DENSE_VECTOR_NAME,
            query_filter=_build_filter(factory=factory, external=external),
            limit=k,
            with_payload=True,
        )

        return [
            (str(point.payload["chunk_id"]), float(point.score))
            for point in results.points
            if point.payload and "chunk_id" in point.payload
        ]

    def bm25_search(
        self,
        query: str,
        *,
        k: int = DEFAULT_K_BM25,
        factory: str | None = None,
        external: bool | None = None,
    ) -> list[tuple[str, float]]:
        if not self._chunks or self._vector_dim is None:
            return []

        query_tokens = query.strip()

        if not query_tokens:
            return []

        query_sparse = self._sparse.encode_query(query)
        results = self._client.query_points(
            collection_name=self._collection,
            query=query_sparse,
            using=QDRANT_SPARSE_VECTOR_NAME,
            query_filter=_build_filter(factory=factory, external=external),
            limit=k,
            with_payload=True,
        )

        return [
            (str(point.payload["chunk_id"]), float(point.score))
            for point in results.points
            if point.payload and "chunk_id" in point.payload
        ]

    def hybrid_search(
        self,
        query: str,
        *,
        k: int = DEFAULT_K_HYBRID,
        factory: str | None = None,
        external: bool | None = None,
    ) -> list[tuple[str, float]]:
        """Qdrant server-side RRF over dense + BM25 sparse."""
        if not self._chunks or self._vector_dim is None or not query.strip():
            return []

        query_filter = _build_filter(factory=factory, external=external)
        query_dense = self._embedder.embed([query])[0].tolist()
        query_sparse = self._sparse.encode_query(query)
        results = self._client.query_points(
            collection_name=self._collection,
            prefetch=[
                Prefetch(
                    query=query_dense,
                    using=QDRANT_DENSE_VECTOR_NAME,
                    filter=query_filter,
                    limit=k,
                ),
                Prefetch(
                    query=query_sparse,
                    using=QDRANT_SPARSE_VECTOR_NAME,
                    filter=query_filter,
                    limit=k,
                ),
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            limit=k,
            with_payload=True,
        )

        return [
            (str(point.payload["chunk_id"]), float(point.score))
            for point in results.points
            if point.payload and "chunk_id" in point.payload
        ]

    def fetch_by_graph_nodes(
        self,
        node_ids: list[str],
        *,
        factory: str | None = None,
        k: int | None = None,
    ) -> list[tuple[str, float]]:
        node_set = {
            node_id
            for node_id in node_ids
            if node_id.startswith(RETRIEVAL_NODE_PREFIXES)
        }

        if not node_set:
            return []

        scroll_filter = _build_graph_filter(node_set, factory=factory)
        records, _ = self._client.scroll(
            collection_name=self._collection,
            scroll_filter=scroll_filter,
            limit=k or 10_000,
            with_payload=True,
        )

        hits: list[tuple[str, float]] = []

        for record in records:
            payload = record.payload or {}
            chunk_id = payload.get("chunk_id")

            if not chunk_id:
                continue

            graph_nodes = set(payload.get("graph_node_ids") or [])
            overlap = node_set & graph_nodes

            if overlap:
                hits.append((str(chunk_id), float(len(overlap))))

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
        type_should = [
            FieldCondition(key="chunk_type", match=MatchValue(value=chunk_type))
            for chunk_type in allowed
        ]
        records, _ = self._client.scroll(
            collection_name=self._collection,
            scroll_filter=Filter(should=type_should),
            limit=500,
            with_payload=True,
        )

        hits: list[tuple[str, float]] = []

        for record in records:
            payload = record.payload or {}
            chunk_id = payload.get("chunk_id")
            chunk_type = payload.get("chunk_type")

            if not chunk_id or chunk_type not in allowed:
                continue

            chunk_factory = payload.get("factory")
            meta = payload.get("metadata") or {}

            if chunk_type == "constraint_budget":
                if budget_tier and meta.get("budget_tier") != budget_tier:
                    continue
            elif factory and chunk_factory and chunk_factory != factory:
                continue

            if (
                chunk_type == "constraint_example"
                and budget_tier
                and meta.get("budget_tier")
                and meta.get("budget_tier") != budget_tier
            ):
                continue

            priority = 2.0 if chunk_type == "constraint_regulation" else 1.0
            hits.append((str(chunk_id), priority))

        hits.sort(key=lambda item: -item[1])

        return hits[:k]

    def texts_map(self) -> dict[str, str]:
        return {chunk_id: chunk.text for chunk_id, chunk in self._chunks.items()}

    def clear(self) -> None:
        if self._client.collection_exists(self._collection):
            self._client.delete_collection(self._collection)

        self._chunks.clear()
        self._vector_dim = None

    def _ensure_collection(self, vector_dim: int) -> None:
        if self._client.collection_exists(self._collection):
            self._vector_dim = vector_dim
            return

        try:
            self._create_collection(vector_dim)
        except Exception as exc:  # noqa: BLE001 — idempotent create
            if self._client.collection_exists(self._collection):
                self._vector_dim = vector_dim
                return

            raise exc

    def _create_collection(self, vector_dim: int) -> None:
        self._client.create_collection(
            collection_name=self._collection,
            vectors_config={
                QDRANT_DENSE_VECTOR_NAME: VectorParams(
                    size=vector_dim,
                    distance=Distance.COSINE,
                )
            },
            sparse_vectors_config={
                QDRANT_SPARSE_VECTOR_NAME: SparseVectorParams(
                    modifier=Modifier.IDF,
                )
            },
        )
        self._vector_dim = vector_dim

    def _upsert_vectors(
        self,
        chunk_ids: list[str],
        dense_vectors: np.ndarray,
        sparse_vectors: list,
    ) -> None:
        points = [
            PointStruct(
                id=_point_id(chunk_id),
                vector={
                    QDRANT_DENSE_VECTOR_NAME: dense_vectors[index].tolist(),
                    QDRANT_SPARSE_VECTOR_NAME: sparse_vectors[index],
                },
                payload=_payload_from_chunk(self._chunks[chunk_id]),
            )
            for index, chunk_id in enumerate(chunk_ids)
        ]

        self._client.upsert(collection_name=self._collection, points=points)


def _payload_from_chunk(chunk: Chunk) -> dict[str, Any]:
    return {
        "chunk_id": chunk.chunk_id,
        "text": chunk.text,
        "summary": chunk.summary,
        "source": chunk.source,
        "factory": chunk.factory,
        "chunk_type": chunk.chunk_type,
        "external": chunk.external,
        "graph_node_ids": list(chunk.graph_node_ids),
        "metadata": dict(chunk.metadata),
    }


def _chunk_from_payload(payload: dict[str, Any]) -> Chunk | None:
    chunk_id = payload.get("chunk_id")

    if not chunk_id:
        return None

    return Chunk(
        chunk_id=str(chunk_id),
        text=str(payload.get("text", "")),
        summary=str(payload.get("summary", "")),
        source=str(payload.get("source", "")),
        factory=payload.get("factory"),
        chunk_type=str(payload.get("chunk_type", "pdf_text")),
        graph_node_ids=list(payload.get("graph_node_ids") or []),
        external=bool(payload.get("external", False)),
        metadata=dict(payload.get("metadata") or {}),
    )


def _build_filter(
    *,
    factory: str | None,
    external: bool | None,
) -> Filter | None:
    conditions = []

    if factory:
        conditions.append(
            FieldCondition(key="factory", match=MatchValue(value=factory))
        )

    if external is not None:
        conditions.append(
            FieldCondition(key="external", match=MatchValue(value=external))
        )

    if not conditions:
        return None

    return Filter(must=conditions)


def _build_graph_filter(
    node_ids: set[str],
    *,
    factory: str | None,
) -> Filter:
    should = [
        FieldCondition(key="graph_node_ids", match=MatchValue(value=node_id))
        for node_id in sorted(node_ids)
    ]
    must: list[Any] = []

    if factory:
        must.append(
            Filter(
                should=[
                    FieldCondition(key="factory", match=MatchValue(value=factory)),
                    FieldCondition(
                        key="chunk_type", match=MatchValue(value="pdf_text")
                    ),
                    FieldCondition(
                        key="chunk_type", match=MatchValue(value="book_text")
                    ),
                    FieldCondition(
                        key="chunk_type", match=MatchValue(value="external_text")
                    ),
                    FieldCondition(
                        key="chunk_type", match=MatchValue(value="scheme_caption")
                    ),
                    FieldCondition(
                        key="chunk_type", match=MatchValue(value="constraint_regulation")
                    ),
                    FieldCondition(
                        key="chunk_type", match=MatchValue(value="constraint_example")
                    ),
                ]
            )
        )

    return Filter(must=must or None, should=should)
