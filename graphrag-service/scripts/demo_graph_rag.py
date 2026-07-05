#!/usr/bin/env python3
"""Run GraphRAG query on production-loaded knowledge base."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from graphrag.bootstrap import build_service

# Primary demo bucket: КГМК +71 closed Pnt Ni (from real Excel)
DEFAULT_BUCKET_ID = "lossform_кгмк_+71_closed_pnt_cp_ni"


def main() -> None:
    service = build_service()
    result = service.query(
        "доизмельчение закрытого пентландита в классе +71 МШР",
        bucket_id=DEFAULT_BUCKET_ID,
        factory="КГМК",
        k_out=5,
    )

    output = {
        "question": result.question,
        "expanded_query": result.expanded_query,
        "bucket_id": result.bucket_id,
        "node_ids": result.node_ids,
        "channel_hits": result.channel_hits,
        "chunks": [
            {
                "chunk_id": chunk.chunk_id,
                "score": round(chunk.score, 4),
                "channel": chunk.retrieval_channel,
                "source": chunk.source,
            }
            for chunk in result.chunks
        ],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
