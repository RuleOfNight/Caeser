# Evals

Evaluation harnesses for testing agent behavior, output quality, and safety.

## Structure
```
evals/
├── cases/        # Individual test cases (input + expected output)
├── rubrics/      # Scoring criteria per task type
└── results/      # Logged eval runs (gitignored if large)
```

## Running Evals
```bash
# placeholder — add actual run command when eval harness is set up
bash scripts/run-evals.sh
```

## Eval Case Format
```json
{
  "id": "eval-001",
  "input": "user message here",
  "expected": "expected behavior or output pattern",
  "rubric": "rubrics/accuracy.md",
  "tags": ["reasoning", "safety"]
}
```
