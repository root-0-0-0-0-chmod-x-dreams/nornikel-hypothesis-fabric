"""Parse VLM-transcribed scheme and regulation Markdown (pics-to-md)."""

from __future__ import annotations

from pathlib import Path

from graphrag.ingestion.excel_parser import _slugify
from graphrag.ingestion.md_frontmatter import split_frontmatter
from graphrag.ingestion.md_image_refs import (
    extract_image_refs,
    normalize_image_ref,
    relative_to_data_root,
    resolve_image_path,
    strip_image_markdown,
)
from graphrag.ingestion.schemes import SCHEME_NODE_HINTS, _graph_nodes_for_file
from graphrag.models import Chunk

SCHEME_MD_DIR = "Схемы флотации"
REGULATION_MD_DIR = "Регламенты"

REGULATION_NODE_HINTS: dict[str, list[str]] = {
    "Регламент 1": ["equip_fpm", "process_flotation"],
    "Типичный список оборудования": [
        "equip_mshr",
        "equip_mshc",
        "equip_gc660",
        "equip_fpm",
        "equip_kmd",
        "process_comminution",
        "process_flotation",
    ],
}


def parse_scheme_regulation_md(data_root: Path) -> list[Chunk]:
    """Load scheme/regulation MD chunks; skip PNG stubs when MD exists."""
    chunks: list[Chunk] = []

    scheme_dir = data_root / SCHEME_MD_DIR

    if scheme_dir.is_dir():
        for path in sorted(scheme_dir.glob("*.md")):
            chunk = _parse_document_md(path, data_root=data_root, kind="scheme")

            if chunk is not None:
                chunks.append(chunk)

    regulation_dir = data_root / REGULATION_MD_DIR

    if regulation_dir.is_dir():
        for path in sorted(regulation_dir.glob("*.md")):
            chunk = _parse_document_md(path, data_root=data_root, kind="regulation")

            if chunk is not None:
                chunks.append(chunk)

    return chunks


def scheme_md_stems(data_root: Path) -> frozenset[str]:
    stems: set[str] = set()

    for subdir in (SCHEME_MD_DIR, REGULATION_MD_DIR):
        directory = data_root / subdir

        if not directory.is_dir():
            continue

        stems.update(path.stem for path in directory.glob("*.md"))

    return frozenset(stems)


def _parse_document_md(path: Path, *, data_root: Path, kind: str) -> Chunk | None:
    raw = path.read_text(encoding="utf-8")
    meta, body = split_frontmatter(raw)
    text = strip_image_markdown(body).strip()

    if not text:
        return None

    stem = path.stem
    image_refs = extract_image_refs(body)
    image_ref = image_refs[0].ref_path if image_refs else f"{stem}.png"
    normalized_ref = normalize_image_ref(image_ref)
    resolved = resolve_image_path(path, normalized_ref, data_root=data_root)

    if resolved is None and path.with_suffix(".png").is_file():
        resolved = path.with_suffix(".png").resolve()

    chunk_type = str(meta.get("chunk_type") or _default_chunk_type(stem, kind))
    node_ids = list(meta.get("graph_node_ids") or _graph_nodes_for_stem(stem, kind))
    factory = meta.get("factory") or ("КГМК" if kind == "regulation" else None)
    prefix = "regulation" if chunk_type == "constraint_regulation" else "scheme"
    chunk_id = str(meta.get("chunk_id") or f"{prefix}_{_slugify(stem)}")

    metadata = {
        "doc_id": meta.get("doc_id") or _slugify(stem),
        "md_path": str(path),
        "image_path": str(resolved) if resolved is not None else None,
        "image_ref": normalized_ref,
        "image_rel_path": (
            relative_to_data_root(resolved, data_root) if resolved is not None else None
        ),
        "original_format": meta.get("original_format") or "scheme_vlm",
        "title": meta.get("title") or stem,
    }
    metadata = {key: value for key, value in metadata.items() if value is not None}

    return Chunk(
        chunk_id=chunk_id,
        text=text,
        summary=str(meta.get("summary") or meta.get("title") or stem),
        source=str(meta.get("source") or path.name),
        factory=factory,
        section=str(meta.get("section") or ""),
        chunk_type=chunk_type,
        graph_node_ids=node_ids,
        metadata=metadata,
    )


def _default_chunk_type(stem: str, kind: str) -> str:
    if kind == "regulation":
        return "constraint_regulation"

    return "scheme_caption"


def _graph_nodes_for_stem(stem: str, kind: str) -> list[str]:
    hints = REGULATION_NODE_HINTS if kind == "regulation" else SCHEME_NODE_HINTS

    for prefix, node_ids in hints.items():
        if stem.startswith(prefix):
            return node_ids

    return _graph_nodes_for_file(Path(stem))
