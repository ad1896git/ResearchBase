# M2 live literature implementation plan

Starting SHA: df603fe0fbb8c80758400e7b13cb831b7f730187. One primary executor, requested feature branch and persistent worktree. The user brief supplies the approved scope; no additional design gate.

Architecture: synchronous standard-library HTTP adapters implement the existing SearchCapability boundary. Existing execution service owns admission, retry, cancellation, authorization and durable observations. DOI-based Crossref comparison produces bibliographic observations, never scientific evidence. Source resolution uses project-scoped source identity/version services and an append-only concrete result linkage, preserving original results.

- [x] Add bounded OpenAlex adapter and offline response/error tests. Translate supported frozen time/language filters; fail closed on unsupported material. Cap a single page at the admitted 100-result bound. Preserve provider order and stable Works identity. Use provider correlation only when actually returned. Unknown network outcomes remain UNKNOWN; never fabricate cancellation confirmation.
- [x] Add DOI-normalized Crossref lookup and compatible/conflicting/ambiguous/unavailable comparison tests. Retain exact observations through approved ArtifactVersion mechanisms; no inline vendor JSON core.
- [x] Implement minimum appended result resolution with project authorization, exact result/plan/execution provenance, source identity replay and frozen versions. Inspect existing M0 response reuse normalization and test any repaired path.
- [x] Compose live provider and trusted credential verifier into CLI. Exercise plan freeze, execution/results, resolution/source reads in separate processes.
- [x] Run focused offline and disposable PostgreSQL 18 tests, M0/M1 regressions, modified-file Ruff/format/Pyright. Execute real OS-user CLI/OpenAlex/Crossref/PostgreSQL restart demonstration, record exact IDs and request times without secrets.
- [x] Review diff against contracts, write M2_LIVE_LITERATURE_COMPLETION.md with actual outcomes and remaining findings, commit, verify clean worktree and one milestone bundle. No push/merge/M3.

M2-AQ-001 approved and implemented by ADR-0013 and migration 0029. M0 confirmed-C1 retry-after normalization inspected and explicitly deferred outside the live provider path. Final verification and historical diagnostic exclusions are recorded in M2_LIVE_LITERATURE_COMPLETION.md.
