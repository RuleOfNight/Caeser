import ast

from extraction.models import FileModule, Function


def resolve_call_name(node: ast.AST) -> str | None:
    # Simple call: foo()
    if isinstance(node, ast.Name):
        return node.id
    # Attribute call: obj.method() or os.path.join()
    if isinstance(node, ast.Attribute):
        base = resolve_call_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    # Dynamic call (e.g. func_list[0]()) — cannot resolve
    return None


def extract(tree: ast.AST, file_path: str) -> FileModule:
    functions = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef):
            calls = []
            for n in ast.walk(node):
                if isinstance(n, ast.Call):
                    name = resolve_call_name(n.func)
                    if name is not None:
                        calls.append(name)
            functions.append(Function(name=node.name, file=file_path, calls=calls))
    return FileModule(name=file_path, functions=functions)
