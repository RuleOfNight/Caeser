# Trợ lý Đồ thị Tri thức Cá nhân

Hệ thống phân tích codebase Python và papers nghiên cứu, lưu trữ dưới dạng đồ thị, và hỗ trợ truy vấn qua LLM với ngữ cảnh ưu tiên từ đồ thị.

---

## Tính năng

**Phân tích codebase** — Trích xuất cấu trúc toàn bộ project Python thành đồ thị có cấu trúc: module, class, function và các quan hệ giữa chúng (import, kế thừa, gọi hàm). Đồ thị lưu dưới dạng JSON, có thể xuất ra Obsidian vault để duyệt trực quan hoặc truy vấn qua CLI.

**Hỏi đáp paper** — Đặt câu hỏi với một paper (định dạng Markdown). Câu trả lời kèm trích dẫn nguồn chính xác.

---

## Kiến trúc

```
Codebase Python
    ↓  extraction/extractor.py   — AST → nodes + ghost edges
    ↓  extraction/resolver.py    — giải quyết cross-file references
    ↓  extraction/merger.py      — gộp per-file graphs → graph.json
    ↓  export/obsidian.py        — graph.json → Obsidian vault
    ↓  query/engine.py           — graph-first context → LLM

Paper Markdown
    ↓  ask.py                    — parse sections → chat với trích dẫn
```

**Chiến lược truy vấn — Graph-first:** Thay vì đưa toàn bộ source code vào context, hệ thống dùng LLM để chọn các node liên quan từ danh mục đồ thị, rồi xây dựng context tối thiểu từ các node đó. Tiết kiệm token đáng kể so với full-code baseline.

---

## Cài đặt

```bash
pip install -r requirements.txt
```

Tạo file `.env` ở thư mục gốc:

```
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Sử dụng

### Phân tích codebase

```bash
# Trích xuất project → graph.json
python -m extraction.merger --input <thư_mục_project> --output data/graph.json

# Xuất ra Obsidian vault
python -m export.obsidian --graph data/graph.json --out data/obsidian
```

Output graph.json mẫu:

    {
      "project": "my_project",
      "extracted_at": "2026-05-28T...",
      "file_count": 14,
      "nodes": [{ "id": "module:src/utils.py", "name": "utils", "type": "Module" }],
      "edges": [{ "type": "IMPORTS", "source_id": "...", "target_id": "...", "confidence": 1.0 }]
    }

### Hỏi đáp codebase

```bash
python -m query.engine data/graph.json
```

Ví dụ phiên làm việc:

    > hàm merge_project làm gì?
    [graph] Matched: merge_project (Function) — merger.py:12
    [llm]  merge_project là entry point của pipeline trích xuất...

    > nó gọi những hàm nào?
    [graph] CALLS edges: extract, resolve, _node_dict, _edge_dict
    [llm]  merge_project gọi extract() cho từng file, sau đó chạy resolver...

### Hỏi đáp paper

Paper cần ở định dạng Markdown với YAML frontmatter và các `##` header cho từng section.

```bash
python ask.py <paper.md>
```

Ví dụ phiên làm việc:

    Paper: Attention Is All You Need  (Vaswani et al., 2017)
    Sections: intro, background, model_architecture, training, results

    You: multi-head attention hoạt động như thế nào?

    Assistant: Multi-head attention chia Q/K/V thành h heads độc lập,
    mỗi head học một dạng attention khác nhau, sau đó concat và project lại.

      Nguồn:
      [model_architecture] "Multi-head attention allows the model to jointly attend..."

---

## Schema đồ thị (Code)

| Node Type | Ý nghĩa |
|-----------|---------|
| Module    | Mỗi file `.py` |
| Class     | Khai báo class |
| Function  | Hàm top-level hoặc method |

| Edge Type | Chiều                    | Confidence |
|-----------|--------------------------|------------|
| IMPORTS   | Module → Module          | 1.0        |
| DEFINES   | Module → Class/Function  | 1.0        |
| CONTAINS  | Class → Function         | 1.0        |
| CALLS     | Function → Function      | 0.5 – 0.7  |
| INHERITS  | Class → Class            | 0.8 – 1.0  |

Các edge có `confidence = 0.0` (external lib, không resolve được) bị lọc ra ở export và query.

---

## Cấu trúc thư mục

```
Source/
├── extraction/      # AST parsing, cross-file resolver, merger
├── graph/           # Graph builder và networkx query helpers
├── export/          # Xuất Obsidian vault
├── query/           # Graph-first context builder + LLM reasoning
├── parsing/         # Xử lý đầu vào (paper, document)
├── explain/         # Tầng giải thích call chain
├── ingestion/       # File scanner và ingestion pipeline
├── data/            # graph.json + obsidian vault output
├── ask.py           # CLI hỏi đáp paper
├── rules/           # Quy tắc hành vi cho agent
├── skills/          # Định nghĩa skill (slash commands)
├── hooks/           # Hook tự động theo sự kiện
├── docs/guides/     # Tài liệu kiến trúc (MASTER_PLAN.md, OBSIDIAN_PIPELINE.md)
├── evals/           # Harness đánh giá chất lượng
├── config/          # Cấu hình settings và model
└── tests/           # Unit và integration tests
```
