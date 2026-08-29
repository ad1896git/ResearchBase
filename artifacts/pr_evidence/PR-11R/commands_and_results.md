# Commands and results

All commands ran from `/Users/onephone/Documents/Codex/ResearchBase` against
the real local PostgreSQL service at `localhost:5432/researchbase`, except the
named disposable migration database.

## Baseline and remediation commits

```text
reviewed PR-11 baseline: 9592b66dc3372fae18fdd66555203f0788e407e2
PR-11R implementation/test commits: 6319fda, 1330419, 4aa969e
```

The baseline was preserved as an ancestor. The working tree retained the
pre-existing untracked `.DS_Store` and execution-pack files.

## TDD and focused verification

```text
pre-fix PR-11R regression run: 3 failed as expected
  - repository parent-only commit was not rejected;
  - raw SQL parent-only commit was not rejected;
  - duplicate repository edge raised raw IntegrityError.

PR-11R focused application/schema/domain tests: 47 passed
```

## Required fresh gates

```text
uv sync --locked: Resolved 38 packages; Checked 34 packages
uv run pytest: 408 passed in 12.04s
uv run ruff check .: All checks passed!
uv run pyright: 0 errors, 0 warnings, 0 informations
uv run pytest tests/test_architecture.py tests/architecture: 34 passed
PR-11R-owned ruff format --check: 7 files already formatted
```

Repository-wide `ruff format --check .` reported only the eight inherited
pre-PR-11 files listed in `unresolved_findings.md`; no PR-11R-owned file was
listed.

## PostgreSQL and migration gates

```text
PR-11 application integration: 27 passed
PR-11 schema integration: 5 passed
PostgreSQL health smoke: 1 passed
PostgreSQL: 18.6, database=researchbase, schema=public
alembic current: 0012_statistical_result_input_guard (head)
clean disposable base -> head: PASS
disposable 0012 -> 0011 -> 0012: PASS
zero-input guard tests on clean disposable head: 2 passed
```

The migration trigger metadata query returned `tgdeferrable=true` and
`tginitdeferred=true`. `git diff --check` passed for the remediation range.
