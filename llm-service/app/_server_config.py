import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH)


@dataclass(frozen=True)
class Config:
    yandex_folder_id: str = field(
        default_factory=lambda: os.getenv("YANDEX_FOLDER_ID", "")
    )
    yandex_api_key: str = field(
        default_factory=lambda: os.getenv("YANDEX_API_KEY", "")
    )
    yandex_base_url: str = field(
        default_factory=lambda: os.getenv(
            "YANDEX_BASE_URL", "https://ai.api.cloud.yandex.net/v1"
        )
    )
    deepseek_api_key: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", "")
    )
    deepseek_model: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    )
    deepseek_base_url: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    )
    deepseek_anthropic_base_url: str = field(
        default_factory=lambda: os.getenv(
            "DEEPSEEK_ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic"
        )
    )

    default_model: str = field(
        default_factory=lambda: os.getenv("DEFAULT_MODEL", "aliceai-llm")
    )
    model_timeout: int = field(
        default_factory=lambda: int(os.getenv("MODEL_TIMEOUT", "120"))
    )
    model_max_retries: int = field(
        default_factory=lambda: int(os.getenv("MODEL_MAX_RETRIES", "3"))
    )

    max_concurrent_requests: int = field(
        default_factory=lambda: int(os.getenv("MAX_CONCURRENT_REQUESTS", "10"))
    )
    queue_max_size: int = field(
        default_factory=lambda: int(os.getenv("QUEUE_MAX_SIZE", "1000"))
    )
    request_timeout_seconds: int = field(
        default_factory=lambda: int(os.getenv("REQUEST_TIMEOUT_SECONDS", "300"))
    )

    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )
    log_format: str = field(
        default_factory=lambda: os.getenv(
            "LOG_FORMAT", "json"
        )
    )

    health_check_interval: int = field(
        default_factory=lambda: int(os.getenv("HEALTH_CHECK_INTERVAL", "60"))
    )
    models_cache_ttl: int = field(
        default_factory=lambda: int(os.getenv("MODELS_CACHE_TTL", "300"))
    )

    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))

    @property
    def is_configured(self) -> bool:
        return bool(self.yandex_folder_id and self.yandex_api_key)

    @property
    def is_yandex_configured(self) -> bool:
        return self.is_configured

    @property
    def is_deepseek_configured(self) -> bool:
        return bool(self.deepseek_api_key)

    @property
    def has_any_provider(self) -> bool:
        return self.is_yandex_configured or self.is_deepseek_configured


_config: Optional[Config] = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config
