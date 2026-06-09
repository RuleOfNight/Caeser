#!/usr/bin/env python3
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass


def cmd_extract(args):
    from extraction.merger import merge_project
    merge_project(args.input, args.output, args.name)
    if args.load_neo4j:
        from graph.loader import load
        load(args.output)


def cmd_export(args):
    from export.obsidian import export
    export(args.graph, args.out)


def cmd_query(args):
    from query.engine import QueryEngine
    engine = QueryEngine(args.graph)
    print(f"[*] Loaded graph: {args.graph}")
    print("[*] Type your question. Enter 'exit' to quit.\n")

    history: list[dict] = []
    while True:
        try:
            question = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question:
            continue
        if question.lower() in ("exit", "quit", "q"):
            break

        answer, sources = engine.ask(question, history)
        if sources:
            print(f"[graph] {', '.join(sources)}")
        print(f"[llm]  {answer}\n")

        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})


def main():
    parser = argparse.ArgumentParser(prog="caeser")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ext = sub.add_parser("extract", help="Extract codebase → JSON graph")
    p_ext.add_argument("--input",  required=True, help="Project root directory")
    p_ext.add_argument("--output", required=True, help="Output JSON path")
    p_ext.add_argument("--name",                  help="Project name (default: folder name)")
    # p_ext.add_argument("--load-neo4j", action="store_true", help="Load graph into Neo4j after extraction")

    p_exp = sub.add_parser("export", help="Export graph → Obsidian vault")
    p_exp.add_argument("--graph", required=True, help="Input JSON graph path")
    p_exp.add_argument("--out",   required=True, help="Obsidian vault directory")

    p_qry = sub.add_parser("query", help="Conversational graph-first Q&A")
    p_qry.add_argument("--graph", required=True, help="Input JSON graph path")

    args = parser.parse_args()
    if args.command == "extract":
        cmd_extract(args)
    elif args.command == "export":
        cmd_export(args)
    elif args.command == "query":
        cmd_query(args)


if __name__ == "__main__":
    main()
