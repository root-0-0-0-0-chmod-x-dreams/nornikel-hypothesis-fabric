#!/usr/bin/env python3
"""Ask the knowledge graph in natural language (text-to-Cypher)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from graphrag.nl_cypher.service import NLGraphQueryService

EXAMPLE_QUESTIONS = (
    "статистика графа",
    "где больше всего теряется никель на КГМК",
    "что делать с закрытым пентландитом в классе +71 на КГМК",
    "извлекаемые потери на НОФ мед",
    "покажи всё оборудование",
    "найди МШР",
)


def _print_result(result, *, show_cypher: bool) -> None:
    print(result.answer)
    print()

    if show_cypher:
        print("Cypher:")
        print(result.cypher)
        if result.params:
            print("Params:", json.dumps(result.params, ensure_ascii=False))
        print()

    if result.hints:
        print("\n".join(result.hints))
        print()


def _interactive(service: NLGraphQueryService, *, show_cypher: bool) -> None:
    print("Graph Ask — задавайте вопросы по-русски. Пустая строка или Ctrl+C — выход.")
    print("Примеры:")
    for question in EXAMPLE_QUESTIONS:
        print(f"  • {question}")
    print()

    while True:
        try:
            question = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not question:
            break

        result = service.ask(question, show_hints=False)
        _print_result(result, show_cypher=show_cypher)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Natural language graph queries (text-to-Cypher)",
    )
    parser.add_argument("question", nargs="*", help="Question in Russian")
    parser.add_argument("-i", "--interactive", action="store_true", help="REPL mode")
    parser.add_argument("--json", action="store_true", help="Full JSON output")
    parser.add_argument("--cypher", action="store_true", help="Show generated Cypher")
    parser.add_argument("--examples", action="store_true", help="Run example questions")
    args = parser.parse_args()

    service = NLGraphQueryService()

    try:
        if args.examples:
            for question in EXAMPLE_QUESTIONS:
                print(f"Q: {question}")
                result = service.ask(question)
                if args.json:
                    print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
                else:
                    _print_result(result, show_cypher=args.cypher)
                print("-" * 60)

            return

        if args.interactive or not args.question:
            _interactive(service, show_cypher=args.cypher)
            return

        question = " ".join(args.question)
        result = service.ask(question)

        if args.json:
            print(
                json.dumps(result.__dict__, ensure_ascii=False, indent=2, default=str)
            )
        else:
            _print_result(result, show_cypher=args.cypher)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"Ошибка: {exc}", file=sys.stderr)
        print("Проверьте: make neo4j-up && make neo4j-seed", file=sys.stderr)
        sys.exit(2)
    finally:
        service.close()


if __name__ == "__main__":
    main()
