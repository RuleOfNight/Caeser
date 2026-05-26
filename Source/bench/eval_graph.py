#!/usr/bin/env python3
"""
Evaluate graph retrieval accuracy (two-stage LLM approach).

Usage:
    python bench/eval_graph.py
    python bench/eval_graph.py --graph data/graph.json
    python bench/eval_graph.py --questions "what does cmd_extract do?" "how does merger work?"
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from query.engine import QueryEngine

DEFAULT_QUESTIONS = [
    "what does cmd_extract do?",
    "how does the extractor parse functions?",
    "what is the role of ImportResolver?",
    "how does QueryEngine find relevant nodes?",
    "how is the graph exported to JSON?",
]


def main():
    parser = argparse.ArgumentParser(description="Evaluate graph retrieval accuracy")
    parser.add_argument("--graph",     default="data/graph.json")
    parser.add_argument("--questions", nargs="+")
    args = parser.parse_args()

    questions = args.questions or DEFAULT_QUESTIONS
    engine = QueryEngine(args.graph)

    col_q   = 44
    col_tok = 8
    width   = col_q + col_tok * 4 + 20

    print(f"\n{'Question':<{col_q}}  {'S1-in':>{col_tok}} {'S1-out':>{col_tok}} {'S2-in':>{col_tok}} {'S2-out':>{col_tok}}  Nodes selected")
    print("-" * width)

    totals = {"s1_input": 0, "s1_output": 0, "s2_input": 0, "s2_output": 0}

    for q in questions:
        q_display = (q[:col_q - 2] + "..") if len(q) > col_q else q
        result = engine.ask_with_usage(q)

        nodes_str = ", ".join(result["sources"]) or "(fallback)"
        print(f"{q_display:<{col_q}}  "
              f"{result['s1_input']:>{col_tok},} {result['s1_output']:>{col_tok},} "
              f"{result['s2_input']:>{col_tok},} {result['s2_output']:>{col_tok},}  "
              f"{nodes_str}")
        print(f"  {result['answer'][:300]}{'...' if len(result['answer']) > 300 else ''}")
        print()

        for k in totals:
            totals[k] += result[k]

    total_tokens = sum(totals.values())
    print("-" * width)
    print(f"{'TOTAL (' + str(len(questions)) + ' questions)':<{col_q}}  "
          f"{totals['s1_input']:>{col_tok},} {totals['s1_output']:>{col_tok},} "
          f"{totals['s2_input']:>{col_tok},} {totals['s2_output']:>{col_tok},}  "
          f"total={total_tokens:,}\n")


if __name__ == "__main__":
    main()
