import ast
from typing import Tuple


def parse_file(path: str) -> Tuple[ast.AST, str]:
    with open(path, encoding="utf-8") as f:
        source = f.read()
    return ast.parse(source, filename=path), source
