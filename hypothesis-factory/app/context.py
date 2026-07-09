"""Knowledge-base context documents and retrieved paragraph aggregation."""

from __future__ import annotations

from typing import Any

from app.sources import knowledge_sources_to_api, merge_knowledge_sources

from app.kb_catalog import discover_kb_documents

KB_DOCUMENTS: list[dict[str, Any]] = [
    {
        "id": "kb-lossform-kgmk",
        "name": "LossForm КГМК — анализ потерь Ni/Cu в хвостах",
        "type": "xlsx",
        "origin": "knowledge_base",
        "pinned": True,
        "status": "ready",
        "chunkCount": 4,
        "description": "Excel LossForm: статьи потерь по минералам и фракциям. Узлы графа + Qdrant.",
    },
    {
        "id": "kb-book-lodeyshchikov",
        "name": "Лодейщиков — Технология извлечения золота и серебра",
        "type": "pdf",
        "origin": "knowledge_base",
        "pinned": True,
        "status": "ready",
        "chunkCount": 926,
        "description": "Учебник обогащения, ~926 параграфов в Qdrant.",
    },
    {
        "id": "kb-book-flotation",
        "name": "Флотационные методы обогащения",
        "type": "pdf",
        "origin": "knowledge_base",
        "pinned": True,
        "status": "ready",
        "chunkCount": 1200,
        "description": "Справочник по флотации сульфидных руд.",
    },
    {
        "id": "kb-book-metallurgy",
        "name": "Металлургия благородных металлов",
        "type": "pdf",
        "origin": "knowledge_base",
        "pinned": True,
        "status": "ready",
        "chunkCount": 890,
        "description": "Процессы извлечения и обогащения.",
    },
    {
        "id": "kb-book-tehnologiya",
        "name": "Технология обогащения полезных ископаемых",
        "type": "pdf",
        "origin": "knowledge_base",
        "pinned": True,
        "status": "ready",
        "chunkCount": 1100,
        "description": "Классический учебник по обогащению.",
    },
    {
        "id": "kb-schemes-flotation",
        "name": "Схемы флотации ТОФ (VLM-транскрипты)",
        "type": "other",
        "origin": "knowledge_base",
        "pinned": True,
        "status": "ready",
        "chunkCount": 12,
        "description": "Технологические схемы: узлы графа equip_*, process_*.",
    },
    {
        "id": "kb-regulations",
        "name": "Регламенты и типовое оборудование",
        "type": "docx",
        "origin": "knowledge_base",
        "pinned": True,
        "status": "ready",
        "chunkCount": 4,
        "description": "Ограничения CAPEX, списки оборудования.",
    },
]


def get_kb_documents() -> list[dict[str, Any]]:
    return discover_kb_documents()


def collect_retrieved_paragraphs(
    validated: list[dict[str, Any]],
    global_sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged = list(global_sources)
    for hyp in validated:
        merged = merge_knowledge_sources(merged, hyp.get("knowledge_sources") or [])
    return knowledge_sources_to_api(merged)
