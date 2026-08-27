# Commands and results

All commands were run from the ResearchBase repository.

```text
DATABASE_URL=... uv run alembic upgrade head
PASS — main database upgraded to 0005_dataset_snapshot.

DATABASE_URL=... uv run pytest tests/integration/test_pr06_application.py tests/integration/test_pr06_schema.py
15 passed in 0.45s

DATABASE_URL=... uv run pytest
222 passed in 1.36s

uv run ruff check .
All checks passed!

uv run pyright
0 errors, 0 warnings, 0 informations

uv run pytest tests/architecture tests/test_architecture.py tests/unit/domain/test_pr06_dataset.py
41 passed in 0.15s

DATABASE_URL=... uv run alembic current
0005_dataset_snapshot (head)

git diff --check
PASS — no whitespace errors.
```

The migration report records the separate disposable-database upgrade/downgrade/upgrade roundtrip.

Git state for the evidence package:

```text
starting accepted PR-05 final baseline: 403a26c
PR-06 implementation/evidence commit: a5c53e2
```

The remaining untracked execution packs and `.DS_Store` files were pre-existing user-owned files and were not included in the PR-06 commit.

Evidence reconciliation: the original PR-06 command/test results remain historical and are not being relabeled as independent proof for PR06-REV-001 through PR06-REV-007. Fresh remediation commands and outcomes are recorded in `artifacts/pr_evidence/PR-06R/commands_and_results.md`.
