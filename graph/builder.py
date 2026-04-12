import networkx as nx
import matplotlib.pyplot as plt

from extraction.models import FileModule
from query.graph_query import get_call_chain


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
            # Use last segment so dotted calls like "os.path.join" or
            # "user.save" can still match a known function named "join" / "save"
            last = call.split(".")[-1]
            targets = [nid for nid in all_functions if nid.endswith(f"::{last}")]
            for target in targets:
                graph.add_edge(node_id, target)

    return graph


def _collect_nodes(chain: dict | str) -> set[str]:
    """de quy qua dict cua get_call_chain de lay ra cac node"""
    nodes = set()
    if isinstance(chain, str):
        # "[cycle]" -> stop this branch
        return nodes
    for node_id, subtree in chain.items():
        nodes.add(node_id)
        nodes |= _collect_nodes(subtree)
    return nodes


def visualize_subgraph(
    
    graph: nx.DiGraph,
    func_name: str,
    depth: int = 1,
    output_path: str = "graph.png",
) -> None:
    """
    Visualize the subgraph of a function
    Args:
        graph: The graph to visualize
        func_name: The name of the function to visualize
        depth: The depth of the subgraph to visualize
        output_path: The path to save the visualization

    get_call_chain(graph, func_name, depth)   →  nested dict
          ↓
    _collect_nodes(chain)                     →  set of node IDs
          ↓
    graph.subgraph(nodes)                     →  subgraph view (only nodes + edges in the set)
          ↓
    draw subgraph using matplotlib
    """
    # Resolve the function name to a full node ID if necessary
    actual_node = func_name
    if actual_node not in graph:
        candidates = [n for n in graph.nodes if n.endswith(f"::{func_name}")]
        if candidates:
            actual_node = candidates[0]
        else:
            print(f"Error: Node '{func_name}' not found in the graph.")
            return

    # Build the call chain and collect only the nodes it contains
    chain = get_call_chain(graph, actual_node, depth=depth)
    nodes = _collect_nodes(chain)

    sub = graph.subgraph(nodes)

    pos = nx.spring_layout(sub, seed=42)
    plt.figure(figsize=(12, 8))

    nx.draw_networkx_nodes(sub, pos, node_color="lightblue", node_size=1500)
    nx.draw_networkx_edges(sub, pos, arrows=True, arrowsize=20)

    # Label format: "func_name (file.py)"
    labels = {
        node: f"{node.split('::')[-1]} ({node.split('::')[0].split('/')[-1]})"
        for node in sub.nodes
    }
    nx.draw_networkx_labels(sub, pos, labels=labels, font_size=8)

    plt.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
