# Core Rules

Rules that apply to all agents and interactions in this project.

## Behavioral Rules
- Always respond in the same language the user writes in
- Be concise — no filler text, no trailing summaries
- Do not take destructive actions without explicit confirmation
- Never expose secrets, API keys, or sensitive data in output
- Prefer editing existing files over creating new ones

## Task Rules
- Break complex tasks into steps before executing
- Verify assumptions before acting on them
- Mark tasks complete only when actually done

## Memory Rules
- Save non-obvious facts learned during conversations
- Do not save things already in code or git history
- Update stale memories rather than duplicating them
