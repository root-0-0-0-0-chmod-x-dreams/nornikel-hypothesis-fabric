#!/usr/bin/env python3
"""Deploy pics-to-md VLM transcripts into bundled case data."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from graphrag.ingestion.md_frontmatter import split_frontmatter
from graphrag.ingestion.md_image_refs import IMAGE_MD_RE
from graphrag.ingestion.scheme_md_parser import REGULATION_MD_DIR, SCHEME_MD_DIR
from graphrag.ingestion.schemes import SCHEME_NODE_HINTS

SERVICE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SRC = SERVICE_ROOT.parent.parent / "pics-to-md"
if not DEFAULT_SRC.is_dir():
    DEFAULT_SRC = SERVICE_ROOT.parent / "pics-to-md"
DATA_CASE = SERVICE_ROOT / "data" / "case"

REGULATION_NAME_MARKERS = ("Регламент", "оборудования", "Типичный")


def _target_kind(filename: str) -> str:
    if any(marker in filename for marker in REGULATION_NAME_MARKERS):
        return "regulation"

    return "scheme"


def _graph_nodes_hint(stem: str, kind: str) -> list[str]:
    hints = SCHEME_NODE_HINTS

    for prefix, node_ids in hints.items():
        if stem.startswith(prefix):
            return node_ids

    return []


def _normalize_body(body: str, stem: str, png_name: str) -> str:
    def repl(_match: re.Match[str]) -> str:
        return f"![{stem}](./{png_name})"

    return IMAGE_MD_RE.sub(repl, body.strip(), count=1)


def _build_frontmatter(stem: str, kind: str) -> str:
    chunk_type = "constraint_regulation" if kind == "regulation" else "scheme_caption"
    node_ids = _graph_nodes_hint(stem, kind)
    lines = [
        "---",
        f"doc_id: {_slug(stem)}",
        f"title: {stem}",
        f"source: {stem}.png",
        "original_format: scheme_vlm",
        f"chunk_type: {chunk_type}",
    ]

    if kind == "regulation":
        lines.append("factory: КГМК")

    if node_ids:
        lines.append(f"graph_node_ids: {node_ids}")

    lines.append("---")
    lines.append("")

    return "\n".join(lines)


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^\w\-]+", "_", value.strip(), flags=re.UNICODE)

    return cleaned.strip("_").lower() or "scheme"


def deploy_file(src: Path, data_case: Path) -> Path:
    kind = _target_kind(src.name)
    subdir = REGULATION_MD_DIR if kind == "regulation" else SCHEME_MD_DIR
    target_dir = data_case / subdir
    target_dir.mkdir(parents=True, exist_ok=True)

    raw = src.read_text(encoding="utf-8")
    _meta, body = split_frontmatter(raw)
    stem = src.stem
    png_name = f"{stem}.png"
    normalized_body = _normalize_body(body, stem, png_name)
    output = f"{_build_frontmatter(stem, kind)}{normalized_body}\n"

    target = target_dir / src.name
    target.write_text(output, encoding="utf-8")

    return target


def deploy_all(src_dir: Path, data_case: Path) -> list[Path]:
    if not src_dir.is_dir():
        raise FileNotFoundError(f"Source directory not found: {src_dir}")

    written: list[Path] = []

    for path in sorted(src_dir.glob("*.md")):
        written.append(deploy_file(path, data_case))

    return written


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SRC
    data_case = Path(sys.argv[2]) if len(sys.argv) > 2 else DATA_CASE
    written = deploy_all(src, data_case)

    print(f"Deployed {len(written)} scheme/regulation MD files → {data_case}")

    for path in written:
        print(f"  {path.relative_to(data_case)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
