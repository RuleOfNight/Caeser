import networkx as nx


def get_function_calls(graph: nx.DiGraph, func_name: str) -> list[str]:
    return list(graph.successors(func_name))
