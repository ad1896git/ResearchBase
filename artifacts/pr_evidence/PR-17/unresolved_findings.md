# Unresolved Findings

P0: none.

P1: none.

P2: none.

P3: repository-wide Ruff formatting reports the same eight pre-existing historical files outside PR-17 ownership.
They were not modified:

- `migrations/versions/0004_experiment_spec.py`
- `tests/integration/test_pr04_application.py`
- `tests/integration/test_pr04_schema.py`
- `tests/integration/test_pr05_application.py`
- `tests/integration/test_pr05_schema.py`
- `tests/integration/test_pr06_application.py`
- `tests/integration/test_pr06_schema.py`
- `tests/unit/domain/test_pr05_experiment.py`

## PR-17R disposition

The later PR-17 Phase 1 Final Independent Reality Review rejected the prior gate on exactly six findings:
`PR17-RR-P1-001`, `PR17-RR-P1-002`, `PR17-RR-P2-001`, `PR17-RR-P2-002`, `PR17-RR-P2-003`, and
`PR17-RR-P2-004`. PR-17R closes all six with the evidence package in
`artifacts/pr_evidence/PR-17R/`. The eight formatting files above remain the only P3 debt.

PR-17R final disposition: P0 = 0, P1 = 0, P2 = 0, P3 = 8 inherited formatting files.
