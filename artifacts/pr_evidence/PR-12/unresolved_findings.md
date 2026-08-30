# Unresolved findings

P0: none.

P1: none.

P2: none.

The independent PR-12 review recorded F-001 through F-005 as open at the original gate. PR-12R closes F-001 (dynamic-head migration isolation), F-002 (Git/database fingerprint reconciliation), F-003 (literal independent oracle), F-004 (complete multi-input closure proof), and F-005 (complete post-freeze SQL guard matrix).

P3: repository-wide formatting debt remains in eight inherited files: `migrations/versions/0004_experiment_spec.py`, `tests/integration/test_pr04_application.py`, `tests/integration/test_pr04_schema.py`, `tests/integration/test_pr05_application.py`, `tests/integration/test_pr05_schema.py`, `tests/integration/test_pr06_application.py`, `tests/integration/test_pr06_schema.py`, and `tests/unit/domain/test_pr05_experiment.py`. This is outside PR-12 scope; PR-12-owned formatting passed.
