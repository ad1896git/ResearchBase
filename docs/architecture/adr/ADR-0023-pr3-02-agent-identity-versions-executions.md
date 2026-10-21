# ADR-0023 — PR3-02 agent identity, versions, executions and promotion

Status: ACCEPTED — APPROVED by owner 2026-10-21 (all recommended decisions). PR3-02-S1 is
authorized for implementation after its execution pack passes two director reviews; PR3-02-S2
waits for accepted PR3-03 and PR3-04 and needs its own authorization.

Contract: [PR3-02 draft](../../proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md).

| Decision | Approved |
|---|---|
| D302-01 Agent identity | Additive project enrollment (`provision_project_agent`) with MTLS_URI proof through the existing identity boundary; independent verifier intake; AQ-S3-08 closes only with positive Application-only B02 G2 AGENT evidence. |
| D302-02 Version scope | Project-scoped immutable AgentVersion; separate availability (ACTIVE/DISABLED/RETIRED); pinned behaviour in artifacts/manifests; no separate fingerprint entity. |
| D302-03 Staged execution | CREATED intent only until PR3-04 policies and PR3-03 gateway land (S2). |
| D302-04 Atomic targets | First targets: the two B02 DRAFT families via in-UoW composition; producer identity kept separate from the promoter (S2). |
| D302-05 Schema/locking | The eight pattern-based tables split S1 (4) / S2 (4); S1 uses the reduced 8-table SHARE inventory, S2 the 23-table inventory. |
| Slices | S1: enrollment + versions/availability. S2: executions + promotion. |
