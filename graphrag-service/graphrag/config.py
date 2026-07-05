"""Environment-backed configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

from graphrag.constants import (
    GRAPH_BACKEND_NETWORKX,
    NEO4J_DEFAULT_PASSWORD,
    NEO4J_DEFAULT_URI,
    NEO4J_DEFAULT_USER,
    QDRANT_DEFAULT_COLLECTION,
    QDRANT_DEFAULT_URL,
    RABBITMQ_DEFAULT_URL,
    RABBITMQ_EXCHANGE,
)


@dataclass(frozen=True)
class Neo4jConfig:
    uri: str
    user: str
    password: str
    database: str = "neo4j"

    @classmethod
    def from_env(cls) -> Neo4jConfig:
        return cls(
            uri=os.getenv("NEO4J_URI", NEO4J_DEFAULT_URI),
            user=os.getenv("NEO4J_USER", NEO4J_DEFAULT_USER),
            password=os.getenv("NEO4J_PASSWORD", NEO4J_DEFAULT_PASSWORD),
            database=os.getenv("NEO4J_DATABASE", "neo4j"),
        )


@dataclass(frozen=True)
class QdrantConfig:
    url: str
    collection: str

    @classmethod
    def from_env(cls) -> QdrantConfig:
        return cls(
            url=os.getenv("QDRANT_URL", QDRANT_DEFAULT_URL),
            collection=os.getenv("QDRANT_COLLECTION", QDRANT_DEFAULT_COLLECTION),
        )


@dataclass(frozen=True)
class RabbitmqConfig:
    url: str
    exchange: str

    @classmethod
    def from_env(cls) -> RabbitmqConfig:
        return cls(
            url=os.getenv("RABBITMQ_URL", RABBITMQ_DEFAULT_URL),
            exchange=os.getenv("RABBITMQ_EXCHANGE", RABBITMQ_EXCHANGE),
        )


@dataclass(frozen=True)
class AppConfig:
    graph_backend: str
    vector_backend: str
    neo4j: Neo4jConfig
    qdrant: QdrantConfig
    rabbitmq: RabbitmqConfig

    @classmethod
    def from_env(cls) -> AppConfig:
        from graphrag.constants import VECTOR_BACKEND_QDRANT

        return cls(
            graph_backend=os.getenv("GRAPH_BACKEND", GRAPH_BACKEND_NETWORKX),
            vector_backend=os.getenv("VECTOR_BACKEND", VECTOR_BACKEND_QDRANT),
            neo4j=Neo4jConfig.from_env(),
            qdrant=QdrantConfig.from_env(),
            rabbitmq=RabbitmqConfig.from_env(),
        )
