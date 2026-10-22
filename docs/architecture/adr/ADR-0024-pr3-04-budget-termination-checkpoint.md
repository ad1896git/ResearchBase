# ADR-0024 — PR3-04 budget, termination and human checkpoints

Status: ACCEPTED — APPROVED by owner 2026-10-21 (all recommended decisions). PR3-04 is
authorized for implementation after its execution pack passes two director reviews.

Contract: [PR3-04 draft](../../proposals/PR3-04_Budget_Termination_Checkpoint_Contract_DRAFT.md).
Ends the policy staging of [ADR-0022](ADR-0022-pr3-01-policy-staging-input-layout.md).

| Decision | Approved |
|---|---|
| D1 Schema | Six typed runtime tables; research_tasks gains three policy FKs, all NULL (planning) or all set; all required for any executable state; no backfill or dummy policy. |
| D2 New budget after stop | Terminal history stays terminal; continuation is a new explicitly linked task with a Human-approved budget; no counter reset. |
| D3 Progress/accounting | Consecutive same-step failures and pinned comparable score; optional thresholds disabled; unknown outcomes keep worst-case charges. |
| D4 Checkpoints | Verified Human OWNER only; default expiry 24 hours; fail closed on expiry/rejection/modification. |
| D5 Autonomy | A1/A2 default; A3 disabled without an explicit bounded policy. |
| D6 Integration | PR3-01 lock protocol and existing ErrorCodes; real execution needs later gateway/worker evidence. |
