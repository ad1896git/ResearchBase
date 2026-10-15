# B05 first-slice verification — 2026-10-15

B05 extends existing immutable review records to exact sealed manuscripts and
provides a complete transient basis to later commands. It does not implement
readiness, Decision/Approval, Issue disposition or manuscript supersession.
Technical test actors are disposable fixtures, not formal human acceptance.

The sole new revision is `0049_b05_manuscript_review`, following
`0048_b04_manuscript_freeze`. No historical migration was edited. Head values and
migration inventories were updated. Substitutions and the explicitly deferred
SUPERSEDED integration case are recorded in
[B05 implementation notes](../proposals/B05_Manuscript_Internal_Review_Contract_DRAFT.md#15-first-slice-implementation-notes--2026-10-15).

All commands ran from this repository. PostgreSQL runs used the explicit disposable
PostgreSQL selector below; the tests create and remove their own databases.

```sh
export UV_CACHE_DIR=/private/tmp/researchbase-uv-cache
export RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres
```

## Focused B05 PostgreSQL suites

```sh
uv run --offline pytest tests/integration/phase2/test_b05_manuscript_review.py tests/integration/phase2/test_b05_review_basis.py tests/integration/phase2/test_b05_review_migration.py tests/integration/phase2/test_b05_review_races.py -o addopts='' -q -rfE -p no:cacheprovider
```

Exit 0: **73 passed, 1 skipped, 223 warnings in 61.69s**. The sole skip is
SUPERSEDED manuscript creation, which B04 currently prohibits. FROZEN review,
read/replay, complete basis, CAS/hash corruption, historical invalidity/authority,
rollback, deferred constraints, real deadlock, first-SHARE timeout, mixed protocols,
normal-role SQL phantoms and nonblocking exact snapshot reads were exercised.

## B04 regression

```sh
uv run --offline pytest tests/integration/phase2/test_b04_manuscript_migration.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b04_manuscript_races.py -o addopts='' -q -rfE -p no:cacheprovider
```

Exit 0: **79 passed, 241 warnings in 69.32s**.

## Existing review / Decision / governance regression

```sh
uv run --offline pytest tests/integration/phase2/test_pr2_14_internal_review.py tests/integration/phase2/test_pr2_14_conclusion_review.py tests/integration/phase2/test_pr2_15_coordination.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_pr2_15_decision.py tests/integration/phase2/test_pr2_19_governance.py -o addopts='' -q -rfE -p no:cacheprovider
```

Exit 0: **81 passed, 252 warnings in 85.60s**.

## Migration head, inventory and boundaries

```sh
uv run --offline pytest tests/unit/test_task12_migration_history.py tests/unit/test_ci_migration_head.py tests/unit/phase2/test_pr2_20_inventory.py tests/unit/phase2/test_pr2_04_r8a_host_topology.py tests/architecture/test_b04_boundaries.py tests/architecture/test_b05_review_boundaries.py tests/architecture/test_basic_approval.py tests/architecture/test_import_boundaries.py -o addopts='' -q -rfE -p no:cacheprovider
```

Exit 0: **37 passed, 6 warnings in 1.80s**.

## B05 contract/hash/boundary tests

```sh
uv run --offline pytest tests/unit/phase2/test_b05_review_contract.py tests/unit/phase2/test_b05_review_hash_vectors.py tests/architecture/test_b05_review_boundaries.py -o addopts='' -q -rfE -p no:cacheprovider
```

Exit 0: **81 passed, 1 warning in 0.62s**.

Independent read-only reviews of the final Application/persistence changes and
migration reported no remaining concrete P0/P1 findings. An earlier persisted
Unicode finding was repaired and covered by corruption tests. Unknown database
errors remain unexpected sanitized failures; only deadlock/serialization errors
qualify for at most three complete-UoW attempts.

## All unit and architecture tests

```sh
uv run --offline pytest tests/unit tests/architecture -o addopts='' -q -rfE -p no:cacheprovider
```

Exit 0: **2,297 passed, 41 warnings in 47.58s**.

## Final replay-corruption correction

Saved manuscript review provenance and issue history are verified before
comparing same-target replay material. Corrupted saved hashes therefore fail as
PROVENANCE_CLOSURE_VIOLATION, rather than IDEMPOTENCY_CONFLICT. A request reused
for a different target still conflicts. The existing corrupt-review cases now
exercise replay as well as complete-basis collection.

```sh
uv run --offline pytest tests/integration/phase2/test_b05_manuscript_review.py tests/integration/phase2/test_b05_review_basis.py -o addopts='' -q -rfE -p no:cacheprovider
```

Exit 0: **29 passed, 1 skipped, 87 warnings in 15.59s**. The requested full check
was restarted after this correction; earlier interrupted full attempts are not
counted as passes.


## Legacy deferred-trigger scope correction

The first completed full run reported **1 failed, 5,988 passed, 50 skipped,
3,957 warnings in 5,347.58s**. The failure was the existing normal-SQL
RevisionAction writer regression: a deferred B05 guard had been queued for a
legacy Claim review and queried after the temporary writer role's privileges
were revoked. The new constraint triggers now queue only manuscript-bound rows,
using immutable target bindings and nonlocking predicates. Legacy guard behavior
is preserved. Two new migration cases cover temporary-role teardown before
commit, with and without an initial Issue.

```sh
uv run --offline pytest tests/integration/phase2/test_b05_review_migration.py tests/integration/phase2/test_revision_action.py::test_normal_sql_review_writer_waits_for_revision_without_lock_inversion -o addopts='' -q -rfE -p no:cacheprovider
```

Exit 0: **25 passed, 79 warnings in 13.04s**.

```sh
uv run --offline pytest tests/integration/phase2/test_revision_action.py -o addopts='' -q -rfE -p no:cacheprovider
```

Exit 0: **51 passed, 157 warnings in 42.57s**. The four B05 PostgreSQL
suites were rerun after this correction; their final counts are recorded above.
The requested full check was rerun against the corrected implementation and passed, as recorded below.


## Requested full check — final corrected implementation

```sh
uv run pyright && uv run ruff format --check . && uv run ruff check . && uv run pytest -o addopts='' -q -rfE -p no:cacheprovider
```

Exit **0**. Pyright: **0 errors, 0 warnings, 0 informations**. Ruff format:
**555 files already formatted**. Ruff lint: **All checks passed!**
Pytest: **5,991 passed, 50 skipped, 3,963 warnings in 5,348.46s (1:29:08)**.
The final run includes the corrected legacy-trigger regression, both new
scope cases, migration head/inventory assertions, and all B05 tests. The B05
SUPERSEDED case is the one new explicit skip; the existing B04 schema cannot
produce that state. Review-side predicates accept it for a later authorized PR.
No earlier failed or interrupted run is counted as a pass.
