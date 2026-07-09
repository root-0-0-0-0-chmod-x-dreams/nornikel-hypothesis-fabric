import json
import logging

from app.agents.llm import call_llm, parse_json_from_text
from app.mcp.vector_db import query_vector_db
from app.sources import chunks_to_knowledge_sources, merge_knowledge_sources
from app.config import get_config

logger = logging.getLogger("hypothesis_factory")
config = get_config()

ACTOR_SYSTEM = """Ты — ведущий технолог-обогатитель, эксперт Норильского комбината с 25-летним опытом. Твоя роль в системе «Фабрика гипотез» — Actor/Validator: ты проверяешь и обосновываешь каждую гипотезу.

ТВОИ ИНСТРУМЕНТЫ (MCP):
1. Векторная БД знаний — запрос через search_knowledge(query)
2. Google Scholar — search_scholar(query)  
3. Arxiv — search_arxiv(query)
4. Интернет — search_web(query)

ТВОЯ ЗАДАЧА:
1. Проверить гипотезу на соответствие данным анализа потерь
2. Найти ПОДТВЕРЖДАЮЩИЕ источники — патенты, статьи, учебники, технологические регламенты
3. Проверить корректность ссылок и механизма влияния
4. Дать развёрнутое ОБОСНОВАНИЕ гипотезы
5. Если Judge (Агент 3) нашёл замечания — исправить их, дополнив обоснование

ВАЖНО: Если замечания Judge НЕВОЗМОЖНО исправить (нет данных, противоречие) — честно признай: гипотезу следует ОТБРОСИТЬ.

ФОРМАТ ОТВЕТА (строго JSON):
{
  "verdict": "pass" | "reject",
  "justification": "Развёрнутое технологическое обоснование (3-6 предложений)",
  "mechanism_detail": "Детальный механизм влияния: физический/химический/технологический процесс",
  "sources": [
    {"type": "patent|article|textbook|web|db", "title": "...", "chunk_id": "опционально для db", "relevance": "как подтверждает гипотезу"}
  ],
  "novelty_assessment": "Оценка новизны по сравнению с известными решениями в отрасли",
  "risks": {
    "technical": "Технические риски внедрения",
    "economic": "Экономические риски (CAPEX/OPEX)"
  },
  "expected_kpi_impact": "Влияние на целевой KPI в цифрах",
  "experiment_roadmap": "План проверки: этапы, оборудование, критерии успеха",
  "judge_comments_resolved": ["перечень исправленных замечаний"]
}

Никакого текста вне JSON."""


def validate_hypothesis(
    hypothesis: dict,
    context: str,
    judge_feedback: list[str] | None = None,
    prefetched_sources: list[dict] | None = None,
) -> dict:
    """Agent 2 (Actor): Validate hypothesis, find sources, provide justification."""

    search_query = " ".join(
        part
        for part in (
            hypothesis.get("title", ""),
            hypothesis.get("mechanism", ""),
            hypothesis.get("description", ""),
        )
        if part
    )
    if prefetched_sources:
        db_sources = list(prefetched_sources)
    else:
        db_chunks = query_vector_db(search_query, top_k=6)
        db_sources = chunks_to_knowledge_sources(db_chunks)

    hyp_text = json.dumps(hypothesis, ensure_ascii=False, indent=2)
    sources_text = json.dumps(db_sources, ensure_ascii=False, indent=2)

    user_msg = f"""# Контекст (данные анализа)
{context}

# Гипотеза для проверки
{hyp_text}

# Источники из базы знаний GraphRAG (обязательно ссылайся на chunk_id в sources)
{sources_text}"""

    if judge_feedback:
        user_msg += f"\n\n# Замечания Judge (требуется исправить)\n" + "\n".join(f"- {f}" for f in judge_feedback)

    user_msg += "\n\nИспользуй источники из базы знаний с chunk_id. Для внешних источников укажи type=web|article|patent. Верни строго JSON."

    messages = [
        {"role": "system", "content": ACTOR_SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    logger.info("actor_validating", extra={"title": hypothesis.get("title", "")[:80]})
    response = call_llm(messages, temperature=0.5, max_tokens=4096)

    result = parse_json_from_text(response)
    if isinstance(result, list):
        result = result[0] if result else {}
    if not isinstance(result, dict) or "verdict" not in result:
        return {"verdict": "reject", "justification": f"Actor parse error: {str(result)[:200]}"}

    llm_sources = []
    for s in result.get("sources") or []:
        if not isinstance(s, dict):
            continue
        chunk_id = s.get("chunk_id")
        matched = next((d for d in db_sources if d.get("chunk_id") == chunk_id), None) if chunk_id else None
        if matched:
            llm_sources.append({**matched, "relevance": s.get("relevance") or matched.get("relevance") or ""})
        else:
            llm_sources.append(
                {
                    "chunk_id": chunk_id,
                    "title": s.get("title") or "Источник",
                    "type": s.get("type") or "reference",
                    "excerpt": s.get("relevance") or "",
                    "relevance": s.get("relevance") or "",
                }
            )

    result["knowledge_sources"] = merge_knowledge_sources(db_sources, llm_sources)

    logger.info("actor_verdict", extra={"verdict": result.get("verdict"), "sources": len(result["knowledge_sources"])})
    return result
