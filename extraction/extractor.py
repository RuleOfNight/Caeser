import ast
from pathlib import Path
from typing import List, Optional, Tuple

from .models import EdgeType, GraphEdge, GraphNode, NodeType


def extract(tree: ast.AST, file_path: str, source: str = "") -> Tuple[List[GraphNode], List[GraphEdge]]:
    visitor = _Extractor(file_path, source)
    visitor.visit(tree)
    return visitor.nodes, visitor.edges


class _Extractor(ast.NodeVisitor):
    def __init__(self, file_path: str, source: str = ""):
        # Chuẩn hóa về forward slash để node ID nhất quán trên Windows/Linux
        self.file_path = Path(file_path).as_posix()
        self.source = source
        self.nodes: List[GraphNode] = []
        self.edges: List[GraphEdge] = []

        # Lưu class đang xử lý để phân biệt method (CONTAINS) với top-level func (DEFINES)
        self._current_class_id: Optional[str] = None
        self._current_class_name: Optional[str] = None

        stem = Path(file_path).stem
        self.module_id = f"module:{self.file_path}"
        self.nodes.append(GraphNode(
            id=self.module_id,
            name=stem,
            type=NodeType.MODULE,
            file_path=self.file_path,
            line_start=1,
        ))

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            # confidence=0.0 vì chưa biết đây là module nội bộ hay thư viện ngoài
            # resolver sẽ nâng confidence lên 1.0 nếu tìm thấy trong project
            self.edges.append(GraphEdge(
                type=EdgeType.IMPORTS,
                source_id=self.module_id,
                target_id=f"dep:{alias.name}",
                confidence=0.0,
            ))

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            self.edges.append(GraphEdge(
                type=EdgeType.IMPORTS,
                source_id=self.module_id,
                target_id=f"dep:{node.module}",
                confidence=0.0,
            ))

    def visit_ClassDef(self, node: ast.ClassDef):
        class_id = f"class:{self.file_path}::{node.name}"
        self.nodes.append(GraphNode(
            id=class_id,
            name=node.name,
            type=NodeType.CLASS,
            file_path=self.file_path,
            line_start=node.lineno,
            docstring=ast.get_docstring(node),
            source_code=ast.get_source_segment(self.source, node) if self.source else None,
            decorators=[_decorator_name(d) for d in node.decorator_list],
        ))
        self.edges.append(GraphEdge(
            type=EdgeType.DEFINES,
            source_id=self.module_id,
            target_id=class_id,
            confidence=1.0,
        ))
        for base in node.bases:
            base_name = _resolve_name(base)
            if base_name:
                # class_ref: là ghost ID — resolver sẽ map về class node thật
                self.edges.append(GraphEdge(
                    type=EdgeType.INHERITS,
                    source_id=class_id,
                    target_id=f"class_ref:{base_name}",
                    confidence=0.0,
                ))

        # Set context trước khi đệ quy để các method bên trong biết mình thuộc class nào
        prev_id, prev_name = self._current_class_id, self._current_class_name
        self._current_class_id = class_id
        self._current_class_name = node.name
        self.generic_visit(node)
        self._current_class_id = prev_id
        self._current_class_name = prev_name

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._handle_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._handle_function(node, is_async=True)

    def _handle_function(self, node, is_async: bool):
        if self._current_class_id:
            # Method: ID bao gồm tên class để tránh trùng với top-level func cùng tên
            func_id = f"func:{self.file_path}::{self._current_class_name}::{node.name}"
            container_id = self._current_class_id
            edge_type = EdgeType.CONTAINS
        else:
            func_id = f"func:{self.file_path}::{node.name}"
            container_id = self.module_id
            edge_type = EdgeType.DEFINES

        self.nodes.append(GraphNode(
            id=func_id,
            name=node.name,
            type=NodeType.FUNCTION,
            file_path=self.file_path,
            line_start=node.lineno,
            docstring=ast.get_docstring(node),
            source_code=ast.get_source_segment(self.source, node) if self.source else None,
            is_async=is_async,
            decorators=[_decorator_name(d) for d in node.decorator_list],
        ))
        self.edges.append(GraphEdge(
            type=edge_type,
            source_id=container_id,
            target_id=func_id,
            confidence=1.0,
        ))
        for call_name in _collect_calls(node):
            # func_ref: là ghost ID — resolver sẽ cố map về func node thật (best-effort)
            self.edges.append(GraphEdge(
                type=EdgeType.CALLS,
                source_id=func_id,
                target_id=f"func_ref:{call_name}",
                confidence=0.0,
            ))
        # Không gọi generic_visit ở đây — bỏ qua nested function (quá chi tiết, gây noise)


def _resolve_name(node: ast.expr) -> Optional[str]:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parts = []
        cur = node
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
            return ".".join(reversed(parts))
    return None


def _decorator_name(node: ast.expr) -> str:
    return _resolve_name(node) or "unknown"


def _collect_calls(func_node) -> List[str]:
    class _Collector(ast.NodeVisitor):
        def __init__(self):
            self.calls: List[str] = []

        def visit_Call(self, node: ast.Call):
            name = _resolve_name(node.func)
            if name:
                self.calls.append(name)
            self.generic_visit(node)

        # Dừng tại nested function — chỉ thu thập call ở body trực tiếp của hàm này
        def visit_FunctionDef(self, node):
            pass

        def visit_AsyncFunctionDef(self, node):
            pass

    collector = _Collector()
    for stmt in func_node.body:
        collector.visit(stmt)
    return collector.calls
