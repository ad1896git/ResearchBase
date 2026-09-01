# Commands and results

## Initial gate

- starting HEAD: `c4b324ab5d29a71fce999c2a801e62c8a124a77d`
- tracked working tree: clean
- pre-existing unrelated untracked files: preserved
- non-evidence tracked modifications: none

## Evidence correction

The three minimum PR-14R3 evidence corrections were committed as
`94536ebbbaa6719de7d38238ee12f4192c09d526`. The R3 reviewed/final current
HEAD now resolves explicitly to `c4b324ab5d29a71fce999c2a801e62c8a124a77d`.

## Preserved substantive results

- downstream SQL SELECTs: 5 / 6 / 6 / 6; stage-bounded PASS
- TargetResolver SELECTs: 4 / 11 / 11; per-target N+1 NONE
- AuditFinding concurrency: real overlap PASS; loser
  `CONCURRENT_MODIFICATION`; final `dismissed`, row version 2
- FK/RESTRICT: 8/8 PASS; fresh-read preservation PASS
- formatting: exactly eight inherited failures; severity P3

## Final verification

Final verification resolves the live branch ref after the package commit and
runs HEAD/status inspection, source/test/migration diff, `git diff --check`,
PostgreSQL-backed `alembic current`, active null/token searches, SHA
resolution, and direct Git changed-file set equality. Exact results are
reported in the required PR-14R4 status output.
