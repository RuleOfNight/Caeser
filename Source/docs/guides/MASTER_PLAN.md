# MASTER PLAN — Personal Knowledge Graph Assistant

## 1. Objective

Build a personal assistant that can:
- Extract structured knowledge from **codebases** and **research papers**
- Represent knowledge as a **graph**
- Enable querying, explanation, and analysis via **LLM with graph-first context**

The system focuses on **structured understanding**, not raw LLM reasoning.

---

## 2. Core Principle

Three layers:

1. **Extraction Layer** — parse input into raw graph
2. **Knowledge Layer** — graph storage, normalization, query
3. **Reasoning Layer** — LLM with structured context from graph

---

## 3. Architecture Overview

```
Input (code / paper)
        ↓
Extraction Layer
  - Code: tree-sitter / Python AST
  - Paper: Graphify-style LLM extraction
        ↓
Raw Graph (per document) → JSON (persisted to disk)
        ↓
Resolver (cross-file reference resolution)
        ↓
Merger (project-level unified graph)
        ↓
Neo4j (graph storage)
        ↓
Export Layer
  - Obsidian vault (visualization + browse)
        ↓
Query Layer (graph-first → LLM reasoning)
  - CLI (conversational)
```

---

## 4. Design Decisions

### 4.1 Two Independent Graph Systems
- **Code graph** and **paper graph** are fully independent
- Separate extraction pipelines, separate Neo4j schemas
- No cross-linking between code and paper nodes
- Shared infrastructure: same Neo4j instance, same query layer pattern

### 4.2 Code Extraction — AST-based
- Use Python's built-in `ast` module (sufficient for Python-only)
- Migrate to `tree-sitter` only if multi-language support needed later
- Coarse-grained schema: Module, Class, Function only
- No Variable nodes, no Statement nodes

### 4.3 Paper Extraction — Graphify-style LLM
- Use LLM to extract nodes (concepts) and edges (relations)
- Probabilistic by nature → confidence scores required
- Deferred to Phase 2 (paper pipeline)

### 4.4 No Multi-Agent System
- No CrewAI, no LangGraph, no agent orchestration
- Single linear pipeline
- Routing via simple conditional logic only

### 4.5 Confidence-aware Graph
- Every edge must carry a `confidence` score (0.0 to 1.0)
- AST-derived edges: `confidence = 1.0`
- Resolved references: `confidence = 0.7–0.9` depending on ambiguity
- Unresolved references: `confidence = 0.0` (kept for debug, filtered in queries)

### 4.6 JSON as Intermediate Format
- Raw graph persisted to disk as JSON before Neo4j load
- Enables: debug without re-running, incremental updates, resume on failure

### 4.7 UI Strategy
- **Obsidian** for graph visualization and browsing (wikilinks auto-generate graph)
- **CLI (conversational)** for LLM-powered Q&A
- No custom web UI

### 4.8 Query Strategy — Graph-first
- Query traverses Neo4j first → builds structured context
- Context passed to LLM for reasoning
- LLM never queries graph directly

---

## 5. Graph Schema — Code

### Node Types
| Type     | Description                        |
|----------|------------------------------------|
| Module   | Each `.py` file (not `__init__.py`)|
| Class    | Class definition                   |
| Function | Top-level function or class method |

### Node Properties
```json
{
  "id": "module:src.utils",
  "name": "utils",
  "type": "Module | Class | Function",
  "file_path": "src/utils.py",
  "line_start": 1,
  "docstring": "optional string"
}
```

### Edge Types
| Type     | Source → Target              | Notes                        |
|----------|------------------------------|------------------------------|
| IMPORTS  | Module → Module              | Internal only, no 3rd party  |
| DEFINES  | Module → Class/Function      |                              |
| CONTAINS | Class → Function             | Methods only                 |
| CALLS    | Function → Function          | Best-effort, may be partial  |
| INHERITS | Class → Class                |                              |

### Edge Properties
```json
{
  "type": "IMPORTS",
  "source_id": "module:src.main",
  "target_id": "module:src.utils",
  "confidence": 1.0
}
```

---

## 6. Extraction Rules

- **Skip `__init__.py` as nodes** — but flatten their re-exports before skipping
- **Skip external/third-party imports** — only track internal project modules
- **Skip nested functions** — top-level and class methods only
- **Skip Variable nodes** — too fine-grained, noisy for Q&A
- **Async functions** treated same as regular functions
- **Decorated functions** — capture decorator name in node properties

---

## 7. Phases

### Phase 1 — Code Graph Extraction Core ← CURRENT
Goal: Extract graph from Python codebase → JSON → Neo4j → Obsidian export → basic CLI query
Details: See `PHASE1_PLAN.md`

### Phase 2 — Paper Graph Extraction
Goal: Extract graph from research papers using Graphify-style LLM extraction
Output: Same JSON format as code graph, loaded into separate Neo4j labels

### Phase 3 — Normalization Layer
Goal: Entity resolution within each graph
- Merge duplicate concept nodes
- Canonical naming
- Embedding similarity + LLM-as-judge hybrid approach

### Phase 4 — Reasoning Layer
Goal: Conversational CLI with graph-first context building
- Explain a function/concept
- Compare two nodes
- Summarize a module/paper

### Phase 5 — Multi-Document Knowledge Network (Paper)
- **5a**: Multi-paper graph with factual + relational linking (`extends`, `contradicts`, `builds_on`)
- **5b**: Concept-centric wiki generation (Karpathy-style, cross-paper)
- **5c**: Research gap inference — only after 5b is stable

---

## 8. Non-Goals

- No multi-agent orchestration
- No complex web UI (Obsidian + CLI is sufficient)
- No perfect static analysis (graph is approximation, use confidence scores)
- No cross-linking between code graph and paper graph
- No large-scale distributed system

---

## 9. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Noisy extraction (CALLS edges) | Confidence scores, filter `confidence < 0.5` in queries |
| Graph fragmentation across files | Resolver + normalization layer |
| LLM hallucination in reasoning | Graph-first context, reference node IDs in prompt |
| `__init__.py` re-export confusion | Flatten re-exports in resolver before skipping file |
| Duplicate nodes same name | Canonical ID scheme: `type:filepath::name` |

---

## 10. Project Structure

```
project/
├── src/
│   ├── extraction/
│   │   ├── extractor.py      # AST visitor, per-file graph extraction
│   │   ├── resolver.py       # Cross-file reference resolution
│   │   ├── merger.py         # Merge per-file graphs → project graph
│   │   └── models.py         # GraphNode, GraphEdge, NodeType, EdgeType
│   ├── graph/
│   │   ├── loader.py         # JSON → Neo4j
│   │   └── queries.py        # Cypher query helpers
│   ├── export/
│   │   └── obsidian.py       # Graph → Obsidian markdown vault
│   ├── reasoning/
│   │   ├── context_builder.py  # Graph traversal → structured context
│   │   └── llm.py              # LLM call with context
│   └── cli/
│       ├── extract.py        # CLI: extract command
│       ├── export.py         # CLI: export command
│       └── query.py          # CLI: conversational query command
├── codebases/                # Input: Python projects to analyze
├── papers/                   # Input: PDFs/papers (Phase 2)
└── docs/
    ├── MASTER_PLAN.md
    └── PHASE1_PLAN.md
```

---

## 11. Success Criteria

### Minimum Viable (Phase 1)
- Extract graph from a Python project
- Store in Neo4j
- Browse structure in Obsidian
- Answer: "what methods does class X have?", "which modules import Y?"

### Intermediate (Phase 2–3)
- Handle research papers
- Merge overlapping concepts within same domain

### Advanced (Phase 4–5)
- Conversational CLI with memory
- Cross-paper concept linking
- Research gap hints
