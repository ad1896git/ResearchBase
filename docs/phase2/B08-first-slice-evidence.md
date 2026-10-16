# B08 first-slice implementation evidence — 2026-10-16

Owner authorization: [approved B08 contract](../proposals/B08_Issue_Disposition_Contract_DRAFT.md).
Architecture admission: [ADR-0016](../architecture/adr/ADR-0016-b08-issue-disposition.md),
building on accepted B07/ADR-0015. This report concerns the authorized first slice
only. The original task reserved whole-suite execution for the external loop.
The subsequent reviewer-remediation instruction explicitly requires the full check;
its results are recorded in the remediation section below.
No commit, push or branch creation was performed.

## Implemented behavior

The existing InternalReviewService now records one OPEN→ADDRESSED/DISMISSED event,
reads an exact disposition, and reads exact Issue history. Commands and readbacks
are closed typed values with strict UUID/enum/text/time/hash checks. An exact
completed action and committed B07 action/re-review membership are required.
The finite HUMAN authority, independence, Decision, favorable-review and result
policies are enforced without changing scientific validity or historical hashes.

Terminal events and the existing status projection commit together. Scientific
history, original descriptors and OPEN roots remain unchanged. Historical replay
requires the original actor and current read entitlement, and reports later
validity/supersession honestly. Other UUIDs cannot replace a disposition. Reads,
including nested SQL history/closure validation, use one lock-free REPEATABLE READ,
READ ONLY snapshot. Writes begin with the exact SHARE inventory in READ COMMITTED,
then the event advisory key, sorted review locks and sorted mixed-mode Issue locks.
No B08 action or scientific target/parent/project row lock was added.

The single new migration is `0053_b08_issue_disposition`, after
`0052_b07_revision_decisions`. It adds only concrete event basis/rationale fields,
partial uniqueness, projection/immutability/history guards and guarded downgrade.
Deferred admission checks cover a selected-review blocker inserted later in the
same transaction, even after SET CONSTRAINTS ALL IMMEDIATE. Committed historical
events retain structural validation when new concerns appear later.

The required real evidence-writer race exposed an existing authorization actor
row lock versus SHARE inventory/FK inversion. The supporting evidence writer
repair reserves its actual INSERT table mode before authority rows, following the
accepted review writer pattern. Its SERIALIZABLE transaction and scientific
semantics are unchanged. Real role/source/evidence/validity writers, correction,
mapping, competing dispositions, sorted multi-Issue passes, release and Approval
are exercised in both commit orders. Snapshot tests prove a separate backend can
commit unrelated insertion/disposition while the earlier read remains paused;
that read retains its snapshot, and a fresh read sees the committed history.

No API/CLI endpoints, new canonical table/entity/hash/receipt, external effect,
reopening, manuscript disposition, release implementation or grant consumption
was added. Existing release/Approval blockers and scientific gates remain active.

## Existing equivalents and substitutions

- Shipped B07 `REVISION_SNAPSHOT_TABLES` already includes `internal_review_records`
  and exactly matches the 26-table inventory. Reuse it directly without duplication.
- The guide's 0041 Issue guard has a later shipped equivalent in 0049. Preserve
  its manuscript INSERT coordination in both the new guard and downgrade restore.
- Persistence retains existing `issue_id`; public DTOs use `review_issue_id`.
- Shared normal-role and exact-result test builders are exported through
  `tests/integration/phase2/revision_support.py`; B08 fixture/build preparation is
  in `b08_support.py`, instead of adding new test-to-test builder dependencies.

## Verification environment and migration evidence

All commands below ran from this checkout with the same exact prefix:

```sh
uv --cache-dir /tmp/b08-uv-cache run --offline --no-sync
```

No dependency installation or network lookup was required. The configured test
admin connection reported PostgreSQL **18.6 (Homebrew)**. Tests use disposable real
PostgreSQL databases, including normal-role SQL and separate backend observations.

`alembic heads` reported `0053_b08_issue_disposition (head)`. A byte comparison of
all 54 tracked files under migrations/versions against HEAD found zero changes;
exactly one new migration file exists. Its SHA-256 is
`ac93a13b17aa6872230bbf831613c2775cf382e81ce1d64774106f8f628b2b63`.
The migration inventory appends B07 and B08; head assertions are updated additively.
Fresh installs, populated B07 upgrades, OPEN-only downgrades, terminal downgrade
refusal and corrupt-root upgrade refusal are covered by the PostgreSQL tests.

## Original focused checks — insufficient for acceptance

| Command after the prefix above | Observed final result |
| --- | --- |
| `ruff check .` | All checks passed; exit 0. |
| `ruff format --check .` | 587 files already formatted; exit 0. |
| `pyright` | 0 errors, 0 warnings, 0 informations; exit 0. |
| `pytest -o addopts='' -q tests/unit tests/architecture` | 4,716 passed, 41 warnings; exit 0. |
| B08 PostgreSQL command below | 95 passed, 290 warnings in 277.86s; exit 0. |
| Inherited governance command below | 383 passed, 1,129 warnings in 425.12s; exit 0. |
| Touched migration/evidence command below | 187 passed, 453 warnings in 142.47s; exit 0. |

B08 PostgreSQL command:

```sh
uv --cache-dir /tmp/b08-uv-cache run --offline --no-sync pytest -o addopts='' -q tests/integration/phase2/test_b08_*.py
```

Inherited governance command:

```sh
uv --cache-dir /tmp/b08-uv-cache run --offline --no-sync pytest -o addopts='' -q \
  tests/integration/phase2/test_revision_action.py \
  tests/integration/phase2/test_b06_revision_action.py \
  tests/integration/phase2/test_b06_revision_concurrency.py \
  tests/integration/phase2/test_pr2_14_internal_review.py \
  tests/integration/phase2/test_pr2_14_conclusion_review.py \
  tests/integration/phase2/test_pr2_15_decision.py \
  tests/integration/phase2/test_pr2_15_decision_schema.py \
  tests/integration/phase2/test_pr2_15_coordination.py \
  tests/integration/phase2/test_pr2_18_concurrency.py \
  tests/integration/phase2/test_b07_*.py \
  tests/integration/phase2/test_approval.py
```

Touched migration/evidence command:

```sh
uv --cache-dir /tmp/b08-uv-cache run --offline --no-sync pytest -o addopts='' -q \
  tests/integration/phase2/test_m3_evidence.py \
  tests/integration/phase2/test_b05_review_basis.py \
  tests/integration/phase2/test_b05_review_races.py \
  tests/integration/phase2/test_b05_review_migration.py \
  tests/integration/phase2/test_b04_manuscript_migration.py \
  tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py \
  tests/integration/phase2/test_pr2_03_review_guards.py \
  tests/integration/phase2/test_pr2_04_execution_migration.py \
  tests/integration/phase2/test_pr2_04_migration_coverage.py \
  tests/integration/phase2/test_pr2_17_authorship_schema.py
```

`git diff --check` passed. Staged development runs exposed the evidence lock
inversion and old OPEN-only SQLSTATE/deferred-check assumptions; these were fixed
and are not counted as successful final runs. Existing Alembic path_separator
warnings, inherited review connection-option warnings, and the Pyright version
notice do not represent failed checks. The three final PostgreSQL selections total **665 passed**, with no failures or skips.
Whole-suite execution was **not run at the original focused handoff**. The
reviewer subsequently reported **5 failed, 8,735 passed**, so that handoff did
not establish a full-check PASS. The results below supersede it for remediation.

Read-only sub-agents investigated and reviewed the implementation; only the main
agent wrote files. Final reviewed application/persistence/migration paths have no
identified P0/P1. A P2 suggestion to cross-check more directly constructed history
DTO fields remains optional; service-generated histories verify their saved graph
before exposure. This report does not declare Phase 2 exit or release acceptance.


## Reviewer remediation

All five reported nodes reproduced together: **5 failed, 15 warnings in 4.79s**.
This confirms the review rejection; the earlier focused counts are historical
observations, not a substitute for the requested full check.

- The B05 read test now observes `transaction_isolation=repeatable read` and
  `transaction_read_only=on`, retaining its no-explicit-lock assertion. Connection
  configuration before the first query replaces the old in-transaction SET SQL.
- Catalog expectations name `ck_b08_issue_status` and require the finite
  OPEN/ADDRESSED/DISMISSED vocabulary. The independent migration allow-list in
  `tests/test_architecture.py` now admits only 0053's accepted existing-table refs.
- Decision blocker queries discover terminal Issue IDs first and validate those
  histories only when present. OPEN-only 0042 checkpoints no longer parse a
  not-yet-installed B08 SQL function; terminal integrity and blocker gates remain.
- Source freeze had a real table-lock inversion: its source_versions UPDATE
  preceded its literature_sources pointer UPDATE, while B08 acquires SHARE in
  the opposite lexical order. Source writes now reserve their final
  ROW EXCLUSIVE modes before any source/authority row lock. The race test keeps
  its original pause after source_versions UPDATE, before pointer publication,
  and asserts the reservation and committed pointer. It was not skipped, xfailed,
  or moved past the unsafe point.
- B08 retry metadata is now an explicit UoW opt-in for disposition writes only.
  Ordinary Decision errors retain their prior metadata and retry behavior.
  Tests cover both isolation of that behavior and the three-attempt B08 limit.
- DTO reflection imports are at module scope and hash checks use public
  foundation.ContentHash, retaining strict lowercase validation.

### Supporting writer reservation scope

[B08 §12.2](../proposals/B08_Issue_Disposition_Contract_DRAFT.md#122-exact-lock-order-and-transactions)
requires the exact table-first SHARE protocol and says “SHARE writes stabilize
mutable inputs”. [§12.4](../proposals/B08_Issue_Disposition_Contract_DRAFT.md#124-test-artifacts-and-required-cases)
requires actual “role/credential/source/evidence/validity writers both orders”.
These sections require compatible writer coordination; the reservation is the
necessary implementation repair inferred from those requirements, rather than
an explicit new scientific operation specified by the guide. The owner's current
instruction to fix the failing concurrency test authorizes the source repair.

The remaining reservations cover existing evidence creation/review destinations
(`literature_evidence`, `literature_evidence_review_events`), document import
(`artifact_versions`, `artifacts`), and source writes (`literature_sources`,
`source_versions` for freeze; `source_versions` for create/update/abandon).
They acquire final compatible ROW EXCLUSIVE modes before authorization rows, with
10s lock/30s statement bounds. Source/evidence transaction isolation remains
SERIALIZABLE; B08 remains READ COMMITTED with its unchanged FIRST-statement SHARE
inventory. No table/schema, scientific state contract or B07 lock order changes.
IMPORT_DOCUMENT retains only its actual artifact_versions/artifacts INSERT
reservations: removing them restored the same actor-FK cycle in unrelated imports
by the disposer. Six additional real-backend cases cover document import and
source draft create/update by that same actor, in both commit orders, and assert
reservation precedes authority rows. These existing paths have no schema changes.

### Remediation commands and results

The default uv cache is outside this sandbox's writable roots. The first literal
`uv run` attempt failed before executing tests with a cache-access error. All
subsequent commands use only this environment adjustment:

```sh
export UV_CACHE_DIR=/tmp/b08-uv-cache
```

Five failing nodes, run by exact node ID after fixes:

```sh
uv run pytest -o addopts='' -q -rfE -p no:cacheprovider \
  tests/integration/phase2/test_b05_manuscript_review.py::test_insert_reservation_precedes_share_and_reads_have_no_explicit_locks \
  'tests/integration/phase2/test_b08_concurrency.py::test_actual_mutable_writers_both_commit_orders[mutation_first-source]' \
  tests/integration/phase2/test_pr2_20_catalog_plans.py::test_catalog_matches_accepted_review_constraints_and_indexes \
  tests/integration/phase2/test_pr2_20_migrations.py::test_populated_conclusion_placement_review_and_0042_checkpoints \
  tests/test_architecture.py::test_phase1_has_no_unauthorized_later_business_schema_migration
```

Observed final rerun: **5 passed, 16 warnings in 4.19s**, exit 0. Additional retry/DTO unit
selection: **2,331 passed in 0.89s**, exit 0.

Repeated concurrency command (three consecutive runs):

```sh
uv run pytest -o addopts='' tests/integration/phase2/test_b08_concurrency.py -q
```

Results, with the final code frozen: **46 passed, 0 failed** in each of the three
consecutive runs (109.53s, 101.24s, 101.61s; 138 warnings per run). All exited 0:
**138 passed, 0 failed** across repetitions, with no new skip/xfail marks.

Required full command (explicitly authorized by the reviewer-remediation request):

```sh
uv run pyright && uv run ruff format --check . && uv run ruff check . && uv run pytest -o addopts='' -q -rfE -p no:cacheprovider
```

An intermediate full run was deliberately interrupted after 206 passed and 48
skipped to apply the follow-up same-actor writer fixes. It is not a PASS.
A second intermediate run found a stale inherited B06 wait assertion and was
interrupted: **1 failed, 557 passed, 49 skipped, 1,253 warnings in 804.68s**.
The exact node
`tests/integration/phase2/test_b06_revision_concurrency.py::test_owning_source_and_evidence_writers_have_observed_commit_orders[action_first-source]`
reproduced with **1 failed, 3 warnings in 10.98s**. The source writer now correctly
waits on its early table reservation, so the test asserts a relation wait and the
exact reservation SQL, retaining backend blocking and both commit-order checks.

```sh
uv run pytest -o addopts='' -q -rfE -p no:cacheprovider tests/integration/phase2/test_b06_revision_concurrency.py
```

The complete B06 concurrency file then passed: **9 passed, 27 warnings in 10.37s**,
exit 0. This test-only expectation correction does not change the production code
used by the three consecutive B08 concurrency runs above.

Final uninterrupted execution: **PASS**, exit 0.

- Pyright: **0 errors, 0 warnings, 0 informations**.
- Ruff format: **587 files already formatted**.
- Ruff lint: **All checks passed!**
- Full pytest: **8,750 passed, 50 skipped, 4,922 warnings in 6,279.76s
  (1:44:39)**; **0 failed, 0 errors**.

The five original failing nodes and the corrected inherited B06 concurrency node
also passed within this complete execution. No B08 concurrency case is skipped or
xfail. The skips above are outside B08. The final full-check log is
`/tmp/b08-review-complete-check.log` in this workspace's execution environment.
`git diff --check` also exited 0 after the final documentation update.
No commits, pushes or branches were created.
