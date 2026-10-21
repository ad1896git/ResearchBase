# B23 first-slice implementation evidence — 2026-10-19

Status: reviewer repairs implemented and focused verification completed. The
owner-requested exact full check is **BLOCKED, not PASS**: static checks and its
changed-file pre-check passed, but the filesystem sandbox denied the script's
shared mutex operations before the six shards started. The blocked invocation
was interrupted with exit **130**. The reviewer's earlier full run remains
**11,126 passed, 1 failed** until the repaired full check can run outside this
restriction. No acceptance or Phase 2 gate is claimed.

## Implemented scope

The proposal has the exact approved status line. ADR-0019's bounded amendments
are implemented through the existing review, revision and correspondence
services. Novelty reviews bind an exact assessment ID/hash and its saved closure.
Issue-only NOVELTY_REASSESSMENT actions refer to a precommitted, usable direct
same-ClaimVersion replacement. Independent re-review links retain exact
correspondence and leave Issues OPEN. Decisions, NO_CHANGE, disposition and
scientific outcome changes remain unavailable for novelty concerns.

V2 material is separate from the seven legacy v1 action shapes. Saved v1 facts
and hashes remain unchanged. Exact reads and nested verification use one
lock-free REPEATABLE READ snapshot. B23 writes use one READ COMMITTED UoW with
literal N SHARE first, owning-table reservations, the prescribed advisory/row
order, post-wait live authorization, forced deferred checks and bounded retries.
Existing consumption/SERIALIZABLE protocols were not changed.

The only new migration is `0071_b23_novelty_review`, parent
`0068_b21_unresolved_capture`. It adds the two concrete indexed RESTRICT FKs and
material-version columns, replaces the prescribed CHECKs, and extends guard
dispatch. Preflight pins current legacy functions and dependent triggers;
downgrade restores those definitions exactly and refuses retained v2 history.
Existing migrations have no tracked edits. No canonical table, dependency or
infrastructure was added. Inventory/head updates retain existing entries.

## Substitutions and dispatch implementation

- CLI registration and the authenticated-root allowlist use existing `cli/app.py`;
  `cli/main.py` remains the entrypoint.
- The guide's `b06_revision_complete` is the existing trigger; its function is
  `b06_complete_revision()`. The existing re-review completion function is
  `b07_complete_re_review_fn()`.
- The existing router supplies `/v1` to the documented project route paths.
- `pr214_open_event` creates the initial OPEN event; Application code does not
  duplicate that effect.
- Section 4's B23 dispatch uses keyword-only `novelty=True` on the reused
  `record_concern_re_review` service method. Dedicated novelty adapters supply
  this invocation context before opening a UoW. The closed command DTO and
  transport inputs are unchanged. The chosen transaction verifies saved material
  version and never probes or falls back to another protocol. Legacy calls keep
  their default protocol. This resolves the earlier attempt's dispatch question;
  no separate owner decision is required by the approved text.

See [API/CLI contract](api-cli-contract.md) for the concrete surfaces.

## Read-only review findings and resolutions

Read-only sub-agents reviewed the approved specification, ADR, diff, migration,
transaction protocol and required cases; only the main agent wrote files.

| Finding | Severity | Resolution |
| --- | --- | --- |
| Preliminary link-dispatch SELECT introduced a second UoW and broke SHARE-first in both protocols | P1 MAJOR | Select explicit invocation protocol before SQL; verify stored version inside the selected transaction. Retain strong B23/B07 first-statement assertions. |
| Saved Issue verification missed parent timestamp equality and novelty-forbidden references | P1 MAJOR | Verify Issue parent/time, forbidden reference fields and initial-event closure on history reads/replay; injected corruption fails closed. |
| Corrupted saved action result could be reported as changed request material | P1 MAJOR | Verify saved action closure after entitlement/creator checks and before request comparison. Intact changed requests still conflict. |
| Required SQL/replay/concurrency cases were missing | P1 MAJOR | Add normal-role bypass/sealing, same-transaction result, legacy/zero capture, foreign scope, corruption, role-loss replay, lock waits, role/credential expiry, predecessor/correction-link, legacy governance overlap and rollback/retry cases. |
| CLI novelty show accepted legacy readbacks that API rejects | P2 MINOR | Apply the same exact Novelty DTO check and NOT_FOUND result in CLI. |

The earlier read-only reviews found no further production defect, but their
focused checks did not cover the later reviewer-reported checkpoint failure.
The repair and still-blocked full-check status are recorded below. The
new result-edge corruption test initially failed with IDEMPOTENCY_CONFLICT;
its required PROVENANCE_CLOSURE_VIOLATION assertion is preserved with the fix.
Earlier interrupted/failing development runs are not acceptance evidence.

## Verification environment

`UV_CACHE_DIR=/tmp/researchbase-b23-uv` keeps the uv cache inside the writable
sandbox without changing dependency definitions. PostgreSQL tests use disposable
real databases on **PostgreSQL 18.6 (Homebrew)** and normal SQL roles where specified. Development/scientific
history was not migrated for verification. Test warnings are reported below;
Pyright's available-version notice did not change pinned dependencies.

### Static checks

```sh
UV_CACHE_DIR=/tmp/researchbase-b23-uv uv run ruff format --check .
UV_CACHE_DIR=/tmp/researchbase-b23-uv uv run ruff check .
UV_CACHE_DIR=/tmp/researchbase-b23-uv uv run pyright
```

Observed: **746 files already formatted**; **All checks passed!**;
**0 errors, 0 warnings, 0 informations**.

### Unit and architecture checks

```sh
UV_CACHE_DIR=/tmp/researchbase-b23-uv uv run pytest -o addopts='' tests/unit tests/architecture tests/test_architecture.py -q --tb=short
```

Observed: **5,705 passed, 49 warnings**, 98.16 seconds.

The focused contract/hash/boundary command also ran:

```sh
UV_CACHE_DIR=/tmp/researchbase-b23-uv uv run pytest -o addopts='' tests/unit/phase2/test_b23_hash_vectors.py tests/unit/phase2/test_b23_novelty_review_contract.py tests/architecture/test_b23_novelty_boundaries.py -q --tb=short
```

Observed: **56 passed**, 0.80 seconds. These cases are included in the unit and
architecture total and must not be added to it as distinct coverage.

### B23 PostgreSQL suites

```sh
UV_CACHE_DIR=/tmp/researchbase-b23-uv uv run pytest -o addopts='' tests/integration/phase2/test_b23_*.py -q --tb=short
```

Observed: **96 passed, 103 warnings**, 170.02 seconds.

### Relevant PostgreSQL dependency regressions

```sh
UV_CACHE_DIR=/tmp/researchbase-b23-uv uv run pytest -o addopts='' tests/integration/phase2/test_pr2_14_internal_review.py tests/integration/phase2/test_pr2_14_conclusion_review.py tests/integration/phase2/test_pr2_15_decision.py tests/integration/phase2/test_pr2_15_coordination.py tests/integration/phase2/test_revision_action.py tests/integration/phase2/test_b06_*.py tests/integration/phase2/test_b07_*.py tests/integration/phase2/test_b08_*.py tests/integration/phase2/test_pr2_18_*.py tests/integration/phase2/test_b19_close_prior_art_*.py tests/integration/phase2/test_b21_capture*.py tests/integration/phase2/test_b22_prior_art_*.py -q --tb=short
```

Observed: **639 passed, 1,473 warnings**, 1,112.83 seconds. Warnings include
Alembic's existing `path_separator` deprecation and one SQLAlchemy
`execution_options ignored` warning in the legacy denied-target test.

### Touched PostgreSQL migration suites

```sh
UV_CACHE_DIR=/tmp/researchbase-b23-uv uv run pytest -o addopts='' tests/integration/phase2/test_b04_manuscript_migration.py tests/integration/phase2/test_b05_review_migration.py tests/integration/phase2/test_b14a_entry_schema.py tests/integration/phase2/test_batch_c_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_04_migration_coverage.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_pr2_17_authorship_schema.py -q --tb=short
```

Observed: **169 passed, 410 warnings**, 163.18 seconds.

### Observable cross-expiry evidence

```sh
UV_CACHE_DIR=/tmp/researchbase-b23-uv uv run pytest -o addopts='' tests/integration/phase2/test_b23_concurrency.py::test_post_target_wait_expiry_has_database_witness -q -s --tb=short
```

Observed: **6 passed, 6 warnings**, 24.15 seconds. The six
[captured database witnesses](cross-expiry-witnesses.json) cover all three
writers and both credential and database-role expiry. Each records transaction
start and observed wait before expiry, lock release/acquisition after expiry,
fresh authorization after acquisition, FORBIDDEN and zero new effects. Timestamp
offsets reflect the database/client sessions and identify the same instants.
These six cases also occur in the B23 suite; counts are not additive.

### Repository checks

```sh
UV_CACHE_DIR=/tmp/researchbase-b23-uv uv run alembic heads
git diff --check
git diff --numstat migrations/versions
```

Observed: exactly **0071_b23_novelty_review (head)**; no whitespace errors;
no edits to existing tracked migrations. No commit, push or branch creation.


## Reviewer repair: checkpoint and exact restoration

The required reproduction command was:

```sh
UV_CACHE_DIR=/tmp/researchbase-b23-uv uv run pytest tests/integration/phase2/test_pr2_20_migrations.py -k test_populated_conclusion_placement_review_and_0042_checkpoints
```

Before repair: **1 failed, 16 deselected, 6 warnings**, 1.99 seconds. This is a
reproducible B23 test compatibility regression, not a flake or a pre-existing
failure. The assertion compared a `SELECT *` JSON manifest from checkpoint 0042
against head. B23's authorized `novelty_assessment_id=NULL` and
`material_version=1` additions changed the row shape and therefore its manifest
hash, while the ten other table manifests were identical.

The repaired
[`test_populated_conclusion_placement_review_and_0042_checkpoints`](../../../tests/integration/phase2/test_pr2_20_migrations.py)
captures every original column at 0042 and uses the existing `manifest(columns=)`
projection before and after upgrade. It separately checks the complete legacy
review ID set and the two new values `(NULL,1)`. It retains scientific hashes,
all original fields/edges, Decision replay, and migration evidence comparisons.
No production code, accepted migration or scientific record was changed for
this repair.

Same reproduction command after repair: **1 passed, 16 deselected, 6 warnings**,
1.96 seconds.

The new
[`test_pinned_guard_definitions_restore_byte_for_byte`](../../../tests/integration/phase2/test_b23_schema.py)
compares complete UTF-8 `pg_get_functiondef` bytes against every `DISPATCH`
entry at head and every `LEGACY` entry after downgrade, repeats the
upgrade/downgrade, and checks exact dependent trigger and original CHECK
definitions. It performs no whitespace normalization and uses no hash-only
comparison. Trigger lookup is scoped to the five B23 owner/link tables, because
PostgreSQL allows the same trigger name on unrelated tables. The pre-existing
empty-roundtrip test did not provide this byte-level assertion.

The complete affected-file run was:

```sh
UV_CACHE_DIR=/tmp/researchbase-b23-uv uv run pytest -o addopts='' tests/integration/phase2/test_pr2_20_migrations.py tests/integration/phase2/test_b23_schema.py -q --tb=short
```

Observed: **37 passed, 85 warnings**, 49.06 seconds. This includes the new exact
restoration test and all 17 checkpoint/migration cases. The first development
run of the new restoration test exposed a test lookup ambiguity: an unrelated
approval table shares the `b10_no_basis_cycle` trigger name. Scoping the query
to B23's prescribed five owning/link tables resolves that ambiguity without
changing any installed SQL or weakening the definition comparisons.

## Guide-to-implementation map

Paths and symbols below identify the complete implementation even when a review
UI truncates the large migration. The first four groups cover every DDL/guard
item in guide §12.1 and the lock/isolation/error inventories in §§7, 11.2, 12.2.

### DDL, guard dispatch and downgrade (§12.1)

All SQL entries below are in
[`0071_b23_novelty_review.py`](../../../migrations/versions/0071_b23_novelty_review.py).
No other migration is changed or added for this repair.

| Guide item | Exact implementation location | Verification |
| --- | --- | --- |
| One forward migration after the actual head; no new table | `revision`, `down_revision`, `DDL`, `upgrade()` | `test_no_new_table_or_domain_adapter_import`; Alembic head check |
| `internal_review_records.novelty_assessment_id UUID`, concrete RESTRICT FK, `SMALLINT NOT NULL DEFAULT 1` version, index | `DDL`: `fk_b23_review_novelty`, `ix_b23_review_novelty` | `test_catalog_and_empty_roundtrip`; populated v1 upgrade and repaired checkpoint test |
| Review XOR and novelty-only v2 admission | `DDL`: drop `ck_pr214_one_target`, add `ck_b23_review_target` and `ck_b23_review_version` | `test_normal_sql_review_bypass_and_deferred_sealing` |
| `revision_actions.result_novelty_assessment_id UUID`, concrete RESTRICT FK, version default, index | `DDL`: `fk_b23_result_novelty`, `ix_b23_result_novelty` | `test_catalog_and_empty_roundtrip`; legacy RevisionAction catalog regression |
| NOVELTY_REASSESSMENT fits existing VARCHAR(32); issue-only/null Decision; exactly one novelty result and seven null legacy results | `DDL`: `ck_b23_revision_shape`, v2 branch | `test_normal_sql_revision_bypass_denied`; separate novelty command DTO |
| Seven v1 shapes unchanged; preserve both predecessor uniqueness constraints | `DDL`: `ck_b23_revision_shape`, v1 branch; neither `uq_revision_action_predecessor` nor `uq_pr218_novelty_predecessor` is replaced | `test_v1_shape_cross_product_equivalent`; correction/no-fork tests |
| READ COMMITTED and actual N SHARE locks required, no transaction-local flag proof | `SQL`: `b23_prelocked()` uses actual PostgreSQL lock inventory through `pr218_capture_prelocked()` | normal-role SQL bypass tests; fixed inventory/first-statement tests |
| Exact novelty review target/hash/project, frozen Claim closure, historical reviewer eligibility and bounds | `SQL`: `b23_review_hash`, `b23_check_review`, `b23_review_guard`; trigger `trg_b23_review_guard` | exact review, independence, corruption and normal-role review tests |
| Parent/Issue/event deferred completeness; ordered 0–100 Issues, exact OPEN actor/time | `SQL`: `b23_complete_review`, `b23_complete_review_record`, `b23_complete_review_issue`, `b23_complete_review_event`, `b23_is_novelty_review`, `b23_is_novelty_issue` | deferred ordinal sealing, atomic OPEN-event and corruption tests |
| Late Issue/event INSERT dispatch; native transaction-ID sealing; no novelty disposition | `DISPATCH`: `pr214_issue_guard`, `b08_event_guard`; native `xmin=pg_current_xact_id()::xid` checks | `test_normal_role_late_issue_and_disposition_denied`; saved Issue closure tests |
| Exact precommitted, usable, direct same-Claim replacement; OPEN Issue; same-basis predecessor/no fork; v2 hash | `SQL`: `b23_action_hash`, `b23_validate_revision`, `b23_revision_guard`, `trg_b23_revision_guard` | same-transaction SQL denial; unusable/wrong result; predecessor competition |
| Deferred revision completeness and legacy B06/B07 dispatch | `SQL`: `b23_complete_revision`, `b23_complete_revision_action`; `DISPATCH`: `pr215_revision_guard`, `b06_complete_revision` | normal-role action tests and legacy B06/B07 regressions |
| Exact result-target re-review/hash, original concern, different independent HUMAN reviewer, attribution/time, immutable link | `SQL`: `b23_validate_re_review`; `DISPATCH`: `b07_validate_re_review`, `b07_re_review_guard`, `b07_complete_re_review_fn`; existing immutable link trigger retained | `test_normal_sql_link_guards_and_immutable_correspondence`; re-review and correction/link races |
| Immutable UPDATE/DELETE remains denied for review/action/Issue/link history | `DISPATCH`: legacy immutable branches retained; `TRIGGERS` inventories immutable review/event/action/link guards | normal-role mutation tests and existing B06/B07 suites |
| Saved nested coverage, comparison, resolution and novelty material/hash dispatch | `SQL`: `b23_resolution_hash`, `b23_verify_capture`, `b23_coverage_hash`, `b23_prior_hash`, `b23_assessment_hash`; `b23_dependencies` for admission counting | v1/v2 capture, Python/SQL hashes, saved-history corruption tests |
| Expected legacy functions and dependent trigger preflight; no SECURITY DEFINER | `LEGACY`, `TRIGGERS`, `upgrade()` exact-definition digest comparison and trigger dictionary equality; all helpers use caller privileges | successful upgrade plus exact restoration test |
| Downgrade first ACCESS EXCLUSIVE owner/link locks; refuse any v2 review/action or corresponding link; preserve history | first two statements of `downgrade()`; existence checks do not delete rows | populated downgrade refusal; empty roundtrip |
| Restore replaced legacy functions/CHECKs exactly; remove only B23-owned additions | `downgrade()` replays `LEGACY`, drops owned functions/triggers/columns, then `LEGACY_REVIEW_TARGET` and `LEGACY_SHAPE` | `test_pinned_guard_definitions_restore_byte_for_byte` compares full definitions against pins and checkpoint CHECKs |

### Transaction and lock inventory (§§7, 12.2)

| Guide item | Exact implementation location | Verification |
| --- | --- | --- |
| Fixed lexical tuple N, owning-table exclusions, no catalog discovery | [`novelty_repository.N`](../../../src/researchbase/persistence/novelty_repository.py); [`internal_review_repository.B23_SNAPSHOT_TABLES = N`](../../../src/researchbase/persistence/internal_review_repository.py) | `test_fixed_inventory_and_first_statement` pins tuple equality/order and exclusions |
| Before SQL: READ COMMITTED; literal N SHARE FIRST | `SqlAlchemyInternalReviewRepository.prepare_novelty_write()` calls `connection(execution_options={isolation_level: READ COMMITTED})`, then the literal LOCK | `test_first_statement_all_writers_and_lock_free_reads`; `test_fixed_snapshot_inventory_wait_is_first_for_each_writer` |
| Own-table ROW EXCLUSIVE, then 10s/30s SET LOCAL, then request advisory | same `prepare_novelty_write()`: review owners `internal_review_records,review_issue_events,review_issues`; revision owner `revision_actions`; link owner `revision_action_re_reviews` | SQL traces plus fixed order architecture assertion |
| Review request key `pr214:review:{derived_review_id}`; Claim FOR UPDATE before assessment FOR SHARE | [`InternalReviewService._create_novelty`](../../../src/researchbase/application/internal_review.py), repository `lock_novelty_targets()` | review first-statement, same-key replay, legacy review overlap and cross-expiry cases |
| Revision request key `pr215:revision:{id}`; Claim, sorted assessments, original review, Issue, optional predecessor FOR UPDATE | [`RevisionActionService._record_novelty_once`](../../../src/researchbase/application/revision_action.py); `lock_novelty_targets()`; [`SqlAlchemyRevisionActionRepository.lock_novelty_basis`](../../../src/researchbase/persistence/revision_action_repository.py) | revision first-statement, predecessor competition, correction/evidence/retraction waits |
| Link key `b23:re-review:{action_id}:{review_id}`; Claim, sorted assessments/reviews, Issue, action FOR SHARE | `RevisionActionService.record_concern_re_review(..., novelty=True)`, `_record_correspondence_once`, `_record_novelty_link_once`; both repository lock helpers above | command-wide first-statement trace; action correction versus link in both orders; legacy B07 first-statement regression |
| Resolve exact IDs before target locks without foreign disclosure; reread after waits | the three Application writer methods above; `b23_validate_revision` and `b23_validate_re_review` repeat saved observations after locks | foreign scope tests and observed PostgreSQL waiter tests |
| Fresh post-lock and pre-commit authorization; half-open role/credential intervals | `_novelty_authorize()` delegates to owning `NoveltyService._authorize`; all three writers call again after readback | six captured database/credential expiry witnesses, all with zero effects |
| Force deferred checks before readback/commit | `force_novelty_constraints()` executes `SET CONSTRAINTS ALL IMMEDIATE`; invoked by all three writers | SQL sealing and failure-injection rollback tests |
| Retry fresh UoWs at most three attempts for 40001/40P01 only | writer loops in `_create_novelty`, `record_novelty_revision`, `record_concern_re_review`; [`SqlAlchemyUnitOfWork._command_database_error`](../../../src/researchbase/persistence/uow.py) marks only those SQLSTATEs retryable | `test_failures_rollback_all_effects_and_retry_only_allowed_states`; unit bounded dispatch tests |
| Unique predecessor race is nonretryable CONCURRENT_MODIFICATION | UoW maps `23505` only when constraint is `uq_revision_action_predecessor`; `retryable_b23=False` | predecessor competition/no-fork and normalization branches |
| 55P03/57014, connection/unknown commit are not automatic retries | B23 UoW fallback raises sanitized infrastructure failure; writer loops require explicit retry flag | timeout rollback case; exact replay tests |
| All exact/history/link reads: one read-only REPEATABLE READ, no table/advisory/row locks | UoW `begin_formal_read()` and `configure_revision_transaction(readonly=True)`; snapshot adapters from `enable_revision_action_snapshot_reads()`; `InternalReviewService.read`, `RevisionActionService.read_revision_action`, `read_novelty_re_review`; owning `NoveltyService.verify_assessment_in_uow` | exact reads finish while conflicting writer locks are held; emitted-statement lock prohibition |
| Legacy protocols and SERIALIZABLE consumption unchanged | explicit pre-UoW link protocol selection preserves legacy writer branch; consumption services and their transaction configuration have no diff | legacy review/Decision/B06/B07/B08 regressions and final whole-suite check |

### Material and adapter boundaries (§§11, 12.3)

| Guide item | Implementation |
| --- | --- |
| Separate exact v2 review and action payloads, all v1 bytes unchanged | [`domain/internal_review.review_material`](../../../src/researchbase/domain/internal_review.py) version dispatch; [`domain/revision_action.novelty_revision_material`](../../../src/researchbase/domain/revision_action.py) separate from the seven-shape builder; pinned independent digest vectors in `test_b23_hash_vectors.py` |
| Closed commands/readbacks, saved closure verification in caller UoW, historical/current split and admission cap | `application/internal_review.py` and `application/revision_action.py` typed DTOs and novelty validators; `application/novelty.py::verify_assessment_in_uow`; `application/ports.py` repository ports |
| Thin authenticated HTTP/CLI routes, exact variant parity, no direct persistence access | [`api/routes.py`](../../../src/researchbase/api/routes.py), `api/app.py`; [`cli/commands/governance.py`](../../../src/researchbase/cli/commands/governance.py), `cli/composition.py`, existing `cli/app.py` registration substitution; [API/CLI contract](api-cli-contract.md) |

### Error mapping inventory (§11.2)

Transport mappings are the existing dictionaries
[`api/errors.py::_STATUS`](../../../src/researchbase/api/errors.py) and
[`cli/errors.py::CLI_EXIT_CODES`](../../../src/researchbase/cli/errors.py).
B23 SQL normalization is `persistence/uow.py::_command_database_error` under
`enable_b23_error_normalization()`. Saved dependency failures normalize through
`application/saved_provenance.py::saved_dependency`; broken saved frozen closure
therefore fails PROVENANCE_CLOSURE_VIOLATION, rather than being readmitted as a
new draft target. Existing legacy frozen-target error mappings remain intact.

| Code | HTTP / CLI | Application or SQL normalization location |
| --- | --- | --- |
| AUTHENTICATION_REQUIRED | 401 / 3 | Trusted-principal checks on create, revision, link and exact read entrypoints |
| FORBIDDEN | 403 / 3 | `_novelty_authorize`, scoped exact lookups and replay creator/reviewer checks; SQL `P23A1` |
| CONFLICT_OF_INTEREST | 403 / 3 | `_novelty_independence`, `_novelty_link_inner`; SQL `P23C1` |
| VALIDATION_ERROR | 422 / 2 | Closed DTO/text/enum/UUID/admission-cap validators; SQL `P17D4` and CHECK `23514` |
| NOT_FOUND | 404 / 3 | Entitled missing exact rows; `_absent`, `verify_assessment_in_uow`, dedicated API/CLI variant checks |
| REVIEW_TARGET_NOT_FROZEN | 409 / 4 | Existing `InternalReviewService` target admission and `P17E2` legacy normalization; no assessment freeze state is fabricated |
| FROZEN_REFERENCE_REQUIRED | 409 / 5 | Owning Claim/source and completed-result admission validators; saved dependency normalization fails closed for corrupt historical closure |
| INVALID_STATE_TRANSITION | 409 / 4 | `_novelty_action_inner(admission=True)`, `_novelty_link_inner(admission=True)`, deferred novelty Decision/disposition/legacy-result paths; SQL `P17D2` |
| DECISION_BASIS_INVALID | 409 / 4 | Existing `_effective_issue`, `_supported` and supplied-Decision exact-basis checks; no novelty Decision DTO field added |
| PROVENANCE_CLOSURE_VIOLATION | 409 / 5 | Review/action/link saved version/hash/edge verification; SQL `P17F2`, `P17D3`; saved dependency normalization |
| IDEMPOTENCY_CONFLICT | 409 / 4 | Verified saved material compared with same actor/request command and ordered normalized Issues |
| IMMUTABLE_RECORD | 409 / 4 | SQL `P17F1`, `P17E1`, `P17D1` immutable and late-insert guards |
| REFERENTIAL_INTEGRITY_ERROR | 409 / 5 | SQL `23503` concrete FK normalization |
| CONCURRENT_MODIFICATION | 409 / 4 | SQL `40001`, `40P01`, or named unique predecessor `23505`; retries bounded as above |
| INTERNAL_ERROR fallback | 500 / 1 | Unknown/timeout/connection/uncertain-commit infrastructure failures sanitized by existing API/CLI exception handlers; no new ErrorCode |

## Owner-requested full check after repair

The later reviewer-repair instruction explicitly authorizes this whole-suite
invocation, superseding the original focused-only restriction. The environment
exports `UV_CACHE_DIR=/tmp/researchbase-b23-uv`; the check itself is exactly:

```sh
uv run pyright && uv run ruff format --check . && uv run ruff check . && git diff --check HEAD && /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/full_suite_sharded.sh 6
```

Observed before the environmental block:

- Pyright: **0 errors, 0 warnings, 0 informations**.
- Ruff format: **746 files already formatted**.
- Ruff lint: **All checks passed!**.
- `git diff --check HEAD`: no errors.
- Script changed-file pre-check: **469 passed, 796 warnings**, 461.94 seconds;
  the script reported **33 changed test files**.

The script then failed to manage its shared lock outside this repository:

```text
rm: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/full_suite.lock/pid: Operation not permitted
rm: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/full_suite.lock: Operation not permitted
```

It remained in its mutex-acquisition loop and was interrupted, returning
**exit 130**. The six-shard stage **did not start**, so there is no new full-suite
pass count and the exact check is **not green**. This is a filesystem-sandbox
restriction on `.pipeline/logs`, not a demonstrated test failure. Session
permissions allow writes only in the lane repository and temporary roots,
with approval/escalation disabled. The external script, shared lock files,
other lanes and governing Harness files were not modified to bypass this
restriction. The exact command requires an execution context that can manage
its configured shared mutex. No commit, push or branch creation occurred.

The checkpoint failure itself is repaired and independently passes as recorded
above; the remaining P1 full-check requirement is still open solely because
this invocation could not reach the sharded tests.
