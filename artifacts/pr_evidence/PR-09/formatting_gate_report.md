# Formatting gate report

- PR-09-owned `ruff format --check`: PASS, 13 files.
- Repository-wide `ruff format --check .`: FAIL on 8 inherited baseline files: `migrations/versions/0004_experiment_spec.py`, PR-04/PR-05/PR-06 integration files, and `tests/unit/domain/test_pr05_experiment.py`.
- PR-09 did not mass-format inherited files. `ruff check .` remains PASS.

