# Commands and Results

Environment: PostgreSQL 18.6; Python project environment with `UV_CACHE_DIR=/tmp/researchbase-uv-cache`.

Subject chronology:

```text
starting HEAD = 03ccba54b8c983815f74d08a2390e0dfa45f8551
PR17R_SUBJECT = 2d8e2abe31d0410717412c182d3cf7bd0811cced
evidence protocol = non-self-referential-v1
```

Exact baseline command and result are in `baseline_regression_report.md`: 156 collected, 154 passed, 2 skipped,
0 failed in 19.35s.

Verification results:

```text
DATABASE_URL=... UV_CACHE_DIR=... uv run pytest -o addopts='' -rA
642 passed, 2 skipped in 56.56s

DATABASE_URL=... UV_CACHE_DIR=... uv run pytest -o addopts='' -q tests/e2e tests/architecture
66 passed in 29.14s

uv run ruff check .
All checks passed

uv run pyright
0 errors, 0 warnings, 0 informations

owned PR-17R format check
6 files already formatted

uv run alembic current
0015_governance_audit (head)

uv run ruff format --check .
8 inherited historical files would be reformatted; 158 files already formatted

git diff --check
pass
```

The clean-install schema replay and removal are recorded in `clean_install_report.md`. The subject range contains
the six source/test paths listed in `changed_files.txt`; the post-subject range is evidence/process-only. The
actual final evidence HEAD is intentionally not included in the fingerprint payload because the protocol does not
require an evidence commit to contain its own SHA.
