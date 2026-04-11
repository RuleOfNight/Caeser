import networkx as nx

from query.graph_query import get_function_calls


def explain_function(graph: nx.DiGraph, func_name: str) -> str:
    calls = get_function_calls(graph, func_name)
    called = ", ".join(calls) if calls else "none"
    return f"Function {func_name} calls: {called}"
