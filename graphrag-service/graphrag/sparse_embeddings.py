"""Sparse BM25 encodings for Qdrant (server-side IDF)."""

from __future__ import annotations

from functools import lru_cache

from qdrant_client.models import SparseVector

from graphrag.constants import QDRANT_SPARSE_VECTOR_NAME

_BM25_MODEL = "Qdrant/bm25"


@lru_cache(maxsize=1)
def _sparse_model():
    from fastembed import SparseTextEmbedding

    return SparseTextEmbedding(_BM25_MODEL, lazy_load=True)


def _to_sparse_vector(embedding) -> SparseVector:
    return SparseVector(
        indices=embedding.indices.tolist(),
        values=embedding.values.tolist(),
    )


class Bm25SparseEncoder:
    """Encode text as BM25 sparse vectors for Qdrant (`modifier=idf`)."""

    vector_name = QDRANT_SPARSE_VECTOR_NAME

    def encode_documents(self, texts: list[str]) -> list[SparseVector]:
        if not texts:
            return []

        model = _sparse_model()

        return [_to_sparse_vector(embedding) for embedding in model.embed(texts)]

    def encode_query(self, query: str) -> SparseVector:
        model = _sparse_model()
        embedding = next(model.query_embed(query))

        return _to_sparse_vector(embedding)
