# PA — Project Assistant

## Overview
This is the central workspace for the PA (Personal Assistant) AI project.
All rules, skills, hooks, agents, and documentation live here.

## Folder Structure
```
PA/
├── rules/          # Behavioral rules and constraints for agents
├── skills/         # Reusable skill definitions (slash commands)
├── hooks/          # Event-driven automation hooks
├── agents/         # Agent definitions and configurations
├── prompts/
│   ├── system/     # System prompts for each agent/role
│   └── templates/  # Reusable prompt templates
├── memory/         # Persistent memory files (user, feedback, project, reference)
├── docs/
│   ├── architecture/  # System design, ADRs
│   ├── guides/        # How-to guides and SOPs
│   └── api/           # API references
├── evals/          # Evaluation harnesses and test cases
├── config/         # Environment and model configuration
├── scripts/        # Utility and automation scripts
└── tests/          # Unit/integration tests for agent behavior
```

## Key Conventions
- All rules go in `rules/` as `.md` files
- Skills follow the format in `skills/TEMPLATE.md`
- Hooks are configured in `hooks/` and registered in `config/settings.json`
- Memory files use frontmatter (type: user | feedback | project | reference)

## Phase
Currently: **Phase 1 — Foundation**
