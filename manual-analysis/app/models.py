from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class AnalysisRow(BaseModel):
    analysis: str = Field(alias="Анализ")
    loss_item: str = Field(alias="Статья_Потерь")
    metal_1_t: float = Field(alias="Металл_1_т")
    metal_2_t: float = Field(alias="Металл_2_т")
    extra: str = Field(default="", alias="Доп_Инфо")

    class Config:
        populate_by_name = True


class AnalysisResult(BaseModel):
    success: bool
    source_file: str
    method: str
    rows: List[AnalysisRow]
    errors: List[str] = Field(default_factory=list)


class LLMStatus(BaseModel):
    available: bool
    url: str
    model: str
    error: str = ""


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    uptime_seconds: float = 0.0
    llm: LLMStatus
