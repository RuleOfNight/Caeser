import os
import sys
import io
import argparse

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.file_scanner import scan_py_files
from parsing.parser import parse_file
from extraction.extractor import extract
from graph.builder import build_graph
from query.graph_query import get_call_chain, format_call_chain
from app.graph_viewer import launch_graph_viewer


def run(repo_path: str):
    """Pipeline: Scan -> Parse -> Extract -> Build Graph."""
    print(f"[*] Scanning: {os.path.abspath(repo_path)}")
    files = scan_py_files(repo_path)

    if not files:
        print("[-] No Python files found.")
        return

    modules = []
    print(f"[*] Extracting AST from {len(files)} files...")
    for f in files:
        try:
            tree = parse_file(f)
            modules.append(extract(tree, f))
        except (SyntaxError, Exception) as e:
            print(f"[-] Skipping {f}: {e}")

    total_fns = sum(len(m.functions) for m in modules)
    print(f"[*] Building graph from {total_fns} functions...")
    graph = build_graph(modules)

    print(f"[+] Nodes: {len(graph.nodes)} | Edges: {len(graph.edges)}")
    if len(graph.nodes) == 0:
        print("[-] Empty graph.")


def main():
    parser = argparse.ArgumentParser(description="Caeser project analyzer")
    parser.add_argument("repo_path", nargs="?", default=".", help="Repository path")
    parser.add_argument("--viewer", action="store_true", help="Open graph viewer")
    args = parser.parse_args()

    if args.viewer:
        launch_graph_viewer(args.repo_path)
        return

    run(args.repo_path)


if __name__ == "__main__":
    main()
