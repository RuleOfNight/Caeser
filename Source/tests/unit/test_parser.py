import ast
import pytest
from parsing.parser import parse_file


def test_parse_file_returns_ast_module(tmp_path):
    f = tmp_path / "sample.py"
    f.write_text("x = 1")
    tree = parse_file(str(f))
    assert isinstance(tree, ast.Module)


def test_parse_file_contains_function(tmp_path):
    f = tmp_path / "sample.py"
    f.write_text("def foo(): pass")
    tree = parse_file(str(f))
    names = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    assert "foo" in names


def test_parse_file_not_found():
    with pytest.raises(FileNotFoundError):
        parse_file("no_such_file.py")


def test_parse_file_syntax_error(tmp_path):
    f = tmp_path / "bad.py"
    f.write_text("def (:")
    with pytest.raises(SyntaxError):
        parse_file(str(f))
