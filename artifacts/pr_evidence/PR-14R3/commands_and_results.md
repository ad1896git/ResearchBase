# Commands and results

## Initial state

- `git rev-parse HEAD`: `3a9cb09ca0c7a84a43c6c12e752c5e41892c3449`
- tracked modifications: five evidence files only
- non-evidence tracked modifications: none

## Historical range regeneration

`git diff --name-status 16695506f285fe015eb15948bb5b07f95f5944aa..3a9cb09ca0c7a84a43c6c12e752c5e41892c3449`
returned exactly 13 added files, all under
`artifacts/pr_evidence/PR-14R2/`. The name-status and name-only inventories are
set-equal.

## Preserved substantive results

- downstream SQL SELECTs: small 5, medium 6, large 6, extra-path 6;
  stage-bounded PASS; per-entity/path SQL NONE OBSERVED
- TargetResolver SELECTs: 1 target 4, 8 targets 11, 32+ targets 11;
  per-target N+1 NONE; reversed insertion order produced identical content hash
- AuditFinding concurrency: independent PostgreSQL UoWs with real overlap;
  initial row version 1; one winner; loser `CONCURRENT_MODIFICATION`; final
  status `dismissed`; final row version 2; partial overwrite NONE
- FK/RESTRICT: 8/8 DELETE attacks rejected; fresh-read preservation PASS
- repository-wide formatting: eight inherited failures; owned failures 0;
  accepted P3 inherited debt

## Final verification contract

Final verification runs `git rev-parse HEAD`, `git status --short`,
`git diff -- src tests migrations`, `git diff --check`, PostgreSQL-backed
`alembic current`, an exact obsolete-token search, SHA resolution, and direct
Git set equality for `3a9cb09..current`. The Git-resolved current HEAD is
reported in the required final status rather than embedded in its own commit.
