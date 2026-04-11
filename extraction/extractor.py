import ast

from extraction.models import FileModule, Function


def extract(tree: ast.AST, file_path: str) -> FileModule:
    functions = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef):
            calls = [
                n.func.id
                for n in ast.walk(node)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            ]
            functions.append(Function(name=node.name, file=file_path, calls=calls))
    return FileModule(name=file_path, functions=functions)
