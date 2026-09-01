# Commands and results

## Initial gate

- starting HEAD: `724c67d4411fac7904470301cef80af18f1507a0`
- tracked working tree: clean
- pre-existing unrelated untracked files: preserved
- non-evidence tracked modifications: none

## Immutable identity correction

The three minimum active PR-14R4 evidence files were corrected in payload
commit `c75db39a3f712b39b7e8ce47eea3eb920bb30b86`. The authoritative PR-14R4
reviewed/final/current identity now directly records
`724c67d4411fac7904470301cef80af18f1507a0`.

## Preserved substantive results

- downstream SQL SELECTs: 5 / 6 / 6 / 6; stage-bounded PASS
- TargetResolver SELECTs: 4 / 11 / 11; per-target N+1 NONE
- AuditFinding concurrency: real overlap PASS; loser
  `CONCURRENT_MODIFICATION`; final `dismissed`, row version 2
- FK/RESTRICT: 8/8 PASS; fresh-read preservation PASS
- formatting: exactly eight inherited failures; severity P3

## Verification commands

- `git rev-parse HEAD`
- `git status --short`
- `git diff -- src tests migrations`
- `git diff --check`
- `UV_CACHE_DIR=/tmp/researchbase-uv-cache uv run alembic current`
- active authoritative identity scan over PR-14R4 and PR-14R5 evidence
- `git rev-parse` and `git cat-file -t` for every recorded SHA
- direct Git range changed-file set comparison

Alembic returned `0015_governance_audit (head)`. Final Git range, identity,
diff, and working-tree results are reported from fresh post-commit checks in
the required PR-14R5 status output.

