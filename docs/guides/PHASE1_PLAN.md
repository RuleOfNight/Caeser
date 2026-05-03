# PHASE 1 PLAN — Code Graph Extraction Core

## Goal

Build a working pipeline that:
1. Takes a Python project folder as input
2. Parses it with Python `ast` module
3. Resolves cross-file references
4. Outputs a unified JSON graph
5. Loads the graph into Neo4j
6. Exports to Obsidian-compatible markdown
7. Provides a basic conversational CLI to query

**Validate on: the project itself (self-referential test)**

---

## Checklist

```
[ ] models.py          — finalize schema (clean up Variable, Dependency)
[ ] extractor.py       — patch AST visitor per decisions below
[ ] resolver.py        — cross-file reference resolution
[ ] merger.py          — merge per-file graphs + write JSON
[ ] graph/loader.py    — JSON → Neo4j
[ ] export/obsidian.py — graph → Obsidian markdown vault
[ ] cli/extract.py     — extract command with progress indicator
[ ] cli/export.py      — export command
[ ] cli/query.py       — basic conversational query (graph-first)
[ ] Validation         — manual spot-check on self project
```

---

## Patch List for extractor.py

These must be fixed before resolver/merger are built:

1. **Remove `visit_Assign`** — Variable nodes are out of scope
2. **Remove `NodeType.VARIABLE` and `NodeType.DEPENDENCY`** — clean up models
3. **Fix `func_id` uniqueness** — method IDs must include class name:
   ```python
   # Inside a class:
   func_id = f"func:{file_path}::{current_class_name}::{node.name}"
   # Top-level:
   func_id = f"func:{file_path}::{node.name}"
   ```
4. **Keep ghost IDs** (`dep:`, `func_ref:`, `class_ref:`) — resolver will handle them
5. **Add `is_async` and `decorators` to Function node properties**

---

## resolver.py — Design

### Role
Receives the merged raw graph (with ghost IDs), returns a resolved graph.

### Three Resolution Types

#### 1. Import Resolution (`dep:` → `module:`)
- Build module map: `"extraction.extractor"` → `"module:extraction/extractor.py"`
- Algorithm: walk all `.py` files, convert path to dotted name, build lookup dict
- Handle `__init__.py` re-exports: scan and build re-export map first
- If module not found in project → **external library → drop edge**
- Confidence: `1.0`

#### 2. INHERITS Resolution (`class_ref:` → `class:`)
- Build class map: `"BaseService"` → list of matching class node IDs
- If 1 match → resolve, confidence `1.0`
- If multiple matches → prefer same package, confidence `0.8`
- If no match → external base class → drop edge
- Confidence: `0.8–1.0`

#### 3. CALLS Resolution (`func_ref:` → `func:`)
- Build func map: `"get_user"` → list of matching function node IDs
- If 1 match → resolve, confidence `0.7`
- If multiple matches → prefer functions in imported modules of caller's file, confidence `0.5`
- If no match → drop edge (likely builtin or external)
- Confidence: `0.5–0.7`

### Unresolved Strategy
- Tag with `confidence: 0.0`, keep in graph
- Filter `confidence == 0.0` edges in queries and Obsidian export
- Useful for debugging extraction quality

### __init__.py Flattening
```python
# extraction/__init__.py
from .extractor import CodeKnowledgeExtractor

# Result: re_export_map["extraction.CodeKnowledgeExtractor"] = "extraction.extractor"
# When resolving: "from extraction import CodeKnowledgeExtractor"
# → maps to module:extraction/extractor.py
```

### Interface
```python
class ImportResolver:
    def __init__(self, project_root: str, all_nodes: List[GraphNode]):
        self.module_map    = self._build_module_map(project_root)
        self.re_export_map = self._build_reexport_map(project_root)
        self.class_map     = self._build_class_map(all_nodes)
        self.func_map      = self._build_func_map(all_nodes)

    def resolve(self, edges: List[GraphEdge]) -> List[GraphEdge]:
        # Returns resolved edges, unresolved tagged confidence=0.0
        ...
```

---

## merger.py — Design

### Role
- Collect per-file (nodes, edges) from extractor
- Deduplicate nodes by ID
- Run resolver on merged edge list
- Write final JSON to disk

### Scaling Requirements
- **File-level parallelism**: parse each file independently (ThreadPoolExecutor)
- **Incremental extraction**: track file hash in a manifest, skip unchanged files
- **Progress indicator**: show `[X/N files]` progress during extraction

### Output Format
```json
{
  "project": "Caeser",
  "project_root": "/path/to/project",
  "extracted_at": "2026-05-02T10:00:00",
  "file_count": 12,
  "nodes": [
    {
      "id": "module:extraction/extractor",
      "name": "extractor",
      "type": "Module",
      "file_path": "extraction/extractor.py",
      "line_start": 1,
      "docstring": null
    }
  ],
  "edges": [
    {
      "type": "IMPORTS",
      "source_id": "module:extraction/extractor",
      "target_id": "module:extraction/models",
      "confidence": 1.0
    }
  ]
}
```

### Manifest Format (for incremental)
```json
{
  "extraction/extractor.py": {
    "hash": "abc123",
    "last_extracted": "2026-05-02T10:00:00"
  }
}
```

---

## graph/loader.py — Design

### Role
Load JSON graph into Neo4j, avoid duplicates on re-run.

### Key Decisions
- Use `MERGE` not `CREATE` in Cypher → idempotent, safe to re-run
- Load nodes first, then edges
- Index on `id` property for performance on large projects

### Basic Cypher Patterns
```cypher
// Node
MERGE (n:Module {id: $id})
SET n.name = $name, n.file_path = $file_path, n.docstring = $docstring

// Edge (only confidence > 0.0)
MATCH (a {id: $source_id}), (b {id: $target_id})
MERGE (a)-[r:IMPORTS]->(b)
SET r.confidence = $confidence
```

---

## export/obsidian.py — Design

### Role
Convert graph nodes to Obsidian markdown files with wikilinks.

### Output Structure
```
obsidian-vault/
└── project_name/
    ├── modules/
    │   └── extractor.md
    ├── classes/
    │   └── CodeKnowledgeExtractor.md
    └── functions/
        └── extract_from_file.md
```

### Markdown Template — Class
```markdown
# CodeKnowledgeExtractor
**Type:** Class
**File:** `extraction/extractor.py`
**Line:** 12

## Docstring
Extracts Nodes and Edges from AST.

## Methods
- [[CodeKnowledgeExtractor.__init__]]
- [[CodeKnowledgeExtractor.visit_ClassDef]]

## Inherits
- [[ast.NodeVisitor]]

## Defined in
- [[extractor]]

## Used by (imported from this module)
- [[main]]
- [[graph_viewer]]
```

### Rules
- Wikilinks use node `name`, not `id` — Obsidian matches by filename
- Only include edges with `confidence > 0.0`
- Each node = one `.md` file, filename = node name (sanitized)
- Overwrite on re-export (idempotent)

---

## CLI Commands

```bash
# Step 1: Extract codebase → JSON
python -m src.cli.extract --input codebases/my_project/ --output graph.json

# Step 2: Load into Neo4j
python -m src.cli.extract --input codebases/my_project/ --output graph.json --load-neo4j

# Step 3: Export to Obsidian
python -m src.cli.export --graph graph.json --out ~/obsidian-vault/my_project/

# Step 4: Query (conversational)
python -m src.cli.query --graph graph.json
```

### Query CLI Behavior
- Conversational with session memory (remembers previous Q in same session)
- Graph-first: traverse Neo4j → build context → send to LLM
- Show which nodes were used to build context (transparency)

Example session:
```
> what methods does CodeKnowledgeExtractor have?
[graph] Found class: CodeKnowledgeExtractor (extraction/extractor.py)
[graph] Methods: visit_Import, visit_ClassDef, visit_FunctionDef, ...
[llm]  CodeKnowledgeExtractor có 6 methods chính...

> which of those call other functions?
[graph] Checking CALLS edges from those methods...
[llm]  visit_FunctionDef gọi ast.get_docstring và ast.get_source_segment...
```

---

## Validation Checklist (end of Phase 1)

- [ ] Run extractor on self project (Caeser repo) — no crashes
- [ ] JSON graph contains expected modules, classes, functions
- [ ] IMPORTS edges resolve correctly (no ghost `dep:` nodes remaining)
- [ ] Obsidian vault opens correctly, graph view shows connected nodes
- [ ] Navigate from a module node to its classes and methods in Obsidian
- [ ] CLI query: "what methods does class X have?" returns correct answer
- [ ] CLI query: "which modules import Y?" returns correct answer
- [ ] Incremental re-run skips unchanged files

---

## What NOT to build in Phase 1

- Paper extraction pipeline
- Advanced normalization / entity resolution
- Cross-document linking
- Research gap analysis
- Web UI
- Complex graph algorithms (clustering, centrality)
