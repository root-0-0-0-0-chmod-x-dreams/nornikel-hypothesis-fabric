"""Shared constants — no magic numbers in business logic."""

from __future__ import annotations

# Graph traversal
DEFAULT_MAX_HOPS = 3
DEFAULT_MAX_PATHS = 20
DEFAULT_RELATION = "RELATED_TO"

# Only these edges drive GraphRAG retrieval (Swanson ABC / intervention path).
INTERVENTION_RELATIONS: frozenset[str] = frozenset(
    {
        "EXPLAINED_BY",
        "ADDRESSED_BY",
        "USES_EQUIPMENT",
        "RELATED_MECHANISM",
    }
)

# Chunk fetch by graph_node_ids for GraphRAG context.
RETRIEVAL_NODE_PREFIXES: tuple[str, ...] = (
    "lossform_",
    "mech_",
    "process_",
    "equip_",
    "mineral_",
    "reagent_",
)

# Literature evidence: follow from ABC nodes to Source (PDF/page).
EVIDENCE_RELATIONS: frozenset[str] = frozenset({"EVIDENCED_BY"})

DEFAULT_K_GRAPH = 30

# Retrieval
DEFAULT_K_DENSE = 60
DEFAULT_K_BM25 = 60
DEFAULT_K_HYBRID = 60
DEFAULT_K_OUT = 8
FUSION_CANDIDATE_MULTIPLIER = 4

# RRF / rerank
RRF_K = 60
RERANK_OVERLAP_WEIGHT = 0.2
GRAPH_OVERLAP_RERANK_WEIGHT = 0.25
MMR_LAMBDA = 0.72

# Channel weights in weighted RRF (graph boosted when bucket known)
RRF_WEIGHT_GRAPH = 2.5
RRF_WEIGHT_GRAPH_REPEAT = 1.5
RRF_WEIGHT_HYBRID = 1.6
RRF_WEIGHT_CONSTRAINT = 2.0
RRF_WEIGHT_DENSE = 1.0
RRF_WEIGHT_BM25 = 1.3

# Embeddings
TFIDF_MAX_FEATURES = 512
HASH_EMBEDDING_DIM = 256

# Retrieval channel labels
CHANNEL_GRAPH = "graph"
CHANNEL_DENSE = "dense"
CHANNEL_BM25 = "bm25"
CHANNEL_HYBRID = "hybrid"
CHANNEL_CONSTRAINT = "constraint"
CHANNEL_FUSED = "fused"

# Neo4j
NEO4J_DEFAULT_URI = "bolt://localhost:7687"
NEO4J_DEFAULT_USER = "neo4j"
NEO4J_DEFAULT_PASSWORD = "hypothesis2026"
NEO4J_ENTITY_LABEL = "Entity"

# Backends
GRAPH_BACKEND_NETWORKX = "networkx"
GRAPH_BACKEND_NEO4J = "neo4j"

VECTOR_BACKEND_MEMORY = "memory"
VECTOR_BACKEND_QDRANT = "qdrant"

# Qdrant
QDRANT_DEFAULT_URL = "http://localhost:6333"
QDRANT_DEFAULT_COLLECTION = "hypothesis_text_chunks"
QDRANT_DENSE_VECTOR_NAME = "dense"
QDRANT_SPARSE_VECTOR_NAME = "bm25"

# RabbitMQ (diagram 07_storage_internals)
RABBITMQ_DEFAULT_URL = "amqp://hypothesis:hypothesis2026@localhost:5672/"
RABBITMQ_EXCHANGE = "hypothesis.factory"
QUEUE_CHUNKS_TEXT = "chunks_text"
QUEUE_CHUNKS_SCHEME = "chunks_scheme"
QUEUE_GRAPH_TRIPLETS = "graph_triplets"
QUEUE_GRAPH_RAG_QUERY = "graph_rag_query"
QUEUE_NL_CYPHER_QUERY = "nl_cypher_query"
QUEUE_INGEST_BOOTSTRAP = "ingest_bootstrap"

# Case data layout
CASE_DATA_DIRNAME = "Задача 1. Фабрика гипотез"
CASE_TASK_DIRNAME = "Задача 1"

# Ingestion
PDF_CHUNK_CHARS = 1200
PDF_CHUNK_OVERLAP = 200
BOOK_CHUNK_GRANULARITY = "paragraph"  # benchmark: best GraphRAG + provenance balance
BOOK_EXTRACTOR_BACKEND = "opendataloader"
EXTERNAL_CHUNK_GRANULARITY = BOOK_CHUNK_GRANULARITY
METAL_NI = "Ni"
METAL_CU = "Cu"
METAL_ELEMENT_28 = "Элемент 28"
METAL_ELEMENT_29 = "Элемент 29"

# Coarse size classes (μm) — used for intervention routing
COARSE_SIZE_CLASSES = ("+125", "+71", "-125+71", "-71+45", "-71 + 45")
FINE_SIZE_CLASS = "-10"
