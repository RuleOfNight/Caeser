import ast
from typing import List, Optional

from .models import FileModule, Function


def resolve_call_name(node: ast.expr) -> Optional[str]:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        # duyệt ngược chuỗi attribute để ghép lại: os.path.join → ["join","path","os"] → reverse
        parts = []
        cur = node
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
            return ".".join(reversed(parts))
        return None  # dynamic call như func_list[0]() — không resolve được
    return None


def extract(tree: ast.AST, file_path: str) -> FileModule:
    extractor = _Extractor(file_path)
    extractor.visit(tree)
    return FileModule(name=file_path, functions=extractor.functions)


class _Extractor(ast.NodeVisitor):
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.functions: List[Function] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        calls = _collect_calls(node)
        self.functions.append(Function(name=node.name, file=self.file_path, calls=calls))

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.generic_visit(node)  # đệ quy vào class để thu thập các method bên trong


def _collect_calls(func_node: ast.FunctionDef) -> List[str]:
    class _CallCollector(ast.NodeVisitor):
        def __init__(self):
            self.calls: List[str] = []

        def visit_Call(self, node: ast.Call):
            name = resolve_call_name(node.func)
            if name:
                self.calls.append(name)
            self.generic_visit(node)

        # dừng đệ quy tại hàm lồng nhau — chỉ thu thập call ở top-level và method
        def visit_FunctionDef(self, node):
            pass

        def visit_AsyncFunctionDef(self, node):
            pass

    collector = _CallCollector()
    for stmt in func_node.body:
        collector.visit(stmt)
    return collector.calls
