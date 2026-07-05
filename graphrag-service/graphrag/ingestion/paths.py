"""Paths to hackathon case data."""

from __future__ import annotations

import os
from pathlib import Path

from graphrag.constants import CASE_DATA_DIRNAME, CASE_TASK_DIRNAME

SERVICE_ROOT = Path(__file__).resolve().parents[2]
_env_root = os.getenv("GRAPHRAG_DATA_ROOT")

BUNDLED_CASE_ROOT = SERVICE_ROOT / "data" / "case"
LITERATURE_MD_ROOT = SERVICE_ROOT / "data" / "literature"

_LOCAL_DATA_ROOT = SERVICE_ROOT / CASE_DATA_DIRNAME / CASE_TASK_DIRNAME
# monorepo layout: hackathon/nornikel-hypothesis-fabric/graphrag-service/
_MONOREPO_DATA_ROOT = (
    SERVICE_ROOT.parent.parent / CASE_DATA_DIRNAME / CASE_TASK_DIRNAME
)


def _default_data_root() -> Path:
    if _env_root:
        return Path(_env_root).expanduser()
    for candidate in (BUNDLED_CASE_ROOT, _LOCAL_DATA_ROOT, _MONOREPO_DATA_ROOT):
        if candidate.is_dir():
            return candidate
    return BUNDLED_CASE_ROOT


DEFAULT_DATA_ROOT = _default_data_root()

EXCEL_SOURCES = (
    ("КГМК", "Пример 1/Хвосты КГМК.xlsx"),
    ("НОФ вкр", "Пример 2/Хвосты НОФ Вкр.xlsx"),
    ("НОФ мед", "Пример 3/Хвосты НОФ мед.xlsx"),
    ("ТОФ", "Пример 4/Хвосты ТОФ_2.xlsx"),
)

PDF_GLOB = "Дополнительные материалы/*.pdf"


def resolve_data_root(root: Path | None = None) -> Path:
    path = root or DEFAULT_DATA_ROOT

    if not path.is_dir():
        raise FileNotFoundError(f"Case data directory not found: {path}")

    return path


def resolve_literature_root() -> Path:
    return LITERATURE_MD_ROOT
