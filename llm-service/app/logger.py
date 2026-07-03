import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)
        for key in ("model", "request_id", "duration_ms", "tokens_used"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)
        return json.dumps(log_entry, ensure_ascii=False)


class PlainFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        extra_parts = []
        for key in ("model", "request_id", "duration_ms", "tokens_used"):
            if hasattr(record, key):
                extra_parts.append(f"{key}={getattr(record, key)}")
        base = f"{self.formatTime(record)} [{record.levelname}] {record.name}: {record.getMessage()}"
        if extra_parts:
            base += " | " + " ".join(extra_parts)
        if record.exc_info and record.exc_info[1]:
            base += "\n" + self.formatException(record.exc_info)
        return base


def setup_logging(level: str = "INFO", fmt: str = "json") -> logging.Logger:
    logger = logging.getLogger("llm_service")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    if fmt == "json":
        formatter = JSONFormatter()
    else:
        formatter = PlainFormatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

    return logger


_logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    global _logger
    if _logger is None:
        from .config import get_config

        config = get_config()
        _logger = setup_logging(config.log_level, config.log_format)
    return _logger
