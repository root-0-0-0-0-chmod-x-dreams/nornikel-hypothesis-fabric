from __future__ import annotations

import base64
import logging
import re
from pathlib import Path
from typing import Any, Dict, List

import httpx

from app.config import get_config
from app.image_manager import get_image_manager
from app.models import ConvertResult
from app.utils import FileType

logger = logging.getLogger("data_processor")

_VISION_PROMPT = """Analyze this image. Output ONLY ONE of:

1. TABLE — output ONLY the Markdown table:
| Header1 | Header2 |
|:--------|:--------|
| data    | data    |

2. DIAGRAM — output ONLY the Mermaid code (no ```):
flowchart TD
    A[Node] --> B[Process]

CRITICAL: Output ONLY the table or Mermaid code. NO other text, NO explanations, NO reasoning. Russian labels exactly as seen."""

_MERMAID_RE = re.compile(r"(?:graph |flowchart |sequenceDiagram|classDiagram|stateDiagram|erDiagram|gantt|pie)[\s\S]*", re.IGNORECASE)
_TABLE_RE = re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE)
_REASONING_PATTERNS = [
    r"(?i)(the user wants|let me|i need|i should|looking at|the prompt|the image|therefore|based on|first,|this is|analyze the|identify the|okay,|wait,)",
]


def _clean_output(text: str) -> str:
    text = text.strip()

    fence = re.search(r"```(?:mermaid)?\s*\n(.*?)\n\s*```", text, re.DOTALL)
    if fence:
        return fence.group(1).strip()

    mermaid = _MERMAID_RE.search(text)
    if mermaid:
        code = mermaid.group(0).strip()
        code = re.sub(r"\n\s*\n\s*(The user|Let me|I need|Okay|Looking|The prompt|Analyze|Based on|This is).*", "", code, flags=re.DOTALL)
        return code

    table = _TABLE_RE.search(text)
    if table:
        lines = text.split("\n")
        table_lines = [l for l in lines if re.match(r"^\s*\|", l)]
        return "\n".join(table_lines).strip()

    for pattern in _REASONING_PATTERNS:
        clean = re.sub(pattern + r".*?$", "", text, flags=re.MULTILINE | re.DOTALL)
        clean = clean.strip()
        if clean and len(clean) > 20:
            return clean

    return text.strip()


def _image_type_from_ext(suffix: str) -> str:
    mapping = {
        ".png": FileType.IMAGE_PNG.value,
        ".jpg": FileType.IMAGE_JPG.value,
        ".jpeg": FileType.IMAGE_JPEG.value,
        ".gif": FileType.IMAGE_GIF.value,
        ".bmp": FileType.IMAGE_BMP.value,
        ".tiff": FileType.IMAGE_TIFF.value,
        ".tif": FileType.IMAGE_TIFF.value,
        ".webp": FileType.IMAGE_WEBP.value,
    }
    return mapping.get(suffix.lower(), "image")


def _fallback_ocr(file_path: Path) -> str:
    try:
        import easyocr
        import io
        import sys
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            reader = easyocr.Reader(["ru", "en"], gpu=False, verbose=False)
        finally:
            sys.stdout = old_stdout
        results = reader.readtext(str(file_path))
        lines = []
        for bbox, text, conf in results:
            if conf > 0.3:
                lines.append(text)
        if lines:
            return "\n".join(lines)
    except ImportError:
        pass
    return ""


def convert_image(file_path: Path, original_filename: str) -> ConvertResult:
    errors: List[str] = []
    warnings: List[str] = []
    config = get_config()

    try:
        image_manager = get_image_manager()
        ref = image_manager.add_image(file_path, prefix="img")
        alt_text = file_path.stem

        with open(file_path, "rb") as f:
            img_bytes = f.read()
        b64 = base64.b64encode(img_bytes).decode()
        ext = file_path.suffix.lower().lstrip(".")
        mime = "image/" + ("jpeg" if ext in ("jpg", "jpeg") else ext)

        md_text = f"![{alt_text}]({ref})\n"
        analyzed = ""

        if config.vision_enabled:
            for attempt in range(1, config.vision_max_retries + 1):
                try:
                    content = _call_vision_api(b64, mime, config)
                    analyzed = _clean_output(content)
                    if analyzed and len(analyzed) > 10:
                        logger.info("vision_ok", extra={"attempt": attempt, "len": len(analyzed)})
                        break
                    logger.warning("vision_empty_output", extra={"attempt": attempt, "raw_len": len(content)})
                except Exception as e:
                    logger.warning("vision_attempt_failed", extra={"attempt": attempt, "error": str(e)[:200]})
                    if attempt == config.vision_max_retries:
                        warnings.append(f"Vision failed after {attempt} attempts: {e}")
            else:
                analyzed = ""

        if not analyzed:
            logger.info("vision_fallback_ocr")
            analyzed = _fallback_ocr(file_path)
            if analyzed:
                md_text += f"```text\n{analyzed}\n```\n"
                warnings.append("Used EasyOCR fallback — vision model unavailable")
            else:
                md_text += "\n"
                warnings.append("Vision and OCR both unavailable — image reference only")
        else:
            md_text += analyzed + "\n"

        return ConvertResult(
            success=True,
            original_filename=original_filename,
            file_type=_image_type_from_ext(file_path.suffix),
            markdown_content=md_text,
            images_extracted=1,
            metadata={"image_ref": ref, "vision_used": bool(analyzed) and analyzed != ""},
            warnings=warnings,
        )

    except Exception as e:
        logger.exception("image_conversion_failed")
        errors.append(str(e))
        return ConvertResult(
            success=False,
            original_filename=original_filename,
            file_type=_image_type_from_ext(file_path.suffix),
            errors=errors,
        )


def _call_vision_api(b64: str, mime: str, config) -> str:
    payload = {
        "model": config.vision_model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": _VISION_PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ],
        }],
        "temperature": 0.1,
        "max_tokens": 8000,
    }

    with httpx.Client(timeout=config.vision_timeout) as client:
        resp = client.post(f"{config.llm_service_url}/chat", json=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"LLM service returned {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return content or ""
