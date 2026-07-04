"""Mineral forms, equipment catalog, intervention routing."""

from __future__ import annotations

from graphrag.constants import (
    COARSE_SIZE_CLASSES,
    FINE_SIZE_CLASS,
    METAL_CU,
    METAL_ELEMENT_28,
    METAL_ELEMENT_29,
    METAL_NI,
)
from graphrag.schema import NodeType, RelationType

MINERAL_FORM_LABELS: tuple[str, ...] = (
    "Раскрытый Pnt/Cp",
    "Закрытый Pnt/Cp",
    "Примесь в пирротине ",
    "Силикатная форма/Валлериит",
    "Пирит/Другие Элемент 29 сульфиды",
    "Миллерит",
)

FORM_SLUG: dict[str, str] = {
    "Раскрытый Pnt/Cp": "open_pnt_cp",
    "Закрытый Pnt/Cp": "closed_pnt_cp",
    "Примесь в пирротине ": "pyrrhotite_impurity",
    "Силикатная форма/Валлериит": "silicate_valleriite",
    "Пирит/Другие Элемент 29 сульфиды": "pyrite",
    "Миллерит": "millerite",
}

RECOVERABLE_FORMS_NI: frozenset[str] = frozenset(
    {"open_pnt_cp", "closed_pnt_cp", "millerite"}
)
RECOVERABLE_FORMS_CU: frozenset[str] = frozenset({"open_pnt_cp", "closed_pnt_cp"})

EQUIPMENT_CATALOG: tuple[tuple[str, str, str], ...] = (
    ("equip_mshr", "МШР 3.2×3.8", NodeType.EQUIPMENT),
    ("equip_mshc", "МШЦ 4.5×6.0", NodeType.EQUIPMENT),
    ("equip_gc660", "ГЦ-660", NodeType.EQUIPMENT),
    ("equip_fpm", "ФПМ-16-4К", NodeType.EQUIPMENT),
    ("equip_kmd", "КМД 2200Т", NodeType.EQUIPMENT),
    ("equip_nelson", "Концентратор Нельсона", NodeType.EQUIPMENT),
)

PROCESS_CATALOG: tuple[tuple[str, str, str], ...] = (
    ("process_comminution", "Доизмельчение", NodeType.PROCESS),
    ("process_classification", "Классификация", NodeType.PROCESS),
    ("process_flotation", "Флотация", NodeType.PROCESS),
    ("process_slime_flotation", "Флотация шламов", NodeType.PROCESS),
)

MECHANISM_CATALOG: tuple[tuple[str, str, str], ...] = (
    ("mech_liberation", "Раскрытие сростков", NodeType.MECHANISM),
    ("mech_slime_recovery", "Флотация шламов", NodeType.MECHANISM),
    ("mech_millerite_activation", "Активация миллерита", NodeType.MECHANISM),
)

FORM_LABEL_BY_SLUG: dict[str, str] = {
    slug: label.strip() for label, slug in FORM_SLUG.items()
}

CATALOG_PROCESS_EQUIPMENT: tuple[tuple[str, str], ...] = (
    ("process_comminution", "equip_mshr"),
    ("process_comminution", "equip_mshc"),
    ("process_comminution", "equip_gc660"),
    ("process_comminution", "equip_kmd"),
    ("process_classification", "equip_gc660"),
    ("process_flotation", "equip_fpm"),
    ("process_slime_flotation", "equip_fpm"),
)

CATALOG_MECHANISM_PROCESS: tuple[tuple[str, str], ...] = (
    ("mech_liberation", "process_comminution"),
    ("mech_slime_recovery", "process_slime_flotation"),
    ("mech_millerite_activation", "process_flotation"),
)


def normalize_size_class(raw: str) -> str:
    text = raw.strip().replace("мкм", "").strip()

    return " ".join(text.split())


def is_coarse_class(size_class: str) -> bool:
    normalized = normalize_size_class(size_class)

    return normalized in COARSE_SIZE_CLASSES or normalized in ("+125", "+71")


def is_fine_class(size_class: str) -> bool:
    return normalize_size_class(size_class) == FINE_SIZE_CLASS


def metal_from_column_header(header: str) -> str | None:
    if METAL_ELEMENT_28 in header or ", т" in header and "28" in header:
        return METAL_NI

    if METAL_ELEMENT_29 in header or ", т" in header and "29" in header:
        return METAL_CU

    return None


def is_recoverable_form(form_slug: str, metal: str) -> bool:
    if metal == METAL_NI:
        return form_slug in RECOVERABLE_FORMS_NI

    if metal == METAL_CU:
        return form_slug in RECOVERABLE_FORMS_CU

    return False


def intervention_edges_for_bucket(
    *,
    bucket_node_id: str,
    form_slug: str,
    size_class: str,
    metal: str,
    recoverable: bool,
) -> list[tuple[str, str, str]]:
    """Return (source, relation, target) edges for graph wiring."""
    if not recoverable:
        return []

    edges: list[tuple[str, str, str]] = []

    if form_slug == "closed_pnt_cp" and is_coarse_class(size_class):
        edges.extend(
            [
                (bucket_node_id, RelationType.EXPLAINED_BY, "mech_liberation"),
                ("mech_liberation", RelationType.ADDRESSED_BY, "process_comminution"),
                ("process_comminution", RelationType.USES_EQUIPMENT, "equip_mshr"),
                ("process_comminution", RelationType.USES_EQUIPMENT, "equip_gc660"),
            ]
        )

    if form_slug == "open_pnt_cp" and is_fine_class(size_class):
        edges.extend(
            [
                (bucket_node_id, RelationType.EXPLAINED_BY, "mech_slime_recovery"),
                (
                    "mech_slime_recovery",
                    RelationType.ADDRESSED_BY,
                    "process_slime_flotation",
                ),
                (
                    "process_slime_flotation",
                    RelationType.USES_EQUIPMENT,
                    "equip_fpm",
                ),
            ]
        )

    if form_slug == "millerite" and metal == METAL_NI:
        edges.extend(
            [
                (
                    bucket_node_id,
                    RelationType.EXPLAINED_BY,
                    "mech_millerite_activation",
                ),
                (
                    "mech_millerite_activation",
                    RelationType.ADDRESSED_BY,
                    "process_flotation",
                ),
            ]
        )

    return edges
