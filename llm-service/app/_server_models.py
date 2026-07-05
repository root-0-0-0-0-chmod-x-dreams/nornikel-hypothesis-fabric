from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ModelStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"
    UNKNOWN = "unknown"


class ModelInfo(BaseModel):
    model_id: str
    display_name: str
    status: ModelStatus = ModelStatus.UNKNOWN
    max_tokens: int = 1000
    supports_streaming: bool = True
    last_checked_at: Optional[str] = None


class Message(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    model: Optional[str] = None
    messages: List[Message]
    temperature: float = Field(default=0.8, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1500, ge=1, le=32000)
    stream: bool = False
    priority: int = Field(default=0, ge=0, le=10)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatChoice(BaseModel):
    index: int = 0
    message: Message
    finish_reason: Optional[str] = None


class ChatResponse(BaseModel):
    request_id: str
    model: str
    choices: List[ChatChoice]
    usage: TokenUsage
    created_at: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
    request_id: Optional[str] = None


class QueueStatus(BaseModel):
    queue_size: int
    active_requests: int
    max_concurrent: int
    models_available: List[str]
    models_unavailable: List[str]


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    uptime_seconds: float
    models_count: int
    yandex_configured: bool
    deepseek_configured: bool
