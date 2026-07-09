"""Shared YAML-frontmatter parsing for MD ingestion."""

from __future__ import annotations

import json
import re

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def split_frontmatter(raw: str) -> tuple[dict, str]:
    match = _FRONTMATTER_RE.match(raw)

    if not match:
        return {}, raw.strip()

    return parse_frontmatter_text(match.group(1)), raw[match.end() :].strip()


def parse_frontmatter_text(text: str) -> dict:
    meta: dict = {}

    for line in text.splitlines():
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        if ":" not in stripped:
            continue

        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        meta[key] = _parse_value(value)

    return meta


def _parse_value(value: str):
    if value.startswith("[") or value.startswith("{") or value[0:1].isdigit() or value in {
        "true",
        "false",
        "null",
    }:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value.strip('"')

    return value.strip('"')
