"""Vector store protocol."""

from __future__ import annotations

from typing import Protocol

from graphrag.models import Chunk


class VectorStoreProtocol(Protocol):
    def add_many(self, chunks: list[Chunk]) -> None: ...

    def get(self, chunk_id: str) -> Chunk | None: ...

    def dense_search(
        self,
        query: str,
        *,
        k: int = 50,
        factory: str | None = None,
        external: bool | None = None,
    ) -> list[tuple[str, float]]: ...

    def bm25_search(
        self,
        query: str,
        *,
        k: int = 50,
        factory: str | None = None,
        external: bool | None = None,
    ) -> list[tuple[str, float]]: ...

    def fetch_by_graph_nodes(
        self,
        node_ids: list[str],
        *,
        factory: str | None = None,
        k: int | None = None,
    ) -> list[tuple[str, float]]: ...

    def texts_map(self) -> dict[str, str]: ...
