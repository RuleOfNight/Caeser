import ast
import pytest
from extraction.extractor import extract, resolve_call_name
from extraction.models import FileModule, Function


def _parse(src: str) -> ast.AST:
    return ast.parse(src)


# ---------------------------------------------------------------------------
# resolve_call_name
# ---------------------------------------------------------------------------

def test_resolve_call_name_simple():
    node = ast.parse("foo()").body[0].value
    assert resolve_call_name(node.func) == "foo"


def test_resolve_call_name_attribute():
    node = ast.parse("os.path.join()").body[0].value
    assert resolve_call_name(node.func) == "os.path.join"


def test_resolve_call_name_unknown():
    # dynamic call: func_list[0]() — cannot resolve
    node = ast.parse("func_list[0]()").body[0].value
    assert resolve_call_name(node.func) is None


# ---------------------------------------------------------------------------
# extract
# ---------------------------------------------------------------------------

def test_extract_returns_file_module():
    tree = _parse("def foo(): pass")
    result = extract(tree, "foo.py")
    assert isinstance(result, FileModule)


def test_extract_function_name():
    tree = _parse("def bar(): pass")
    result = extract(tree, "bar.py")
    assert len(result.functions) == 1
    assert result.functions[0].name == "bar"


def test_extract_multiple_functions():
    tree = _parse("def a(): pass\ndef b(): pass")
    result = extract(tree, "mod.py")
    names = [f.name for f in result.functions]
    assert "a" in names
    assert "b" in names


def test_extract_calls():
    tree = _parse("def foo():\n    bar()\n    baz()")
    result = extract(tree, "mod.py")
    assert result.functions[0].calls == ["bar", "baz"]


def test_extract_attribute_calls():
    # attribute calls are now captured as dotted strings
    tree = _parse("def foo():\n    obj.method()")
    result = extract(tree, "mod.py")
    assert result.functions[0].calls == ["obj.method"]


def test_extract_mixed_calls():
    src = "def foo():\n    bar()\n    os.path.join('a', 'b')"
    result = extract(ast.parse(src), "mod.py")
    assert result.functions[0].calls == ["bar", "os.path.join"]


def test_extract_no_functions():
    tree = _parse("x = 1")
    result = extract(tree, "mod.py")
    assert result.functions == []


def test_extract_file_path_stored():
    tree = _parse("def foo(): pass")
    result = extract(tree, "some/path.py")
    assert result.functions[0].file == "some/path.py"
