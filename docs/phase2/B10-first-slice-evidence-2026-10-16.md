# B10 first conclusion slice — implementation and evidence

> Historical lane evidence. Integrated head: `0056_b10_reconsideration`.
> Owner-authorized remediation on 2026-10-17 preserves B09 SQL, composes B10's
> existing Decision policies with B07/B11, and removes both workaround revisions.
> Current verification is in `docs/verification/batch-c/integration-evidence.md`.

Owner authority: the 2026-10-16 task approves the proposal's first slice and its
READ COMMITTED, first-inventory-SHARE write protocol. This supersedes the draft's
historical documentation-only/open-approval wording for that slice. The proposal
status has been updated exactly as requested.

Implemented: both reconsideration grounds through the existing Decision
Application boundary; closed commands and immutable readback; literal R2 hashes;
all project/purpose rejections; fresh independent review and completed revision or
explicit review correction; exact old/fresh material verification; unique linked
successor; creation/decision fence rechecks; immutable/deferred normal-role SQL
enforcement; bounded typed cycle traversal and predecessor verification. No grant
or scientific history is reactivated or rewritten by reconsideration.

One migration, `0056_b10_reconsideration`, follows the observed head
`0055_b09_approval_tuples`. Existing migration source is unchanged. Populated
reconsideration downgrade refuses; empty downgrade restores prior checks/guards.
Head expectations and inventories receive values/appended entries only.

The participating ordinary PROCEED writer now uses first-inventory-SHARE ordering
and lock-free historical replay. Review writers reserve their owning INSERT table
before target coordination to avoid inversion with the new inventory. New review
INSERTs receive server creation time after coordination, preventing a supplied
future timestamp from manufacturing freshness; prior rows and hashes are retained.

Existing equivalents/substitutions:

- `configure_approval_transaction(readonly=...)` supplies write/read configuration
  and the existing connection timeout profile before BEGIN. No parallel UoW mode
  or infrastructure was introduced.
- The literal N inventory lives in existing `B09_SNAPSHOT_TABLES` / `B09_SHARE_SQL`,
  expanded to the exact approved B04 union. The migration carries its literal
  inventory; an architecture test checks both equalities. B06's imported legacy
  inventory remains unchanged.
- Existing exact repository operations and same-UoW review/revision verifiers are
  reused. Concrete typed basis insert operations are declared in the shared port
  without creating a reverse Phase 1 dependency on the Decision domain.
- Fresh-review eligibility follows §3.1's strict post-every-rejection definition;
  specified old corrected reviews are included separately, as that paragraph
  requires. Saved timestamps derive this partition for exact replay. Human error
  and relevance assessments remain attributable narrative; UUID-only rationale
  and bare recommendation summaries cannot substitute for correction explanation.

No separate transport exposure was authorized. New reconsideration HTTP/CLI
adapters and their conditional tests are outside this slice. Manuscripts,
support-only change inference, mixed grounds, Issue disposition and external
execution remain unavailable under their separate contracts.

Verification uses the installed local environment with
`UV_CACHE_DIR=/tmp/rb-b10-uv`; `DATABASE_URL` and explicit `RB_TEST_ADMIN_URL` are
inherited from the task environment. PostgreSQL suites use their existing random,
disposable database fixtures. Observed server: PostgreSQL **18.6 (Homebrew)**,
aarch64-apple-darwin27.0.0, 64-bit.

Observed focused verification results follow. The final B10-only rerun follows
the last B10 authority/text checks; its cases overlap the combined PostgreSQL run
and must not be added to that run as distinct tests.

| Command | Observed result |
| --- | --- |
| `UV_CACHE_DIR=/tmp/rb-b10-uv uv run --no-sync ruff check .` | PASS: All checks passed! |
| `UV_CACHE_DIR=/tmp/rb-b10-uv uv run --no-sync ruff format --check .` | PASS: 579 files already formatted |
| `UV_CACHE_DIR=/tmp/rb-b10-uv uv run --no-sync pyright` | PASS: 0 errors, 0 warnings, 0 informations |
| `UV_CACHE_DIR=/tmp/rb-b10-uv uv run --no-sync pytest -o addopts='' tests/unit tests/architecture tests/test_architecture.py -q --tb=short` | 2,434 passed, 41 warnings in 51.01s |
| Focused PostgreSQL command below | 512 passed, 1 skipped, 1,440 warnings in 428.12s |
| `git diff --check` | PASS: exit 0, no diagnostics |

```sh
UV_CACHE_DIR=/tmp/rb-b10-uv uv run --no-sync pytest -o addopts='' \
  tests/integration/phase2/test_approval.py \
  tests/integration/phase2/test_pr2_15_decision.py \
  tests/integration/phase2/test_pr2_15_decision_schema.py \
  tests/integration/phase2/test_b06_revision_action.py \
  tests/integration/phase2/test_b06_revision_concurrency.py \
  tests/integration/phase2/test_b04_manuscript_freeze.py \
  tests/integration/phase2/test_b05_manuscript_review.py \
  tests/integration/phase2/test_b05_review_basis.py \
  tests/integration/phase2/test_b05_review_races.py \
  tests/integration/phase2/test_b09_approval_schema.py \
  tests/integration/phase2/test_b09_approval_concurrency.py \
  tests/integration/phase2/test_b10_reconsideration.py \
  tests/integration/phase2/test_b10_reconsideration_schema.py \
  tests/integration/phase2/test_b10_reconsideration_concurrency.py \
  tests/integration/phase2/test_b04_manuscript_migration.py \
  tests/integration/phase2/test_b05_review_migration.py \
  tests/integration/phase2/test_pr2_03_review_guards.py \
  tests/integration/phase2/test_pr2_04_migration_coverage.py \
  tests/integration/phase2/test_pr2_17_authorship_schema.py \
  tests/integration/phase2/test_revision_action.py \
  tests/integration/phase2/test_pr2_14_internal_review.py \
  -q -rs --tb=short
```

The one skip is the existing
`tests/integration/phase2/test_b05_manuscript_review.py::test_superseded_manuscript_review`:
“B04 only creates DRAFT/FROZEN; exact SUPERSEDED history awaits the later
supersession contract.” It is not a passing case. Warnings are the existing
Alembic `path_separator` deprecation; Pyright also printed its update-availability
notice, separate from its zero diagnostics.

Final B10 rerun: **57 passed, 174 warnings in 82.95s**:

```sh
UV_CACHE_DIR=/tmp/rb-b10-uv uv run --no-sync pytest -o addopts='' \
  tests/integration/phase2/test_b10_reconsideration.py \
  tests/integration/phase2/test_b10_reconsideration_schema.py \
  tests/integration/phase2/test_b10_reconsideration_concurrency.py \
  -q --tb=short
```

Lock evidence includes actual independent PostgreSQL backend blocking witnesses
through `pg_blocking_pids()`, matching/changed same-UUID races, competing
successors, and credential loss across inventory/scope/target waits. Statement
capture proves N SHARE precedes write queries/coordination, and read/replay
statements use READ ONLY REPEATABLE READ without explicit table/advisory/row locks.
Normal-role tests exercise deferred and forced completeness, hashes, ordinals,
immutability, sealed-parent append denial, prior evidence, forged predecessor
laundering, and server-owned review time. Isolated, rolled-back traversal graph
fault injection tests direct/transitive cycles and the 10,000/10,001 distinct-node
boundary; its synthetic edges are not retained as scientific acceptance history.

Read-only delegated reviews found no remaining concrete P0/P1 in the inspected
schema/successor/predecessor enforcement after remediation. This is first-slice
implementation evidence, not a full B10 or Phase-exit declaration. The reviewer
subsequently required the full check; its remediation evidence follows. No commit,
push or branch was created.


## Reviewer remediation

The owner's loop reported six failures; the earlier 512-pass focused result did
not include the three files below and did not establish a passing full check.
Reproduction before remediation: **6 failed, 12 passed, 47 warnings in 9.02s**.

Three migration assertions still expected `0055_b09_approval_tuples`; only their
expected values were changed to `0056_b10_reconsideration`. The replay failures
were deterministic consequences of the participating PROCEED protocol change:
the fresh-read spy watched `DecisionRepository.reviews`, whereas the writer now
uses `ApprovalRepository.target_reviews`; the permanent-denial test counted one
UoW whereas the lock-free replay preflight followed by the writer creates two.
The spies now watch the actual review read, preserving the three distinct
write-transaction IDs, identical review-read transaction IDs, rollback and exact
recovery assertions for both SQLSTATEs. Permanent denial additionally asserts
exactly one literal N SHARE/write attempt, alongside the two UoWs and unchanged
persisted counts. No runtime behavior was changed for those six reported failures.

Exact requested rerun (with `UV_CACHE_DIR=/tmp/rb-b10-uv` exported):

```sh
uv run pytest -o addopts='' -q tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_19_replay.py
```

Result before the additional error fixes: **18 passed, 48 warnings in 9.42s**,
exit 0. Exact rerun after those fixes: **18 passed, 48 warnings in 11.88s**,
exit 0.

Head-sensitive PostgreSQL coverage includes these previously omitted suites:

- `tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py`
- `tests/integration/phase2/test_pr2_04_execution_migration.py`

Together with the earlier focused run, coverage also includes
`test_b04_manuscript_migration.py`, `test_b05_review_migration.py`,
`test_pr2_03_review_guards.py`, `test_pr2_04_migration_coverage.py`,
`test_pr2_15_decision_schema.py`, `test_pr2_17_authorship_schema.py`, and
`test_revision_action.py`. Head-sensitive unit and architecture tests are covered
by the unit/architecture command and the full check. All these suites must be
included when validating a changed head; the full check below includes them.

The reviewer requested re-review because the previous diff was truncated. Review
entry points are `src/researchbase/application/decision.py` (closed commands,
reconsideration admission, lock-free read/replay), `application/approval.py`
(successor gate), `domain/decision.py` (material and rationale validation),
`persistence/approval_repository.py` (literal N inventory and scope),
`persistence/decision_repository.py` (typed basis), `application/ports.py`, and
`persistence/uow.py` (transaction configuration and error mappings), all under
`src/researchbase/`. In `migrations/versions/0056_b10_reconsideration.py`, inspect
both the installed `pr216_gate`/completeness rewrite and the downgrade restoration
separately. Passing checks do not constitute reviewer acceptance of those paths.


Read-only re-review of the complete migration found no additional concrete P0/P1.
Application re-review identified two additional error-contract gaps: a missing
revision UUID leaked `NoResultFound` during the prior-commit check, and upstream
invalidation of a reconsideration target bypassed `APPROVAL_TARGET_STALE`.
Two new PostgreSQL regressions reproduced both failures (the `-k maps_` run:
2 failed, 1 passed, 26 deselected, 9 warnings in 2.73s). The commitment query now
returns false when no row exists. Target admission verifies historical material,
derives current validity and reports stale, then checks current support, matching
the existing approval gate; corrupt historical material remains a provenance
error. Both regressions assert the exact domain error, unchanged approval history
and absence of the proposed DecisionRecord.

The first remediation full-check run passed static checks but was deliberately
interrupted while implementing these additional P1 fixes; it is not passing
completion evidence. A fresh full check runs against the final source below.


Focused final source verification (with `UV_CACHE_DIR=/tmp/rb-b10-uv` exported):

```sh
uv run pytest -o addopts='' -q tests/integration/phase2/test_b10_reconsideration.py tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_19_replay.py
```

Result: **47 passed, 135 warnings in 44.24s**, exit 0.


Follow-up read-only review confirms both additional P1 error-mapping findings are
resolved; no remaining finding was reported in those fixes. This delegated review
does not replace the owner's requested independent re-review.


Requested full check against the final source (with
`UV_CACHE_DIR=/tmp/rb-b10-uv` exported):

```sh
uv run pyright && uv run ruff format --check . && uv run ruff check . && uv run pytest -o addopts='' -q -rfE -p no:cacheprovider
```

Observed static stages: Pyright **0 errors, 0 warnings, 0 informations**;
Ruff format **579 files already formatted**; Ruff check **All checks passed!**.


Final full pytest result: **6,319 passed, 50 skipped, 4,455 warnings in
5952.25s (1:39:12)**. The entire chained command exited **0**. Skipped cases
remain skips, not passes. These full-run counts include the focused cases above;
they must not be summed with the focused counts. The owner's six reported
failures and both additional error-mapping regressions are green in this run.
Final `git diff --check`: exit **0**. Independent owner re-review remains required;
this evidence does not declare a Phase exit or reviewer approval.
