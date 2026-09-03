# Formatting Report

- `ruff check .`: PASS.
- `pyright`: PASS, 0 errors, 0 warnings, 0 informations.
- Owned `ruff format --check tests/e2e tests/conftest.py`: PASS; 8 files already formatted.
- `git diff --check`: PASS before evidence metadata.
- Repository-wide `ruff format --check .`: the exact same eight inherited historical P3 files are reported and
  remain unchanged:

  - `migrations/versions/0004_experiment_spec.py`
  - `tests/integration/test_pr04_application.py`
  - `tests/integration/test_pr04_schema.py`
  - `tests/integration/test_pr05_application.py`
  - `tests/integration/test_pr05_schema.py`
  - `tests/integration/test_pr06_application.py`
  - `tests/integration/test_pr06_schema.py`
  - `tests/unit/domain/test_pr05_experiment.py`
