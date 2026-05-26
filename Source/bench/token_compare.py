#!/usr/bin/env python3
"""
Compare three retrieval approaches: keyword graph, two-stage LLM graph, full codebase.

Usage:
    python bench/token_compare.py
    python bench/token_compare.py --graph data/graph.json --root .
    python bench/token_compare.py --questions "what does cmd_extract do?"
    python bench/token_compare.py --out results/my_run.md
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

import anthropic
from query.engine import QueryEngine
from ingestion.file_scanner import scan_py_files

MODEL = "claude-haiku-4-5-20251001"

DEFAULT_QUESTIONS = [
    "what does cmd_extract do?",
    "how does the extractor parse functions?",
    "what is the role of ImportResolver?",
    "how does QueryEngine find relevant nodes?",
    "how is the graph exported to JSON?",
]


# ── Data collection ───────────────────────────────────────────────────────────

def fullcode_approach(project_root: str, client: anthropic.Anthropic, question: str) -> dict:
    files = scan_py_files(project_root)
    parts = []
    for f in sorted(files):
        try:
            src = Path(f).read_text(encoding="utf-8")
            parts.append(f"# === {f} ===\n{src}")
        except Exception:
            pass

    system = (
        "You are a code assistant. The full codebase is provided below. "
        "Answer questions concisely. Reference specific file names and functions.\n\n"
        f"=== CODEBASE ===\n{chr(10).join(parts)}\n================"
    )
    response = client.messages.create(
        model=MODEL, max_tokens=1024, system=system,
        messages=[{"role": "user", "content": question}],
    )
    return {
        "answer": response.content[0].text, "sources": [],
        "s1_input": 0, "s1_output": 0,
        "s2_input": response.usage.input_tokens,
        "s2_output": response.usage.output_tokens,
    }


def total_tokens(r: dict) -> int:
    return r["s1_input"] + r["s1_output"] + r["s2_input"] + r["s2_output"]


# ── Console output ────────────────────────────────────────────────────────────

def print_question(q: str, kw: dict, llm: dict, full: dict):
    col_l, col_n = 12, 8
    width = 2 + col_l + 4 + col_n * 4 + 12

    def row(label, r, show_nodes=True):
        nodes = (", ".join(r["sources"]) or "-") if show_nodes and r.get("sources") else ""
        tok = total_tokens(r)
        s = (f"  {label:<{col_l}}"
             f"  {r['s1_input']:>{col_n},}  {r['s2_input']:>{col_n},}"
             f"  {r['s2_output']:>{col_n},}  {tok:>{col_n},}")
        return s + (f"  {nodes}" if nodes else "")

    header = (f"  {'Approach':<{col_l}}"
              f"  {'S1-in':>{col_n}}  {'S2-in':>{col_n}}"
              f"  {'S2-out':>{col_n}}  {'Total':>{col_n}}  Nodes")

    q_display = (q[:74] + "..") if len(q) > 76 else q
    print(f"\nQ: {q_display}")
    print(header)
    print("-" * width)
    print(row("keyword",   kw))
    print(row("llm-sel",   llm))
    print(row("full code", full))

    kw_t   = kw["s2_input"] + kw["s2_output"]
    llm_t  = total_tokens(llm)
    full_t = total_tokens(full)
    print(f"  vs full:  keyword={full_t/kw_t:.1f}x  llm-sel={full_t/llm_t:.1f}x")
    print(f"  [keyword]  {kw['answer'][:200]}{'...' if len(kw['answer'])>200 else ''}")
    print(f"  [llm-sel]  {llm['answer'][:200]}{'...' if len(llm['answer'])>200 else ''}")
    print(f"  [full]     {full['answer'][:200]}{'...' if len(full['answer'])>200 else ''}")


def print_summary(results: list[dict], questions: list[str]):
    col_l, col_n = 12, 8
    width = 2 + col_l + 4 + col_n * 4 + 12

    def agg(key):
        return {k: sum(r[key][k] for r in results) for k in ["s1_input","s1_output","s2_input","s2_output"]}

    kw_t   = agg("keyword")
    llm_t  = agg("llm")
    full_t = agg("full")

    def row(label, r):
        tok = total_tokens(r)
        return (f"  {label:<{col_l}}"
                f"  {r['s1_input']:>{col_n},}  {r['s2_input']:>{col_n},}"
                f"  {r['s2_output']:>{col_n},}  {tok:>{col_n},}")

    header = (f"  {'Approach':<{col_l}}"
              f"  {'S1-in':>{col_n}}  {'S2-in':>{col_n}}"
              f"  {'S2-out':>{col_n}}  {'Total':>{col_n}}")

    kw_sum   = total_tokens(kw_t)
    llm_sum  = total_tokens(llm_t)
    full_sum = total_tokens(full_t)

    print(f"\n{'=' * width}")
    print(f"TOTAL ({len(questions)} questions)")
    print(header)
    print("-" * width)
    print(row("keyword",   kw_t))
    print(row("llm-sel",   llm_t))
    print(row("full code", full_t))
    print(f"  vs full:  keyword={full_sum/kw_sum:.1f}x  llm-sel={full_sum/llm_sum:.1f}x\n")


# ── Markdown output ───────────────────────────────────────────────────────────

def write_markdown(results: list[dict], questions: list[str], out_path: Path):
    def n(x): return f"{x:,}"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# Token Comparison Report",
        f"",
        f"Generated: {now}  ",
        f"Model: `{MODEL}`  ",
        f"Questions: {len(questions)}",
        f"",
        f"---",
        f"",
        f"## Summary",
        f"",
        f"| Approach | S1 input | S2 input | S2 output | Total | vs full code |",
        f"|---|---:|---:|---:|---:|---:|",
    ]

    def agg(key):
        return {k: sum(r[key][k] for r in results) for k in ["s1_input","s1_output","s2_input","s2_output"]}

    kw_t   = agg("keyword")
    llm_t  = agg("llm")
    full_t = agg("full")

    kw_sum   = total_tokens(kw_t)
    llm_sum  = total_tokens(llm_t)
    full_sum = total_tokens(full_t)

    lines += [
        f"| keyword   | {n(kw_t['s1_input'])} | {n(kw_t['s2_input'])} | {n(kw_t['s2_output'])} | **{n(kw_sum)}** | {full_sum/kw_sum:.1f}x cheaper |",
        f"| llm-sel   | {n(llm_t['s1_input'])} | {n(llm_t['s2_input'])} | {n(llm_t['s2_output'])} | **{n(llm_sum)}** | {full_sum/llm_sum:.1f}x cheaper |",
        f"| full code | {n(full_t['s1_input'])} | {n(full_t['s2_input'])} | {n(full_t['s2_output'])} | **{n(full_sum)}** | baseline |",
        f"",
        f"---",
        f"",
    ]

    for i, (q, r) in enumerate(zip(questions, results), 1):
        kw   = r["keyword"]
        llm  = r["llm"]
        full = r["full"]
        kw_t_q   = total_tokens(kw)
        llm_t_q  = total_tokens(llm)
        full_t_q = total_tokens(full)

        kw_nodes   = ", ".join(kw["sources"])   or "-"
        llm_nodes  = ", ".join(llm["sources"])  or "-"

        lines += [
            f"## Q{i}: {q}",
            f"",
            f"| Approach | S1 input | S2 input | S2 output | Total | Nodes |",
            f"|---|---:|---:|---:|---:|---|",
            f"| keyword   | {n(kw['s1_input'])} | {n(kw['s2_input'])} | {n(kw['s2_output'])} | **{n(kw_t_q)}** | {kw_nodes} |",
            f"| llm-sel   | {n(llm['s1_input'])} | {n(llm['s2_input'])} | {n(llm['s2_output'])} | **{n(llm_t_q)}** | {llm_nodes} |",
            f"| full code | {n(full['s1_input'])} | {n(full['s2_input'])} | {n(full['s2_output'])} | **{n(full_t_q)}** | - |",
            f"",
            f"vs full code: keyword **{full_t_q/kw_t_q:.1f}x** cheaper · llm-sel **{full_t_q/llm_t_q:.1f}x** cheaper",
            f"",
            f"**keyword:**",
            f"",
            kw["answer"],
            f"",
            f"**llm-select:**",
            f"",
            llm["answer"],
            f"",
            f"**full code:**",
            f"",
            full["answer"],
            f"",
            f"---",
            f"",
        ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[+] Report saved: {out_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--graph",     default="data/graph.json")
    parser.add_argument("--root",      default=".")
    parser.add_argument("--questions", nargs="+")
    parser.add_argument("--out",       default=None, help="Output .md path (default: bench/results/YYYY-MM-DD_HH-MM.md)")
    args = parser.parse_args()

    questions    = args.questions or DEFAULT_QUESTIONS
    project_root = str(Path(args.root).resolve())
    engine       = QueryEngine(args.graph)
    client       = anthropic.Anthropic()

    out_path = Path(args.out) if args.out else (
        Path(__file__).parent / "results" /
        f"{datetime.now().strftime('%Y-%m-%d_%H-%M')}.md"
    )

    results = []
    for q in questions:
        kw   = engine.ask_keyword_with_usage(q)
        llm  = engine.ask_with_usage(q)
        full = fullcode_approach(project_root, client, q)
        results.append({"keyword": kw, "llm": llm, "full": full})
        print_question(q, kw, llm, full)

    print_summary(results, questions)
    write_markdown(results, questions, out_path)


if __name__ == "__main__":
    main()
