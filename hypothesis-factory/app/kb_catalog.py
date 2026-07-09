"""Discover knowledge-base documents from GraphRAG case data on disk."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from app.util.md_frontmatter import split_frontmatter

BOOK_DISPLAY_NAMES: dict[str, str] = {
    "geokniga_lodeyshchikovvvtehnologiyaizvlecheniyazolotaiserebraizupornyh1": (
        "Лодейщиков — Технология извлечения золота и серебра"
    ),
    "geokniga_flotacionnye_metody_obogashcheniya_0": "Флотационные методы обогащения",
    "geokniga_metallurgiya_blagorodnyh_metallov_0": "Металлургия благородных металлов",
    "geokniga_tehnologiyaobogashcheniyapoleznyhiskopaemyh": (
        "Технология обогащения полезных ископаемых"
    ),
    "tehnologiya_izvlecheniya_zolota_i_serebra_iz_upornogo_zolotosoderzhaschego": (
        "Технология извлечения золота и серебра (упорные руды)"
    ),
}

TAILINGS_FILES: tuple[tuple[str, str, str], ...] = (
    ("kb-tails-kgmk", "КГМК", "Хвосты КГМК.xlsx"),
    ("kb-tails-nof-vkr", "НОФ (вкрап.)", "Хвосты НОФ Вкр.xlsx"),
    ("kb-tails-nof-med", "НОФ (медь)", "Хвосты НОФ мед.xlsx"),
    ("kb-tails-tof", "ТОФ", "Хвосты ТОФ_2.xlsx"),
)

HYPOTHESIS_DOCX: tuple[tuple[str, str], ...] = (
    ("kb-hyp-kgmk", "Гипотезы КГМК.docx"),
    ("kb-hyp-nof-vkr", "Гипотезы НОФ вкр.docx"),
    ("kb-hyp-nof-med", "Гипотезы НОФ мед.docx"),
    ("kb-hyp-tof", "Гипотезы ТОФ.docx"),
)


def graphrag_data_root() -> Path:
    root = Path(os.getenv("GRAPHRAG_DATA_ROOT", "/app/data/case")).expanduser()
    return root


def _doc_entry(
    *,
    doc_id: str,
    name: str,
    doc_type: str,
    description: str,
    chunk_count: int | None = None,
    preview_kind: str,
    relative_path: str,
    indexed: bool = True,
) -> dict[str, Any]:
    return {
        "id": doc_id,
        "name": name,
        "type": doc_type,
        "origin": "knowledge_base",
        "pinned": True,
        "status": "ready",
        "chunkCount": chunk_count,
        "description": description,
        "previewAvailable": True,
        "previewKind": preview_kind,
        "relativePath": relative_path,
        "indexedInGraphRag": indexed,
        "url": f"/api/v1/context/documents/{doc_id}/file",
    }


def _read_frontmatter(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        meta, _ = split_frontmatter(text)
        return meta
    except OSError:
        return {}


def discover_kb_documents(root: Path | None = None) -> list[dict[str, Any]]:
    data_root = root or graphrag_data_root()
    if not data_root.is_dir():
        return _fallback_documents()

    docs: list[dict[str, Any]] = []

    for doc_id, factory, filename in TAILINGS_FILES:
        rel = filename
        path = data_root / rel
        if path.is_file():
            docs.append(
                _doc_entry(
                    doc_id=doc_id,
                    name=f"LossForm {factory} — анализ хвостов",
                    doc_type="xlsx",
                    description=f"Excel: статьи потерь Ni/Cu, фабрика {factory}.",
                    chunk_count=4 if factory == "КГМК" else None,
                    preview_kind="spreadsheet",
                    relative_path=rel,
                )
            )

    md_root = data_root / "Дополнительные материалы" / "md"
    if md_root.is_dir():
        for book_dir in sorted(md_root.iterdir()):
            if not book_dir.is_dir() or book_dir.name.startswith("_"):
                continue
            paras = sorted(book_dir.glob("*.md"))
            meta_path = md_root / "_book.meta.md"
            meta = _read_frontmatter(meta_path) if meta_path.is_file() else {}
            doc_key = book_dir.name
            title = BOOK_DISPLAY_NAMES.get(doc_key) or meta.get("title") or doc_key
            source_pdf = meta.get("original_pdf") or meta.get("source") or f"{doc_key}.pdf"
            docs.append(
                _doc_entry(
                    doc_id=f"kb-book-{doc_key}",
                    name=title,
                    doc_type="pdf",
                    description=f"Учебник/справочник, {len(paras)} параграфов в Qdrant. Источник: {source_pdf}",
                    chunk_count=len(paras),
                    preview_kind="book",
                    relative_path=str(book_dir.relative_to(data_root)),
                )
            )

    schemes_dir = data_root / "Схемы флотации"
    if schemes_dir.is_dir():
        for md_path in sorted(schemes_dir.glob("*.md")):
            meta = _read_frontmatter(md_path)
            title = meta.get("title") or md_path.stem
            stem = md_path.stem
            docs.append(
                _doc_entry(
                    doc_id=f"kb-scheme-{_slug(stem)}",
                    name=f"Схема: {title}",
                    doc_type="other",
                    description="VLM-транскрипт технологической схемы флотации.",
                    chunk_count=1,
                    preview_kind="scheme",
                    relative_path=str(md_path.relative_to(data_root)),
                )
            )

    reg_dir = data_root / "Регламенты"
    if reg_dir.is_dir():
        for md_path in sorted(reg_dir.glob("*.md")):
            meta = _read_frontmatter(md_path)
            title = meta.get("title") or md_path.stem
            factory = meta.get("factory", "")
            docs.append(
                _doc_entry(
                    doc_id=f"kb-regulation-{_slug(md_path.stem)}",
                    name=f"Регламент: {title}",
                    doc_type="docx",
                    description=f"Технологический регламент{' (' + factory + ')' if factory else ''}.",
                    chunk_count=1,
                    preview_kind="regulation",
                    relative_path=str(md_path.relative_to(data_root)),
                )
            )

    for doc_id, filename in HYPOTHESIS_DOCX:
        rel = filename
        if (data_root / rel).is_file():
            docs.append(
                _doc_entry(
                    doc_id=doc_id,
                    name=filename.replace(".docx", ""),
                    doc_type="docx",
                    description="Справочный документ с примерами гипотез (не индексируется в Qdrant).",
                    chunk_count=None,
                    preview_kind="document",
                    relative_path=rel,
                    indexed=False,
                )
            )

    return docs if docs else _fallback_documents()


def _slug(text: str) -> str:
    value = re.sub(r"[^\w\-]+", "-", text.lower(), flags=re.UNICODE)
    return re.sub(r"-+", "-", value).strip("-") or "doc"


def _fallback_documents() -> list[dict[str, Any]]:
    from app.context import KB_DOCUMENTS

    return [dict(doc, previewAvailable=False, indexedInGraphRag=True) for doc in KB_DOCUMENTS]


def get_kb_document(doc_id: str, root: Path | None = None) -> dict[str, Any] | None:
    for doc in discover_kb_documents(root):
        if doc["id"] == doc_id:
            return doc
    return None


def resolve_document_path(doc_id: str, root: Path | None = None) -> Path | None:
    doc = get_kb_document(doc_id, root)
    if not doc:
        return None
    rel = doc.get("relativePath")
    if not rel:
        return None
    path = (root or graphrag_data_root()) / str(rel)
    return path if path.exists() else None
