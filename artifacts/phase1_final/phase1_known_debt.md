# Phase 1 known debt

P0 = 0; P1 = 0; P2 = 0. Accepted P3: one inherited Ruff-formatting debt category affecting exactly eight files. No fixes made.

- `migrations/versions/0004_experiment_spec.py`
- `tests/integration/test_pr04_application.py`
- `tests/integration/test_pr04_schema.py`
- `tests/integration/test_pr05_application.py`
- `tests/integration/test_pr05_schema.py`
- `tests/integration/test_pr06_application.py`
- `tests/integration/test_pr06_schema.py`
- `tests/unit/domain/test_pr05_experiment.py`

Fresh check: exit 1, eight files would be reformatted, 158 already formatted. This is the explicitly accepted exception, not a repository-wide format PASS.

The two opt-in legacy migration tests remain skipped in the default suite because PR11R2_MIGRATION_DB_URL is unset. This is a verification coverage limit, not a newly discovered code defect; historical migration evidence remains in PR-11R2/PR-11R3 and PR-17R.

Historical superseded fingerprints and original untracked local files are described in the commit inventory; neither is silently promoted into the accepted baseline.
