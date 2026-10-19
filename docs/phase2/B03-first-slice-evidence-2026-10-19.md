# B03 first-slice implementation evidence — 2026-10-19

Owner authority: approved B03 first slice and ACCEPTED ADR-0020. This records
implementation/check evidence, not owner acceptance or a Phase 2 gate declaration.

Implemented the research-owned `DiscussionHypothesisService` with
`promote_discussion_to_hypothesis` and `get_discussion_hypothesis_admission`.
The command creates one fresh DRAFT Hypothesis/version 1/current pointer and
atomically retains initial material, exact session/turn/transcript/question and
the existing scoped immutable receipt. Replay returns saved material after legal
draft edits or freezing and uses current HUMAN read entitlement. First admission
requires current HUMAN OWNER/RESEARCHER authority and verified retained transcript
bytes. Exact reads use a lock-free REPEATABLE READ snapshot; writes use READ
COMMITTED and the guide's literal first-statement SHARE inventory, receipt lock,
then candidate lock. Existing SERIALIZABLE consumption paths are unchanged.

Added only migration `0069_b03_discussion_hypothesis` after inspected head
`0068_b21_unresolved_capture`. Existing migration files are unchanged. The new
relation and receipt completeness/immutability guards preserve historical
commands and refuse populated downgrade. Existing head expectations and migration
inventories changed only in values or appended entries. The legacy untyped
promotion remains denied. No transport, B02 or Phase 3 implementation was added.

Existing equivalents/substitutions:

- All proposed module paths exist; no location substitution was needed.
- Phase 1 has no physical hypothesis-version `hash_scheme` column. Its repository
  derives that domain field from `content_hash`. The SQL guard therefore checks
  null content_hash/frozen_at; ordinary domain loading preserves null hash_scheme
  for the DRAFT. No extra column was added.
- Existing JSONB persistence maps absent success criteria to JSON `null`; direct
  SQL can use SQL NULL. The guard accepts both representations of absent criteria
  and rejects non-null criteria. No Phase 1 serialization/hash contract changed.
- Database-derived timestamptz values are converted to UTC for admission DTOs,
  using the existing `to_utc` equivalent independently of the database session zone.

Read-only sub-agents investigated the guide/existing code and reviewed the final
migration, guards, authorization, locking and replay. No remaining P0/P1 finding
was reported. The input-accessibility check and rendering-error normalization
identified during review were addressed by the sole writing agent.

All commands below used `UV_CACHE_DIR=/tmp/researchbase-uv-cache` and the existing
explicit local test database environment. PostgreSQL reported `18.6 (Homebrew)`.
The initial implementation verification below did not run the whole suite. These
are inherited results from the earlier implementation, not fresh takeover results.
The review follow-up records the director-reported full-suite interruption; fresh
focused takeover verification is recorded separately below. No commit, push or
branch was created.

```sh
UV_CACHE_DIR=/tmp/researchbase-uv-cache uv run alembic heads
# 0069_b03_discussion_hypothesis (head)
UV_CACHE_DIR=/tmp/researchbase-uv-cache uv run alembic upgrade head
# exit 0; configured lane database upgraded from 0068 to 0069
UV_CACHE_DIR=/tmp/researchbase-uv-cache uv run ruff check .
# All checks passed!
UV_CACHE_DIR=/tmp/researchbase-uv-cache uv run ruff format --check .
# 743 files already formatted
UV_CACHE_DIR=/tmp/researchbase-uv-cache uv run pyright
# 0 errors, 0 warnings, 0 informations
UV_CACHE_DIR=/tmp/researchbase-uv-cache uv run pytest -o addopts= -q tests/unit tests/architecture
# 5693 passed, 49 warnings in 125.90s
UV_CACHE_DIR=/tmp/researchbase-uv-cache uv run pytest -o addopts= -q tests/integration/phase2/test_pr2_19_discussion.py
# 5 passed, 15 warnings in 10.39s
```

The focused PostgreSQL command includes the new B03 suites, research/discussion
regressions, G4/F4 and all integration suites whose head expectations were touched:

```sh
UV_CACHE_DIR=/tmp/researchbase-uv-cache uv run pytest -o addopts= -q tests/integration/phase2/test_b03_discussion_hypothesis.py tests/integration/phase2/test_b03_discussion_hypothesis_guards.py tests/integration/phase2/test_b04_manuscript_migration.py tests/integration/phase2/test_b05_review_migration.py tests/integration/phase2/test_b08_schema.py tests/integration/phase2/test_b14a_entry_schema.py tests/integration/phase2/test_batch_c_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_04_migration_coverage.py tests/integration/phase2/test_pr2_10_binding_contract.py tests/integration/phase2/test_pr2_10_discussion_persistence.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_pr2_17_authorship_schema.py tests/integration/phase2/test_pr2_19_discussion.py tests/integration/phase2/test_revision_action.py tests/integration/test_pr04_application.py tests/integration/test_pr04_schema.py
```

PostgreSQL run: **325 passed, 843 warnings in 648.18s (10:48)**. No failures or skips.

The B03 tests cover normalized closed DTOs and independent candidate hash vectors;
initial material after edit/freeze; same-request restart/concurrency/conflict;
cross-request/cross-actor duplicate prevention; current authority/expiry; archived
read/replay; OPEN/unbound sessions; corrupt/missing retained provenance; rollback
after identity/version/pointer/receipt/admission/constraint stages; direct SQL
creation closure and graft rejection; exact FKs; immutable history; empty/prior-head
upgrade and protected downgrade. G4 checks one explicit DRAFT and unchanged Claim,
EvidenceRelation, support snapshot, Decision and grant counts. Warnings observed are Alembic configuration deprecations and 16 existing B05
SQLAlchemy connection execution-options warnings. Pyright also printed its
version-update notice.

Intermediate implementation/test-fixture and stale head/inventory failures were
corrected before the final focused results above. `git diff --check` exited 0 after evidence generation. The initial focused run did not cover the three additional lineage inventories
identified by the reviewer; their repair and full verification are recorded below.


## Reviewer follow-up

The reviewer reported three migration-lineage failures. Reproduction by the exact
three node IDs produced **3 failed, 7 warnings in 4.62s**. Each assertion reported
only the extra `discussion_hypothesis_admissions` table. Appended that table to the
expected added inventories in `test_b07_schema.py` and `test_b15_package_schema.py`,
and to the expected dropped inventory in `test_b21_capture_schema.py`. Owning table
constants, FK/trigger checks, downgrade targets and migration 0069 are unchanged.

The [B03 proposal status](../proposals/B03_Discussion_Candidate_Promotion_Contract_DRAFT.md)
is present on line 3, exactly:

> Status: APPROVED by owner 2026-10-19 — first slice authorized for implementation

The physical-schema substitutions are recorded above. Write isolation is specified
by [B03 §7](../proposals/B03_Discussion_Candidate_Promotion_Contract_DRAFT.md#7-transactions-concurrency-and-failure-recovery):
“One READ COMMITTED UoW per write attempt”. The
[§12.2 operation table](../proposals/B03_Discussion_Candidate_Promotion_Contract_DRAFT.md#122-exact-lock-order-and-transactions)
requires “Set connection READ COMMITTED before SQL” for a new write attempt,
and REPEATABLE READ without explicit locks for the exact query. The implementation
follows these owning requirements; unrelated SERIALIZABLE consumption is unchanged.

Exact-node rerun (exit 0):

```sh
UV_CACHE_DIR=/tmp/researchbase-uv-cache uv run pytest -o addopts='' -q tests/integration/phase2/test_b07_schema.py::test_empty_forward_upgrade_and_downgrade tests/integration/phase2/test_b15_package_schema.py::test_clean_upgrade_catalog_and_empty_downgrade tests/integration/phase2/test_b21_capture_schema.py::test_catalog_and_owned_downgrade
# 3 passed, 13 warnings in 6.70s
```

Round 2's full suite did not finish. Per the director's takeover instructions,
the director's cleanup command accidentally killed shard 0. This supersedes the
earlier blocked-run conclusion in this document. The takeover did not observe a
completed full-suite result and claims neither a blocked nor a passing full suite.
The earlier focused counts apply only to their listed files. The loop's next
check owns full-suite execution and its output is the evidence; no full-suite
or gate-success claim is made here.

## Director takeover — focused verification

Changed both freshness predicates in migration 0069 to native xid comparison:
`h.xmin = pg_current_xact_id()::xid` and
`v.xmin = pg_current_xact_id()::xid`, following migration 0057's wraparound rule.
Added an architecture regression assertion pinning both predicates and rejecting
the bigint/text conversion. No accepted migration was edited.

Reviewed every existing head-expectation edit against HEAD. An AST comparison of
17 Python test files confirmed only expected revision values changed, including
the head's expected predecessor; assertion operators, queries and test behavior
are preserved. Exact text comparison confirmed the CI and static-baseline edits
also change only the expected head value. Three migration-lineage inventories
append the new migration, and three table inventories append the new relation;
these inventory additions preserve their exact equality assertions.

Fresh takeover commands (using the existing local `DATABASE_URL` and explicit
`RB_TEST_ADMIN_URL`; server readback: **18.6 (Homebrew)**):

```sh
UV_CACHE_DIR=/tmp/researchbase-uv-cache uv run ruff format --check .
# 743 files already formatted; exit 0
UV_CACHE_DIR=/tmp/researchbase-uv-cache uv run ruff check .
# All checks passed!; exit 0
UV_CACHE_DIR=/tmp/researchbase-uv-cache uv run pyright
# 0 errors, 0 warnings, 0 informations; exit 0
# Pyright also printed its version-update notice.
git diff --check HEAD
# exit 0
UV_CACHE_DIR=/tmp/researchbase-uv-cache uv run pytest -o addopts= -q tests/unit tests/architecture
# 5694 passed, 49 warnings in 75.04s (0:01:15); exit 0
```

The focused PostgreSQL command below selects 22 files; it does not invoke the
whole suite or the sharded runner:

```sh
UV_CACHE_DIR=/tmp/researchbase-uv-cache uv run pytest -o addopts= -q tests/integration/phase2/test_b03_discussion_hypothesis.py tests/integration/phase2/test_b03_discussion_hypothesis_guards.py tests/integration/phase2/test_b04_manuscript_migration.py tests/integration/phase2/test_b05_review_migration.py tests/integration/phase2/test_b07_schema.py tests/integration/phase2/test_b08_schema.py tests/integration/phase2/test_b14a_entry_schema.py tests/integration/phase2/test_b15_package_schema.py tests/integration/phase2/test_b21_capture_schema.py tests/integration/phase2/test_batch_c_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_04_migration_coverage.py tests/integration/phase2/test_pr2_10_binding_contract.py tests/integration/phase2/test_pr2_10_discussion_persistence.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_pr2_17_authorship_schema.py tests/integration/phase2/test_pr2_19_discussion.py tests/integration/phase2/test_revision_action.py tests/integration/test_pr04_application.py tests/integration/test_pr04_schema.py
# 382 passed, 974 warnings in 418.37s (0:06:58); exit 0
```

No failures or skips occurred in either fresh pytest run. PostgreSQL warnings
were Alembic configuration deprecations and 16 existing B05 SQLAlchemy connection
execution-options warnings. The final `git diff --check HEAD` after recording
these results exited 0. No full-suite runner was invoked during this takeover;
the loop's check remains the source of full-suite evidence. No commit, push or
branch was created.
