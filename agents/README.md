# Agents

Each file in this folder defines one agent — its role, system prompt reference,
tools it may use, and rules it must follow.

## Agent File Convention
```
agents/
├── orchestrator.md   # Top-level coordinator agent
├── researcher.md     # Web search and synthesis agent
├── coder.md          # Code generation and review agent
└── reviewer.md       # Quality and safety review agent
```

## Agent Definition Schema
```markdown
---
name: agent-name
role: one-line description
system_prompt: prompts/system/agent-name.md
tools: [Read, Write, Edit, Grep, Glob, WebSearch]
rules:
  - rules/core.md
  - rules/agent-behavior.md
---

## Responsibilities
...

## Escalation
When to hand off to another agent or the user.
```
