"""Build vector/graph chunks from Markdown image references."""

from __future__ import annotations

from pathlib import Path

from graphrag.ingestion.excel_parser import _slugify
from graphrag.ingestion.md_image_refs import (
    MarkdownImageRef,
    relative_to_data_root,
    resolve_image_path,
)
from graphrag.models import Chunk


def image_ref_to_chunk(
    meta: dict,
    md_path: Path,
    image_ref: MarkdownImageRef,
    *,
    data_root: Path | None = None,
    suffix: str | None = None,
) -> Chunk:
    resolved = resolve_image_path(md_path, image_ref.ref_path, data_root=data_root)
    ref_name = Path(image_ref.ref_path).name
    alt = image_ref.alt.strip() or ref_name
    doc_id = str(meta.get("doc_id") or md_path.parent.name or md_path.stem)

    chunk_id = str(
        meta.get("chunk_id")
        or _default_image_chunk_id(doc_id, ref_name, suffix=suffix)
    )

    if resolved is not None and resolved.is_file():
        caption = str(meta.get("summary") or meta.get("image_caption") or alt)
        text = f"{caption}\n\nИллюстрация: {resolved.name}"
        image_path = str(resolved)
        image_rel = relative_to_data_root(resolved, data_root) if data_root else None
        image_missing = False
    else:
        caption = alt or ref_name
        text = f"{caption}\n\n[image not found: {image_ref.ref_path}]"
        image_path = image_ref.ref_path
        image_rel = None
        image_missing = True

    metadata = {
        "doc_id": doc_id,
        "title": meta.get("title"),
        "page": meta.get("page"),
        "paragraph_index": meta.get("paragraph_index"),
        "md_path": str(md_path),
        "image_path": image_path,
        "image_ref": image_ref.ref_path,
        "image_rel_path": image_rel,
        "image_alt": alt,
        "image_missing": image_missing,
        "original_format": meta.get("original_format") or _guess_format(ref_name),
    }
    metadata = {key: value for key, value in metadata.items() if value is not None}

    return Chunk(
        chunk_id=chunk_id,
        text=text,
        summary=caption,
        source=str(meta.get("source") or ref_name),
        factory=meta.get("factory"),
        section=str(meta.get("section") or ""),
        chunk_type=str(meta.get("chunk_type") or "md_image"),
        graph_node_ids=list(meta.get("graph_node_ids") or []),
        metadata=metadata,
    )


def _default_image_chunk_id(doc_id: str, ref_name: str, *, suffix: str | None) -> str:
    stem = _slugify(Path(ref_name).stem)
    parts = ["image", _slugify(doc_id), stem]

    if suffix is not None:
        parts.append(suffix)

    return "_".join(parts)


def _guess_format(ref_name: str) -> str:
    suffix = Path(ref_name).suffix.lower().lstrip(".")

    return suffix or "image"
