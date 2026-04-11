# Hooks

Hooks are shell commands that execute automatically in response to events.
They are registered in `config/settings.json`.

## Available Hook Events
- `PreToolCall` — runs before a tool is called
- `PostToolCall` — runs after a tool completes
- `Stop` — runs when Claude finishes a response

## Hook File Convention
Each hook is a shell script in this folder:
- `pre-edit.sh` — validate before file edits
- `post-commit.sh` — run after git commits
- `on-stop.sh` — cleanup or logging after each turn

## Registration
Add hooks to `config/settings.json` under the `hooks` key.
