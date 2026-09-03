# Formatting Reconciliation

Fresh command:

```text
uv run ruff format --check .
```

Result: exit 1; `8 files would be reformatted, 150 files already formatted`.

Exact failing set, in command output order:

1. `migrations/versions/0004_experiment_spec.py`
2. `tests/integration/test_pr04_application.py`
3. `tests/integration/test_pr04_schema.py`
4. `tests/integration/test_pr05_application.py`
5. `tests/integration/test_pr05_schema.py`
6. `tests/integration/test_pr06_application.py`
7. `tests/integration/test_pr06_schema.py`
8. `tests/unit/domain/test_pr05_experiment.py`

All eight files predate PR-16 ownership and remain unchanged. The explicit PR-16-owned formatting check
passed: 22 files already formatted, with zero PR-16-owned failures.

The reviewed active PR-16 file `artifacts/pr_evidence/PR-16/unresolved_findings.md` contained a stale
seven-file inventory at baseline; PR-16R adds `tests/integration/test_pr06_schema.py` so it now contains this
exact eight-file inventory. No other PR-16 evidence file contains a stale seven-file inventory.
