# Formatting ownership report

`uv run ruff format --check .` reports 8 files that would be reformatted:

- `migrations/versions/0004_experiment_spec.py`
- `tests/integration/test_pr04_application.py`
- `tests/integration/test_pr04_schema.py`
- `tests/integration/test_pr05_application.py`
- `tests/integration/test_pr05_schema.py`
- `tests/integration/test_pr06_application.py`
- `tests/integration/test_pr06_schema.py`
- `tests/unit/domain/test_pr05_experiment.py`

These are inherited files outside the PR-09R3 diff. They were not mass-
formatted. All PR-09, PR-09R, PR-09R2, and PR-09R3-owned Python files pass
scoped `ruff format --check`. This remains an explicitly reported inherited P2
condition and is not a PR-09R3 implementation failure.
