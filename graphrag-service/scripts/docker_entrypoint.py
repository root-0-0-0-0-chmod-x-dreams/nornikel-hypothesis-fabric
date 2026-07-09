#!/usr/bin/env python3
"""Docker entrypoint: wait for Qdrant, bootstrap if empty, start RMQ worker."""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

logger = logging.getLogger(__name__)


def _wait_qdrant(url: str, *, timeout_sec: int = 120) -> None:
    import httpx

    deadline = time.monotonic() + timeout_sec
    target = url.rstrip("/")

    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"{target}/collections", timeout=3.0)

            if response.status_code == 200:
                logger.info("Qdrant ready at %s", target)

                return
        except Exception as exc:
            logger.debug("Qdrant not ready yet: %s", exc)

        time.sleep(2)

    raise TimeoutError(f"Qdrant not ready after {timeout_sec}s: {target}")


def _bootstrap_if_needed() -> None:
    from graphrag.ingestion.pipeline import _qdrant_has_indexed_data, load_knowledge_base
    from graphrag.ingestion.paths import resolve_data_root
    from graphrag.vector_factory import create_vector_store

    data_root = resolve_data_root()
    logger.info("Using data root: %s", data_root)

    force = os.getenv("GRAPHRAG_BOOTSTRAP", "auto").strip().lower()
    vectors = create_vector_store()
    indexed = _qdrant_has_indexed_data(vectors)
    should_bootstrap = force in {"1", "true", "yes", "force"} or (
        force == "auto" and not indexed
    )

    if not should_bootstrap:
        logger.info("Qdrant already indexed — skipping bootstrap")

        return

    logger.info("Bootstrapping knowledge base into Qdrant...")
    loaded = load_knowledge_base(data_root=data_root, reload_vectors=True)
    logger.info("Bootstrap complete: %s", loaded.stats)


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

    qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
    _wait_qdrant(qdrant_url)
    _bootstrap_if_needed()

    from graphrag.messaging.worker import run_worker

    run_worker()


if __name__ == "__main__":
    main()
