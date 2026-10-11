# M3 Runner binding candidate evidence

Baseline: `4c0931510fe5be2981136e1277e4c7d88ba6cc05` in an isolated
`feature/m3-runner-bind` worktree. No scientific schema or migration file changed.

- Focused test command: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests/unit/test_m3_runner_binding.py tests/unit/test_hg1_runtime.py tests/unit/test_hg1_runner.py`. Result: 41 passed under host permission for Unix socket binding.
- Ruff check of the two production files and focused test: all checks passed.
- Pyright on the two production files using the existing Phase 1 virtual environment: zero errors, zero warnings.
- `tests/test_architecture.py`: 12 passed.
- `tests/architecture/test_import_boundaries.py`: one pre-existing stale migration-list assertion fails because it expects only migrations through 0026 while the accepted M3 baseline contains 0027–0031. No migrations were changed.
- Read-only host inspection: durable root, M3 installation, and M3 CAS are owned by `onephone` and mode `0700`; the HG1-00B HBA file contains the seven peer/reject rules. Actual root-controlled M3 policy file is absent.
- Retained M3 owner Runner smoke: NOT_RUN because the required host administrator policy is not installed. No B/C accounts, credentials, attestations or reviews were fabricated.

The M3 profile is exact and policy-required. Four existing M2 profile names and
policy-optional behavior remain accepted by focused tests. The Runner continues
to use the existing macOS `getpeereid` and HG1-02 coordinator/Application
authorization. No host policy, PostgreSQL, CAS, retained data or accepted
HG1-01/02 branch was modified.
