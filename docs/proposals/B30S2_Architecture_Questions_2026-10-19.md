# B30-S2 architecture questions — 2026-10-19

Status: director decisions recorded 2026-10-19; implementation authorized.
No architecture exception or full PR2-19 gate acceptance is granted.

## AQ-S2-01 — READY/PREPARE grant STALE maintenance

Decision: confirmed production defect, owned by B13. Authorize one forward
hardening migration after 0068, with no new schema. B13 §3.1 requires a failed
current fact gate to yield STALE/GRANT_STALE and explicit maintenance to persist
the state and event. The READY regression constructs both grant and subsequent
OPEN/BLOCKING Issue through owning Application commands.

The 0067 `b13_stale` handler omitted P14B1 from `b14a_admission`, reached through
`b14_consumption_gate`. Migration 0069 adds this deterministic blocker denial.
Its docstring records the audited gate codes: existing P16T1/P16G1/P16C1/P16A1
and retained P16R1/P13S1 remain stale causes; malformed tuple/basis, sealed graph,
hash and history errors continue to propagate. In particular P14P1 and P17F2
must never be caught as blanket stale causes. PREPARE maintenance uses B12;
B17's package-specific admission remains a consumer check. Downgrade restores
the 0067 body exactly. No existing migration changes.

Reviewer follow-up adds direct gate evidence: corrected and retracted source
cases raise P16T1 before READY maintenance persists STALE and its terminal event.
Integrity propagation is tested for both READY (b14a_admission) and PREPARE
(b12_approval_gate, the actual maintenance path). The migration also asserts its
replacement changes the SQL and includes the P14B1 exception entry.

Required regression `test_f9_terminal_grants_cannot_create_effect[stale-ready]`
is unchanged. Focused owner tests cover READY and PREPARE maintenance with
persisted terminal events, integrity-error propagation and exact downgrade.
Current verification is recorded in
[verification.md](../../artifacts/pr_evidence/PR2-19/B30-S2/verification.md).
Historical failure transcripts and duplicate/stripped logs have been removed;
no previous failed run is reclassified as passing.

## AQ-S2-02 — scheduled role expiry

Decision: **BLOCKED — no owning Application command to schedule role expiry**.
`AssignProjectRole` has no effective-until input; `CloseProjectRole` timestamps
closure from the database clock at execution. Do not simulate scheduled expiry
with SQL or add an Application command in this scope.

The F9 subcase inventory explicitly retains this blocker. Credential/grant expiry
across an observed wait remains runnable and tested by
`test_f9_observed_required_wait_crosses_credential_or_grant_expiry`.
Application role closure is revocation evidence, never scheduled-expiry coverage.
The remaining historical PR2-19 blockers and fail-closed full gate are retained.
