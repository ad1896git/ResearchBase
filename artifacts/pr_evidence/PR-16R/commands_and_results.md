# Commands and Results

Baseline and scope:

- `git rev-parse HEAD`: `390cbda614215c439766ce805947d339772dc55a`.
- `git diff --name-status 390cbda614215c439766ce805947d339772dc55a..HEAD`: empty.
- `git diff -- src tests migrations`: empty.
- `git diff --check`: PASS.
- Baseline active PR-16 formatting inventory: 7 files; PR-16R correction: added
  `tests/integration/test_pr06_schema.py`.

Fresh verification:

- `uv run ruff format --check .`: exit 1; exactly 8 inherited files, 150 already formatted.
- PR-16-owned `uv run ruff format --check ...`: PASS; 22 files already formatted.
- `uv run ruff check .`: PASS; all checks passed.
- `uv run pyright`: PASS; 0 errors, 0 warnings, 0 informations.
- `alembic current` against PostgreSQL: `0015_governance_audit (head)`.

Post-commit range reconciliation is resolved directly from Git. The final range contains exactly the eight
files listed in `changed_files.txt`: the corrected active PR-16 finding inventory and the seven PR-16R
evidence files.
