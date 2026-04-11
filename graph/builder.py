import networkx as nx

from extraction.models import FileModule


def build_graph(modules: list[FileModule]) -> nx.DiGraph:
    graph = nx.DiGraph()

    all_functions = {
        f"{fn.file}::{fn.name}": fn
        for mod in modules
        for fn in mod.functions
    }

    for node_id in all_functions:
        graph.add_node(node_id)

    for node_id, fn in all_functions.items():
        for call in fn.calls:
            targets = [nid for nid in all_functions if nid.endswith(f"::{call}")]
            for target in targets:
                graph.add_edge(node_id, target)

    return graph
