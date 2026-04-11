import networkx as nx
import matplotlib.pyplot as plt

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


def visualize_graph(graph: nx.DiGraph, output_path: str = "graph.png") -> None:
    # Compute node positions using spring layout for readable spacing
    pos = nx.spring_layout(graph, seed=42)

    plt.figure(figsize=(12, 8))

    # Draw nodes as light blue circles with black borders
    nx.draw_networkx_nodes(graph, pos, node_color="lightblue", node_size=1500)

    # Draw directed edges with arrows to show call direction
    nx.draw_networkx_edges(graph, pos, arrows=True, arrowsize=20)

    # Draw labels using only the function name part (after '::') for readability
    labels = {node: node.split("::")[-1] for node in graph.nodes}
    nx.draw_networkx_labels(graph, pos, labels=labels, font_size=8)

    plt.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
