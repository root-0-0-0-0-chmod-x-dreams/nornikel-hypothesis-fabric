"""Domain query expansion for mining / flotation terminology."""

from __future__ import annotations

import re

from graphrag.ingestion.domain import (
    EQUIPMENT_CATALOG,
    FORM_LABEL_BY_SLUG,
    MECHANISM_CATALOG,
    PROCESS_CATALOG,
)

# token/phrase -> extra search terms (lowercase)
_DOMAIN_EXPANSIONS: dict[str, tuple[str, ...]] = {
    "мшр": ("шаровая мельница", "доизмельчение", "измельчение"),
    "мшц": ("цилиндрическая мельница", "измельчение"),
    "гц-660": ("гидроциклон", "классификация", "гц 660"),
    "гц 660": ("гидроциклон", "классификация"),
    "фпм": ("флотомашина", "флотация"),
    "кмд": ("дробилка", "дробление"),
    "пентландит": ("закрытый пентландит", "раскрытый пентландит", "сростки"),
    "миллерит": ("активация", "сульфид"),
    "шлам": ("тонкий класс", "минус 10", "флотация шламов"),
    "-10": ("тонкий класс", "шлам", "флотация шламов"),
    "пдн": ("собиратель", "флотация"),
    "ни": ("никель", "элемент 28"),
    "cu": ("медь", "элемент 29"),
    "никель": ("ni", "элемент 28"),
    "медь": ("cu", "элемент 29"),
}

_TOKEN_PATTERN = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9]+(?:[-+]\d+)?")


def _catalog_expansions() -> dict[str, tuple[str, ...]]:
    extra: dict[str, set[str]] = {}

    for _node_id, label, _type in (
        *EQUIPMENT_CATALOG,
        *PROCESS_CATALOG,
        *MECHANISM_CATALOG,
    ):
        key = label.lower()
        tokens = _TOKEN_PATTERN.findall(key)

        for token in tokens:
            if len(token) < 3:
                continue

            extra.setdefault(token, set()).add(label.lower())

    return {key: tuple(sorted(values)) for key, values in extra.items()}


_CATALOG_EXPANSIONS = _catalog_expansions()


def expand_query(query: str, *, max_terms: int = 12) -> str:
    """Append domain synonyms; keeps original question intact."""
    lowered = query.lower()
    tokens = set(_TOKEN_PATTERN.findall(lowered))
    additions: list[str] = []

    for token in tokens:
        for source in (token, lowered):
            for synonym in _DOMAIN_EXPANSIONS.get(source, ()):
                if synonym not in lowered and synonym not in additions:
                    additions.append(synonym)

        for synonym in _CATALOG_EXPANSIONS.get(token, ()):
            if synonym not in lowered and synonym not in additions:
                additions.append(synonym)

    if not additions:
        return query

    return f"{query} {' '.join(additions[:max_terms])}"


def mineral_label(slug: str) -> str:
    return FORM_LABEL_BY_SLUG.get(slug, slug.replace("_", " "))
