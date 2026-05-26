import ast
import textwrap
from typing import List, Optional, Tuple

from .models import GraphNode, GraphEdge, NodeType, EdgeType


def resolve_call_name(node: ast.expr) -> Optional[str]:
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


def extract(tree: ast.AST, file_path: str, source: str) -> Tuple[List[GraphNode], List[GraphEdge]]:
    extractor = _Extractor(file_path, source)
    extractor.visit(tree)
    return extractor.nodes, extractor.edges


class _Extractor(ast.NodeVisitor):
    def __init__(self, file_path: str, source: str):
        self.file_path = file_path
        self.source = source
        self.source_lines = source.splitlines()
        self.nodes: List[GraphNode] = []
        self.edges: List[GraphEdge] = []
        self._current_class: Optional[str] = None

        # Module node
        module_id = f"module:{file_path}"
        self.module_id = module_id
        self.nodes.append(GraphNode(
            id=module_id,
            name=file_path,
            type=NodeType.MODULE,
            file_path=file_path,
            line_start=1,
        ))

    def _get_docstring(self, node) -> Optional[str]:
        return ast.get_docstring(node)

    def _get_source(self, node) -> Optional[str]:
        try:
            return ast.get_source_segment(self.source, node)
        except Exception:
            return None

    def _get_decorators(self, node) -> List[str]:
        result = []
        for d in getattr(node, "decorator_list", []):
            name = resolve_call_name(d)
            if name:
                result.append(name)
        return result

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            target_id = f"module:{alias.name}"
            self.edges.append(GraphEdge(
                type=EdgeType.IMPORTS,
                source_id=self.module_id,
                target_id=target_id,
                confidence=0.0,  # unresolved until ImportResolver runs
            ))

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            target_id = f"module:{node.module}"
            self.edges.append(GraphEdge(
                type=EdgeType.IMPORTS,
                source_id=self.module_id,
                target_id=target_id,
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
            docstring=self._get_docstring(node),
            source_code=self._get_source(node),
            decorators=self._get_decorators(node),
        ))
        self.edges.append(GraphEdge(
            type=EdgeType.DEFINES,
            source_id=self.module_id,
            target_id=class_id,
        ))

        for base in node.bases:
            base_name = resolve_call_name(base)
            if base_name:
                self.edges.append(GraphEdge(
                    type=EdgeType.INHERITS,
                    source_id=class_id,
                    target_id=f"class::{base_name}",
                    confidence=0.0,
                ))

        prev_class = self._current_class
        self._current_class = class_id
        self.generic_visit(node)
        self._current_class = prev_class

    def _visit_func(self, node):
        if self._current_class:
            func_id = f"func:{self.file_path}::{node.name}"
            parent_id = self._current_class
            edge_type = EdgeType.CONTAINS
        else:
            func_id = f"func:{self.file_path}::{node.name}"
            parent_id = self.module_id
            edge_type = EdgeType.DEFINES

        self.nodes.append(GraphNode(
            id=func_id,
            name=node.name,
            type=NodeType.FUNCTION,
            file_path=self.file_path,
            line_start=node.lineno,
            docstring=self._get_docstring(node),
            source_code=self._get_source(node),
            is_async=isinstance(node, ast.AsyncFunctionDef),
            decorators=self._get_decorators(node),
        ))
        self.edges.append(GraphEdge(
            type=edge_type,
            source_id=parent_id,
            target_id=func_id,
        ))

        for call_name in _collect_calls(node):
            self.edges.append(GraphEdge(
                type=EdgeType.CALLS,
                source_id=func_id,
                target_id=f"func::{call_name}",
                confidence=0.0,
            ))

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._visit_func(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._visit_func(node)


def _collect_calls(func_node) -> List[str]:
    class _CallCollector(ast.NodeVisitor):
        def __init__(self):
            self.calls: List[str] = []

        def visit_Call(self, node: ast.Call):
            name = resolve_call_name(node.func)
            if name:
                self.calls.append(name)
            self.generic_visit(node)

        def visit_FunctionDef(self, node):
            pass

        def visit_AsyncFunctionDef(self, node):
            pass

    collector = _CallCollector()
    for stmt in func_node.body:
        collector.visit(stmt)
    return collector.calls
