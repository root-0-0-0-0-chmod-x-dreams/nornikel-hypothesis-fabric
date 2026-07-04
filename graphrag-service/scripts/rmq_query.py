#!/usr/bin/env python3
"""RPC smoke test: call graph_rag_query via RabbitMQ."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from graphrag.messaging.client import GraphRagMessagingClient

DEFAULT_BUCKET = "lossform_кгмк_+71_closed_pnt_cp_ni"


def main() -> None:
    question = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "доизмельчение закрытого пентландита в классе +71 МШР"
    )
    client = GraphRagMessagingClient()

    try:
        result = client.graphrag_query(
            question,
            hypotheses=[
                {
                    "id": "h1",
                    "label": "доизмельчение МШР",
                    "retrieval_query": question,
                }
            ],
            bucket_id=DEFAULT_BUCKET,
            factory="КГМК",
            k_out=5,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    main()
