"""Turn Cypher rows into human-readable Russian answers."""

from __future__ import annotations

from graphrag.nl_cypher.models import ParsedQuery, QueryIntent


def format_answer(parsed: ParsedQuery, rows: list[dict], bucket_id: str | None) -> str:
    formatters = {
        QueryIntent.STATS: _format_stats,
        QueryIntent.FACTORY_BREAKDOWN: _format_factory_breakdown,
        QueryIntent.TOP_LOSSES: _format_top_losses,
        QueryIntent.BUCKET_LOOKUP: _format_bucket_lookup,
        QueryIntent.INTERVENTION_PATH: _format_intervention_path,
        QueryIntent.SEARCH_NODES: _format_search_nodes,
        QueryIntent.LIST_BY_TYPE: _format_list_by_type,
        QueryIntent.RECOVERABLE_LOSSES: _format_top_losses,
        QueryIntent.LITERATURE_EVIDENCE: _format_literature,
        QueryIntent.NEIGHBORS: _format_neighbors,
        QueryIntent.EDGE_STATS: _format_edge_stats,
        QueryIntent.PROCESS_EQUIPMENT: _format_process_equipment,
    }
    formatter = formatters[parsed.intent]

    return formatter(parsed, rows, bucket_id)


def _format_stats(
    _parsed: ParsedQuery, rows: list[dict], _bucket_id: str | None
) -> str:
    if not rows:
        return "Граф пуст — сначала выполните make neo4j-seed."

    row = rows[0]
    return (
        f"В графе {row.get('nodes', 0)} узлов, {row.get('edges', 0)} связей "
        f"и {row.get('loss_forms', 0)} форм потерь (LossForm)."
    )


def _format_factory_breakdown(
    _parsed: ParsedQuery, rows: list[dict], _bucket_id: str | None
) -> str:
    if not rows:
        return "Формы потерь не найдены."

    lines = ["Потери по фабрикам:"]
    for row in rows:
        lines.append(
            f"• {row.get('factory')}: {row.get('buckets')} bucket-ов, "
            f"суммарно {row.get('total_tonnes')} т"
        )

    return "\n".join(lines)


def _format_top_losses(
    parsed: ParsedQuery, rows: list[dict], _bucket_id: str | None
) -> str:
    if not rows:
        scope = _scope_label(parsed)
        return f"Потери не найдены{scope}."

    lines = [f"Топ потерь{ _scope_label(parsed) }:"]
    for index, row in enumerate(rows, start=1):
        recoverable = "извлекаемо" if row.get("recoverable") else "неизвлекаемо"
        lines.append(
            f"{index}. {row.get('label')} — {row.get('tonnes')} т ({recoverable})"
        )

    return "\n".join(lines)


def _format_bucket_lookup(
    _parsed: ParsedQuery, rows: list[dict], bucket_id: str | None
) -> str:
    if not rows:
        return (
            "Bucket не найден. Уточните фабрику, класс крупности, "
            "форму минерала и металл."
        )

    row = rows[0]
    recoverable = "да" if row.get("recoverable") else "нет"
    lines = [
        f"Bucket: {row.get('label')}",
        f"Потери: {row.get('tonnes')} т {row.get('metal')}",
        f"Извлекаемо: {recoverable}",
        f"Фабрика: {row.get('factory')}, класс: {row.get('size_class')}",
    ]

    if bucket_id:
        lines.append(f"ID: {bucket_id}")

    return "\n".join(lines)


def _format_intervention_path(
    _parsed: ParsedQuery, rows: list[dict], bucket_id: str | None
) -> str:
    if not rows:
        return (
            "Не удалось построить цепочку интервенции. "
            "Укажите фабрику, класс (+71), форму (закрытый пентландит) и металл."
        )

    head = rows[0]
    lines = [
        f"Bucket: {head.get('bucket_label')} — {head.get('tonnes')} т",
        f"Извлекаемо: {'да' if head.get('recoverable') else 'нет'}",
    ]

    if bucket_id:
        lines.append(f"ID: {bucket_id}")

    targets: dict[str, str] = {}
    for row in rows:
        target_id = row.get("target_id")
        target_label = row.get("target_label")
        target_type = row.get("target_type")

        if target_id and target_label:
            targets[target_id] = f"[{target_type}] {target_label}"

    if targets:
        lines.append("")
        lines.append("Цепочка интервенции (Swanson ABC):")
        for node_id, label in sorted(targets.items(), key=lambda item: item[0]):
            lines.append(f"→ {label} ({node_id})")
    else:
        lines.append("")
        lines.append("Для этого bucket интервенция в графе не размечена.")

    return "\n".join(lines)


def _format_search_nodes(
    _parsed: ParsedQuery, rows: list[dict], _bucket_id: str | None
) -> str:
    if not rows:
        return "Ничего не найдено по запросу."

    lines = ["Найденные узлы:"]
    for row in rows:
        lines.append(
            f"• [{row.get('node_type')}] {row.get('label')} — {row.get('node_id')}"
        )

    return "\n".join(lines)


def _format_list_by_type(
    parsed: ParsedQuery, rows: list[dict], _bucket_id: str | None
) -> str:
    node_type = parsed.node_type or "Equipment"

    if not rows:
        return f"Узлы типа {node_type} не найдены."

    lines = [f"Узлы типа {node_type}:"]
    for row in rows:
        lines.append(f"• {row.get('label')} — {row.get('node_id')}")

    return "\n".join(lines)


def _scope_label(parsed: ParsedQuery) -> str:
    parts: list[str] = []

    if parsed.factory:
        parts.append(parsed.factory)

    if parsed.metal:
        parts.append(parsed.metal)

    if parsed.form_slug:
        parts.append(parsed.form_slug)

    if parsed.size_class:
        parts.append(parsed.size_class)

    if not parts:
        return ""

    return f" ({', '.join(parts)})"


def build_hints(parsed: ParsedQuery) -> list[str]:
    return [
        "Примеры вопросов:",
        "• где больше всего теряется никель на КГМК",
        "• что делать с закрытым пентландитом в классе +71 на КГМК",
        "• извлекаемые потери меди на ТОФ",
        "• покажи всё оборудование",
        "• найди МШР",
        "• какая литература подтверждает раскрытие пентландита",
        "• с чем связан mech_liberation",
        "• какое оборудование на измельчение",
        "• сколько связей в графе по типам",
        "• статистика графа",
        f"Распознан intent: {parsed.intent}",
        f"entity_id: {parsed.entity_id or '—'}",
    ]


def _format_literature(
    _parsed: ParsedQuery, rows: list[dict], _bucket_id: str | None
) -> str:
    if not rows:
        return "Литературных ссылок (EVIDENCED_BY) для этой сущности не найдено."

    lines = ["Источники, подтверждающие сущность:"]
    for row in rows:
        page = row.get("page")
        page_suffix = f", стр. {page}" if page else ""
        lines.append(
            f"• {row.get('entity_label')} ← {row.get('source_label')}{page_suffix}"
        )

    return "\n".join(lines)


def _format_neighbors(
    _parsed: ParsedQuery, rows: list[dict], _bucket_id: str | None
) -> str:
    if not rows:
        return "Соседей не найдено — проверьте node_id или уточните запрос."

    center = rows[0].get("center_label") or rows[0].get("center_id")
    lines = [f"Соседи узла {center}:"]

    for row in rows:
        if not row.get("neighbor_id"):
            continue

        direction = "→" if row.get("direction") == "out" else "←"
        lines.append(
            f"{direction} [{row.get('relation')}] "
            f"[{row.get('neighbor_type')}] {row.get('neighbor_label')}"
        )

    return "\n".join(lines)


def _format_edge_stats(
    _parsed: ParsedQuery, rows: list[dict], _bucket_id: str | None
) -> str:
    if not rows:
        return "Граф пуст."

    lines = ["Связи по типам:"]
    for row in rows[:20]:
        lines.append(f"• {row.get('relation')}: {row.get('edges')}")

    return "\n".join(lines)


def _format_process_equipment(
    _parsed: ParsedQuery, rows: list[dict], _bucket_id: str | None
) -> str:
    if not rows:
        return "Оборудование для указанного процесса не найдено."

    lines = ["Оборудование по процессам:"]
    for row in rows:
        lines.append(
            f"• {row.get('process_label')}: {row.get('equipment_label')} "
            f"({row.get('equipment_id')})"
        )

    return "\n".join(lines)
