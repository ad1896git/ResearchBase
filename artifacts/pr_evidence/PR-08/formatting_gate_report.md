# Formatting gate

PR-08-owned scoped format check: PASS (11 files). Repository-wide `ruff format --check .`: FAIL only for inherited files: `migrations/versions/0004_experiment_spec.py`, `tests/integration/test_pr04_application.py`, `tests/integration/test_pr04_schema.py`, `tests/integration/test_pr05_application.py`, `tests/integration/test_pr05_schema.py`, `tests/integration/test_pr06_application.py`, `tests/integration/test_pr06_schema.py`, and `tests/unit/domain/test_pr05_experiment.py`. No inherited files were mass-reformatted.
