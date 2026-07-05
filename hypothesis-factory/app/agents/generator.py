import json
import logging

from app.agents.llm import call_llm, parse_json_from_text
from app.mcp.vector_db import query_vector_db
from app.config import get_config

logger = logging.getLogger("hypothesis_factory")
config = get_config()

GENERATOR_SYSTEM = """Ты — ведущий научный сотрудник НИИ обогащения полезных ископаемых с 30-летним опытом работы на Норильской обогатительной фабрике. Твоя специализация — анализ потерь в хвостах флотации и генерация технологических гипотез по их снижению.

Ты работаешь в системе «Фабрика гипотез» и твоя задача — на основе предоставленных данных (анализ потерь, документы по флотации, схемы, учебники, веб-источники) сгенерировать конкретные, проверяемые технологические гипотезы.

ПРАВИЛА ГЕНЕРАЦИИ ГИПОТЕЗ:
1. Каждая гипотеза должна содержать КОНКРЕТНОЕ технологическое решение (не «улучшить флотацию», а «заменить песковые насадки гидроциклонов с 12 на 8 мм»)
2. Гипотеза должна быть ПРОВЕРЯЕМОЙ в лабораторных или промышленных условиях
3. Каждая гипотеза должна иметь ЧЁТКИЙ механизм влияния на целевой показатель
4. Гипотезы должны быть РАЗНООБРАЗНЫМИ — затрагивать разные аспекты процесса (измельчение, флотация, классификация, автоматизация)
5. Приоритет: гипотезы с НАИБОЛЬШИМ ПОТЕНЦИАЛЬНЫМ ЭФФЕКТОМ и НАИМЕНЬШИМИ ЗАТРАТАМИ на проверку

ТЫ ДОЛЖЕН ВЕРНУТЬ JSON-МАССИВ гипотез СТРОГО в формате:
[
  {
    "title": "Краткое название гипотезы (1 предложение)",
    "description": "Развёрнутое описание (2-4 предложения)",
    "rationale": "Обоснование из данных: какие цифры/факты подтверждают необходимость",
    "mechanism": "Ожидаемый механизм влияния: КАК именно технология повлияет на KPI",
    "expected_impact": "Ожидаемый эффект в % или абсолютных величинах",
    "category": "измельчение|флотация|классификация|автоматизация|реагентный режим|оборудование",
    "novelty": "high|medium|low",
    "references": ["ключевые источники из данных"]
  }
]

НИКАКОГО текста вне JSON. Только массив объектов."""


def generate_hypotheses(
    query: str,
    documents: list[str],
    analysis_data: str = "",
    image_descriptions: list[str] | None = None,
    num_hypotheses: int | None = None,
) -> list[dict]:
    """Agent 1: Generate hypotheses from query + documents + analysis data."""

    num = num_hypotheses or config.default_hypotheses_count

    # Step 1: Retrieve relevant chunks from vector DB
    logger.info("agent1_retrieving", extra={"query": query[:100]})
    retrieved = query_vector_db(query, top_k=5)
    retrieved_text = ""
    if retrieved and not retrieved[0].get("status"):
        retrieved_text = "\n".join(
            r.get("content", r.get("text", json.dumps(r, ensure_ascii=False)[:500]))
            for r in retrieved[:5]
        )

    # Step 2: Build context
    context_parts = [f"# Запрос пользователя\n{query}"]

    if analysis_data:
        context_parts.append(f"\n# Аналитический отчёт по потерям в хвостах\n{analysis_data}")

    if image_descriptions:
        imgs_text = "\n".join(f"- {img}" for img in image_descriptions)
        context_parts.append(f"\n# Описания схем и изображений\n{imgs_text}")

    if documents:
        docs_text = "\n\n".join(doc[:3000] for doc in documents[:5])
        context_parts.append(f"\n# Документы пользователя\n{docs_text}")

    if retrieved_text:
        context_parts.append(f"\n# Релевантные данные из базы знаний\n{retrieved_text}")

    context = "\n".join(context_parts)

    # Step 3: Generate hypotheses
    messages = [
        {"role": "system", "content": GENERATOR_SYSTEM},
        {"role": "user", "content": f"{context}\n\nСгенерируй ровно {num} гипотез. Только JSON-массив."},
    ]

    logger.info("agent1_generating", extra={"num": num})
    response = call_llm(messages, temperature=0.8, max_tokens=8000)

    hypotheses = parse_json_from_text(response)
    if isinstance(hypotheses, dict):
        hypotheses = [hypotheses]

    logger.info("agent1_done", extra={"count": len(hypotheses)})
    return hypotheses
