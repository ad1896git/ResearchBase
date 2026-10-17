# B27 first-slice implementation — 2026-10-17

## Batch D integration correction

The owner’s Batch D integration instruction supersedes the earlier requirement
for an empty migration below. `0052_b27_defensive_closure_read` was removed;
B27 requires no DDL. The integrated history ends at
`0059_b13_grant_consumption`, following B12 and the existing Batch C chain.
The release writer retains the broader accepted approval snapshot protocol
before request/target locks. The results below describe the original lane;
current integration checks are recorded in
[Batch D evidence](../batch-d/integration-evidence.md).

## Original lane authority and interpretation

The owner's implementation task and subsequent review instructions override the
proposal's earlier restrictions on migrations and write ordering. Specifically:

- Proposal §12.1 says “No migration to build.” Its SQL is explicitly an inventory
  of existing FK and immutable/completeness guards, not new DDL. The later owner
  instruction requires one new revision. Revision
  `0052_b27_defensive_closure_read`, directly after `0051_b06_revision_action`,
  therefore records the read-contract change without changing schema, guards,
  historical rows, dependencies, or hash material. No historical migration changed.
- Proposal §12.2 describes “Existing write protocols (observed, not B27 build
  instructions)” and says B27 “authorizes no write-order change.” The later owner
  instruction explicitly supersedes that observation for scoped writes. Decision
  `_record_once` now calls `lock_snapshot` before `lock_request` and `target`.
  Novelty `prepare` now acquires its existing N inventory before timeouts,
  advisory coordination and ClaimVersion row locks for every scoped write kind.
  Both select READ COMMITTED before the inventory's FIRST transaction statement.

Before editing, affected call sites were identified as
`application/decision.py:213–220` and
`persistence/novelty_repository.py:74–85`. Existing manuscript-freeze and manuscript
review write protocols already start with SHARE and were retained.

No naming substitution was necessary. Existing
`enable_revision_action_snapshot_reads` supplies protected nested adapters;
`begin_formal_read` extends the existing typed UoW boundary with lock-free
REPEATABLE READ, READ ONLY and protected authorization. Existing manuscript trace
and internal review snapshot setup remains in place.

## Implemented behavior

Stored Decision basis and selected snapshot edges survive target absence.
StatisticalResult identity, direct Measurements and statistical inputs are checked
independently. Exact snapshot predecessor chains retain empty memberships and
verify existing support/content hashes. Trace Conclusion material uses the
existing literal hash builders; removed membership cannot shorten a successful
trace. Source predecessor, owning identity and selected artifact references must
resolve. Trace Claim closure uses the existing typed batch context and validator.

Run/Claim diagnostics check required owning ExperimentSpec, Dataset, Artifact and
MetricDefinition identities, retaining global Dataset, Artifact and MetricDefinition policy and the
existing diagnostic report shape and sorting. Owner lookups add fixed typed
batches, independent of edge count; query-count assertions were updated to the
observed constant stage counts.

The frozen Phase 1 query-plan manifest remains unchanged. A separate B27 contract
extends only Run provenance and Claim trace expectations with the four required
owner relations, repository batches, and ID predicates. Existing purity and
topology restrictions remain enforced; unit cases assert the exact additive
delta and unchanged downstream/audit contracts.

Standalone Conclusion and novelty reads use one read-only repeatable snapshot;
Conclusion authorization uses protected queries and a fresh final clock/credential
check. Nested verification keeps the caller's transaction. Saved-dependency
failures map to the existing closure code with message
`saved formal provenance is unresolved` and null details. Root absence and
credential/permission failures retain their existing mappings. No repair writes,
new DTO, endpoint, scientific status, or PR2-19 acceptance update was introduced.

## Verification

PostgreSQL **18.6** was used. All uv commands use
`UV_CACHE_DIR=/tmp/researchbase-lane16-uv` because the default cache is outside the
writable workspace. Only the primary agent wrote repository files; sub-agents
performed read-only investigation/review.

Test corruption bypasses only allowlisted guards and catalog-discovered exact FK
triggers in disposable databases, restores their original enabled states, and
commits before fresh readers. Ordinary-role FK SQLSTATE 23503 and immutable-guard
controls remain enforced. The race uses a fresh reader backend to exclude
SERIALIZABLE SIReadLock predicate locks retained by earlier fixture transactions.
It asserts separate backend PIDs, no explicit reader locks, one intact old
snapshot after concurrent corruption commits, and fresh-reader denial.

The broader run exposed the existing B06 global-Artifact regression. The owner
check now preserves global Dataset, Artifact and MetricDefinition semantics while
still rejecting absent owners and non-global owners from another project. The
regression and explicit global-scope cases are included in the final focused run.
Read-only final review confirmed the previous owning-identity, removed-membership
and source-lineage findings are addressed, with no remaining P0/P1 in its bounded
review. No Phase 2 gate acceptance or PR2-19 inventory update is claimed.

| Final focused command | Observed result |
| --- | --- |
| `uv run pyright` | 0 errors, 0 warnings, 0 informations. |
| `uv run ruff format --check .` | 584 files already formatted. |
| `uv run ruff check .` | All checks passed. |
| `uv run pytest -o addopts='' -q tests/unit tests/architecture` | 2,480 passed, 41 warnings in 61.24s (0:01:01). |
| `uv run pytest -o addopts='' -q tests/unit/phase2/test_b27_defensive_closure_read.py tests/architecture/test_b27_defensive_closure_read.py tests/integration/phase2/test_b27_defensive_closure_read.py tests/integration/phase2/test_pr2_19_integrity.py tests/integration/phase2/test_b06_revision_action.py::test_global_artifact_metric_inputs_keep_phase1_owner_semantics` | 59 passed, 122 warnings in 28.37s. |
| `git diff --check` | Exit 0. |

After adding the explicit B27 query-plan contract:

```sh
uv run pytest -o addopts='' -q \
  tests/unit/phase2/test_b27_defensive_closure_read.py \
  tests/unit/test_pr18_explain_contract.py \
  tests/integration/test_pr18_hardening.py
```

Result: **303 passed, 2 warnings in 2.04s**.

Affected PostgreSQL regression command:

```sh
uv run pytest -o addopts='' -q \
  tests/integration/test_pr12_closure.py \
  tests/integration/test_pr13_queries.py \
  tests/integration/phase2/test_pr2_13_scientific_trace.py \
  tests/integration/phase2/test_pr2_11_r2_persistence.py \
  tests/integration/phase2/test_pr2_14_internal_review.py \
  tests/integration/phase2/test_pr2_15_decision.py \
  tests/integration/phase2/test_pr2_15_decision_schema.py \
  tests/integration/phase2/test_pr2_18_*.py \
  tests/integration/phase2/test_pr2_19_integrity.py
```

Result: **181 passed, 315 warnings in 131.73s (0:02:11)**. The later global-scope
compatibility correction is covered by the final 59-test focused run above.

The owner's latest review explicitly requests the full check, superseding the
original instruction to reserve full-suite execution for the loop. Earlier
interrupted attempts are not PASS evidence. The first completed full run had
**1 failed, 6,405 passed, 50 skipped, 4,542 warnings in 6,117.47s**. Its sole
failure was the Phase 1 query-plan inventory rejecting B27's four required owner
tables. The additive B27 contract above fixes that failure without changing the
frozen manifest or audit validators.

Final owner-requested check (each `uv` invocation used the cache override above):

```sh
uv run pyright && uv run ruff format --check . && uv run ruff check . && uv run pytest -o addopts='' -q -rfE -p no:cacheprovider
```

Observed exit status: **0**. Pyright: **0 errors, 0 warnings, 0 informations**.
Ruff format: **584 files already formatted**. Ruff lint: **All checks passed!**
Pytest: **6,408 passed, 50 skipped, 4,542 warnings in 6,227.99s (1:43:47)**.
Warnings include existing Alembic configuration deprecations and the legacy
mixed-protocol fixtures' already-established-connection warning. No failure or
error remained. The final bounded read-only review found no concrete remaining
P0/P1. No commit, push, branch creation, or gate acceptance was performed.
