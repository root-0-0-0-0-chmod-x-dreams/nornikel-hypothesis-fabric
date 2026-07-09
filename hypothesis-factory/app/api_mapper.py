"""Map hypothesis-factory internal models → frontend API contract."""

from __future__ import annotations

import re
from typing import Any

from app.sources import knowledge_sources_to_api


def _novelty(raw: str | None) -> str:
    v = (raw or "medium").lower()
    if v in ("high", "medium", "low"):
        return v
    return "medium"


def hypothesis_to_api(hyp: dict[str, Any], index: int) -> dict[str, Any]:
    actor = hyp.get("actor_validation") or {}
    judge = hyp.get("judge_evaluation") or {}
    actor_sources = actor.get("sources") or []
    refs = hyp.get("references") or []
    knowledge_sources = hyp.get("knowledge_sources") or []

    sources: list[str] = list(refs)
    for s in actor_sources:
        if isinstance(s, dict):
            parts = [s.get("type"), s.get("title"), s.get("relevance")]
            line = " — ".join(p for p in parts if p)
            if line:
                sources.append(line)

    for ks in knowledge_sources:
        title = ks.get("title")
        if title and title not in sources:
            sources.append(str(title))

    source_details = knowledge_sources_to_api(knowledge_sources)
    if not source_details:
        source_details = [{"title": s, "type": "reference"} for s in sources]

    risks = actor.get("risks") or {}
    final_score = float(judge.get("final_score") or 0)
    confidence = min(1.0, final_score / 5.0) if final_score else 0.7

    return {
        "id": hyp.get("id") or f"h{index + 1}",
        "title": hyp.get("title") or f"Гипотеза {index + 1}",
        "description": hyp.get("description") or "",
        "rationale": hyp.get("rationale") or actor.get("justification") or "",
        "mechanism": hyp.get("mechanism") or actor.get("mechanism_detail") or "",
        "expectedValue": hyp.get("expected_impact") or actor.get("expected_kpi_impact") or "",
        "novelty": _novelty(hyp.get("novelty")),
        "noveltyRationale": actor.get("novelty_assessment") or "",
        "confidence": confidence,
        "sources": sources or ["GraphRAG / внутренние документы"],
        "sourceDetails": source_details,
        "risks": {
            "technical": risks.get("technical") or "Не оценено",
            "economic": risks.get("economic") or "Не оценено",
        },
    }


def _parse_roadmap_steps(text: str) -> list[dict[str, Any]] | None:
    """Parse numbered experiment roadmap lines into steps."""
    steps: list[dict[str, Any]] = []
    order = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = re.match(r"^(\d+)[.)]\s*(.+)", line)
        if not match:
            continue
        order += 1
        body = match.group(2).strip()
        steps.append(
            {
                "id": f"s{order}",
                "order": order,
                "title": body[:120],
                "description": body,
                "resources": "—",
                "duration": "—",
                "successCriteria": "—",
                "failureCriteria": "—",
                "status": "pending",
            }
        )
    return steps if steps else None


def _attach_sources_to_steps(steps: list[dict[str, Any]], source_details: list[dict[str, Any]]) -> None:
    if not source_details:
        return
    for i, step in enumerate(steps):
        primary = source_details[i % len(source_details)]
        secondary = source_details[(i + 1) % len(source_details)] if len(source_details) > 1 else None
        step_sources = [primary]
        if secondary and secondary.get("chunkId") != primary.get("chunkId"):
            step_sources.append(secondary)
        step["sourceDetails"] = step_sources


def roadmap_from_hypothesis(hyp: dict[str, Any], hypothesis_id: str) -> dict[str, Any]:
    actor = hyp.get("actor_validation") or {}
    text = str(actor.get("experiment_roadmap") or "")
    knowledge_sources = hyp.get("knowledge_sources") or []
    source_details = knowledge_sources_to_api(knowledge_sources)

    parsed_steps = _parse_roadmap_steps(text) if text else None
    default_steps = parsed_steps or [
        {
            "id": "s1",
            "order": 1,
            "title": "Отбор пробы",
            "description": "Отбор репрезентативной пробы для лабораторных испытаний",
            "resources": "Пробоотборник, аналитическая лаборатория",
            "duration": "3–5 дней",
            "successCriteria": "Проба соответствует целевому составу",
            "failureCriteria": "Нерепрезентативная проба",
            "status": "pending",
        },
        {
            "id": "s2",
            "order": 2,
            "title": "Лабораторная проверка",
            "description": text[:500] if text else "Проверка гипотезы в лабораторных условиях",
            "resources": "Лабораторное оборудование",
            "duration": "1–2 недели",
            "successCriteria": "Подтверждение ожидаемого эффекта",
            "failureCriteria": "Эффект ниже порога значимости",
            "status": "pending",
        },
        {
            "id": "s3",
            "order": 3,
            "title": "Анализ и отчёт",
            "description": "Статистическая обработка результатов, TECHNO-ECON отчёт",
            "resources": "Аналитик",
            "duration": "1 неделя",
            "successCriteria": "Отчёт готов, p < 0.05",
            "failureCriteria": "Нет статистической значимости",
            "status": "pending",
        },
    ]

    _attach_sources_to_steps(default_steps, source_details)

    return {
        "hypothesisId": hypothesis_id,
        "totalDuration": "4–6 недель" if not parsed_steps else f"{len(default_steps)} этапов",
        "totalResources": "Лаборатория, реагенты, аналитика",
        "steps": default_steps,
        "sourceDetails": source_details,
    }
