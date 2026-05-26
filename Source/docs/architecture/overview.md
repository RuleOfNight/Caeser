# Architecture Overview

## Status
Phase 1 — Foundation (in progress)

## High-Level Design
```
User
 │
 ▼
Orchestrator Agent
 ├── Researcher Agent   (web search, synthesis)
 ├── Coder Agent        (code generation, review)
 └── Reviewer Agent     (quality, safety, hallucination check)
```

## Data Flow
1. User sends a request
2. Orchestrator decomposes it into subtasks
3. Subtasks are dispatched to specialist agents
4. Results are aggregated and reviewed
5. Final response returned to user

## Key Design Decisions
Document architectural decisions in `docs/architecture/adr/`.
