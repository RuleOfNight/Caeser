# Personal AI Assistant — Master Plan

## 1. Objective

Build a modular **Personal AI Assistant** capable of:

- Understanding and analyzing codebases
- Answering questions based on documents
- Analyzing research papers and extracting insights
- Supporting future multi-agent workflows

The system is designed to be **extensible, modular, and hybrid (local + API LLM)**.

---

## 2. Design Principles

- Modular architecture (each capability is isolated)
- Clear separation of responsibilities
- Start simple → iterate
- No over-engineering in early phases
- Prefer deterministic pipelines before LLM reasoning

---

## 3. High-Level Architecture


User Query
↓
[Routing Layer]
↓
[Execution Layer]
├── Code Intelligence (Graph-based)
├── Document QA (RAG)
└── Research Analysis (Graph-based)
↓
[LLM / Response Generation]


---

## 4. System Components

### 4.1 Code Intelligence System
- Parses codebase
- Builds structural graph
- Supports dependency and flow analysis
- Provides explainable outputs

---

### 4.2 Document QA System (RAG)
- Processes documents
- Uses embeddings + vector search
- Retrieves relevant context
- Generates grounded answers

---

### 4.3 Research Analysis System
- Converts papers into structured graph
- Extracts:
  - problem
  - method
  - limitations
- Enables comparison and gap detection

---

### 4.4 Routing Layer (Future)
- Classifies user queries
- Routes to appropriate system component

---

### 4.5 Orchestration Layer (Future)
- Coordinates multi-step workflows
- Enables multi-agent execution

---

## 5. Development Phases

### Phase 1 — Code Intelligence (Graph-based)
- Parse code (AST)
- Extract structure (functions, calls)
- Build graph representation
- Implement query + explanation

---

### Phase 2 — Document QA (RAG)
- Chunk documents
- Generate embeddings
- Store in vector database
- Implement retrieval + answer generation

---

### Phase 3 — Routing Layer
- Classify query types
- Route to correct module

---

### Phase 4 — Orchestration (Multi-step workflows)
- Define execution flows
- Integrate multiple modules

---

### Phase 5 — Research Analysis
- Build graph from papers
- Extract structured knowledge
- Compare and identify gaps

---

### Phase 6 — Hybrid LLM Integration
- Combine local LLM and API
- Optimize cost and performance

---

## 6. Scope Control

### Important Rules

- Each phase must be implemented **independently**
- Do NOT anticipate future phases during implementation
- Do NOT introduce unnecessary dependencies
- Keep implementations minimal and testable

---

## 7. Current Focus

The current implementation target is:

> **Phase 1 — Code Intelligence System**

All other phases are **out of scope for now**.

---

## 8. Non-Goals (for now)

- No multi-agent system
- No LangGraph / CrewAI
- No LLM-based reasoning in Phase 1
- No distributed system design

---

## 9. Future Direction

This system will evolve into:

- A hybrid AI assistant
- Supporting:
  - code understanding
  - knowledge retrieval
  - research assistance
- With controlled multi-agent orchestration

---

## 10. Final Note

This project prioritizes:

- clarity over complexity
- working system over perfect system

Build step-by-step. Validate each phase before moving forward.