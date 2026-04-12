import os
import sys
import io

# Fix encoding for Windows console to support tree characters like ├──, └──, │
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# add the project root to sys.path
# khong hieu thi nem het may folder ngang hang kia vao /app la dc
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.file_scanner import scan_py_files
from parsing.parser import parse_file
from extraction.extractor import extract
from graph.builder import build_graph, visualize_subgraph
from explain.formatter import explain_function


def run(repo_path: str):
    files = scan_py_files(repo_path)
    modules = [extract(parse_file(f), f) for f in files]
    graph = build_graph(modules)

    nodes = list(graph.nodes)
    if not nodes:
        print("No functions found.")
        return

    visualize_subgraph(graph, nodes[0], depth=2)
    print(explain_function(graph, nodes[0]))


if __name__ == "__main__":
    run(".")  # thay = path to repo, (.) to run it self
