import base64
import logging
from pathlib import Path
from typing import Optional

import httpx

from app.config import get_config

logger = logging.getLogger("hypothesis_factory")
config = get_config()


def analyze_image(image_path: str) -> str:
    """
    Send an image to the data-processor for VLM analysis.
    Returns markdown with table or Mermaid diagram.
    """
    try:
        path = Path(image_path)
        if not path.exists():
            return f"[image not found: {image_path}]"

        with open(path, "rb") as f:
            img_bytes = f.read()

        b64 = base64.b64encode(img_bytes).decode()
        ext = path.suffix.lower().lstrip(".")
        mime = f"image/{'jpeg' if ext in ('jpg','jpeg') else ext}"

        payload = {
            "model": "qwen3.6-35b-a3b",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": (
                        "Analyze this image. Output ONLY ONE of:\n"
                        "1. TABLE — output ONLY Markdown table\n"
                        "2. DIAGRAM — output ONLY Mermaid code (no ```)\n"
                        "NO other text, NO explanations, NO reasoning. Russian labels exactly as seen."
                    )},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ],
            }],
            "temperature": 0.1,
            "max_tokens": 8000,
        }

        with httpx.Client(timeout=180) as client:
            resp = client.post(f"{config.llm_service_url}/chat", json=payload)
            if resp.status_code != 200:
                return f"[vision error: {resp.status_code}]"

            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")

    except Exception as e:
        logger.warning("vision_tool_failed", extra={"error": str(e)[:200]})
        return f"[vision unavailable: {str(e)[:200]}]"
