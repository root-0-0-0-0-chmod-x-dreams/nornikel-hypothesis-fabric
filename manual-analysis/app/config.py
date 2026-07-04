import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH)


@dataclass(frozen=True)
class Config:
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8002")))

    llm_service_url: str = field(
        default_factory=lambda: os.getenv("LLM_SERVICE_URL", "http://localhost:8000/api/v1")
    )
    llm_enabled: bool = field(
        default_factory=lambda: os.getenv("LLM_ENABLED", "true").lower() == "true"
    )
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "aliceai-llm"))
    llm_timeout: int = field(default_factory=lambda: int(os.getenv("LLM_TIMEOUT", "120")))

    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))


_config: Optional[Config] = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config
