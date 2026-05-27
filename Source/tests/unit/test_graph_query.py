import pytest
import networkx as nx

from extraction.models import FileModule, Function
from graph.builder import build_graph
from query.graph_query import get_function_calls, get_callers, get_call_chain, format_call_chain


# ---------------------------------------------------------------------------
# Shared fixture — a small graph used across most tests:
#
#   foo --> bar --> baz
#       \-> qux
#
# foo calls bar and qux; bar calls baz; baz and qux call nothing.
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_graph():
    modules = [
        FileModule("a.py", [
            Function("foo", "a.py", ["bar", "qux"]),
            Function("bar", "a.py", ["baz"]),
            Function("baz", "a.py", []),
            Function("qux", "a.py", []),
        ])
    ]
    return build_graph(modules)


@pytest.fixture
def cycle_graph():
    # Mutual cycle: alpha calls beta, beta calls alpha
    modules = [
        FileModule("a.py", [
            Function("alpha", "a.py", ["beta"]),
            Function("beta",  "a.py", ["alpha"]),
        ])
    ]
    return build_graph(modules)


# ---------------------------------------------------------------------------
# get_function_calls
# ---------------------------------------------------------------------------

def test_get_function_calls_returns_direct_callees(simple_graph):
    # foo directly calls bar and qux
    result = get_function_calls(simple_graph, "a.py::foo")
    assert set(result) == {"a.py::bar", "a.py::qux"}


def test_get_function_calls_empty_for_leaf(simple_graph):
    # baz calls nothing
    assert get_function_calls(simple_graph, "a.py::baz") == []


def test_get_function_calls_unknown_node_raises(simple_graph):
    # networkx raises NetworkXError for unknown nodes
    with pytest.raises(Exception):
        get_function_calls(simple_graph, "a.py::nonexistent")


# ---------------------------------------------------------------------------
# get_callers
# ---------------------------------------------------------------------------

def test_get_callers_returns_direct_callers(simple_graph):
    # bar is called only by foo
    assert get_callers(simple_graph, "a.py::bar") == ["a.py::foo"]


def test_get_callers_multiple(simple_graph):
    # baz is called only by bar; but let us also verify foo has no callers
    assert get_callers(simple_graph, "a.py::foo") == []


def test_get_callers_unknown_node_raises(simple_graph):
    with pytest.raises(Exception):
        get_callers(simple_graph, "a.py::ghost")


# ---------------------------------------------------------------------------
# get_call_chain
# ---------------------------------------------------------------------------

def test_call_chain_root_is_func_name(simple_graph):
    chain = get_call_chain(simple_graph, "a.py::foo", depth=1)
    assert "a.py::foo" in chain


def test_call_chain_depth_1_returns_direct_callees(simple_graph):
    chain = get_call_chain(simple_graph, "a.py::foo", depth=1)
    children = chain["a.py::foo"]
    # depth=1: bar and qux present, but their sub-dicts must be empty (depth exhausted)
    assert "a.py::bar" in children
    assert "a.py::qux" in children
    assert children["a.py::bar"] == {}
    assert children["a.py::qux"] == {}


def test_call_chain_depth_2_expands_grandchildren(simple_graph):
    chain = get_call_chain(simple_graph, "a.py::foo", depth=2)
    # foo -> bar -> baz (depth 2 should expose baz)
    assert "a.py::baz" in chain["a.py::foo"]["a.py::bar"]


def test_call_chain_depth_0_returns_empty_subtree(simple_graph):
    chain = get_call_chain(simple_graph, "a.py::foo", depth=0)
    # depth=0: the root node has no children expanded
    assert chain["a.py::foo"] == {}


def test_call_chain_detects_direct_cycle(cycle_graph):
    # alpha -> beta -> alpha forms a cycle at depth 2
    chain = get_call_chain(cycle_graph, "a.py::alpha", depth=2)
    beta_subtree = chain["a.py::alpha"]["a.py::beta"]
    # alpha reappears inside beta's subtree — must be marked as cycle
    assert beta_subtree["a.py::alpha"] == "[cycle]"


def test_call_chain_no_false_cycle_on_shared_callee(simple_graph):
    # baz is reachable via foo->bar->baz; it should NOT be marked as cycle
    # because it is not an ancestor of itself on that path
    chain = get_call_chain(simple_graph, "a.py::foo", depth=3)
    baz_value = chain["a.py::foo"]["a.py::bar"]["a.py::baz"]
    assert baz_value != "[cycle]"
    assert isinstance(baz_value, dict)


# ---------------------------------------------------------------------------
# format_call_chain
# ---------------------------------------------------------------------------

def test_format_call_chain_contains_root(simple_graph):
    chain = get_call_chain(simple_graph, "a.py::foo", depth=1)
    output = format_call_chain(chain)
    # Root label: "foo (a.py)"
    assert "foo (a.py)" in output


def test_format_call_chain_contains_children(simple_graph):
    chain = get_call_chain(simple_graph, "a.py::foo", depth=1)
    output = format_call_chain(chain)
    assert "bar (a.py)" in output
    assert "qux (a.py)" in output


def test_format_call_chain_uses_tree_connectors(simple_graph):
    chain = get_call_chain(simple_graph, "a.py::foo", depth=1)
    output = format_call_chain(chain)
    # Tree drawing characters must appear
    assert any(c in output for c in ["├", "└", "│"])


def test_format_call_chain_marks_cycle(cycle_graph):
    chain = get_call_chain(cycle_graph, "a.py::alpha", depth=2)
    output = format_call_chain(chain)
    # The cyclic node must be annotated
    assert "[cycle]" in output


def test_format_call_chain_returns_string(simple_graph):
    chain = get_call_chain(simple_graph, "a.py::foo", depth=2)
    assert isinstance(format_call_chain(chain), str)
