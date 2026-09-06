# PR-18 Hardening Design

## Status

Approved implementation contract for PR-18 Hardening. This document freezes the
scope for the implementation subject; it does not authorize Phase 2.

## Objective

Harden and independently verify the finalized Phase 1 surface without changing
accepted Phase 1 semantics. PR-18 is verification-first: production changes are
permitted only when a focused check demonstrates a defect required by this
contract.

## In scope

- PostgreSQL catalog and required index verification.
- EXPLAIN-plan baselines for the existing Phase 1 read paths.
- Error and structured-log redaction audit.
- Architecture-test coverage for existing boundaries.
- Agent-ready Core boundary audit only.
- API and CLI examples using the frozen Phase 1 surface.
- Classification and disposition of relevant TODO/FIXME markers.
- Final architecture-TODO gate with no unexplained architecture-critical marker.
- PR-18-specific reproducible evidence in `artifacts/pr_evidence/PR-18/`.

## Explicitly out of scope

- Phase 2 runtime, schema, APIs, migrations, flags, or scaffolding.
- Agent framework, orchestration, persistence, scheduling, or agent APIs.
- Speculative architecture changes, API redesign, storage redesign, or new
  subsystems.
- Proactive index or migration additions without a demonstrated defect.
- Changes to accepted PR-17D semantics, evidence protocol, or Phase 1
  boundaries.

## Frozen invariants

The implementation preserves history protection, migration `0016_pr17d_history_protection`,
WriteResult behavior, historical exactness, provenance, hash invariance, adapter
equivalence, database invariants, transaction atomicity, concurrency behavior,
evidence reproducibility, JUnit accounting, fail-closed command accounting,
credential redaction, repository-relative evidence, and deterministic closure
evidence.

The existing Application/Core boundary remains the only path for API/CLI
behavior. Adapters do not own domain persistence or transactions. The Core does
not import agent frameworks, vendor-specific agent state, or Phase 2 runtime
objects.

## Acceptance criteria mapped to tests and evidence

| Criterion | Direct verification | Evidence |
| --- | --- | --- |
| Required catalog/index invariants are present and correct | PostgreSQL catalog tests in `tests/integration/test_pr18_hardening.py` | `catalog_verification.json` |
| Existing critical read paths have stable, reviewed EXPLAIN baselines | PostgreSQL EXPLAIN tests with normalized plans | `query_explain_baselines.json` |
| Errors and logs do not expose credentials or raw internal details | Unit tests for structured logging, HTTP errors, and CLI errors | `error_log_audit.md` |
| Architecture boundaries remain enforced | Static architecture tests and AST/import checks | `architecture_verification.md` |
| Core is agent-ready without implementing agents | Boundary audit tests; no agent runtime or persistence symbols | `agent_ready_core_audit.md` |
| Frozen Phase 1 API/CLI surface is documented with runnable examples | Documentation contract tests and examples | `api_cli_examples.md` |
| Every relevant TODO/FIXME has an explicit disposition | Repository marker audit and final gate test | `todo_fixme_disposition.md` |
| PR-18 evidence is reproducible and fail-closed | Evidence contract tests, exact command/fingerprint checks, clean reproduction | `implementation_verification.json` and `commands_and_results.md` |

## Migration rule

No migration is planned. A migration or index change may be introduced only if
the live catalog audit, a frozen invariant, and a focused failing verification
jointly demonstrate that a required index is absent or incorrect. In that case
the smallest linear migration must include upgrade/downgrade, catalog, rollback,
and compatibility coverage.

## Evidence and chronology

The implementation subject contains only PR-18 tests, documentation, audits,
and any narrowly justified hardening implementation. Evidence is generated in a
separate PR-18 namespace and committed afterward as an evidence-only commit.
Evidence records the implementation subject, exact command tokens, fingerprints,
counts, environment, stale-result status, path and credential audits, and clean
reproduction instructions. No PR-17DR artifact is overwritten.

## Gate

PR-18 may be reported ready for independent review only when focused checks,
full regression, PostgreSQL integration, static checks, evidence reproduction,
and worktree/history checks pass. The implementation report must keep
`PR18_FINAL_GATE` pending independent review and must keep
`PHASE_2_AUTHORIZED: NO`.
