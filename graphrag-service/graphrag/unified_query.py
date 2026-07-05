"""Unified GraphRAG query — one RPC for LLM Service / agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from graphrag.constants import DEFAULT_K_OUT
from graphrag.embeddings import tokenize
from graphrag.graph.base import GraphStoreProtocol
from graphrag.models import GraphRAGResult
from graphrag.nl_cypher.parser import parse_question
from graphrag.nl_cypher.service import NLGraphQueryService
from graphrag.service import GraphRAGQueryService
from graphrag.session_context import resolve_session_context
from graphrag.vector_protocol import VectorStoreProtocol


@dataclass
class HypothesisQuery:
    id: str
    retrieval_query: str
    label: str | None = None


@dataclass
class UnifiedQueryRequest:
    """Input from LLM Service (original goal + optional LLM rephrasing)."""

    question: str
    retrieval_query: str | None = None
    retrieval_queries: list[str] = field(default_factory=list)
    hypotheses: list[HypothesisQuery] | list[dict[str, Any]] = field(default_factory=list)
    bucket_id: str | None = None
    factory: str | None = None
    budget_tier: str | None = None
    user_constraints: list[str] = field(default_factory=list)
    k_out: int = DEFAULT_K_OUT
    include_external: bool = False
    auto_bucket: bool = True
    include_graph_analytics: bool = False
    include_hypothesis_support: bool = True
    use_graph: bool = True
    max_hops: int | None = None


@dataclass
class UnifiedQueryResult:
    question: str
    retrieval_query: str
    retrieval_queries: list[str]
    bucket_id: str | None
    factory: str | None
    budget_tier: str | None
    graph_rag: GraphRAGResult
    agent_role: str | None = None
    constraints: dict[str, Any] = field(default_factory=dict)
    hypotheses: list[dict[str, Any]] = field(default_factory=list)
    budget_inference: dict[str, Any] | None = None
    graph_analytics: dict[str, Any] | None = None
    resolution: dict[str, Any] = field(default_factory=dict)


class UnifiedGraphRAGService:
    """Single entrypoint: hybrid retrieval + graph traverse + rerank + optional NL graph stats."""

    def __init__(
        self,
        graph: GraphStoreProtocol,
        vectors: VectorStoreProtocol,
        *,
        nl_cypher: NLGraphQueryService | None = None,
    ) -> None:
        self._graph_rag = GraphRAGQueryService(graph, vectors)
        self._nl_cypher = nl_cypher

    def query(self, request: UnifiedQueryRequest) -> UnifiedQueryResult:
        parsed = parse_question(request.question)
        session = resolve_session_context(
            self._graph_rag._graph,
            request.question,
            bucket_id=request.bucket_id,
            factory=request.factory,
            budget_tier=request.budget_tier,
            user_constraints=request.user_constraints,
            auto_bucket=request.auto_bucket,
        )
        bucket_id = session.bucket_id
        factory = session.factory
        budget_tier = session.budget_tier
        budget_inference = session.budget_inference
        hypotheses = _resolve_hypotheses(request)
        retrieval_queries = [hypothesis.retrieval_query for hypothesis in hypotheses]

        query_kwargs: dict[str, Any] = {
            "bucket_id": bucket_id,
            "factory": factory,
            "k_out": request.k_out,
            "include_external": request.include_external,
            "budget_tier": budget_tier,
            "use_graph": request.use_graph,
        }

        if retrieval_queries:
            if len(retrieval_queries) == 1:
                query_kwargs["retrieval_query"] = retrieval_queries[0]
            else:
                query_kwargs["retrieval_queries"] = retrieval_queries

        if request.max_hops is not None:
            query_kwargs["max_hops"] = request.max_hops

        graph_rag = self._graph_rag.query(request.question, **query_kwargs)

        hypothesis_payloads = _build_hypothesis_payloads(
            hypotheses,
            graph_rag,
            probe_support=(
                graph_rag.hypothesis_probe
                if request.include_hypothesis_support and graph_rag.hypothesis_probe
                else (
                    self._graph_rag.probe_hypothesis_support(
                        retrieval_queries,
                        factory=factory,
                        include_external=request.include_external,
                    )
                    if request.include_hypothesis_support and len(retrieval_queries) > 1
                    else []
                )
            ),
        )

        graph_analytics = None

        if request.include_graph_analytics:
            graph_analytics = self._graph_analytics(request.question)

        return UnifiedQueryResult(
            question=request.question,
            retrieval_query=graph_rag.expanded_query or request.question,
            retrieval_queries=retrieval_queries or [graph_rag.expanded_query or request.question],
            bucket_id=bucket_id,
            factory=factory,
            budget_tier=budget_tier,
            graph_rag=graph_rag,
            hypotheses=hypothesis_payloads,
            budget_inference=budget_inference,
            agent_role=session.agent_role,
            constraints=session.constraints,
            graph_analytics=graph_analytics,
            resolution={
                "auto_bucket": request.auto_bucket,
                "parsed_intent": parsed.intent.value,
                "parsed_factory": parsed.factory,
                "parsed_metal": parsed.metal,
                "parsed_size_class": parsed.size_class,
                "parsed_form_slug": parsed.form_slug,
                "hypothesis_count": len(hypothesis_payloads),
                "bucket_resolution": session.bucket_resolution,
                "budget_inference": budget_inference,
                "agent_role": session.agent_role,
                "constraints": session.constraints,
                "top_buckets": session.top_buckets,
            },
        )

    def _graph_analytics(self, question: str) -> dict[str, Any]:
        if self._nl_cypher is None:
            compiled = NLGraphQueryService.compile(question, show_hints=True)

            return {
                "answer": compiled.answer,
                "cypher": compiled.cypher,
                "intent": compiled.intent,
                "bucket_id": compiled.bucket_id,
                "rows": compiled.rows,
                "hints": compiled.hints,
                "executed": False,
            }

        result = self._nl_cypher.ask(question, show_hints=True)

        return {
            "answer": result.answer,
            "cypher": result.cypher,
            "intent": result.intent,
            "bucket_id": result.bucket_id,
            "rows": result.rows,
            "hints": result.hints,
            "executed": True,
        }


def _resolve_hypotheses(request: UnifiedQueryRequest) -> list[HypothesisQuery]:
    if request.hypotheses:
        normalized: list[HypothesisQuery] = []

        for index, item in enumerate(request.hypotheses):
            if isinstance(item, HypothesisQuery):
                normalized.append(item)
                continue

            if isinstance(item, dict):
                query = str(
                    item.get("retrieval_query") or item.get("query") or item.get("graph_question") or ""
                ).strip()

                if not query:
                    continue

                normalized.append(
                    HypothesisQuery(
                        id=str(item.get("id") or f"h{index + 1}"),
                        label=item.get("label"),
                        retrieval_query=query,
                    )
                )

        if normalized:
            return normalized

    queries: list[str] = []

    if request.retrieval_query and request.retrieval_query.strip():
        queries.append(request.retrieval_query.strip())

    for query in request.retrieval_queries:
        cleaned = str(query).strip()

        if cleaned and cleaned not in queries:
            queries.append(cleaned)

    if not queries:
        return []

    return [
        HypothesisQuery(id=f"h{index + 1}", retrieval_query=query)
        for index, query in enumerate(queries)
    ]


def _build_hypothesis_payloads(
    hypotheses: list[HypothesisQuery],
    graph_rag: GraphRAGResult,
    *,
    probe_support: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not hypotheses:
        return []

    probe_by_index = {item["index"]: item for item in probe_support}
    fused_chunk_ids = {chunk.chunk_id for chunk in graph_rag.chunks}
    payloads: list[dict[str, Any]] = []

    for index, hypothesis in enumerate(hypotheses):
        query_tokens = set(tokenize(hypothesis.retrieval_query))
        supporting_chunks: list[dict[str, Any]] = []

        for chunk in graph_rag.chunks:
            overlap = _token_overlap(query_tokens, chunk.text)

            if overlap <= 0:
                continue

            supporting_chunks.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "score": chunk.score,
                    "overlap": overlap,
                    "source": chunk.source,
                    "in_fused_result": chunk.chunk_id in fused_chunk_ids,
                }
            )

        supporting_chunks.sort(key=lambda item: (-item["overlap"], -item["score"]))

        probe = probe_by_index.get(index, {})
        top_probe = probe.get("top_chunks") or []

        payloads.append(
            {
                "id": hypothesis.id,
                "label": hypothesis.label,
                "retrieval_query": hypothesis.retrieval_query,
                "supporting_chunks": supporting_chunks[:5],
                "probe_top_chunks": top_probe[:5],
            }
        )

    return payloads


def _token_overlap(query_tokens: set[str], text: str) -> float:
    if not query_tokens:
        return 0.0

    doc_tokens = set(tokenize(text))

    return len(query_tokens & doc_tokens) / max(len(query_tokens), 1)


def unified_request_from_payload(payload: dict[str, Any]) -> UnifiedQueryRequest:
    hypotheses = _hypotheses_from_payload(payload)
    retrieval_queries = [
        str(query).strip()
        for query in (payload.get("retrieval_queries") or payload.get("graph_questions") or [])
        if str(query).strip()
    ]
    retrieval = payload.get("retrieval_query") or payload.get("graph_question")

    return UnifiedQueryRequest(
        question=str(payload["question"]),
        retrieval_query=str(retrieval).strip() if retrieval else None,
        retrieval_queries=retrieval_queries,
        hypotheses=hypotheses,
        bucket_id=payload.get("bucket_id"),
        factory=payload.get("factory"),
        budget_tier=payload.get("budget_tier"),
        user_constraints=[
            str(item).strip()
            for item in (payload.get("constraints") or payload.get("user_constraints") or [])
            if str(item).strip()
        ],
        k_out=int(payload.get("k_out", DEFAULT_K_OUT)),
        include_external=bool(payload.get("include_external", False)),
        auto_bucket=bool(payload.get("auto_bucket", True)),
        include_graph_analytics=bool(payload.get("include_graph_analytics", False)),
        include_hypothesis_support=bool(payload.get("include_hypothesis_support", True)),
        use_graph=bool(payload.get("use_graph", True)),
        max_hops=int(payload["max_hops"]) if payload.get("max_hops") is not None else None,
    )


def _hypotheses_from_payload(payload: dict[str, Any]) -> list[HypothesisQuery]:
    raw = payload.get("hypotheses") or []

    if not raw:
        return []

    hypotheses: list[HypothesisQuery] = []

    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            continue

        query = str(
            item.get("retrieval_query") or item.get("query") or item.get("graph_question") or ""
        ).strip()

        if not query:
            continue

        hypotheses.append(
            HypothesisQuery(
                id=str(item.get("id") or f"h{index + 1}"),
                label=item.get("label"),
                retrieval_query=query,
            )
        )

    return hypotheses


def unified_result_to_dict(result: UnifiedQueryResult) -> dict[str, Any]:
    from graphrag.messaging.schemas import graph_rag_result_to_dict

    graph_payload = graph_rag_result_to_dict(result.graph_rag)

    pipeline = [
        "graph_traverse",
        "hybrid_dense_bm25",
        "constraint_fetch",
        "weighted_rrf",
        "graph_overlap_rerank",
        "overlap_rerank",
        "mmr",
    ]

    if len(result.retrieval_queries) > 1:
        pipeline.insert(3, "multi_hypothesis_rrf")

    return {
        **graph_payload,
        "question": result.question,
        "retrieval_query": result.retrieval_query,
        "retrieval_queries": result.retrieval_queries,
        "hypotheses": result.hypotheses,
        "bucket_id": result.bucket_id,
        "factory": result.factory,
        "budget_tier": result.budget_tier,
        "budget_inference": result.budget_inference,
        "agent_role": result.agent_role,
        "constraints": result.constraints,
        "resolution": result.resolution,
        "graph_analytics": result.graph_analytics,
        "pipeline": pipeline,
    }
