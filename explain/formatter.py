import networkx as nx

from query.graph_query import get_call_chain, format_call_chain


def explain_function(graph: nx.DiGraph, func_name: str) -> str:
    # Build the recursive call chain and format it as a tree
    chain = get_call_chain(graph, func_name, depth=3)
    return format_call_chain(chain)
