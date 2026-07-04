"""Ontology: node types, relations, and data-source mapping."""

from __future__ import annotations

from enum import StrEnum


class NodeType(StrEnum):
    """MVP node labels (10 types for hackathon demo)."""

    ORE = "Ore"
    MINERAL = "Mineral"
    SIZE_CLASS = "SizeClass"
    LOSS_FORM = "LossForm"
    PROCESS = "Process"
    EQUIPMENT = "Equipment"
    PARAMETER = "Parameter"
    REAGENT = "Reagent"
    MECHANISM = "Mechanism"
    INTERVENTION = "Intervention"
    HYPOTHESIS = "Hypothesis"
    PASSAGE = "Passage"
    SOURCE = "Source"
    KPI = "KPI"
    FACTORY = "Factory"
    METAL = "Metal"


class RelationType(StrEnum):
    """Allowed edge types in knowledge graph."""

    CONTAINS_MINERAL = "CONTAINS_MINERAL"
    CARRIES_METAL = "CARRIES_METAL"
    IN_SIZECLASS = "IN_SIZECLASS"
    OF_MINERAL = "OF_MINERAL"
    RECOVERABLE = "RECOVERABLE"
    NON_RECOVERABLE = "NON_RECOVERABLE"
    USES_EQUIPMENT = "USES_EQUIPMENT"
    HAS_PARAMETER = "HAS_PARAMETER"
    USES_REAGENT = "USES_REAGENT"
    INFLUENCES = "INFLUENCES"
    EXPLAINED_BY = "EXPLAINED_BY"
    ADDRESSED_BY = "ADDRESSED_BY"
    TARGETS = "TARGETS"
    PROPOSES_CHANGE = "PROPOSES_CHANGE"
    EVIDENCED_BY = "EVIDENCED_BY"
    PART_OF = "PART_OF"
    NEXT_PASSAGE = "NEXT_PASSAGE"
    MENTIONS = "MENTIONS"
    SHARES_TOPIC = "SHARES_TOPIC"
    SUPPORTS_HYPOTHESIS = "SUPPORTS_HYPOTHESIS"
    HAS_PASSAGE = "HAS_PASSAGE"
    RELATED_SOURCE = "RELATED_SOURCE"
    CONFLICTS_WITH = "CONFLICTS_WITH"
    COMBINES_WITH = "COMBINES_WITH"
    SUPERSEDES = "SUPERSEDES"
    VALIDATED_ON = "VALIDATED_ON"
    RELATED_MECHANISM = "RELATED_MECHANISM"
    RELATED_TO = "RELATED_TO"
    HAS_LOSS = "HAS_LOSS"
    HAS_EQUIPMENT = "HAS_EQUIPMENT"


# What ingestion writes into the graph
DATA_SOURCE_MAPPING: dict[str, str] = {
    "excel_bucket": "Auto: LossForm nodes from Excel хвостов parser",
    "pdf_text": "LLM/NER: Mechanism, Process, Reagent from справочники",
    "scheme_caption": "VLM: Equipment, Process, FEEDS/USES triplets",
    "constraint_regulation": "Structured: regulation excerpts + equipment topology",
    "constraint_budget": "Expert: budget tier → allowed intervention types",
    "constraint_example": "Reference: эталонные гипотезы мозгового штурма",
    "external_text": "External: web/PDF snippet with auto entity linking",
    "vlm_triplet": "VLM/LLM: S-P-O edges from PNG/PDF schemes",
    "expert_approve": "Expert Studio: VALIDATED_ON, SUPERSEDES edges",
    "genetic_merge": "Verification: COMBINES_WITH between Hypothesis nodes",
}

# Required LossForm attributes when built from Excel
LOSS_FORM_ATTRS = (
    "factory",
    "size_class",
    "mineral_form",
    "metal",
    "tonnes",
    "recoverable",
)
