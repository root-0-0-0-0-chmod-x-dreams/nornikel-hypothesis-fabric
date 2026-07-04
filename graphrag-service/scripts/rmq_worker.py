#!/usr/bin/env python3
"""Run GraphRAG RabbitMQ worker."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from graphrag.messaging.worker import run_worker

if __name__ == "__main__":
    run_worker()
