# Pipeline: Codebase → Obsidian

## Tổng quan thay đổi

Phiên này xây dựng pipeline hoàn chỉnh từ Python source code đến Obsidian vault.
Neo4j bị skip — sẽ làm sau khi cần CLI query. Obsidian chỉ cần JSON, không cần Neo4j.

```
source code
    ↓  extraction/extractor.py   (per-file AST parsing)
    ↓  extraction/resolver.py    (cross-file reference resolution)
    ↓  extraction/merger.py      (orchestrator → graph.json)
    ↓  export/obsidian.py        (graph.json → .md files)
Obsidian vault
```

**Lệnh chạy:**
```bash
python cli.py extract --input . --output data/graph.json
python cli.py export  --graph data/graph.json --out data/obsidian
```

---

## Các file thay đổi

### 1. `extraction/models.py` — Schema mới hoàn toàn

**Trước:** `Function` + `FileModule` — chỉ có hàm và file, không có class, không có edge type.

**Sau:** Schema đầy đủ với 3 node type và 5 edge type.

| Node Type | Ý nghĩa |
|-----------|---------|
| `Module`  | Mỗi file `.py` (trừ `__init__.py`) |
| `Class`   | Khai báo class |
| `Function`| Hàm top-level hoặc method |

| Edge Type  | Chiều           | Ý nghĩa |
|------------|-----------------|---------|
| `IMPORTS`  | Module → Module | File này import file kia |
| `DEFINES`  | Module → Class/Function | File khai báo class/hàm top-level |
| `CONTAINS` | Class → Function | Class chứa method |
| `CALLS`    | Function → Function | Hàm gọi hàm (best-effort) |
| `INHERITS` | Class → Class   | Kế thừa |

**Trường `confidence` trên `GraphEdge`:**
- `1.0` = chắc chắn (DEFINES, CONTAINS, resolved IMPORTS)
- `0.7` = cao (CALLS — chỉ 1 hàm có tên đó trong project)
- `0.5` = trung bình (CALLS — nhiều hàm cùng tên, chọn theo heuristic)
- `0.0` = unresolved (external lib, builtin, hoặc ambiguous) → bị lọc ra ở export/query

---

### 2. `extraction/extractor.py` — Rewrite AST visitor

**Thay đổi chính:**

- **Return type mới:** `extract(tree, file_path) → (List[GraphNode], List[GraphEdge])` thay vì `FileModule`
- **Module node:** Tạo 1 node `Module` cho mỗi file
- **Ghost IDs:** Thay vì bỏ qua import/call chưa resolve, extractor tạo placeholder:
  - `dep:module.name` → sẽ được resolver map về `module:path`
  - `class_ref:ClassName` → sẽ được resolver map về `class:path::Name`
  - `func_ref:func_name` → sẽ được resolver map về `func:path::Name`
- **Method vs. top-level function:** Dùng `_current_class_id` context để tạo đúng ID và đúng edge type (`CONTAINS` vs `DEFINES`)
- **Nested function bị bỏ qua:** `_handle_function` không gọi `generic_visit` → hàm lồng nhau không được thu thập (quá chi tiết, gây noise)
- **Normalize path:** `Path(file_path).as_posix()` để node ID nhất quán trên Windows

**ID scheme:**
```
module:C:/project/extraction/extractor.py
class:C:/project/extraction/extractor.py::_Extractor
func:C:/project/extraction/extractor.py::_Extractor::visit_ClassDef
func:C:/project/extraction/extractor.py::extract          ← top-level
```

---

### 3. `extraction/resolver.py` — File mới

**Vai trò:** Nhận edges với ghost IDs từ extractor, trả về edges với node IDs thật.

**Cơ chế:**

**Import resolution** (`dep:` → `module:`):
- Build map: `"extraction.extractor"` → `"module:C:/...extractor.py"`
- Chuyển file path → dotted name: `extraction/extractor.py` → `extraction.extractor`
- Nếu không tìm thấy (thư viện ngoài như `os`, `ast`, `typing`) → confidence=0.0

**INHERITS resolution** (`class_ref:` → `class:`):
- Dùng phần cuối của tên: `"ast.NodeVisitor"` → tìm class tên `"NodeVisitor"`
- Nếu tìm thấy trong project → confidence=1.0, nếu không → drop (external)

**CALLS resolution** (`func_ref:` → `func:`):
- Dùng phần cuối: `"self.generic_visit"` → tìm func tên `"generic_visit"`
- 1 ứng viên → confidence=0.7
- Nhiều ứng viên → ưu tiên cùng file với caller → confidence=0.5
- Không tìm thấy → confidence=0.0 (builtin, thư viện ngoài)

---

### 4. `extraction/merger.py` — File mới

**Vai trò:** Orchestrator — kết nối toàn bộ pipeline và ghi JSON ra disk.

**Tại sao skip `__init__.py`:**
`__init__.py` thường re-export từ các module con. Nếu xử lý như module thường sẽ tạo Module node trùng lặp và IMPORTS edges lộn xộn. Re-export flattening được để dành cho phase sau.

**Output JSON:**
```json
{
  "project": "PA",
  "extracted_at": "2026-05-04T...",
  "file_count": 14,
  "nodes": [{ "id": "module:...", "name": "extractor", "type": "Module", ... }],
  "edges": [{ "type": "IMPORTS", "source_id": "...", "target_id": "...", "confidence": 1.0 }]
}
```

---

### 5. `export/obsidian.py` — File mới

**Vai trò:** Đọc JSON graph → tạo 1 file `.md` cho mỗi node trong vault.

**Cấu trúc vault:**
```
data/obsidian/PA/
├── modules/      ← extractor.md, merger.md, builder.md, ...
├── classes/      ← _Extractor.md, ImportResolver.md, GraphNode.md, ...
└── functions/    ← extract.md, resolve.md, build_graph.md, ...
```

**Template mỗi loại:**

*Module:*
```markdown
# extractor
**Type:** Module
**File:** `extraction/extractor.py`

## Classes
- [[_Extractor]]

## Functions
- [[extract]]

## Imported by
- [[graph_viewer]]
- [[main]]
```

*Class:*
```markdown
# _Extractor
**Type:** Class
**Line:** 14

## Methods
- [[visit_ClassDef]]
- [[_handle_function]]

## Defined in
- [[extractor]]
```

*Function:*
```markdown
# extract
**Type:** Function
**Line:** 10

## Module
- [[extractor]]

## Calls
- [[_Extractor]]

## Called by
- [[merge_project]]
```

**Tại sao wikilink dùng `name` không phải `id`:**
Obsidian match `[[extractor]]` theo tên file `extractor.md`. Nếu dùng full ID như `module:C:/...` thì wikilink sẽ không match.

**Tại sao filter `confidence > 0.0`:**
Edge confidence=0.0 nghĩa là target là external lib hoặc không resolve được. Giữ lại sẽ tạo ra wikilink gãy (broken link) trong Obsidian.

---

### 6. `graph/builder.py` — Cập nhật signature

**Trước:** `build_graph(modules: List[FileModule]) → DiGraph`

**Sau:** `build_graph(nodes: List[GraphNode], edges: List[GraphEdge]) → MultiDiGraph`

Trả về `MultiDiGraph` trực tiếp (thay vì DiGraph rồi convert trong viewer), và include đầy đủ node attributes (type, file_path, content) mà viewer cần.

---

### 7. `app/main.py` + `app/graph_viewer.py` — Cập nhật để dùng schema mới

Cả hai file thay đổi từ:
```python
modules = [extract(tree, f) for f in files]   # FileModule
build_graph(modules)
```
sang:
```python
all_nodes, all_edges = [], []
for f in files:
    nodes, edges = extract(tree, f)
    all_nodes.extend(nodes); all_edges.extend(edges)
resolver = ImportResolver(root, all_nodes)
resolved = resolver.resolve(all_edges)
build_graph(all_nodes, resolved)
```

Graph viewer giờ hiển thị đúng node type (Module/Class/Function) với màu khác nhau và edges có đúng relationship type.

---

### 8. `cli.py` — Entry point mới ở root

```bash
python cli.py extract --input <project_dir> --output <graph.json>
python cli.py export  --graph <graph.json>  --out <vault_dir>
```

---

## Kết quả chạy trên chính project này (self-test)

```
[*] Extracting 14 files...
[*] Resolving cross-file references...
[+] Written to data/graph.json
    Nodes: 93 | Edges: 572 (194 resolved)

[+] Obsidian vault -> data\obsidian\PA
    Files: 93
```

194/572 edges resolved = IMPORTS + CALLS nội bộ. 378 edges còn lại là external libs (ast, os, typing, networkx...) → confidence=0.0 → không xuất hiện trong vault.

---

## Những gì chưa làm (để sau)

- `__init__.py` re-export flattening (resolver chưa xử lý)
- Incremental extraction (skip file không thay đổi)
- Neo4j loader + CLI query (Phase sau)
- CALLS edges accuracy còn thấp (heuristic theo tên hàm, chưa theo import scope)
