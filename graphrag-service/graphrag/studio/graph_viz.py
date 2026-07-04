"""Interactive graph HTML export (vis-network)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from graphrag.graph.networkx_store import NetworkXGraphStore
from graphrag.schema import NodeType, RelationType

NODE_COLORS: dict[str, str] = {
    NodeType.PASSAGE: "#4FC3F7",
    NodeType.SOURCE: "#FFB74D",
    NodeType.HYPOTHESIS: "#BA68C8",
    NodeType.LOSS_FORM: "#EF5350",
    NodeType.FACTORY: "#1E88E5",
    NodeType.MECHANISM: "#66BB6A",
    NodeType.PROCESS: "#43A047",
    NodeType.EQUIPMENT: "#2E7D32",
    NodeType.MINERAL: "#8D6E63",
    NodeType.METAL: "#78909C",
    NodeType.REAGENT: "#26A69A",
    NodeType.SIZE_CLASS: "#90A4AE",
    NodeType.PARAMETER: "#A1887F",
    NodeType.INTERVENTION: "#EC407A",
    NodeType.KPI: "#FFA726",
    NodeType.ORE: "#8BC34A",
}

RELATION_COLORS: dict[str, str] = {
    RelationType.SHARES_TOPIC: "#E91E63",
    RelationType.NEXT_PASSAGE: "#29B6F6",
    RelationType.PART_OF: "#FF9800",
    RelationType.MENTIONS: "#9C27B0",
    RelationType.SUPPORTS_HYPOTHESIS: "#7B1FA2",
    RelationType.RELATED_SOURCE: "#F44336",
    RelationType.EVIDENCED_BY: "#795548",
    RelationType.EXPLAINED_BY: "#388E3C",
    RelationType.ADDRESSED_BY: "#2E7D32",
    RelationType.USES_EQUIPMENT: "#1B5E20",
    RelationType.HAS_LOSS: "#C62828",
}

VIEW_FILTERS: dict[str, dict[str, Any]] = {
    "full": {
        "title": "Полный граф",
        "exclude_types": set(),
        "exclude_relations": set(),
    },
    "literature": {
        "title": "Литература и параграфы",
        "include_types": {
            NodeType.PASSAGE,
            NodeType.SOURCE,
            NodeType.HYPOTHESIS,
            NodeType.MECHANISM,
            NodeType.PROCESS,
            NodeType.EQUIPMENT,
            NodeType.REAGENT,
            NodeType.MINERAL,
        },
        "include_relations": {
            RelationType.PART_OF,
            RelationType.NEXT_PASSAGE,
            RelationType.MENTIONS,
            RelationType.SHARES_TOPIC,
            RelationType.SUPPORTS_HYPOTHESIS,
            RelationType.RELATED_SOURCE,
            RelationType.HAS_PASSAGE,
            RelationType.EVIDENCED_BY,
        },
    },
    "taxonomy": {
        "title": "Таксономия (без Passage)",
        "exclude_types": {NodeType.PASSAGE},
    },
    "passage_links": {
        "title": "Связи между параграфами",
        "include_types": {NodeType.PASSAGE, NodeType.SOURCE, NodeType.HYPOTHESIS},
        "include_relations": {
            RelationType.PART_OF,
            RelationType.NEXT_PASSAGE,
            RelationType.SHARES_TOPIC,
            RelationType.SUPPORTS_HYPOTHESIS,
            RelationType.RELATED_SOURCE,
            RelationType.HAS_PASSAGE,
        },
    },
}


def export_graph_html(
    graph: NetworkXGraphStore,
    output_path: Path,
    *,
    view: str = "full",
    max_nodes: int | None = None,
) -> dict[str, int]:
    """Write self-contained interactive HTML; returns node/edge counts."""
    nodes, edges = _collect_graph(graph, view=view, max_nodes=max_nodes)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        _render_html(nodes, edges, title=VIEW_FILTERS.get(view, {}).get("title", view)),
        encoding="utf-8",
    )
    return {"nodes": len(nodes), "edges": len(edges), "view": view}


def _collect_graph(
    graph: NetworkXGraphStore,
    *,
    view: str,
    max_nodes: int | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    spec = VIEW_FILTERS.get(view, VIEW_FILTERS["full"])
    include_types = spec.get("include_types")
    exclude_types = spec.get("exclude_types", set())
    include_relations = spec.get("include_relations")
    exclude_relations = spec.get("exclude_relations", set())

    raw_nodes: list[tuple[str, dict[str, Any]]] = []

    for node_id, data in graph._graph.nodes(data=True):
        node_type = str(data.get("node_type", ""))
        if include_types is not None and node_type not in include_types:
            continue
        if node_type in exclude_types:
            continue
        raw_nodes.append((node_id, data))

    if max_nodes is not None and len(raw_nodes) > max_nodes:
        priority = {
            NodeType.FACTORY: 0,
            NodeType.LOSS_FORM: 1,
            NodeType.HYPOTHESIS: 2,
            NodeType.SOURCE: 3,
            NodeType.MECHANISM: 4,
            NodeType.PROCESS: 5,
            NodeType.EQUIPMENT: 6,
            NodeType.PASSAGE: 9,
        }
        raw_nodes.sort(
            key=lambda item: (
                priority.get(str(item[1].get("node_type", "")), 8),
                item[0],
            )
        )
        raw_nodes = raw_nodes[:max_nodes]

    kept = {node_id for node_id, _ in raw_nodes}
    vis_nodes: list[dict[str, Any]] = []

    for node_id, data in raw_nodes:
        node_type = str(data.get("node_type", ""))
        label = str(data.get("label") or node_id)
        short = label if len(label) <= 42 else label[:39] + "…"
        vis_nodes.append(
            {
                "id": node_id,
                "label": short,
                "title": f"{node_type}\n{node_id}\n{label}",
                "group": node_type,
                "color": NODE_COLORS.get(node_type, "#B0BEC5"),
                "font": {"size": 10 if node_type == NodeType.PASSAGE else 12},
            }
        )

    vis_edges: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str, str]] = set()

    for source, target, data in graph._graph.edges(data=True):
        relation = str(data.get("relation", ""))
        if source not in kept or target not in kept:
            continue
        if include_relations is not None and relation not in include_relations:
            continue
        if relation in exclude_relations:
            continue

        key = (source, relation, target)
        if key in seen_edges:
            continue

        seen_edges.add(key)
        vis_edges.append(
            {
                "from": source,
                "to": target,
                "label": relation,
                "title": relation,
                "color": {"color": RELATION_COLORS.get(relation, "#9E9E9E")},
                "arrows": "to",
                "font": {"size": 8, "align": "middle"},
                "smooth": {"type": "dynamic"},
            }
        )

    return vis_nodes, vis_edges


def _render_html(nodes: list[dict], edges: list[dict], *, title: str) -> str:
    payload = json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False)
    legend = "".join(
        f'<span class="legend-item"><i style="background:{color}"></i>{nt}</span>'
        for nt, color in sorted(NODE_COLORS.items(), key=lambda item: item[0])
    )

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    html, body {{ margin: 0; height: 100%; font-family: system-ui, sans-serif; background: #0f1419; color: #e8eaed; }}
    #toolbar {{ padding: 10px 14px; background: #1a2332; border-bottom: 1px solid #2d3a4d; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }}
    #stats {{ opacity: 0.85; font-size: 13px; }}
    #network {{ width: 100%; height: calc(100vh - 96px); background: radial-gradient(circle at 20% 20%, #152033, #0b1018); }}
    button {{ background: #2b5278; color: white; border: none; border-radius: 6px; padding: 6px 12px; cursor: pointer; }}
    button:hover {{ background: #3a6ea0; }}
    .legend {{ display: flex; flex-wrap: wrap; gap: 8px; font-size: 11px; max-width: 70vw; }}
    .legend-item i {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 4px; }}
    input[type=search] {{ padding: 6px 10px; border-radius: 6px; border: 1px solid #3a4a5c; background: #0f1419; color: inherit; min-width: 220px; }}
  </style>
</head>
<body>
  <div id="toolbar">
    <strong>{title}</strong>
    <span id="stats"></span>
    <input id="search" type="search" placeholder="Поиск node_id / label…" />
    <button id="fit">Fit</button>
    <button id="physics">Physics: ON</button>
    <div class="legend">{legend}</div>
  </div>
  <div id="network"></div>
  <script>
    const data = {payload};
    const container = document.getElementById('network');
    const nodes = new vis.DataSet(data.nodes);
    const edges = new vis.DataSet(data.edges);
    let physics = true;
    const network = new vis.Network(container, {{ nodes, edges }}, {{
      physics: {{
        enabled: true,
        stabilization: {{ iterations: 120 }},
        barnesHut: {{ gravitationalConstant: -12000, springLength: 120, damping: 0.35 }}
      }},
      interaction: {{ hover: true, tooltipDelay: 120, navigationButtons: true, keyboard: true }},
      nodes: {{ shape: 'dot', size: 14, borderWidth: 1, font: {{ color: '#e8eaed' }} }},
      edges: {{ width: 0.6, selectionWidth: 2 }}
    }});
    document.getElementById('stats').textContent =
      `${{data.nodes.length}} узлов · ${{data.edges.length}} рёбер`;
    document.getElementById('fit').onclick = () => network.fit({{ animation: true }});
    document.getElementById('physics').onclick = (e) => {{
      physics = !physics;
      network.setOptions({{ physics: {{ enabled: physics }} }});
      e.target.textContent = 'Physics: ' + (physics ? 'ON' : 'OFF');
    }};
    document.getElementById('search').addEventListener('keydown', (ev) => {{
      if (ev.key !== 'Enter') return;
      const q = ev.target.value.trim().toLowerCase();
      if (!q) return;
      const hit = data.nodes.find(n => n.id.toLowerCase().includes(q) || (n.label||'').toLowerCase().includes(q));
      if (!hit) return;
      network.selectNodes([hit.id]);
      network.focus(hit.id, {{ scale: 1.4, animation: true }});
    }});
    network.once('stabilizationIterationsDone', () => {{
      network.fit({{ animation: true }});
    }});
  </script>
</body>
</html>
"""
