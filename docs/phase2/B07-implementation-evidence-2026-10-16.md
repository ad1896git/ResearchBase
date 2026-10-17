# B07 first-slice implementation evidence — 2026-10-16

Status: first-slice review-remediation verified; the full required check passed.
The historical blocked result below is superseded by review round 2's passing
evidence. No Phase 2 gate declaration.

## Authority and scope

The owner's 2026-10-16 implementation instruction authorizes the first slice of
[B07](../proposals/B07_Revision_Decisions_Contract_DRAFT.md), including both
Architecture Questions. [ADR-0015](../architecture/adr/ADR-0015-b07-revision-decisions-concern-carry-forward.md)
records that approval and its accepted absence of cryptographic association binding.

Implemented revision-purpose Decisions, complete typed review basis, one exact
concern per Decision, Issue/Decision/combined action bases, explicit NO_CHANGE,
attributable exact re-review correspondence, and historical carry-forward reads.
The single new migration is `0052_b07_revision_decisions`, after
`0051_b06_revision_action`. Prior migrations and frozen numbered architecture
files are unchanged. Existing material_version=1 hash functions are retained.

Writes configure READ COMMITTED and begin transactional SQL with the lexical
26-table SHARE inventory. Reads configure REPEATABLE READ / READ ONLY before
queries and use nonlocking authorization/closure adapters. Deferred completeness
checks cover parent and child insertions; new relations are immutable concrete
RESTRICT FKs. Populated B07-history downgrade refuses loss. SQL graph traversal
uses the concrete FK type rather than inferring type from UUID existence.

Issue disposition, Decision correction, manuscript actions, new scientific result
creation, Approval/release effects, API/CLI endpoints and B08 remain outside scope.
No runtime dependency, branch, commit or push was added. The original focused
verification omitted the PR2-20 checkpoint suite. The external loop reported a
full-check failure; its focused follow-up evidence is recorded below. No whole
suite was run during this restart.

## Recorded substitutions and reuse

- The guide requests Registry 03 / Field Contract 13 edits, but the owner expressly
  forbids editing frozen numbered architecture documents. ADR-0015 supplies the
  additive relation registry, field contracts and purpose policy instead; §11.4
  links that approval. This is an explicit owner override, not inferred approval.
- Exact-ID readers retain the repository's existing `identity` parameter naming
  where the guide describes an `id` argument. Canonical command/DTO field names
  are unchanged.
- Existing B06 UoW connection configuration and protected adapters supply the
  prescribed transaction profile; the existing PostgreSQL `pr216_hash` /
  `pr216_ref` utilities compute literal accepted payloads. No new hash scheme,
  material version, association digest or request receipt was introduced.
- Existing head assertions/inventories and CI head value advance to 0052. The B06
  review-overlap test now establishes review-first ROW EXCLUSIVE exclusion before
  B07 starts, reflecting the newly prescribed review-table SHARE inventory.

## Environment and exact commands

Observed Python **3.12.15**, PostgreSQL **18.6 (Homebrew)**, one Alembic head
`0052_b07_revision_decisions`. Inherited disposable-database configuration was
available. Credentials and connection URLs are omitted.

All uv commands used this prefix from the repository root:

```bash
export UV_PROJECT_ENVIRONMENT=/Users/fengwang/Documents/ResearchBaseProject/.venv
export PYTHONPATH=src
uv --cache-dir /tmp/b07-uv-cache run --offline --no-sync <command>
```

Static and unit/architecture commands:

```bash
ruff check .
ruff format --check .
pyright --pythonpath /Users/fengwang/Documents/ResearchBaseProject/.venv/bin/python
pytest -o addopts='' -ra tests/unit tests/architecture tests/test_architecture.py
```

Focused PostgreSQL command:

```bash
pytest -o addopts='' -ra \
  tests/integration/phase2/test_b07_revision_decisions.py \
  tests/integration/phase2/test_b07_concern_carry_forward.py \
  tests/integration/phase2/test_b07_schema.py \
  tests/integration/phase2/test_b07_concurrency.py \
  tests/integration/phase2/test_revision_action.py \
  tests/integration/phase2/test_b06_revision_action.py \
  tests/integration/phase2/test_b06_revision_concurrency.py \
  tests/integration/phase2/test_pr2_15_decision.py \
  tests/integration/phase2/test_pr2_15_decision_schema.py \
  tests/integration/phase2/test_pr2_15_coordination.py \
  tests/integration/phase2/test_pr2_14_internal_review.py \
  tests/integration/phase2/test_pr2_14_conclusion_review.py \
  tests/integration/phase2/test_pr2_18_concurrency.py \
  tests/integration/phase2/test_approval.py \
  tests/integration/phase2/test_pr2_03_review_guards.py \
  tests/integration/phase2/test_pr2_04_migration_coverage.py \
  tests/integration/phase2/test_pr2_17_authorship_schema.py \
  tests/integration/phase2/test_b04_manuscript_migration.py \
  tests/integration/phase2/test_b05_review_migration.py \
  tests/integration/phase2/test_pr2_04_execution_migration.py \
  tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py
```

Final targeted checks after forcing the inherited parent completeness constraint
alongside B07 constraints, extending historical-source readback verification, and
checking retained-release preflight and exact typed UUID-collision isolation:

```bash
pytest -o addopts='' -ra tests/integration/phase2/test_b07_revision_decisions.py
pytest -o addopts='' -ra 'tests/integration/phase2/test_b07_concern_carry_forward.py::test_each_changed_result_has_exact_independent_scientific_re_review[SOURCE_CHANGE-valid]'
pytest -o addopts='' -ra tests/integration/phase2/test_b07_schema.py::test_upgrade_preflights_retained_release_without_reapplying_late_blockers
pytest -o addopts='' -ra tests/integration/phase2/test_b07_schema.py
git diff --check
```

## Observed final results

| Check | Observed result |
| --- | --- |
| Ruff | All checks passed; exit 0. |
| Format | 578 files already formatted; exit 0. |
| Pyright | 0 errors, 0 warnings, 0 informations; exit 0. |
| Unit + architecture + root architecture | 2,424 passed, 41 warnings; no failures/errors/skips; exit 0. |
| Focused PostgreSQL | 495 passed, 1,335 warnings; no failures/errors/skips; exit 0. |
| Final Decision constraint check | 27 passed, 81 warnings; exit 0. |
| Final historical source check | 1 passed, 3 warnings; exit 0. |
| Retained-release preflight regression | 1 passed, 5 warnings; exit 0. |
| Final schema suite, including later collision regressions | 18 passed, 59 warnings; exit 0. |
| Whitespace | `git diff --check`: exit 0. |

Some targeted checks overlap the comprehensive focused selection; these counts
must not be summed as unique tests. The final schema rerun includes three later
regression cases beyond the comprehensive selection. Pytest warnings are the existing Alembic path_separator
deprecation. Pyright also prints a package-update notice outside its zero-warning
analysis result.

Logs: `/tmp/b07-final-ruff.log`, `/tmp/b07-final-format.log`,
`/tmp/b07-final-pyright.log`, `/tmp/b07-final2-unit-architecture.log`,
`/tmp/b07-verified-postgres.log`, `/tmp/b07-constraints-final.log`,
`/tmp/b07-history-final.log`, `/tmp/b07-release-preflight.log`,
`/tmp/b07-schema-verified.log`. Development failures were corrected and focused
checks rerun; earlier failing logs are not acceptance evidence.


A final content comparison against HEAD verified that all **53** accepted migration
files and all **20** frozen numbered architecture documents are unchanged. Relative
approval/ADR/evidence links resolve, and `git diff --check` passes. Read-only agent
review identified concrete defects during development; the implementation and
regressions address the reported validity, authorship, retained-history and typed
traversal findings. This is automated/read-only review evidence, not a HUMAN gate.

## Reviewer follow-up

The reported failure reproduced with:

```bash
export UV_CACHE_DIR=/tmp/b07-uv-cache
uv run pytest -o addopts='' -q -p no:cacheprovider tests/integration/phase2/test_pr2_20_migrations.py
```

Observed **1 failed, 16 passed, 55 warnings in 7.95s**, exit 1. Relevant failure
output (the complete local log is `/tmp/b07-review-pr220.log`):

```text
_______ test_populated_conclusion_placement_review_and_0042_checkpoints ________
>       saved = service.record_decision(reviewer, request)
tests/integration/phase2/test_pr2_20_migrations.py:525:
>               raise ResearchBaseError(error.code, error.message) from None
E               researchbase.foundation.errors.ResearchBaseError: decision transaction failed
src/researchbase/application/decision.py:212: ResearchBaseError
FAILED tests/integration/phase2/test_pr2_20_migrations.py::test_populated_conclusion_placement_review_and_0042_checkpoints
1 failed, 16 passed, 55 warnings in 7.95s
```

This fails before upgrade from 0042 to head: B07 extended the release reader's
`basis()` SQL with a reference to `decision_basis_claims`, absent at 0042.
The fix restores the accepted release-only query and adds `revision_basis()`
for B07 Claim/conclusion Decisions. No migration or checkpoint expectation was
changed. The unchanged populated checkpoint test is the regression test: it now
records at 0042, upgrades to head preserving manifests, and replays identically.
The same command now reports **17 passed, 56 warnings in 8.85s**, exit 0
(`/tmp/b07-review-pr220-fixed.log`).

Additional requested suites:

```bash
uv run pytest -o addopts='' -q -p no:cacheprovider tests/integration/phase2/test_b07_concurrency.py tests/integration/phase2/test_pr2_04_migration_coverage.py
```

Observed **40 passed, 111 warnings in 34.38s**, exit 0
(`/tmp/b07-review-lock-inventory.log`). This includes the first-SHARE write/replay
protocol and all three exact-read snapshot/lock-free tests. SQL
`b07_validate_decision` locks only with `complete_snapshot=true`, called from the
deferred Decision completeness trigger. The other caller is action write
validation with `false`. Exact read services use Python historical verification
and the nonlocking `pr216_decision_authorized` function; they never call the
locking SQL validator. Inventory waits test holder-first table exclusion, and
link/correction tests cover both orders; this is not evidence of a broader matrix
against every existing owning writer.

Approval audit: the proposal status is exactly
**APPROVED by owner 2026-10-16 — first slice authorized for implementation**.
Section 11.4 is APPROVED and links ADR-0015. ADR-0015 has Context, Decision,
Consequences and Alternatives. The downgrade restores the accepted 0042 Decision
functions and 0051 revision functions; the schema suite exercises empty downgrade,
re-upgrade and refusal to discard populated B07 history.

Scope commands:

```bash
git diff --stat HEAD
git diff --name-status HEAD -- migrations/versions docs/architecture
git diff --check
```

The architecture/migration name-status output contains only:

```text
A docs/architecture/adr/ADR-0015-b07-revision-decisions-concern-carry-forward.md
A migrations/versions/0052_b07_revision_decisions.py
```

All existing migrations and frozen numbered architecture documents remain
unchanged. The full diff-stat was shown in the tool output during this follow-up.

## Restart verification and open P1 — 2026-10-16

Historical stopping-point evidence: the subsequent owner instruction authorized
the protocol remediation recorded in review round 2 below.

This restart reviewed the partial tree and used two read-only investigation agents;
only the primary agent wrote files. The 0042 reader fix above was already present
and was retained. A further scope-error defect was corrected: a new action naming
a foreign Decision now returns FORBIDDEN, an absent Decision returns NOT_FOUND,
and a broken persisted Decision reference remains PROVENANCE_CLOSURE_VIOLATION.
Two real-PostgreSQL regression cases pass and leave no partial action.

The required real-writer concurrency matrix was extended with 18 cases: each B07
write against the existing release Decision, InternalReview and novelty prior-art
commands in both orders. These tests use events, separate backend IDs,
pg_stat_activity and pg_blocking_pids, rather than sleep-only ordering. Implicit
result-FK waits are distinguished from explicit scientific row locking.

**P1 MAJOR — B07 §12.2 compatibility reasoning contradicts the existing Review
writer. Implementation stopped under the owner's semantic/architecture
contradiction instruction; this is not an accepted first slice.**

Two reproducible cases fail:

```text
test_real_governance_writers_overlap_without_scientific_lock_inversion[b07_first-review-decision]
test_real_governance_writers_overlap_without_scientific_lock_inversion[b07_first-review-link]
psycopg.errors.DeadlockDetected: deadlock detected
LINE 1: INSERT INTO internal_review_records
DETAIL: Process 1031 waits for RowExclusiveLock ... blocked by process 994.
Process 994 waits for ShareLock on transaction 3269226; blocked by process 1031.
2 failed, 45 passed, 141 warnings in 48.25s
```

Backend evidence captures both edges: Review waits at INSERT into
`internal_review_records` on B07's SHARE inventory; B07 waits at INSERT into
`decision_records` or `revision_action_re_reviews` on the Review transaction.
Review's accepted authorization path takes FOR UPDATE on project and actor rows
(`ScientificConclusionService._authorize` / literature-search-plan repository).
PostgreSQL's implicit FK checks on the new rows need conflicting KEY SHARE locks;
the absence of explicit scientific row locks in B07 does not remove those waits.
The link case uses the same HUMAN reviewer, so its `recorded_by` FK participates.
This occurs before the B07 validation functions discussed in round 1.

The Review command is the deadlock victim and exposes its existing driver error;
B07's bounded retry cannot retry a different owning command. A correction needs
an owner-approved protocol amendment, such as admitting a Review writer change
that establishes review-table insertion exclusion before its row locks, or a
different approved compatible exclusion protocol. Neither silently changing the
FIRST SHARE statement nor modifying other owning writers is authorized here.
The failing regressions remain enabled; no xfail/skip or weakened assertion hides
this finding. The remaining 16 new real-writer cases pass.

All commands below ran from the repository root with
`UV_CACHE_DIR=/tmp/b07-uv-cache`; the checkout-local uv environment was used.

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest -o addopts='' -q -p no:cacheprovider tests/unit tests/architecture tests/test_architecture.py
uv run pytest -o addopts='' -q -p no:cacheprovider tests/integration/phase2/test_pr2_20_migrations.py
uv run pytest -o addopts='' -q -p no:cacheprovider tests/integration/phase2/test_b07_revision_decisions.py
uv run pytest -o addopts='' -q -p no:cacheprovider --tb=short tests/integration/phase2/test_b07_concurrency.py
uv run pytest -o addopts='' -q -p no:cacheprovider tests/integration/test_pr11r2_migration.py
uv run pytest -o addopts='' -q -p no:cacheprovider tests/integration/phase2/test_m2_metadata.py
uv run alembic heads
git diff --check
git diff --stat HEAD
git diff --name-status HEAD -- migrations/versions docs/architecture
```

The additional focused PostgreSQL command (collected before the 20 new regression
cases were added; overlapping counts must not be summed):

```bash
uv run pytest -o addopts='' -q -p no:cacheprovider \
  tests/integration/phase2/test_b07_revision_decisions.py \
  tests/integration/phase2/test_b07_concern_carry_forward.py \
  tests/integration/phase2/test_b07_schema.py \
  tests/integration/phase2/test_b07_concurrency.py \
  tests/integration/phase2/test_revision_action.py \
  tests/integration/phase2/test_b06_revision_action.py \
  tests/integration/phase2/test_b06_revision_concurrency.py \
  tests/integration/phase2/test_pr2_15_decision.py \
  tests/integration/phase2/test_pr2_15_decision_schema.py \
  tests/integration/phase2/test_pr2_15_coordination.py \
  tests/integration/phase2/test_pr2_14_internal_review.py \
  tests/integration/phase2/test_pr2_14_conclusion_review.py \
  tests/integration/phase2/test_pr2_18_concurrency.py \
  tests/integration/phase2/test_approval.py \
  tests/integration/phase2/test_pr2_03_review_guards.py \
  tests/integration/phase2/test_pr2_04_migration_coverage.py \
  tests/integration/phase2/test_pr2_17_authorship_schema.py \
  tests/integration/phase2/test_b04_manuscript_migration.py \
  tests/integration/phase2/test_b05_review_migration.py \
  tests/integration/phase2/test_pr2_04_execution_migration.py \
  tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py
```

| Restart check | Observed result |
| --- | --- |
| Ruff | All checks passed; exit 0. |
| Format | 578 files already formatted; exit 0. |
| Pyright | 0 errors, 0 warnings, 0 informations; exit 0. |
| Unit/architecture/root architecture | 2,424 passed, 41 warnings in 52.39s; exit 0. |
| 0042/populated checkpoint suite | 17 passed, 56 warnings in 10.04s; exit 0. |
| 21-file focused PostgreSQL selection | 498 passed, 1,346 warnings in 438.06s; exit 0. |
| Final revision-decision suite | 29 passed, 87 warnings in 30.70s; exit 0. |
| Final concurrency suite | **2 failed, 45 passed**, 141 warnings in 48.25s; exit 1. |
| PR11R2 head-dependent migration suite | 2 passed, 2 warnings in 13.75s; exit 0. |
| M2 head-dependent migration suite | 21 passed, 25 warnings in 147.82s; exit 0. |
| Alembic heads | One head: 0052_b07_revision_decisions. |

Logs: `/tmp/b07-restart-unit-architecture-final.log`,
`/tmp/b07-restart-pr220-final.log`, `/tmp/b07-restart-postgres.log`,
`/tmp/b07-restart-decisions-final.log`, `/tmp/b07-restart-concurrency-final2.log`,
`/tmp/b07-restart-pr11r2-inventory.log`, `/tmp/b07-restart-m2-inventory.log`.
Earlier development runs of the new
concurrency tests had fixture/assertion defects; those were corrected and are
not the final result above. No whole-suite run, commit, push or branch was made.

The draft status remains exactly **APPROVED by owner 2026-10-16 — first slice
authorized for implementation**; §11.4 remains APPROVED and links ADR-0015.
The read-only audit confirmed Context, Decision, Consequences and Alternatives
in that ADR, and whitespace-normalized equality of all four downgrade-restored
functions against accepted 0042/0051. The architecture/migration name-status
output still contains only the new ADR and 0052. Existing migrations and frozen
numbered architecture files remain unchanged. The validator's row locks remain
write-only; the exact-read snapshot/lock-free tests pass in the final concurrency
run. None of those passes closes the new P1.

## Review round 2 — authorized writer-order remediation

The owner's next task explicitly requires one global B07 row order and authorizes
changing the Review writer to remove the cycle. ADR-0015 records this amendment;
the proposal's implementation guide now states it. No frozen architecture file
was changed.

The original §12.2 said:

> New request: current write entitlement; exact Issue `FOR UPDATE`

and for re-review links:

> New link: action `FOR UPDATE`; reread successor; collect old and new immutable
> review IDs, lock `FOR SHARE` in UUID order, then effective Issue `FOR SHARE`.

Those original row sequences differed from the global order now explicitly
requested. The previously observed deadlock was additionally caused by an
implicit FK/Review-authorization cycle: B07 held SHARE on internal_review_records
and waited at INSERT into decision_records/revision_action_re_reviews; Review
held project/actor FOR UPDATE locks and waited for ROW EXCLUSIVE on
internal_review_records. The earlier backend details and failing test names are
preserved above rather than reclassified as passing evidence.

The implemented order is now:

1. Every B07 write/replay starts with SHARE(B), unchanged READ COMMITTED bounded
   profile and request advisory identity. Replays do not enter admission locks.
2. New admission discovers immutable IDs nonlocking, locks review records FOR
   SHARE by UUID, then the Issue (FOR UPDATE for Decision selection; FOR SHARE
   for action/link), then action/predecessor FOR UPDATE when needed. Concern and
   successor presence are checked after the relevant lock wait. Application and
   new/replaced revision SQL trigger paths use this same order.
3. Existing Review creation/replay first reserves ROW EXCLUSIVE on its insertion
   table, before any scientific/project/actor row lock. This excludes B07 before
   either side can form the FK cycle; Review writers remain mutually compatible.
   It does not SHARE-lock its own destination and therefore cannot form a
   SHARE-to-ROW-EXCLUSIVE upgrade cycle. Normal-role SQL INSERT reserves this mode
   before running its triggers automatically.
4. BEFORE re-review admission validates current correspondence and holds all
   exclusions through commit. Deferred re-review validation calls
   `b07_validate_re_review(NEW,false)` and acquires no admission locks, while still
   rechecking closure, successor state and current validity. Other transactions
   cannot change protected mutable facts before commit; a new regression also
   denies later invalidation by the same SQL transaction. The action lock
   continues to serialize first linkage with predecessor correction.

Database-observed tests hold a review FOR UPDATE, observe the SQL guard waiting,
and successfully probe Issue/action with FOR UPDATE NOWAIT. Thus later locks
have not been acquired early. A separate read-only call proves deferred-mode
validation completes while another backend holds action/review row locks.
The real-writer overlap matrix now checks Review waits at its *first reservation*
with no granted RowShareLock before B07 is released; both sides then commit.
The former unconditional reverse-cycle witness was replaced with this assertion
because a correct writer must no longer enter that cycle.

Decision/action/concern graph reads, including mapped re-reviews, are inspected
after every SQL statement by a separate pg_locks observer. They use REPEATABLE
READ, acquire no explicit tuple/advisory/table exclusion locks, and never call
B07 SQL validators. SIReadLock is excluded from the assertion: PostgreSQL may
retain nonblocking predicate locks from an earlier SERIALIZABLE transaction on
a pooled backend; these are neither newly acquired row locks nor B07 exclusions.
The existing concurrent-INSERT snapshot tests additionally cover READ ONLY and
snapshot isolation throughout nested readers.

Requested scope output at this revision:

```text
$ git diff --stat HEAD -- migrations docs/architecture
 ...b07-revision-decisions-concern-carry-forward.md |   81 ++
 migrations/versions/0052_b07_revision_decisions.py | 1312 ++++++++++++++++++++
 2 files changed, 1393 insertions(+)

$ grep -n "APPROVED by owner" docs/proposals/B07_Revision_Decisions_Contract_DRAFT.md
3:**Status: APPROVED by owner 2026-10-16 — first slice authorized for implementation**
321:| Schema | **Option (b) for both `decision_revision_concerns` and `revision_action_re_reviews`: APPROVED by owner 2026-10-16 through ADR-0015 (§11.4).** Activate already-registered `decision_basis_claims` separately; it is not a new schema proposal. No generic target JSON, new canonical entity, hash or receipt. |
405:### 11.4 Architecture Questions — APPROVED by owner 2026-10-16
504:-- B07-AQ-01: APPROVED by owner 2026-10-16; ADR-0015.
513:-- B07-AQ-02: APPROVED by owner 2026-10-16; ADR-0015.
```

The only entries are new ADR-0015 and new 0052. All four downgrade restore bodies
remain unchanged from their earlier audited form; the new lock helper is dropped
after restoration. ADR-0015 still has Context, Decision, Consequences and
Alternatives. The sole modified existing Review assertion now expects its new
first insertion reservation followed by the original B05 SHARE inventory.

Final focused results (same UV_CACHE_DIR prefix, repository root):

```bash
uv run pytest -o addopts='' -q -p no:cacheprovider tests/unit tests/architecture tests/test_architecture.py
uv run pytest -o addopts='' -q -p no:cacheprovider tests/integration/phase2/test_b07_concurrency.py
uv run pytest -o addopts='' -q -p no:cacheprovider tests/integration/phase2/test_b07_revision_decisions.py
uv run pytest -o addopts='' -q -p no:cacheprovider tests/integration/phase2/test_b07_schema.py::test_deferred_link_still_rejects_later_same_transaction_invalidation
uv run pytest -o addopts='' -q -p no:cacheprovider tests/integration/phase2/test_b05_manuscript_review.py::test_insert_reservation_precedes_share_and_reads_have_no_explicit_locks
```

| Final focused check | Actual result |
| --- | --- |
| Unit/architecture/root architecture on the final implementation | 2,424 passed, 41 warnings in 48.83s; exit 0. |
| B07 concurrency, including both formerly failing cases | 54 passed, 162 warnings in 63.55s; exit 0. |
| B07 revision Decisions, including all three pg_locks read assertions | 32 passed, 96 warnings in 39.82s; exit 0. |
| Same-transaction deferred validity regression | 1 passed, 3 warnings in 0.96s; exit 0. |
| Updated manuscript first-reservation/read regression | 1 passed, 4 warnings in 0.67s; exit 0. |

Logs: `/tmp/b07-r2-unit-architecture.log`, `/tmp/b07-r2-concurrency-verified.log`,
`/tmp/b07-r2-decisions-verified.log`, `/tmp/b07-r2-validity-final.log`,
`/tmp/b07-r2-b05-reservation.log`. The manuscript regression also emits an
SQLAlchemy warning that prepare_write's redundant isolation option is ignored;
the UoW already configured READ COMMITTED before the first reservation. Its
effective profile is asserted by the concurrency tests.

The first full-check attempt was interrupted to preserve current-validity
revalidation in the deferred nonlocking mode (exit 130). It is not pass evidence.
The full required command was restarted after that correction and passed:

```bash
export UV_CACHE_DIR=/tmp/b07-uv-cache
uv run pyright && uv run ruff format --check . && uv run ruff check . && uv run pytest -o addopts='' -q -rfE -p no:cacheprovider
```

Observed output, `/tmp/b07-r2-required-final.log`, overall **exit 0**:

```text
0 errors, 0 warnings, 0 informations
578 files already formatted
All checks passed!
6341 passed, 50 skipped, 4614 warnings in 6001.40s (1:40:01)
```

The 50 existing gated cases remained skipped, rather than being counted as
passing; no skip/xfail was added for B07 or its deadlock regressions.
The skips are the opt-in large PR220 benchmark, the authorized HG1 live-check
gate, and the future SUPERSEDED-manuscript contract case. Warning
output includes the existing Alembic path_separator deprecation and the redundant
isolation-option warning described above. Both formerly failing real-Review
overlap cases, the full migration/checkpoint inventories, and every touched suite
ran in this required check. All P1 findings from this review round are closed by
the implementation and passing evidence; no Phase 2 gate or merge is declared.
