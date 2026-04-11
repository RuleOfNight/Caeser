import ast
from extraction.extractor import extract
from extraction.models import FileModule, Function


def _parse(src: str) -> ast.AST:
    return ast.parse(src)


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


def test_extract_ignores_attribute_calls():
    tree = _parse("def foo():\n    obj.method()")
    result = extract(tree, "mod.py")
    assert result.functions[0].calls == []


def test_extract_no_functions():
    tree = _parse("x = 1")
    result = extract(tree, "mod.py")
    assert result.functions == []


def test_extract_file_path_stored():
    tree = _parse("def foo(): pass")
    result = extract(tree, "some/path.py")
    assert result.functions[0].file == "some/path.py"
