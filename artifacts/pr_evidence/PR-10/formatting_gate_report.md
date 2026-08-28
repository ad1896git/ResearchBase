# Formatting gate report

All PR-10-owned and PR-10-touched files pass:

    uv run ruff format --check <PR-10-owned files>
    14 files already formatted

Repository-wide uv run ruff format --check . remains FAIL because of eight
pre-existing files outside PR-10:

    migrations/versions/0004_experiment_spec.py
    tests/integration/test_pr04_application.py
    tests/integration/test_pr04_schema.py
    tests/integration/test_pr05_application.py
    tests/integration/test_pr05_schema.py
    tests/integration/test_pr06_application.py
    tests/integration/test_pr06_schema.py
    tests/unit/domain/test_pr05_experiment.py

No inherited formatting debt was modified. uv run ruff check . passes.
