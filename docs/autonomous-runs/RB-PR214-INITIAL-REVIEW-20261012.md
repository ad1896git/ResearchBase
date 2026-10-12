# PR2-14 Initial Internal Review — conditional development checkpoint

## Lineage and scope

- Starting accepted evidence HEAD: `f40aaed866431a563aef0aa07dbf9b8910cbc749`.
- Isolated worktree: `worktrees/pr2-14-internal-review`, branch `feature/pr2-14-internal-review`.
- Implementation candidate: `c7ef9d68f7e97bf7d2e559dfe7f5304ed25e3033`.
- Reviewed final implementation/test candidate: `08aa6abaa5cda0dd8d3203442b6d9b4d426aabb6`.
- Frozen contract matrix: `docs/phase2/PR2-14-review-slice-matrix.md`.
- Authority: frozen Phase 2 specification §19 and §PR2-14, Phase 2 correction §§4, 6, 7, Global Registry governance table.

This bounded slice supports an independent authenticated REVIEWER/OWNER creating one immutable InternalReviewRecord against an exact, currently valid, frozen same-project ClaimVersion, plus initial OPEN ReviewIssues. The schema uses four concrete target FKs and one-target XOR, but the Application command accepts ClaimVersion only. It does not support other review targets, issue transitions, DecisionRecord, Approval, manuscript freezing or formal admission. All test actors are disposable TEST ONLY principals.

## Verification evidence

- Test PostgreSQL: Unix socket `/private/tmp`, port `55442`, system identifier `7695073913076924777`. The fixture verified `current_user=onephone`, `current_database=postgres`, and exact PGDATA before creating uniquely named `researchbase_pr211_r2_test_*` databases. After the final run, a read-only catalog query found no remaining matching test database.
- Contract-first test initially failed during collection because `researchbase.application.internal_review` did not exist. After implementation, focused disposable PostgreSQL command `RB_PR211_R2_TEST_ADMIN_URL='postgresql+psycopg://onephone@/postgres?host=/private/tmp&port=55442' uv run pytest -q tests/integration/phase2/test_pr2_14_internal_review.py --tb=short --show-capture=no`: **3 passed**, exit 0.
- Combined disposable PostgreSQL and architecture command: `RB_PR210_TEST_ADMIN_URL='postgresql+psycopg://onephone@/postgres?host=/private/tmp&port=55442' RB_PR211_R2_TEST_ADMIN_URL='postgresql+psycopg://onephone@/postgres?host=/private/tmp&port=55442' uv run pytest -q tests/integration/phase2/test_pr2_10_binding_contract.py tests/integration/phase2/test_pr2_11_r2_persistence.py tests/integration/phase2/test_pr2_12_publication_draft.py tests/integration/phase2/test_pr2_12_migration.py tests/integration/phase2/test_pr2_13_citation_placement.py tests/integration/phase2/test_pr2_13_claim_placement.py tests/integration/phase2/test_pr2_13_artifact_placement.py tests/integration/phase2/test_pr2_13_citation_rebinding.py tests/integration/phase2/test_pr2_13_scientific_trace.py tests/integration/phase2/test_pr2_14_internal_review.py tests/architecture/test_import_boundaries.py tests/architecture/test_pr2_00_boundaries.py -k 'not test_migration_lineage_preserves_phase1_and_adds_authorized_phase2_migration' --tb=short --show-capture=no`: **62 passed**, exit 0.
- Ruff on changed Python files: PASS, exit 0. Focused Pyright on new service/repository: 0 errors and 0 warnings, exit 0. `git diff --check`: PASS. Alembic: one head `0040_pr2_14_initial_internal_review`.
- Migration verification: clean upgrade; an empty 0040 downgrade preserves 0039 tables; nonempty downgrade refuses to discard review history. The historical 0038→0039 catalog test was pinned to 0039, replacing its floating `head` assumption. Accepted 0036–0039 migration contents were not edited.
- PostgreSQL negative checks: DRAFT Claim rejected; cross-project and forged-credential request rejected; author self-review rejected; changed review or issue request replay rejected; direct SQL target-hash and multi-target insert rejected; review UPDATE, issue DELETE and issue-event UPDATE rejected; concurrent identical replay returned one record; reconnect readback matched. No LiteratureEvidence VERIFIED event or scientific target mutation occurred.
- Not run as direct tests in this slice: currently invalid or missing Claim target, actual role expiry/revocation, optional issue reference cross-project cases, genuine human review. The guards are present, but no PASS claim is made for those specific negative scenarios. The obsolete migration-list architecture assertion was excluded; two historical execution-service cancellation failures and repository-wide Pyright baseline were not rerun.

## Independent review and gate classification

One fresh read-only independent reviewer reviewed `c7ef9d6`: PASS with no P0/P1 and a P2 negative-test evidence gap. A follow-up read-only review of `08aa6ab` confirmed the added DRAFT Claim, forged credential, SQL XOR, immutable event and changed-issue replay tests: PASS, no P0/P1. Remaining P2 wording gap was resolved by marking unrun cases explicitly in the matrix. The reviewer did not rerun tests.

PR2-09 official STORM thin adapter is SHOULD and remains dependent on an externally pinned upstream interface; the frozen roadmap permits deferral while the native strategy satisfies its gate. PR2-14 is the next unfinished MUST PR. This ClaimVersion initial-review slice is independent for conditional development, while full PR2-14 implementation, M3 Human Gate, formal admission and retained deployment remain blocked or separately unapproved. There was no retained M2/M3 write, provider activation, fabricated HUMAN evidence, root-policy change, protected-branch merge or remote push.

## Resume

Resume from this worktree's separate evidence HEAD only for a separately authorized next slice. The next frozen PR2-14 work is other target types and issue transitions subject to their frozen authorizations and PR2-15 DecisionRecord dependency. Do not infer formal PR2-14/Phase 2 admission from this conditional result.
