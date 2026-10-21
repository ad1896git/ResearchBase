# PR3-00 contract freeze

Owner authorization: 2026-10-20, PR3-00 only, under
[ADR-0021 (TDG-3)](../architecture/adr/ADR-0021-tdg3-phase3-technology-decisions.md).
This freezes proposal [PR3-00 §§5–6](../proposals/PR3-00_Agent_Runtime_Bootstrap_Contract_DRAFT.md#5-implementation-guide--future-work-only)
with the concrete revision and bounded verification requested by the owner.

The accepted Phase 2 baseline is commit `286cd9a`, migration
`0075_m1_reconsideration`, recorded in the
[2026-10-20 acceptance record](../phase2/phase2_acceptance_2026-10-20.md),
[exit report](../phase2/phase2_exit_report.md) and its independent review.
Historical baseline evidence: 12,524 passed, 66 skipped, zero failed; this is not a
new verification run. Existing Phase 2 deferrals remain recorded there.

Scope: empty package markers for agent_runtime/{domain,application,ports,services},
strategies/scientific, capabilities/{coding,compute,sandbox,analysis,model},
adapters/{coding,compute,runtime}, and missing parents; one empty forward migration
`0076_agent_runtime_bootstrap` directly after `0075_m1_reconsideration`; recursive
boundary guards, disposable PostgreSQL 18 verification, development commands and
evidence. Current-head pins advance; historical Phase 2 round trips retain their
accepted upper bound. No accepted migration bytes change.

No runtime dependency, schema object, task model, API/CLI command, worker, provider,
policy activation or harness modification is authorized. Future callers must use
the existing Application Command/Query → port/UoW → persistence boundary.
Agent output remains candidate material; development harness and product runtime
remain separate. Bootstrap does not establish later runtime guarantees.

[ADR-0022](../architecture/adr/ADR-0022-pr3-01-policy-staging-input-layout.md)
records decisions for PR3-01 only; it does not authorize that implementation.
TDG-3's later sandbox/compute/coding/model intake obligations remain in their
owning PRs. No technology is activated here.

Verification is focused: static checks, unit/architecture tests and PostgreSQL
migration suites touched by this PR. The enclosing loop owns the full suite and
its resulting evidence. After PR3-00 evidence: **STOP**. PR3-01 requires separate
owner authorization. No existing Status line is changed.
