# System Prompts

One file per agent role. These are the foundational instructions loaded at the
start of every session for that agent.

## Convention
- `orchestrator.md` — master coordinator prompt
- `researcher.md` — research and synthesis
- `coder.md` — code generation, review, debugging

## Format
Each system prompt should include:
1. Role definition
2. Capabilities and limitations
3. Output format expectations
4. Escalation conditions
