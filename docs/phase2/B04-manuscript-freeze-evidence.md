# B04 first-slice implementation evidence — 2026-10-15

This records the initial implementation runs. [Review remediation and the subsequently authorized full check](B04-review-remediation.md) supersede the unresolved-failure and focused-only status below.

Owner authorization: the B04 proposal status is `APPROVED by owner 2026-10-15 — first slice authorized for implementation`.

Implemented Application/persistence/readback only: initial manuscript seal and NULL-to-exact-version Publication pointer, literal placement/content digests, complete owner closure and CAS verification, exact-version preview/history, natural replay, scoped database errors and bounded retries. Publication remains DRAFTING. Existing draft creation and placement DTOs remain available. No new transports, tables, canonical entities, runtime dependencies, readiness, grants, authorship, package or external effects were added.

Migration: `0048_b04_manuscript_freeze` follows the inspected head `0047_pr2_18_novelty_prior_art`. No historical migration was edited. Head expectation values and migration inventory entries were updated. Preflight rejects incompatible document/placement/seal material with IDs; downgrade preserves frozen history. No commit, push or branch was created.

Writes acquire the literal sorted SHARE inventory as their first transaction statement, then project, publication and exact-version coordination in READ COMMITTED. Exact reads begin REPEATABLE READ, READ ONLY before authorization, use protected nonlocking owner adapters, and finish with fresh credential/time validation. B04 write factories opt into connection options using `create_database_engine(..., b04_write_timeouts=True)` to bound the first SHARE wait; ordinary engine callers retain server defaults. Tests observe PostgreSQL blocking, not just scheduling delays.

Existing equivalents/substitutions: the existing conclusion owner readback calls its derived state `validity`; B04 maps this into `current_validity`. Existing `enable_revision_action_snapshot_reads()` supplies protected owner adapters and now also a protected Publication adapter. Existing placement/trace constructors gain an optional ArtifactStore argument so existing draft callers retain their signatures and frozen callers can supply CAS verification. The candidate migration path and all new module paths match the guide. No semantic or architectural contradiction was found.

Read-only persistence and closure reviews found no remaining P0/P1 after fixing transitive source fulltext/correction-basis CAS/validity and exact predecessor verification. Corrected sources verify retained predecessor material without inheriting the predecessor's derived staleness. Regression fixtures consolidate existing separate CAS roots into one store; production storage semantics are unchanged.

## Initial observed checks (historical)

Server: PostgreSQL **18.6 (Homebrew)** on aarch64-apple-darwin27.0.0.

| Command | Observed result |
| --- | --- |
| `UV_CACHE_DIR=/private/tmp/researchbase-uv-cache uv run --offline ruff format --check .` | Exit 0; 546 files already formatted. |
| `UV_CACHE_DIR=/private/tmp/researchbase-uv-cache uv run --offline ruff check .` | Exit 0; All checks passed. |
| `UV_CACHE_DIR=/private/tmp/researchbase-uv-cache uv run --offline pyright` | Exit 0; 0 errors, 0 warnings, 0 informations. |
| Unit/architecture command below | 2,214 passed, 1 failed, 40 warnings in 65.30s; inherited whitespace failure described below. |
| `UV_CACHE_DIR=/private/tmp/researchbase-uv-cache uv run --offline pytest tests/test_architecture.py -o addopts='' -q -ra --tb=short` | 12 passed in 0.34s. |
| Focused PostgreSQL regression command below | 263 passed, 640 warnings in 185.65s. |
| B04/G5 final slice command below | 70 passed, 214 warnings in 66.34s. |
| Additional transaction retry command below | 4 passed, 12 warnings in 3.66s. |
| Additional direct placement race command below | 3 passed, 9 warnings in 2.40s. |
| Final closure/G5 rerun below | 26 passed, 78 warnings in 16.51s, after the final explicit conclusion-seal check. |
| `git diff --check` | Exit 0; no whitespace diagnostics. |

Counts overlap between broad regression and B04/G5 runs and must not be summed. The final slice run includes populated nonblocking reads, review/retraction/impact races and mixed Decision/Novelty repository coordination probes; those probes preserve existing owner lock orders and do not create Decision/Novelty effects. The two additional commands cover tests added after that run collected its tests. The retry tests inject real PostgreSQL transaction-aborting SQLSTATEs after staged seal/pointer changes and verify rollback plus fresh UoWs, or exhaustion after three attempts.

Unit/architecture exact command:

```bash
RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres UV_CACHE_DIR=/private/tmp/researchbase-uv-cache uv run --offline pytest tests/unit tests/architecture -o addopts='' -ra --tb=short
```

The sole failure in the initial unit/architecture run was `tests/unit/phase2/test_pr2_04_static_acceptance.py::test_candidate_static_gates_and_inherited_formatter_delta`. Its inherited baseline comparison, `git diff --check b8179f17720ca47c3b25ad9d36f6a8e8d4aa79ff`, reports `pr_evidence/pr2-20/3ea9a7ac2f6d2a7f04ad79b907e344b24661a6cfc466be11e02dee1f3725836d/pyright-000.txt:4: new blank line at EOF`. This is the same unrelated evidence-file defect recorded in the approved proposal. That file was unchanged during the initial run. Review remediation subsequently reproduces the failure on clean HEAD and removes the trailing blank line, along with B04-local whitespace defects. The initial red result remains recorded as a failure; see the remediation evidence for current check results.

Focused PostgreSQL exact command:

```bash
RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres UV_CACHE_DIR=/private/tmp/researchbase-uv-cache uv run --offline pytest tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b04_manuscript_migration.py tests/integration/phase2/test_b04_manuscript_races.py tests/integration/phase2/test_pr2_12_migration.py tests/integration/phase2/test_pr2_12_publication_draft.py tests/integration/phase2/test_pr2_13_citation_placement.py tests/integration/phase2/test_pr2_13_claim_placement.py tests/integration/phase2/test_pr2_13_artifact_placement.py tests/integration/phase2/test_pr2_13_citation_rebinding.py tests/integration/phase2/test_pr2_13_scientific_trace.py tests/integration/phase2/test_pr2_19_citation_trace.py tests/integration/phase2/test_m3_evidence.py tests/integration/phase2/test_pr2_11_r2_persistence.py tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_04_migration_coverage.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_pr2_17_authorship_schema.py tests/integration/phase2/test_revision_action.py -o addopts='' -q -ra --tb=short
```

Final B04/G5 exact command:

```bash
RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres UV_CACHE_DIR=/private/tmp/researchbase-uv-cache uv run --offline pytest tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b04_manuscript_migration.py tests/integration/phase2/test_b04_manuscript_races.py tests/integration/phase2/test_pr2_19_citation_trace.py -o addopts='' -q -ra --tb=short
```

Additional transaction rollback/retry exact command:

```bash
RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres UV_CACHE_DIR=/private/tmp/researchbase-uv-cache uv run --offline pytest tests/integration/phase2/test_b04_manuscript_freeze.py::test_retry_aborted_transactions_from_fresh_share_snapshot -o addopts='' -q -ra --tb=short
```

Additional observed placement UPDATE/DELETE/reparent race exact command:

```bash
RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres UV_CACHE_DIR=/private/tmp/researchbase-uv-cache uv run --offline pytest tests/integration/phase2/test_b04_manuscript_races.py::test_freeze_vs_direct_placement_mutation -o addopts='' -q -ra --tb=short
```

Final closure/G5 rerun exact command:

```bash
RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres UV_CACHE_DIR=/private/tmp/researchbase-uv-cache uv run --offline pytest tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_pr2_19_citation_trace.py -o addopts='' -q -ra --tb=short
```

Raw final outputs: [PostgreSQL regressions](b04-evidence/postgres-regressions.txt), [unit/architecture](b04-evidence/unit-architecture.txt), [B04/G5](b04-evidence/b04-g5.txt), [retry](b04-evidence/retry.txt), [placement races](b04-evidence/placement-races.txt), [Pyright](b04-evidence/pyright.txt), [final closure/G5](b04-evidence/final-closure.txt).

The initial request prohibited running the whole suite, so these initial runs were focused. The subsequent review-remediation request explicitly authorizes the full check; its command and result are recorded separately. The implementation scope remains the authorized first slice.
