# Governance replay timeout follow-ups

These local tickets record the findings from the 2026-10-21 issue-disposition
review. Owner: **ResearchBase Phase 2 governance maintainer**, with the project
owner responsible for triage and assignment to a named implementer. No external
issue has been created. Both tickets are resolved by the scoped failed-wait recovery fix described
below; this is not a global governance gate acceptance claim.

## RB-GOV-REPLAY-001 — Decision failed-wait receipt recovery

Priority: **P1 MAJOR**. Status: **RESOLVED (worktree; commit pending)**.

Targets: `DecisionService.record_revision_decision` and
`record_ready_for_submission_decision`, and
`persistence/uow.py::_decision_database_error`.

Original evidence: the generic normalizer maps `55P03` to `INVALID_STATE_TRANSITION`.
These command handlers return the error without a fresh entitled comparison of a
potentially completed same-key result. Their successful lock waits do compare
saved records before admitting a new effect.

Required action (completed below): agree the command-specific timeout/read-recovery contract;
perform only entitled exact actor/project/material/history reads after rollback;
retain finite mutation retry eligibility. Reproduce real PostgreSQL failed waits
with completed, conflicting, unauthorized and absent results. Record the bounded
behavior when a winner remains uncommitted; do not promise eventual success from
a finite timeout. Run owning Decision suites and the required check.

## RB-GOV-REPLAY-002 — Legacy revision failed-wait receipt recovery

Priority: **P1 MAJOR**. Status: **RESOLVED (worktree; commit pending)**.

Targets: `RevisionActionService.record_revision_action`, legacy
`record_concern_re_review(novelty=False)`, and their generic Decision normalizer.

Original evidence: the same `55P03` fallback bypasses the saved action/link read after a
failed wait. Action and correspondence identities, readback checks and retry
policies differ, so a global normalizer edit alone is insufficient.

Required action (completed below): define scoped receipt-only recovery for each command and test
its actor, project, normalized material, historical closure and current read
entitlement. Preserve existing lock order and finite mutation retry rules. Use
actual database wait witnesses and cover the uncommitted/rolled-back winner.
Run owning revision and correspondence suites and the required check.

## Resolution — RB-GOV-REPLAY-001/002

Fix commit: **pending integration**. This task explicitly forbids committing,
pushing or creating a branch, so no fix commit hash is claimed. The worktree is
based on `f0bff71` ("Fix same-key concurrent replay after a lock timeout in issue
disposition"), whose receipt-recovery protocol this change follows. The integrator
must replace this pending reference with the eventual fix commit hash.

After `55P03`, each of the four targeted writers exits its failed UoW and performs
one exact-key read-only lookup under current read entitlement. Saved actor,
project, normalized material and frozen historical provenance are checked using
the existing readback paths. An entitled matching receipt replays; changed
material conflicts; revoked entitlement fails; an absent receipt yields a
sanitized `CONCURRENT_MODIFICATION` timeout. The generic Decision normalizer
retains its classification for other writers and adds internal receipt-recovery
metadata consumed only by these scoped paths. Existing `40001`/`40P01` mutation
retry budgets and lock order remain unchanged.

The lookup is bounded: if the winner remains uncommitted at its snapshot, the
waiter returns the sanitized timeout immediately, even if the winner later
commits. It never retries a mutation or polls for eventual completion.

Deterministic PostgreSQL regressions in
`tests/integration/phase2/test_governance_failed_wait_recovery.py`:

- `test_revision_decision_failed_wait_receipt` (RB-GOV-REPLAY-001)
- `test_readiness_decision_failed_wait_receipt` (RB-GOV-REPLAY-001)
- `test_revision_action_failed_wait_receipt` (RB-GOV-REPLAY-002)
- `test_concern_re_review_failed_wait_receipt` (RB-GOV-REPLAY-002)

Each observes the advisory wait through `pg_locks`, witnesses the actual driver
`55P03`, and pauses error delivery while the winner commits or rolls back. Cases
cover replay, changed material, revoked entitlement, winner rollback and a still
uncommitted winner. Legacy correspondence has no independent material payload:
its action/re-review pair is its exact key, so changed material at the same pair
cannot be represented. Its cases cover all four applicable outcomes. Recovery
assertions require exactly one read-only transaction and forbid mutation and
lock SQL. Readiness additionally checks fresh validity-evaluation timestamp
ordering and equality of every other receipt field.

All 19 cases failed against the original three source modules from `f0bff71`
with real witnessed failed waits. See
[verification evidence](Governance_Replay_Timeout_Verification.md) for commands,
results and the final focused verification counts. No skip/xfail or existing
assertion was loosened; the normalizer unit assertion now requires the exact new
internal recovery metadata. The readiness timeout-code assertion was also
updated to the scoped timeout contract and strengthened with an exact read-only
recovery-session count; its entire owning race file passed afterward.
