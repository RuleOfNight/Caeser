---
name: Phase 1 Current State
description: Where we are in Phase 1 — what files exist, what's built, what's still missing
type: project
---

**Phase:** Phase 1 — Code Graph Extraction Core (IN PROGRESS)

**Branch:** `khoa`

**Goal:** Extract Python codebase → JSON graph → Neo4j → Obsidian export → CLI query

## What exists (files on disk)

### Extraction layer (partial)
- `extraction/models.py` — GraphNode, GraphEdge, NodeType, EdgeType (needs cleanup: remove Variable, Dependency)
- `extraction/extractor.py` — AST visitor, per-file extraction (needs patches per PHASE1_PLAN)
- `extraction/__init__.py`

### Graph layer (partial)
- `graph/builder.py` — exists but purpose unclear vs. planned `graph/loader.py` (JSON → Neo4j)
- `graph/__init__.py`

### Query layer (partial)
- `query/graph_query.py` — exists
- `query/__init__.py`

### App layer (exists, diverges from plan)
- `app/main.py` — modified
- `app/graph_viewer.py` — modified; viewer opens in a separate CMD window (not Neo4j Browser)

### Tests
- `tests/unit/test_file_scanner.py`

## What's MISSING (per PHASE1_PLAN checklist)
- `cli/query.py` (or query subcommand in `cli.py`) — graph-first conversational Q&A (NOT YET BUILT)

## What WAS missing but is now BUILT (updated 2026-05-05)
- `extraction/resolver.py` — ✅ built (ImportResolver, ghost ID resolution)
- `extraction/merger.py` — ✅ built (merge_project, JSON output)
- `graph/loader.py` — ✅ built (JSON → Neo4j via MERGE, idempotent)
- `export/obsidian.py` — ✅ built (graph → Obsidian vault with wikilinks)
- `cli.py` extract + export commands — ✅ built; `--load-neo4j` flag added

## Deleted files (staged deletions)
- ChromaDB files, vector_store.py, old agents/, old indexing/ — removed (old approach)
- Old markdown docs (CHEATSHEET.md, HUONG_DAN_CHI_TIET.md, etc.) — cleaned up

## Architecture decisions (frozen)
- AST-based extraction (Python `ast` module), no tree-sitter
- Neo4j for graph storage (MERGE not CREATE, idempotent)
- JSON as intermediate format (persisted before Neo4j load)
- Obsidian for visualization (wikilinks), no custom web UI
- Graph-first query: Neo4j traversal → LLM context

## graph_viewer.py note
The current viewer opens in a separate CMD window. Neo4j Browser (localhost:7474) is the intended long-term graph UI.

**Why:** Neo4j is for persistent storage and Cypher queries; the viewer is a debug tool.
**How to apply:** Don't conflate the CMD viewer with Neo4j. Neo4j is used once loader.py is built.
