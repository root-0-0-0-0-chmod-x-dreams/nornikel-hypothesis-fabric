#!/usr/bin/env python3
"""Bootstrap knowledge base from real case files."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from graphrag.bootstrap import bootstrap


def main() -> None:
    loaded = bootstrap()
    print(json.dumps(loaded.stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
