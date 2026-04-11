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
    # Both callees must appear in the output
    assert "a.py::bar" in result
    assert "a.py::baz" in result


def test_explain_format_prefix():
    g = simple_graph()
    result = explain_function(g, "a.py::foo")
    assert result.startswith("Function a.py::foo calls:")


def test_explain_no_calls_returns_none_label():
    g = simple_graph()
    # bar calls nothing — output should say "none"
    result = explain_function(g, "a.py::bar")
    assert result == "Function a.py::bar calls: none"


def test_explain_single_callee():
    mods = [FileModule("m.py", [
        Function("entry", "m.py", ["helper"]),
        Function("helper", "m.py", []),
    ])]
    g = build_graph(mods)
    result = explain_function(g, "m.py::entry")
    assert result == "Function m.py::entry calls: m.py::helper"


def test_explain_returns_string():
    g = simple_graph()
    assert isinstance(explain_function(g, "a.py::foo"), str)
