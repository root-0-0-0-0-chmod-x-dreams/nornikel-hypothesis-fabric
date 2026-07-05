"""Resolve catalog entity ids from free-text Russian questions."""

from __future__ import annotations

import re

from graphrag.ingestion.pdf_graph_linker import (
    EQUIPMENT_HINTS,
    MECHANISM_HINTS,
    METAL_HINTS,
    MINERAL_HINTS,
    PROCESS_HINTS,
    REAGENT_HINTS,
)

_NODE_ID_RE = re.compile(
    r"\b("
    r"lossform_[\w+]+|mech_\w+|equip_\w+|process_\w+|"
    r"mineral_\w+|reagent_\w+|metal_\w+|source_\w+"
    r")\b",
    re.IGNORECASE,
)

_CATALOG_MAPS: tuple[dict[str, tuple[str, ...]], ...] = (
    EQUIPMENT_HINTS,
    MECHANISM_HINTS,
    PROCESS_HINTS,
    MINERAL_HINTS,
    REAGENT_HINTS,
    METAL_HINTS,
)


def resolve_entity_id(text_lower: str) -> str | None:
    """Best-effort entity id from explicit id or domain keywords."""
    direct = _NODE_ID_RE.search(text_lower)

    if direct:
        return direct.group(1).lower()

    for catalog in _CATALOG_MAPS:
        for node_id, keywords in catalog.items():
            if any(keyword in text_lower for keyword in keywords):
                return node_id

    return None


def resolve_search_tokens(text_lower: str) -> list[str]:
    """Keywords useful for CONTAINS search in Cypher."""
    tokens: list[str] = []

    for catalog in _CATALOG_MAPS:
        for node_id, keywords in catalog.items():
            if any(keyword in text_lower for keyword in keywords):
                tokens.append(node_id)
                tokens.extend(keywords[:2])

    if not tokens:
        # strip question words, keep substantive tokens
        stripped = re.sub(
            r"\b(что|как|где|какой|какие|покажи|найди|сколько|всего|для|на|по|с|из)\b",
            " ",
            text_lower,
        )
        tokens = [word for word in stripped.split() if len(word) > 3][:5]

    return tokens[:8]
