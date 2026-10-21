# ADR-0014 — Minimal internal scientific DecisionRecord contract

Status: ACCEPTED; owner-approved A–E; independent compatibility review PASS; contract-only scope.

## Context and problem

The frozen Phase 2 PR2-15 roadmap specifies typed immutable decisions, but its first executable command lacked purpose/value, complete evidence-selection, Issue coordination, non-replacement and replay rules. Accepted PR2-14 evidence proves later Issue INSERT locks only its ReviewRecord, so a Decision-only conclusion lock does not serialize the gate. The previous caller-selected review-set proposal also cannot satisfy the owner's final complete-review-set decision.

## Owner decision and provenance

The project owner's instruction **“ResearchBase — PR2-15 V2 FINAL CONTRACT FREEZE / Owner-Approved A–E”** explicitly approves A exact blockers/common row coordination, B authorized historical UUID replay, C limited PROCEED semantics, D service-selected complete evidence/non-replacement, and E deferred no-change DISMISSED. This conversation instruction is the approval provenance; no invented signature, participant identity or timestamp is attached. It authorizes contract freeze after independent consistency review only, not engineering implementation or database migration.

## Options and decision

Decision-only locking leaves concurrent inserts unprotected; caller-selected favorable reviews lose evidence; permitting new UUID replacement loses history. Retain the existing concrete conclusion target as the shared row coordination point, select the complete eligible review set, seal it in existing typed basis/hash material, permit at most one initial decision per exact project/target/purpose, and use the canonical decision ID as request UUID. No new canonical entity, receipt table, field or digest is admitted.

The exact normative companion is [Minimal Decision Command v1.0](../20_PR2_15_Minimal_Decision_Command_Contract_v1.0.md), incorporated by Addendum A23. Existing R2 creator authority, hash payloads and temporal authorization remain in force. Only this command is closed; RevisionAction and other Decision purposes remain separately gated.

## Scientific integrity, security and API compatibility

PROCEED is immutable evidence, not Approval or scientific release. All eligible reviews, including unfavorable recommendations, must be represented. Exact-version Issue and review writes share coordination; later concerns do not rewrite a prior decision and later approval gates recheck. Current disclosure authorization controls stale-history replay; expired authoring authority gives no permanent access. PR2-14 creation and historical replay are unchanged except for future separately authorized coordination obligations.

## Data migration and rollback

This ADR changes no database. A future separately authorized forward migration must use approved DecisionRecord/basis tables, enforce exact scope uniqueness and immutable history, and extend review/Issue guards for coordinated snapshots, including normal-role direct SQL. Existing migrations stay unchanged. No destructive rollback of scientific history is authorized; populated-history downgrade must fail closed. Withdrawal/revision of this contract requires a new governed amendment, not silent alteration of the frozen reference.

## Tests and affected phases

Companion §8 defines planned PostgreSQL races, complete-set selection, non-replacement, replay/disclosure, authorization, atomicity and catalog tests. They are NOT RUN in this documentation task. Phase 2 PR2-14 coordination/PR2-15-S1 only; Phase 1 scientific semantics, retained M2/M3 state and formal admission gates are unaffected.

## Change-control procedure

Cross-Phase Contract §38–39 requires ADR/compatibility review for frozen semantics or Application-contract changes; §49 requires documentation synchronization. Addendum A18 defines the authoritative hierarchy. Repository ADR-0012/0013 demonstrate explicit architecture-owner approval in the ADR and linked physical/command contract. This change follows that mechanism: explicit owner A–E → ADR and authoritative companion/addendum/Phase-spec synchronization → fresh independent read-only compatibility review → separate scoped freeze declaration binding file hashes and Git history. No separate required signing service, signature or additional approver was identified in the applicable repository change-control clauses. Implementation-start/formal-acceptance gates remain separate.
