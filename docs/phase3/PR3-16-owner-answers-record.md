# PR3-16 owner answers record (2026-10-26)

**Purpose.** This file makes the owner answers traceable. Each row quotes the draft line that was accepted, so reviewers can check that no answer was broadened or narrowed.

**Source.** The owner's instruction on 2026-10-26 was to accept the draft recommendations for every item ("全部按草稿推荐"). The draft is `PR3-16-G0-answers-draft.md` (planning draft, lane301). A copy is kept beside the review tasks in the runtime root. Each quote below is verbatim from that draft line.

**Scope.** This record accepts answers only. It does not freeze the pack, admit the schema, or authorize implementation.

**t322 source-verification limit.** Work is confined to this repository. The external answers draft has not been accessed in this correction, so original draft-to-record quotation fidelity is **UNVERIFIED** here. The accepted table and all thirteen recommendation paragraphs below are preserved from the task's Git baseline; no answer is reinterpreted. Historical t322 checks for this record and the pack are recorded in [execution pack §5.1](PR3-16-execution-pack-r2.md#51-r2-review-b-round-7-checks-t322-2026-10-26).

| Item | Draft location | Accepted in one line | Note |
| --- | --- | --- | --- |
| D1 | draft line 44 | Admit the four tables; conservative proof or deny; atomic amendment as a separately reviewed amendment before activation (draft line 44) | Draft line 44 (unconditional): make atomic admission a separately reviewed amendment before activation. Draft line 142 (Q3) adds: require it when no trusted producer can satisfy the proof. Whether the two combine into one rule is for owner confirmation at freeze. |
| D2 | draft line 58 | Limited append-only lifecycle |  |
| D3 | draft line 72 | Actor-attributed planning, execution disabled |  |
| D4 | draft line 86 | Multiple Runs per node; explicit reuse as lineage |  |
| D5 | draft line 100 | Typed optional exact references; scoring deferred |  |
| Q1 | draft line 114 | Reviewed complete inventory before DDL |  |
| Q2 | draft line 128 | Strategy material omitted for this slice | Source is the draft only; C does not state this choice. |
| Q3 | draft line 142 | Conservative proof; deny when no trusted producer is proven |  |
| Q4 | draft line 156 | Closure-time cutoff for post-close links | Source is the draft only; C does not state this choice. |
| Q5 | draft line 170 | Structural constraints now; semantic detection staged |  |
| Q6 | draft line 184 | Whole-tree bounded reads | Source is the draft only; C does not state this choice. |
| Q7 | draft line 198 | Actor-only identity proof |  |
| Q8 | draft line 212 | Application-only scope; conditional 0081 |  |

## Verbatim accepted recommendations

### D1

**Proposed answer — INFERRED:** Recommend the four-table scope for later admission, with conservative proof-or-deny for this storage slice. Make atomic admission a separately reviewed amendment before activation; do not treat gateway fake accounting as node spend. Q1 must supply the full inventory and Q3 a valid trusted producer before this can be frozen.

### D2

**Proposed answer — INFERRED:** Recommend the limited lifecycle. Terminal ancestors block new descendants; existing children remain distinct. Closure blocks new nodes/failure/pruning but permits only Q4-approved historical Run reconciliation, without spend, reopening or implicit cancellation. Defer bulk subtree operations and PR3-17 scoring/selection/success.

### D3

**Proposed answer — INFERRED:** Recommend actor-attributed planning with current verified Human/Agent identity and existing write/read entitlements. For this planning-only slice, propose no AgentVersion/availability prerequisite; require Q7 to freeze the identity checks and coordination. Keep all execution disabled until separately delivered provenance and admission are approved; no dummy execution UUID.

### D4

**Proposed answer — INFERRED:** Recommend both permissions, with concrete same-project links and node/Run ExperimentSpec equality when the node names a version. A fresh command repeating an existing link fails; only the original receipt replays successfully (`C:99`, `C:137–143`).

### D5

**Proposed answer — INFERRED:** Recommend the bounded typed material, with saved hash present iff its reference is present and reverified on admission/read. Preserve existing error codes, serial migrations and no-provider scope. Leave strategy pinning to Q2; require reviewed freeze and separate implementation authorization after decisions close.

### Q1

**Proposed answer — INFERRED:** Recommend that four-table inventory with event-derived status, RESTRICT FKs, no-op UPDATE/DELETE rejection, one root, unique event sequence/reservation use and at most one terminal event per node and per session. Reuse receipts: each command has one revision, receipt and task event plus its declared lineage effects. Require a named old-guard preservation map and full SQL/result inventory before admission; this draft does not invent the missing definitions.

### Q2

**Proposed answer — INFERRED:** Recommend omitting strategy material only through explicit owner-approved staging, not through a test name. Use material version 1, NFC text/lowercase UUIDs, all defaults/NULLs and authenticated actor; exclude generated values/current projections. Freeze every UUID rule, result order and literal vector independently before implementation; keep entitlement → committed replay → fresh-write checks.

### Q3

**Proposed answer — INFERRED:** Follow D1's conservative path: accept only a reservation made by a proven existing trusted producer/evaluator, otherwise deny. Retain charged gaps/UNKNOWN outcomes and existing trusted settlement ownership; PR3-16 neither nests a public reservation command nor settles/refunds. If no producer can satisfy the proof, require the separately reviewed atomic amendment instead of making up trust or a resource vector.

### Q4

**Proposed answer — INFERRED:** Recommend closure-time cutoff for post-close links, with exact Run identity and durable already-existing-work proof defined and reviewed before freeze; deny ambiguous cases. Recommend rejecting fresh repeated/conflicting terminal commands without effects, while preserving entitled original-receipt replay. Keep current write authority on new reconciliation and freeze the complete terminal-node/ancestor/task/session matrix.

### Q5

**Proposed answer — INFERRED:** Recommend the known structural constraints now and an explicit reviewed staging disposition for semantic duplicate detection in the later strategy work. Do not infer root/node equality, inheritance or a Hypothesis/ExperimentSpec relationship beyond owning-domain rules and stated scope/frozen-reference checks. Keep the Phase 3 duplicate-branch obligation open until its semantic contract/test is defined.

### Q6

**Proposed answer — INFERRED:** Recommend bounded whole-tree reads in one snapshot, event-sequence order and deterministic Run-link ID order. Freeze separate node/depth/event/link bounds before implementation; do not import 256 or silently truncate history. Propose NOT_FOUND for entitled absent targets, referential-integrity failure for corrupt ancestry and provenance-closure failure for saved-hash contradictions, with sanitized envelopes.

### Q7

**Proposed answer — INFERRED:** Recommend D3's actor-only planning proof, retaining whatever existing identity coordination that verification requires. Freeze the exact per-caller sequence before code: no additional AgentVersion validation by implication; any required identity keys precede row locks. Preserve current entitlement → committed receipt replay → fresh admission after each wait/write/constraint check, excluding own uncommitted effects.

### Q8

**Proposed answer — INFERRED:** Recommend Application-only scope and the conditional revision, never reservation of 0081. Recheck integration head/ref and freeze exact paths/tests/catalog deltas after all answers. Preserve historical fixture pins, including review B's omitted locations; disposition both reviews and rewrite answer-dependent tests/authorization wording before pack freeze (`RB:50–57`; `RA:21–46`).

## r2 review B round 7 coverage status (t322)

The accepted answers above are unchanged. [Execution pack §1.4](PR3-16-execution-pack-r2.md#14-owner-answers-mapped-to-observable-checks) now separates proposed assertions from **MISSING / NOT RUN** coverage. In particular, verified identity and actor-only planning need behavioral checks; an architecture scan or expiry refresh does not prove either. Same-project/ExperimentSpec Run links, saved-hash presence and admission/read validation, fresh repeated/conflicting terminal-command denial, and the three Q6 read-error classes are explicitly MISSING. Q6 event-sequence/Run-link ordering is mapped to the proposed S6 read-contract node.

The five previously named missing nodes now have owners and explicit future command selections: no strategy column (S1), duplicate IDs/links (S5), no API/CLI routes (S7), terminal-ancestor denial and unfrozen/wrong-version rejection (S8). Their assertion definitions remain MISSING and their execution is NOT RUN. Future freeze preparation must name and schedule every other missing check before freeze review; no freeze or implementation is authorized by this record.

## t324 review B round 8 and ADR review A corrections

The 13 answer rows and 13 recommendation paragraphs above retain their baseline wording. [Execution pack §5.2](PR3-16-execution-pack-r2.md#52-t324-document-corrections-and-focused-verification-2026-10-26) records the exact comparison against `cde62c66bdf00a9f64aa47e0579e1f3c152576f0`, focused checks and their evidence limits. The external answers draft remains unaccessed; original quotation fidelity is UNVERIFIED.

Pack §1.4 now maps the Q1 RESTRICT FKs, no-op mutation rejection, single root, reservation uniqueness and exact command effects. Database checks for unique event sequence and one terminal event per node and per session are explicitly **MISSING / NOT RUN**. Q8 also maps to S1's proposed forward-only migration/single-head check; competing revision reconciliation stays OPEN.

[ADR-0026](../architecture/adr/ADR-0026-pr3-16-experiment-search-core.md) restores the D2/D3/Q3 qualifiers and D4's distinction between reuse and proof of task-budget attribution. Its undecided list now includes Q5 fingerprint/pair consistency and Q8 reconciliation with PR3-02-S2. The ADR remains PROPOSED; no owner answer, freeze, schema admission or implementation authorization changes.
