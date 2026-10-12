# PR2-13 unified ManuscriptVersion scientific trace — conditional evidence

## Identity and frozen scope

- Accepted base: `57b70f38fc0a9317bf537beae19b9af14ca04ee0`.
- Worktree: `worktrees/pr2-13-scientific-trace`; branch: `feature/pr2-13-scientific-trace`.
- Initial implementation: `7a71424b24d3d73ee44a0f3e1edf5f31cd8eac86`.
- Reviewed corrected implementation: `a5bcd3db383c4022f4f11304e5b8536ef0ec60a1`.
- Contract matrix: `docs/phase2/PR2-13-scientific-trace-matrix.md`; authority: frozen Phase 2 specification §33.1 and §PR2-13, accepted placement and upstream scientific contracts.
- Only a read-only Application query and fixed-batch repository queries were added. No route, table, column, index, migration, scientific promotion or retained deployment operation was added.

## Reproduction and correction

The first independent review found a P2 trace-association defect: all literature support snapshots of a traced Claim were returned, although a placed ConclusionVersion pins one exact snapshot. A new disposable PostgreSQL test created two unreviewed contradictory snapshots, froze a test-only Conclusion against the older one, and failed on the initial implementation (`2 != 1`, exit 1). The correction joins `scientific_conclusion_claim_inputs.literature_support_snapshot_id` to the matching snapshot and ClaimVersion and returns the exact ConclusionVersion ID. The same test then passed, returning only the pinned snapshot. No human VERIFIED review was fabricated.

## Verification

- Disposable PostgreSQL port `55442`, system identifier `7695073913076924777`; tests created and dropped uniquely named `researchbase_pr211_r2_test_*` databases. A post-test catalog query found none. Retained M2/M3 databases were not targeted.
- Focused: `RB_PR211_R2_TEST_ADMIN_URL='postgresql+psycopg://onephone@/postgres?host=/private/tmp&port=55442' uv run pytest -q tests/integration/phase2/test_pr2_13_scientific_trace.py --tb=short`: **4 passed**, exit 0.
- Combined: `RB_PR210_TEST_ADMIN_URL='postgresql+psycopg://onephone@/postgres?host=/private/tmp&port=55442' RB_PR211_R2_TEST_ADMIN_URL='postgresql+psycopg://onephone@/postgres?host=/private/tmp&port=55442' uv run pytest -q tests/integration/phase2/test_pr2_10_binding_contract.py tests/integration/phase2/test_pr2_11_r2_persistence.py tests/integration/phase2/test_pr2_12_publication_draft.py tests/integration/phase2/test_pr2_12_migration.py tests/integration/phase2/test_pr2_13_citation_placement.py tests/integration/phase2/test_pr2_13_claim_placement.py tests/integration/phase2/test_pr2_13_artifact_placement.py tests/integration/phase2/test_pr2_13_citation_rebinding.py tests/integration/phase2/test_pr2_13_scientific_trace.py tests/architecture/test_import_boundaries.py tests/architecture/test_pr2_00_boundaries.py -k 'not test_migration_lineage_preserves_phase1_and_adds_authorized_phase2_migration' --tb=short`: **59 passed**, exit 0.
- `.venv/bin/ruff check --no-cache` on changed Python files: PASS, exit 0. `.venv/bin/pyright` on changed production files: 0 errors, 0 warnings, exit 0. `git diff --check`: PASS. `uv run alembic heads`: exactly `0039_pr2_13_citation_rebinding_guard`; no migration changed.
- Test coverage: four placement kinds, citation-only semantics, direct Claim→Measurement→Run evidence, exact Conclusion Claim/literature input paths, unreviewed contradictory evidence, exact frozen snapshot pin, empty and duplicate paths, unauthorized/cross-project/missing targets, stable reconnect readback, and unchanged counted scientific tables. StatisticalResult multi-input and genuine HUMAN VERIFIED paths were not exercised in this slice; no such retained evidence was created.
- Known baseline failures remain separate: obsolete migration-list architecture assertion excluded; two execution-service cancellation failures not run; repository-wide Pyright baseline diagnostics not rerun or claimed as PASS.

## Independent review

First fresh read-only reviewer: BLOCKED for P2 exact snapshot association. Fresh read-only reviewer of `a5bcd3d`: PASS, no P0/P1/P2 in the remediation or cumulative query. Reviewers did not rerun tests. Maximum one remediation round used.

## PR2-13 frozen-scope coverage

| Obligation | Status | Evidence |
| --- | --- | --- |
| SourceVersion Citation Placement and direct-SQL binding integrity | COMPLETED | Accepted 0036 and 0039 slices; evidence HEAD `57b70f3`. |
| Claim/Conclusion Placement | COMPLETED | Accepted implementation `b9d8a94a033abbb82fd18764325070eca02019f0`. |
| Artifact Placement | COMPLETED | Accepted implementation `539951cef96ea628766a13ca525af659b70477b1`. |
| Unified ManuscriptVersion scientific trace query | COMPLETED | `a5bcd3d`, 4 focused and 59 combined PostgreSQL tests, independent PASS. |
| Formal admission/deployment | REQUIRES_FORMAL_APPROVAL | M3 Human Gate blocked; no formal PR2-13 acceptance or retained deployment. |

Conditional technical development is COMPLETE under frozen §PR2-13; this is not formal acceptance. No production schema delta, retained M2/M3 write, live provider contact, root policy installation, fabricated human verification, or protected-branch merge occurred.

## Resume

Resume at the evidence HEAD of `worktrees/pr2-13-scientific-trace` for any separately authorized future task. Do not rerun this accepted conditional slice or infer formal PR2-13/M4 admission from it.
