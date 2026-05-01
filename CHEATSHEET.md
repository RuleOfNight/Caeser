# ⚡ QUICK REFERENCE - PA PROJECT CHEATSHEET

## 🎬 Nhanh 5 phút Setup

```bash
# 1️⃣ Activate venv
venv\Scripts\activate

# 2️⃣ Install dependencies
pip install -r requirements.txt

# 3️⃣ Run pipeline
python app/main.py

# 4️⃣ View results
# - Bản đồ: db/full_architecture_map.png
# - Console output: Sơ đồ cây + kết quả truy vấn
```

---

## 🔨 Import Statements Cơ Bản

```python
# Scan file
from ingestion.file_scanner import scan_py_files
files = scan_py_files(".")  # List all .py files

# Parse AST
from parsing.parser import parse_file
ast_tree = parse_file("app/main.py")

# Extract nodes + edges
from extraction.extractor import extract_from_file
nodes, edges = extract_from_file("app/main.py")

# Build graph
from graph.builder import build_graph, visualize_architecture
graph = build_graph(nodes, edges)
visualize_architecture(graph, "output.png")

# Query graph
from query.graph_query import get_call_chain, format_call_chain, search_jit_context
chain = get_call_chain(graph, "app/main.py::run", depth=2)
tree = format_call_chain(chain)
print(tree)

# Vector search
from indexing.vector_store import VectorStore
vstore = VectorStore()
vstore.add_nodes(nodes)
results = search_jit_context(graph, vstore, "extract functions", top_k=3)

# Format output
from explain.formatter import explain_function
output = explain_function(graph, "app/main.py::run")
print(output)
```

---

## 📊 Dữ Liệu Struct

### **GraphNode**
```python
from extraction.models import GraphNode, NodeType

node = GraphNode(
    id="app/main.py::run",              # Unique ID
    name="run",                         # Function name
    type=NodeType.FUNCTION,             # Node type
    file_path="app/main.py",            # Source file
    content="Function docstring",       # Description
    source_code="def run(...):\n...",   # Code
    summary="Runs pipeline",            # 1-2 line summary
)
```

### **GraphEdge**
```python
from extraction.models import GraphEdge, EdgeType

edge = GraphEdge(
    source_id="app/main.py::run",
    target_id="ingestion/file_scanner.py::scan_py_files",
    type=EdgeType.CALLS,                # Relationship type
)
```

### **Call Chain Dict**
```python
{
    "app/main.py::run": {
        "ingestion/file_scanner.py::scan_py_files": {},
        "graph/builder.py::build_graph": {
            "extraction/extractor.py::extract_from_file": {},
        },
    }
}
```

---

## 🎯 Common Tasks

### **1️⃣ Tìm hàm X gọi hàm nào?**
```python
chain = get_call_chain(graph, "app/main.py::run", depth=3)
print(format_call_chain(chain))
```

### **2️⃣ Tìm ai gọi hàm X?**
```python
callers = [src for src, dst in graph.in_edges("app/main.py::run")]
for caller in callers:
    print(caller)
```

### **3️⃣ Tìm hàm liên quan đến keyword?**
```python
results = search_jit_context(graph, vstore, "parse python code", top_k=5)
for r in results:
    print(f"{r['name']}: {r['score']:.2f}")
```

### **4️⃣ Vẽ bản đồ dự án?**
```python
visualize_architecture(graph, output_path="db/architecture.png")
# Mở: db/architecture.png
```

### **5️⃣ Xem chi tiết hàm?**
```python
node_data = graph.nodes["app/main.py::run"]
print(f"Name: {node_data['name']}")
print(f"Type: {node_data['type']}")
print(f"File: {node_data['file_path']}")
print(f"Docstring: {node_data['content']}")
print(f"Code: {node_data['source_code']}")
```

---

## 📁 File Layout

```
app/main.py          ← Chạy: python app/main.py
├─ ingestion/        ← Quét file
├─ parsing/          ← AST parse
├─ extraction/       ← Trích node + edge
├─ graph/            ← Build đồ thị
├─ query/            ← Truy vấn
├─ explain/          ← Format output
└─ indexing/         ← Vector store

tests/unit/          ← Chạy: pytest tests/
db/                  ← Output PNG, DB files
docs/                ← Tài liệu
```

---

## 🧪 Test Commands

```bash
# Chạy tất cả test
pytest tests/

# Chạy 1 file test
pytest tests/unit/test_builder.py -v

# Chạy 1 test function
pytest tests/unit/test_builder.py::test_build_graph_returns_digraph -v

# Coverage report
pytest --cov=. tests/
```

---

## 🔍 Debug Tips

### **Kiểm tra input/output từng bước:**
```python
# Step 1: Files
files = scan_py_files(".")
print(f"Found {len(files)} files: {files[:3]}")

# Step 2: Parse
ast_tree = parse_file(files[0])
print(f"Parsed type: {type(ast_tree)}")

# Step 3: Extract
nodes, edges = extract_from_file(files[0])
print(f"Got {len(nodes)} nodes, {len(edges)} edges")

# Step 4: Build
graph = build_graph(nodes, edges)
print(f"Graph: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
```

### **In chi tiết node:**
```python
node = graph.nodes["app/main.py::run"]
for key, value in node.items():
    print(f"{key}: {value}")
```

### **Kiểm tra edge:**
```python
edges = graph.edges("app/main.py::run", data=True)
for src, dst, attr in edges:
    print(f"{src} --{attr['relationship']}--> {dst}")
```

---

## 📊 Node Types & Edge Types

**NodeType enum:**
- `FILE` → File Python
- `CLASS` → Class/Object  
- `FUNCTION` → Function/Method
- `VARIABLE` → Variable
- `DEPENDENCY` → External lib

**EdgeType enum:**
- `CALLS` → Hàm gọi hàm
- `CONTAINS` → File chứa hàm
- `INHERITS` → Class kế thừa
- `IMPORTS` → Import module
- `USES_VARIABLE` → Dùng biến

---

## ⚡ Most Used APIs

| API | Purpose | Example |
|-----|---------|---------|
| `scan_py_files(path)` | Find all `.py` | `scan_py_files(".")` |
| `parse_file(path)` | Get AST tree | `parse_file("main.py")` |
| `extract_from_file(path)` | Get nodes+edges | `extract_from_file("main.py")` |
| `build_graph(nodes, edges)` | Create graph | `build_graph(n, e)` |
| `get_call_chain(g, node, depth)` | Build call tree | `get_call_chain(g, "x::f", 2)` |
| `format_call_chain(chain)` | Format tree | `format_call_chain(chain)` |
| `search_jit_context(g, v, q, k)` | Search by query | `search_jit_context(g, v, "find", 3)` |
| `visualize_architecture(g, path)` | Draw PNG | `visualize_architecture(g, "x.png")` |

---

## 🎓 Data Flow Diagram

```
repo_path
    ↓
[scan_py_files]
    ↓
list[str] file_paths
    ↓
for each file:
  [parse_file] → ast.AST
  [extract_from_file] → (nodes[], edges[])
    ↓
all_nodes[], all_edges[]
    ↓
[build_graph]
    ↓
nx.MultiDiGraph
    ├→ [visualize_architecture] → PNG
    └→ [get_call_chain] 
       [format_call_chain] → string tree
```

---

## 🐛 Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: No module named 'X'` | Chưa install | `pip install -r requirements.txt` |
| `FileNotFoundError: 'app/main.py'` | Sai path | Dùng abs path hoặc chạy từ root |
| `KeyError: 'node_id'` | Node không tồn tại | Kiểm tra `print(graph.nodes())` |
| `[cycle]` trong output | Đệ quy | OK - hệ thống tự detect |
| `PNG file rỗng` | Graph quá lớn | Giảm depth hoặc filter nodes |

---

## 🚀 One-Liner Snippets

```python
# 1. Quét + Parse + Extract
from ingestion.file_scanner import scan_py_files
from extraction.extractor import extract_from_file
all_data = [(f, extract_from_file(f)) for f in scan_py_files(".")]

# 2. Build + Query
from graph.builder import build_graph
from query.graph_query import get_call_chain, format_call_chain
g = build_graph(*zip(*[extract_from_file(f) for f in scan_py_files(".")]))
print(format_call_chain(get_call_chain(g, "app/main.py::run", 2)))

# 3. Search
from indexing.vector_store import VectorStore
from query.graph_query import search_jit_context
vs = VectorStore()
vs.add_nodes([n for n,_ in all_data])
print(search_jit_context(g, vs, "extract code", 3))
```

---

## 📞 Khi Cần Giúp

1. **Không hiểu module X?** → Xem `HUONG_DAN_CHI_TIET.md`
2. **Muốn diagram?** → Xem `TANG_QUAN_DU_AN.md`
3. **Muốn code example?** → Xem `project_analysis.md`
4. **Muốn kế hoạch?** → Xem `docs/guides/PHASE1_PLAN.md`
5. **Muốn chạy test?** → `pytest tests/ -v`

---

**Cập nhật: 20/04/2026**
