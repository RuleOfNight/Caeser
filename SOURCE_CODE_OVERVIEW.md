# 💻 SOURCE CODE OVERVIEW - Các Hàm Chính

Tài liệu này chỉ ra và giải thích **source code** của các hàm quan trọng nhất trong dự án.

---

## 1️⃣ INGESTION - Quét File

### **File:** `ingestion/file_scanner.py`

```python
from pathlib import Path

_EXCLUDE = {".venv", "venv", "__pycache__", ".git"}

def scan_py_files(root: str) -> list[str]:
    """
    Quét toàn bộ file Python từ thư mục root (đệ quy).
    
    Args:
        root (str): Đường dẫn thư mục gốc
        
    Returns:
        list[str]: Danh sách đường dẫn các file .py (posix format)
    """
    return [
        p.as_posix()                              # Chuyển thành "/" format
        for p in Path(root).rglob("*.py")         # Tìm ** *.py
        if p.is_file() and not _EXCLUDE.intersection(p.parts)  # Loại trừ thư mục cấm
    ]
```

**Giải thích:**
- `Path(root).rglob("*.py")` = tìm **đệ quy** mọi `*.py` file
- `_EXCLUDE.intersection(p.parts)` = nếu có phần nào trong path nằm trong `_EXCLUDE` → bỏ qua
- `p.as_posix()` = chuyển Windows path `C:\a\b.py` → `C:/a/b.py`

**Ví dụ:**
```python
scan_py_files(".")
# → ["app/main.py", "ingestion/file_scanner.py", "parsing/parser.py", ...]
```

---

## 2️⃣ PARSING - Đọc AST

### **File:** `parsing/parser.py`

```python
import ast

def parse_file(path: str) -> ast.AST:
    """
    Đọc file Python và chuyển thành cây cú pháp trừu tượng.
    
    Args:
        path (str): Đường dẫn file .py
        
    Returns:
        ast.AST: Cây cú pháp (thường là ast.Module)
        
    Raises:
        SyntaxError: Nếu file có lỗi syntax
    """
    with open(path, "r", encoding="utf-8") as f:
        source_code = f.read()
    return ast.parse(source_code)
```

**Giải thích:**
- `ast.parse(source_code)` = Python built-in để chuyển text → cây cú pháp
- Không cần chạy code → nhanh & an toàn
- Trả về `ast.Module` root node

**Ví dụ:**
```python
tree = parse_file("app/main.py")
print(type(tree))  # <class 'ast.Module'>
```

---

## 3️⃣ EXTRACTION - Trích Xuất Nodes & Edges

### **File:** `extraction/models.py`

```python
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

class NodeType(Enum):
    FILE = "File"
    CLASS = "Class"
    FUNCTION = "Function"
    VARIABLE = "Variable"
    DEPENDENCY = "Dependency"

class EdgeType(Enum):
    CONTAINS = "CONTAINS"        # File chứa Function
    CALLS = "CALLS"              # Function gọi Function
    INHERITS = "INHERITS"        # Class kế thừa Class
    IMPORTS = "IMPORTS"          # Import module
    USES_VARIABLE = "USES_VARIABLE"

@dataclass
class GraphNode:
    id: str                       # "app/main.py::run"
    name: str                     # "run"
    type: NodeType                # NodeType.FUNCTION
    file_path: str                # "app/main.py"
    content: str = ""             # Docstring
    source_code: str = ""         # Mã nguồn gốc
    summary: str = ""             # Bản tóm tắt
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GraphEdge:
    source_id: str                # "app/main.py::run"
    target_id: str                # "ingestion/file_scanner.py::scan_py_files"  
    type: EdgeType                # EdgeType.CALLS
```

### **File:** `extraction/extractor.py` (Phần chính)

```python
import ast
import os
from typing import List, Tuple
from .models import NodeType, EdgeType, GraphNode, GraphEdge

class CodeKnowledgeExtractor(ast.NodeVisitor):
    """Trích xuất Nodes, Edges từ AST."""
    
    def __init__(self, file_path: str, source_code: str):
        self.file_path = file_path
        self.source_code = source_code
        self.nodes: List[GraphNode] = []
        self.edges: List[GraphEdge] = []
        
        self.current_file_id = f"file:{file_path}"
        self.current_class_id = None
        self.current_func_id = None
        
        # Tạo Node cho file
        self.nodes.append(GraphNode(
            id=self.current_file_id, 
            name=os.path.basename(file_path), 
            type=NodeType.FILE, 
            file_path=self.file_path,
            content="",
            source_code=self.source_code
        ))

    def visit_FunctionDef(self, node):
        """Xử lý khi tìm thấy function definition."""
        parent_id = self.current_class_id if self.current_class_id else self.current_file_id
        func_id = f"func:{self.file_path}::{node.name}"
        
        docstring = ast.get_docstring(node) or ""
        func_source = ast.get_source_segment(self.source_code, node) or ""
        
        # Tạo Node cho hàm
        self.nodes.append(GraphNode(
            id=func_id, 
            name=node.name, 
            type=NodeType.FUNCTION, 
            file_path=self.file_path,
            content=docstring,
            source_code=func_source
        ))
        
        # Tạo edge: file/class CONTAINS function
        self.edges.append(GraphEdge(parent_id, func_id, EdgeType.CONTAINS))
        
        # Recursively visit function body
        prev_func_id = self.current_func_id
        self.current_func_id = func_id
        self.generic_visit(node)
        self.current_func_id = prev_func_id

    def visit_ClassDef(self, node):
        """Xử lý khi tìm thấy class definition."""
        class_id = f"class:{self.file_path}::{node.name}"
        docstring = ast.get_docstring(node) or ""
        
        self.nodes.append(GraphNode(
            id=class_id, 
            name=node.name, 
            type=NodeType.CLASS, 
            file_path=self.file_path,
            content=docstring
        ))
        
        # File CONTAINS class
        self.edges.append(GraphEdge(self.current_file_id, class_id, EdgeType.CONTAINS))
        
        # Recursively visit class body
        prev_class_id = self.current_class_id
        self.current_class_id = class_id
        self.generic_visit(node)
        self.current_class_id = prev_class_id

    def visit_Call(self, node):
        """Xử lý khi tìm thấy function call."""
        if not self.current_func_id:
            self.generic_visit(node)
            return
            
        # Extract function name (đơn giản - chỉ handle func_name())
        callee_name = None
        if isinstance(node.func, ast.Name):
            callee_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            # Không handle method call hiện tại
            pass
        
        if callee_name:
            # Tìm callee_id từ nodes đã create
            for n in self.nodes:
                if n.name == callee_name and n.type == NodeType.FUNCTION:
                    callee_id = n.id
                    # Tạo edge: current_func CALLS callee
                    self.edges.append(
                        GraphEdge(self.current_func_id, callee_id, EdgeType.CALLS)
                    )
                    break
        
        self.generic_visit(node)

def extract_from_file(file_path: str) -> Tuple[List[GraphNode], List[GraphEdge]]:
    """
    Trích xuất toàn bộ nodes và edges từ một file.
    
    Args:
        file_path (str): Đường dẫn file .py
        
    Returns:
        Tuple[List[GraphNode], List[GraphEdge]]: Nodes và edges
    """
    with open(file_path, "r", encoding="utf-8") as f:
        source_code = f.read()
    
    tree = ast.parse(source_code)
    extractor = CodeKnowledgeExtractor(file_path, source_code)
    extractor.visit(tree)
    
    return extractor.nodes, extractor.edges
```

**Giải thích:**
- Dùng `ast.NodeVisitor` để duyệt cây AST
- Khi tìm `FunctionDef` → tạo GraphNode + edge CONTAINS
- Khi tìm `Call` → tạo edge CALLS (nếu tìm được callee)
- Dùng `ast.get_docstring()` & `ast.get_source_segment()` để lấy metadata

---

## 4️⃣ GRAPH - Xây Dựng Đồ Thị

### **File:** `graph/builder.py`

```python
import networkx as nx
import matplotlib.pyplot as plt
from typing import List
from extraction.models import GraphNode, GraphEdge

def build_graph(nodes: List[GraphNode], edges: List[GraphEdge]) -> nx.MultiDiGraph:
    """
    Xây dựng đồ thị đa nhãn từ nodes + edges.
    
    Args:
        nodes (List[GraphNode]): Danh sách node
        edges (List[GraphEdge]): Danh sách edge
        
    Returns:
        nx.MultiDiGraph: Đồ thị
    """
    graph = nx.MultiDiGraph()  # Tạo đồ thị mới
    
    # Thêm node
    for node in nodes:
        graph.add_node(
            node.id,                    # Node ID
            name=node.name,             # Tên
            type=node.type.value,       # Loại
            file_path=node.file_path,   # File
            source_code=node.source_code,  # Code
            content=node.content        # Docstring
        )
    
    # Thêm cạnh
    for edge in edges:
        graph.add_edge(
            edge.source_id,             # Từ node nào
            edge.target_id,             # Tới node nào
            relationship=edge.type.value  # Loại liên kết
        )
    
    return graph


def _collect_nodes(chain: dict | str) -> set[str]:
    """
    Đệ quy qua dict của call chain để lấy tất cả node ID.
    
    Args:
        chain (dict | str): Dict lồng từ get_call_chain() hoặc "[cycle]"
        
    Returns:
        set[str]: Tập hợp toàn bộ node ID
    """
    nodes = set()
    if isinstance(chain, str):  # "[cycle]" case
        return nodes
    for node_id, subtree in chain.items():
        nodes.add(node_id)
        nodes |= _collect_nodes(subtree)  # Đệ quy
    return nodes


def visualize_architecture(
    graph: nx.MultiDiGraph, 
    output_path: str = "architecture_map.png"
):
    """
    Vẽ bản đồ kiến trúc của dự án thành PNG.
    
    Args:
        graph (nx.MultiDiGraph): Đồ thị
        output_path (str): Đường dẫn xuất PNG
    """
    plt.figure(figsize=(24, 16))
    
    # Tính vị trí node (spring layout - nodes nổi ra)
    pos = nx.spring_layout(graph, k=0.8, iterations=100, seed=42)
    
    # Định nghĩa màu cho từng loại node
    color_map = {
        "File": "#1f77b4",          # Xanh dương
        "Class": "#2ca02c",         # Xanh lá
        "Function": "#d62728",      # Đỏ
        "Variable": "#bcbd22",      # Vàng
        "Dependency": "#7f7f7f"     # Xám
    }
    
    # Vẽ node
    for n_type, color in color_map.items():
        n_list = [n for n, d in graph.nodes(data=True) if d.get("type") == n_type]
        if n_list:
            size = 3500 if n_type == "File" else 1200
            nx.draw_networkx_nodes(
                graph, pos,
                nodelist=n_list,
                node_color=color,
                node_size=size,
                label=n_type
            )
    
    # Vẽ cạnh
    nx.draw_networkx_edges(
        graph, pos,
        width=1.5,
        alpha=0.6,
        arrows=True,
        arrowsize=20
    )
    
    # Vẽ nhãn
    labels = {n: d.get("name", n) for n, d in graph.nodes(data=True)}
    nx.draw_networkx_labels(
        graph, pos,
        labels=labels,
        font_size=8,
        font_weight="bold"
    )
    
    # Format
    plt.title("Bản đồ Kiến trúc Toàn diện Dự án", fontsize=25, pad=20)
    plt.legend(scatterpoints=1, loc="upper left", fontsize=15)
    plt.axis("off")
    plt.tight_layout()
    
    # Save
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"[+] Đã tạo bản đồ tại: {output_path}")
```

---

## 5️⃣ QUERY - Truy Vấn Đồ Thị

### **File:** `query/graph_query.py`

```python
import networkx as nx

def get_node_context(graph: nx.MultiDiGraph, node_id: str) -> dict:
    """
    Lấy toàn bộ thông tin chi tiết của một node.
    
    Args:
        graph: Đồ thị
        node_id: ID node (ví dụ: "app/main.py::run")
        
    Returns:
        dict: {id, name, type, file_path, docstring, source_code}
    """
    if node_id not in graph:
        return {}
    node_data = graph.nodes[node_id]
    return {
        "id": node_id,
        "name": node_data.get("name"),
        "type": node_data.get("type"),
        "file_path": node_data.get("file_path"),
        "docstring": node_data.get("content", ""),
        "source_code": node_data.get("source_code", "N/A")
    }


def get_call_chain(
    graph: nx.MultiDiGraph,
    start_node_id: str,
    depth: int = 2
) -> dict:
    """
    Xây dựng cây gọi hàm (call tree) từ một hàm, detect cycle.
    
    Args:
        graph: Đồ thị
        start_node_id: Node để bắt đầu
        depth: Độ sâu tối đa
        
    Returns:
        dict: Cây lồng của gọi hàm
        
    Ví dụ:
        {
            "app/main.py::run": {
                "ingestion/file_scanner.py::scan_py_files": {},
                "graph/builder.py::build_graph": {
                    "extraction/extractor.py::extract_from_file": {}
                }
            }
        }
    """
    def _expand(node: str, remaining_depth: int, path: frozenset) -> dict | str:
        # Nếu node đã trên path → cycle
        if node in path:
            return "[cycle]"
        
        # Nếu depth = 0 → dừng
        if remaining_depth == 0:
            return {}
        
        # Đánh dấu node lên path hiện tại
        current_path = path | {node}
        children = {}
        
        # Tìm toàn bộ node mà 'node' gọi
        callees = [
            v for _, v, data in graph.out_edges(node, data=True)
            if data.get("relationship") == "CALLS"
        ]
        
        # Đệ quy cho từng callee
        for callee in callees:
            children[callee] = _expand(callee, remaining_depth - 1, current_path)
        
        return children
    
    return {start_node_id: _expand(start_node_id, depth, frozenset())}


def format_call_chain(chain: dict) -> str:
    """
    Format dict lồng của call chain thành sơ đồ cây text đẹp.
    
    Args:
        chain: Dict từ get_call_chain()
        
    Returns:
        str: Sơ đồ cây dạng text
        
    Ví dụ output:
        run (main.py)
        ├── scan_py_files (file_scanner.py)
        ├── build_graph (builder.py)
        │   └── extract_from_file (extractor.py)
        └── [cycle]
    """
    def _short(node_id: str) -> str:
        # Chuyển "app/main.py::run" → "run (main.py)"
        if "::" in node_id:
            file_path, name = node_id.split("::", 1)
            file_name = file_path.split("/")[-1]  # Lấy phần sau cùng
            return f"{name} ({file_name})"
        return node_id
    
    def _render(node_id: str, subtree: dict | str, prefix: str, is_last: bool) -> list[str]:
        # Quyết định connector: "└── " (last) hay "├── " (not last)
        connector = "└── " if is_last else "├── "
        # Quyết định extension: "    " (last) hay "│   " (not last)
        extension = "    " if is_last else "│   "
        
        label = _short(node_id)
        
        # Nếu "[cycle]" → không có subtree
        if subtree == "[cycle]":
            return [prefix + connector + label + "  [cycle]"]
        
        lines = [prefix + connector + label]
        
        # Render subtree
        children = list(subtree.items())
        for i, (child_id, child_subtree) in enumerate(children):
            is_child_last = i == len(children) - 1
            lines += _render(child_id, child_subtree, prefix + extension, is_child_last)
        
        return lines
    
    lines = []
    for root_id, subtree in chain.items():
        # Render root
        lines.append(_short(root_id))
        children = list(subtree.items())
        for i, (child_id, child_subtree) in enumerate(children):
            is_last = i == len(children) - 1
            lines += _render(child_id, child_subtree, "", is_last)
    
    return "\n".join(lines)


def search_jit_context(
    graph: nx.MultiDiGraph,
    vstore,  # VectorStore instance
    ai_query: str,
    top_k: int = 2
) -> list[dict]:
    """
    Tìm kiếm hybrid (vector + BM25) để tìm node liên quan.
    
    Args:
        graph: Đồ thị
        vstore: VectorStore instance
        ai_query: Truy vấn của AI
        top_k: Số kết quả top
        
    Returns:
        list[dict]: Danh sách node tìm được
    """
    # Tìm bằng vector + BM25
    results = vstore.search(ai_query, top_k=top_k)
    
    # Đính kèm thông tin node từ graph
    for result in results:
        node_data = get_node_context(graph, result['id'])
        result.update(node_data)
    
    return results
```

---

## 6️⃣ EXPLAIN - Định Dạng Output

### **File:** `explain/formatter.py`

```python
from query.graph_query import get_call_chain, format_call_chain

def explain_function(graph, node_id: str) -> str:
    """
    Giải thích tất cả công việc của một hàm (call chain + format).
    
    Args:
        graph: Đồ thị
        node_id: ID hàm (ví dụ: "app/main.py::run")
        
    Returns:
        str: Sơ đồ cây đầy đủ
    """
    # Bước 1: Build call chain
    chain = get_call_chain(graph, node_id, depth=3)
    
    # Bước 2: Format thành sơ đồ cây
    tree = format_call_chain(chain)
    
    return tree
```

---

## 7️⃣ APP - Entry Point

### **File:** `app/main.py` - Hàm `run()`

```python
import os
import sys
import io
import networkx as nx
from collections import Counter

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.file_scanner import scan_py_files
from extraction.extractor import extract_from_file
from graph.builder import build_graph, visualize_architecture
from query.graph_query import get_call_chain, format_call_chain, search_jit_context
from indexing.vector_store import VectorStore

def run(repo_path: str):
    """
    Pipeline hoàn chỉnh:
    Scan → Extract → Graph → Index → Visualize → Query
    """
    
    # 1. SCAN: Tìm tất cả .py files
    print(f"[*] Đang quét thư mục: {os.path.abspath(repo_path)}")
    files = scan_py_files(repo_path)
    
    if not files:
        print("[-] Không tìm thấy file Python nào.")
        return
    
    # 2. EXTRACT: Trích xuất từ tất cả file
    all_nodes = []
    all_edges = []
    
    print(f"[*] Đang phân tích AST và trích xuất từ {len(files)} file...")
    for f in files:
        nodes, edges = extract_from_file(f)
        all_nodes.extend(nodes)
        all_edges.extend(edges)
    
    # 3. GRAPH: Build đồ thị
    print(f"[*] Đang dựng Knowledge Graph...")
    graph = build_graph(all_nodes, all_edges)
    
    node_types = nx.get_node_attributes(graph, 'type').values()
    type_counts = Counter(node_types)
    print(f"[+] Tổng: {len(graph.nodes)} Nodes, {len(graph.edges)} Edges")
    print(f"[+] Phân bổ: {dict(type_counts)}")
    
    if len(graph.nodes) == 0:
        print("[-] Đồ thị rỗng.")
        return
    
    os.makedirs("db", exist_ok=True)
    
    # 4. INDEX: Lưu vào vector store
    vstore = VectorStore()
    vstore.add_nodes(all_nodes)
    
    # 5. VISUALIZE: Vẽ bản đồ
    output_img = "db/full_architecture_map.png"
    print(f"[*] Đang vẽ bản đồ kiến trúc...")
    visualize_architecture(graph, output_path=output_img)
    
    # 6. QUERY: Tìm kiếm semantic
    print("\n" + "="*50)
    print(" DEMO: HYBRID SEARCH (VECTOR + BM25)")
    print("="*50)
    
    ai_query = "extract nodes and edges from abstract syntax tree"
    print(f"[*] Truy vấn: '{ai_query}'")
    
    top_contexts = search_jit_context(graph, vstore, ai_query, top_k=2)
    
    for i, ctx in enumerate(top_contexts, 1):
        print(f"\n--- [Kết quả {i}: {ctx['name']}] ---")
        print(f"Type: {ctx['type']} | File: {ctx['file_path']}")
        print(f"Docstring: {ctx['docstring'][:200]}")
        
        # Vẽ call chain
        chain = get_call_chain(graph, ctx['id'], depth=1)
        print("\nCấu trúc liên kết:")
        print(format_call_chain(chain))

if __name__ == "__main__":
    run(".")
```

---

## 🔗 Mối Liên Kết Giữa Các Hàm

```
run()
├─→ scan_py_files()           [ingestion]
│   └─→ Path.rglob()          [pathlib]
│
├─→ extract_from_file()       [extraction] ×N files
│   ├─→ parse_file()          [parsing]
│   │   └─→ ast.parse()       [ast]
│   └─→ CodeKnowledgeExtractor.visit()
│       ├─→ visit_FunctionDef()
│       ├─→ visit_ClassDef()
│       ├─→ visit_Call()
│       └─→ visit_Import()
│
├─→ build_graph()             [graph]
│   └─→ nx.MultiDiGraph()     [networkx]
│
├─→ visualize_architecture()  [graph]
│   ├─→ _collect_nodes()
│   └─→ plt.savefig()          [matplotlib]
│
├─→ VectorStore.add_nodes()   [indexing]
│
└─→ search_jit_context()      [query]
    ├─→ get_call_chain()
    │   └─→ _expand()         [recursive]
    ├─→ format_call_chain()
    └─→ VectorStore.search()
```

---

## 📊 Ví Dụ Trực Tiếp

### **Chạy pipeline hoàn chỉnh:**

```python
from app.main import run

run(".")  # Quét dự án hiện tại
```

**Output:**
```
[*] Đang quét thư mục: d:\Code\DALN\Caeser
[*] Đang phân tích AST và trích xuất từ 42 file...
[*] Đang dựng Knowledge Graph với 187 Nodes và 342 Edges...
[+] Phân bổ: {'File': 42, 'Function': 120, 'Class': 25}
[*] Đang vẽ bản đồ kiến trúc...
[+] Đã tạo bản đồ tại: db/full_architecture_map.png

==================================================
 DEMO: HYBRID SEARCH (VECTOR + BM25)
==================================================
[*] Truy vấn: 'extract nodes and edges from abstract syntax tree'

--- [Kết quả 1: extract_from_file] ---
Type: Function | File: extraction/extractor.py
Docstring: Trích xuất toàn bộ nodes và edges từ một file...

Cấu trúc liên kết:
extract_from_file (extractor.py)
└── CodeKnowledgeExtractor.visit()
    ├── visit_FunctionDef()
    └── visit_Call()
```

---

**Tài liệu này giúp bạn hiểu sâu hơn về source code!** 🚀
