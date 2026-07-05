#!/usr/bin/env python3
"""Run Cypher smoke checks against Neo4j."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neo4j import GraphDatabase

from graphrag.config import Neo4jConfig
from graphrag.constants import NEO4J_ENTITY_LABEL

# Primary H-01 bucket from КГМК Excel
DEMO_BUCKET_ID = "lossform_кгмк_+71_closed_pnt_cp_ni"
EXPECTED_CHAIN = (
    "mech_liberation",
    "process_comminution",
    "equip_mshr",
    "equip_gc660",
)

CHECKS: tuple[tuple[str, str, dict[str, Any]], ...] = (
    (
        "ping",
        "RETURN 1 AS ok",
        {},
    ),
    (
        "counts",
        f"""
        MATCH (n:{NEO4J_ENTITY_LABEL})
        WITH count(n) AS nodes
        MATCH ()-[r]->()
        WITH nodes, count(r) AS edges
        MATCH (lf:{NEO4J_ENTITY_LABEL})
        WHERE lf.node_type = 'LossForm'
        RETURN nodes, edges, count(lf) AS loss_forms
        """,
        {},
    ),
    (
        "isolated_nodes",
        f"""
        MATCH (n:{NEO4J_ENTITY_LABEL})
        WHERE NOT (n)--()
        RETURN count(n) AS isolated
        """,
        {},
    ),
    (
        "loss_forms_by_factory",
        f"""
        MATCH (n:{NEO4J_ENTITY_LABEL})
        WHERE n.node_type = 'LossForm'
        RETURN n.factory AS factory, count(*) AS buckets
        ORDER BY factory
        """,
        {},
    ),
    (
        "demo_bucket",
        f"""
        MATCH (n:{NEO4J_ENTITY_LABEL} {{node_id: $bucket_id}})
        RETURN n.node_id AS node_id,
               n.label AS label,
               n.tonnes AS tonnes,
               n.recoverable AS recoverable
        """,
        {"bucket_id": DEMO_BUCKET_ID},
    ),
    (
        "demo_bucket_chain",
        f"""
        MATCH (b:{NEO4J_ENTITY_LABEL} {{node_id: $bucket_id}})
              -[*1..4]->(m:{NEO4J_ENTITY_LABEL})
        RETURN DISTINCT m.node_id AS node_id,
               m.node_type AS node_type,
               m.label AS label
        ORDER BY node_id
        """,
        {"bucket_id": DEMO_BUCKET_ID},
    ),
    (
        "catalog_equipment",
        f"""
        MATCH (n:{NEO4J_ENTITY_LABEL})
        WHERE n.node_type = 'Equipment'
        RETURN n.node_id AS node_id, n.label AS label
        ORDER BY node_id
        """,
        {},
    ),
)


def _rows_to_dicts(records: Any) -> list[dict[str, Any]]:
    return [dict(record) for record in records]


def run_checks(config: Neo4jConfig) -> dict[str, Any]:
    driver = GraphDatabase.driver(
        config.uri,
        auth=(config.user, config.password),
    )
    report: dict[str, Any] = {
        "uri": config.uri,
        "checks": {},
        "passed": True,
        "errors": [],
    }

    try:
        with driver.session(database=config.database) as session:
            for name, cypher, params in CHECKS:
                rows = _rows_to_dicts(session.run(cypher, **params))
                report["checks"][name] = rows

            report["assertions"] = _evaluate(report["checks"])
            report["passed"] = all(item["ok"] for item in report["assertions"].values())
    finally:
        driver.close()

    return report


def _evaluate(checks: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    counts = checks.get("counts", [{}])[0]
    chain_nodes = {
        row["node_id"]
        for row in checks.get("demo_bucket_chain", [])
        if row.get("node_id")
    }
    demo_bucket = checks.get("demo_bucket", [])

    return {
        "neo4j_alive": {
            "ok": checks.get("ping", [{}])[0].get("ok") == 1,
            "detail": "RETURN 1",
        },
        "has_nodes": {
            "ok": counts.get("nodes", 0) >= 200,
            "detail": f"nodes={counts.get('nodes', 0)} (expected >= 200)",
        },
        "has_loss_forms": {
            "ok": counts.get("loss_forms", 0) >= 200,
            "detail": f"loss_forms={counts.get('loss_forms', 0)} (expected >= 200)",
        },
        "has_edges": {
            "ok": counts.get("edges", 0) >= 1000,
            "detail": f"edges={counts.get('edges', 0)} (expected >= 1000)",
        },
        "low_isolation": {
            "ok": checks.get("isolated_nodes", [{}])[0].get("isolated", 999) <= 15,
            "detail": (
                f"isolated={checks.get('isolated_nodes', [{}])[0].get('isolated', '?')} "
                "(expected <= 15)"
            ),
        },
        "demo_bucket_exists": {
            "ok": len(demo_bucket) == 1,
            "detail": DEMO_BUCKET_ID,
        },
        "demo_bucket_recoverable": {
            "ok": bool(demo_bucket and demo_bucket[0].get("recoverable") is True),
            "detail": str(demo_bucket[0].get("recoverable") if demo_bucket else None),
        },
        "demo_chain_complete": {
            "ok": all(node_id in chain_nodes for node_id in EXPECTED_CHAIN),
            "detail": f"found={sorted(chain_nodes & set(EXPECTED_CHAIN))}",
        },
    }


def _print_human(report: dict[str, Any]) -> None:
    print(f"Neo4j: {report['uri']}")
    print()

    counts = report["checks"].get("counts", [{}])[0]
    print("Counts:")
    print(f"  nodes:      {counts.get('nodes', 0)}")
    print(f"  edges:      {counts.get('edges', 0)}")
    print(f"  loss_forms: {counts.get('loss_forms', 0)}")
    print()

    print("LossForm by factory:")
    for row in report["checks"].get("loss_forms_by_factory", []):
        print(f"  {row.get('factory')}: {row.get('buckets')}")
    print()

    demo = report["checks"].get("demo_bucket", [])
    if demo:
        row = demo[0]
        print("Demo bucket:")
        label = row.get("label")
        tonnes = row.get("tonnes")
        recoverable = row.get("recoverable")
        print(f"  {label} — {tonnes} t, recoverable={recoverable}")
    print()

    print(f"Chain from {DEMO_BUCKET_ID}:")
    for row in report["checks"].get("demo_bucket_chain", []):
        print(f"  [{row.get('node_type')}] {row.get('node_id')} — {row.get('label')}")
    print()

    print("Assertions:")
    for name, item in report["assertions"].items():
        mark = "OK" if item["ok"] else "FAIL"
        print(f"  [{mark}] {name}: {item['detail']}")
    print()

    status = "PASSED" if report["passed"] else "FAILED"
    print(status)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Neo4j Cypher checks")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full report as JSON",
    )
    args = parser.parse_args()

    try:
        report = run_checks(Neo4jConfig.from_env())
    except Exception as exc:  # pylint: disable=broad-except
        print(f"Neo4j check error: {exc}", file=sys.stderr)
        sys.exit(2)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        _print_human(report)

    sys.exit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
