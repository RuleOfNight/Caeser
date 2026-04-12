from extraction.models import FileModule, Function
from graph.builder import build_graph
from explain.formatter import explain_function


# ---------------------------------------------------------------------------
# Shared fixture — foo calls bar and baz; bar and baz call nothing
# ---------------------------------------------------------------------------

def _build(modules):
    return build_graph(modules)


def simple_graph():
    mods = [FileModule("a.py", [
        Function("foo", "a.py", ["bar", "baz"]),
        Function("bar", "a.py", []),
        Function("baz", "a.py", []),
    ])]
    return build_graph(mods)


# ---------------------------------------------------------------------------
# explain_function
# ---------------------------------------------------------------------------

def test_explain_lists_callees():
    g = simple_graph()
    result = explain_function(g, "a.py::foo")
    # Both callees must appear in the tree output (short label format)
    assert "bar (a.py)" in result
    assert "baz (a.py)" in result


def test_explain_root_label():
    g = simple_graph()
    result = explain_function(g, "a.py::foo")
    # Root line uses short label: "func (file.py)"
    assert result.startswith("foo (a.py)")


def test_explain_no_calls_returns_just_root():
    g = simple_graph()
    # bar calls nothing — tree has only the root line
    result = explain_function(g, "a.py::bar")
    assert result == "bar (a.py)"


def test_explain_single_callee():
    mods = [FileModule("m.py", [
        Function("entry", "m.py", ["helper"]),
        Function("helper", "m.py", []),
    ])]
    g = build_graph(mods)
    result = explain_function(g, "m.py::entry")
    assert "entry (m.py)" in result
    assert "helper (m.py)" in result


def test_explain_returns_string():
    g = simple_graph()
    assert isinstance(explain_function(g, "a.py::foo"), str)
