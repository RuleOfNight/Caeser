from ingestion.file_scanner import scan_py_files
from parsing.parser import parse_file
from extraction.extractor import extract
from graph.builder import build_graph
from explain.formatter import explain_function


def run(repo_path: str):
    files = scan_py_files(repo_path)
    modules = [extract(parse_file(f), f) for f in files]
    graph = build_graph(modules)

    nodes = list(graph.nodes)
    if not nodes:
        print("No functions found.")
        return

    print(explain_function(graph, nodes[0]))


if __name__ == "__main__":
    run("data/sample_repo")
