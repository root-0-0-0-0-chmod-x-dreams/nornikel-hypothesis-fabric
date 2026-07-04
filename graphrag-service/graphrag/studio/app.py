"""Gradio dashboard for GraphRAG microservice."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import gradio as gr

from graphrag.ingestion.external_source import apply_external_ingest, ingest_external_source
from graphrag.nl_cypher.service import NLGraphQueryService
from graphrag.service import GraphRAGQueryService
from graphrag.studio.helpers import (
    chunk_search_rows,
    chunks_for_nodes,
    factories,
    infra_status,
    loss_form_choices,
    neighbors_table,
    node_row,
    retrieval_node_labels,
)
from graphrag.studio.graph_viz import VIEW_FILTERS, export_graph_html


def _ensure_loaded() -> None:
    if STATE.graph_rag is None:
        STATE.reload()


def on_reload() -> tuple[str, gr.Dropdown, gr.Dropdown, list[list[str]]]:
    message = STATE.reload()
    graph = STATE.loaded.graph  # type: ignore[union-attr]
    bucket_choices = loss_form_choices(graph)
    factory_choices = ["— все —", *factories(graph)]

    return (
        message,
        gr.Dropdown(choices=bucket_choices, value=bucket_choices[0][1] if bucket_choices else None),
        gr.Dropdown(choices=factory_choices, value=factory_choices[0] if factory_choices else None),
        infra_status(),
    )


def run_graph_rag(
    question: str,
    bucket_id: str | None,
    factory: str,
    k_out: int,
    include_external: bool,
    budget_tier: str,
) -> tuple[str, str, list[list[Any]], str, str]:
    _ensure_loaded()
    assert STATE.graph_rag is not None

    factory_filter = None if factory in {None, "", "— все —"} else factory
    bucket = None if bucket_id in {None, "", "— без bucket —"} else bucket_id
    budget = None if budget_tier in {None, "", "— любой —"} else budget_tier

    result = STATE.graph_rag.query(
        question,
        bucket_id=bucket,
        factory=factory_filter,
        k_out=int(k_out),
        include_external=include_external,
        budget_tier=budget,
    )

    chunk_rows = [
        [
            idx + 1,
            chunk.chunk_id,
            f"{chunk.score:.4f}",
            chunk.retrieval_channel,
            (chunk.citation or {}).get("source", chunk.source),
            (chunk.citation or {}).get("display_ref")
            or _format_citation_ref(chunk.citation),
            (chunk.citation or {}).get("highlight")
            or (chunk.citation or {}).get("excerpt", chunk.text[:200]),
        ]
        for idx, chunk in enumerate(result.chunks)
    ]

    channel_md = "\n".join(
        f"- **{name}**: {count}" for name, count in sorted(result.channel_hits.items())
    )
    nodes_md = "\n".join(f"- `{node_id}`" for node_id in result.node_ids)
    abc_md = _format_abc_evidence(result.abc_evidence)

    paths_json = [
        {
            "nodes": path.nodes,
            "edges": [
                {"source": s, "relation": r, "target": t} for s, r, t in path.edges
            ],
        }
        for path in result.graph_paths
    ]

    return (
        result.expanded_query or question,
        f"### Swanson ABC\n{abc_md}\n\n### Каналы\n{channel_md}\n\n### Узлы retrieval\n{nodes_md}",
        chunk_rows,
        json.dumps(paths_json, ensure_ascii=False, indent=2),
        json.dumps(
            {
                "question": result.question,
                "bucket_id": result.bucket_id,
                "channel_hits": result.channel_hits,
                "abc_evidence": result.abc_evidence,
            },
            ensure_ascii=False,
            indent=2,
        ),
    )


def _format_citation_ref(citation: dict | None) -> str:
    if not citation:
        return ""

    parts = [str(citation.get("source", ""))]

    if citation.get("page"):
        parts.append(f"стр. {citation['page']}")

    if citation.get("paragraph_index") is not None:
        parts.append(f"§{int(citation['paragraph_index']) + 1}")

    if citation.get("excel_cell"):
        parts.append(str(citation["excel_cell"]))

    return ", ".join(part for part in parts if part)


def _format_abc_evidence(abc: dict | None) -> str:
    if not abc:
        return "_Укажите bucket для цепочки ABC._"

    lines = [
        f"**{abc.get('discovery_note', '')}**",
        f"Источников: {abc.get('source_count', 0)}",
    ]

    for hop in abc.get("hops") or []:
        lines.append(
            f"\n**{hop.get('hop')}** `{hop.get('from_label')}` "
            f"—[{hop.get('relation')}]→ `{hop.get('to_label')}`"
            f"{' _(inferred)_' if hop.get('inferred') else ''}"
        )

        for citation in hop.get("citations") or []:
            ref = citation.get("source", "")
            page = citation.get("page")
            cell = citation.get("excel_cell")

            if page:
                ref += f", стр. {page}"

            if cell:
                ref += f", {cell}"

            excerpt = (citation.get("highlight") or citation.get("excerpt") or "")[:160]
            lines.append(f"- {ref}: «{excerpt}…»" if excerpt else f"- {ref}")

    return "\n".join(lines)


def run_nl_cypher(question: str, show_cypher: bool, compile_only: bool) -> tuple[str, str, list[list[Any]]]:
    _ensure_loaded()

    if compile_only or STATE.nl_cypher is None:
        result = NLGraphQueryService.compile(question, show_hints=True)
        cypher_block = ""

        if show_cypher:
            cypher_block = (
                f"**intent:** `{result.intent}`  |  **bucket:** `{result.bucket_id or '—'}`\n\n"
                f"```cypher\n{result.cypher}\n```\n\n"
                f"Params: `{json.dumps(result.params, ensure_ascii=False)}`"
            )

        if compile_only:
            hints = "\n".join(f"- {line}" for line in result.hints)
            return f"{result.answer}\n\n{hints}", cypher_block, []

        if STATE.nl_cypher is None:
            return (
                "Neo4j недоступен — показан только Cypher preview. "
                "Запусти: `docker compose up -d neo4j && make neo4j-seed`",
                cypher_block,
                [],
            )

    result = STATE.nl_cypher.ask(question, show_hints=True)
    cypher_block = ""

    if show_cypher:
        cypher_block = (
            f"**intent:** `{result.intent}`  |  **bucket:** `{result.bucket_id or '—'}`\n\n"
            f"```cypher\n{result.cypher}\n```\n\n"
            f"Params: `{json.dumps(result.params, ensure_ascii=False)}`"
        )

    table: list[list[Any]] = []

    if result.rows:
        keys = list(result.rows[0].keys())
        table.append(keys)

        for row in result.rows[:50]:
            table.append([row.get(key, "") for key in keys])

    return result.answer, cypher_block, table


def ingest_external(
    title: str,
    text: str,
    source_url: str,
    node_ids_csv: str,
    auto_link: bool,
) -> tuple[str, list[list[Any]]]:
    _ensure_loaded()
    assert STATE.loaded is not None

    explicit = [item.strip() for item in node_ids_csv.split(",") if item.strip()]
    result = ingest_external_source(
        text=text,
        title=title or "External source",
        source_url=source_url or None,
        explicit_node_ids=explicit,
        auto_link=auto_link,
    )
    apply_external_ingest(STATE.loaded.graph, STATE.loaded.vectors, result)
    STATE.graph_rag = GraphRAGQueryService(STATE.loaded.graph, STATE.loaded.vectors)

    summary = (
        f"Добавлено **{len(result.chunks)}** chunk(s), первый: `{result.chunks[0].chunk_id}`\n\n"
        f"**Source:** `{result.source_id}`\n\n"
        f"**Связано сущностей:** {len(result.matched_entities)}\n\n"
        + ", ".join(result.matched_entities)
    )
    table = [["entity_id", "edge"]] + [
        [entity, "EVIDENCED_BY → " + result.source_id] for entity in result.matched_entities
    ]

    return summary, table


def export_graph_map(view: str, open_browser: bool) -> tuple[str, str | None]:
    _ensure_loaded()
    assert STATE.loaded is not None

    from graphrag.graph.networkx_store import NetworkXGraphStore

    graph = STATE.loaded.graph
    if not isinstance(graph, NetworkXGraphStore):
        return (
            "HTML-экспорт доступен только с `GRAPH_BACKEND=networkx` (по умолчанию в Gradio).",
            None,
        )

    out_dir = Path("output/graph")
    path = out_dir / f"graph_{view}.html"
    stats = export_graph_html(graph, path, view=view)

    md = (
        f"### {VIEW_FILTERS[view]['title']}\n"
        f"- **Узлов:** {stats['nodes']}\n"
        f"- **Рёбер:** {stats['edges']}\n"
        f"- **Файл:** `{path.resolve()}`\n\n"
        "Откройте файл в браузере (двойной клик) или Neo4j Browser: "
        "[http://localhost:7474](http://localhost:7474) → `assets/cypher/passage_graph.cypher`"
    )

    if open_browser:
        import webbrowser

        webbrowser.open(path.resolve().as_uri())

    return md, str(path.resolve())


def explore_bucket(bucket_id: str) -> tuple[list[list[Any]], list[list[Any]], list[list[Any]], str]:
    _ensure_loaded()
    assert STATE.loaded is not None

    if not bucket_id:
        return [], [], [], "Выберите bucket"

    graph = STATE.loaded.graph
    attrs = graph.get_node_attributes(bucket_id) or {}
    meta = node_row(graph, bucket_id)
    neighbors = neighbors_table(graph, bucket_id, direction="both")
    direct_chunks = chunks_for_nodes(STATE.loaded.vectors, [bucket_id], limit=10)

    from graphrag.retrieval_nodes import expand_retrieval_nodes

    expanded = expand_retrieval_nodes(graph, bucket_id, [bucket_id])
    graph_chunks = chunks_for_nodes(STATE.loaded.vectors, expanded, limit=25)

    summary = (
        f"**Bucket:** `{bucket_id}`\n\n"
        f"- factory: {attrs.get('factory')}\n"
        f"- size: {attrs.get('size_class')}\n"
        f"- mineral: {attrs.get('mineral_form')}\n"
        f"- metal: {attrs.get('metal')}\n"
        f"- tonnes: {attrs.get('tonnes')}\n"
        f"- recoverable: {attrs.get('recoverable')}\n\n"
        f"**Expanded retrieval nodes ({len(expanded)}):** "
        + ", ".join(f"`{n}`" for n in expanded)
    )

    return meta, neighbors, graph_chunks, summary


def inspect_node(node_id: str) -> tuple[list[list[Any]], list[list[Any]]]:
    _ensure_loaded()
    assert STATE.loaded is not None

    if not node_id:
        return [], []

    graph = STATE.loaded.graph

    return (
        node_row(graph, node_id.strip()),
        neighbors_table(graph, node_id.strip(), direction="both"),
    )


def search_chunks(
    query: str,
    mode: str,
    factory: str,
    k: int,
) -> list[list[Any]]:
    _ensure_loaded()
    assert STATE.loaded is not None

    factory_filter = None if factory in {None, "", "— все —"} else factory

    return chunk_search_rows(
        STATE.loaded.vectors,
        query,
        mode,
        factory=factory_filter,
        k=int(k),
    )


def rmq_graph_rag(question: str, bucket_id: str, factory: str) -> str:
    try:
        from graphrag.messaging.client import GraphRagMessagingClient

        client = GraphRagMessagingClient()
        factory_filter = None if factory in {None, "", "— все —"} else factory
        bucket = None if bucket_id in {None, "", "— без bucket —"} else bucket_id

        try:
            payload = client.graph_rag_query(
                question,
                bucket_id=bucket,
                factory=factory_filter,
                k_out=8,
            )

            return json.dumps(payload, ensure_ascii=False, indent=2)
        finally:
            client.close()
    except Exception as exc:  # noqa: BLE001
        return f"RabbitMQ error: {exc}\n\nЗапусти: make rmq-worker"


def build_app() -> gr.Blocks:
    if STATE.graph_rag is None:
        STATE.reload()

    assert STATE.loaded is not None
    startup_message = (
        f"Ready: {STATE.stats.get('nodes', 0)} nodes, "
        f"{STATE.loaded.vectors.size} chunks indexed."
    )

    bucket_choices = loss_form_choices(STATE.loaded.graph)
    factory_choices = ["— все —", *factories(STATE.loaded.graph)]
    node_choices = retrieval_node_labels(STATE.loaded.graph)

    with gr.Blocks(title="GraphRAG Studio") as app:
        gr.Markdown(
            "# GraphRAG Studio\n"
            "Микросервис: граф + Qdrant hybrid + RabbitMQ. "
            "Смотри retrieval, граф, чанки — ищи что допилить."
        )

        with gr.Row():
            status_box = gr.Textbox(
                label="Статус",
                value=startup_message,
                interactive=False,
                scale=3,
            )
            reload_btn = gr.Button("🔄 Reload KB", variant="primary", scale=1)

        infra_table = gr.Dataframe(
            headers=["Service", "URL", "Status", "Detail"],
            value=infra_status(),
            label="Инфраструктура",
            interactive=False,
        )

        with gr.Tabs():
            with gr.Tab("🔍 GraphRAG Query"):
                with gr.Row():
                    with gr.Column(scale=2):
                        q_question = gr.Textbox(
                            label="Вопрос",
                            value="доизмельчение закрытого пентландита в классе +71 МШР",
                            lines=2,
                        )
                        with gr.Row():
                            q_bucket = gr.Dropdown(
                                label="Bucket (LossForm)",
                                choices=[("— без bucket —", "")] + bucket_choices,
                                value=bucket_choices[0][1] if bucket_choices else "",
                                allow_custom_value=True,
                            )
                            q_factory = gr.Dropdown(
                                label="Фабрика",
                                choices=factory_choices,
                                value="КГМК" if "КГМК" in factory_choices else factory_choices[0],
                            )
                        with gr.Row():
                            q_k = gr.Slider(3, 20, value=8, step=1, label="k_out")
                            q_external = gr.Checkbox(label="include_external", value=False)
                            q_budget = gr.Dropdown(
                                label="Бюджет",
                                choices=["— любой —", "low", "medium", "high"],
                                value="— любой —",
                            )
                        q_run = gr.Button("Run GraphRAG", variant="primary")
                    with gr.Column(scale=3):
                        q_expanded = gr.Textbox(label="Expanded query", lines=3)
                        q_meta = gr.Markdown()
                q_chunks = gr.Dataframe(
                    headers=["#", "chunk_id", "score", "channel", "source", "citation ref", "excerpt"],
                    label="Top chunks + citations",
                    interactive=False,
                )
                with gr.Accordion("Graph paths JSON", open=False):
                    q_paths = gr.Code(language="json")
                with gr.Accordion("Raw meta JSON", open=False):
                    q_raw = gr.Code(language="json")

                q_run.click(
                    run_graph_rag,
                    inputs=[q_question, q_bucket, q_factory, q_k, q_external, q_budget],
                    outputs=[q_expanded, q_meta, q_chunks, q_paths, q_raw],
                )

            with gr.Tab("🗣 NL → Cypher"):
                nl_question = gr.Textbox(
                    label="Вопрос по графу (русский)",
                    value="что делать с закрытым пентландитом +71 на КГМК",
                )
                with gr.Row():
                    nl_show_cypher = gr.Checkbox(label="Показать Cypher", value=True)
                    nl_compile_only = gr.Checkbox(
                        label="Только Cypher (без Neo4j)",
                        value=False,
                    )
                with gr.Row():
                    nl_run = gr.Button("Ask graph", variant="primary")
                    nl_compile = gr.Button("Compile Cypher")
                nl_answer = gr.Markdown()
                nl_cypher = gr.Markdown()
                nl_table = gr.Dataframe(label="Neo4j rows", interactive=False)
                nl_run.click(
                    run_nl_cypher,
                    inputs=[nl_question, nl_show_cypher, nl_compile_only],
                    outputs=[nl_answer, nl_cypher, nl_table],
                )
                nl_compile.click(
                    lambda q, show: run_nl_cypher(q, show, True),
                    inputs=[nl_question, nl_show_cypher],
                    outputs=[nl_answer, nl_cypher, nl_table],
                )

            with gr.Tab("🌐 External source"):
                gr.Markdown(
                    "Добавьте внешний текст (статья, отчёт, заметка). "
                    "Автолинковка по ключевым словам каталога + явные `graph_node_ids`."
                )
                ex_title = gr.Textbox(label="Название", value="Отраслевой обзор флотации")
                ex_url = gr.Textbox(label="URL (опционально)")
                ex_nodes = gr.Textbox(
                    label="graph_node_ids через запятую",
                    placeholder="mech_liberation, process_flotation",
                )
                ex_text = gr.Textbox(
                    label="Текст",
                    lines=8,
                    value=(
                        "Для раскрытия закрытого пентландита рекомендуется доизмельчение на МШР "
                        "с последующей флотацией на ФПМ."
                    ),
                )
                ex_auto = gr.Checkbox(label="auto_link по ключевым словам", value=True)
                ex_run = gr.Button("Ingest external", variant="primary")
                ex_summary = gr.Markdown()
                ex_links = gr.Dataframe(
                    headers=["entity_id", "edge"],
                    label="Созданные связи EVIDENCED_BY",
                    interactive=False,
                )
                ex_run.click(
                    ingest_external,
                    inputs=[ex_title, ex_text, ex_url, ex_nodes, ex_auto],
                    outputs=[ex_summary, ex_links],
                )

            with gr.Tab("🕸 Graph Map"):
                gr.Markdown(
                    "Интерактивная карта графа (vis-network). "
                    "**full** — все ~5k узлов; для параграфов удобнее **literature** или **passage_links**."
                )
                with gr.Row():
                    g_view = gr.Dropdown(
                        label="Срез графа",
                        choices=list(VIEW_FILTERS),
                        value="literature",
                    )
                    g_open = gr.Checkbox(label="Открыть в браузере", value=True)
                g_run = gr.Button("Сгенерировать HTML", variant="primary")
                g_summary = gr.Markdown()
                g_file = gr.File(label="Скачать HTML")
                g_run.click(
                    export_graph_map,
                    inputs=[g_view, g_open],
                    outputs=[g_summary, g_file],
                )

            with gr.Tab("📦 Bucket Explorer"):
                b_bucket = gr.Dropdown(
                    label="LossForm bucket",
                    choices=bucket_choices,
                    value=bucket_choices[0][1] if bucket_choices else None,
                    allow_custom_value=True,
                )
                b_run = gr.Button("Explore", variant="primary")
                b_summary = gr.Markdown()
                with gr.Row():
                    b_meta = gr.Dataframe(headers=["field", "value"], label="Attributes")
                    b_neighbors = gr.Dataframe(
                        headers=["from", "relation", "to", "dir"],
                        label="Соседи в графе",
                    )
                b_chunks = gr.Dataframe(
                    headers=["chunk_id", "score", "type", "source", "factory", "nodes", "text"],
                    label="Chunks по graph_node_ids (expanded path)",
                )
                b_run.click(
                    explore_bucket,
                    inputs=[b_bucket],
                    outputs=[b_meta, b_neighbors, b_chunks, b_summary],
                )

            with gr.Tab("🧩 Chunk Search"):
                with gr.Row():
                    c_query = gr.Textbox(label="Query", value="МШР пентландит флотация")
                    c_mode = gr.Radio(
                        ["hybrid", "dense", "bm25"],
                        value="hybrid",
                        label="Режим",
                    )
                    c_factory = gr.Dropdown(
                        label="Factory filter",
                        choices=factory_choices,
                        value="— все —",
                    )
                    c_k = gr.Slider(5, 60, value=20, step=5, label="k")
                c_run = gr.Button("Search", variant="primary")
                c_results = gr.Dataframe(
                    headers=["chunk_id", "score", "type", "source", "factory", "text"],
                    label="Hits",
                    interactive=False,
                )
                c_run.click(
                    search_chunks,
                    inputs=[c_query, c_mode, c_factory, c_k],
                    outputs=[c_results],
                )

            with gr.Tab("🕸 Node Inspector"):
                with gr.Row():
                    n_pick = gr.Dropdown(
                        label="Retrieval node",
                        choices=node_choices,
                        value=node_choices[0] if node_choices else None,
                        allow_custom_value=True,
                    )
                    n_custom = gr.Textbox(label="или node_id", placeholder="mech_liberation")
                n_run = gr.Button("Inspect", variant="primary")

                def _inspect(pick: str, custom: str):
                    node_id = custom.strip() or (pick.split(" — ")[0] if pick else "")
                    return inspect_node(node_id)

                with gr.Row():
                    n_meta = gr.Dataframe(headers=["field", "value"])
                    n_neighbors = gr.Dataframe(
                        headers=["from", "relation", "to", "dir"],
                    )
                n_run.click(_inspect, inputs=[n_pick, n_custom], outputs=[n_meta, n_neighbors])

            with gr.Tab("🐰 RabbitMQ RPC"):
                gr.Markdown(
                    "Проверка микросервисного канала. Worker: `make rmq-worker` в отдельном терминале."
                )
                r_question = gr.Textbox(
                    label="Question",
                    value="доизмельчение закрытого пентландита МШР",
                )
                with gr.Row():
                    r_bucket = gr.Dropdown(
                        label="Bucket",
                        choices=[("— без bucket —", "")] + bucket_choices,
                        value=bucket_choices[0][1] if bucket_choices else "",
                    )
                    r_factory = gr.Dropdown(
                        label="Factory",
                        choices=factory_choices,
                        value="КГМК" if "КГМК" in factory_choices else factory_choices[0],
                    )
                r_run = gr.Button("RPC graph_rag_query", variant="primary")
                r_out = gr.Code(language="json")
                r_run.click(
                    rmq_graph_rag,
                    inputs=[r_question, r_bucket, r_factory],
                    outputs=[r_out],
                )

        reload_btn.click(
            on_reload,
            outputs=[status_box, q_bucket, q_factory, infra_table],
        )

    return app


def launch(**kwargs) -> None:
    app = build_app()
    defaults = {
        "theme": gr.themes.Soft(primary_hue="slate"),
        "css": ".gradio-container {max-width: 1400px !important}",
    }
    defaults.update(kwargs)
    app.launch(**defaults)
