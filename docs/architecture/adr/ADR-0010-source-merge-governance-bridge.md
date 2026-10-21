# ADR-0010: Typed governance bridge for global source merges

- Status: Accepted for design under the explicit human architecture decision in Luna Sleep Mode V5; implementation is gated by independent review of execution/phase2/PR2-02-GOV_Source_Merge_Governance_Execution_Pack_v1.0.md.
- Context: LiteratureSource is globally shared and access is project-scoped. Existing ApprovalRequest and ApprovalDecision targets are limited to ManuscriptVersion and ScientificConclusionVersion. ArtifactVersion is scientific content and cannot own merge proposal identity.
- Decision: Admit a narrow typed SourceMergeProposal and per-project SourceMergeApproval path. Freeze ordered source pair, survivor, effective project set, identifier/version basis, rationale/evidence and basis hash. Every affected project requires approval by its effective HUMAN OWNER with live verified credential. This bridge stores governance; PR2-02 performs merge effects.
- Scope: No generic target extension, workflow engine, identifier resolver, SourceVersion creation, or manuscript/conclusion approval change. No polymorphic target_type + target_id or opaque JSON semantic core.
- Temporal/concurrency: Check authority at fresh PostgreSQL clock_timestamp() after required locks/rereads. The later merge locks sources/links, recomputes the project set and rejects stale basis before mutation.
- Schema admission: Typed proposal, affected-project snapshot, identifier/version basis, per-project decisions and append-only lifecycle/revocation events are the minimum bridge admitted by the human decision. Migration 0021 follows 0020.
- Consequence: Missing, rejected, revoked, stale or no-longer-authorized approvals cannot authorize merge. Bridge-time empty SourceVersion basis becomes stale when later versions change it; PR2-02 adds concrete same-parent refs before enabling new proposals.
- Rejected alternatives: ArtifactVersion as proposal, generic approval metadata, unilateral project approval, automatic identifier rebinding, mutation of PR2-01 identity rows.
- Authority: frozen Phase 1, Addendum A18-A22, Phase 2 R2/R3/R4 contracts, accepted PR2-00/01 and explicit human V5 decision.
