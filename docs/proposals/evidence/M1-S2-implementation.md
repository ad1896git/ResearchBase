# M1-S2 implementation and focused verification — 2026-10-20

Only the owner-authorized corrected-review slice is implemented. Manuscript
REVISED_TARGET reconsideration remains deferred under §12.5. This record makes
no Phase 2 exit or whole-suite acceptance claim. No commit, push or branch was
created.

## Changes and compatibility

- Added the closed `RecordManuscriptRejectionReconsiderationCommand` and exact
  record/get methods for READY_FOR_SUBMISSION and PREPARE_SUBMISSION. The release
  command retains its required conclusion argument and its existing two grounds.
- Reused concrete manuscript/review/rejection basis relations and unchanged R2
  hashes. The additive readback has an optional manuscript ID and nullable
  conclusion ID with exactly-one XOR. S2 reads derive canonical basis ordinals.
- Enforced current HUMAN APPROVER authority, independence from every cited
  reviewer, every rejector and the new target's material authors; complete
  project/purpose rejection coverage; all eligible committed fresh independent
  reviews; named, reasoned corrections of saved request reviews; and empty
  revision-action IDs. Reconsideration creates no grant.
- Enabled separately requested, uniquely consuming successors through the normal
  B12/B14r gates. Requester/approver independence, exact target/hash, complete
  rejection coverage, consent policy and ordinary approval checks remain active.
  B14 consumption also admits the validated READY successor; the reconsideration
  command performs no lifecycle effect.
- Added project-scoped POST/GET `manuscript-rejection-reconsiderations` and the
  requested CLI record/get commands, with closed payloads and trusted principals.
- Added only migration `0075_m1_reconsideration`, after 0074. Accepted migrations are unchanged; no tables, columns, dependencies, hash
  schemes or canonical entities were added. Existing guards and the question
  constraint are extended by the new migration.
  Existing writer lock inventories are unchanged. S2 uses the existing literal
  first B09 SHARE, decision advisory, purpose-scope advisory, manuscript FOR UPDATE,
  then Publication FOR SHARE. Writes remain READ COMMITTED; read/replay discovery
  remains REPEATABLE READ / READ ONLY without explicit locks or constraint forcing.

The [migration](../../../migrations/versions/0075_m1_reconsideration.py) carries
literal predecessor function bodies in `_DOWNGRADE`; `_UPGRADE` contains the
forward definitions. Its downgrade refuses
S2 reconsideration/successor history with P17F1, otherwise restores the exact 0074
functions, question constraint and typed graph view, and removes only S2 helpers
and triggers. The pristine-0074 catalog roundtrip test compares all public function definitions,
trigger definitions, the view, the question constraint and table/column inventory,
then re-upgrades. No scientific history is deleted, rewritten or rehashed.

Saved manuscript facts and current admission use separate SQL paths. Corrected
old targets may be stale while their immutable seals remain verifiable. The new
target must be current and VALID, in the required lifecycle, with no applicable
OPEN/BLOCKING issue. Tests cover this distinction for both purposes.

## Recorded substitutions

- The guide's tentative second migration number is rebased to the actual child
  `0075_m1_reconsideration` after committed 0074.
- The existing manuscript dispatch is `b11_manuscript_basis_guard`; existing
  `pr215_complete_basis` already delegates reconsideration completion to B10.
  `b10_basis_guard` and `b10_no_basis_cycle` reuse their existing algorithms via
  the extended helpers/view and the two required manuscript constraint triggers.
- `b10_edges` is the existing typed graph **view**, not a stored graph entity or
  function. It now includes manuscript basis, review and frozen dependency edges.
- S2 race cases live in `test_m1_reconsideration_races.py` beside the existing
  S1 `test_m1_concurrency.py`; S2 schema cases live with their manuscript
  reconsideration acceptance cases. Existing S1 case bodies remain unchanged.
- Existing typed ports, UoW configuration, SQLSTATE normalization and approval
  repository locking methods already supply S2's operations; no redundant new
  port or UoW protocol was introduced.

## Focused verification

Commands use the repository's inherited local TCP PostgreSQL test-admin selector
and disposable databases; `UV_CACHE_DIR=/tmp/researchbase-m1-uv-cache` redirects
only the uv cache. The configured application database was not migrated by these
runs. The whole test suite was not run; the owner's loop owns that check.

```sh
UV_CACHE_DIR=/tmp/researchbase-m1-uv-cache uv run ruff check .
UV_CACHE_DIR=/tmp/researchbase-m1-uv-cache uv run ruff format --check .
UV_CACHE_DIR=/tmp/researchbase-m1-uv-cache uv run pyright
git diff --check HEAD
UV_CACHE_DIR=/tmp/researchbase-m1-uv-cache uv run pytest tests/unit tests/architecture tests/test_architecture.py --tb=short
UV_CACHE_DIR=/tmp/researchbase-m1-uv-cache uv run pytest tests/integration/phase2/test_m1_manuscript_reconsideration.py tests/integration/phase2/test_m1_reconsideration_races.py -s --tb=short
UV_CACHE_DIR=/tmp/researchbase-m1-uv-cache uv run pytest tests/integration/phase2/test_b10_reconsideration.py tests/integration/phase2/test_b10_reconsideration_schema.py tests/integration/phase2/test_b10_reconsideration_concurrency.py tests/integration/phase2/test_b12_prepare_decision.py tests/integration/phase2/test_b12_prepare_approval.py tests/integration/phase2/test_b12_prepare_schema.py tests/integration/phase2/test_b12_prepare_races.py tests/integration/phase2/test_b12_prepare_replay.py tests/integration/phase2/test_b14r_ready_approval.py tests/integration/phase2/test_b14r_ready_approval_schema.py tests/integration/phase2/test_b14r_ready_approval_races.py tests/integration/phase2/test_b14r_ready_approval_replay.py --tb=short
UV_CACHE_DIR=/tmp/researchbase-m1-uv-cache uv run pytest tests/integration/phase2/test_b10_reconsideration_schema.py --tb=short
```

| Check | Exact observed result |
|---|---|
| Ruff lint | All checks passed; exit 0 |
| Ruff format | 794 files already formatted; exit 0 |
| Pyright | 0 errors, 0 warnings, 0 informations; exit 0 |
| Whitespace | `git diff --check HEAD`: exit 0, no output |
| Unit + architecture + root architecture | 6,263 passed, 54 warnings in 89.04 seconds |
| Final S2 PostgreSQL acceptance and races | 53 passed, 162 warnings in 137.18 seconds |
| Combined B10/B12/B14r regression run | 202 passed, 1 failed, 627 warnings in 528.80 seconds |
| Complete B10 schema rerun after head-count correction | 22 passed, 69 warnings in 88.17 seconds |
| Other touched PostgreSQL suites and B14 consumption regressions, started before the constraint-literal fix | 414 passed, 3 failed, 1,129 warnings in 684.56 seconds |
| All three catalog failure nodes after the migration fix | 3 passed, 26 warnings in 5.26 seconds |
| Strengthened pristine-0074 catalog roundtrip | 1 passed, 4 warnings in 1.73 seconds |

The combined regression run's sole failure was
`test_empty_roundtrip_and_populated_downgrade_refusal`: its head-catalog assertion
expected 10 B10 deferred triggers. S2 explicitly requires one additional
`b10_no_basis_cycle` trigger on `decision_basis_manuscripts`, so the head count is
11. Only that expected value changed; its FK, deferred, history and rollback
assertions remain. The complete 22-case schema rerun passed. All other 202 nodes
passed the combined run. No failed test is represented as a PASS in the table.

The other regression batch's three failures were the two B14a clean-downgrade
parameters and the migration-chain catalog roundtrip. Exact comparison identified
a carriage return in `ck_b10_text_bounds`' original 29-character whitespace set:
Python source loading had normalized an embedded CR to LF. The new migration now
uses PostgreSQL `E'\u....'` escape strings for both forward and restored check
literals. No existing assertion was changed to accommodate this bug. All three
nodes passed the targeted rerun. The S2 roundtrip test was also strengthened to
create an untouched 0074 from accepted migrations before capturing its complete
logical catalog, rather than capturing a baseline after an S2 downgrade; it
passed. The final 53-case S2 run above uses the repaired migration. The 414 other
nodes passed their batch. These results resolve all four observed regression
failure nodes; the earlier nonzero invocations remain reported exactly.

The other regression batch was launched by `uv run python` with this exact
subprocess command:

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane73/.venv/bin/python -m pytest tests/integration/phase2/test_b03_discussion_hypothesis.py tests/integration/phase2/test_b04_manuscript_migration.py tests/integration/phase2/test_b05_review_migration.py tests/integration/phase2/test_b08_schema.py tests/integration/phase2/test_b14a_entry_schema.py tests/integration/phase2/test_b23_schema.py tests/integration/phase2/test_batch_c_migration.py tests/integration/phase2/test_batch_g_integration.py tests/integration/phase2/test_m1_schema.py tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_04_migration_coverage.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_pr2_17_authorship_schema.py tests/integration/phase2/test_revision_action.py tests/integration/phase2/test_b14_publication_ready.py tests/integration/phase2/test_b14_ready_schema.py tests/integration/phase2/test_b14_ready_replay.py tests/integration/phase2/test_b14_ready_concurrency.py --tb=short
```

Exact repair/strengthening commands:

```sh
UV_CACHE_DIR=/tmp/researchbase-m1-uv-cache uv run pytest 'tests/integration/phase2/test_b14a_entry_schema.py::test_fresh_upgrade_catalog_and_empty_downgrade[base]' 'tests/integration/phase2/test_b14a_entry_schema.py::test_fresh_upgrade_catalog_and_empty_downgrade[0061_b16_consent_withdrawal]' tests/integration/phase2/test_batch_g_integration.py::test_each_downgrade_restores_exact_predecessor_catalog --tb=short
UV_CACHE_DIR=/tmp/researchbase-m1-uv-cache uv run pytest tests/integration/phase2/test_m1_manuscript_reconsideration.py::test_s2_upgrade_downgrade_restores_exact_0074_catalog --tb=short
```

New tests include strict DTO/transport bounds, both purpose flows, unchanged
material correction, distinct approval and READY grant consumption, independence,
reused reconsideration, replay after write-role loss, changed/foreign replay,
complete cross-Publication coverage, invalid current versus stale old targets,
canonical read ordinals, direct SQL bypasses, upgrade/downgrade refusal and exact
restoration, actual backend waits, both commit orders, post-wait expiry and late
failure rollback of a complete candidate graph.

The final race run captured **18 actual PostgreSQL backend waits** and **6 expiry
records**. See [the raw witness extract](M1-S2-race-witnesses.txt). The expiry tests
prove transaction start and observed wait precede expiry, release follows expiry,
and final authorization follows release and denies; every denied command leaves
zero DecisionRecord and typed basis rows. Reconsideration/rejection and
successor/rejection races cover both commit orders for both purposes. Late
credential loss after basis insertion also rolls back the complete candidate.

Earlier development runs exposed a new PL/pgSQL variable/alias collision and a
PREPARE fixture missing its required consent condition; both were corrected.
The first unit run had 7 failures (6,236 passed): outdated head/route inventories (including the static acceptance test
that checks the head). Updating values/appending the authorized migration
and two routes yielded the passing 6,263-case final run above (including 17 new pinned HTTP/CLI mapping cases). An intermediate
S2 run had 4 test-import failures and 44 passes; its corrected final run is the
53-case acceptance above. The initial Unix-socket URL experiment hit an older
fixture's percent-interpolation error; all final runs use the inherited TCP
selector, without changing that fixture or production behavior.
