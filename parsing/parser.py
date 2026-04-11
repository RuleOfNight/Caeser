import ast


def parse_file(path: str) -> ast.AST:
    with open(path, encoding="utf-8") as f:
        return ast.parse(f.read(), filename=path)
