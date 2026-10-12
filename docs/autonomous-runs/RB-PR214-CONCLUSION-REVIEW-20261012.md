# PR2-14 ScientificConclusionVersion review: conditional evidence

Accepted base: `616ced51ed9356c7428915b71d794edf37f0101c`.
Isolated worktree: `worktrees/pr2-14-conclusion-review`, branch `feature/pr2-14-conclusion-review`.
Implementation commits: `a0810c61b0919b2f713656b3f8d37d0602f283ba`, then remediation `e28f7a84b8313e945af020c180ccaa22b675c4ef`.
This evidence file is a separate commit; obtain its SHA from Git, avoiding a self-reference.

## Frozen scope and contract-to-test map

Phase 2 specification §19.1 permits an InternalReviewRecord target of `scientific_conclusion_version`; architecture correction §6 requires an exact frozen/current-valid target and effective independent REVIEWER/OWNER; the R2 governance contract §1 requires completed exact-version review as a *later* release prerequisite, not as release itself. R2 hash-payload contract §InternalReviewRecord permits an exact ScientificConclusionVersion target. The accepted migration `0040_pr2_14_initial_internal_review` already supplies the concrete FK and trigger guards. R4 temporal authorization requires revalidation after lock waits.

| Requirement | PostgreSQL test |
| --- | --- |
| Frozen, current, same-project exact conclusion/version and hash | `test_conclusion_review_exact_frozen_target_and_initial_issue`; missing/draft/cross-project/stale negative tests |
| Independent effective reviewer with temporal validity | self-review, role closure, observed target-row wait, observed request-lock expiry tests |
| Immutable review and initial OPEN Issue/Event, atomic rejection | positive, role-closure and issue-reference tests |
| Request UUID duplicate/concurrent behavior | positive test replay and concurrent calls |
| Historical hash-bound readback after upstream staleness | `test_historical_conclusion_review_remains_readable_after_upstream_stales` |
| Existing Claim command unaffected | combined PR2-14 regression suite |

The first positive test failed before production changes because the existing command rejected the conclusion target. The historical readback test failed on the first candidate because its verifier required upstream *current* validity; it passed after changing historical verification to `require_current=False`. New review creation still requires `require_current=True`. No migration, schema, PR2-15 command, Approval, or scientific promotion was added.

## Verification

Before writes, the PostgreSQL test server reported user `onephone`, port `55442`, PGDATA `/private/tmp/rb-m3-postgres`, system identifier `7695073913076924777`. Tests used fixture-created disposable databases with exact target checks and fixture teardown. Both `RB_PR211_R2_TEST_ADMIN_URL` and `RB_PR210_TEST_ADMIN_URL` were set to `postgresql+psycopg://onephone@/postgres?host=/private/tmp&port=55442`.

Final commands and results:

```text
uv run --offline pytest -q tests/integration/phase2/test_pr2_14_conclusion_review.py --tb=short
exit 0; 8 passed

uv run --offline pytest -q tests/integration/phase2/test_pr2_10*.py tests/integration/phase2/test_pr2_11*.py tests/integration/phase2/test_pr2_12*.py tests/integration/phase2/test_pr2_13*.py tests/integration/phase2/test_pr2_14*.py --tb=short
exit 0; 70 passed (includes the eight above; counts are not additive)

uv run --offline ruff check src/researchbase/application/internal_review.py src/researchbase/persistence/internal_review_repository.py tests/integration/phase2/test_pr2_14_conclusion_review.py
exit 0; all checks passed

uv run --offline pyright src/researchbase/application/internal_review.py src/researchbase/persistence/internal_review_repository.py tests/integration/phase2/test_pr2_14_conclusion_review.py
exit 0; 0 errors, 0 warnings
```

One earlier combined run omitted `RB_PR210_TEST_ADMIN_URL` and failed at fixture setup; the correctly configured rerun above passed. Historical cancellation tests, legacy migration-list assertion and repository-wide Pyright were not run here and are not claimed as passes.

## Independent review

First read-only review of `a0810c6`: no P0/P1; P2 historical readback after upstream staleness. Reproduced with a red PostgreSQL test, then fixed narrowly. Fresh read-only review of frozen `e28f7a8`: **PASS; no P0/P1**. Residual P2: replaying the same request UUID after the conclusion later becomes STALE fails current-validity validation before looking up the stored review. This matches existing ClaimVersion behavior; historical read itself works. The general replay-after-staleness policy remains a follow-up, not a claim of a new PASS.

## PR2-15 concurrency preflight: design only

**VERIFIED_EXISTING_BEHAVIOR:** Initial ReviewRecord insertion under migration 0040 checks and locks the concrete target; the Application also takes a request advisory lock and conclusion/version row locks. A separate ReviewIssue insert for an existing review locks the ReviewRecord row, not the ScientificConclusionVersion target row. The diagnostic PostgreSQL test observed an Issue insert proceed while a target-row lock was held, but wait when the ReviewRecord row was locked. Severity is explicit; an OPEN issue is not automatically a BLOCKING-severity issue.

**PROPOSED_FUTURE_PROTOCOL, not implemented:** A future Decision eligibility check and every conflicting Issue write would require a common serialization point or another frozen, proven transaction protocol. If a blocking Issue commits before a future check, a consistent check can observe it. If the check starts first, target-row locking alone does not exclude a later Issue insert. End-to-end Issue-write-versus-Decision-check serialization cannot be verified without an approved and implemented Decision command.

**REQUIRES_CONTRACT_APPROVAL:** The PR2-15 `record_decision(INTERNAL_SCIENTIFIC_RELEASE, PROCEED)` proposal remains unapproved. Issue resolution is not implemented. R2 governance describes ADDRESSED after exact frozen result/RevisionAction and independent reviewer validation, and DISMISSED after DecisionRecord/OWNER validation. Thus the ADDRESSED route has no apparent Decision cycle, while a blocking OPEN issue requiring a Decision to dismiss could conflict with a future PROCEED precondition requiring no OPEN blocking issue. The precise no-change/dismissal rule remains unresolved and requires owner contract choice.

No retained M2/M3 database, CAS, policy, or authentication state was touched. PR2-14 conditional development remains PARTIAL. Formal PR2-14/15 acceptance, PR2-15 contract approval and implementation, M3 Human Gate, TDG2 activation and M4 remain blocked or unapproved.

Resume: inspect this worktree at its evidence HEAD and frozen implementation `e28f7a84b8313e945af020c180ccaa22b675c4ef`; resolve PR2-15's normative Issue/Decision choices before any Decision implementation. Do not infer formal acceptance from this conditional result.
