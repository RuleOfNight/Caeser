import networkx as nx
from extraction.models import FileModule, Function
from graph.builder import build_graph


def _mod(file, fns):
    functions = [Function(name=n, file=file, calls=c) for n, c in fns]
    return FileModule(name=file, functions=functions)


def test_build_graph_returns_digraph():
    g = build_graph([])
    assert isinstance(g, nx.DiGraph)


def test_nodes_created_for_each_function():
    mod = _mod("a.py", [("foo", []), ("bar", [])])
    g = build_graph([mod])
    assert "a.py::foo" in g.nodes
    assert "a.py::bar" in g.nodes


def test_edge_created_for_call():
    mod = _mod("a.py", [("foo", ["bar"]), ("bar", [])])
    g = build_graph([mod])
    assert g.has_edge("a.py::foo", "a.py::bar")


def test_no_edge_for_unknown_call():
    mod = _mod("a.py", [("foo", ["unknown"])])
    g = build_graph([mod])
    assert len(g.edges) == 0


def test_cross_module_edge():
    mod_a = _mod("a.py", [("foo", ["bar"])])
    mod_b = _mod("b.py", [("bar", [])])
    g = build_graph([mod_a, mod_b])
    assert g.has_edge("a.py::foo", "b.py::bar")


def test_empty_modules():
    g = build_graph([])
    assert len(g.nodes) == 0
    assert len(g.edges) == 0
