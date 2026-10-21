# PR2-13 Citation rebinding integrity recovery

## Identity and scope

- Accepted base evidence HEAD: `ccfd516b9828b6aa500811ece930f9d1672efe27`.
- Isolated worktree: `worktrees/pr2-13-cite-integrity`, branch `feature/pr2-13-cite-integrity`.
- Implementation: `4f0d32b5bc71c2db848a50ce4f1f284ffa86bf6f`.
- Frozen invariant and design: `docs/phase2/PR2-13-citation-rebinding-decision.md`.
- Replaced only the existing `pr213_citation_guard()` function in forward migration 0039. Accepted migrations 0036–0038 were not edited. No new table, column, index or trigger was created.

## Reproduction and verification

- Test PostgreSQL: port 55442, system identifier `7695073913076924777`; fixture created only uniquely named `researchbase_pr210_test_*` and `researchbase_pr211_r2_test_*` databases and dropped them. A post-test read-only catalog query returned no matching test database.
- Before 0039, `test_citation_parent_cannot_be_rebound_by_direct_sql` failed, exit 1: `Failed: DID NOT RAISE DBAPIError`. Direct SQL moved a valid citation row from one DRAFT manuscript to another, while changing section, ordinal and purpose.
- After 0039, the exact multi-column update and two concurrent reparent attempts fail with `P17D3`. Same-parent DRAFT display edits and replacement by another eligible frozen same-project SourceVersion succeed. DRAFT and unlinked source substitutions fail. Attempted FROZEN SourceVersion regression to DRAFT fails under the accepted source guard.
- Existing row survives upgrade; nonempty downgrade refuses to remove the new protection. Empty upgrade/downgrade checks the function body, one citation trigger and unchanged table/column catalog. Transaction rollback and reconnect readback pass.
- Combined command: `RB_PR210_TEST_ADMIN_URL='postgresql+psycopg://onephone@/postgres?host=/private/tmp&port=55442' RB_PR211_R2_TEST_ADMIN_URL='postgresql+psycopg://onephone@/postgres?host=/private/tmp&port=55442' uv run pytest -q tests/integration/phase2/test_pr2_10_binding_contract.py tests/integration/phase2/test_pr2_11_r2_persistence.py tests/integration/phase2/test_pr2_12_publication_draft.py tests/integration/phase2/test_pr2_12_migration.py tests/integration/phase2/test_pr2_13_citation_placement.py tests/integration/phase2/test_pr2_13_claim_placement.py tests/integration/phase2/test_pr2_13_artifact_placement.py tests/integration/phase2/test_pr2_13_citation_rebinding.py tests/architecture/test_import_boundaries.py tests/architecture/test_pr2_00_boundaries.py -k 'not test_migration_lineage_preserves_phase1_and_adds_authorized_phase2_migration' --tb=short`.
- Combined result: 55 passed, exit 0. Ruff: PASS, exit 0. Focused Pyright: 0 errors/0 warnings, exit 0. Alembic: exactly one head `0039_pr2_13_citation_rebinding_guard`. `git diff --check`: PASS.
- Historical Artifact migration catalog test was pinned to 0038 instead of floating `head`; no production behavior changed by that test edit.
- Existing baseline failures tracked separately: legacy migration-list assertion excluded; two historical execution-service cancellation failures not run; repository-wide Pyright's 95 baseline diagnostics not rerun and not claimed as PASS.

## Independent review

One fresh read-only reviewer assessed exact implementation SHA `4f0d32b5bc71c2db848a50ce4f1f284ffa86bf6f` against frozen PR2-13 contracts and the SQL regression. Verdict PASS; no P0/P1/P2 finding in the delta. Reviewer did not rerun checks; test results above are executor evidence.

## Conditional completeness

| Requirement | Classification | Evidence or remaining work |
| --- | --- | --- |
| SourceVersion Citation placement and direct-SQL binding | COMPLETED | 0036 plus corrective 0039; authenticated DRAFT read/write, exact target, guard and tests. |
| Claim/Conclusion placement | COMPLETED | Accepted implementation `b9d8a94a033abbb82fd18764325070eca02019f0`, evidence `89b2cfa48c75b9b110109100c7b566480134cf04`. |
| Artifact placement | COMPLETED | Accepted implementation `539951cef96ea628766a13ca525af659b70477b1`, evidence `ccfd516b9828b6aa500811ece930f9d1672efe27`. |
| Unified ManuscriptVersion scientific trace query | DEVELOPMENT_ONLY | Phase 2 specification §PR2-13 explicitly names it. Current per-kind DRAFT `trace()` methods do not establish the unified query or upstream evidence traversal. It is outside this bounded 0039 repair. |
| Formal PR2-13 admission and retained deployment | REQUIRES_FORMAL_ADMISSION | M3 Human Gate remains blocked; no formal acceptance or deployment performed. |

Thus PR2-13 conditional development remains PARTIAL despite this Citation repair passing. Citation placement is presentation only; no SUPPORTS, VERIFIED, manuscript freeze, approval or scientific promotion was created. Retained M2/M3 databases and CAS were not connected for writes.

## Resume

Resume from this evidence HEAD in `worktrees/pr2-13-cite-integrity` only after a separate authorized scope for the unified scientific trace query, or follow the formal admission process once its external prerequisites are satisfied. Do not treat this conditional repair as formal PR2-13 acceptance.
