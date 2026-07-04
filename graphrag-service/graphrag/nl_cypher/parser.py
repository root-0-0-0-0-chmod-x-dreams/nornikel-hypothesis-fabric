"""Parse Russian natural language into structured graph query intents."""

from __future__ import annotations

import re

from graphrag.constants import METAL_CU, METAL_NI
from graphrag.ingestion.excel_parser import _slugify
from graphrag.nl_cypher.models import ParsedQuery, QueryIntent
from graphrag.nl_cypher.slots import resolve_entity_id, resolve_search_tokens

_FACTORY_ALIASES: tuple[tuple[str, str], ...] = (
    ("кгмк", "КГМК"),
    ("ноф вкр", "НОФ вкр"),
    ("ноф мед", "НОФ мед"),
    ("ноф", "НОФ вкр"),
    ("тоф", "ТОФ"),
)

_FORM_HINTS: tuple[tuple[str, str], ...] = (
    ("закрыт", "closed_pnt_cp"),
    ("closed", "closed_pnt_cp"),
    ("раскрыт", "open_pnt_cp"),
    ("open", "open_pnt_cp"),
    ("миллерит", "millerite"),
    ("пирротин", "pyrrhotite_impurity"),
    ("силикат", "silicate_valleriite"),
    ("валлериит", "silicate_valleriite"),
    ("пирит", "pyrite"),
    ("пентландит", "closed_pnt_cp"),
)

_NODE_TYPE_HINTS: tuple[tuple[str, str], ...] = (
    ("оборудован", "Equipment"),
    ("аппарат", "Equipment"),
    ("процесс", "Process"),
    ("передел", "Process"),
    ("механизм", "Mechanism"),
    ("реагент", "Reagent"),
    ("источник", "Source"),
    ("литератур", "Source"),
)

_SIZE_RE = re.compile(r"(?:класс[еа]?\s*)?([+-]?\d+(?:\s*\+\s*\d+)?)", re.IGNORECASE)


def parse_question(question: str) -> ParsedQuery:
    text = question.strip()
    lower = text.lower()
    params = _extract_params(lower, text)

    intent = _classify_intent(lower, params)
    limit = (
        5 if intent in (QueryIntent.TOP_LOSSES, QueryIntent.RECOVERABLE_LOSSES) else 10
    )

    return ParsedQuery(
        intent=intent,
        question=text,
        limit=limit,
        **params,
    )


def build_bucket_id(parsed: ParsedQuery) -> str | None:
    if parsed.entity_id and parsed.entity_id.startswith("lossform_"):
        return parsed.entity_id

    if not all((parsed.factory, parsed.size_class, parsed.form_slug, parsed.metal)):
        return None

    return _slugify(
        "lossform",
        parsed.factory,
        parsed.size_class,
        parsed.form_slug,
        parsed.metal,
    )


def _extract_params(lower: str, original: str) -> dict[str, str | None]:
    factory = _match_alias(lower, _FACTORY_ALIASES)
    metal = _extract_metal(lower)
    form_slug = _match_alias(lower, _FORM_HINTS)
    size_class = _extract_size(lower)
    node_type = _match_alias(lower, _NODE_TYPE_HINTS)
    entity_id = resolve_entity_id(lower)

    if "пентландит" in lower and form_slug is None:
        form_slug = "closed_pnt_cp"

    if metal is None and any(word in lower for word in ("никел", "ni ", "ni,")):
        metal = METAL_NI

    if metal is None and any(word in lower for word in ("мед", "cu ", "cu,")):
        metal = METAL_CU

    if metal is None and "пентландит" in lower:
        metal = METAL_NI

    search_text = None
    tokens = resolve_search_tokens(lower)

    if tokens:
        search_text = tokens[0]

    for token in ("мшр", "мшц", "гц-660", "гц 660", "фпм", "нельсон", "кмд", "кмп"):
        if token in lower:
            search_text = token
            break

    if search_text is None and len(original.strip()) > 3:
        search_text = original.strip()

    return {
        "factory": factory,
        "metal": metal,
        "form_slug": form_slug,
        "size_class": size_class,
        "node_type": node_type,
        "search_text": search_text,
        "entity_id": entity_id,
    }


def _classify_intent(lower: str, params: dict[str, str | None]) -> QueryIntent:
    if any(word in lower for word in ("сколько", "статистик", "count", "всего узл")):
        if any(word in lower for word in ("связ", "ребр", "рёбер", "edge")):
            return QueryIntent.EDGE_STATS

        return QueryIntent.STATS

    if any(
        word in lower
        for word in (
            "литератур",
            "источник",
            "подтвержд",
            "evidenced",
            "pdf",
            "доказатель",
            "ссылк",
        )
    ):
        return QueryIntent.LITERATURE_EVIDENCE

    if any(
        word in lower
        for word in ("сосед", "связан", "окруж", "neighbors", "с чем связ")
    ):
        return QueryIntent.NEIGHBORS

    if any(
        word in lower
        for word in (
            "оборудован",
            "аппарат",
            "машин",
        )
    ) and any(
        word in lower
        for word in ("процесс", "передел", "измельч", "флотац", "классиф", "дроблен")
    ):
        return QueryIntent.PROCESS_EQUIPMENT

    if any(
        word in lower
        for word in (
            "интервен",
            "что делать",
            "как снизить",
            "как уменьшить",
            "мер",
            "доизмельч",
            "цепочк",
            "swanson",
            "путь",
            "куда вмеш",
        )
    ):
        return QueryIntent.INTERVENTION_PATH

    if any(
        word in lower
        for word in ("топ", "больше всего", "максимальн", "крупнейш", "самые больш")
    ):
        return QueryIntent.TOP_LOSSES

    if any(word in lower for word in ("извлекаем", "recoverable", "можно извлечь")):
        return QueryIntent.RECOVERABLE_LOSSES

    if any(word in lower for word in ("по фабрик", "разбивк", "фабрикам")):
        return QueryIntent.FACTORY_BREAKDOWN

    if params.get("search_text") and any(
        word in lower for word in ("найди", "найти", "поиск")
    ):
        return QueryIntent.SEARCH_NODES

    if params.get("entity_id") and not params.get("factory"):
        return QueryIntent.NEIGHBORS

    if params.get("search_text") or any(
        word in lower for word in ("найди", "найти", "поиск")
    ):
        return QueryIntent.SEARCH_NODES

    if params.get("node_type") and any(
        word in lower for word in ("список", "все", "покажи", "какие")
    ):
        return QueryIntent.LIST_BY_TYPE

    if all(params.get(key) for key in ("factory", "size_class", "form_slug", "metal")):
        return QueryIntent.INTERVENTION_PATH

    if params.get("factory") or params.get("metal") or params.get("form_slug"):
        return QueryIntent.BUCKET_LOOKUP

    if params.get("node_type"):
        return QueryIntent.LIST_BY_TYPE

    return QueryIntent.SEARCH_NODES


def _match_alias(lower: str, aliases: tuple[tuple[str, str], ...]) -> str | None:
    for needle, value in aliases:
        if needle in lower:
            return value

    return None


def _extract_metal(lower: str) -> str | None:
    if any(word in lower for word in ("никел", "ni", "элемент 28", "элемент28")):
        return METAL_NI

    if any(word in lower for word in ("мед", "cu", "элемент 29", "элемент29")):
        return METAL_CU

    return None


def _extract_size(lower: str) -> str | None:
    match = _SIZE_RE.search(lower)

    if not match:
        return None

    raw = match.group(1).replace(" ", "")

    if "+" in raw and not raw.startswith(("+", "-")):
        return "+" + raw.replace("+", "+", 1)

    return raw
