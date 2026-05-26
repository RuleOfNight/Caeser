import io
import os
import sys
import argparse
from pathlib import Path
from typing import List

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.file_scanner import scan_py_files
from parsing.parser import parse_file
from extraction.extractor import extract
from extraction.resolver import ImportResolver
from extraction.models import GraphNode, GraphEdge
from graph.builder import build_graph
from app.graph_viewer import launch_graph_viewer


def run(repo_path: str):
    root = Path(repo_path).resolve()
    files = [f for f in scan_py_files(str(root)) if Path(f).name != "__init__.py"]
    if not files:
        print("[-] No Python files found.")
        return

    all_nodes: List[GraphNode] = []
    all_edges: List[GraphEdge] = []
    print(f"[*] Extracting {len(files)} files from {root}...")
    for f in files:
        try:
            tree = parse_file(f)
            nodes, edges = extract(tree, f)
            all_nodes.extend(nodes)
            all_edges.extend(edges)
        except (SyntaxError, Exception) as e:
            print(f"[-] Skipping {f}: {e}")

    print("[*] Resolving references...")
    resolver = ImportResolver(str(root), all_nodes)
    resolved_edges = resolver.resolve(all_edges)

    graph = build_graph(all_nodes, resolved_edges)
    print(f"[+] Nodes: {len(graph.nodes)} | Edges: {len(graph.edges)}")


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
