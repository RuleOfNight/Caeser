import ast
from typing import Tuple


def parse_file(path: str) -> ast.AST:
    with open(path, encoding="utf-8-sig") as f:
        source = f.read()
    return ast.parse(source, filename=path)


def parse_file_with_source(path: str) -> Tuple[ast.AST, str]:
    with open(path, encoding="utf-8-sig") as f:
        source = f.read()
    return ast.parse(source, filename=path), source
