from datetime import datetime, timezone


def generate_final_report(
    query: str,
    hypotheses: list[dict],
    rejected: list[dict],
    analysis_data: str,
    request_id: str,
) -> str:
    """Generate the final markdown report with roadmap, sources, and metrics."""

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        f"# Отчёт: Фабрика гипотез",
        f"",
        f"**ID запроса:** `{request_id}`",
        f"**Дата генерации:** {now}",
        f"**Запрос:** {query}",
        f"",
        f"## Сводка",
        f"",
        f"| Метрика | Значение |",
        f"|:--------|:---------|",
        f"| Сгенерировано гипотез | {len(hypotheses) + len(rejected)} |",
        f"| Прошли валидацию | {len(hypotheses)} |",
        f"| Отклонено | {len(rejected)} |",
        f"",
    ]

    if analysis_data:
        lines += [
            f"## Данные анализа потерь",
            f"",
            f"```csv",
            analysis_data.strip(),
            f"```",
            f"",
        ]

    if hypotheses:
        lines.append(f"## Принятые гипотезы ({len(hypotheses)})")
        lines.append("")

        for i, hyp in enumerate(hypotheses, 1):
            title = hyp.get("title", f"Гипотеза {i}")
            lines += [
                f"### {i}. {title}",
                f"",
                f"**Описание:** {hyp.get('description', '—')}",
                f"",
                f"**Обоснование:** {hyp.get('rationale', '—')}",
                f"",
                f"**Механизм влияния:** {hyp.get('mechanism', '—')}",
                f"",
                f"**Ожидаемый эффект:** {hyp.get('expected_impact', '—')}",
                f"",
                f"**Категория:** {hyp.get('category', '—')}",
                f"**Новизна:** {hyp.get('novelty', '—')}",
                f"",
            ]

            # Actor validation
            actor = hyp.get("actor_validation", {})
            if actor:
                lines += [
                    f"### Обоснование (Actor)",
                    f"",
                    f"**Заключение:** {actor.get('justification', '—')}",
                    f"",
                    f"**Детальный механизм:** {actor.get('mechanism_detail', '—')}",
                    f"",
                    f"**Оценка новизны:** {actor.get('novelty_assessment', '—')}",
                    f"",
                ]

                sources = actor.get("sources", [])
                if sources:
                    lines.append("**Источники:**")
                    for s in sources:
                        lines.append(f"- [{s.get('type', 'источник')}] {s.get('title', '')} — {s.get('relevance', '')}")
                    lines.append("")

                risks = actor.get("risks", {})
                if risks:
                    lines += [
                        f"**Технические риски:** {risks.get('technical', '—')}",
                        f"**Экономические риски:** {risks.get('economic', '—')}",
                        f"",
                    ]

                lines.append(f"**Влияние на KPI:** {actor.get('expected_kpi_impact', '—')}")
                lines.append("")

                roadmap = actor.get("experiment_roadmap", "")
                if roadmap:
                    lines += [
                        f"### План проверки",
                        f"",
                        f"{roadmap}",
                        f"",
                    ]

            # Judge evaluation
            judge = hyp.get("judge_evaluation", {})
            if judge:
                metrics = judge.get("metrics", {})
                lines += [
                    f"### Оценка Judge",
                    f"",
                    f"**Вердикт:** {judge.get('verdict', '—')}",
                    f"**Итоговый балл:** {judge.get('final_score', 0)}",
                    f"",
                    f"| Метрика | Значение | Вес |",
                    f"|:--------|:---------|:----|",
                    f"| Полное обоснование | {'✓' if metrics.get('full_rationale') else '✗'} | 0.5 |",
                    f"| Все ссылки на источники | {'✓' if metrics.get('all_sources') else '✗'} | блокирующая |",
                    f"| Механизм влияния + новизна | {'✓' if metrics.get('mechanism_and_novelty') else '✗'} | 0.3 |",
                    f"| Риски (техн. + экон.) | {'✓' if metrics.get('risks_assessed') else '✗'} | блокирующая |",
                    f"| Влияние на KPI | {'✓' if metrics.get('kpi_impact') else '✗'} | 0.2 |",
                    f"",
                ]

            lines.append("---")
            lines.append("")

    if rejected:
        lines += [
            f"## Отклонённые гипотезы ({len(rejected)})",
            f"",
        ]
        for i, r in enumerate(rejected, 1):
            hyp = r.get("hypothesis", {})
            title = hyp.get("title", f"Гипотеза {i}")
            reason = r.get("reason", "—")
            lines += [
                f"### {title}",
                f"",
                f"**Причина отклонения:** {reason}",
                f"",
                "---",
                "",
            ]

    lines += [
        f"## Дорожная карта внедрения",
        f"",
        f"1. Лабораторная проверка гипотез (1-2 недели)",
        f"2. Опытно-промышленные испытания на одной секции фабрики (1-2 месяца)",
        f"3. Анализ результатов и корректировка параметров",
        f"4. Тиражирование на все секции при подтверждении эффективности",
        f"5. Мониторинг KPI и непрерывное улучшение",
        f"",
        f"---",
        f"",
        f"*Отчёт сгенерирован автоматически системой «Фабрика гипотез» {now}*",
    ]

    return "\n".join(lines)
