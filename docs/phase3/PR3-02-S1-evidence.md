# PR3-02-S1 implementation evidence

Scope: owner-authorized ADR-0023 S1 and its frozen execution pack, including the
2026-10-21 enrollment-locking amendment. No S2 execution, promotion, worker,
provider, gateway or policy schema was added. Existing B02 promotion commands
are exercised as regression evidence; they are not S2 implementation.

Migration `0079_agent_identity_versions` temporarily has
`down_revision = '0077_research_task_graph'`, as explicitly directed for this
lane. The sole head is 0079. PR3-04 / 0078 is absent from this branch. The director
must re-parent the revision to accepted `0078_task_safety_policies` at integration
(values only). No accepted migration or document Status line was changed.
No upgrade-through-0078 or PR3-04 policy-preservation result is claimed here.

The frozen pack records two director reviews and the ADR amendment. Those are
contract reviews, not an independent review of this implementation. Independent
implementation review and integration acceptance remain pending. No Phase 3 GO,
AQ-S3-08 closure or production mTLS readiness is asserted.

## Delivered behavior

- Four exact S1 tables, 17 explicit indexes, eight new invoker-rights functions,
  14 new triggers, the replacement binding-trigger target, and the narrow
  membership-event predicate extension. The existing HUMAN challenge function
  and trigger remain intact. Downgrade refuses before DDL or revision change.
- Immediate child guards use `xmin = pg_current_xact_id()::xid`; only the receipt
  root has a new deferred whole-state check. Versions, receipts and events reject
  no-op UPDATE and DELETE. Configuration scope and version hashes are checked
  independently by PostgreSQL.
- Closed immutable commands, results, proof values and ordered HarnessManifest;
  all three literal request-hash vectors. Immutable version material excludes
  the version record ID, creation metadata and current availability as specified.
- Application/UoW/repository boundaries, additive identity enrollment/resolution,
  exact version reads, HTTP routes and `agents` CLI commands. SQL is confined to
  persistence adapters. Receipts supply database time; returned timestamps and
  copied command timestamps are normalized to aware UTC.
- Required lock prefixes, scoped advisory/actor/availability locks, current
  entitlement checks, historical replay, CAS, bounded whole-transaction retry and
  uncertain-commit reconciliation. Server-generated IDs survive retries.
- Default-deny enrollment, mTLS and retained-pin ports. Deterministic test adapters
  bind complete enrollment intent; pin tests resolve retained files and verify
  configuration bytes before database locks. Production verifier intake is
  **pending/blocked**, not satisfied by these adapters. No credentials or runtime
  dependencies were added.

## Initial delivery: environment and focused checks

Observed PostgreSQL: **18.6 (Homebrew)**; Python 3.12.15; pytest 8.4.2. New database
fixtures create/drop random disposable databases through `RB_TEST_ADMIN_URL`.
Normal command and adversarial DML connections use a NOSUPERUSER role with DML
permissions and enabled triggers. Privileged connections only provision/clean up
fixtures and inspect lock waits. Files produced by the new tests live under
pytest temporary paths, including retained pins and content-addressed bytes.

Commands below were executed from the repository root. Output was redirected to
session-local `/tmp/302-*.log` files; the commands shown are the executed programs
and arguments, without the redirection. No whole-suite run was performed.

| Exact command | Observed result |
| --- | --- |
| `.venv/bin/ruff check .` | Exit 0; All checks passed! |
| `.venv/bin/ruff format --check .` | Exit 0; 861 files already formatted |
| `.venv/bin/pyright` | Exit 0; 0 errors, 0 warnings, 0 informations |
| `.venv/bin/alembic heads` | `0079_agent_identity_versions (head)` |
| `.venv/bin/pytest -o addopts='' -ra tests/unit/phase3 tests/architecture` | **598 passed**, 50 warnings, 39.99 s; no failures/skips |
| `.venv/bin/pytest -o addopts='' -ra tests/integration/phase3` | **253 passed**, 106 warnings, 119.71 s; no failures/skips |
| `.venv/bin/pytest -o addopts='' -ra tests/integration/phase2/test_pr2_00_*.py tests/integration/phase2/test_b02_*.py tests/integration/phase2/test_b03_*.py` | **207 passed**, 430 warnings, 313.47 s; no failures/skips |
| `.venv/bin/pytest -o addopts='' -ra tests/integration/phase3/test_pr3_02_s1_application.py tests/integration/phase3/test_pr3_02_s1_identity.py tests/integration/phase3/test_pr3_02_s1_b02_agent.py` | **34 passed**, 34 warnings, 49.83 s; post-review repository-boundary check, before final UTC normalization |
| `.venv/bin/pytest -o addopts='' -ra tests/integration/phase3/test_pr3_02_s1_migration.py` | **3 passed**, 8 warnings, 4.59 s; includes strengthened populated-0077 preservation case |
| `.venv/bin/pytest -o addopts='' -q -s tests/integration/phase3/test_pr3_02_s1_concurrency.py tests/integration/phase3/test_pr3_02_s1_schema.py::test_one_deferred_whole_state_firing_per_command` | **8 passed**, 8 warnings, 12.68 s; observations below |
| `git diff --check` | Exit 0 |

Warnings in pytest runs are the existing Alembic `path_separator` deprecation.
Pyright's separate installed-version update notice is not a type-check warning.
The supplemental counts overlap the required subsets and must not be summed.

## Concrete observations

Enrollment first and second Application statements, captured for both workers in
both same-project and different-project tests:

```sql
LOCK TABLE actor_subject_bindings, actors, project_membership_events,
  project_memberships, project_role_assignments IN SHARE ROW EXCLUSIVE MODE;
LOCK TABLE projects IN SHARE MODE;
```

Each worker attempted the prefix once. Both committed after an observed real
lock wait, without 40P01 or transaction retries. Measured completion after holder
release was 0.050897249951958656 s (same project) and 0.056017625029198825 s
(different projects) in the supplementary observation run. These measurements
are test observations, not a performance guarantee. The enrollment/version race
observed the version command waiting at its first eight-table SHARE statement.
CAS racing produced exactly one accepted change and one stale-revision denial.

The root-function test samples PostgreSQL function-call counters before and
after forcing constraints: each provision/register command adds exactly one
`pr302_receipt_complete` call; forcing constraints again adds zero. The test
measures differences because backend statistics can include pending prior calls.
No child has a new deferred whole-state trigger.

Observed credential expiry during the actual first enrollment lock wait (all
samples are database timestamps, displayed with the connection's -04:00 offset):

| Credential | Transaction start | Lock wait start | Expiry | Lock acquired | Authorization checked | New receipts |
| --- | --- | --- | --- | --- | --- | --- |
| Subject | 09:40:19.974072 | 09:40:19.974238 | 09:40:20.369436 | 09:40:20.384409 | 09:40:20.396692 | 0 |
| Operator | 09:40:22.323230 | 09:40:22.323319 | 09:40:22.717657 | 09:40:22.726836 | 09:40:22.738200 | 0 |
| Owner | 09:40:24.519291 | 09:40:24.519460 | 09:40:24.913528 | 09:40:24.918548 | 09:40:24.930278 | 0 |

Date: 2026-10-21. Test instrumentation samples lock acquisition after the complete
required table-lock prefix and before authorization. Expiry is observed before
releasing the holder. Assertions establish transaction/wait start < expiry <=
lock acquisition <= authorization, and zero protected receipts after denial.

Normal-role non-ASCII parity uses Application-enrolled AGENT and retained pins
`café-研究@1.0.0`, `modèle-模型@1.0.0`, `outils-策略@1.0.0`. PostgreSQL
`pr216_cjson(...).encode('utf-8')` equals Python `canonical_json_bytes`;
`pr216_hash` equals Python `sha256_canonical_json` and persisted version hash.
The owning configuration hash is copied without inventing an ArtifactVersion
hash-scheme field.

Application-only B02 evidence provisions the Agent through
`Phase2IdentityService.provision_project_agent`, resolves the trusted MTLS subject
to the existing VerifiedPrincipal, captures the native strategy, then promotes
both question and hypothesis candidates through existing B02 Application
commands. Saved creator/capture IDs are the enrolled Agent. B03 denies that
principal. No SQL-forged AGENT, binding, membership or execution is used.

Replay retains original IDs/revision/time after retirement and project archive;
changed material conflicts, revoked read entitlement denies, and uncertain
commit reconciles the original receipt. Injected failure after each enrollment
and registration flush rolls back all new state. Retry tests observe three whole
attempts for 40001/40P01 and one for 55P03/57014, stable IDs/material, resampled
receipt times and zero durable effects on failure.

Empty/populated migration tests prove refusal without revision/catalog changes.
The populated 0077 -> 0079 test compares every pre-existing row, retained frozen
search-plan readback and ResearchTask graph; exactly four tables are added and
execution remains disabled. Historical PR3-01 upgrade assertions remain pinned
to 0077 while repository-head assertions track 0079.

## Development failures and fixture incident

Intermediate failures were corrected before the final checks: a PL/pgSQL CASE
syntax error; a heterogeneous-trigger record-field lookup; obsolete head/table
count expectations; a SQL DELETE test statement; unavailable normal-role lock
inspection; and a function-counter assertion that needed to subtract its
baseline. Missing receipt results correctly raised native FK 23503 before the
root constraint check; that assertion now checks the native FK diagnostic.

An early new fixture failed to set `DATABASE_URL` to its disposable URL before
Alembic. Because the migration environment gives that variable precedence over
Config, the corrected-syntax attempt advanced the preconfigured test database
**`researchbase_lane102` to 0079**, then failed when bootstrap found no tables in
the separate empty disposable database. The fixture now sets its disposable URL
before migration. Successful new-test runs use random disposable databases.
Read-only inspection confirmed the configured lane test DB is at 0079. At initial delivery, no
rollback, schema deletion or repair was attempted: 0079 is forward-only. The
reviewer subsequently authorized the disposable lane DB reset recorded below. No production database use is claimed.

## Review and integration limits

The implementation was self-reviewed against the pack, SQL diff and focused
results. This is not independent implementation-review evidence. Production
verifier intake, independent review and director re-parenting remain explicit
integration/acceptance work. No forward repair is implemented or claimed approved.
Full-suite verification belongs to the external check loop. No branch, commit
or push was created. Stop at S1.

## Reviewer remediation (2026-10-21)

The reviewer reported the required check exiting **1 with 11 full-suite failures**.
The earlier 598/253/207 targeted counts above did **not** establish full-suite
acceptance. The reviewer did not provide the original full-suite passed count,
so none is inferred. This section records the remediation and supersedes any
interpretation of the initial delivery as a full-suite PASS.

### Findings and concrete fixes

All eleven reported nodes were rerun together: **11 passed, 14 warnings in
19.17 s**, exit 0. No reported failure is dismissed as pre-existing. Historical
migration byte/hash assertions remain enforced; only authorized child/head pins
and current-surface expectations changed.

| Reported failing node | Resolution |
| --- | --- |
| `tests/unit/test_pr15_http.py::test_openapi_has_exact_frozen_v1_surface_and_is_reproducible` | Add exactly the four S1 agent paths to the exhaustive expected surface. |
| `tests/unit/test_pr15r_route_contract.py::test_all_63_routes_have_exact_schema_operation_and_application_bindings` | Track 113 operations (109 + 4), their exact request/response schemas, operation IDs, endpoint module and shared Application decoder/execution binding. Add typed AgentCommandResult/AgentVersionDTO response models to the four routes. |
| `tests/unit/test_task12_migration_history.py::test_task12_preserves_every_historical_migration_byte_and_exact_child` | Admit only migration 0079 as the additional authorized child and pin the sole head to 0079; preserve every historical SHA-256 assertion. |
| `tests/unit/test_batch_c_migration_history.py::test_batch_c_linear_history_and_frozen_lane_sql` | Append 0079 after 0077 in the exact linear chain, retaining frozen Batch C SQL digests. |
| `tests/unit/test_ci_migration_head.py::test_ci_migration_head_assertion_matches_repository_head` | Update CI's exact current-revision assertion to `0079_agent_identity_versions (head)`. |
| `tests/unit/phase2/test_pr2_04_r8a_host_topology.py::test_r8a_actual_migration_graph_and_frozen_bytes` | Pin current head 0079 / temporary parent 0077; retain frozen R8A migration bytes and historical applicability checks. |
| `tests/unit/phase2/test_pr2_04_static_acceptance.py::test_candidate_static_gates_and_inherited_formatter_delta` | Update the authorized head in `phase2_static_baseline.json`; leave the historical baseline commit and zero-diagnostic/formatter requirements intact. |
| `tests/unit/phase2/test_pr2_20_inventory.py::test_inventory_resolves_actual_source_lock_modes_and_unversioned_api` | Update the computed inventory's terminal revision expectation to 0079. Add separate S1 assertions for the five-table SHARE ROW EXCLUSIVE enrollment prefix and eight-table version SHARE inventory, preserving the adapter/dependency-lock inventory checks. |
| `tests/integration/phase2/test_pr2_20_migrations.py::test_populated_source_evidence_conclusion_placement_review_decision_head_noop` | Start the head-no-op catalog comparison at 0079, then repeat upgrade to head. Actual populated 0077 -> 0079 row/hash/graph preservation remains tested separately by the S1 migration suite. |
| `tests/integration/phase2/test_pr2_04_execution_migration.py::test_pr2_04_upgrade_adds_exact_tables_and_unique_head` | Preserve the historical 0024 upgrade/table assertion; update only the repository's sole-head expectation to 0079. |
| `tests/integration/test_pr02_application.py::test_create_and_get_actor` | Diagnose the original AGENT fixture below. Preserve HUMAN round-trip coverage and add explicit generic-AGENT enrollment-bypass rejection. Normalize `pr302_scope` to existing FORBIDDEN for legacy UoW callers as well as S1 callers. |

Adding response models exposed two incomplete fake-service results in
`test_agent_version_transports.py`: the first controls run had **28 passed,
2 failed in 4.82 s**. Those fake results now return complete immutable
AgentCommandResult values instead of two-field dictionaries. The corrected
controls run passed **all 30 tests**; HTTP/CLI equality is still checked.

### Actor baseline comparison and root cause

Base is **`c7447ed803b5406de97b82bdc404a02d342d5868`** (documentation freeze,
0077 head). `git archive HEAD` was extracted into
`/tmp/rb-pr302-base-kf17zqsg`; no branch, checkout, commit or historical file was
changed. Base and branch each received a separately created random disposable
PostgreSQL database, migrated with that source tree's own Alembic history.
`PYTHONPATH` selected the matching tree's `src`, and `UV_PROJECT_ENVIRONMENT`
selected the existing dependency environment.

Executed comparison driver:

```sh
PYTHONPATH=src:. .venv/bin/python /tmp/302-review-baseline.py
```

Its exact test subprocess in each source tree was:

```sh
uv run --no-sync pytest -o addopts='' -ra tests/integration/test_pr02_application.py::test_create_and_get_actor
```

Observed: **base 1 passed**, exit 0; **original branch 1 failed**, exit 1.
The same original branch failure was reproduced on the ambient lane DB before
reset. PostgreSQL's cause was `CheckViolation: fresh actor receipt required`,
raised by `pr302_identity_insert_guard`, not a HUMAN identity/proof failure.
The original test passed **ActorType.AGENT with an external key** to generic
`create_actor`. That is incompatible with S1's mandatory enrollment receipt and
fresh AGENT/external_key-NULL contract. Removing the guard would violate the
frozen pack. The legacy round-trip now explicitly requests HUMAN and still
checks exact readback/type/revision. A separate test proves generic Agent
creation cannot bypass enrollment and returns FORBIDDEN. Positive Agent
creation remains covered by Application-only S1 enrollment and B02 evidence.

After resetting the lane DB, this exact requested command passed **1 test in
0.51 s**, exit 0:

```sh
uv run pytest tests/integration/test_pr02_application.py::test_create_and_get_actor
```

The subsequent control run covered all six tests in the legacy actor module,
including HUMAN/project/workspace behavior, duplicate SERVICE external keys and
the new unreceipted-AGENT denial.

### Sanctioned lane database reset

The reviewer explicitly authorized this reset. Followed only the disposable DB
portion of the existing `.pipeline/bin/lane_run.sh` procedure: DROP the named
lane test database, CREATE it again, and run Alembic upgrade head. The lane
runner itself was not executed (it also replaces checkouts), and no accepted
migration was downgraded or edited.

Executed `.venv/bin/python /tmp/302-review-reset.py`. That script verified the
configured name was exactly `researchbase_lane102`, admin DB was local
`postgres`, caller/host/port matched, and there were **zero active lane DB
connections** before executing:

```sql
DROP DATABASE researchbase_lane102;
CREATE DATABASE researchbase_lane102;
```

It then executed `uv run alembic upgrade head`, exit 0. Database OID changed
from **121645080** to **236705964**. Reconnection confirmed
`0079_agent_identity_versions`. All eleven reported tests, including both
migration integration tests, were rerun after this reset. Their own migration
fixtures also use independent disposable databases. No production DB or other
lane was reset. This completes follow-up of the original fixture incident.

### Exact remediation verification commands

`uv` initially could not open its default cache outside the writable roots
(exit 2, before test collection). Subsequent invocations use the supported
writable-cache setting:

```sh
export UV_CACHE_DIR=/tmp/rb-pr302-review-uv-cache
```

Exact eleven-node rerun (exit 0, **11 passed / 14 warnings / 19.17 s**):

```sh
uv run pytest -o addopts='' -ra tests/unit/test_pr15_http.py::test_openapi_has_exact_frozen_v1_surface_and_is_reproducible tests/unit/test_pr15r_route_contract.py::test_all_63_routes_have_exact_schema_operation_and_application_bindings tests/unit/test_task12_migration_history.py::test_task12_preserves_every_historical_migration_byte_and_exact_child tests/unit/test_batch_c_migration_history.py::test_batch_c_linear_history_and_frozen_lane_sql tests/unit/test_ci_migration_head.py::test_ci_migration_head_assertion_matches_repository_head tests/unit/phase2/test_pr2_04_r8a_host_topology.py::test_r8a_actual_migration_graph_and_frozen_bytes tests/unit/phase2/test_pr2_04_static_acceptance.py::test_candidate_static_gates_and_inherited_formatter_delta tests/unit/phase2/test_pr2_20_inventory.py::test_inventory_resolves_actual_source_lock_modes_and_unversioned_api tests/integration/phase2/test_pr2_20_migrations.py::test_populated_source_evidence_conclusion_placement_review_decision_head_noop tests/integration/phase2/test_pr2_04_execution_migration.py::test_pr2_04_upgrade_adds_exact_tables_and_unique_head tests/integration/test_pr02_application.py::test_create_and_get_actor
```

Additional final checks (overlapping counts, not additive):

| Exact command | Observed result |
| --- | --- |
| `uv run pytest -o addopts='' -ra tests/integration/test_pr02_application.py tests/unit/phase3/test_agent_version_transports.py tests/unit/phase2/test_pr2_20_inventory.py` | **30 passed**, no failures/skips/warnings, 3.98 s; exit 0 |
| `uv run pytest -o addopts='' -ra tests/unit tests/architecture` | **6742 passed**, 55 warnings, 146.87 s; exit 0 |
| `uv run pytest -o addopts='' -ra tests/integration/phase3` | **253 passed**, 106 warnings, 107.32 s; exit 0 |
| `uv run pyright` | 0 errors, 0 warnings, 0 informations; exit 0 |
| `uv run ruff format --check .` | 861 files already formatted; exit 0 |
| `uv run ruff check .` | All checks passed!; exit 0 |
| `git diff --check HEAD` | Exit 0 |

### Required full-suite chain: BLOCKED, not PASS

Attempted the exact requested chain twice, including after correcting the
response fixtures:

```sh
uv run pyright && uv run ruff format --check . && uv run ruff check . && git diff --check HEAD && /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/full_suite_sharded.sh 6
```

Both attempts completed all four static stages successfully. The runner printed:

```text
== quick pre-check skipped: 108 changed test files (> 25)
rm: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/full_suite.lock/pid: Operation not permitted
rm: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/full_suite.lock: Operation not permitted
```

The first attempt also encountered the same denial for `full_suite.lock2`.
The runner could not acquire/clean its shared mutex and remained in its queue
loop. Both blocked attempts were interrupted; the execution tool reported
**exit 1**, with **no shard pytest run or full-suite counts produced**. The
sandbox permits writes only inside this repository and temporary directories;
`.pipeline/logs` is outside those roots. Approval escalation is unavailable.
Neither the runner, shared mutexes nor its external duration database was
modified or bypassed to manufacture a passing gate.

The six shard database OIDs were identical before/after the final attempted
chain, independently confirming that no fresh shards were created:

| DB suffix (`researchbase_lane102_`) | Before | After |
| --- | --- | --- |
| s0 | 149872420 | 149872420 |
| s1 | 149872865 | 149872865 |
| s2 | 149873699 | 149873699 |
| s3 | 149874964 | 149874964 |
| s4 | 149877416 | 149877416 |
| s5 | 149879009 | 149879009 |

All eleven reported test failures are resolved in the executed rerun. The
requested **full-suite gate remains unverified/BLOCKED**, and needs the exact
chain rerun by the external check loop with access to its shared mutex/duration
paths. No full-suite acceptance or independent review PASS is claimed.

Integration: migration `0079_agent_identity_versions` is re-parented to `0078_task_safety_policies`, as planned in the S1 pack.

## PR3-04 / PR3-02-S1 merge resolution verification (2026-10-21)

Resolved working-tree conflict contents by retaining both PRs' additions. The
exhaustive route/operation count is 121. All assertions remain in place; current
head pins and parent/chain values reflect 0077 -> 0078 -> 0079. S1 migration tests
use the intervening 0078 parent and still assert exactly four S1 tables added.
No new runtime behavior was introduced by the resolution.

Commands below ran with `UV_CACHE_DIR=/tmp/rb-lane103-uv-cache`.

| Exact command | Observed result |
| --- | --- |
| `git grep -nE '^(<<<<<<<|>>>>>>>|=======)$'` | Empty output; exit 1 (no matches). |
| `uv run alembic heads` | Only `0079_agent_identity_versions (head)`; exit 0. |
| `uv run ruff check .` | All checks passed; exit 0. |
| `uv run ruff format --check .` | 884 files already formatted; exit 0. |
| `uv run pyright` | 0 errors, 0 warnings, 0 informations; exit 0. |
| `uv run pytest -o addopts='' -q -ra tests/unit tests/architecture` | 6847 passed, 55 warnings, 112.28 s; exit 0. Includes migration-history and route-contract tests. |
| `uv run pytest -o addopts='' -q -ra tests/integration/phase3` | 325 passed, 115 warnings, 83.99 s; exit 0. |
| `git diff --check HEAD` | Empty output; exit 0. |

The full test suite was not run. The git index could not be updated:
`git add` failed with `Unable to create .../.git/index.lock: Operation not
permitted` because `.git` is read-only in this session. Consequently the index
still contains the original 26 unmerged paths, despite resolved working-tree
contents. No cherry-pick continuation, commit, push or branch creation occurred;
continuation also creates a commit, which the task's final instruction prohibits.

Touched PostgreSQL compatibility command (same writable uv cache):

```sh
uv run pytest -o addopts='' -q -ra tests/integration/phase2/test_b02_identity_boundary.py tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_04_migration_coverage.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_pr2_17_authorship_schema.py tests/integration/phase2/test_pr2_20_migrations.py tests/integration/phase2/test_revision_action.py tests/integration/test_pr02_application.py
```

Observed **181 passed, 6 failed, 441 warnings, 165.61 s**, exit 1. All six
failures were in `test_pr02_application.py`: PostgreSQL UndefinedTable,
`relation "actors" does not exist`, against the initially configured database.
The other eight touched modules passed. No application/test behavior was changed
to address this test-environment prerequisite.

Reran all six legacy actor tests with the existing disposable PostgreSQL helper,
setting DATABASE_URL only in the subprocess environment. Exact driver:

```sh
uv run python - <<'PYTHON'
import os, subprocess, sys
from tests.disposable_postgres import disposable_database
with disposable_database('researchbase_pr212_test_') as url:
    env = dict(os.environ, DATABASE_URL=url)
    subprocess.run(['uv','run','alembic','upgrade','head'], env=env, check=True)
    result = subprocess.run(['uv','run','pytest','-o','addopts=','-q','-ra','tests/integration/test_pr02_application.py'], env=env)
sys.exit(result.returncode)
PYTHON
```

Observed migration exit 0 followed by **6 passed in 0.25 s**, driver exit 0.
Preflight confirmed local PostgreSQL port 5432, system ID 7696072587520791948.
The randomly named disposable database was dropped by the helper. The ambient
database was not reset or migrated. These six passing reruns overlap the six
failed nodes above; the initial failed invocation remains recorded as failed.

## Reviewer rejection follow-up (2026-10-21)

**Status: full-suite gate and cherry-pick completion remain BLOCKED, not PASS.**
This section supplements the earlier focused checks; none of those checks
established full-suite acceptance.

### Reported failing gate

The reviewer reported **13,349 passed, 1 failed, exit 1**, with
`tests/integration/test_pr02_application.py::test_generic_create_actor_cannot_bypass_agent_enrollment`
failing in shard 4. This is reviewer-supplied evidence, not a run performed in
this follow-up. Its full traceback was not supplied. The reported actor-guard
failure is distinct from the six earlier UndefinedTable failures; the earlier
fresh-database rerun does not explain this later rejection. No pre-existing
failure or environmental root cause is claimed. The original traceback was
requested while investigation continued.

### Required fresh-database reproduction

With `UV_CACHE_DIR=/tmp/rb-lane103-uv-cache`, executed this exact driver:

```sh
uv run python - <<'PYTHON'
import os, subprocess, sys
from tests.disposable_postgres import disposable_database
with disposable_database('researchbase_pr212_test_') as url:
    env = dict(os.environ, DATABASE_URL=url)
    subprocess.run(['uv','run','alembic','upgrade','head'], env=env, check=True)
    result = subprocess.run(['uv','run','pytest','tests/integration/test_pr02_application.py','-k','bypass_agent_enrollment','-x'], env=env)
sys.exit(result.returncode)
PYTHON
```

Alembic upgraded a fresh random database through 0078 to 0079, exit 0. The exact
requested pytest command returned **1 passed, 5 deselected in 0.33 s**, exit 0.
There was **no traceback** in this reproduction. The existing helper dropped
the disposable database afterward. Output was retained in
`/tmp/rb-lane103-review-guard-fresh.log` for this session.

Read-only catalog inspection of all six retained lane shard databases confirmed
0079 and the enabled `pr302_agent_actor_write` trigger. Reran the same pytest
command with DATABASE_URL selecting the retained `researchbase_lane103_s4`:
**1 passed, 5 deselected in 0.31 s**, exit 0. The failing command was rejected
as expected; no generic AGENT was persisted. The ambient `researchbase_lane103`
database still has no Alembic table; it was not reset or migrated.

### Source inspection and docstring correction

Migration 0079 differs from `eaa6b9a` only in its authorized down_revision and
now-corrected docstring: “Re-parented to accepted 0078_task_safety_policies at
integration, as planned.” The `pr302_identity_insert_guard` body is unchanged.
`src/researchbase/application/phase2_identity.py` and
`src/researchbase/persistence/phase2_identity_repository.py` are byte-identical
to S1 parent `eaa6b9a`. The UoW diff against S1 adds only the PR3-04 task-safety
repository import, annotation and construction; its S1 error normalization is
unchanged. AST inspection confirms every class/function declaration from both
parents remains in models.py, uow.py, api/app.py and cli/app.py.

The bypass test was introduced by S1: it does not exist in parent `f4e38e4`,
whose legacy actor round-trip explicitly creates a generic AGENT. No claim that
the new regression test passed on both parents, or that this failure is
pre-existing, is made.

### Exact required chain attempt

Executed with the same writable uv cache:

```sh
! git grep -nE "^(<<<<<<<|>>>>>>>)" -- . ":!*.md" && test "$(uv run alembic heads 2>/dev/null | tail -1)" = "0079_agent_identity_versions (head)" && uv run pyright && uv run ruff format --check . && uv run ruff check . && git diff --check HEAD && /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/full_suite_sharded.sh 6
```

The marker and head checks passed. Pyright returned **0 errors, 0 warnings,
0 informations**; Ruff format reported **884 files already formatted**; Ruff
lint reported **All checks passed**; diff whitespace checking passed. Each
static stage exited 0. Independent working-tree `rg` scanning of src, tests and
.github also found no conflict markers, including reconstructed DA files.

The runner then printed:

```text
rm: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/full_suite.lock2/pid: Operation not permitted
rm: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/full_suite.lock2: Operation not permitted
```

It remained in its shared-lock queue. Interrupted the blocked command (exit
**130**); it produced **no new full-suite counts**. The runner, shared locks and
external duration database were not changed or bypassed. The prior reviewer
full-suite failure remains the latest supplied full-suite result.

### Git/index blocker

Retried `git add migrations/versions/0079_agent_identity_versions.py`; it exited
**128** with `Unable to create .../.git/index.lock: Operation not permitted`.
The session permission policy explicitly grants only read access to `.git`;
normal filesystem owner/mode inspection showed no permission-bit issue to fix.
No permission boundary was bypassed.

Current index inspection differs from the prior turn: `git ls-files -u` is
empty, but `git status --porcelain=v1` reports **26 DA paths** (staged deletions
with restored working-tree files). They must be staged as retained files before
continuation; running cherry-pick --continue against that index would discard
both PRs' required files. The reconstructed files are preserved in the working
tree. `git add` is blocked, so cherry-pick continuation was not attempted.

The user's new continuation request supersedes the previous no-commit
instruction, but cannot override the session's read-only `.git` permission.
`git status` is **not clean**. `git log -2 --oneline` remains:

```text
f4e38e4 Implement PR3-04 Budget / Termination / HumanCheckpoint (owner-authorized, ADR-0024)
fd877b4 Freeze the PR3-04 execution pack after two director reviews; fix plan_sealed_at naming (documentation only)
```

Completing the cherry-pick and exact full-suite gate requires a session allowed
to write `.git` and the runner's shared lock/duration paths. No new commit, push
or branch was created in this follow-up.

Additional focused contract verification (exit 0, **18 passed, 4 warnings in
6.97 s**):

```sh
UV_CACHE_DIR=/tmp/rb-lane103-uv-cache uv run pytest -o addopts='' -q tests/unit/test_pr15_http.py tests/unit/test_pr15r_route_contract.py tests/unit/test_batch_c_migration_history.py tests/unit/test_task12_migration_history.py tests/unit/test_ci_migration_head.py tests/architecture/test_pr3_02_s1_boundaries.py tests/architecture/test_pr3_04_boundaries.py
```

These checks cover the exhaustive 121-route union, both PR boundary contracts,
single head/parent/chain and preserved migration-history assertions. Final
`git diff --check HEAD` returned exit 0 after this documentation update.

Integration record (director, 2026-10-21): on branch codex/phase3-wave2-impl the
revision is re-parented to `0078_task_safety_policies` (single head
`0079_agent_identity_versions`). Integrated full check with PR3-04 and the Phase 3
fixture isolation fix (42c1d82): 13,350 passed, 0 failed, 66 skipped (six shards).
