# ADR-0027 — PR3-16 D1 node-budget amendment

Status: PROPOSED

Date: 2026-10-27. Companion:
[D1 contract draft](../../phase3/design/PR3-16-d1-amendment-contract.md).
Disposition counts: **RESOLVED 3; OWNER 3; MISSING 1** (A01–A07).
These count this ADR's dispositions, including its summaries of contract items;
they are not additional owner decisions or implementation evidence.

## A01 — RESOLVED — context and problem

The owner requests a separate contract and PROPOSED ADR now; no implementation is
scheduled and production node admission stays denied until the contract is
approved. The atomic amendment is unconditional before activation. The current
storage contract requires a previously committed reservation, while PR3-04 records
budget stop when a reservation takes the last additive unit. A subsequent append
then denies, leaving a charged gap. Existing accounting derives depth from task
steps and requires a comparable evaluator for positive node charges. No production
producer or approved node evaluator/vector is supplied. Sources:
`docs/phase3/PR3-16-owner-decisions-2026-10-27.md:14`,
`docs/phase3/PR3-16-execution-pack-r2.md:499`,
`docs/phase3/PR3-16-execution-pack-r2.md:502`,
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:184`,
`docs/phase3/PR3-16-freeze-inventory.md:294`.

## A02 — RESOLVED — invariants, scientific integrity and security

Retain existing PR3-04 accounting, admitted counters, charged gaps/UNKNOWN outcomes
and trusted settlement ownership. No search ledger, implicit refund, nested public
reservation command or fake production capability is admitted. Human and Agent
share the Application boundary; actor-only planning does not establish resource
trust or execution authority. Current entitlement, committed replay and fresh
admission retain their order and post-wait validation. Concrete provenance,
immutable failed/pruned history, Run seals and scientific hashes remain intact.
Operational progress scores do not become Measurements or scientific validity.
Sources: `docs/architecture/adr/ADR-0026-pr3-16-experiment-search-core.md:34`,
`docs/architecture/adr/ADR-0026-pr3-16-experiment-search-core.md:39`,
`docs/architecture/adr/ADR-0026-pr3-16-experiment-search-core.md:43`,
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:54`,
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:64`,
`docs/phase3/PR3-04-contract-freeze.md:574`,
`docs/phase3/PR3-16-execution-pack-r2.md:502`.

## A03 — OWNER — proposed decision and alternatives

**Question:** what complete node-aware admission composition, registered producer,
evaluator, full resource vector, depth/occupancy mapping, stop effects and settlement
owner will the owner and architecture review approve? These are the contract's
O01–O08 decisions; their detailed questions/options/recommendations remain open.

**Options:** approve a complete atomic composition through existing accounting in
one owning Application transaction, preserving prior command semantics; or retain
production denial while the required design is incomplete. Continuing conservative
storage does not remove the unconditional amendment prerequisite. Nesting a public
safety command, minting a new ledger or substituting the gateway fake vector is
incompatible with the established constraints.

**Recommendation / proposed decision:** develop the reviewed composition within
existing accounting and receipt families, with reservation and node admission
committing together or neither committing. Preserve denial on prior stop and
review the last-unit case explicitly. Resolve evaluator success/observation and
settlement lifetime before treating node creation as an admitted iteration.
The candidate composition is not a frozen effect manifest, command name, producer
registration, evaluator implementation or authorization. Pending those decisions,
this ADR remains PROPOSED and production admission stays denied.

**Consequences if later approved and verified:** the combined operation could
avoid a new reservation-without-node gap caused by splitting those effects across
commands. It cannot refund existing gaps, remove UNKNOWN charges, clear sticky
stops or authorize scientific execution. Sources:
`docs/phase3/PR3-16-execution-pack-r2.md:52`,
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:189`,
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:321`,
`docs/phase3/PR3-03-contract-freeze.md:1778`,
`docs/phase3/PR3-16-owner-decisions-2026-10-27.md:14`.

## A04 — OWNER — data migration and rollback

**Question:** what exact forward guard/receipt/catalog delta, preservation evidence
and rollback or forward-repair procedure will implement the approved effects?
**Options:** review that inventory and recovery procedure after the effect contract
is complete; or leave the amendment unavailable. **Recommendation:** preserve all
historical reservations, usage, receipts and scientific records, and require the
explicit changed/unchanged-object manifest before any migration authorization.
Do not reinterpret old reservations as atomic node admission or repair charged
gaps by deletion/refund. No migration identifier, SQL body, backfill or executable
rollback is assigned by this ADR. Contract O09 remains unanswered. Sources:
`docs/phase3/PR3-16-execution-pack-r2.md:50`,
`docs/phase3/PR3-16-owner-decisions-2026-10-27.md:8`,
`docs/architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md:373`,
`docs/architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md:428`.

## A05 — OWNER — API compatibility and exact composition

**Question:** does a separately defined atomic command or an explicitly versioned
extension own the new material/results, and what per-caller locks and guards
preserve replay and existing safety/gateway behavior? **Options:** specify a
separate command contract; or review a compatible versioned extension.
**Recommendation:** settle the exact envelope/effect inventory and independent
vectors before choosing names or altering guards. Preserve old safety commands and
hash vectors, same Application boundary, no serializable trust flag, no extra
transaction/receipt and no copied gateway lock helper. Contract O06/O09 detail
the unresolved mapping. This ADR adds no HTTP/CLI route or production capability.
Sources: `docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:321`,
`docs/phase3/PR3-03-contract-freeze.md:1778`,
`docs/phase3/PR3-03-contract-freeze.md:1789`,
`docs/phase3/PR3-16-owner-decisions-2026-10-27.md:10`,
`docs/phase3/PR3-16-owner-decisions-2026-10-27.md:13`,
`docs/architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md:326`.

## A06 — MISSING — amendment acceptance checks

No executable D1 atomic check exists. Contract M01–M10 enumerate the absent storage,
atomicity/recovery, trust/evaluator, vector, mapping, stop-race, settlement,
ordinary-role guard, compatibility and literal/replay checks. Existing PR3-04
tests and the absent proposed search budget test do not establish atomic node
admission. Exact assertions await the owner decisions; no missing row counts as
coverage. Focused documentation-change verification is recorded in the companion
contract, separately from unrun D1 acceptance. Sources:
`docs/phase3/PR3-16-freeze-inventory.md:294`,
`docs/phase3/PR3-16-design-closeout.md:274`,
`docs/phase3/PR3-16-owner-decisions-2026-10-27.md:18`.

## A07 — RESOLVED — affected phases and authorization limit

This proposal concerns Phase 3 search lineage and its existing task-safety
accounting dependency. Phase 1/2 scientific ownership and immutable provenance
remain unchanged. PR3-17 decisions/scoring, Run creation/execution, workers,
providers, promotion and Phase 4 remain outside this design task. Owner approval
of this design is still pending; implementation requires separate authorization.
No implementation is scheduled, ADR acceptance asserted, or other closeout decision
changed. Sources: `docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:78`,
`docs/architecture/06_Phase3_Development_Specification_v1.1_Harness_Integrated.md:2568`,
`docs/architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md:1188`,
`docs/phase3/PR3-16-owner-decisions-2026-10-27.md:3`,
`docs/phase3/PR3-16-owner-decisions-2026-10-27.md:14`,
`docs/phase3/PR3-16-execution-pack-r2.md:533`.
