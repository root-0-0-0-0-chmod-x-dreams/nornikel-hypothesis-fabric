"""Vector store factory."""

from __future__ import annotations

import os

from graphrag.config import QdrantConfig
from graphrag.constants import VECTOR_BACKEND_MEMORY, VECTOR_BACKEND_QDRANT
from graphrag.embeddings import EmbeddingProvider
from graphrag.qdrant_store import QdrantVectorStore
from graphrag.vector_protocol import VectorStoreProtocol
from graphrag.vector_store import VectorStore


def create_vector_store(
    backend: str | None = None,
    *,
    embedder: EmbeddingProvider | None = None,
    qdrant_config: QdrantConfig | None = None,
) -> VectorStoreProtocol:
    selected = backend or os.getenv("VECTOR_BACKEND", VECTOR_BACKEND_QDRANT)

    if selected == VECTOR_BACKEND_MEMORY:
        return VectorStore(embedder=embedder)

    return QdrantVectorStore(config=qdrant_config, embedder=embedder)
