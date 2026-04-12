import networkx as nx
import pytest
from unittest.mock import patch, MagicMock
from extraction.models import FileModule, Function
from graph.builder import build_graph, visualize_subgraph


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


# ---------------------------------------------------------------------------
# visualize_subgraph — mock matplotlib to avoid file I/O and display
# ---------------------------------------------------------------------------

_DRAW_PATCHES = [
    "graph.builder.plt",
    "graph.builder.nx.draw_networkx_labels",
    "graph.builder.nx.draw_networkx_edges",
    "graph.builder.nx.draw_networkx_nodes",
    "graph.builder.nx.spring_layout",
]


@patch("graph.builder.plt")
@patch("graph.builder.nx.draw_networkx_labels")
@patch("graph.builder.nx.draw_networkx_edges")
@patch("graph.builder.nx.draw_networkx_nodes")
@patch("graph.builder.nx.spring_layout")
def test_visualize_subgraph_saves_file(
    mock_layout, mock_draw_nodes, mock_draw_edges, mock_draw_labels, mock_plt
):
    """visualize_subgraph should call plt.savefig with the given output path."""
    mock_layout.return_value = {}
    g = build_graph([_mod("a.py", [("foo", ["bar"]), ("bar", [])])])
    visualize_subgraph(g, "a.py::foo", depth=1, output_path="out.png")
    mock_plt.savefig.assert_called_once_with("out.png", dpi=150)


@patch("graph.builder.plt")
@patch("graph.builder.nx.draw_networkx_labels")
@patch("graph.builder.nx.draw_networkx_edges")
@patch("graph.builder.nx.draw_networkx_nodes")
@patch("graph.builder.nx.spring_layout")
def test_visualize_subgraph_closes_figure(
    mock_layout, mock_draw_nodes, mock_draw_edges, mock_draw_labels, mock_plt
):
    """visualize_subgraph should close the figure after saving."""
    mock_layout.return_value = {}
    g = build_graph([_mod("a.py", [("foo", [])])])
    visualize_subgraph(g, "a.py::foo", depth=1)
    mock_plt.close.assert_called_once()


@patch("graph.builder.plt")
@patch("graph.builder.nx.draw_networkx_labels")
@patch("graph.builder.nx.draw_networkx_edges")
@patch("graph.builder.nx.draw_networkx_nodes")
@patch("graph.builder.nx.spring_layout")
def test_visualize_subgraph_label_format(
    mock_layout, mock_draw_nodes, mock_draw_edges, mock_draw_labels, mock_plt
):
    """Labels should use 'func_name (file.py)' format."""
    mock_layout.return_value = {}
    g = build_graph([_mod("path/to/a.py", [("foo", [])])])
    visualize_subgraph(g, "path/to/a.py::foo", depth=1)
    _, kwargs = mock_draw_labels.call_args
    labels = kwargs.get("labels") or mock_draw_labels.call_args[0][2]
    assert labels.get("path/to/a.py::foo") == "foo (a.py)"


@patch("graph.builder.plt")
@patch("graph.builder.nx.draw_networkx_labels")
@patch("graph.builder.nx.draw_networkx_edges")
@patch("graph.builder.nx.draw_networkx_nodes")
@patch("graph.builder.nx.spring_layout")
def test_visualize_subgraph_only_includes_chain_nodes(
    mock_layout, mock_draw_nodes, mock_draw_edges, mock_draw_labels, mock_plt
):
    """Only nodes within the call chain should be drawn — not the full graph."""
    mock_layout.return_value = {}
    # foo -> bar; baz is isolated
    g = build_graph([_mod("a.py", [("foo", ["bar"]), ("bar", []), ("baz", [])])])
    visualize_subgraph(g, "a.py::foo", depth=1)
    # spring_layout receives the subgraph — check it only has foo and bar
    subgraph_arg = mock_layout.call_args[0][0]
    assert set(subgraph_arg.nodes) == {"a.py::foo", "a.py::bar"}
    assert "a.py::baz" not in subgraph_arg.nodes


@patch("graph.builder.plt")
@patch("graph.builder.nx.draw_networkx_labels")
@patch("graph.builder.nx.draw_networkx_edges")
@patch("graph.builder.nx.draw_networkx_nodes")
@patch("graph.builder.nx.spring_layout")
def test_visualize_subgraph_with_cycle_does_not_raise(
    mock_layout, mock_draw_nodes, mock_draw_edges, mock_draw_labels, mock_plt
):
    """Cyclic call chains (which produce '[cycle]' sentinels) should not raise."""
    mock_layout.return_value = {}
    # alpha -> beta -> alpha (mutual cycle)
    g = build_graph([_mod("a.py", [("alpha", ["beta"]), ("beta", ["alpha"])])])
    visualize_subgraph(g, "a.py::alpha", depth=2)
    mock_plt.savefig.assert_called_once()
