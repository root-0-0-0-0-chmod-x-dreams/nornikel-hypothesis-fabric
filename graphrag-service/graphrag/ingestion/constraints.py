"""Factory constraints: equipment allowlist, budget tiers, regulation & example chunks."""

from __future__ import annotations

from graphrag.ingestion.excel_parser import _slugify
from graphrag.models import Chunk, GraphEdge, GraphNode
from graphrag.schema import NodeType, RelationType

# Оборудование, реально присутствующее на фабрике (из регламентов §6, тезисы_кейс.md)
FACTORY_EQUIPMENT: dict[str, frozenset[str]] = {
    "КГМК": frozenset(
        {
            "equip_mshr",
            "equip_mshc",
            "equip_gc660",
            "equip_fpm",
            "equip_kmd",
            "equip_nelson",
        }
    ),
    "НОФ вкр": frozenset(
        {
            "equip_mshr",
            "equip_mshc",
            "equip_gc660",
            "equip_fpm",
            "equip_kmd",
        }
    ),
    "НОФ мед": frozenset(
        {
            "equip_mshr",
            "equip_mshc",
            "equip_gc660",
            "equip_fpm",
            "equip_kmd",
        }
    ),
    "ТОФ": frozenset(
        {
            "equip_mshr",
            "equip_mshc",
            "equip_gc660",
            "equip_fpm",
        }
    ),
}

BUDGET_TIERS: dict[str, str] = {
    "low": (
        "Бюджет низкий: только операционные изменения без капзатрат — "
        "насадки гидроциклонов 12→8 мм, перераспределение фронта флотации, "
        "дозировки реагентов, pH, время операций, контактные чаны."
    ),
    "medium": (
        "Бюджет средний: модернизация без новых переделов — "
        "замена футеровки МШР/МШЦ, автоматизация подачи воды, "
        "датчики гранулометрии, замена спиралей на ГЦ-660 в отдельных секциях."
    ),
    "high": (
        "Бюджет высокий: капитальные интервенции — "
        "полная замена классификаторов на гидроциклоны, отдельный цикл доизмельчения, "
        "концентратор Нельсона, магнитная сепарация, промежуточная дробилка."
    ),
}

REGULATION_CHUNKS: list[dict] = [
    {
        "factory": "КГМК",
        "title": "Регламент 1 — топология флотации",
        "text": (
            "Cu-флотация КГМК: аэрация (5 машин) → I основная (4) → II основная (4) → "
            "перечистная (2) на ФПМ-16-4К / ФМ-16УМ-4К. Коллективный концентрат → "
            "доизмельчение 90-95% −0.045 мм → пропарка 64-73 °C → Ni-флотация. "
            "Отвальные хвосты β_Ni≈0.105%. Реагенты: ПДН-11 350 г/т, Kx 130, Af 15, Т92 15."
        ),
        "graph_node_ids": ["equip_fpm", "process_flotation", "reagent_pdn"],
    },
    {
        "factory": "КГМК",
        "title": "Схема 5 — измельчение и классификация",
        "text": (
            "ИФЦ КГМК: МШЦ 4.5×6.0, МШР 3.2×3.8, МШРГУ 4.5×6.0; "
            "спирали 1КСП24М / 2КСН24; гидроциклоны ГЦ-660 (батареи 4-2, 5-3, 5-5). "
            "Рычаг: насадки циклонов 12→8 мм для тоньше слива."
        ),
        "graph_node_ids": ["equip_mshr", "equip_mshc", "equip_gc660", "process_comminution"],
    },
    {
        "factory": None,
        "title": "Физический потолок — извлекаемый металл",
        "text": (
            "Hard-constraint: гипотеза не может обещать извлечение из "
            "силикатной формы/валлериита и примеси Ni в решётке пирротина сверх доли "
            "«извлекаемого металла» в Excel. recoverable=false → блок интервенций флотацией."
        ),
        "graph_node_ids": ["mineral_silicate_valleriite", "mineral_pyrrhotite_impurity"],
    },
]

EXAMPLE_HYPOTHESES: list[dict] = [
    {
        "factory": "КГМК",
        "text": (
            "Эталон H-КГМК-1: магнитная сепарация целевого класса + доизмельчение "
            "в отдельном цикле для закрытого пентландита в крупных классах."
        ),
        "graph_node_ids": ["mech_liberation", "process_comminution", "equip_mshr"],
        "budget_tier": "high",
    },
    {
        "factory": "КГМК",
        "text": (
            "Эталон H-КГМК-3: замена песковых насадок гидроциклонов 12→8 мм — "
            "тоньше слив, меньше крупняка в хвостах. Бюджет: low."
        ),
        "graph_node_ids": ["equip_gc660", "process_classification"],
        "budget_tier": "low",
    },
    {
        "factory": "НОФ вкр",
        "text": (
            "Эталон H-НОФ-5: замена насадок классификаторов, контроль возвратной нагрузки. "
            "Адресует закрытый Pnt в +125."
        ),
        "graph_node_ids": ["equip_gc660", "process_classification"],
        "budget_tier": "low",
    },
    {
        "factory": "НОФ мед",
        "text": (
            "Эталон H-НОФмед-6: реагент Finfix 300 в контактные чаны — "
            "рост времени агитации перед контрольной флотацией."
        ),
        "graph_node_ids": ["equip_fpm", "process_flotation"],
        "budget_tier": "low",
    },
    {
        "factory": "ТОФ",
        "text": (
            "Эталон H-ТОФ-6: замена спиральных классификаторов на гидроциклоны ГЦ-660."
        ),
        "graph_node_ids": ["equip_gc660", "process_classification"],
        "budget_tier": "medium",
    },
]


def build_constraint_chunks() -> list[Chunk]:
    chunks: list[Chunk] = []

    for tier, text in BUDGET_TIERS.items():
        chunks.append(
            Chunk(
                chunk_id=_slugify("constraint", "budget", tier),
                text=text,
                summary=f"Ограничение бюджета: {tier}",
                source="constraints/budget",
                chunk_type="constraint_budget",
                graph_node_ids=[],
                metadata={"budget_tier": tier},
            )
        )

    for index, item in enumerate(REGULATION_CHUNKS):
        chunks.append(
            Chunk(
                chunk_id=_slugify("constraint", "regulation", str(index), item["title"][:24]),
                text=item["text"],
                summary=item["title"],
                source=item["title"],
                factory=item.get("factory"),
                chunk_type="constraint_regulation",
                graph_node_ids=list(item.get("graph_node_ids") or []),
            )
        )

    for index, item in enumerate(EXAMPLE_HYPOTHESES):
        chunks.append(
            Chunk(
                chunk_id=_slugify("constraint", "example", item["factory"], str(index)),
                text=item["text"],
                summary=f"Пример гипотезы ({item['factory']})",
                source="constraints/examples",
                factory=item["factory"],
                chunk_type="constraint_example",
                graph_node_ids=list(item.get("graph_node_ids") or []),
                metadata={"budget_tier": item.get("budget_tier")},
            )
        )

    return chunks


def build_factory_equipment_edges(
    nodes_by_id: dict[str, GraphNode],
) -> list[GraphEdge]:
    edges: list[GraphEdge] = []
    edge_keys: set[tuple[str, str, str]] = set()

    for factory, equipment_ids in FACTORY_EQUIPMENT.items():
        factory_id = _slugify("factory", factory)

        if factory_id not in nodes_by_id:
            nodes_by_id[factory_id] = GraphNode(
                node_id=factory_id,
                node_type=NodeType.FACTORY,
                label=factory,
                attributes={"factory": factory},
            )

        for equip_id in equipment_ids:
            key = (factory_id, RelationType.HAS_EQUIPMENT, equip_id)

            if key in edge_keys:
                continue

            edge_keys.add(key)
            edges.append(GraphEdge(factory_id, equip_id, RelationType.HAS_EQUIPMENT))

    return edges


def factory_equipment_ids(factory: str | None) -> frozenset[str]:
    if not factory:
        return frozenset()

    return FACTORY_EQUIPMENT.get(factory, frozenset())


def filter_nodes_by_factory_equipment(
    node_ids: list[str],
    factory: str | None,
) -> list[str]:
    """Drop catalog equipment not installed on this factory."""
    allowed = factory_equipment_ids(factory)

    if not allowed:
        return node_ids

    return [
        node_id
        for node_id in node_ids
        if not node_id.startswith("equip_") or node_id in allowed
    ]
