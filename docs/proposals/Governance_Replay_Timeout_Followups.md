# Governance replay timeout follow-ups

These local tickets record the findings from the 2026-10-21 issue-disposition
review. Owner: **ResearchBase Phase 2 governance maintainer**, with the project
owner responsible for triage and assignment to a named implementer. No external
issue has been created. Both tickets remain OPEN and prevent a global governance
gate acceptance claim.

## RB-GOV-REPLAY-001 — Decision failed-wait receipt recovery

Priority: **P1 MAJOR**. Status: **OPEN**.

Targets: `DecisionService.record_revision_decision` and
`record_ready_for_submission_decision`, and
`persistence/uow.py::_decision_database_error`.

Evidence: the generic normalizer maps `55P03` to `INVALID_STATE_TRANSITION`.
These command handlers return the error without a fresh entitled comparison of a
potentially completed same-key result. Their successful lock waits do compare
saved records before admitting a new effect.

Required action: agree the command-specific timeout/read-recovery contract;
perform only entitled exact actor/project/material/history reads after rollback;
retain finite mutation retry eligibility. Reproduce real PostgreSQL failed waits
with completed, conflicting, unauthorized and absent results. Record the bounded
behavior when a winner remains uncommitted; do not promise eventual success from
a finite timeout. Run owning Decision suites and the required check.

## RB-GOV-REPLAY-002 — Legacy revision failed-wait receipt recovery

Priority: **P1 MAJOR**. Status: **OPEN**.

Targets: `RevisionActionService.record_revision_action`, legacy
`record_concern_re_review(novelty=False)`, and their generic Decision normalizer.

Evidence: the same `55P03` fallback bypasses the saved action/link read after a
failed wait. Action and correspondence identities, readback checks and retry
policies differ, so a global normalizer edit alone is insufficient.

Required action: define scoped receipt-only recovery for each command and test
its actor, project, normalized material, historical closure and current read
entitlement. Preserve existing lock order and finite mutation retry rules. Use
actual database wait witnesses and cover the uncommitted/rolled-back winner.
Run owning revision and correspondence suites and the required check.
