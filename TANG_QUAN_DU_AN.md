# 📊 SƠ ĐỒ TỔNG QUÁT DỰ ÁN PA

## 🎯 Mục Đích Chính

Hệ thống phân tích mã nguồn Python tĩnh để:
- ✅ Quét và trích xuất structure code
- ✅ Xây dựng đồ thị mối quan hệ gọi hàm (call graph)
- ✅ Cho phép truy vấn "hàm X gọi hàm nào?" hoặc "ai gọi hàm X?"
- ✅ Trực quan hóa bằng PNG, sơ đồ cây text
- ✅ Hỗ trợ tìm kiếm semantic (AI-powered search)

---

## 🔄 Quy Trình Dữ Liệu (Data Flow)

```
INPUT: Đường dẫn thư mục (repository)
  │
  ├─→ [1] ingestion/file_scanner.py::scan_py_files()
  │         Quét tất cả *.py → Danh sách file paths
  │
  ├─→ [2] parsing/parser.py::parse_file()
  │         Chuyển code thành AST tree
  │
  ├─→ [3] extraction/extractor.py::extract_from_file()
  │         Trích từ AST: hàm, class, biến, gọi hàm → GraphNode, GraphEdge
  │
  ├─→ [4] graph/builder.py::build_graph()
  │         ┌─────────────────────────────────────────┐
  │         │ Tạo nx.MultiDiGraph từ nodes + edges   │
  │         │ Lưu metadata đầy đủ vào từng node      │
  │         └─────────────────────────────────────────┘
  │            │
  │            ├─→ [4a] visualize_architecture()
  │            │         Vẽ PNG: full_architecture_map.png
  │            │
  │            └─→ [5] query/graph_query.py
  │                    ├─ get_call_chain() → cây gọi (dict)
  │                    ├─ format_call_chain() → sơ đồ cây (str)
  │                    ├─ get_function_calls() → ai gọi?
  │                    ├─ get_callers() → tôi được ai gọi?
  │                    └─ search_jit_context() → tìm semantic
  │
  ├─→ [6] explain/formatter.py::explain_function()
  │         Kết hợp call chain + format → output cuối
  │
  ├─→ [7] indexing/vector_store.py::VectorStore
  │         Lưu embedding node vào ChromaDB + BM25 index
  │
  └─→ OUTPUT: Sơ đồ cây + Hình ảnh + Kết quả truy vấn
```

---

## 📂 CẤU TRÚC FILE LOGIC

```
┌─────────────────────────────────────────────────────────────┐
│                    app/main.py (ENTRY POINT)               │
│                    run(repo_path)                          │
└────────────┬────────────────────────────────────────────────┘
             │
      ┌──────┴──────┬────────┬─────────┬──────────┬──────────┐
      │             │        │         │          │          │
      ▼             ▼        ▼         ▼          ▼          ▼
┌──────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│ingestion │ │parsing  │ │extract  │ │ graph   │ │ query   │ │explain  │
│          │ │         │ │         │ │         │ │         │ │         │
│scan_py   │ │parse_   │ │extract_ │ │build_   │ │get_call │ │explain_ │
│files()   │ │file()   │ │from_    │ │graph()  │ │chain()  │ │function │
│          │ │         │ │file()   │ │         │ │format_  │ │()       │
│List[str] │ │ast.AST  │ │(Node[], │ │MultiDi  │ │chain()  │ │String   │
│          │ │         │ │Edge[])  │ │Graph    │ │Search   │ │(Tree)   │
└──────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘
   INPUT      AST Tree    Entities   Knowledge   Queries    Pretty
                                      Graph              Output
```

---

## 🔑 Khái Niệm Chính

### **1. GraphNode** (Đơn vị cơ bản)
```
GraphNode {
  id: "app/main.py::run"                    # Duy nhất
  name: "run"                               # Tên hàm
  type: NodeType.FUNCTION                   # Loại
  file_path: "app/main.py"                  # Đường dẫn
  content: "Docstring của hàm"              # Mô tả
  source_code: "def run(...):\n    ..."     # Code gốc
  summary: "Chạy pipeline"                  # Tóm tắt
}
```

### **2. GraphEdge** (Mối quan hệ)
```
GraphEdge {
  source_id: "app/main.py::run"              # Từ
  target_id: "ingestion/file_scanner.py::scan_py_files"  # Đến
  type: EdgeType.CALLS                      # Loại liên kết
}
```

### **3. Call Chain** (Cây gọi hàm)
```
{
  "app/main.py::run": {
    "ingestion/file_scanner.py::scan_py_files": {},  # Không gọi hàm nào
    "graph/builder.py::build_graph": {
      "extraction/extractor.py::extract_from_file": {},
      # ...
    },
    # ...
  }
}
```

---

## 🎬 Ví Dụ Thực Thi

### **Scenario 1: Người dùng muốn biết hàm `run()` gọi hàm nào?**

```python
chain = get_call_chain(graph, "app/main.py::run", depth=3)
tree = format_call_chain(chain)
print(tree)
```

**Output:**
```
run (main.py)
├── scan_py_files (file_scanner.py)
├── build_graph (builder.py)
├── visualize_architecture (builder.py)
│   ├── get_call_chain (graph_query.py)
│   └── _collect_nodes (builder.py)
├── extract_from_file (extractor.py)
└── search_jit_context (graph_query.py)
    └── get_call_chain (graph_query.py)  [cycle]
```

### **Scenario 2: Người dùng muốn tìm hàm liên quan đến "extract"?**

```python
results = search_jit_context(graph, vstore, "extract nodes", top_k=3)
for r in results:
    print(f"{r['name']}: {r['docstring'][:100]}")
```

**Output:**
```
extract_from_file: Duyệt AST, trích xuất hàm, class, biến, mối gọi...
GraphNode: Định nghĩa node trong đồ thị...
extract: Trích xuất thực thể từ cây AST...
```

---

## 📊 Các Node Types

| Type | Ý Nghĩa | Ví dụ |
|------|---------|-------|
| **FILE** | File Python | `app/main.py` |
| **CLASS** | Class/Object | `class MyClass:` |
| **FUNCTION** | Hàm | `def run():` |
| **VARIABLE** | Biến toàn cục | `result = []` |
| **DEPENDENCY** | External import | `import networkx` |

---

## 📊 Các Edge Types

| Type | Ý Nghĩa | Ví dụ |
|------|---------|-------|
| **CALLS** | Hàm A gọi hàm B | `run()` → `scan_py_files()` |
| **CONTAINS** | File chứa hàm | `main.py` ◄── `run()` |
| **INHERITS** | Class kế thừa | Class B ← Class A |
| **IMPORTS** | Import module | `import networkx` |
| **USES** | Sử dụng biến | Hàm A dùng `global_var` |

---

## 🧪 Các Test Case Chính

| Test | Kiểm tra gì |
|------|-----------|
| `test_build_graph_returns_digraph` | Graph là MultiDiGraph? |
| `test_nodes_created_for_each_function` | Mỗi hàm tạo 1 node? |
| `test_edge_created_for_call` | Gọi hàm → edge? |
| `test_no_edge_for_unknown_call` | Gọi hàm chưa biết → không edge ✓ |
| `test_cycle_detection` | Phát hiện vòng lặp [cycle]? |

---

## ⚠️ Hạn Chế Hiện Tại (Phase 1)

### **Không xử lý được:**
- ❌ `obj.method()` — gọi method qua object
- ❌ `os.path.join()` — gọi module path  
- ❌ `callback()` — gọi qua biến pointer
- ❌ Lambda & nested function phức tạp
- ❌ Dynamic call via eval, exec

### **Tại sao?**
Hiện tại chỉ dùng static regex trên AST Name node, không phân tích attribute access hay dynamic binding.

---

## 🚀 Lộ Trình Phát Triển

### **Phase 1 (Hiện tại): Foundation ✅**
- ✅ Scan + Parse + Extract + Graph
- ✅ Basic query (call chain, format)
- ✅ Visualization (PNG, tree)

### **Phase 2: AI Integration**
- 🔄 LLM summarization (tóm tắt auto)
- 🔄 Semantic search (AI-powered)
- 🔄 Agent orchestration

### **Phase 3: Advanced Analysis**
- ⏳ Multi-language support
- ⏳ Complexity metrics
- ⏳ Optimization suggestions

---

## 💻 Command Quick Reference

```bash
# Scan project
python -c "from ingestion.file_scanner import scan_py_files; print(len(scan_py_files('.')))"

# Parse single file
python -c "from parsing.parser import parse_file; print(parse_file('app/main.py'))"

# Run full pipeline
python app/main.py

# Run tests
pytest tests/ -v

# Check coverage
pytest --cov=. tests/
```

---

## 📚 Liên Kết Tài Liệu

- **Chi tiết:** [HUONG_DAN_CHI_TIET.md](HUONG_DAN_CHI_TIET.md)
- **Phân tích:** [project_analysis.md](project_analysis.md)
- **Kế hoạch:** [docs/guides/PHASE1_PLAN.md](docs/guides/PHASE1_PLAN.md)
- **Kiến trúc:** [docs/architecture/overview.md](docs/architecture/overview.md)

---

**Tài liệu được cập nhật: 20/04/2026**
