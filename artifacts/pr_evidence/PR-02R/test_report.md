# PR-02R Test Report

## Finding-specific verification

- PR02-IRR-002: PASS. The `[actor]` Workspace FK test first commits a valid Actor and Project,
  then inserts a Workspace with a valid `project_id` and nonexistent `created_by`; PostgreSQL
  rejects the specific `workspaces_created_by_fkey`.
- PR02-IRR-003: PASS. Explicit rollback now writes Actor and Project, rolls back explicitly, and
  checks both are absent from a new UoW/Session.
- PR02-IRR-004: PASS. Four adversarial fixtures cover literal `importlib.import_module` targets
  `researchbase.persistence` and `sqlalchemy`, plus literal `__import__` targets `fastapi` and
  `typer`; existing absolute/relative and recursive checks remain green.

## Fresh gate results

```text
Full pytest: 96 passed in 0.31s
PostgreSQL integration: 16 passed, 80 deselected in 0.27s
Architecture tests: 26 passed in 0.02s
Ruff: All checks passed!
Pyright: 0 errors, 0 warnings, 0 informations
```

Prior PR-00, PR-01, and PR-01R tests remain included in the full suite.
