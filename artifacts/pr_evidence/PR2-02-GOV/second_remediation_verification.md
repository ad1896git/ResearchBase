# PR2-02-GOV second remediation verification

## Subjects and lineage

- Starting subject: `905c79a4fa40e1570a0319d2a38a286aceda8f04`.
- Governance design subject: `89bbad27f1e636182fcd5d9804a33612a755502f`.
- Initial implementation: `c00efe323a48da063885377f073e2b14c691b330`.
- Initial evidence: `451a779d785ac9becff8cd5f4104c473a7d81cf5`.
- First remediation: `e24f5804ce1c851a7b88cc6f51cefeac4813b00d`.
- First remediation evidence: `905c79a4fa40e1570a0319d2a38a286aceda8f04`.
- Second remediation implementation subject: `1f275548d3c52e9a66043fd7ab95fdd7b9e88317`.
- Evidence is an evidence-only child of that implementation and does not certify its own subject.
- Migration chain: `0020_literature_source_identity` → `0021_source_merge_governance_bridge` → `0021a_source_merge_gov_guards`.
- Phase 1 annotated tag object: `63f6a1d28afa79ce8620fc9233793ab9c40a515d`.
- `phase1-final-v4^{commit}` and the frozen baseline resolve to `d2400fbeca835c89bd802a4e9d647bda01cfd115`.

## Prior independent review findings

The fresh reviewer of the first remediation reported P0=0, P1=1, P2=1, FAIL. The P1 was that basis insertion could race proposal submission because the insert guard only queried for a `SUBMITTED` event. The P2 was that a `PROPOSAL_STALE` event checked shape but did not prove that the proposal's durable basis was stale.

## P1 remediation: serialize and seal the basis

Migration `0021a_source_merge_gov_guards` adds the same proposal-row `FOR UPDATE` coordination to basis inserts and governance-event inserts. Basis insert guards lock the proposal before reading submission state. The submission event trigger locks that same row before capturing counts for all four basis collections (projects, identifiers, source-version snapshots, and evidence). Existing immutable-table triggers continue to deny basis updates and deletes.

The parent proposal, its basis rows, and its submitted event are created atomically by the canonical command. If a competing writer cannot see the uncommitted proposal row, the concrete FK rejects its child row. If an insert reaches a committed proposal, it waits for the proposal lock and then sees the seal. Deferred checks also compare every basis collection's final row count with the immutable count snapshot on the submitted event, so a child insert that reaches commit after waiting cannot alter a sealed set.

PostgreSQL race evidence:

- `test_submission_lock_serializes_late_basis_insert`: transaction A holds the proposal row lock; transaction B attempts a distinct frozen evidence-basis insert. PostgreSQL lock wait was observed in `pg_stat_activity`. After A commits, B is denied with the sealed-basis constraint; the evidence count remains unchanged.
- `test_basis_first_submission_is_atomic_and_rejects_parallel_submit_attempt`: the canonical proposal command pauses after completing basis inserts and before its submitted event. A second transaction attempts submission while the parent is uncommitted and is rejected by the proposal FK. The canonical transaction then submits and commits exactly one event with its complete basis.
- `test_proposal_lock_serializes_canonical_stale_transition`: after a material identifier change, a canonical decision waits behind the proposal lock; once released, it detects the changed basis and commits one stale event.

These tests exercise both basis-first and submission-lock-first orderings. A parallel write to an uncommitted proposal is rejected by the FK; it is not reported as a lock-wait trace. No successful late basis commit was observed.

## P2 remediation: stale is basis-derived

The new deferred stale-event guard checks the frozen effective source/project links and identifier snapshots against current durable rows. A direct stale event with the correct proposal basis hash is rejected while those facts remain current. The existing event validator still enforces affected-project membership, basis hash, command shape, and terminal-state rules. Updates to proposal/event rows remain denied by existing immutability triggers. The canonical Application path commits a stale event only after it recomputes and detects a changed basis; the existing integration coverage exercises that path.

This migration validates the link and identifier state available in the 0021 schema. PR2-02's SourceVersion migration must extend the stale-basis check to its new immutable version references as part of that migration, consistent with the frozen source-merge pack.

## PostgreSQL clean-room reviewer setup

Validated with PostgreSQL `18.6` from `postgres:18-alpine`, using the following disposable, test-only setup. The reviewer should not assume an existing container or inherited `DATABASE_URL`:

```bash
docker run --detach --rm \
  --name researchbase-pr2-02-gov-review-pg \
  -e POSTGRES_USER=researchbase_test \
  -e POSTGRES_PASSWORD=researchbase_test \
  -e POSTGRES_DB=postgres \
  -p 127.0.0.1:55441:5432 \
  postgres:18-alpine

for attempt in $(seq 1 30); do
  if docker exec researchbase-pr2-02-gov-review-pg pg_isready \
      -U researchbase_test -d postgres >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

unset DATABASE_URL
export DATABASE_URL='postgresql+psycopg://researchbase_test:researchbase_test@127.0.0.1:55441/postgres'
uv run alembic upgrade 0018_current_pointer_same_parent_integrity
uv run pytest -q --tb=short \
  tests/integration/phase2/test_pr2_02_gov_migration.py \
  tests/integration/phase2/test_pr2_02_gov_application.py
uv run pytest -o addopts=''
docker stop researchbase-pr2-02-gov-review-pg
```

The base database is intentionally bootstrapped to the frozen Phase 1 schema because Phase 1 catalog tests use it directly. Each Phase 2 integration fixture creates a uniquely named isolated database, upgrades it through the current Alembic head, and drops it afterward. No secret is required; credentials above are local disposable test credentials. PostgreSQL startup and this bootstrap/focused/full-suite sequence were independently simulated from an unset `DATABASE_URL` and a fresh container before writing this evidence.

## Verification results

| Check | Exact command or evidence | Result |
|---|---|---|
| Focused bridge PostgreSQL suite | `uv run pytest -q --tb=short tests/integration/phase2/test_pr2_02_gov_migration.py tests/integration/phase2/test_pr2_02_gov_application.py` | **PASS** — 8 passed on PostgreSQL 18.6 |
| Concurrency | The three named race tests above; lock waits checked through `pg_stat_activity` | **PASS** — no basis row commits after the seal; one submitted event; stale event only after real basis change |
| PR2-00 regression / temporal | Full suite, including `tests/integration/phase2/test_pr2_00_*` | **PASS** — no post-expiry challenge success reproduced; accepted residual P2 not reopened |
| PR2-01 regression | Full suite and `tests/integration/phase2/test_pr2_01_*` | **PASS** |
| Phase 1 regression | Full suite on base database at `0018_current_pointer_same_parent_integrity` | **PASS** |
| Full suite | `uv run pytest -o addopts=''` | **PASS** — 1,875 passed, 2 skipped, 0 failed, 1,877 collected, 82.53 s |
| Ruff | `uv run ruff check .` | **PASS** — all checks passed |
| Pyright | `uv run pyright` | **PASS** — 0 errors, warnings, or informations |
| Raw formatter | `uv run ruff format --check .` | **FAIL as raw command**, exactly the nine inherited baseline files below; 237 files already formatted |
| Changed-Python formatter | `.venv/bin/ruff format --check migrations/versions/0021a_source_merge_governance_guards.py tests/architecture/test_import_boundaries.py tests/integration/phase2/test_pr2_01_migration.py tests/integration/phase2/test_pr2_02_gov_application.py tests/integration/phase2/test_pr2_02_gov_migration.py` | **PASS** — five files already formatted |
| Formatter baseline delta | Current failures minus accepted baseline failures | **PASS** — empty set; no new formatter failures |
| Migration | `.venv/bin/alembic heads`; `.venv/bin/alembic history -r '0020:0021a'`; fresh-install and downgrade tests | **PASS** — one head `0021a_source_merge_gov_guards`, parent 0021; empty downgrade succeeds; populated guard downgrade refuses before DDL |
| Architecture | `tests/architecture/test_import_boundaries.py` in full suite | **PASS** |
| Whitespace | `git diff --check` before implementation commit | **PASS** |
| Phase 1 drift | Frozen migration diff against baseline and full Phase 1 suite | **NO DRIFT** |

Raw formatter failures are the accepted inherited set:

```text
migrations/versions/0004_experiment_spec.py
scripts/pr17dr_evidence.py
tests/integration/test_pr04_application.py
tests/integration/test_pr04_schema.py
tests/integration/test_pr05_application.py
tests/integration/test_pr05_schema.py
tests/integration/test_pr06_application.py
tests/unit/domain/test_pr05_experiment.py
tests/unit/test_pr17dr2_evidence.py
```

## Verification chronology retained

An earlier full-suite attempt on the fresh temporary database had 1,872 passed, 2 skipped, and 3 failed. The base database had incorrectly been bootstrapped to the Phase 2 head, so two Phase 1 catalog tests saw Phase 2 indexes; the CI head assertion also still named 0021. The base database was restored to migration 0018, the CI assertion and migration-head expectations were updated, and the complete suite was rerun successfully with 1,875 passed, 2 skipped, and no failures.

During race-test authoring, early test attempts also failed because the harness used a duplicate key, read an uncommitted proposal as if it were committed, and initially passed a list where a UUID was required. Those were corrected in the tests; the final two-lock-wait tests and the basis-first atomicity test pass on PostgreSQL 18.6. These setup failures did not establish a successful late basis write.

The final independent remediation review has not started. It must use a new review-only context, start PostgreSQL from the committed setup above, inspect the exact remediation diff and rerun critical checks. This evidence does not certify its own Git subject.
