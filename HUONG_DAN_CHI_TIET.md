# 📚 HƯỚNG DẪN CHI TIẾT DỰ ÁN - PA (Project Assistant)

---

## 📋 MỤC LỤC
1. [Tổng quan dự án](#tổng-quan-dự-án)
2. [Cấu trúc thư mục](#cấu-trúc-thư-mục)
3. [Quy trình hoạt động](#quy-trình-hoạt-động)
4. [Chi tiết từng Module](#chi-tiết-từng-module)
5. [Cách sử dụng từng bước](#cách-sử-dụng-từng-bước)
6. [Ví dụ thực tế](#ví-dụ-thực-tế)
7. [Dependency & Yêu cầu](#dependency--yêu-cầu)

---

## 🎯 TỔNG QUAN DỰ ÁN

### **PA — Hệ thống Phân tích Mã nguồn Python**

**Mục đích:** Quét một dự án Python, trích xuất cấu trúc code (các hàm, class, biến), xây dựng **đồ thị gọi hàm** (call graph), và cung cấp công cụ truy vấn để hiểu luồng chương trình.

**Tính chất:**
- 🔍 **Phân tích tĩnh** (Static Analysis) — không chạy code
- 🐍 **Chỉ Python** — sử dụng module `ast` có sẵn
- 🚫 **Không dùng AI/LLM** — Phase 1 thuần logic
- 📊 **Xây dựng đồ thị** — dùng NetworkX (thư viện đồ thị)
- 🖼️ **Trực quan hóa** — vẽ file `graph.png` để nhìn rõ cấu trúc code

**Trạng thái:** Phase 1 — Foundation (nền tảng cơ bản đang xây dựng)

---

## 📂 CẤU TRÚC THƯ MỤC

```
PA/
├── app/                          # Ứng dụng chính
│   ├── __init__.py
│   ├── main.py                   # ⚙️ ĐIỂM KHỞI CHẠY - chứa hàm run()
│   └── agent_test.py             # Test cơ bản cho agent
│
├── ingestion/                    # **[1️⃣ BƯỚC 1]** Quét file
│   ├── __init__.py
│   └── file_scanner.py           # Tìm tất cả *.py trong thư mục
│
├── parsing/                      # **[2️⃣ BƯỚC 2]** Đọc cú pháp (AST)
│   ├── __init__.py
│   └── parser.py                 # Chuyển code thành cây cú pháp
│
├── extraction/                   # **[3️⃣ BƯỚC 3]** Trích xuất thông tin
│   ├── __init__.py
│   ├── models.py                 # Định nghĩa cấu trúc dữ liệu (GraphNode, GraphEdge)
│   └── extractor.py              # Trích xuất hàm, class, biến từ AST
│
├── graph/                        # **[4️⃣ BƯỚC 4]** Xây dựng đồ thị
│   ├── __init__.py
│   └── builder.py                # Tạo graph, vẽ PNG
│
├── query/                        # **[5️⃣ BƯỚC 5]** Truy vấn đồ thị
│   ├── __init__.py
│   └── graph_query.py            # Tìm hàm gọi hàm, liệt kê mối quan hệ
│
├── explain/                      # **[6️⃣ BƯỚC 6]** Định dạng output
│   ├── __init__.py
│   └── formatter.py              # Xuất ra sơ đồ cây dễ đọc
│
├── indexing/                     # **[7️⃣ BƯỚC 7]** Lập chỉ mục (Vector Store)
│   ├── __init__.py
│   └── vector_store.py           # Lưu trữ embedding cho tìm kiếm semantic
│
├── tests/                        # Test coverage
│   └── unit/
│       ├── test_file_scanner.py
│       ├── test_parser.py
│       ├── test_extractor.py
│       ├── test_builder.py
│       ├── test_graph_query.py
│       └── test_formatter.py
│
├── db/                           # 💾 Lưu trữ dữ liệu
│   ├── full_architecture_map.png # Bản đồ kiến trúc được vẽ tự động
│   └── (Các file DB khác)
│
├── docs/                         # 📖 Tài liệu
│   ├── architecture/
│   │   └── overview.md           # Thiết kế kiến trúc tổng thể
│   └── guides/
│       ├── getting-started.md
│       ├── MASTER_PLAN.md
│       ├── phase1_execution.md
│       └── PHASE1_PLAN.md        # Kế hoạch Phase 1
│
├── agents/                       # 🤖 Cấu hình agent AI (Phase 2+)
│   ├── README.md
│   ├── tools.py
│   └── workflow.py
│
├── config/                       # ⚙️ Cấu hình
│   └── settings.json             # Model: claude-sonnet-4-6
│
├── memory/                       # 🧠 Lưu trữ dài hạn
│   └── MEMORY.md
│
├── rules/                        # 📏 Quy tắc hành vi
│   ├── core.md
│   └── agent-behavior.md
│
├── hooks/                        # 🔗 Event-driven automation
│   └── README.md
│
├── skills/                       # 💡 Reusable skill definitions
│   ├── TEMPLATE.md
│   └── python-testing/
│       └── SKILL.md
│
├── prompts/                      # 💬 Prompt templates
│   ├── system/
│   │   ├── general_system.txt
│   │   ├── phase1_system.txt
│   │   └── README.md
│   └── templates/
│       └── README.md
│
├── evals/                        # 📊 Test & Evaluation
│   ├── README.md
│   └── (chưa có nội dung)
│
├── scripts/                      # 🔧 Utility scripts
│   └── (chưa có nội dung)
│
├── data/                         # 📦 Dữ liệu mẫu
│   └── sample_repo/
│       └── test_attr.py          # File test mẫu
│
├── CLAUDE.md                     # 📋 Cấu trúc project (theo CLAUDE)
├── project_analysis.md           # 📊 Phân tích dự án (chi tiết)
└── requirements.txt              # 📦 Dependencies
```

---

## ⚙️ QUY TRÌNH HOẠT ĐỘNG

### **Biểu đồ Pipeline từ Trái sang Phải:**

```
┌─────────────┐
│Source Code  │
│   (Python)  │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐        ┌─────────────┐
│  ingestion/         │        │ file_scanner│
│  Quét file          │◄────────    scan_py  │
└──────┬──────────────┘        │   _files() │
       │ (Danh sách .py)       └─────────────┘
       │
       ▼
┌─────────────────────┐        ┌─────────────┐
│  parsing/           │        │  parser.py  │
│  Đọc AST            │◄────────  parse_file│
└──────┬──────────────┘        │    ()       │
       │ (ast.AST tree)        └─────────────┘
       │
       ▼
┌─────────────────────┐        ┌─────────────┐
│  extraction/        │        │ models.py   │
│  Trích xuất         │        │ GraphNode   │
│  thông tin          │        │ GraphEdge   │
└──────┬──────────────┘        └─────────────┘
       │ (GraphNode[], GraphEdge[])
       │
       ▼
┌─────────────────────┐        ┌─────────────┐
│  graph/             │        │ builder.py  │
│  Xây đồ thị         │◄────────  build_     │
└──────┬──────────────┘        │   graph()   │
       │ (nx.MultiDiGraph)     └─────────────┘
       │
       ├─────────────────────────┐
       │                         │
       ▼                         ▼
   ┌───────────┐         ┌──────────────┐
   │ query/    │         │ graph/       │
   │ Truy vấn  │◄───┐    │ visualize_   │
   │ đồ thị    │    └────► architecture │
   └─────┬─────┘         │ .png         │
         │               └──────────────┘
         ▼
   ┌──────────┐
   │ explain/ │
   │ Format   │
   │ output   │
   └────┬─────┘
        │
        ▼
   ┌──────────────┐
   │ Kết quả:     │
   │ - Sơ đồ cây  │
   │ - Mối liên kết
   │ - Hình ảnh   │
   └──────────────┘
```

**Théloại dữ liệu từ trái sang phải:**
1. File `.py` → Danh sách đường dẫn
2. Danh sách đường dẫn → AST tree
3. AST tree → GraphNode, GraphEdge
4. GraphNode, GraphEdge → nx.MultiDiGraph
5. nx.MultiDiGraph → Sơ đồ cây + PNG + Thông tin

---

## 📚 CHI TIẾT TỪNG MODULE

### **[1️⃣ BƯỚC 1] `ingestion/` — Quét file Python**

**File chính:** [ingestion/file_scanner.py](ingestion/file_scanner.py)

**Hàm chính:**
```python
scan_py_files(root: str) -> list[str]
```

**Tác dụng:**
- Tìm **tất cả** file `.py` trong thư mục `root` (toàn bộ, đệ quy)
- **Loại trừ** các thư mục: `venv`, `.venv`, `__pycache__`, `.git`, `tests`
- Trả về danh sách đường dẫn dạng `/` (posix)

**Ví dụ:**
```python
files = scan_py_files(".")
# Kết quả:
# ["app/main.py", "ingestion/file_scanner.py", "parsing/parser.py", ...]
```

**Điểm lưu ý:**
- Hàm dùng `pathlib.Path.rglob()` — tìm kiếm đệ quy toàn bộ cây thư mục
- `_EXCLUDE = {".venv", "venv", "__pycache__", ".git"}` — danh sách "thư mục cấm"
- Kết quả là danh sách `str` đơn thuần

---

### **[2️⃣ BƯỚC 2] `parsing/` — Đọc cú pháp (AST)**

**File chính:** [parsing/parser.py](parsing/parser.py)

**Hàm chính:**
```python
parse_file(path: str) -> ast.AST
```

**Tác dụng:**
- Đọc nội dung file Python
- Chuyển source code thành **Abstract Syntax Tree (AST)** — cây cú pháp trừu tượng
- AST là đại diện nội bộ của Python để "hiểu" code mà không chạy code

**Ví dụ:**
```python
import ast
tree = parse_file("app/main.py")
# Kết quả: ast.Module(body=[...])

# tree là một cấu trúc cây với các node:
# - Module (root)
#   ├── FunctionDef (hàm run)
#   │   ├── Call (gọi hàm)
#   │   └── ...
#   └── ...
```

**Lý do dùng AST:**
- Không cần chạy code → nhanh, an toàn
- Có thể trích xuất hàm, class, biến mà không hiểu ý nghĩa
- Python built-in module `ast` — không cần cài thêm gì

---

### **[3️⃣ BƯỚC 3] `extraction/` — Trích xuất thông tin**

**File chính:**
- [extraction/models.py](extraction/models.py) — Định nghĩa cấu trúc dữ liệu
- [extraction/extractor.py](extraction/extractor.py) — Trích xuất từ AST

#### **A. Cấu trúc dữ liệu (`models.py`):**

```python
class NodeType(Enum):
    FILE = "File"
    CLASS = "Class"
    FUNCTION = "Function"
    VARIABLE = "Variable"
    DEPENDENCY = "Dependency"

class EdgeType(Enum):
    CONTAINS = "CONTAINS"      # File chứa Class/Function
    CALLS = "CALLS"            # Hàm gọi hàm
    INHERITS = "INHERITS"      # Class kế thừa Class
    IMPORTS = "IMPORTS"        # Import module
    USES_VARIABLE = "USES_VARIABLE"  # Sử dụng biến

@dataclass
class GraphNode:
    id: str                     # Duy nhất, ví dụ: "app/main.py::run"
    name: str                   # Tên hàm/class, ví dụ: "run"
    type: NodeType              # Loại: FILE, CLASS, FUNCTION, ...
    file_path: str              # Đường dẫn file
    content: str                # Docstring hoặc mô tả
    source_code: str            # Mã nguồn gốc (để AI đọc)
    summary: str                # Bản tóm tắt (tiết kiệm token)
    metadata: Dict              # Thông tin bổ sung

@dataclass
class GraphEdge:
    source_id: str              # Node nguồn
    target_id: str              # Node đích
    type: EdgeType              # Loại liên kết
```

#### **B. Hàm trích xuất (`extractor.py`):**

```python
extract_from_file(file_path: str) -> (List[GraphNode], List[GraphEdge])
```

**Tác dụng:**
- Duyệt qua cây AST của file
- Tìm **tất cả hàm** (function definition)
- Tìm **tất cả class** (class definition)
- Tìm **tất cả biến** toàn cục (global variables)
- Tìm **các lệnh gọi hàm** (function calls) trong từng hàm
- Tạo `GraphNode` cho mỗi entity
- Tạo `GraphEdge` cho mỗi mối quan hệ (ai gọi ai, ai chứa ai)

**Ví dụ output:**
```python
nodes = [
    GraphNode(id="app/main.py::run", name="run", type=NodeType.FUNCTION, ...),
    GraphNode(id="app/main.py", name="app/main.py", type=NodeType.FILE, ...),
    GraphNode(id="ingestion/file_scanner.py::scan_py_files", ...),
    # ...
]

edges = [
    GraphEdge("app/main.py::run", "ingestion/file_scanner.py::scan_py_files", EdgeType.CALLS),
    GraphEdge("app/main.py", "app/main.py::run", EdgeType.CONTAINS),
    # ...
]
```

**⚠️ Hạn chế hiện tại:**
- Chỉ phát hiện lệnh gọi hàm **đơn giản**: `func_name()`
- **CHƯA xử lý được:**
  - Gọi qua object: `obj.method()` ❌
  - Gọi qua module: `os.path.join()` ❌
  - Gọi qua biến: `callback()` ❌
  - Lambda functions ❌

---

### **[4️⃣ BƯỚC 4] `graph/` — Xây dựng đồ thị**

**File chính:** [graph/builder.py](graph/builder.py)

**Hàm chính:**
```python
build_graph(nodes: List[GraphNode], edges: List[GraphEdge]) -> nx.MultiDiGraph
```

**Tác dụng:**
1. Tạo một đồ thị **nhiều cạnh có hướng** (MultiDiGraph) từ NetworkX
2. Nạp tất cả `GraphNode` thành node trong graph
3. Nạp tất cả `GraphEdge` thành edge (cạnh) trong graph
4. Lưu đầy đủ metadata (id, name, type, file_path, docstring, v.v.)

**Ví dụ:**
```python
graph = build_graph(nodes, edges)
# graph là object nx.MultiDiGraph
# graph.nodes["app/main.py::run"] → {"name": "run", "type": "FUNCTION", ...}
# graph.edges["app/main.py::run", "ingestion/file_scanner.py::scan_py_files"]
#   → {"type": "CALLS", ...}
```

#### **Thêm: Vẽ bản đồ kiến trúc:**

```python
visualize_architecture(graph, output_path="db/full_architecture_map.png")
```

**Tác dụng:**
- Vẽ toàn bộ cấu trúc code thành file PNG
- **Node colors:**
  - 🔵 Xanh dương: File
  - 🟢 Xanh lá: Class
  - 🔴 Đỏ: Function
  - 🟡 Vàng: Variable
  - ⚫ Xám: Dependency
- **Layout:** Spring layout để node "nổi" ra không chồng nhau
- Mỗi node có nhãn tên, mỗi cạnh có mũi tên hướng

**Output:** `db/full_architecture_map.png` (file hình 24×16 inch @ 200 DPI)

---

### **[5️⃣ BƯỚC 5] `query/` — Truy vấn đồ thị**

**File chính:** [query/graph_query.py](query/graph_query.py)

**Các hàm chính:**

#### **1. Lấy thông tin node:**
```python
get_node_context(graph, node_id: str) -> dict
```
**Trả về:** Tất cả metadata của node (id, name, type, file_path, docstring, source_code)

#### **2. Hàm được gọi bởi hàm nào:**
```python
get_function_calls(graph, node_id: str) -> list[str]
```
**Trả về:** Danh sách các hàm mà node `node_id` **gọi trực tiếp**

**Ví dụ:**
```python
# Hàm run() gọi hàm nào?
get_function_calls(graph, "app/main.py::run")
# → ["ingestion/file_scanner.py::scan_py_files", 
#    "graph/builder.py::build_graph", ...]
```

#### **3. Xây dựng cây gọi (Call Chain):**
```python
get_call_chain(graph, start_node_id: str, depth: int = 2) -> dict
```

**Tác dụng:**
- Xây dựng cây gọi **đệ quy** từ `start_node_id`
- Độ sâu tối đa: `depth`
- **Tự động phát hiện chu trình** (cycle): nếu hàm A → B → A, sẽ đánh dấu `[cycle]` và dừng

**Ví dụ:**
```python
chain = get_call_chain(graph, "app/main.py::run", depth=2)
# Kết quả (dict lồng nhau):
# {
#   "app/main.py::run": {
#       "ingestion/file_scanner.py::scan_py_files": {},
#       "graph/builder.py::build_graph": {},
#       "graph/builder.py::visualize_architecture": {
#           "query/graph_query.py::get_call_chain": {}
#       },
#       # ...
#   }
# }
```

#### **4. Định dạng cây gọi:**
```python
format_call_chain(chain: dict) -> str
```

**Tác dụng:**
- Chuyển dict lồng nhau thành **sơ đồ cây text** dễ đọc
- Dùng ký tự `├─`, `└─`, `│`, để vẽ nhánh

**Ví dụ output:**
```
run (app/main.py)
├── scan_py_files (ingestion/file_scanner.py)
├── build_graph (graph/builder.py)
│   └── (sau đó là các hàm con)
├── visualize_architecture (graph/builder.py)
│   ├── get_call_chain (query/graph_query.py)
│   └── _collect_nodes (graph/builder.py)
│       └── _collect_nodes (graph/builder.py)  [cycle]
└── (các hàm khác)
```

#### **5. Tìm kiếm semantic hybrid (Vector + BM25):**
```python
search_jit_context(graph, vstore, ai_query: str, top_k: int = 2) -> List[dict]
```

**Tác dụng:**
- Tìm kiếm **hybrid**: kết hợp **vector embedding** (semantic) + **BM25** (keyword)
- Dùng RRF (Reciprocal Rank Fusion) để kết hợp 2 kết quả
- Trả về `top_k` node phù hợp nhất

**Ví dụ:**
```python
ai_query = "extract nodes and edges from abstract syntax tree"
results = search_jit_context(graph, vstore, ai_query, top_k=2)
# Kết quả: [
#   {"id": "extraction/extractor.py::extract_from_file", "name": "extract_from_file", ...},
#   {"id": "extraction/models.py", "name": "models", ...}
# ]
```

---

### **[6️⃣ BƯỚC 6] `explain/` — Định dạng Output**

**File chính:** [explain/formatter.py](explain/formatter.py)

**Hàm chính:**
```python
explain_function(graph, node_id: str) -> str
```

**Tác dụng:**
- Kết hợp `get_call_chain()` + `format_call_chain()` để tạo output cuối cùng
- Trả về một **string** với sơ đồ cây dễ đọc

**Ví dụ:**
```python
explain = explain_function(graph, "app/main.py::run")
print(explain)
# Output:
# run (app/main.py)
# ├── scan_py_files (file_scanner.py)
# ├── build_graph (builder.py)
# ├── visualize_architecture (builder.py)
# │   ├── get_call_chain (graph_query.py)
# │   └── _collect_nodes (builder.py)
# ├── extract_from_file (extractor.py)
# ├── explain_function (formatter.py)
# │   ├── get_call_chain (graph_query.py)
# │   └── format_call_chain (graph_query.py)
# └── parse_file (parser.py)
```

---

### **[7️⃣ BƯỚC 7] `indexing/` — Vector Store (Lập chỉ mục)**

**File chính:** [indexing/vector_store.py](indexing/vector_store.py)

**Lớp chính:**
```python
VectorStore()
```

**Tác dụng:**
- Lưu trữ **embedding vector** của các node để tìm kiếm semantic
- Tích hợp **ChromaDB** để lưu vector
- Hỗ trợ **BM25** cho tìm kiếm keyword-based
- Dùng cho `search_jit_context()` (tìm kiếm hybrid)

**Phương thức chính:**
```python
vstore = VectorStore()
vstore.add_nodes(all_nodes)              # Thêm node vào vector store
results = vstore.search(query, top_k=2)  # Tìm kiếm top-k
```

---

## 🚀 CÁCH SỬ DỤNG TỪNG BƯỚC

### **Bước 1: Chuẩn bị môi trường**

```bash
# 1. Clone hoặc đi vào thư mục project
cd d:\Code\DALN\Caeser

# 2. Tạo virtual environment (nếu chưa có)
python -m venv venv
venv\Scripts\activate

# 3. Cài đặt dependencies
pip install -r requirements.txt
```

**File `requirements.txt`:**
```
pytest==8.1.1
pytest-cov==5.0.0
networkx==3.2.1
matplotlib
embedi…(cho vector embedding)
chromadb (cho vector store)
```

---

### **Bước 2: Hiểu Input & Output**

| Bước | Input | Hàm | Output |
|------|-------|-----|--------|
| Ingestion | Đường dẫn thư mục | `scan_py_files(.)` | `list[str]` file paths |
| Parsing | File path | `parse_file()` | `ast.AST` |
| Extraction | `ast.AST` + file path | `extract_from_file()` | `(nodes, edges)` |
| Graph | `nodes, edges` | `build_graph()` | `nx.MultiDiGraph` |
| Query | `graph` + node id | `get_call_chain()` | `dict` (cây lồng) |
| Explain | `chain` dict | `format_call_chain()` | `str` (sơ đồ cây) |
| Visualize | `graph` | `visualize_architecture()` | `PNG` file |

---

### **Bước 3: Chạy Pipeline từ `main.py`**

```python
# File: app/main.py

from app.main import run

# Chạy toàn bộ pipeline
run(".")  # Quét từ thư mục hiện tại
```

**Chi tiết hàm `run()`:**
```python
def run(repo_path: str):
    """Pipeline hoàn chỉnh: Scan -> Extract -> Graph -> Index -> Save DB -> Query."""
    
    # 1. Quét file
    print(f"[*] Đang quét thư mục: {os.path.abspath(repo_path)}")
    files = scan_py_files(repo_path)
    
    if not files:
        print("[-] Không tìm thấy file Python nào.")
        return
    
    # 2. Trích xuất node + edge từ tất cả file
    all_nodes = []
    all_edges = []
    print(f"[*] Đang phân tích AST và trích xuất từ {len(files)} file...")
    for f in files:
        nodes, edges = extract_from_file(f)
        all_nodes.extend(nodes)
        all_edges.extend(edges)
    
    # 3. Xây dựng đồ thị
    print(f"[*] Đang dựng Knowledge Graph với {len(all_nodes)} Nodes...")
    graph = build_graph(all_nodes, all_edges)
    
    # 4. Lưu vào vector store (ChromaDB)
    vstore = VectorStore()
    vstore.add_nodes(all_nodes)
    
    # 5. Vẽ bản đồ kiến trúc
    output_img = "db/full_architecture_map.png"
    print(f"[*] Đang vẽ bản đồ kiến trúc...")
    visualize_architecture(graph, output_path=output_img)
    
    # 6. Tìm kiếm semantic query (demo)
    ai_query = "extract nodes and edges from abstract syntax tree"
    print(f"[*] Truy vấn: {ai_query}")
    top_contexts = search_jit_context(graph, vstore, ai_query, top_k=2)
    
    # 7. In kết quả
    for ctx in top_contexts:
        print(f"\n[+] Kết quả: {ctx['name']}")
        print(f"    File: {ctx['file_path']}")
        print(f"    Docstring: {ctx['docstring']}")
        
        # Vẽ cây gọi
        chain = get_call_chain(graph, ctx['id'], depth=1)
        print("Cấu trúc liên kết:")
        print(format_call_chain(chain))
```

---

## 💻 VÍ DỤ THỰC TẾ

### **Ví dụ 1: Quét dự án hiện tại**

```python
from ingestion.file_scanner import scan_py_files

files = scan_py_files(".")
print(f"Tìm thấy {len(files)} file Python")
for f in files[:5]:  # In 5 file đầu
    print(f"  - {f}")
```

**Output:**
```
Tìm thấy 42 file Python
  - app/main.py
  - ingestion/file_scanner.py
  - parsing/parser.py
  - extraction/models.py
  - extraction/extractor.py
```

---

### **Ví dụ 2: Phân tích 1 file**

```python
from parsing.parser import parse_file
from extraction.extractor import extract_from_file
import ast

# Parse 1 file
tree = parse_file("app/main.py")
print(f"Cây AST: {type(tree)}")  # <class 'ast.Module'>

# Trích xuất node + edge
nodes, edges = extract_from_file("app/main.py")
print(f"Tìm thấy {len(nodes)} node, {len(edges)} edge")

# In chi tiết
for node in nodes[:3]:
    print(f"  Node: {node.id} ({node.type.value}) - {node.file_path}")
```

**Output:**
```
Cây AST: <class 'ast.Module'>
Tìm thấy 5 node, 8 edge
  Node: app/main.py (File) - app/main.py
  Node: app/main.py::run (Function) - app/main.py
  Node: app/main.py::__main__ (Function) - app/main.py
```

---

### **Ví dụ 3: Xây dựng đồ thị và truy vấn**

```python
from ingestion.file_scanner import scan_py_files
from extraction.extractor import extract_from_file
from graph.builder import build_graph
from query.graph_query import get_call_chain, format_call_chain

# 1. Scan + Extract
all_nodes, all_edges = [], []
for f in scan_py_files("."):
    nodes, edges = extract_from_file(f)
    all_nodes.extend(nodes)
    all_edges.extend(edges)

# 2. Build graph
graph = build_graph(all_nodes, all_edges)
print(f"Đồ thị có {len(graph.nodes)} node, {len(graph.edges)} edge")

# 3. Truy vấn: hàm run() gọi hàm nào?
chain = get_call_chain(graph, "app/main.py::run", depth=2)
tree = format_call_chain(chain)
print(tree)
```

**Output:**
```
Đồ thị có 187 node, 342 edge

run (app/main.py)
├── scan_py_files (file_scanner.py)
├── build_graph (builder.py)
├── visualize_architecture (builder.py)
├── extract_from_file (extractor.py)
├── search_jit_context (graph_query.py)
│   ├── VectorStore.search()
│   └── get_call_chain (graph_query.py)
└── (các hàm khác)
```

---

### **Ví dụ 4: Tìm kiếm semantic**

```python
from query.graph_query import search_jit_context
from indexing.vector_store import VectorStore

# Build vector store
vstore = VectorStore()
vstore.add_nodes(all_nodes)

# Tìm kiếm
query = "how to extract functions from code"
results = search_jit_context(graph, vstore, query, top_k=3)

for i, res in enumerate(results, 1):
    print(f"{i}. {res['name']} ({res['type']})")
    print(f"   Điểm: {res['score']:.2f}")
    print(f"   File: {res['file_path']}")
    print()
```

**Output:**
```
1. extract_from_file (Function)
   Điểm: 0.92
   File: extraction/extractor.py

2. GraphNode (Class)
   Điểm: 0.87
   File: extraction/models.py

3. parser (Module)
   Điểm: 0.76
   File: parsing/parser.py
```

---

## 📦 DEPENDENCY & YÊU CẦU

### **Python version:**
- Python 3.9+ (dùng features như `list[str]` type hints)

### **Dependencies (trong `requirements.txt`):**

```
# Core
pytest==8.1.1              # Unit testing framework
pytest-cov==5.0.0         # Code coverage tool

# Graph & Visualization
networkx==3.2.1           # Thư viện đồ thị
matplotlib                # Vẽ visualization

# Vector embedding & Search
openai                    # Cho embedding model (hoặc thay bằng local model)
chromadb                  # Vector database
rank-bm25                 # Keyword-based ranking

# Utilities
pydantic                  # Data validation
typing-extensions         # Nâng cao typing (Python 3.9)
```

---

## 🔗 CÁCH CHẠY LẦN ĐẦU (Quick Start)

```bash
# 1. Tạo virtual env
python -m venv venv
venv\Scripts\activate

# 2. Cài dependencies
pip install -r requirements.txt

# 3. Chạy pipeline
python app/main.py

# 4. Xem kết quả
# - Bản đồ: db/full_architecture_map.png
# - Output: Console
```

---

## 🧪 CHẠY TEST

```bash
# Chạy tất cả test
pytest tests/

# Chạy 1 test file
pytest tests/unit/test_builder.py

# Chạy với coverage
pytest --cov=. tests/

# Chạy test từ một hàm cụ thể
pytest tests/unit/test_builder.py::test_build_graph_returns_digraph -v
```

---

## 📊 TRẠNG THÁI HIỆN TẠI

| Thành phần | Trạng thái | Ghi chú |
|-----------|----------|--------|
| ✅ Ingestion | Hoàn thành | Quét file hoạt động tốt |
| ✅ Parsing | Hoàn thành | AST parse OK |
| ✅ Extraction | 80% | Chưa xử lý method calls, imports |
| ✅ Graph | Hoàn thành | MultiDiGraph OK, vẽ PNG OK |
| ✅ Query | Hoàn thành | Cycle detection, call chain OK |
| ✅ Explain | Hoàn thành | Format sơ đồ cây OK |
| 🔄 Indexing | Đang làm | Vector store + BM25 OK |
| ❌ Agents | Chưa làm | Phase 2+ |
| ❌ Rules/Hooks | Chưa làm | Phase 2+ |
| ❌ Memory | Chưa làm | Phase 2+ |

---

## 🎯 CÁC TỪ KHÓA QUAN TRỌNG

| Từ khóa | Ý nghĩa |
|---------|---------|
| **AST** | Abstract Syntax Tree — cây cú pháp trừu tượng |
| **GraphNode** | Node trong đồ thị (đại diện hàm, class, biến, v.v.) |
| **GraphEdge** | Cạnh (liên kết giữa 2 node) |
| **Call Chain** | Chuỗi gọi hàm (hàm A gọi B gọi C gọi...) |
| **Cycle** | Vòng lặp (A → B → A) |
| **Semantic Search** | Tìm kiếm theo ý nghĩa (không chỉ từ khóa) |
| **BM25** | Thuật toán xếp hạng keyword-based |
| **Vector Embedding** | Chuyển text thành số vector để tính similarity |
| **RRF** | Reciprocal Rank Fusion — kết hợp 2 kết quả tìm kiếm |

---

## 💡 BÀI HỌC THIẾT KẾ

### **Tại sao lại sử dụng AST thay vì regex?**
- AST: Hiểu được cấu trúc code → chính xác
- Regex: Chỉ match text → dễ sai

### **Tại sao lại dùng NetworkX?**
- Hỗ trợ đồ thị đa nhãn (MultiDiGraph)
- Có sẵn thuật toán graph (BFS, DFS, v.v.)
- Tích hợp tốt với matplotlib để vẽ

### **Tại sao lại detect cycle?**
- Tránh infinite loop khi vẽ sơ đồ cây
- Dễ nhìn thấy code có đệ quy hay vòng lặp phức tạp

---

## 🚀 BƯỚC TIẾP THEO (Phase 2+)

- [ ] Hỗ trợ method calls: `obj.method()`
- [ ] Hỗ trợ module imports: `os.path.join()`
- [ ] Tích hợp LLM để summarize function tự động
- [ ] Xây dựng agent AI làm việc với dự án
- [ ] Hỗ trợ các ngôn ngữ khác (không chỉ Python)

---

**Hy vọng tài liệu này giúp bạn hiểu rõ dự án! 🎉**
