# Commands and results

All commands ran from `/Users/onephone/Documents/Codex/ResearchBase`.

## Required Git and scope checks

```text
git rev-parse HEAD
git status --short
git log --oneline --decorate -15
git diff --name-only e62d19f..716e316
git diff --name-status e62d19f..716e316
git diff --stat e62d19f..716e316
git diff --check e62d19f..716e316
git diff --check
git diff -- src tests migrations
```

The baseline inspection reported starting HEAD
`716e316d57d4dc40b4c13586f3dfafebdc17caba`. The target range contained 15
paths. The historical target-range whitespace check identified the nine
listed PR-11R3 Markdown EOF defects; after cleanup, the current working-tree
`git diff --check` passed. The source/test/migration diff is empty.

## Evidence checks

```text
git diff --name-only e62d19f..716e316 | sort
sort artifacts/pr_evidence/PR-11R3/changed_files.txt
git cat-file -e <each recorded full SHA>^{commit}
find artifacts/pr_evidence/PR-11R4 -maxdepth 1 -type f -print | sort
```

The final evidence checks report exact target-range set equality, all recorded
full SHAs Git-resolved, and all eight PR-11R4 files present. The final metadata
commit is intentionally not self-recorded inside its own content; its full
SHA is reported separately after commit creation.

Observed optional verification results:

```text
uv run pytest: 410 passed in 14.91s
uv run ruff check .: All checks passed!
uv run pyright: 0 errors, 0 warnings, 0 informations
uv run alembic current: 0013_statistical_result_legacy_input_precheck (head)
```

The first attempts to run the PostgreSQL-backed suite and unscoped `uv` tools
inside the sandbox were blocked by local network/cache permissions. The same
commands were then rerun with the required local verification permission and
produced the observations above.

## Repository state checks

```text
git diff -- src tests migrations
uv run alembic current
```

The expected Alembic head remains
`0013_statistical_result_legacy_input_precheck (head)`. No PR-12
implementation is present.
