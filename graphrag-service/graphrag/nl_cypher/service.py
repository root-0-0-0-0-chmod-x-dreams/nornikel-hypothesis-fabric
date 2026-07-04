"""Execute NL graph queries against Neo4j."""

from __future__ import annotations

from typing import Any

from neo4j import GraphDatabase

from graphrag.config import Neo4jConfig
from graphrag.nl_cypher.formatter import build_hints, format_answer
from graphrag.nl_cypher.models import NLQueryResult
from graphrag.nl_cypher.parser import build_bucket_id, parse_question
from graphrag.nl_cypher.templates import build_cypher


class NLGraphQueryService:
    """Text-to-Cypher: Russian question → safe template Cypher → answer."""

    def __init__(self, config: Neo4jConfig | None = None) -> None:
        self._config = config or Neo4jConfig.from_env()
        self._driver = GraphDatabase.driver(
            self._config.uri,
            auth=(self._config.user, self._config.password),
        )

    @staticmethod
    def compile(question: str, *, show_hints: bool = False) -> NLQueryResult:
        """Build Cypher from NL without executing Neo4j (preview / offline)."""
        parsed = parse_question(question)
        bucket_id = build_bucket_id(parsed)
        cypher, params = build_cypher(parsed, bucket_id=bucket_id)
        normalized = " ".join(line.strip() for line in cypher.splitlines()).strip()

        return NLQueryResult(
            question=question,
            intent=parsed.intent.value,
            cypher=normalized,
            params=params,
            rows=[],
            answer="Cypher сгенерирован. Нажмите «Ask graph» для выполнения в Neo4j.",
            bucket_id=bucket_id,
            hints=build_hints(parsed) if show_hints else [],
        )

    def close(self) -> None:
        self._driver.close()

    def ask(self, question: str, *, show_hints: bool = False) -> NLQueryResult:
        compiled = self.compile(question, show_hints=show_hints)
        rows = self._run(compiled.cypher, compiled.params)
        parsed = parse_question(question)
        answer = format_answer(parsed, rows, compiled.bucket_id)

        return NLQueryResult(
            question=compiled.question,
            intent=compiled.intent,
            cypher=compiled.cypher,
            params=compiled.params,
            rows=rows,
            answer=answer,
            bucket_id=compiled.bucket_id,
            hints=compiled.hints,
        )

    def _run(self, cypher: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        with self._driver.session(database=self._config.database) as session:
            result = session.run(cypher, **params)

            return [dict(record) for record in result]
