# ADR-0011: Bounded search-execution attempt accounting

- **Status:** PROPOSED FOR INDEPENDENT DESIGN REVIEW. Not accepted, not implementation permission.
- **Date / baseline:** 2026-10-05 / `cdc50eb8b4c35602501741e9205b7e0f3a43509f`.
- **Affected phase:** PR2-04 only; no Phase 1 or accepted PR2-00–03 changes.
- **Companions:** [execution pack](../../../execution/phase2/PR2-04_Literature_Search_Execution_Execution_Pack_v1.0.md), [acceptance matrix](../../../execution/phase2/PR2-04_Acceptance_Matrix_v1.0.md).

## Context and problem

TDG2-06/07 and accepted ADR-0008 require bounded external calls, TX A/external/TX B/TX C, observable retry, idempotency, cancellation and UNKNOWN. Schema Field Contract 13 fixes execution/query/result semantic columns and terminal immutability. Hash Contract 15 fixes the query hash. None specifies a durable pre-call reservation or a place to distinguish a provider attempt from a database retry and an idempotent command replay.

Only keeping final results cannot distinguish a crash before dispatch from a crash after remote processing. Reusing a RESERVED invocation after restart risks unobservable duplicate calls. Encoding mutable attempt histories in execution_context would violate the typed provenance boundary. Adding unregistered semantic columns silently would violate Contract 13's exhaustive-field rule.

An explicit admission is therefore needed before implementation, not a convenient restatement of existing retry policy. This ADR proposes subordinate supporting Entity/Relation/Event patterns under the already registered LiteratureSearchExecution; it does not admit another top-level canonical scientific concept.

## Options considered

1. **Only existing execution/query/result columns.** Fewest tables, but no durable pre-dispatch ownership, unsuccessful attempt history or reliable uncertainty recovery. Reject: insufficient for TDG2-06/07 crash/retry evidence.
2. **Generic event JSON, queue/workflow engine or lease-based dispatcher.** Can encode everything, but adds polymorphic semantic storage, hidden scheduling and takeover hazards outside the PR. Reject: architectural complexity and ownership expansion.
3. **Typed dependent attempt, event and receipt records.** A fixed reservation plus one sealed outcome; append-only lifecycle/cancel events; dedicated scoped admission receipts. Select: minimum bounded support for this execution's uncertainty, state changes and accepted idempotency pattern.

## Proposed decision and exact admission

Subject to independent approval, admit only these supporting tables, fully specified in pack §13:

- `literature_search_provider_attempts`: typed execution FK, input-query index, per-query attempt number, immutable dispatch reservation/key/deadline, and a write-once outcome with optional concrete query FK. No provider JSON or source/evidence promotion.
- `literature_search_execution_events`: append-only typed execution/attempt FKs and lifecycle/row-version coordinates, including durable cancellation intent. Not a generic event bus.
- `literature_search_execution_command_receipts`: the established project/actor/command/request scoped receipt pattern with a concrete execution FK and immutable versioned admission DTO.

No change to Contract 13's execution/query/result semantic columns or statuses. Shared `row_version` applies to execution and unsealed attempt; shared own-hash columns apply to immutable results. QueryRecord's existing query_hash is its sole binding; no redundant query content_hash. Operational audit events and receipts are explicitly exempt from own scientific content_hash, matching prior accepted event/receipt patterns. Their row immutability and receipt request hash remain mandatory. Attempt warning_codes is a closed operational enum array, not arbitrary JSON metadata. These exceptions/columns apply only to the new supporting tables.

Contract 13 requires immutable-record own hashes, but Contract 15 supplies no SearchResultRecord template. Admit the exact **new** v1 payload in pack §13.4 (type/material_version/query_hash/rank/external_identifier/title/url/snippet/provider_score). Use existing sha256-cjson-v1, canonical decimal strings and NFC. This publishes new immutable material; hence ADR review is necessary. It changes no existing payload, serializer, Phase 1 hash or golden vector.

Result hashes bind provenance/integrity only: not result identity, deduplication identity, source identity or authority for destructive merge. Repeated provider observations remain distinct; the literal serialization and hash-input rules remain in pack §13.4.

No accepted document is edited to pretend this proposal already has higher precedence. Acceptance must explicitly record approval of this narrow supporting-schema/hash supplement alongside the pack. If reviewers conclude an incorporated contract requires a different admission mechanism, STOP for that approval; the Executor must not infer it from an ADR filename or authorship.

## Operational consequences

Only an acknowledged new reservation owner may issue its invocation, once. An unresolved reservation is never taken over or blindly replayed; after a bounded deadline, authorized recovery may seal UNKNOWN and fence late writes. This sacrifices automatic recovery of some never-sent work to preserve honest uncertainty. It does not guarantee remote exactly-once behavior.

The fence is transactional state/CAS protection, not a distributed token system: a worker/recovery path may persist an outcome only while locked execution/attempt state, attempt identity and expected row versions authorize that write. Concurrent recoveries serialize; each seal and terminal transition has one winner, and losers reread durable state through normal bounded retry. No duplicate provider invocation, query/result or FINISHED event is permitted. No leases, queue, scheduler, distributed workers or automatic reconciliation engine are admitted.

Durable cancellation intent belongs to the unique CANCEL_REQUESTED event, not a new schema concept. C1 admits intent/receipt and increments execution version; separate C2 finalizes and emits FINISHED only with the actual terminal transition. Interrupted PLANNED cancellation with committed intent and no attempts converges to CANCELLED through an explicit currently authorized recovery, without provider work. PLANNED without intent remains PLANNED. Exact admission replay is read-only; it never claims C2 completed. Pack §§10–11,18–19 specify coordinates and races.

Terminal immutability prohibits state/provenance/attempt/query/result/event mutation or late work. It does not prohibit the explicitly permitted independently keyed terminal RECOVER no-op admission receipt, which changes none of those facts and invokes no provider. Existing receipts are immutable; exact replay creates nothing. Receipt identity is the complete deployment/actor/project/command/request key, distinct from project-wide execution creation uniqueness; only changed payload under the same complete key is a receipt conflict (pack §11).

Known-safe provider retries create separate reservations. DB serialization retries rerun only their DB phase, with durable reads and fresh authorization, never external I/O. UNKNOWN is terminal and immutable. Reconciliation of terminal unknown facts remains a future separately governed appended record, not reopening execution state.

Baseline UoW already normalizes 40001, not 40P01. PR2-04 owns narrowly scoped 40P01 normalization at its persistence boundary and bounded DB retries, as specified in pack §9. This ADR does not authorize changing the global UoW policy or earlier services; any necessary expansion requires separate approval and historical non-drift evidence. DB retry, provider retry, caller replay and explicit recovery remain distinct.

Current authority is required for every database phase. Admission is not a durable authorization grant. A lost-authority caller may leave a pending reservation, later recoverable by a current authorized actor without accepting that caller's lost response as canonical. No privileged background writer is introduced.

## Scientific integrity and scope

Query/result records are retrieval provenance, not evidence. Results remain unresolved provider hits. Repeated identical queries/hits remain separately observable by ordinal/rank. No changes to LiteratureSource identity, SourceVersion, LiteratureEvidence, Phase 1 Run, frozen plans or reference closure. No PR2-05/06 implementation or real-provider activation.

## Data migration and rollback

Future additive `0024_literature_search_execution` has parent `0023a_search_plan_review_guards`, creates the six pack tables and guards, and becomes the unique head. No existing data rewrite. Fresh, 0018-origin and populated accepted-head upgrade paths must be tested. Downgrade refuses while any new table is populated; empty-only downgrade/reupgrade is required. Existing migration files stay untouched. No migration is created by this ADR.

## API compatibility

Existing commands/receipts/errors are unchanged. New execution commands return immutable admission DTOs and expose current state through authorized queries. New error additions are only the upstream-named SEARCH_PLAN_NOT_FROZEN, ADAPTER_UNAVAILABLE and ADAPTER_VERSION_MISMATCH; provider outcome reasons are a separate operational enum. The provider port keeps the established `SearchCapability.search` name. Minimal port/fake support does not activate the later adapter PR.

## Security

No credentials, raw provider responses, arbitrary error text or canonical reference lists in JSON. Configuration privately injects credentials into adapters. Typed rows store bounded provider-neutral metadata; live calls and caches are disabled in acceptance. Cancellation tokens and request IDs are not authorization. Provider data is never executable policy or scientific truth.

## Required tests and evidence

The matrix binds schema admission, exact hash payloads, all crash boundaries (including C1-committed/C2-interrupted cancellation), recovery-vs-recovery and duplicate dispatch races, sealed-outcome state/CAS fencing, current authority, complete-key receipt replay/conflict and terminal no-op receipt exception, safe/uncertain retry separation, scoped 40001/40P01 behavior, absence of DB transactions during I/O, and migration/non-drift proof. The final candidate's runtime trace must distinguish provider attempts, DB attempts and public command keys. These corrections expand existing coverage without new IDs: 65 requirements remain NOT_RUN. No tests have been run or implementation results claimed by this ADR.

## Review/STOP

Approval of ADR-0011 and the companion pack is a required design gate, not self-generated acceptance. No production/migration implementation may start merely because these documents exist. If the supporting schema is rejected or conflicts with an unamended higher contract, return to design review; do not hide attempt semantics in generic JSON.
