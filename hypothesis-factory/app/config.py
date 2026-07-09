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
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8003")))

    llm_service_url: str = field(
        default_factory=lambda: os.getenv("LLM_SERVICE_URL", "http://llm-service:8000/api/v1")
    )
    deepseek_model: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    )
    deepseek_api_key: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", "")
    )
    deepseek_base_url: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    )

    rabbitmq_host: str = field(
        default_factory=lambda: os.getenv("RABBITMQ_HOST", "194.67.116.167")
    )
    rabbitmq_port: int = field(
        default_factory=lambda: int(os.getenv("RABBITMQ_PORT", "5672"))
    )
    rabbitmq_user: str = field(
        default_factory=lambda: os.getenv("RABBITMQ_USER", "guest")
    )
    rabbitmq_pass: str = field(
        default_factory=lambda: os.getenv("RABBITMQ_PASS", "guest")
    )

    data_processor_url: str = field(
        default_factory=lambda: os.getenv("DATA_PROCESSOR_URL", "http://data-processor:8001")
    )
    content_extraction_url: str = field(
        default_factory=lambda: os.getenv("CONTENT_EXTRACTION_URL", "http://194.67.116.167:8005")
    )

    default_hypotheses_count: int = field(
        default_factory=lambda: int(os.getenv("DEFAULT_HYPOTHESES_COUNT", "2"))
    )
    max_agent_iterations: int = field(
        default_factory=lambda: int(os.getenv("MAX_AGENT_ITERATIONS", "2"))
    )
    agent_timeout: int = field(
        default_factory=lambda: int(os.getenv("AGENT_TIMEOUT", "300"))
    )

    reports_dir: str = field(
        default_factory=lambda: os.getenv("REPORTS_DIR", "/app/reports")
    )
    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )


_config: Optional[Config] = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config
