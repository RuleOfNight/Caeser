# Getting Started

## Prerequisites
- Claude Code CLI installed
- Access to this working directory

## Setup
1. Open this folder in Claude Code
2. CLAUDE.md is auto-loaded as project context
3. Rules in `rules/` define agent behavior
4. Skills in `skills/` are available as slash commands

## Key Files to Know
| File | Purpose |
|------|---------|
| `CLAUDE.md` | Project overview — auto-loaded |
| `rules/core.md` | Universal behavioral rules |
| `config/settings.json` | Hook registrations and model config |
| `memory/MEMORY.md` | Persistent memory index |
| `docs/architecture/overview.md` | System design |

## Adding a New Skill
1. Copy `skills/TEMPLATE.md` to `skills/your-skill.md`
2. Fill in the frontmatter and steps
3. Reload plugins: `/reload-plugins`

## Adding a Hook
1. Write the shell script in `hooks/`
2. Register it in `config/settings.json`
3. Reload to apply
