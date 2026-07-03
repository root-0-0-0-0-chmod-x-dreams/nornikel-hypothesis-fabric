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
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8001")))

    images_dir: str = field(
        default_factory=lambda: os.getenv("IMAGES_DIR", "/app/images")
    )
    uploads_dir: str = field(
        default_factory=lambda: os.getenv("UPLOADS_DIR", "/app/uploads")
    )
    output_dir: str = field(
        default_factory=lambda: os.getenv("OUTPUT_DIR", "/app/output")
    )

    max_file_size_mb: int = field(
        default_factory=lambda: int(os.getenv("MAX_FILE_SIZE_MB", "100"))
    )
    cleanup_temp_after_minutes: int = field(
        default_factory=lambda: int(os.getenv("CLEANUP_TEMP_AFTER_MINUTES", "60"))
    )

    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


_config: Optional[Config] = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config
