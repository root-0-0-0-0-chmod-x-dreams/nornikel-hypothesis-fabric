"""Persist NetworkX graph snapshot for fast worker startup."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from graphrag.graph.networkx_store import NetworkXGraphStore
from graphrag.ingestion.paths import BUNDLED_CASE_ROOT, resolve_data_root

logger = logging.getLogger(__name__)

CACHE_DIRNAME = "cache"
GRAPH_FILENAME = "graph.json"
META_FILENAME = "graph.meta.json"


def graph_cache_dir(data_root: Path | None = None) -> Path:
    root = data_root or resolve_data_root(BUNDLED_CASE_ROOT if BUNDLED_CASE_ROOT.is_dir() else None)
    service_root = Path(__file__).resolve().parents[2]
    bundled_cache = service_root / "data" / CACHE_DIRNAME

    if root == BUNDLED_CASE_ROOT or str(root).endswith("/data/case"):
        return bundled_cache

    return root / CACHE_DIRNAME


def use_graph_cache() -> bool:
    return os.getenv("GRAPHRAG_USE_GRAPH_CACHE", "1").strip().lower() not in {
        "0",
        "false",
        "no",
    }


def data_fingerprint(data_root: Path) -> str:
    parts: list[str] = [str(data_root.resolve())]

    for pattern in ("Пример */*.xlsx", "Дополнительные материалы/md/*/_book.meta.md"):
        for path in sorted(data_root.glob(pattern)):
            stat = path.stat()
            parts.append(f"{path.relative_to(data_root)}:{stat.st_mtime_ns}:{stat.st_size}")

    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()

    return digest[:16]


@dataclass
class GraphCacheSnapshot:
    graph: NetworkXGraphStore
    stats: dict[str, int | float | str | list[str]]


def save_graph_cache(
    data_root: Path,
    graph: NetworkXGraphStore,
    stats: dict,
) -> Path:
    cache_dir = graph_cache_dir(data_root)
    cache_dir.mkdir(parents=True, exist_ok=True)

    graph_path = cache_dir / GRAPH_FILENAME
    meta_path = cache_dir / META_FILENAME
    fingerprint = data_fingerprint(data_root)

    graph.save_json(graph_path)
    meta_path.write_text(
        json.dumps(
            {
                "fingerprint": fingerprint,
                "data_root": str(data_root.resolve()),
                "stats": stats,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    logger.info("graph cache saved → %s (%s nodes)", graph_path, stats.get("nodes"))

    return graph_path


def try_load_graph_cache(data_root: Path) -> GraphCacheSnapshot | None:
    if not use_graph_cache():
        return None

    cache_dir = graph_cache_dir(data_root)
    graph_path = cache_dir / GRAPH_FILENAME
    meta_path = cache_dir / META_FILENAME

    if not graph_path.is_file() or not meta_path.is_file():
        return None

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None

    expected = data_fingerprint(data_root)

    if meta.get("fingerprint") != expected:
        logger.info("graph cache stale (fingerprint mismatch)")
        return None

    graph = NetworkXGraphStore.load_json(graph_path)
    stats = dict(meta.get("stats") or {})
    stats.setdefault("nodes", graph._graph.number_of_nodes())  # noqa: SLF001
    stats.setdefault("edges", graph._graph.number_of_edges())  # noqa: SLF001
    stats["graph_cache"] = True

    logger.info("graph cache loaded ← %s (%s nodes)", graph_path, stats.get("nodes"))

    return GraphCacheSnapshot(graph=graph, stats=stats)


def invalidate_graph_cache(data_root: Path | None = None) -> None:
    cache_dir = graph_cache_dir(data_root)

    for name in (GRAPH_FILENAME, META_FILENAME):
        path = cache_dir / name

        if path.is_file():
            path.unlink()
