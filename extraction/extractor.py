import ast
import os
from typing import List, Tuple
from .models import NodeType, EdgeType, GraphNode, GraphEdge

class CodeKnowledgeExtractor(ast.NodeVisitor):
    """Trích xuất Nodes, Edges, Source Code và Docstrings từ AST."""
    
    def __init__(self, file_path: str, source_code: str):
        self.file_path = file_path
        self.source_code = source_code # Cần truyền source code gốc vào để cắt chuỗi
        self.nodes: List[GraphNode] = []
        self.edges: List[GraphEdge] = []
        
        self.current_file_id = f"file:{file_path}"
        self.current_class_id = None
        self.current_func_id = None
        
        # Node gốc cho file
        self.nodes.append(GraphNode(
            id=self.current_file_id, 
            name=os.path.basename(file_path), 
            type=NodeType.FILE, 
            file_path=self.file_path,
            content=ast.get_docstring(ast.parse(self.source_code)) or "",
            source_code=self.source_code
        ))

    def visit_Import(self, node):
        for alias in node.names:
            dep_id = f"dep:{alias.name}"
            # Tránh tạo trùng node dependency
            if not any(n.id == dep_id for n in self.nodes):
                self.nodes.append(GraphNode(dep_id, alias.name, NodeType.DEPENDENCY, ""))
            self.edges.append(GraphEdge(self.current_file_id, dep_id, EdgeType.IMPORTS))
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module_name = node.module if node.module else "unknown"
        dep_id = f"dep:{module_name}"
        if not any(n.id == dep_id for n in self.nodes):
            self.nodes.append(GraphNode(dep_id, module_name, NodeType.DEPENDENCY, ""))
        self.edges.append(GraphEdge(self.current_file_id, dep_id, EdgeType.IMPORTS))
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        class_id = f"class:{self.file_path}::{node.name}"
        docstring = ast.get_docstring(node) or ""
        class_source = ast.get_source_segment(self.source_code, node) or ""
        
        self.nodes.append(GraphNode(
            id=class_id, 
            name=node.name, 
            type=NodeType.CLASS, 
            file_path=self.file_path,
            content=docstring,
            source_code=class_source
        ))
        self.edges.append(GraphEdge(self.current_file_id, class_id, EdgeType.CONTAINS))
        
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_id = f"class_ref:{base.id}" 
                self.edges.append(GraphEdge(class_id, base_id, EdgeType.INHERITS))
        
        prev_class_id = self.current_class_id
        self.current_class_id = class_id
        self.generic_visit(node)
        self.current_class_id = prev_class_id

    def visit_FunctionDef(self, node):
        parent_id = self.current_class_id if self.current_class_id else self.current_file_id
        func_id = f"func:{self.file_path}::{node.name}"
        
        docstring = ast.get_docstring(node) or ""
        func_source = ast.get_source_segment(self.source_code, node) or ""
        
        self.nodes.append(GraphNode(
            id=func_id, 
            name=node.name, 
            type=NodeType.FUNCTION, 
            file_path=self.file_path,
            content=docstring,
            source_code=func_source
        ))
        self.edges.append(GraphEdge(parent_id, func_id, EdgeType.CONTAINS))
        
        prev_func_id = self.current_func_id
        self.current_func_id = func_id
        self.generic_visit(node)
        self.current_func_id = prev_func_id

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)

    def visit_Call(self, node):
        caller_id = self.current_func_id if self.current_func_id else (
            self.current_class_id if self.current_class_id else self.current_file_id
        )
        
        callee_name = None
        if isinstance(node.func, ast.Name):
            callee_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            callee_name = node.func.attr
            
        if callee_name:
            callee_id = f"func_ref:{callee_name}" 
            self.edges.append(GraphEdge(caller_id, callee_id, EdgeType.CALLS))
            
        self.generic_visit(node)

    def visit_Assign(self, node):
        active_context_id = self.current_func_id or self.current_class_id or self.current_file_id
        
        for target in node.targets:
            var_name = None
            if isinstance(target, ast.Name):
                var_name = target.id
            elif isinstance(target, ast.Attribute):
                var_name = target.attr
                
            if var_name:
                var_id = f"var:{self.file_path}::{var_name}"
                if not any(n.id == var_id for n in self.nodes):
                    self.nodes.append(GraphNode(var_id, var_name, NodeType.VARIABLE, self.file_path))
                
                self.edges.append(GraphEdge(active_context_id, var_id, EdgeType.USES_VARIABLE))
                
        self.generic_visit(node)

def extract_from_file(file_path: str) -> Tuple[List[GraphNode], List[GraphEdge]]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
        # Truyền cả file_path và source thô vào Extractor
        extractor = CodeKnowledgeExtractor(file_path, source)
        extractor.visit(tree)
        return extractor.nodes, extractor.edges
    except SyntaxError as se:
        print(f"[-] Syntax Error in {file_path}: {se}")
        return [], []
    except Exception as e:
        print(f"[-] Error extracting {file_path}: {e}")
        return [], []