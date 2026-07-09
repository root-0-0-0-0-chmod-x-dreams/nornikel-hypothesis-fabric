"""Map GraphRAG chunks → frontend source contract."""

from __future__ import annotations

from typing import Any


def chunks_to_knowledge_sources(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for chunk in chunks:
        if chunk.get("status"):
            continue
        chunk_id = str(chunk.get("chunk_id") or "")
        if not chunk_id:
            continue
        citation = chunk.get("citation") or {}
        text = str(chunk.get("text") or chunk.get("content") or "")
        excerpt = str(citation.get("excerpt") or text[:320])
        sources.append(
            {
                "chunk_id": chunk_id,
                "title": citation.get("display_ref") or chunk.get("source") or chunk_id,
                "type": citation.get("source_type") or "db",
                "excerpt": excerpt,
                "relevance": "",
                "page": citation.get("page"),
                "paragraph_index": citation.get("paragraph_index"),
                "source_url": citation.get("source_url"),
                "citation": citation,
            }
        )
    return sources


def merge_knowledge_sources(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for group in groups:
        for item in group:
            chunk_id = str(item.get("chunk_id") or "")
            key = chunk_id or str(item.get("title") or "")
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def knowledge_sources_to_api(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    for src in sources:
        chunk_id = src.get("chunk_id")
        citation = src.get("citation") or {}
        entry: dict[str, Any] = {
            "title": src.get("title") or chunk_id or "Источник",
            "type": src.get("type") or "db",
            "excerpt": src.get("excerpt") or src.get("relevance") or "",
        }
        if chunk_id:
            entry["chunkId"] = chunk_id
            entry["url"] = f"/api/v1/sources/chunks/{chunk_id}"
        elif src.get("source_url"):
            entry["url"] = src["source_url"]
        page = src.get("page") if src.get("page") is not None else citation.get("page")
        para = (
            src.get("paragraph_index")
            if src.get("paragraph_index") is not None
            else citation.get("paragraph_index")
        )
        if page is not None:
            entry["page"] = page
        if para is not None:
            entry["paragraphIndex"] = para
        details.append(entry)
    return details
