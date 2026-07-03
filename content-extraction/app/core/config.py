from dataclasses import dataclass
from functools import lru_cache
import os


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    max_pages: int = 4
    page_timeout: int = 30
    user_agent: str = DEFAULT_USER_AGENT
    headless: bool = True
    stealth: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        max_pages=int(os.getenv("MAX_PAGES", "4")),
        page_timeout=int(os.getenv("PAGE_TIMEOUT", "30")),
        user_agent=os.getenv("USER_AGENT", DEFAULT_USER_AGENT),
        headless=_get_bool("HEADLESS", True),
        stealth=_get_bool("STEALTH", True),
    )
