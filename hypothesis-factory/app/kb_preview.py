"""Load preview content for knowledge-base documents."""

from __future__ import annotations

import re
from pathlib import Path

import httpx

from app.config import get_config
from app.kb_catalog import get_kb_document, graphrag_data_root, resolve_document_path
from app.util.md_frontmatter import split_frontmatter

MAX_BOOK_PARAS = 120
MAX_MARKDOWN_CHARS = 180_000


def _rewrite_asset_links(markdown: str, doc_id: str) -> str:
    def repl(match: re.Match[str]) -> str:
        alt = match.group(1)
        target = match.group(2).strip()
        if target.startswith("http://") or target.startswith("https://"):
            return match.group(0)
        filename = Path(target).name
        url = f"/api/v1/context/documents/{doc_id}/assets/{filename}"
        return f"![{alt}]({url})"

    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", repl, markdown)


def _strip_frontmatter(text: str) -> tuple[dict[str, str], str]:
    meta, body = split_frontmatter(text)
    return meta, body.strip()


def preview_book_markdown(book_dir: Path, doc_id: str) -> tuple[str, str, str]:
    parts: list[str] = []
    title = book_dir.name
    paras = sorted(book_dir.glob("*.md"))[:MAX_BOOK_PARAS]
    for para_path in paras:
        try:
            raw = para_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        meta, body = _strip_frontmatter(raw)
        title = meta.get("title") or title
        page = meta.get("page")
        para_idx = meta.get("paragraph_index")
        header = f"### Стр. {page}, §{para_idx}" if page else f"### {para_path.stem}"
        if body:
            parts.append(f"{header}\n\n{body}")
    markdown = "\n\n---\n\n".join(parts)
    if len(paras) < len(list(book_dir.glob("*.md"))):
        markdown += (
            f"\n\n---\n\n*Показаны первые {len(paras)} параграфов из "
            f"{len(list(book_dir.glob('*.md')))}. Полный текст — в Qdrant/GraphRAG.*"
        )
    markdown = markdown[:MAX_MARKDOWN_CHARS]
    return title, markdown, markdown[:500]


def preview_md_file(md_path: Path, doc_id: str) -> tuple[str, str, str]:
    raw = md_path.read_text(encoding="utf-8", errors="replace")
    meta, body = _strip_frontmatter(raw)
    title = meta.get("title") or md_path.stem
    markdown = _rewrite_asset_links(body or raw, doc_id)
    return title, markdown, markdown[:500]


async def convert_office_to_markdown(file_path: Path) -> tuple[str, str, str]:
    config = get_config()
    convert_url = f"{config.data_processor_url.rstrip('/')}/api/v1/convert"
    with file_path.open("rb") as handle:
        files = {"file": (file_path.name, handle, "application/octet-stream")}
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(convert_url, files=files)
    if resp.status_code != 200:
        raise RuntimeError(f"Convert failed: HTTP {resp.status_code}")
    data = resp.json()
    markdown = str(
        data.get("markdown_content") or data.get("markdown") or data.get("content") or ""
    )
    title = file_path.stem
    return title, markdown[:MAX_MARKDOWN_CHARS], markdown[:500]


async def build_preview_payload_async(doc_id: str) -> dict:
    doc = get_kb_document(doc_id)
    if not doc:
        raise FileNotFoundError(doc_id)

    path = resolve_document_path(doc_id)
    if path is None:
        raise FileNotFoundError(doc_id)

    kind = doc.get("previewKind") or "document"
    title = doc["name"]
    markdown = ""
    excerpt = doc.get("description") or ""

    if kind == "book" and path.is_dir():
        title, markdown, excerpt = preview_book_markdown(path, doc_id)
    elif path.suffix.lower() == ".md":
        title, markdown, excerpt = preview_md_file(path, doc_id)
    elif path.suffix.lower() in {".xlsx", ".xls", ".docx", ".doc"}:
        title, markdown, excerpt = await convert_office_to_markdown(path)
    else:
        raise ValueError(f"Unsupported preview: {path.suffix}")

    return {
        "documentId": doc_id,
        "title": title,
        "markdown": markdown,
        "text": markdown,
        "excerpt": excerpt,
        "html": "",
        "metadata": {
            "title": title,
            "description": doc.get("description"),
            "source": doc.get("name"),
            "indexedInGraphRag": doc.get("indexedInGraphRag", True),
        },
    }


def resolve_asset_path(doc_id: str, filename: str) -> Path | None:
    doc = get_kb_document(doc_id)
    if not doc:
        return None
    root = graphrag_data_root()
    rel = doc.get("relativePath")
    if not rel:
        return None
    base = root / Path(str(rel)).parent
    candidate = base / filename
    if candidate.is_file():
        return candidate
    # schemes/regulations: png next to md
    alt = root / Path(str(rel)).parent / filename
    return alt if alt.is_file() else None
