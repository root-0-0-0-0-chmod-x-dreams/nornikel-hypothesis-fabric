import json
import logging
import re
from typing import Optional

import httpx

from app.config import get_config

logger = logging.getLogger("hypothesis_factory")
config = get_config()


def call_llm(
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 8000,
    model: Optional[str] = None,
) -> str:
    """Call DeepSeek via llm-service. Returns response text."""
    payload = {
        "model": model or config.deepseek_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    with httpx.Client(timeout=config.agent_timeout) as client:
        resp = client.post(f"{config.llm_service_url}/chat", json=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"LLM error {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return content or ""


def parse_json_from_text(text: str) -> dict | list:
    """Extract JSON object or array from LLM response."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text[:-3]
    match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}
