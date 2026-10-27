# ADR-0026 — PR3-16 Experiment Search Core

Status: ACCEPTED — owner approved 2026-10-26 (decision recorded in the owner answers record).

## Context

PR3-16 proposes session/node/lineage storage with six commands:
`create_search_session`, `append_search_node`, `link_search_node_run`,
`record_search_node_failure`, `prune_search_node`, `close_search_session`; and three
queries: `get_experiment_search_tree`, `get_branch_lineage`, `get_search_budget`.
The four proposed tables are `experiment_search_sessions`, `experiment_search_nodes`,
`experiment_search_node_runs` and `experiment_search_events`. They instantiate
Entity/Relation/Event patterns; immutable events derive session/node status and
concrete links reference ordinary Runs without copying scientific truth.

[AGENTS.md §4](../../../AGENTS.md#4-architecture-complexity-budget) defaults to
“DO NOT ADD SCHEMA” for new top-level canonical schema unless existing patterns
cannot clearly express the concept and ADR/architecture review approves it.
These four tables therefore require explicit admission; this draft supplies none.
Sources: [execution pack §§1.2, 1.4, 4.1, 6](../../phase3/PR3-16-execution-pack-r2.md)
and [owner answers record](../../phase3/PR3-16-owner-answers-record.md).
The record reports owner acceptance of answers on 2026-10-26, not freeze or
implementation approval. External draft-to-record quotation fidelity is UNVERIFIED;
quotations below are from the repository record.

## Decision

Propose admitting only these four tables after the complete reviewed freeze
inventory (Q1) exists and explicit schema admission (G0-A) is granted. Preserve
the recorded D1–D5 and Q1–Q8 answers below; none resolves their remaining details.

- **D1:** “Recommend the four-table scope for later admission, with conservative proof-or-deny for this storage slice.” “Make atomic admission a separately reviewed amendment before activation”; gateway fake accounting is not node spend. Q1 inventory and Q3 trusted producer are prerequisites to freeze.
- **D2:** “Limited append-only lifecycle”: ACTIVE → CANCELLED/EXHAUSTED/TERMINATED_BUDGET sessions; PROPOSED → FAILED/PRUNED nodes. Terminal ancestors block new descendants; existing children remain distinct. Closure blocks new nodes/failure/pruning, permitting only Q4-approved historical Run reconciliation without spend, reopening or implicit cancellation. Bulk subtree operations and PR3-17 scoring/selection/success remain deferred.
- **D3:** “Actor-attributed planning, execution disabled”: current verified Human/Agent identity and existing write/read entitlements; no AgentVersion/availability prerequisite for this planning-only slice. Q7 must freeze the identity checks and coordination. Execution requires separately delivered provenance and admission; no dummy execution UUID.
- **D4:** “Multiple Runs per node; explicit reuse as lineage”: concrete same-project links and node/Run ExperimentSpec equality when the node names a version. “A fresh command repeating an existing link fails; only the original receipt replays successfully”. Reuse records lineage, neither a fresh experiment/evidence item nor proof of task-budget attribution.
- **D5:** “Typed optional exact references; scoring deferred”: optional exact frozen Hypothesis/ExperimentSpec references and bounded reasons, “saved hash present iff its reference is present and reverified on admission/read.” Preserve existing errors, serial migrations and no-provider scope; strategy pinning belongs to Q2.
- **Q1:** “Reviewed complete inventory before DDL”: event-derived status, RESTRICT FKs, no-op UPDATE/DELETE rejection, one root, unique event sequence/reservation use, at most one terminal event per node/session. Each command reuses one revision, receipt and task event plus declared lineage effects. Require the named old-guard preservation map and full field/SQL/result inventory before admission.
- **Q2:** “Recommend omitting strategy material only through explicit owner-approved staging, not through a test name.” Material version 1; NFC text/lowercase UUIDs; all defaults/NULLs and authenticated actor; exclude generated values/current projections. Independently freeze UUID rules, result order and literal vectors; preserve entitlement → committed replay → fresh-write checks.
- **Q3:** Accept only a committed reservation from a proven existing trusted producer/evaluator; otherwise deny. Retain charged gaps/UNKNOWN outcomes and existing trusted settlement ownership; no nested public reservation command or PR3-16 settlement/refund. “If no producer can satisfy the proof, require the separately reviewed atomic amendment instead of making up trust or a resource vector.”
- **Q4:** “Closure-time cutoff for post-close links”: exact Run identity and reviewed durable already-existing-work proof; deny ambiguity. Reject fresh repeated/conflicting terminal commands without effects; preserve entitled original-receipt replay and current write authority for new reconciliation. Freeze the full terminal-node/ancestor/task/session matrix.
- **Q5:** “Structural constraints now; semantic detection staged”: require reviewed staging for later semantic detection. No inferred root/node equality, inheritance or Hypothesis/ExperimentSpec relationship beyond owning-domain rules and stated scope/frozen-reference checks. The Phase 3 duplicate-branch obligation remains open.
- **Q6:** “Whole-tree bounded reads” in one snapshot, event-sequence and Run-link ID order; separate node/depth/event/link bounds, no imported 256 or silent history truncation. NOT_FOUND for entitled absent targets; referential-integrity failure for corrupt ancestry; provenance-closure failure for saved-hash contradictions, with sanitized envelopes. Pagination is not chosen.
- **Q7:** “Actor-only identity proof”: retain required existing coordination; freeze exact per-caller sequence before code. No additional AgentVersion validation by implication; identity keys precede row locks. Preserve entitlement → committed receipt replay → fresh admission after every wait/write/constraint check, excluding own uncommitted effects.
- **Q8:** “Application-only scope; conditional 0081”: no API/CLI routes. `0081_experiment_search_core` is conditional on verified integration head `0080_capability_gateway`, never reserved. Recheck head/ref; freeze paths/tests/catalog deltas; preserve historical fixture pins. Disposition both earlier reviews and rewrite answer-dependent tests/authorization wording before freeze.

**Explicitly not decided:** trusted producer/evaluator identity (Q3); durable
already-existing-work proof (Q4); whether the atomic amendment is unconditional
(D1, draft line 44) or conditional (Q3, draft line 142); numeric bounds (Q6);
strategy-material staging approval (Q2); duplicate fingerprint / optional-reference
pair-consistency algorithm (Q5); reconciliation with the competing PR3-02-S2
next-migration proposal (Q8); and the exact freeze inventory, including
names, types, SQL bodies, vectors, lock sequence, live head and release paths/tests.
Wider specification-material staging also remains open. These are unresolved,
UNVERIFIED prerequisites, not choices delegated to implementation.

## Consequences

After admission and authorization, this enables bounded, attributable search
lineage retaining failed/pruned/negative/unexecuted branches and ordinary Run
references. Search state cannot confer scientific validity or mutate scientific
hashes, sealed inputs or outcomes. PR3-17 decisions/scoring, execution/promotion,
Run creation, workers, providers and Phase 4 remain outside this slice.

No implementation before admission, reviewed inventory/pack, owner freeze approval
and separate G0-X authorization. Pack §1.4 assertions marked MISSING must be
defined and scheduled before freeze; named future tests are NOT RUN, and proposed
behavior is UNVERIFIED. This ADR adds no migration, API or rollback operation.

Pack §4.1 risks remain: rewritten history/hidden losers (immutable rows and retained
branches); lock inversion/stale entitlement/false replay (frozen lock order and
fresh checks); reconciliation becoming execution/budget bypass (Q4 proof, no new
spend); repeated validation cost and the gateway's 60-second admission-deadline
lesson (measure at Q6 bounds, without inventing a search deadline); CI/local timing
differences (capture runner/PG timings; deadline margin and JIT attribution remain
UNVERIFIED); head/catalog drift (exact reviewed deltas, preserved historical pins
and old guards). These require future evidence, not inferred mitigation success.
