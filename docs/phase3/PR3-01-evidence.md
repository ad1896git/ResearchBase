# PR3-01 planning slice — implementation evidence, 2026-10-21

Authority: the owner's 2026-10-21 implementation request, the frozen
[execution pack](PR3-01-contract-freeze.md) §§1–7, and
[ADR-0022](../architecture/adr/ADR-0022-pr3-01-policy-staging-input-layout.md).
The contract and ADR Status lines were not changed. This evidence does not assert
TDG-3, Phase 3 GO, scientific execution, or a whole-phase exit.

## Delivered scope

- Forward-only `0077_research_task_graph`, parent `0076_agent_runtime_bootstrap`:
  ten tables, 34 explicitly named indexes, 14 functions, 19 triggers. Four
  triggers are deferred: per-edge reachability, per-step parent walk, one task
  final check, and one receipt-completeness check. Indexed immediate guards use
  PostgreSQL tuple xmin/current transaction identity; history cannot be changed
  or extended by a later transaction. The two input tables each have six concrete
  version FKs and the prescribed XOR, scheme, partial-unique and reverse indexes.
- Pure planning domain, closed immutable commands/read DTOs, canonical request
  normalization and all three fixed hash vectors; Kahn DAG and three-color parent
  validation; the 256-node/1,024-edge/256-binding admission limits.
- One READ COMMITTED command UoW with the literal 18-table first SHARE inventory,
  project/command/task coordination, fresh authorization after waits, exact saved
  results and read-entitled replay before CAS/state checks. Only 40001/40P01 retry,
  at most three fresh transactions. Uncertain results reconcile the exact receipt.
  Dedicated connection pools supply startup timeouts before Application SQL.
- Lock-free REPEATABLE READ READ ONLY queries through `begin_formal_read()`.
  Frozen-input verification uses owning material and retained-seal verification
  in the same UoW, including observed validity warnings, without ArtifactStore
  backend I/O under planning locks.
- Existing `/v1/research-tasks` API composition and the `research-tasks` CLI group
  share Application services and the closed decoder. Existing error enums/maps
  and envelopes remain in use. Optional service-bundle fields are appended to
  preserve existing positional construction.
- Create, plan, append step/dependency, seal, cancel and read only. Reserved
  execution commands deny with `INVALID_STATE_TRANSITION` and
  `details.reason=EXECUTION_PREREQUISITES_UNMET`. No policy bindings, execution,
  gateway, worker, outbox, promotion, provider or runtime dependency was added.
- All nine specified test files. Existing migration head/parent pins and migration
  inventories advance to 0077. Historical PR3-00 migration tests explicitly target
  0076, preserving their empty-bootstrap assertions. Architecture checks continue
  to forbid runtime imports from scientific Core and admit only the specified
  PR3-01 files at the formerly empty runtime boundary.

## Environment and commands

Observed environment: macOS 27.0 arm64, Python 3.12.15, pytest 8.4.2,
PostgreSQL **18.6 (Homebrew)**. Database tests use random disposable databases via
`tests.disposable_postgres.disposable_database`; `RB_TEST_ADMIN_URL` was supplied
by the local test environment. Normal-role SQL uses a temporary NOSUPERUSER,
NOCREATEDB, NOCREATEROLE role with ordinary DML privileges. No triggers were
disabled. Test-generated CAS files, timing files and snapshots use pytest
`tmp_path`/`tmp_path_factory` directories.

Every uv command below was executed with the prefix
`UV_CACHE_DIR=/tmp/researchbase-lane89-uv`. The default cache was inaccessible in
this sandbox; relocating the cache changes no dependencies or lockfile.

| Exact command after that environment prefix | Observed result |
| --- | --- |
| `uv sync --locked` | Exit 0; resolved 38 packages, checked 34 packages. |
| `uv run ruff check .` | Exit 0; All checks passed! |
| `uv run ruff format --check .` | Exit 0; 837 files already formatted. |
| `uv run pyright` | Exit 0; 0 errors, 0 warnings, 0 informations. A newer-tool-version notice was printed. |
| `uv run alembic heads` | Exit 0; sole head `0077_research_task_graph (head)`. |
| `uv run pytest -o addopts='' -ra tests/unit/phase3 tests/architecture tests/unit/architecture tests/integration/phase3` | Exit 0; **702 passed, 0 failed, 0 skipped**, 75 Alembic configuration deprecation warnings, 91.09 seconds. |
| `uv run pytest -o addopts='' -ra tests/unit/test_task12_migration_history.py tests/unit/test_batch_c_migration_history.py tests/unit/phase2/test_pr2_04_r8a_host_topology.py tests/unit/phase2/test_pr2_20_inventory.py` | Exit 0; **15 passed, 0 failed, 0 skipped**, 3 warnings, 3.02 seconds. |
| `uv run pytest -o addopts='' -ra -s tests/integration/phase3/test_pr3_01_schema.py::test_1024_edge_commit_timing_and_one_final_firing tests/integration/phase3/test_pr3_01_concurrency.py::test_actual_wait_crosses_credential_expiry` | Exit 0; **4 passed, 0 failed, 0 skipped**, 1 warning, 7.18 seconds. This intentionally repeats four cases to expose timing witnesses. |
| `uv run pytest -o addopts='' -ra tests/unit/phase3/test_research_task_transports.py` | Exit 0; **20 passed, 0 failed, 0 skipped**, 3.88 seconds; rerun after preserving service-bundle positional compatibility. |

`git diff --check` also exited 0. The initial authoring turn did **not run** the
whole repository test suite. The reviewer subsequently supplied a failing full-suite
result and explicitly authorized a full rerun; see the review follow-up below.
The separate test counts above overlap and must not be summed as unique cases.

## Database witnesses

The catalog test verifies the exact ten-table/34-index/14-function/19-trigger
inventory, four deferred triggers and RESTRICT FKs. The schema cases exercise all
six input families at both owners, zero/multiple references, twelve partial
uniques, NULL/forbidden schemes, saved-hash mismatch, missing frozen timestamps
or hashes, foreign project/unlinked source denial, and the absence of a global
Artifact exception. Same-task parent/dependency FKs and the structurally required
current-step FK are checked; non-NULL current-step values remain prohibited.

Adversarial DML covers later-transaction child/history/result-link inserts,
committed child material and immutable no-op updates/deletes, cycles closed by a
last batch edge or later flush/edit, and success history without its named
mutation. Valid complete normal-role commands commit. Opposite-edge commands,
seal/append and cancel/append races coordinate actual PostgreSQL waits. A
membership revocation committed during a first-SHARE wait denies the subsequent
write. The accepted source-link deletion guard remains immutable: its deletion
attempt waits for planning SHARE and then rejects; this is not evidence of a new
source-link revocation feature.

For 256 nodes and 1,024 edges, the measured `SET CONSTRAINTS ALL IMMEDIATE` time
was **0.102219 s**. From starting that forced deferred check through successful
commit was **0.104846 s**, against an asserted **10 s** bound. Actual
`pg_stat_xact_user_functions` counter deltas were exactly **one**
`pr301_graph_final_guard` call and **one** `pr301_receipt_complete` call. Per-row
cycle checks remain active. These measurements describe this environment only.

The three expiry witnesses below are database timestamps, shown in UTC. Each
wait was observed as an ungranted entry in `pg_locks`; an after-acquisition hook
recorded database time before final credential authorization. All three returned
FORBIDDEN with zero protected new task rows/events/receipts.

| Wait | Transaction start | Expiry | Observed waiting | Acquired | Authorization checked |
| --- | --- | --- | --- | --- | --- |
| First SHARE | 07:57:55.337791 | 07:57:55.582066 | 07:57:55.341948 | 07:57:55.589626 | 07:57:55.600167 |
| Project advisory | 07:57:55.636337 | 07:57:55.879716 | 07:57:55.647322 | 07:57:55.887404 | 07:57:55.896979 |
| Task advisory | 07:57:55.917749 | 07:57:56.160487 | 07:57:55.931099 | 07:57:56.164673 | 07:57:56.173530 |

The implementation performs its first authorization only after **all** blocking
waits; it has no later blocking lock acquisition after a preliminary successful
authorization. Snapshot-reader tests retain their original view across a writer
commit and complete while writer exclusion locks remain held.

Migration cases cover a clean upgrade, frozen Phase 2 fixtures retained across
0076→0077 with identical old rows/hashes/readback, repeated upgrade, and empty and
populated downgrade refusal with unchanged revision/catalog/history. No repair
migration was implemented: repair requires a separately approved forward change.
No policy UUID is fabricated and planning remains execution-ineligible.

## Development corrections and review limits

Earlier focused development runs had failures; they are not PASS evidence. They
led to corrections in the disposable-database selector, function-counter baseline,
SourceVersion verification without a required fulltext document, transport auth
ordering, closed array validation, fixture ownership, and stale architecture/head
assumptions. The final results above supersede those failed runs.

One early setup attempt lacked a per-test `DATABASE_URL` override. Alembic used
the ambient local **researchbase_lane89** database and advanced it from 0076 to an
early development version of 0077; fixture bootstrap then failed against the
still-empty disposable database. That attempt wrote no scientific or planning
rows. The fixture now explicitly sets the disposable URL before migration. The
ambient lane database was not reset or treated as evidence of the final 0077
function bodies. All successful PostgreSQL results reported here use freshly
created disposable databases.

Human attribution, read-role replay and unbound-Agent denial are tested. Positive
Agent enrollment/provenance remains dependent on PR3-02; denial is not a positive
Agent provenance claim. Independent formal review was **not run** in this
authoring turn; these results are supplied for the check loop/director review,
without claiming independent review PASS or a gate decision. No commit, push or
branch creation was performed. Stop at this planning slice.


## Review follow-up — P1 required-check regressions

The reviewer-supplied full-suite result was **FAIL, exit 1**: **12,955 passed,
66 skipped, 3 failed**, with 10,410 warnings. The three failures were the exact
route contract, reproducible OpenAPI surface, and populated-head no-op migration
tests listed below. The original 702-pass focused run was insufficient to detect
these regressions and is not a substitute for a successful full-suite run.

Corrections:

- Pack §5.1 admits the nine planning routes and explicitly permits publishing the
  six reserved denial routes. Extend only the literal route/OpenAPI inventories
  from 94 to **109** operations; preserve the existing equality, schema,
  operation-ID, Application-binding and reproducibility assertions. Existing
  routes retain their contract values.
- Fix the new API routes to declare their closed DTO response schemas and stable
  command/query operation IDs. Named handlers call the corresponding Application
  methods explicitly. This makes the admitted new surface satisfy the existing
  structural contract rather than relaxing its schema/binding checks. The six
  reserved operations still deny execution; no execution behavior was added.
- The populated-head no-op test previously constructed its fixture at 0075 and
  compared that catalog with the additive 0077 head. It now explicitly upgrades
  its setup to **0077_research_task_graph before taking the baseline**, then
  upgrades to head again. Both complete row-manifest and catalog equality checks
  remain unchanged. The separate `PHASE2_HEAD=0075` historical empty-round-trip
  cases remain pinned: changing those to forward-only 0077 would invalidate their
  intentional historical downgrade test.

Individual reruns (each command used
`UV_CACHE_DIR=/tmp/researchbase-lane89-uv`):

| Exact command | Actual result |
| --- | --- |
| `uv run pytest -o addopts='' -ra tests/unit/test_pr15r_route_contract.py::test_all_63_routes_have_exact_schema_operation_and_application_bindings` | Exit 0; **1 passed**, 0 failed/skipped, 1.57 seconds. |
| `uv run pytest -o addopts='' -ra tests/unit/test_pr15_http.py::test_openapi_has_exact_frozen_v1_surface_and_is_reproducible` | Exit 0; **1 passed**, 0 failed/skipped, 1.94 seconds. |
| `uv run pytest -o addopts='' -ra -s tests/integration/phase2/test_pr2_20_migrations.py::test_populated_source_evidence_conclusion_placement_review_decision_head_noop` | Exit 0; **1 passed**, 0 failed/skipped, 6 warnings, 2.25 seconds. |
| `uv run pytest -o addopts='' -ra tests/unit/test_pr15r_route_contract.py tests/unit/test_pr15_http.py tests/unit/phase3/test_research_task_transports.py tests/architecture/test_pr15_http_boundaries.py tests/architecture/test_pr3_01_boundaries.py` | Exit 0; **38 passed**, 0 failed/skipped, 8.89 seconds. These cases overlap the individual reruns. |

The migration rerun proved isolation with these actual fixture messages:

```text
DISPOSABLE_CREATED: researchbase_pr211_r2_test_ec43557bb1cd4645a7149e37f454d814
PR211_R2_REVISION: researchbase_pr211_r2_test_ec43557bb1cd4645a7149e37f454d814=0033_pr2_11_r2_scientific_conclusion
DISPOSABLE_DROPPED: researchbase_pr211_r2_test_ec43557bb1cd4645a7149e37f454d814
```

That fixture asserts the new database initially has zero public tables, migrates
its historical starting state, and supplies that URL to the test. It does not use
`researchbase_lane89`. The observed regression was the 0075-versus-0077 baseline,
not a flaky assertion or an inherited early lane schema.

### Requested full check — blocked by filesystem sandbox

Executed the owner's exact chain after exporting the writable uv-cache location:

```sh
export UV_CACHE_DIR=/tmp/researchbase-lane89-uv
uv run pyright && uv run ruff format --check . && uv run ruff check . && git diff --check HEAD && /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/full_suite_sharded.sh 6
```

The four static stages succeeded: Pyright **0 errors, 0 warnings,
0 informations**; Ruff format **837 files already formatted**; Ruff check
**All checks passed!**; `git diff --check HEAD` exit 0. The sharded runner printed:

```text
== quick pre-check skipped: 72 changed test files (> 25)
rm: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/full_suite.lock2/pid: Operation not permitted
rm: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/full_suite.lock2: Operation not permitted
```

It could not acquire/clean its shared mutex outside this session's writable
roots and stayed in its queue loop. The blocked invocation was interrupted,
**exit 130**, before any shard launched. New full-suite counts are **NOT RUN**,
not zero-test PASS. The runner, shared mutexes and governing harness were not
modified to bypass this restriction. The same four static stages were then
rerun as a standalone `&&` chain and exited **0**. Full acceptance remains
unverified until the requested runner can execute in an environment permitted
to write its shared log/mutex and duration paths.

### Shard database inspection

Read the actual runner: after acquiring its mutex, it executes `DROP DATABASE
IF EXISTS` and `CREATE DATABASE` separately for `researchbase_lane89_s0` through
`researchbase_lane89_s5`, migrates each to head, and sets each child's DATABASE_URL
to that shard. The optional quick pre-check uses the lane database, but was
explicitly skipped in both the reviewer log and this attempt. The shards are
separate from the ambient `researchbase_lane89` database.

Observed the six database OIDs before and after the blocked invocation using
`uv run python -` with a read-only query against `pg_database`:

```sql
SELECT datname,oid::text FROM pg_database
WHERE datname LIKE 'researchbase_lane89_s%' ORDER BY datname;
```

They were unchanged: s0=4272288036, s1=4272288322, s2=4272288323,
s3=4272288324, s4=4272288325, s5=4272288327. Thus this blocked invocation created
**no fresh shard databases**. Do not misrepresent the retained shards as a new run.

Also executed this read-only revision check for each suffix 0 through 5:

```sh
DATABASE_URL="postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase_lane89_s${shard}" UV_CACHE_DIR=/tmp/researchbase-lane89-uv uv run alembic current
```

All six reported **0077_research_task_graph (head)**, exit 0. This proves their
current revision and distinct database selection; a revision alone does not prove
fresh creation or completion of the new full-suite run. No new full-suite PASS,
independent review PASS or gate success is claimed by this follow-up.
