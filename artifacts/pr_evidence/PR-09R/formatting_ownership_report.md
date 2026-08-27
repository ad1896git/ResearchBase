# Formatting ownership report

Git-derived PR-09 baseline ownership:

- command: `git diff --name-only 275de41..8e67b48 | rg '\\.py$'`
- count: 14 Python files.

PR-09R union ownership adds `migrations/versions/0009_run_input_seal_fix.py`, for 15 Python files total. Scoped `ruff format --check` passes all 15. Repository-wide formatting still reports 8 inherited baseline files; no inherited files were mass-formatted.
