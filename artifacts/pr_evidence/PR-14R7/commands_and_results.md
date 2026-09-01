# Commands and results

## Initial gate

- `git rev-parse HEAD` returned
  `b1a1f16e9972618b8115488baceb293279f901f7`.
- tracked working tree was clean; pre-existing unrelated untracked files were
  preserved.
- evidence parent was known before evidence commit as
  `b1a1f16e9972618b8115488baceb293279f901f7`.

## Immutable R5 range

`git diff --name-status 724c67d4411fac7904470301cef80af18f1507a0..b1a1f16e9972618b8115488baceb293279f901f7`
returned the exact 11-file evidence-only set recorded in the corrected R5
`changed_files.txt`.

## Required verification

The pre-commit verification includes:

- exact parsed JSON assertions for protocol, subject, parent, scope, and the
  false self-SHA-in-payload flag;
- forbidden authoritative self-field inspection;
- resolution as commit objects of every SHA stored in the R7 payload;
- `git diff -- src tests migrations`;
- `git diff --check`;
- `UV_CACHE_DIR=/tmp/researchbase-uv-cache uv run alembic current`;
- staged path classification and exact file-set equality.

Results:

- exact parsed JSON assertions: PASS;
- forbidden authoritative self fields: none;
- source/test/migration diff: empty;
- `git diff --check`: PASS;
- Alembic: `0015_governance_audit (head)`;
- production/test/migration/architecture/business/PR-15 files: zero.

The post-commit verification checks the immutable range from the evidence
parent, tracked working-tree cleanliness, and the same repository invariants.
The containing R7 evidence commit SHA is intentionally absent from the tracked
payload and is resolved directly from Git by the independent reviewer.
