# B14 READY first-slice implementation evidence — 2026-10-18

The owner authorized the first slice on 2026-10-18. The proposal status was changed
before implementation. The reconciled predecessor was
`0061_b14r_ready_approval`, following B13 (`0059`) and the real B14a entry (`0060`).
The owner instruction supplies the joint B13/B14 READY authorization; package,
consent, sending, repeat readiness cycles and transport adapters remain deferred.

`PublicationService.transition_publication_ready` returns the existing B13 receipt
with its closed READY saved result v1. `get_publication_ready_transition` reads that
receipt, its unique concrete lifecycle event, and separate current diagnostics.
READY records an internal gate; scientific validity remains a canonical-fact
projection. The write rechecks the exact frozen manuscript, saved Decision/review basis,
current closure and bytes, later reviews, applicable Issue histories/blockers,
rejection fence, caller and independently issuing HUMAN's live credentials.
Publication status/version, lifecycle event, receipt, consumed grant and terminal
grant event share one transaction and exact actor/time.

One new migration, `0062_b14_publication_ready`, extends the existing tables and
retains old migrations byte for byte. It adds the concrete Decision/receipt FKs,
READY uniqueness and both directions of deferred completeness. Normal-role SQL
must pass the preheld inventory/isolation, literal material checks and complete
same-transaction graph. Downgrade refuses retained entry/READY history.

Writes use SERIALIZABLE and the frozen existing B13 N→W→A inventory as first
application SQL, then the existing consumption/purpose advisories and exact
manuscript→Publication→request→grant row order. Reads and completed replay use one
REPEATABLE READ, READ ONLY snapshot without explicit table/advisory/row exclusion
locks or writes. Only 40001/40P01 retry, at most three fresh write UoWs. Deferred
constraints precede final fresh-clock caller/issuer/expiry checks. Unexpected
READY/receipt database errors have a strict sanitized error path and do not use
raw diagnostic text or become business conflicts.

## Reconciled names and representations

| Guide baseline | Existing equivalent retained |
| --- | --- |
| `ck_b14_publication_status`, `ck_b14_event_tuple` | Extend `ck_b14a_publication_status`, `ck_b14a_event_tuple` with READY; retain their names. |
| `ck_b14_event_time`, `uq_b14_initial_event`, `uq_b14_review_entry` | Existing `ck_b14a_event_time`, `uq_b14a_initial_event`, `uq_b14a_review_entry`. |
| Event has no manuscript column in the old guide baseline | Preserve B14a's `manuscript_version_id` and concrete same-parent FK for entry. READY leaves this column null and derives its exact manuscript through the receipt/grant/request chain. |
| Prepared write and SERIALIZABLE UoW entry | Reuse `approval.prepare_write`, literal `B13_SNAPSHOT_TABLES`, `configure_grant_transaction(consuming=True)` and `lock_grant_chain`; no second lock inventory or scope namespace. |
| Receipt plus event/current readback | `ReadyTransitionReadback.consumption` contains the existing typed B13 readback; event facts and current diagnostics are separate fields. |

B14a's deferred entry triggers remain compatible continuity guards alongside the
new B14 completeness triggers. The B14r migration-only roundtrip pins revision
0061 before creating entry history, so it does not attempt a forbidden B14
downgrade over retained history. Existing head expectations/inventories and CI's
head value were updated. B14r's old “effect dependency unavailable” assertions now
expect an otherwise valid READY grant to be usable.

Both Human and Agent call the same method. The current identity contract reserves
Agent enrollment for its own reviewed adapter; the test rejects an unbound Agent
without inventing enrollment or bypassing canonical guards.

## Verification

Commands ran with the existing environment using `uv run --no-sync`. The common
cache prefix was `UV_CACHE_DIR=/private/tmp/b14-uv-cache`. PostgreSQL environment:

```sh
DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase_lane19
RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres
```

| Exact command after the cache prefix | Observed result |
| --- | --- |
| `uv run --no-sync ruff check .` | All checks passed. [Output](b14-ready-evidence/ruff.txt). |
| `uv run --no-sync ruff format --check .` | 660 files already formatted. [Output](b14-ready-evidence/format.txt). |
| `uv run --no-sync pyright` | 0 errors, 0 warnings, 0 informations. [Output](b14-ready-evidence/pyright.txt). |
| `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 uv run --no-sync pytest tests/unit tests/architecture tests/test_architecture.py --tb=short` | **5,306 passed, 1 failed**, 42 warnings, 86.58s. [Output](b14-ready-evidence/unit-architecture.txt). |
| `PYTHONPATH=src uv run --no-sync pytest tests/unit/phase2/test_b14_ready_contract.py tests/architecture/test_b14_ready_boundaries.py --tb=short` | 53 passed, 0.90s. [Output](b14-ready-evidence/contract.txt). |
| `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 uv run --no-sync pytest tests/integration/phase2/test_b14_publication_ready.py tests/integration/phase2/test_b14_ready_schema.py tests/integration/phase2/test_b14_ready_replay.py tests/integration/phase2/test_b14_ready_concurrency.py --tb=short` | 78 passed, 313 warnings, 155.47s. [Output](b14-ready-evidence/ready-postgres.txt). |
| `PYTHONPATH=src uv run --no-sync pytest tests/integration/phase2/test_b14_ready_concurrency.py::test_two_grants_one_publication_one_winner_unused_permission_is_retained --tb=short` | 2 additional cases passed, 8 warnings, 5.37s. [Output](b14-ready-evidence/competing-grants.txt). |
| `PYTHONPATH=src uv run --no-sync pytest tests/integration/phase2/test_b14_publication_ready.py::test_failure_after_each_individual_sql_write_is_atomic --tb=short` | 5 additional cases passed, 20 warnings, 7.36s. [Output](b14-ready-evidence/individual-writes.txt). |
| `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 uv run --no-sync pytest tests/integration/phase2/test_b14r_ready_approval_schema.py --tb=short` | 20 passed, 86 warnings, 19.31s. [Output](b14-ready-evidence/b14r-schema.txt). |
| `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 uv run --no-sync pytest tests/integration/phase2/test_b13_*.py --tb=short` | 77 passed, 234 warnings, 138.88s. Repeated after strict receipt-read normalization. [Output](b14-ready-evidence/b13-regression.txt). |

The broader focused dependency run used this exact command after the cache
prefix:

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 uv run --no-sync pytest tests/integration/phase2/test_pr2_12_*.py tests/integration/phase2/test_b04_*.py tests/integration/phase2/test_b05_*.py tests/integration/phase2/test_b08_*.py tests/integration/phase2/test_b09_*.py tests/integration/phase2/test_b10_*.py tests/integration/phase2/test_b11_*.py tests/integration/phase2/test_b12_*.py tests/integration/phase2/test_b13_*.py tests/integration/phase2/test_b14a_*.py tests/integration/phase2/test_b14r_*.py tests/integration/phase2/test_approval.py tests/integration/phase2/test_pr2_15_decision*.py --tb=short
```

Observed: **903 passed, 1 failed, 1 skipped**, 3,091 warnings, 1,203.44s.
[Full output](b14-ready-evidence/focused-regressions.txt). This long-running process
had already collected the predecessor B14r populated migration fixture before its
revision-pinning correction. It attempted a forbidden B14 downgrade over retained
entry history. The corrected B14r schema file was rerun separately: **20 passed**,
as recorded above. The broad command was not repeated after that targeted repair.
The skipped B05 case explicitly awaits the separately approved manuscript
SUPERSEDED lifecycle; it is not acceptance for that future behavior. The final
strict receipt-read normalization was additionally verified by the complete
77-case B13 rerun and READY runs above.

The 85 new PostgreSQL cases include real Application entry/Decision/approval,
normal-role complete/deferred cycles and denied partial graphs, immutable history,
corrupt receipt detection, replay after later blockers/validity/credential loss,
write/read entitlement loss, uncertain commit recovery, both review phantom commit
orders, same-key/two-key/two-grant races, exact FIRST SQL/isolation and pg_locks
read witnesses, real legacy deadlock recovery, bounded retry/error classification,
and observed table/scope/target/grant/deferred waits crossing grant expiry.
Failure injection covers every individual SQL write, forced constraints and final
credential checks, with no partial effect.

The initial unit/architecture run failed at
`test_candidate_static_gates_and_inherited_formatter_delta`, whose baseline
whitespace check found a final blank line in
`docs/phase2/b14r-ready-approval-evidence/pyright.txt:4`. The earlier “inherited”
classification established only that the file matched HEAD; it did **not** prove
that the complete test passed or failed on a clean base. That classification was
insufficient for acceptance. Review remediation removes exactly that blank line,
keeps the pinned baseline and all assertions unchanged, and reruns the check.

Warnings are the existing Alembic `path_separator` deprecation and the fixture-owned
review/Decision adapters' already-established connection isolation warnings. PostgreSQL
catalog tests checked the real server's version number begins with 18.

Read-only sub-agent reviews investigated dependencies, schema and test fixtures,
then reviewed Application/persistence and migration changes. Identified
cross-command replay, pre-effect structural admission, SQL material verification
and post-gate clock gaps were repaired and covered by focused verification. The final read-only review found no open P0/P1 in the implementation. No
other agent edited files. The initial implementation did not run the whole suite.
The reviewer then explicitly authorized the exact full gate; its follow-up evidence
is recorded below. No commit, push or branch creation was performed, and this
record does not declare a Phase 2 exit.


## Reviewer remediation

The rejected full run reported 10,072 passed, 2 failed and 50 skipped. Earlier
focused pass counts above are historical observations, not proof of a passing
full gate. This section records the follow-up verification.

### Lock observation root cause

The requested isolated command reproduced the failure: `uv run pytest
tests/integration/phase2/test_b14_ready_concurrency.py::test_first_sql_and_read_locks_are_exact
-x` returned **1 failed**. Its FIRST-SQL, row-order and read-isolation assertions
passed. The failing assertion counted retained `('tuple', 'SIReadLock')` entries
as explicit row exclusion locks on a backend reused from the committed writer.

[PostgreSQL 18 §13.2.3](https://www.postgresql.org/docs/18/transaction-iso.html#XACT-SERIALIZABLE)
distinguishes nonblocking SSI predicate locks from exclusion locks and explains
that they may survive commit while overlapping transactions remain. The fixed
observation excludes only that nonblocking mode. It continues to reject all
advisory locks, actual tuple exclusion locks and every relation mode except
ordinary `AccessShareLock` and nonblocking `SIReadLock`; it continues to assert literal FIRST SQL, row order, READ ONLY REPEATABLE
READ and absence of locking SQL.

The test now deliberately holds an overlapping read/write SERIALIZABLE snapshot,
observes the committed writer's retained SIRead locks, then verifies the real
readback/replay. Three positive controls demonstrate that the same observer detects
an advisory lock, `SELECT FOR UPDATE`'s relation exclusion lock and an explicit
`SHARE UPDATE EXCLUSIVE` table lock. Production
read isolation and locking behavior were not altered to hide the observation.

The timing-based shard allocator's current snapshot assigns the file to shard 1,
although the rejected run assigned it to shard 3. The shard-3 reproduction uses
its frozen current file list plus the exact failing node, after those files in
the same pytest process. The six frozen manifests are retained under
[review-shards](b14-ready-evidence/review-shards/shard-3.txt), rather than claiming
that changing duration measurements reproduce an unavailable previous manifest.
The before-fix process collected the original failing observer; the after-fix
process collected the corrected observer. While those contexts ran, the observer
was further tightened to reject every non-read relation mode and gained the table
control. The final 92-case PostgreSQL rerun verifies that final version. Production
code was unchanged between those context collections and the final focused run.

### Full source diffs for repository/domain/UoW review

These are complete per-file `git diff --unified=0 HEAD -- <path>` outputs,
without response truncation or omitted hunks. Zero context avoids introducing
trailing-whitespace-only context lines into tracked evidence. The complete source
files are linked for surrounding context.

| Component/source | Full diff |
| --- | --- |
| [Approval repository](../../src/researchbase/persistence/approval_repository.py) | [Diff](b14-ready-evidence/review-approval_repository.diff) |
| [Publication repository](../../src/researchbase/persistence/publication_repository.py) | [Diff](b14-ready-evidence/review-publication_repository.diff) |
| [UoW](../../src/researchbase/persistence/uow.py) | [Diff](b14-ready-evidence/review-uow.diff) |
| [Approval domain values](../../src/researchbase/domain/approval.py) | [Diff](b14-ready-evidence/review-approval.diff) |
| [Approval Application service](../../src/researchbase/application/approval.py) | [Diff](b14-ready-evidence/review-application-approval.diff) |
| [Publication Application service](../../src/researchbase/application/publication.py) | [Diff](b14-ready-evidence/review-publication.diff) |
| [Typed ports](../../src/researchbase/application/ports.py) | [Diff](b14-ready-evidence/review-ports.diff) |
| [Forward migration](../../migrations/versions/0064_b14_publication_ready.py) | [Diff](b14-ready-evidence/review-0062_b14_publication_ready.diff) |

### SQL verifier origins and drift controls

| B14 verifier | Origin and deliberate adaptation |
| --- | --- |
| `b14_facts` | Mirrors `pr216_facts` in frozen [0045](../../migrations/versions/0045_pr2_16_basic_approval.py), replacing only the function name and the conclusion-rooted `pr216_closure(target)` with `b11_closure(target)`. |
| `b14_material` conclusion hashes | Mirrors 0045 `pr216_material_gate`'s conclusion input/support/content hash block. |
| `b14_material` claim hashes and current claim validity | Mirrors 0045 `pr216_material_gate`'s claim content/support and correction/impact checks; substitutes `r.project_id` with the explicit `pid`. |
| `b14_material` literature validity | Mirrors 0045 `pr216_material_gate`'s effective literature/source/current-review block, unchanged. |
| Manuscript-root traversal | Reuses [0054](../../migrations/versions/0054_b11_ready_for_submission.py) `b11_roots`/`b11_closure`, which delegates transitive closure to B07. No second stored graph is introduced. |
| Added manuscript verification | Reconstructs the owning B04 literals from [domain/manuscript.py](../../src/researchbase/domain/manuscript.py): placement set and content hash. Uses byte-compatible `C` section ordering. Adds graph-wide correction/impact/source validity checks over the same closure. |

The existing SQL gate accepts one scientific conclusion root, whereas READY must
verify all roots of an exact manuscript, including direct claims, document,
artifact and citation placements. Calling it with a manuscript UUID would not
verify that graph. The bounded specialization preserves the existing release
binding and frozen migrations; all hashes are reconstructed from the existing
concrete canonical rows using the existing hash helpers. It creates no new
scientific facts, hash scheme, payload contract or persistence owner. Release
review/Decision-specific checks are not copied into this material verifier:
B14a admission and B14r saved-Decision checks own the READY basis.

`test_mirrored_scientific_material_keeps_owning_hash_contracts` compares the full
facts function after its two explicit renames and checks all three inherited
material blocks against the owning function. This prevents silent divergent
copies; any future material change must update the owning contract and its
approved specialization together.

### Local READY tuple validation

`b14_consumption_gate` now rejects wrong purpose, missing manuscript or a non-null
scientific conclusion before looking up any target. Thus `b13_release_gate`'s
READY dispatch validates the same finite tuple locally, as well as relying on the
existing persisted request CHECK. Four PostgreSQL tests invoke both gates with
transient malformed typed request rows and require SQLSTATE `P16P1`; no persisted
request, immutable guard or trigger is bypassed.


### Follow-up commands and observed results

All commands below use `UV_CACHE_DIR=/private/tmp/b14-uv-cache`; no baseline or
assertion was relaxed for the formatter failure. The unit/architecture command
clears the repository's default quiet flag so the exact count remains visible.

| Exact command after cache prefix | Observed result |
| --- | --- |
| `uv run pytest tests/integration/phase2/test_b14_ready_concurrency.py::test_first_sql_and_read_locks_are_exact -x` (before fix) | **1 failed**, 4 warnings, 1.71s. [Output](b14-ready-evidence/review-isolation.txt). |
| Same exact isolated command after final observer tightening | **1 passed**, 4 warnings, 1.89s. [Output](b14-ready-evidence/review-isolation-final.txt). |
| `uv run pytest tests/integration/phase2/test_b14_ready_concurrency.py::test_first_sql_and_read_locks_are_exact tests/integration/phase2/test_b14_ready_concurrency.py::test_read_lock_observer_detects_real_exclusion` | **4 passed**, 13 warnings, 4.20s. [Output](b14-ready-evidence/review-lock-final.txt). |
| `uv run pytest tests/unit/phase2/test_pr2_04_static_acceptance.py tests/architecture/test_b14_ready_boundaries.py tests/integration/phase2/test_b14_ready_schema.py` | **25 passed**, 78 warnings, 31.99s. [Output](b14-ready-evidence/review-targeted-final.txt). |
| `uv run pytest tests/integration/phase2/test_b14_publication_ready.py tests/integration/phase2/test_b14_ready_schema.py tests/integration/phase2/test_b14_ready_replay.py tests/integration/phase2/test_b14_ready_concurrency.py` | **92 passed**, 366 warnings, 138.26s. [Output](b14-ready-evidence/review-ready-final.txt). |
| `uv run pytest -o addopts='' -q tests/unit tests/architecture tests/test_architecture.py --junitxml=/private/tmp/b14-review-unit-architecture.xml` | **5,308 passed**, 42 warnings, 63.91s. [Output](b14-ready-evidence/review-unit-architecture.txt). |


### Exact full-gate attempt and environment blocker

The reviewer explicitly authorized running the full suite. The following exact
chain was invoked with the cache variable above (the last stage's stdout/stderr
was captured to the linked log):

```sh
uv run pyright && uv run ruff format --check . && uv run ruff check . && git diff --check HEAD && /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/full_suite_sharded.sh 6
```

The first four stages passed: Pyright **0 errors, 0 warnings, 0 informations**;
Ruff format **660 files already formatted**; Ruff check **All checks passed**;
`git diff --check HEAD` exit **0**. The runner's changed-file precheck then passed:
**762 passed, 1,769 warnings in 554.91s**.
[Runner output](b14-ready-evidence/review-full-gate.txt).
That process collected tests before the final additional table-lock positive
control; the final four-case observer run above covers that tightening.

The runner then needs to create its mutex directory under
`/Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs` and later update
`/Users/fengwang/Documents/ResearchBaseProject/.pipeline/test_durations.json`.
Both are outside this session's writable roots (repository and temporary paths).
The mutex creation preflight returned `PermissionError: Operation not permitted`.
The unmodified runner suppresses that mkdir error and waits forever in its mutex
loop, even when both mutex slots are absent. After the successful precheck the
waiting command was interrupted (exit **130**); none of the six full shards ran.
The owner was asked to enable those write paths or run the exact gate in the
unsandboxed owner loop. The runner and its mutex protocol were not modified.
**There is no full-gate PASS claim.**


The final static chain was also rerun after the observer tightening:
`uv run pyright && uv run ruff format --check . && uv run ruff check . && git diff --check HEAD`.
It exited **0**, with **0 type errors/warnings**, **660 files already formatted**,
and **All checks passed**. [Output](b14-ready-evidence/review-static.txt).
A read-only follow-up review found no P0/P1 in the observer or tuple guard.


### Shard-3 context commands

The pre-fix invocation used the existing lane database and the frozen shard-3
manifest, with the exact failing node appended after all context files:

```sh
uv run pytest -o addopts='' -q -rfE -p no:cacheprovider -x $(cat docs/phase2/b14-ready-evidence/review-shards/shard-3.txt) tests/integration/phase2/test_b14_ready_concurrency.py::test_first_sql_and_read_locks_are_exact
```

Observed before-fix context result: **1,712 passed, 49 skipped, 1,423 warnings in
1,305.78s**, exit **0**. [Output](b14-ready-evidence/review-shard3-before.txt).
This invocation did **not** reproduce the failure; the exact isolated command did
(see the one-failure log above). The different outcome is consistent with the
original observer depending on retained predicate locks' lifetime. It is not
presented as a recreation of the unavailable rejected-run manifest. The new
observer's deliberate overlapping snapshot removes that accidental precondition.


The after-fix invocation used a separate test database, migrated to the same head,
and the identical frozen file order plus failing node:

```sh
DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase_lane19_review_s3 uv run alembic upgrade head
DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase_lane19_review_s3 uv run pytest -o addopts='' -q -rfE -p no:cacheprovider -x $(cat docs/phase2/b14-ready-evidence/review-shards/shard-3.txt) tests/integration/phase2/test_b14_ready_concurrency.py::test_first_sql_and_read_locks_are_exact
```

Observed after-fix context result: **1,712 passed, 49 skipped, 1,423 warnings in
1,283.38s**, exit **0**. [Output](b14-ready-evidence/review-shard3-after.txt).
This includes the previously failing static acceptance test in the context and
the corrected lock observer after it. Together with the exact isolated failure
and final isolated pass, the final 92-case READY suite and 5,308-case
unit/architecture run, these are the completed local verification results.
The requested six-shard gate remains blocked as documented above; no gate PASS
or Phase 2 acceptance is asserted.
