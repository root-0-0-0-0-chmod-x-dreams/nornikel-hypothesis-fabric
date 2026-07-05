import json
import logging

from app.agents.llm import call_llm, parse_json_from_text
from app.mcp.web_retrieval import search_scholar, search_arxiv, search_web
from app.config import get_config

logger = logging.getLogger("hypothesis_factory")
config = get_config()

JUDGE_SYSTEM = """Ты — главный технолог-критик Норильского ГМК с 35-летним опытом. Твоя роль в системе «Фабрика гипотез» — Judge/Critic. Ты БЕСПОЩАДНО критикуешь каждую гипотезу, целенаправленно ищешь контраргументы и слабые места.

ТВОИ ИНСТРУМЕНТЫ (MCP):
1. Векторная БД знаний — search_knowledge(query)
2. Google Scholar — search_scholar(query)
3. Arxiv — search_arxiv(query)
4. Интернет — search_web(query)

ТВОЯ ЗАДАЧА:
1. Найти КОНТРАРГУМЕНТЫ — почему гипотеза может НЕ работать
2. Проверить ПОЛНОТУ обоснования — все ли аспекты учтены
3. Выявить отсутствующие блоки: нет механизма? нет источников? нет оценки рисков?
4. Оценить по БИНАРНЫМ МЕТРИКАМ (строго 0 или 1):

МЕТРИКИ ОЦЕНКИ:
- full_rationale: полное корректное обоснование (1/0, вес 0.5)
- all_sources: все ссылки на источники присутствуют (1/0, БЛОКИРУЮЩАЯ — без неё гипотеза отклоняется)
- mechanism_and_novelty: описан механизм влияния И оценка новизны (1/0, вес 0.3)
- risks_assessed: проанализированы технические И экономические риски (1/0, БЛОКИРУЮЩАЯ)
- kpi_impact: указано влияние на целевой KPI (1/0, вес 0.2)

Итоговый порог: ВСЕ пункты = 1. Если хотя бы одна блокирующая метрика = 0 — гипотеза ОТКЛОНЯЕТСЯ.

ФОРМАТ ОТВЕТА (строго JSON):
{
  "verdict": "pass" | "reject",
  "metrics": {
    "full_rationale": 1,
    "all_sources": 1,
    "mechanism_and_novelty": 1,
    "risks_assessed": 1,
    "kpi_impact": 1
  },
  "critique": "Развёрнутая критика (3-6 предложений) — что не так и почему",
  "counter_arguments": ["Перечень контраргументов с ссылками на источники"],
  "missing_blocks": ["Каких блоков не хватает в обосновании"],
  "suggestions_for_actor": ["Что Actor должен исправить/добавить"],
  "final_score": 0.85
}

Никакого текста вне JSON."""


def critique_hypothesis(hypothesis: dict, actor_result: dict, context: str) -> dict:
    """Agent 3 (Judge): Criticize hypothesis, evaluate binary metrics."""

    hyp_text = json.dumps(hypothesis, ensure_ascii=False, indent=2)
    actor_text = json.dumps(actor_result, ensure_ascii=False, indent=2)

    user_msg = f"""# Контекст (данные анализа)
{context}

# Гипотеза
{hyp_text}

# Обоснование Actor (Агент 2)
{actor_text}

Найди контраргументы через search_scholar/search_arxiv/search_web/search_knowledge. Оцени по бинарным метрикам. Верни строго JSON."""

    messages = [
        {"role": "system", "content": JUDGE_SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    logger.info("judge_critiquing", extra={"title": hypothesis.get("title", "")[:80]})
    response = call_llm(messages, temperature=0.3, max_tokens=8000)

    result = parse_json_from_text(response)
    if isinstance(result, list):
        result = result[0] if result else {}
    if not isinstance(result, dict) or "verdict" not in result:
        return {
            "verdict": "reject",
            "metrics": {"full_rationale": 0, "all_sources": 0, "mechanism_and_novelty": 0, "risks_assessed": 0, "kpi_impact": 0},
            "critique": f"Judge parse error: {str(result)[:200]}",
            "missing_blocks": ["all"],
            "suggestions_for_actor": ["retry"],
            "final_score": 0.0,
        }

    logger.info("judge_verdict", extra={"verdict": result.get("verdict"), "score": result.get("final_score")})
    return result


def check_pass_criteria(judge_result: dict) -> bool:
    """Check if all binary metrics pass."""
    metrics = judge_result.get("metrics", {})
    required = ["full_rationale", "all_sources", "mechanism_and_novelty", "risks_assessed", "kpi_impact"]
    return all(metrics.get(m, 0) == 1 for m in required)
