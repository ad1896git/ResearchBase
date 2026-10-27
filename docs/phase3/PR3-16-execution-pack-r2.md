# PR3-16 Experiment Search Core execution pack

Planning only, 2026-10-25; revision r2 2026-10-26, review B round 8 and ADR review A correction (t324). The initial r2 record names `origin/main` at `585e071` (PR #14 merged) and branch `pr316-pack-r2`; these are historical context, not this revision's checkout. The t322 correction started at `ba03f96cce6129932a184566acf170147b3cea3d` on `fix-pr316-r2`. This t324 correction starts at `cde62c66bdf00a9f64aa47e0579e1f3c152576f0` (the local `pr316-pack-r2` ref) on the existing branch `fix/p2-pr316`. The owner accepted the draft recommendation for D1–D5 and Q1–Q8 (§1.2, §6). That acceptance records answers only: it does not freeze the pack, admit the schema, or authorize implementation.

**r1 history:** queue base `dc67a9886eb4da1f322be697a67abac1c33a8115` was already checked out on `pr316-pack`; local `origin/main` then resolved to the older Phase 1 commit `919c220f184242198d2cf4edb46ab9c163744a39`. r1 reported no checkout, branch creation, staging, commit or push. The same no-checkout/no-branch/no-staging/no-commit/no-push restriction applies to this correction. Reconcile the live integration ref before a future freeze; neither historical ref is asserted as current.

Authority: `AGENTS.md`; architecture 01 → 02 → 03 → 08 → Phase 3 specification → Harness 09; then the repository draft, local historical review, preserved owner answers and accepted seam records. The unavailable original plan is historical context only. The section structure follows `docs/phase3/PR3-03-implementation-plan.md:15`, `:46`, `:117`, `:655`, `:675`, `:741`.

Citation aliases below refer to repository files. Appendix S quotes the local review passages used for G0 and source provenance. The former external plan alias P is retired: its original text is absent from this checkout and local Git history, so original P line contents and completeness against its G0 are **UNVERIFIED**. No current requirement or owner answer relies on an inaccessible P citation.

- **R** = `docs/phase3/PR3-16-plan-review.md` (in-repository historical review, baseline `d744074`; its statements about the unavailable plan are secondary evidence, not verification of the plan itself).
- **C** = `docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md`.
- **A3** = `docs/architecture/06_Phase3_Development_Specification_v1.1_Harness_Integrated.md`.

Only `docs/phase3/PR3-16-execution-pack-r2.md`, `docs/phase3/PR3-16-owner-answers-record.md` and `docs/architecture/adr/ADR-0026-pr3-16-experiment-search-core.md` are revised in this t324 correction. Proposed files, identifiers, test nodes and future commands below are **PROPOSED / NOT RUN**, unless explicitly identified as existing or measured in §5.1 (t322) or §5.2 (t324). This pack neither changes a contract nor supplies missing approval; accepted answer text is preserved.

## 1. Verdict and evidence

### 1.1 Scope, non-goals and G0

**G0 is not satisfied.** The proposed deliverable is session/node/lineage storage: six commands (`create_search_session`, `append_search_node`, `link_search_node_run`, `record_search_node_failure`, `prune_search_node`, `close_search_session`) and three queries (`get_experiment_search_tree`, `get_branch_lineage`, `get_search_budget`), with exact links to ordinary Runs and retained failed/pruned/unexecuted branches (`C:7`, `C:95`, `C:119`).

Proposed persistence is four Entity/Relation/Event pattern instances, subject to schema admission: `experiment_search_sessions`, `experiment_search_nodes`, `experiment_search_node_runs`, `experiment_search_events` (`C:147`). Session/node status derives from immutable events. Preserve scientific hashes, Run input seals and outcomes; search lineage grants no scientific validity (`C:64`, `C:157`; `A3:1296`).

Non-goals: PR3-17 Experiment Manager decisions, SearchDecisionRecord, selection/ranking/scoring, winner or scientific-success designation, execution/promotion, Run creation, workers, cancellation I/O, providers, new dependencies, PR3-05 saving and Phase 4. PR3-16 is “session/node/lineage”; PR3-17 owns decisions (`A3:2568`, `A3:2572`; `C:78`).

This pack's G0 checklist is assessed below using the local draft's prerequisite rule (`C:12`–`C:14`) and the local review's report (`R:93`–`R:104`, quoted in Appendix S). Exact inventory and head maintenance are explicit pack requirements. Exhaustiveness against the unavailable original plan is UNVERIFIED; G0 remains unsatisfied.

| G0 condition | Status | Evidence and remaining work |
| --- | --- | --- |
| D1–D5 resolved | OWNER ANSWERED (2026-10-26) | Answered 2026-10-26: draft recommendations accepted in §1.2. The D1 sub-question (unconditional or conditional atomic amendment) stays open for owner confirmation. Each answer still needs its exact freeze text (`C:317`; `R:93`). |
| Q1–Q8 resolved | OWNER ANSWERED (2026-10-26) | Answered 2026-10-26: draft recommendations accepted in §1.2. The D1 sub-question (unconditional or conditional atomic amendment) stays open for owner confirmation. Details the recommendations leave unspecified (exact names, bytes, bounds) stay OPEN until the freeze step (`R:63`, `R:95`). |
| ADR/schema admission | NOT MET | Four-table admission and an ADR are required. Owner answers do not admit the schema. `docs/architecture/adr/ADR-0026-pr3-16-experiment-search-core.md` is PROPOSED; it grants no admission, which still depends on the complete inventory (Q1) (`C:3`, `C:12`, `C:147`). |
| Reviewed execution pack | NOT MET | Revision r2 awaits independent review. The earlier plan review has no P0/P1 but explicitly grants no contract approval (`R:40`, `R:100`). |
| Exact path/test/head-maintenance inventory | NOT MET | §3 and Appendix H propose concrete paths/nodes. Q1/Q2/Q3/Q7 are accepted in principle, but exact names, bytes, counts and the live integration head are produced only in the freeze step (`C:16`, `C:169`; `R:66`–`R:73`). |
| PR3-03 acceptance evidence reconciled | MET | `docs/phase3/PR3-03-evidence.md:7333` records owner acceptance; `:7335` distinguishes merged `fb734e6` from code head `c5a91ba`; `:7336` records successful CI; `:7349` satisfies the planning prerequisite. This retires the historical discrepancy reported at `R:15` and addresses `R:13`'s P2. |
| Implementation separately authorized | NOT MET | This task authorizes only the three documentation files named above. Draft approval alone does not enable execution (`C:12`); the local review reports the separate authorization requirement (`R:95`, `R:100`). Owner freeze approval is necessary but does not itself grant implementation. |

### 1.2 Open decisions and proposed resolutions

The supplied sources do not delegate these contract decisions to Claude (`C:12`; `R:91`). On 2026-10-26 the owner accepted the draft recommendation for every row (**OWNER ANSWERED**; each accepted line is quoted verbatim in `docs/phase3/PR3-16-owner-answers-record.md`); no **CLAUDE DECISION** is asserted. Each recommendation is still a proposal until the freeze step writes its exact text. Any answer that narrows scope requires a revised pack before dependent work.

| ID / question | Proposed resolution, reason and sources | Label / disposition |
| --- | --- | --- |
| D1 — Admit the four tables; conservative or atomic node accounting? | Recommend the four bounded pattern instances only after full inventory/ADR admission. For this storage slice, retain conservative committed-reservation proof or deny; Accepted (draft line 44): conservative committed-reservation proof or deny for this storage slice. Draft line 44: "Make atomic admission a separately reviewed amendment before activation." C:200 and C:321 recommend the amendment. Existing accounting has no ready node-aware API; never reuse the gateway fake vector as node spend (`C:147`, `C:184`, `C:321`; `docs/phase3/PR3-03-contract-freeze.md:1802`). | OWNER ANSWERED — draft recommendation accepted 2026-10-26; freeze text pending |
| D2 — Approve limited lifecycle, terminal ancestors and reconciliation? | Recommend ACTIVE → CANCELLED/EXHAUSTED/TERMINATED_BUDGET sessions and PROPOSED → FAILED/PRUNED nodes via append-only events. Terminal ancestors block new descendants; existing children remain; closure permits only approved historical Run reconciliation. Defer bulk subtree operations, success and scoring to avoid silently importing the wider lifecycle (`C:99`, `C:104`, `C:322`; `A3:1173`). | OWNER ANSWERED — draft recommendation accepted 2026-10-26; freeze text pending |
| D3 — Allow Human/verified Agent planning; what identity proof applies? | Recommend existing actor-attributed planning through the shared Application boundary with execution disabled. Require current verified identity; answered as current verified identity (actor-only planning proof, Q7); no AgentVersion/availability prerequisite for this planning-only slice. Execution later requires separately delivered concrete PR3-02 execution FK and reviewed admission, never a dummy UUID (`C:113`, `C:207`, `C:323`). | OWNER ANSWERED — draft recommendation accepted 2026-10-26; freeze text pending |
| D4 — Multiple Runs per node and reuse across nodes? | Recommend multiple distinct Runs and explicit reuse, unique per node/Run. Reuse records lineage, neither a fresh experiment/evidence item nor proof of task-budget attribution; this preserves existing Run ownership Accepted details: same-project links; node/Run ExperimentSpec equality when the node names a version; a repeated fresh link fails and only the original receipt replays (`C:99`, `C:170`, `C:203`, `C:324`). | OWNER ANSWERED — draft recommendation accepted 2026-10-26; freeze text pending |
| D5 — Optional scientific references and release boundary? | Recommend typed optional exact frozen root/node Hypothesis/ExperimentSpec references, saved owning hashes and bounded reasons; defer objective/scoring structures to PR3-17. Preserve existing errors and no-provider scope. This avoids JSON becoming the semantic core; accepted details: saved owning hash present iff its reference is present, reverified on admission and read; wider spec material staging still needs approval (`C:93`, `C:160`, `C:267`, `C:325`; `A3:1181`). | OWNER ANSWERED — draft recommendation accepted 2026-10-26; freeze text pending |
| Q1 — Complete schema/guard inventory? | Require a reviewed field/type/nullability list, named CHECK/UNIQUE/FK/index inventory, sequence/event literals, receipt result pointers, complete immediate/deferred definitions and old-guard preservation map before admission. Enforce the draft's four immutable tables, same-task/session/project ties and exact effects. Unstated names, bodies and counts remain OPEN; do not copy PR3-03's counts (`C:16`, `C:150`, `C:167`, `C:174`). | OWNER ANSWERED — draft recommendation accepted 2026-10-26; freeze text pending |
| Q2 — DTOs, material, vectors, errors and strategy pinning? | Recommend closed envelopes covering all six commands, all defaults/NULLs and authenticated actor; normalize NFC/lowercase UUIDs before existing canonical hashing. Freeze literal bytes/digests, UUID rules, result cardinality/order and per-command error precedence independently of implementation. Answered: strategy material omitted for this slice, conditional on explicit owner-approved staging (draft line 128); material version 1 (accepted detail); no strategy column is specified; exact vector bytes are not specified by this pack (`R:68`; `C:87`, `C:130`, `C:267`; `A3:1170`). | OWNER ANSWERED — draft recommendation accepted 2026-10-26; freeze text pending |
| Q3 — Who admits/reserves node budget and owns settlement? | Conservative recommendation requires committed same-task/active-budget reservation, `tree_nodes=1`, operation ID = node ID, unused/nonfinal reservation, exact step/search depth and current gates. Deny after stop; retain last-unit gaps/UNKNOWN charges. Accepted (draft line 142): conservative proof only. If no trusted producer can satisfy the proof, require the separately reviewed atomic amendment (caller trust, full vector, depth mapping, stop semantics, receipt effects, settlement owner). Trusted producer/evaluator identity remains OPEN; no nested safety command or new ledger (`R:47`, `R:50`; `C:184`; `src/researchbase/agent_runtime/application/task_safety.py:122`, `:149`, `:160`, `:247`). | OWNER ANSWERED — draft recommendation accepted 2026-10-26; freeze text pending |
| Q4 — Full temporal/state matrix and proof of already-existing work? | Freeze every command/state/ancestor combination, fresh-command repeated terminal requests and post-close authority. Recommend reconciliation with no execution/spend/reopen, while retaining all earlier branches. Answered: closure-time cutoff for post-close links. Accepted details: deny ambiguous cases; the durable proof of already-existing work must be defined before freeze and remains OPEN; no timestamp predicate is invented here (`R:70`; `C:67`, `C:97`, `C:110`, `C:115`). | OWNER ANSWERED — draft recommendation accepted 2026-10-26; freeze text pending |
| Q5 — Duplicate branch meaning and scientific-reference consistency? | Preserve explicit duplicate-ID/link/root constraints and node/Run ExperimentSpec equality. Accepted restriction: do not infer root/node equality, inheritance or a Hypothesis/ExperimentSpec relationship beyond owning-domain rules and the stated frozen-reference checks. Structural constraints now; semantic duplicate detection is staged to a later reviewed contract, and the Phase 3 duplicate-branch obligation stays OPEN. No fingerprint or pair-consistency algorithm is specified; these remain OPEN rather than replacing the required duplicate-branch test with ID-only checks (`R:70`, `R:88`; `C:99`, `C:157`, `C:170`; `A3:2327`). | OWNER ANSWERED — draft recommendation accepted 2026-10-26; freeze text pending |
| Q6 — Read envelopes, ordering, size bounds and corrupt ancestry? | Recommend root-to-node paths, labeled current Run/seal projections and same-snapshot safety projection. Accepted: order by event sequence and Run-link ID; NOT_FOUND for entitled absent targets; referential-integrity failure for corrupt ancestry; provenance-closure failure for saved-hash contradictions, with sanitized envelopes; whole-tree bounds (pagination not chosen). Numeric depth/size limits remain OPEN. All unspecified details remain OPEN; do not import gateway or context limits (`R:72`; `C:119`, `C:162`, `C:261`). | OWNER ANSWERED — draft recommendation accepted 2026-10-26; freeze text pending |
| Q7 — Identity keys, exact lock composition and post-write validation? | Preserve exact 18-table first SHARE, project/command/task prefix, required identity keys before rows, and fresh entitlement/replay/admission after every wait, DML and constraint forcing. Answered: actor-only identity proof. The resulting lock sequence still needs its exact freeze text. Never append keys after row locks or call the broader checkpoint-locking helper implicitly (`R:48`, `R:51`; `C:215`; `docs/phase3/PR3-03-contract-freeze.md:1772`; `src/researchbase/persistence/task_safety_repository.py:86`). | OWNER ANSWERED — draft recommendation accepted 2026-10-26; freeze text pending |
| Q8 — Revision, parent, files/transports and acceptance inventory? | Recommend Application-only scope, no API/CLI routes, and conditional next revision `0081_experiment_search_core` after verified `0080_capability_gateway`; reassign if another approved migration lands first. Appendix H enumerates observed maintenance. PR3-03 evidence discrepancy is resolved, but integration ref, exact revision/file list and release inventory remain OPEN, and the PR3-02-S2 pack on main proposes a competing next migration that must be reconciled first; no revision reservation or new CI success is asserted (`R:73`; `C:34`; `migrations/versions/0080_capability_gateway.py:5`; `docs/phase3/PR3-03-evidence.md:7331`). | OWNER ANSWERED — draft recommendation accepted 2026-10-26; freeze text pending |

### 1.3 Dependencies on accepted seams

Acceptance below is read from records, not measured again or extended to PR3-16. The conditional PR3-04 record is preserved as written.

| Seam | Evidence (file:line) | Dependency / limit |
| --- | --- | --- |
| PR3-00 runtime boundary | `docs/phase3/PR3-00-evidence.md:8`; `tests/architecture/test_pr3_00_boundaries.py:129` | Runtime owns planning; adapters do not own scientific truth. |
| PR3-01 entitlement, CAS and replay | `src/researchbase/agent_runtime/application/research_task.py:73`, `:94`; `src/researchbase/persistence/research_task_repository.py:115`, `:122` | Reuse task revision, actor-scoped receipts and saved results; no independent session CAS. |
| PR3-02-S1 identity | `src/researchbase/persistence/agent_version_repository.py:54`, `:78`; `docs/phase3/PR3-02-S1-contract-freeze.md:36` | Enrollment/version coordination does not prove execution provenance. |
| PR3-03 accepted gateway | `docs/phase3/PR3-03-evidence.md:7333`, `:7336`, `:7345` | Recorded CI runs `40073810419`/`40073808655` succeeded on `c5a91ba`; earlier local counts belong to `9f9fcd1`. Residual quadratic checks and unmeasured CI deadline margin remain limits. |
| D303-04 composition | `docs/phase3/PR3-03-contract-freeze.md:1778`, `:1789`, `:1802`; `src/researchbase/agent_runtime/application/capability_gateway.py:127`, `:170`, `:191` | In-UoW reserve/settle, identity-based trust, no second receipt/revision/transaction. Fake tree-node charge is zero; search accounting needs D1/Q3. |
| PR3-03 replay/fresh cadence | `src/researchbase/agent_runtime/application/capability_gateway.py:841`, `:901`, `:1070`; `docs/phase3/PR3-03-evidence.md:2044` | Current entitlement → committed receipt replay → new-write checks; retain checks after writes/forced constraints and distinguish own uncommitted effects. |
| PR3-04 acceptance and accounting | `docs/phase3/PR3-04-acceptance.md:3`, `:8`, `:24`, `:31`; `src/researchbase/agent_runtime/application/task_safety.py:122`, `:138`, `:247` | Owner acceptance conditional on green full-suite CI; records runs `40111940781`/`40111943031` on `2914208` without counts here. Two-review requirement was waived by owner. No new waiver or CI outcome inferred. A2/A3 reserve remains denied; positive node charges require an evaluator. |
| Shared locks/UoW | `src/researchbase/persistence/research_task_repository.py:13`; `src/researchbase/persistence/task_safety_repository.py:55`, `:70`, `:86`; `src/researchbase/persistence/uow.py:646`, `:661` | Exact SHARE prefix and synchronous writer; formal reads use one REPEATABLE READ READ ONLY snapshot. Broader checkpoint-locking helper is not the draft's read-only safety recipe. |
| Same-snapshot safety reads | `src/researchbase/agent_runtime/application/task_safety.py:692`, `:700` | Compose `safety_projection` in the search UoW; calling public `get_task_safety` would open another snapshot. |
| PR3-05 read-only acceptance | `docs/phase3/PR3-05-readonly-acceptance.md:9`, `:11`, `:56`, `:65`, `:115` | Accepted R1–R4 reads corroborate the snapshot pattern; PR3-16 has no required memory consumer. PR3-05 D1-C save/replay and D2-C save locks stay deferred; those D1/D2 are distinct from this pack's D1/D2. Full PR3-05, promotion and execution are not accepted. This refreshes `R:53`'s historical absence. |
| PR3-02-S2 availability | `docs/phase3/PR3-05-readonly-acceptance.md:118`; `C:207` | `docs/phase3/PR3-02-S2-contract-freeze.md` is absent from the r1 base but is not what r2 needs: on the r2 base, `docs/phase3/PR3-02-S2-execution-pack.md` and `PR3-02-S2-pack-review.md` are present (PR #14). They are proposals, and no accepted S2 freeze record is present. The S2 pack proposes a migration named `<approved_next_revision>` (its line 109), which competes for the slot after 0080. Do not infer delivered execution or import a sibling revision. |
| Scientific ownership / serialization | `src/researchbase/domain/run.py:22`, `:50`, `:99`; `src/researchbase/foundation/canonical_json.py:11`; `C:160` | Run owns status/seal/spec; normalize text before hashing and reverify saved owning hashes on admission/read. |

### 1.4 Owner answers mapped to observable checks

Every search node below is **PROPOSED / NOT RUN**; no owner answer is verified by naming a node. “Proposed” identifies a planned observable assertion, not implemented coverage. **MISSING** identifies a detail without a sufficiently specified check, including the five previously suggested but undefined nodes. The owning step must define the assertions and add every missing node to its command block during future freeze preparation; unresolved MISSING entries block freeze. A frozen test plan still does not verify behavior: implementation and recorded execution evidence require separate authorization. Architecture scans and entitlement/expiry tests do not establish identity verification or the absence of an AgentVersion prerequisite.

| Answer / accepted detail | Owning step and proposed observable check | Status |
| --- | --- | --- |
| D1/Q3 conservative admission | S4 `test_experiment_search.py::test_append_matches_frozen_budget_admission`; S8 `test_pr3_16_budget.py::test_cross_session_caps_depth_gaps_and_terminal_no_refund`: wrong reservation/depth/trust or stopped admission denied; charges retained | Proposed / NOT RUN; producer identity OPEN |
| D2 limited lifecycle, terminal ancestors | S3 `test_experiment_search_contracts.py::test_root_child_depth_and_terminal_ancestor_matrix` (unit doubles only); S8 owns `test_pr3_16_application.py::test_terminal_ancestor_blocks_child_in_database`, now selected explicitly in S8 | DB assertion definition MISSING / NOT RUN |
| D3/Q7 current verified Human/Agent identity | S8 must name a behavioral node admitting verified callers and denying an unverified Agent with zero protected effects, through the same Application commands | MISSING / NOT RUN; boundary/wait scans are not substitutes |
| D3/Q7 actor-only proof; no AgentVersion/availability prerequisite | S8 must name a positive planning node for an otherwise entitled verified Agent with no AgentVersion/availability row, preserving Agent attribution and disabled execution | MISSING / NOT RUN |
| Q7 wait/write/constraint cadence | S2 `test_experiment_search_repository.py::test_every_blocking_stage_calls_fresh_validation`; S8 `test_pr3_16_concurrency.py::test_each_wait_refreshes_entitlement_replay_and_expiry`: observe fresh checks and replay order after each wait | Proposed / NOT RUN; exact lock sequence OPEN |
| D4 multiple/reused Runs and duplicate-link replay | S5 `test_experiment_search.py::test_run_links_preserve_status_seal_and_scientific_rows`, `test_duplicate_link_differs_from_original_receipt_replay`; S8 `test_pr3_16_application.py::test_failed_pruned_negative_and_unexecuted_lineage_retained` | Proposed / NOT RUN |
| D4 same-project links | S5/S8 must name denial checks for a foreign-project Run; no relation, event, receipt or revision effect may survive | MISSING / NOT RUN |
| D4 node/Run ExperimentSpec equality when the node names a version | S5/S8 must name a mismatch-denial check and matching-version control without inferring a reference when the node has none | MISSING / NOT RUN |
| D5 typed optional frozen references | S8 owns `test_pr3_16_application.py::test_unfrozen_or_wrong_version_reference_denied`, now selected explicitly in S8 | Assertion definition MISSING / NOT RUN |
| D5 saved hash present iff its reference is present | S1/S8 must name checks for all presence combinations on each optional root/node reference: reject either mismatched pair; allow both absent or both valid | MISSING / NOT RUN |
| D5 saved owning hash reverified on admission | S4/S8 must name an exact-version/owning-hash contradiction check that denies admission without effects | MISSING / NOT RUN |
| D5 saved owning hash reverified on read | S6/S8 must name a persisted-hash contradiction check that rejects the read without repair; Q6 fixes the error class below | MISSING / NOT RUN |
| Q1 complete inventory before admission | S1 `test_pr3_16_schema.py::test_all_frozen_sql_definitions_compile_on_pg18`; S8 `test_pr3_16_guards.py::test_normal_role_scope_cycle_root_and_reservation_attacks`, `test_immutable_rows_and_receipt_effects_across_flushes` | Proposed / NOT RUN; exact inventory OPEN |
| Q1 RESTRICT foreign keys | S1 `test_pr3_16_schema.py::test_frozen_columns_keys_indexes_and_no_json_or_cascade`: inspect every admitted FK and require RESTRICT deletion semantics | Proposed / NOT RUN; exact FK inventory OPEN |
| Q1 no-op UPDATE/DELETE rejection | S8 `test_pr3_16_guards.py::test_immutable_rows_and_receipt_effects_across_flushes`: ordinary-role attempts against each of the four immutable tables fail without changing history | Proposed / NOT RUN |
| Q1 one root | S8 `test_pr3_16_guards.py::test_normal_role_scope_cycle_root_and_reservation_attacks`: reject a second root in the same session at the database boundary | Proposed / NOT RUN |
| Q1 unique event sequence | S1/S8 must name a database guard check rejecting a duplicate event sequence in its frozen uniqueness scope; the read-ordering check does not prove uniqueness | MISSING / NOT RUN; exact key definition OPEN |
| Q1 unique reservation use | S8 `test_pr3_16_guards.py::test_normal_role_scope_cycle_root_and_reservation_attacks`: reject reuse of a reservation at the database boundary, with no extra node or lineage effects | Proposed / NOT RUN |
| Q1 at most one terminal event per node | S1/S8 must name an ordinary-role database guard check rejecting a second terminal event for the same node, including a different terminal kind, without persisting the extra event | MISSING / NOT RUN; database enforcement is separate from Q4 command checks |
| Q1 at most one terminal event per session | S1/S8 must name an ordinary-role database guard check rejecting a second terminal event for the same session, including a different terminal kind, without persisting the extra event | MISSING / NOT RUN; database enforcement is separate from Q4 command checks |
| Q1 one revision, receipt and task event per command | S8 `test_pr3_16_application.py::test_all_commands_atomic_and_scientific_rows_unchanged`: assert exactly one of each for each fresh successful command plus its declared lineage effects; S8 `test_pr3_16_guards.py::test_immutable_rows_and_receipt_effects_across_flushes` rejects missing/extra effects | Proposed / NOT RUN |
| Q2 envelopes/material version 1/normalization and strategy omission | S3 `test_experiment_search_contracts.py::test_closed_envelopes_and_fixed_vectors`; S1 owns `test_pr3_16_schema.py::test_no_strategy_column`, now selected explicitly in S1 | No-column assertion definition MISSING / NOT RUN; vectors and staging approval OPEN |
| Q4 closure-time cutoff and current authority on new reconciliation | S5 `test_experiment_search.py::test_closure_blocks_mutations_and_allows_frozen_reconciliation` must distinguish allowed historical links from ambiguous/new work and denied current authority | Durable-proof check MISSING / NOT RUN (proof OPEN) |
| Q4 fresh repeated or conflicting terminal commands rejected without effects | S5/S8 must name checks using new command IDs for repeated/conflicting node and session terminal requests; assert unchanged lineage, task revision, receipts and task events, with original-receipt replay as a separate control | MISSING / NOT RUN |
| Q5 structural duplicate constraints | S5 owns `test_experiment_search.py::test_duplicate_id_and_link_constraints_enforced`, now selected explicitly in S5; duplicate IDs/links fail (not a semantic duplicate-branch check) | Assertion definition MISSING / NOT RUN |
| Q5 no inferred root/node equality, inheritance or Hypothesis/ExperimentSpec relationship | S5/S8 must name controls allowing otherwise valid independent references under owning-domain rules | MISSING / NOT RUN |
| Q5 semantic detection | Staged to a later contract; no check in this slice; Phase 3 duplicate-branch obligation remains OPEN | Staged / NOT RUN |
| Q6 whole-tree bounded reads | S6 `test_experiment_search_queries.py::test_tree_keeps_failed_pruned_negative_and_unexecuted_branches`; S8 `test_pr3_16_application.py::test_recheck_cadence_and_query_work_at_frozen_bounds`: enforce separate node/depth/event/link bounds without silent history truncation | Proposed / NOT RUN; numeric bounds OPEN |
| Q6 event-sequence and Run-link ID ordering | S6 `test_experiment_search_queries.py::test_scope_hash_and_ordering_follow_frozen_read_contract`: shuffle insertion order, then assert exact event-sequence and Run-link ID order | Proposed / NOT RUN |
| Q6 NOT_FOUND for entitled absent targets | S6/S8 must name a read-error check asserting NOT_FOUND, with entitled and unauthorized callers distinguished | MISSING / NOT RUN |
| Q6 referential-integrity failure for corrupt ancestry | S6/S8 must name a read-error check asserting REFERENTIAL_INTEGRITY_ERROR on corrupt ancestry, without repair or foreign ID/SQL disclosure | MISSING / NOT RUN |
| Q6 provenance-closure failure for saved-hash contradictions | S6/S8 must name a read-error check asserting PROVENANCE_CLOSURE_VIOLATION and a sanitized envelope, without saved-hash repair | MISSING / NOT RUN |
| Q8 Application-only, no transport | S7 owns `tests/architecture/test_pr3_16_boundaries.py::test_no_api_or_cli_routes_added`, now selected explicitly in S7 | Assertion definition MISSING / NOT RUN |
| Q8 conditional 0081 / single head | S1 `test_pr3_16_migration.py::test_forward_only_migration_and_single_head`: require one forward-only head with the frozen revision/parent; 0081 after 0080 is conditional on the rechecked integration head and reconciliation of the competing PR3-02-S2 proposal | Proposed / NOT RUN; revision/ref reconciliation OPEN |

## 2. Rules shared by every sub-task

**Authorization rule:** every S1–S8 is not authorized until the owner approves this pack's freeze; separate implementation authorization and every G0 condition must also be satisfied. Future commands are not instructions to execute during this documentation task.

**Architecture rule:** Caller → Application → port/UoW → persistence → PostgreSQL 18; synchronous DB I/O; one command/transaction; no scientific cascade, generic JSON provenance, copied Run truth, external/provider I/O under locks, new dependency or governing Harness change (`AGENTS.md:59`; `C:54`, `C:215`).

**Stop rule G:** document a concrete conflicting pack/source `file:line`, impact and blocked observable check; leave dependent work unstarted and record Deviations. Do not invent semantics to fill OPEN answers. Required missing evidence, zero collection or skips are not PASS; no acceptance with open P0/P1 (`C:315`; `AGENTS.md:126`).

**SQL rule L:** named complete multiline SQL definitions and parameterized queries within existing lint limits; preserve frozen bytes and ancestor migrations; no trigger disabling, lint exemption or automatic splitting on semicolons (`docs/phase3/PR3-03-implementation-plan.md:65`).

**Evidence rule E:** each step records exact commands, stdout/stderr, exit codes, actual collected/passed/failed/skipped counts, requirement → node mapping, revision/environment and Deviations. Store future raw captures under ignored `tmp/pr3-16/`; independent review and the external full-suite loop remain required. Historical counts are not current verification (`C:313`–`C:315`; `AGENTS.md:126`).

**Common future gate C** after each step; run separately and preserve each result:

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
git diff --check HEAD
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run alembic heads
```

Future setup: `uv sync --locked --group dev`; explicitly select disposable local PG18 via `RB_TEST_ADMIN_URL` and PG18 client tools. Suites requiring `DATABASE_URL` need a separate disposable runtime database. Use approved random prefixes; never application data or SQLite (`tests/disposable_postgres.py:20`, `:27`, `:53`). No search test exists yet; the proposed selections become runnable only after its authorized step adds them.

## 3. Sub-tasks

Follow the proposed S1–S8 order defined in this section. The local historical review identifies this sequencing as a plan proposal (`R:66`–`R:67`); it is not a frozen architecture rule. In file lists only, **AR** = `src/researchbase/agent_runtime/`, **DB** = `src/researchbase/persistence/`, **U** = `tests/unit/phase3/`, **I** = `tests/integration/phase3/`, **A** = `tests/architecture/`; concatenate prefix and suffix. All new names and tests remain proposals pending Q8. Every step includes C/E and stops under G.

### S1 — Forward schema and compile/compatibility gate

**Authorization:** not authorized until the owner approves this pack's freeze, gives separate implementation authorization (G0-X), and all G0 conditions are met.

Files: proposed `migrations/versions/0081_experiment_search_core.py` (conditional Q8 assignment), `I/search_fixtures.py`, `I/test_pr3_16_schema.py`, `I/test_pr3_16_migration.py`, and Appendix H's exact maintenance inventory. Dependencies: G0, D1/Q1/Q8. Translate only the admitted four-table inventory, support keys and receipt/task-event guard extensions; no Application behavior (`C:147`, `C:299`).

```sh
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_16_schema.py::test_all_frozen_sql_definitions_compile_on_pg18 tests/integration/phase3/test_pr3_16_schema.py::test_frozen_columns_keys_indexes_and_no_json_or_cascade
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_16_schema.py::test_no_strategy_column
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_16_migration.py::test_clean_and_populated_upgrade_preserve_accepted_rows tests/integration/phase3/test_pr3_16_migration.py::test_forward_only_migration_and_single_head
# Existing regression nodes; r2 focused results are in §5.1; this future gate is NOT RUN.
uv run pytest -o addopts='' -ra tests/unit/test_ci_migration_head.py::test_ci_migration_head_assertion_matches_repository_head
```

Gate: PG18 compiles every frozen body; record actual inventory/count, normal-role guards, sole head, clean/populated upgrade, old rows/hashes/receipts and guard attachments. Run H regressions after compilation; no borrowed “13/13” count.

### S2 — Repository ports, lock composition and stored-row reads

**Authorization:** not authorized until the owner approves this pack's freeze, gives separate implementation authorization (G0-X), and all G0 conditions are met.

Files: new `AR/ports/search_repository.py`, `DB/experiment_search_repository.py`, `U/test_experiment_search_repository.py`; update `DB/models.py`, `DB/uow.py`; factor existing safety port/adapter only if Q7 freezes that need. Dependencies: S1 and Q7. Implement approved first SHARE/advisory/row/read recipe; no Run/immutable-lineage row locking or implicit checkpoint updates (`R:51`; `C:215`).

```sh
uv run pytest -o addopts='' -ra tests/unit/phase3/test_experiment_search_repository.py::test_first_statement_and_complete_lock_order tests/unit/phase3/test_experiment_search_repository.py::test_every_blocking_stage_calls_fresh_validation tests/unit/phase3/test_experiment_search_repository.py::test_immutable_reads_do_not_lock_runs_or_lineage tests/unit/phase3/test_experiment_search_repository.py::test_formal_read_has_one_snapshot_and_no_writes
# Existing regression nodes; r2 focused results are in §5.1; this future gate is NOT RUN.
uv run pytest -o addopts='' -ra tests/unit/phase3/test_capability_gateway_repository.py tests/unit/phase3/test_task_safety_transports.py
```

Gate: recorded SQL/callback order, no constructor SQL, no ORM/Session leakage, accepted-caller compatibility. Recording doubles do not prove PostgreSQL contention; S8 does.

### S3 — Closed values, lifecycle predicates and hash vectors

**Authorization:** not authorized until the owner approves this pack's freeze, gives separate implementation authorization (G0-X), and all G0 conditions are met.

Files: new `AR/domain/experiment_search.py`, `AR/application/search_contracts.py`, `U/test_experiment_search_contracts.py`. Dependencies: S1–S2; D2/D5/Q2/Q4/Q5/Q6. Implement only frozen fields/defaults, lifecycle predicates and exact-reference material; keep old vectors unchanged (`C:87`, `C:130`, `C:297`).

```sh
uv run pytest -o addopts='' -ra tests/unit/phase3/test_experiment_search_contracts.py::test_closed_envelopes_and_fixed_vectors tests/unit/phase3/test_experiment_search_contracts.py::test_nfc_uuid_defaults_and_reason_bounds tests/unit/phase3/test_experiment_search_contracts.py::test_root_child_depth_and_terminal_ancestor_matrix tests/unit/phase3/test_experiment_search_contracts.py::test_no_score_success_or_execution_semantics
# Existing regression nodes; r2 focused results are in §5.1; this future gate is NOT RUN.
uv run pytest -o addopts='' -ra tests/unit/phase3/test_research_task_contracts.py::test_fixed_vectors tests/unit/phase3/test_task_safety_contracts.py::test_fixed_hash_vectors tests/unit/phase3/test_agent_version_contracts.py::test_literal_vectors tests/unit/phase3/test_capability_gateway_contracts.py
```

Gate: field/default/normalization/vector matrix maps to passing nodes; literal expected vectors are independent of the implementation. No generic JSON escape hatch or invented lifecycle edge.

### S4 — Session/node commands and approved budget admission

**Authorization:** not authorized until the owner approves this pack's freeze, gives separate implementation authorization (G0-X), and all G0 conditions are met.

Files: new `AR/application/experiment_search.py`, `U/test_experiment_search.py`, `U/search_fixtures.py`; update S2 port/adapter. The separately reviewed atomic amendment (D1) is not in S4's file list, so S4 adds no task-safety files until that amendment is reviewed. Dependencies: S1–S3, D1/Q3. Implement stable-ID retry/replay writer and session/node effects under task CAS; no second ledger, nested safety command or reinterpretation of `FAKE_RESOURCES` (`C:137`, `C:174`, `C:184`).

```sh
uv run pytest -o addopts='' -ra tests/unit/phase3/test_experiment_search.py::test_create_session_has_one_receipt_and_no_execution tests/unit/phase3/test_experiment_search.py::test_append_matches_frozen_budget_admission tests/unit/phase3/test_experiment_search.py::test_all_sessions_share_caps_and_sticky_stops tests/unit/phase3/test_experiment_search.py::test_rollback_at_each_write_and_constraint_stage tests/unit/phase3/test_experiment_search.py::test_current_entitlement_and_saved_replay_precede_cas_after_every_wait
# Existing regression nodes; r2 focused results are in §5.1; this future gate is NOT RUN.
uv run pytest -o addopts='' -ra tests/unit/phase3/test_task_budget_accounting.py tests/unit/phase3/test_capability_gateway.py::test_request_atomic_effects_exact_vector_refs_and_no_nested_safety tests/unit/phase3/test_capability_gateway.py::test_exact_final_unit_sets_sticky_stop_and_denies_next_request
```

Gate: chosen admission semantics, exact one-receipt/event/revision effects, depth/evaluator denial, charged gaps and whole rollback; own uncommitted effects neither replay nor double count. Conservative admission cannot borrow gateway's own-stop exception.

### S5 — Run links, branch terminal events and closure/replay

**Authorization:** not authorized until the owner approves this pack's freeze, gives separate implementation authorization (G0-X), and all G0 conditions are met.

Files: S4 Application/unit module and existing search fixtures; S2 port/adapter. Dependencies: S1–S4, D2/D4/Q4/Q5. Add immutable exact Run links and failure/prune/close events; preserve descendants, reasons, input seals and scientific outcomes; no refund or scientific success (`C:64`, `C:99`).

```sh
uv run pytest -o addopts='' -ra tests/unit/phase3/test_experiment_search.py::test_run_links_preserve_status_seal_and_scientific_rows tests/unit/phase3/test_experiment_search.py::test_failure_without_run_and_prune_retain_descendants tests/unit/phase3/test_experiment_search.py::test_closure_blocks_mutations_and_allows_frozen_reconciliation tests/unit/phase3/test_experiment_search.py::test_duplicate_link_differs_from_original_receipt_replay tests/unit/phase3/test_experiment_search.py::test_uncertain_commit_recovers_original_ids tests/unit/phase3/test_experiment_search.py::test_three_transient_attempts_and_no_timeout_retry
uv run pytest -o addopts='' -ra tests/unit/phase3/test_experiment_search.py::test_duplicate_id_and_link_constraints_enforced
```

Gate: all approved transition/denial/reconciliation cases, any Run status, exact saved results after later links/events, lost-response recovery and unchanged scientific/accounting rows.

### S6 — Tree, branch lineage and shared-budget snapshot queries

**Authorization:** not authorized until the owner approves this pack's freeze, gives separate implementation authorization (G0-X), and all G0 conditions are met.

Files: new `DB/experiment_search_queries.py`, `U/test_experiment_search_queries.py`; update S4 Application, S3 read DTOs and S2 port/adapter. Dependencies: S1–S5, Q6. Use one entitled formal-read UoW for tree, paths, current Run/seal labels and existing safety projection (`C:119`, `C:261`).

```sh
uv run pytest -o addopts='' -ra tests/unit/phase3/test_experiment_search_queries.py::test_tree_keeps_failed_pruned_negative_and_unexecuted_branches tests/unit/phase3/test_experiment_search_queries.py::test_root_to_node_path_and_exact_links tests/unit/phase3/test_experiment_search_queries.py::test_budget_projection_uses_same_uow tests/unit/phase3/test_experiment_search_queries.py::test_current_run_seal_labels_and_empty_tree tests/unit/phase3/test_experiment_search_queries.py::test_scope_hash_and_ordering_follow_frozen_read_contract
# Existing regression nodes (not run for r2).
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_04_queries.py
```

Gate: complete retained lineage, frozen Q6 order/bounds, empty tree without success, no foreign identity disclosure, no repair/write/lock/second snapshot. S8 proves database coherence.

### S7 — Complete unit and architecture boundary evidence

**Authorization:** not authorized until the owner approves this pack's freeze, gives separate implementation authorization (G0-X), and all G0 conditions are met.

Files: new `A/test_pr3_16_boundaries.py`; complete S2–S6 unit files/fixtures. Dependencies: S1–S6. Preserve earlier boundary tests and use a deliberate violation fixture to prove scanner detection (`C:297`, `C:298`).

```sh
uv run pytest -o addopts='' -ra tests/architecture/test_pr3_16_boundaries.py::test_human_and_agent_share_application_boundary tests/architecture/test_pr3_16_boundaries.py::test_domain_has_no_orm_transport_provider_dependencies tests/architecture/test_pr3_16_boundaries.py::test_no_execution_promotion_strategy_or_new_dependency tests/architecture/test_pr3_16_boundaries.py::test_boundary_scanner_detects_deliberate_violation
uv run pytest -o addopts='' -ra tests/architecture/test_pr3_16_boundaries.py::test_no_api_or_cli_routes_added
# Existing unit regression directory; r2 results are in §5.1; future search additions are NOT RUN.
uv run pytest -o addopts='' -ra tests/unit/phase3
# Existing regression nodes; r2 focused results are in §5.1; this future gate is NOT RUN.
uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture
```

Gate: all six commands, three queries and frozen denial/replay/terminal predicates mapped to actual passing nodes; old vectors and disabled execution preserved. Production defects return to their owning step; doubles do not close DB guarantees.

### S8 — PostgreSQL guards, contention, performance and acceptance evidence

**Authorization:** not authorized until the owner approves this pack's freeze, gives separate implementation authorization (G0-X), and all G0 conditions are met.

Files: complete S1 schema/migration/fixtures; new `I/test_pr3_16_guards.py`, `I/test_pr3_16_application.py`, `I/test_pr3_16_budget.py`, `I/test_pr3_16_concurrency.py`, `I/test_pr3_16_replay.py`, `I/test_pr3_16_queries.py`, `docs/phase3/PR3-16-evidence.md`. `I/conftest.py` only if frozen fixture registration requires it; README only if Q8 admits it. Dependencies: S1–S7 (`C:299`–`C:302`). Seed scientific rows through owning Application commands; raw SQL attacks use ordinary DML role.

| Proposed node (prefix `tests/integration/phase3/`) | Observable evidence |
| --- | --- |
| `test_pr3_16_guards.py::test_normal_role_scope_cycle_root_and_reservation_attacks` | Same task/project/session, second root, cycles/reparenting, reused reservation, exact version/hash and FK indexes. |
| `test_pr3_16_guards.py::test_immutable_rows_and_receipt_effects_across_flushes` | Four-table no-op UPDATE/DELETE rejection; missing/extra effects and committed receipt reuse roll back; old guard cases/attachments survive. |
| `test_pr3_16_application.py::test_all_commands_atomic_and_scientific_rows_unchanged` | Exact revision/receipt/task-event/cardinality; fault at every write; no Run/Measurement/Claim mutation. |
| `test_pr3_16_application.py::test_failed_pruned_negative_and_unexecuted_lineage_retained` | Retained identities/reasons and D4 multiple/reused Run relations after pruning/closure/reconciliation. |
| `test_pr3_16_application.py::test_terminal_ancestor_blocks_child_in_database` | D2: a fresh append beneath a terminal ancestor is denied in real PG18 with zero new node/receipt/event/revision effects; existing descendants remain. Assertion definition MISSING / NOT RUN. |
| `test_pr3_16_application.py::test_unfrozen_or_wrong_version_reference_denied` | D5: unfrozen or wrong exact scientific references are denied without effects. Assertion definition MISSING / NOT RUN; the separate hash-presence/admission/read checks in §1.4 are still MISSING. |
| `test_pr3_16_budget.py::test_cross_session_caps_depth_gaps_and_terminal_no_refund` | D1/Q3 depth/evaluator/trust, stop/expiry/gates, charged gaps/UNKNOWN, no refund or invented Run accounting. |
| `test_pr3_16_concurrency.py::test_observed_lock_order_and_competing_writers` | DB-observed waits; append versus append/stop/cancel/close/settle/revoke. |
| `test_pr3_16_concurrency.py::test_each_wait_refreshes_entitlement_replay_and_expiry` | Every acquisition/DML/FK wait rechecks; saved replay precedes CAS; DB times prove cross-expiry denial. |
| `test_pr3_16_replay.py::test_lost_response_hash_conflict_and_bounded_retries` | Original IDs after lost/uncertain commit; hash conflict; no duplicate effects; only 40001/40P01, at most three attempts. |
| `test_pr3_16_queries.py::test_one_lock_free_snapshot_under_concurrent_writer` | Tree/path/events/Run/safety coherent in one snapshot; zero exclusion locks, repairs or second session. |
| `test_pr3_16_application.py::test_recheck_cadence_and_query_work_at_frozen_bounds` | Per-write cadence and query/guard counts at Q6-approved sizes; separately captured unprofiled timings. |

```sh
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_16_application.py::test_terminal_ancestor_blocks_child_in_database tests/integration/phase3/test_pr3_16_application.py::test_unfrozen_or_wrong_version_reference_denied
uv run pytest -o addopts='' -ra --junitxml=tmp/pr3-16/schema.xml tests/integration/phase3/test_pr3_16_schema.py tests/integration/phase3/test_pr3_16_guards.py tests/integration/phase3/test_pr3_16_migration.py
uv run pytest -o addopts='' -ra -s --durations=0 --junitxml=tmp/pr3-16/behavior.xml tests/integration/phase3/test_pr3_16_application.py tests/integration/phase3/test_pr3_16_budget.py tests/integration/phase3/test_pr3_16_concurrency.py tests/integration/phase3/test_pr3_16_replay.py tests/integration/phase3/test_pr3_16_queries.py
# Existing regression nodes (not run for r2).
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_01_replay.py tests/integration/phase3/test_pr3_02_s1_schema.py tests/integration/phase3/test_pr3_04_accounting.py tests/integration/phase3/test_pr3_04_concurrency.py tests/integration/phase3/test_pr3_04_queries.py
# Existing regression nodes (not run for r2).
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_03_guards.py tests/integration/phase3/test_pr3_03_migration.py tests/integration/phase3/test_pr3_03_replay.py tests/integration/phase3/test_pr3_03_input_versions.py
```

Gate: actual focused counts, manifests/hash parity, normal-role effects, wait/backend/timestamp traces, timing environment and P0–P3 dispositions. Include PR3-05 read regressions if shared UoW changes affect them. External loop supplies exact full-suite shard inventory/commands/counts/JUnit; missing output/review stays PENDING. No local whole-suite run.

## 4. Exact order and progression gates

**G0 → S1 → S2 → S3 → S4 → S5 → S6 → S7 → S8 → external full-suite check + independent review → STOP at PR3-16.** Each predecessor's stated gate plus C/E must pass before its successor. Freeze approval does not substitute for implementation authorization. Open P0/P1 or missing required evidence blocks acceptance (`C:315`; `AGENTS.md:147`).

### 4.1 Risks and mitigations

| Risk | Mitigation / required evidence |
| --- | --- |
| Scientific history rewritten or losers hidden | Four immutable tables, concrete RESTRICT FKs, fixed parent/reference/hash, all failed/pruned/negative/unexecuted branches retained. Verify unchanged scientific rows; PR3-17 scores cannot become Measurements or Claim support (`C:61`, `C:157`; `A3:1296`, `A3:1957`). |
| Lock inversion, stale entitlement or false replay after wait | Freeze Q7; exact first 18-table SHARE and common advisory prefix, identity keys before rows, no new namespace/lock upgrade. Preserve current entitlement → committed replay → fresh new-write checks after waits, DML and forced constraints; exclude own uncommitted receipt. Observe actual `pg_locks`/backend waits and database timestamps, not sleeps (`C:137`, `C:215`; `src/researchbase/agent_runtime/application/capability_gateway.py:841`, `:901`, `:1070`). |
| Reconciliation becomes new execution or budget bypass | Q4 must define already-existing-work proof; reconcile only exact Run links with current authority, never spend/start/cancel/refund/reopen. Preserve stopped-task denial and charged gaps; shared task accounting spans sessions (`C:67`, `C:184`). |
| 60-second admission deadline and repeated validation cost | PR3-03's instrumented attempt failed after the 60-second reservation deadline (`docs/phase3/PR3-03-evidence.md:7035`); acceptance preserves quadratic per-row rechecks (`:7345`). Measure SQL work per pass and total passes at Q6-approved bounds; batch exact reads within one pass only. Keep fresh checks, error order and deadlines; separate instrumented counts from unprofiled timings. This is a gateway lesson, not an invented PR3-16 deadline/SLO. |
| CI runner timing differs from local samples | CI deadline margin was not measured (`docs/phase3/PR3-03-evidence.md:7346`). Capture runner/PG settings and setup/call/teardown times, bounded waiter diagnostics and full-UUID consistent principals. CI is six Ubuntu shards, PG18, 120-minute jobs; JIT attribution remains unverified (`.github/workflows/ci.yml:9`, `:23`, `:70`). Diagnose 57014/timeouts without automatic retry or deadline widening; only 40001/40P01 allow three total fresh attempts (`C:255`). |
| Head/catalog drift weakens accepted tests | Appendix H changes only current expectations and exact reviewed catalog deltas; historical fixture revisions, definitions and hash manifests stay pinned. Reinspect actual integration head before assignment. Retain both prior command guards and no-op immutability rejection (`C:169`, `C:174`). |

## Appendix H — Mechanical head maintenance owned by S1

Measured source head is `0080_capability_gateway` (`migrations/versions/0080_capability_gateway.py:5`); parent `0079_agent_identity_versions` is declared at `migrations/versions/0080_capability_gateway.py:6`. Conditional next head: **`0081_experiment_search_core`**, `down_revision = "0080_capability_gateway"`, only if 0080 is still sole integration head. No revision is reserved; a prior S2/other migration requires re-parenting and updated inventory. The draft's 0079/“0080+” baseline is historical (`C:34`).

Observed references below would change after Q8 freezes the new head. These are exact locations, not permission for global replacement. Q1 must still supply exact schema/support-key/helper/trigger deltas before the inventory can be complete.

| Current reference (file:line) | Future maintenance |
| --- | --- |
| `.github/workflows/ci.yml:66`; `tests/unit/test_ci_migration_head.py:12` | Advance CI's current-head assertion; the unit test derives expected head dynamically and should run unchanged. Keep six shards/JUnit policy at `:70`/`:77`; duration data changes only from measured results, never guessed timings. |
| `tests/fixtures/phase2_static_baseline.json:4` | Advance active `migration_head` only; retain historical baseline commit/Pyright fields. |
| `tests/architecture/test_import_boundaries.py:198`; `tests/unit/test_batch_c_migration_history.py:42`; `tests/unit/test_task12_migration_history.py:61`, `:65` | Append the exact migration to inventories/linear chain and advance head; retain all historical byte/hash pins. |
| `tests/architecture/test_b02_strategy_promotion_boundaries.py:77`; `tests/architecture/test_b04_boundaries.py:43`; `tests/architecture/test_b05_review_boundaries.py:76` | Advance current-head assertions. |
| `tests/architecture/test_b20_screening_boundaries.py:32`, `:34`; `tests/architecture/test_basic_approval.py:55`, `:57`; `tests/unit/phase2/test_pr2_04_r8a_host_topology.py:38`, `:40` | Advance current head and its immediate parent to the frozen new revision/0080 pair. |
| `tests/architecture/test_pr3_02_s1_boundaries.py:12`; `tests/unit/phase2/test_pr2_20_inventory.py:54` | Advance current-head/inventory-tail assertions; retain explicit 0079 → 0078 historical assertion. |
| `tests/integration/phase2/test_pr2_03_review_guards.py:572`; `tests/integration/phase2/test_pr2_04_execution_migration.py:73`; `tests/integration/phase2/test_pr2_04_migration_coverage.py:144`, `:273` | Advance repository-head assertions; keep historical migration subjects. |
| `tests/integration/phase2/test_pr2_15_decision_schema.py:60`; `tests/integration/phase2/test_revision_action.py:509`; `tests/integration/phase2/test_pr2_17_authorship_schema.py:61` | Advance repository-head assertions only. |
| `tests/integration/phase3/test_pr3_00_bootstrap.py:101`; `tests/integration/phase3/test_pr3_01_migration.py:37`; `tests/integration/phase3/test_pr3_04_migration.py:120`; `tests/integration/phase3/test_pr3_02_s1_migration.py:56`; `tests/integration/phase3/test_pr3_03_migration.py:77` | Advance repository-head assertions, including the newly relevant PR3-03 check; preserve explicit historical upgrades, catalogs and downgrade refusal evidence. |
| `tests/integration/phase2/pr2_20_support.py:160`; `tests/integration/phase2/test_pr2_20_migrations.py:187` | The 0079 → current-head comparison currently permits only named 0080 deltas. Review/add exact frozen PR3-16 catalog additions/replacements, retaining the 0080 inventory and unchanged prior-object definitions. Full new delta is OPEN under Q1; never blanket-exclude all new objects or weaken comparison. |

Keep pinned: `tests/integration/phase3/gateway_fixtures.py:48` at 0080; `tests/integration/phase3/agent_fixtures.py:102` at 0079; `tests/integration/phase3/conftest.py:93` at 0078; explicit 0080 upgrades in `test_pr3_03_migration.py:64`, `:121`, `:334`; explicit 0079 setup in `test_pr3_02_s1_migration.py:55` and `tests/integration/phase2/test_pr2_20_migrations.py:187`. New search fixtures alone advance to the new revision.

Future H verification after S1's compile gate (plus S1/S7/S8 selections):

```sh
# Existing regression nodes; r2 focused results are in §5.1; this future gate is NOT RUN.
uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture
# Existing regression nodes (not run for r2 except the CI-head node covered in §5.1).
uv run pytest -o addopts='' -ra tests/unit/test_ci_migration_head.py tests/unit/test_batch_c_migration_history.py tests/unit/test_task12_migration_history.py tests/unit/phase2/test_pr2_04_r8a_host_topology.py tests/unit/phase2/test_pr2_20_inventory.py tests/unit/phase2/test_pr2_04_static_acceptance.py
# Existing regression nodes (not run for r2).
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_00_bootstrap.py tests/integration/phase3/test_pr3_01_migration.py tests/integration/phase3/test_pr3_04_migration.py tests/integration/phase3/test_pr3_02_s1_migration.py tests/integration/phase3/test_pr3_03_migration.py
# Existing regression nodes (not run for r2).
uv run pytest -o addopts='' -ra tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_04_migration_coverage.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_revision_action.py tests/integration/phase2/test_pr2_17_authorship_schema.py tests/integration/phase2/test_pr2_20_migrations.py
```

## 5. Verification of this documentation-only task

**Scope:** t322 revised the pack and owner-answers record; t324 also revises ADR-0026. The table below preserves the r1 baseline measured on 2026-10-25 against `docs/phase3/PR3-16-execution-pack.md`; that r1 artifact is absent from this checkout, so its baseline cannot be re-inspected here. Those historical counts are not r2 evidence. Historical t322 checks are in §5.1; current t324 checks are in §5.2.

**r1-only environment and scope:** `export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"`. Only the r1 Markdown pack was authored; no code, migration, test, contract, ADR or Harness edit. r1 recorded `uv sync --locked --group dev` exiting 0 (38 packages resolved, 34 installed into the local environment); dependency definitions stayed unchanged. The following are historical baseline/documentation checks on 2026-10-25, not PR3-16 implementation acceptance. Future S1–S8/H gates remain NOT RUN.

| Exact command | Observed output / result | Exit |
| --- | --- | --- |
| `uv run --locked ruff check .` | `All checks passed!` | 0 |
| `uv run --locked ruff format --check .` | `931 files already formatted` | 0 |
| `uv run --locked pyright` | `0 errors, 0 warnings, 0 informations`; separate available-version notice (1.1.411 → 1.1.414), no upgrade performed | 0 |
| `uv run --locked alembic heads` | `0080_capability_gateway (head)` | 0 |
| `uv run --locked pytest -o addopts="" -q tests/unit/phase3 tests/architecture tests/unit/architecture tests/unit/test_ci_migration_head.py` | `1399 passed, 51 warnings in 30.42s`; warnings are Alembic `path_separator` deprecations; no failures/skips reported | 0 |
| `git diff --check HEAD` | Empty stdout/stderr | 0 |
| `test -s docs/phase3/PR3-16-execution-pack.md && echo pack-present` | `pack-present` | 0 |
| `git diff --no-index --check /dev/null docs/phase3/PR3-16-execution-pack.md` | Empty stdout/stderr; no whitespace diagnostics. Exit 1 denotes the new-file difference, not an exit-0 test. | 1 |

**r1-only handoff note (historical):** the extra no-index inspection covered the then-untracked r1 pack, which `git diff --check HEAD` alone omitted. No staging was performed. The instruction that the final handoff repeat required checks and show only that new Markdown file belonged to r1. t322 covered its two tracked files and reported results in §5.1; t324 covers all three permitted files in §5.2.

PostgreSQL/migration behavior suites are NOT RUN: this documentation change touches no executable/database suite. No PR3-16 implementation test can be run before it exists. The whole suite belongs to the external check loop; its output is not available in this authoring task and no result is assumed.

### 5.1 r2 review B round 7 checks (t322, 2026-10-26)

Run against both tracked files, with no staging, commit, push or branch creation. The task started from clean HEAD `ba03f96cce6129932a184566acf170147b3cea3d` on `fix-pr316-r2`. The commands below are historical t322 evidence only; they do not execute the proposed search nodes or authorize any future gate. No checked blob hashes were recorded, and the pack was edited afterward to include the results. Its final bytes are therefore not established by these whitespace checks. Whitespace checks must be rerun on the final bytes after every further edit; §5.2 records t324 verification separately.

Every `uv` command in this table was invoked with the exact prefix `UV_CACHE_DIR="$PWD/tmp/t322-uv-cache"`. The first invocation created the ignored `.venv` with CPython 3.12.15 and installed 34 locked packages; dependency definitions were unchanged.

| Exact command | Observed output / result | Exit |
| --- | --- | --- |
| `uv run --locked ruff check .` | `All checks passed!` | 0 |
| `uv run --locked ruff format --check .` | `931 files already formatted` | 0 |
| `uv run --locked pyright` | `0 errors, 0 warnings, 0 informations`; available-version notice v1.1.411 → v1.1.414; no upgrade performed | 0 |
| `uv run --locked alembic heads` | `0080_capability_gateway (head)` | 0 |
| `uv run --locked pytest -o addopts='' -q tests/unit/phase3 tests/architecture tests/unit/architecture tests/unit/test_ci_migration_head.py` | `1399 passed, 51 warnings in 31.29s`; all 51 warnings are Alembic `path_separator` deprecations; no failures or skips reported | 0 |
| `test -s docs/phase3/PR3-16-execution-pack-r2.md` | Empty stdout/stderr | 0 |
| `test -s docs/phase3/PR3-16-owner-answers-record.md` | Empty stdout/stderr | 0 |
| `git diff --no-index --check /dev/null docs/phase3/PR3-16-execution-pack-r2.md` | Empty stdout/stderr; no whitespace diagnostics. Exit 1 records the file difference against `/dev/null`, not an exit-0 check. | 1 |
| `git diff --no-index --check /dev/null docs/phase3/PR3-16-owner-answers-record.md` | Empty stdout/stderr; no whitespace diagnostics. Exit 1 records the file difference against `/dev/null`, not an exit-0 check. | 1 |
| `git diff --check HEAD` | Empty stdout/stderr | 0 |

**UNVERIFIED historical document-audit claims:** t322 reported unchanged answer rows/recommendation paragraphs against its HEAD, five previously omitted nodes present in owning-step shell blocks, three exact Appendix S excerpts, and only two authorized paths in its tracked diff. No exact commands, stdout/stderr or exit codes were retained for those claims, so they are not verified evidence. The reproducible t324 audit in §5.2 checks the current documents against its explicit baseline; it does not retroactively verify t322. Proposed search nodes remain NOT RUN.

PostgreSQL/integration/migration behavior suites: **NOT RUN**, zero suites invoked; neither Markdown change touches database behavior. `alembic heads` inspects the source revision graph only. New search nodes: **NOT RUN**, not implemented. Whole-suite run: **NOT RUN** by this author; the external loop's output remains **UNVERIFIED / not yet supplied**. No CI result, freeze, schema admission or implementation authorization is claimed.

### 5.2 t324 document corrections and focused verification (2026-10-26)

Baseline: clean `cde62c66bdf00a9f64aa47e0579e1f3c152576f0`, also the local `pr316-pack-r2` ref, on the existing `fix/p2-pr316` branch. Only the three permitted Markdown files changed. No branch creation, staging, commit, push, freeze, schema admission or implementation authorization occurred.

All `uv` commands below used the exact prefix `UV_CACHE_DIR="$PWD/tmp/t324-uv-cache"`. The first invocation created the ignored `.venv` using CPython 3.12.15, built the local package and installed 34 locked packages. Dependency definitions were unchanged. Results are documentation-task regressions, not evidence for unimplemented search behavior.

| Exact command (with the prefix above for `uv`) | Observed output / result | Exit |
| --- | --- | --- |
| `uv run --locked ruff check .` | `All checks passed!` after the environment setup described above | 0 |
| `uv run --locked ruff format --check .` | `931 files already formatted` | 0 |
| `uv run --locked pyright` | `0 errors, 0 warnings, 0 informations`; available-version notice v1.1.411 → v1.1.414; no upgrade performed | 0 |
| `uv run --locked alembic heads` | `0080_capability_gateway (head)` | 0 |
| `uv run --locked pytest -o addopts='' -q tests/unit/phase3 tests/architecture tests/unit/architecture tests/unit/test_ci_migration_head.py` | `1399 passed, 51 warnings in 33.10s`; 0 failed, 0 skipped; all 51 warnings are Alembic `path_separator` deprecations | 0 |
| `git diff --check HEAD` | Empty stdout/stderr | 0 |
| `git diff --no-index --check /dev/null docs/phase3/PR3-16-execution-pack-r2.md` | Empty stdout/stderr; no whitespace diagnostics; exit 1 denotes the file difference | 1 |
| `git diff --no-index --check /dev/null docs/phase3/PR3-16-owner-answers-record.md` | Empty stdout/stderr; no whitespace diagnostics; exit 1 denotes the file difference | 1 |
| `git diff --no-index --check /dev/null docs/architecture/adr/ADR-0026-pr3-16-experiment-search-core.md` | Empty stdout/stderr; no whitespace diagnostics; exit 1 denotes the file difference | 1 |

**Final-byte rule:** this pack contains its own evidence and was edited after the static/test runs. Whitespace checks must be rerun after the final edit. The four whitespace commands above and the document audit below were repeated after this evidence text was added; any subsequent edit requires another final-byte run. The t322 results without blob hashes cannot establish the current bytes.

Exact read-only document-audit command (exit **0**, empty stderr):

```sh
python3 - <<'PY'
from pathlib import Path
import re
import subprocess

base = "cde62c66bdf00a9f64aa47e0579e1f3c152576f0"
pack_path = "docs/phase3/PR3-16-execution-pack-r2.md"
record_path = "docs/phase3/PR3-16-owner-answers-record.md"
adr_path = "docs/architecture/adr/ADR-0026-pr3-16-experiment-search-core.md"
allowed = sorted([pack_path, record_path, adr_path])

def git(*args):
    return subprocess.check_output(["git", *args], text=True)

assert git("rev-parse", "HEAD").strip() == base
record = Path(record_path).read_text()
original = git("show", f"{base}:{record_path}")
rows = r"^\| [DQ]\d \|.*$"
paragraphs = r"^\*\*Proposed answer — INFERRED:\*\*.*$"
for label, pattern in [("Answer rows", rows), ("Recommendation paragraphs", paragraphs)]:
    before = re.findall(pattern, original, re.M)
    after = re.findall(pattern, record, re.M)
    assert len(before) == len(after) == 13 and before == after, label
    print(f"{label}: 13 unchanged")

pack = Path(pack_path).read_text()
original_pack = git("show", f"{base}:{pack_path}")
def answers(text):
    return text.split("### 1.2 ", 1)[1].split("### 1.3 ", 1)[0]
assert answers(pack) == answers(original_pack)
print("Pack section 1.2: unchanged")

nodes = [
    ("S1", "tests/integration/phase3/test_pr3_16_schema.py::test_no_strategy_column"),
    ("S5", "tests/unit/phase3/test_experiment_search.py::test_duplicate_id_and_link_constraints_enforced"),
    ("S7", "tests/architecture/test_pr3_16_boundaries.py::test_no_api_or_cli_routes_added"),
    ("S8", "tests/integration/phase3/test_pr3_16_application.py::test_terminal_ancestor_blocks_child_in_database"),
    ("S8", "tests/integration/phase3/test_pr3_16_application.py::test_unfrozen_or_wrong_version_reference_denied"),
]
for step, node in nodes:
    section = pack.split(f"### {step} — ", 1)[1]
    section = re.split(r"\n(?:### S\d|## 4\.)", section, maxsplit=1)[0]
    blocks = re.findall(r"```sh\n(.*?)\n```", section, re.S)
    assert any(node in block.split() for block in blocks), node
print("Previously omitted nodes in owning-step shell blocks: 5/5")

appendix = pack.split("\n## Appendix S — ", 1)[1]
excerpts = re.findall(r"`([^\n`]+):(\d+)–(\d+)`:\n\n```text\n(.*?)\n```", appendix, re.S)
assert len(excerpts) == 3
for path, first, last, quote in excerpts:
    lines = Path(path).read_text().splitlines()
    assert quote == "\n".join(lines[int(first) - 1:int(last)]), path
print("Appendix S exact excerpts: 3/3")

assert not Path("docs/phase3/PR3-16-execution-pack.md").exists()
print("r1 artifact: absent")
assert sorted(git("diff", "--name-only", base).splitlines()) == allowed
assert git("ls-files", "--others", "--exclude-standard") == ""
assert all("accepted".upper() not in Path(path).read_text() for path in allowed)
assert "Status: PROPOSED — not accepted. Owner acceptance pending." in Path(adr_path).read_text()
print("Tracked diff: exactly 3 permitted paths; untracked nonignored files: 0")
print("ADR status: PROPOSED; prohibited uppercase token: absent")
PY
```

Observed stdout:

```text
Answer rows: 13 unchanged
Recommendation paragraphs: 13 unchanged
Pack section 1.2: unchanged
Previously omitted nodes in owning-step shell blocks: 5/5
Appendix S exact excerpts: 3/3
r1 artifact: absent
Tracked diff: exactly 3 permitted paths; untracked nonignored files: 0
ADR status: PROPOSED; prohibited uppercase token: absent
```

`git diff --name-only HEAD` (exit **0**, empty stderr) returned:

```text
docs/architecture/adr/ADR-0026-pr3-16-experiment-search-core.md
docs/phase3/PR3-16-execution-pack-r2.md
docs/phase3/PR3-16-owner-answers-record.md
```

`git status --porcelain` (exit **0**, empty stderr) returned:

```text
 M docs/architecture/adr/ADR-0026-pr3-16-experiment-search-core.md
 M docs/phase3/PR3-16-execution-pack-r2.md
 M docs/phase3/PR3-16-owner-answers-record.md
```

PostgreSQL/integration/migration behavior suites: **NOT RUN**, zero suites invoked because only documentation changed and no database behavior is touched. `alembic heads` inspected the source graph only. Proposed search nodes remain **NOT RUN**. The whole suite was **NOT RUN** by this author; the external loop's output is pending and **UNVERIFIED**.

## 6. Owner answers recorded and remaining steps

**Owner decisions, 2026-10-26 (approved as recommended):**
- A1 ADR-0026 accepted. A2 pack r2 frozen as the answers below. A3 G0-X granted for the freeze-inventory step (F1) only; S1 starts only after F1 is reviewed. A4 push and PR approved (pack PR #19). A5 flake fix approved (PR #20).
- D1 (B6): the atomic amendment is unconditional before activation (draft line 44).
- Q2 (B7): strategy material omitted with explicit owner-approved staging.
- D5 (B11): wider spec-material staging is not approved; it stays open.
- Q3 (B8): a trusted producer is a registered consumer capability that calls the TaskSafetyService reservation path. TrustedFakeConsumer is test-only. No production producer exists, so production node admission is denied until the amendment in D1 is reviewed.
- Q4 (B9): a Run is already-existing iff its created_at (database transaction timestamp) is strictly earlier than the closure event's transaction timestamp, read in one snapshot. Equal or undeterminable means deny.
- Q6 (B10): initial read bounds equal the existing budget caps in safety_contracts.py BudgetSpec (nodes 10, depth 3, parallel branches 1). They are measured and revised at S8. No other numbers are introduced.

**Freeze status:** FROZEN r2 with the decisions above. Exact inventory (Q1), literal vectors (Q2) and the live integration head (Q8) are generated in step F1 from the live repository and must pass review before S1.

**Owner answers (2026-10-26), in the accepted draft wording (record file).** These are answers, not open choices. Only the items marked OPEN below are still open.

- D1/Q3: conservative committed-reservation proof or deny for this storage slice. Draft line 44: "Make atomic admission a separately reviewed amendment before activation." Draft line 142: require the separately reviewed atomic amendment when no trusted producer can satisfy the proof. Whether the amendment is unconditional or conditional is for owner confirmation at freeze. Trusted producer identity is OPEN.
- D2: limited append-only lifecycle.
- D3: actor-attributed planning with execution disabled; no AgentVersion/availability prerequisite for this planning-only slice.
- D4: multiple distinct Runs per node, and explicit reuse as lineage. Same-project links; node/Run ExperimentSpec equality when the node names a version; a repeated fresh link fails and only the original receipt replays.
- D5: typed optional exact references with bounded reasons. Saved owning hash present iff its reference is present, reverified on admission and read. Scoring structures deferred to PR3-17 (draft D5, lines 91–103). Wider spec-material staging is not an accepted answer and stays open.
- Q1: a complete reviewed inventory is required before admission. RESTRICT FKs; one root; at most one terminal event per node and per session. Exact names, types and bodies are OPEN until the freeze step.
- Q2: strategy material omitted for this slice, conditional on explicit owner-approved staging (draft line 128); material version 1; NFC text and lowercase UUIDs. Literal vector bytes are OPEN.
- Q3: see D1/Q3 above.
- Q4: closure-time cutoff for post-close links; deny ambiguous cases; fresh repeated or conflicting terminal commands are rejected without effects; original-receipt replay is kept; current write authority applies to new reconciliation. The durable proof of already-existing work is OPEN.
- Q5: structural duplicate constraints now. Accepted restriction: no inferred root/node equality, inheritance or Hypothesis/ExperimentSpec relationship beyond owning-domain rules. Semantic duplicate detection is staged; the Phase 3 duplicate-branch obligation stays OPEN.
- Q6: whole-tree bounded reads; order by event sequence and Run-link ID; NOT_FOUND for entitled absent targets; referential-integrity failure for corrupt ancestry; provenance-closure failure for saved-hash contradictions, with sanitized envelopes. Separate node, depth, event and link bounds are required before implementation, and history is not silently truncated (draft line 184). Numeric values are OPEN. Whole-tree reads are the draft recommendation; pagination is not chosen.
- Q7: actor-only identity proof; no additional AgentVersion validation by implication. The exact lock sequence still needs its freeze text.
- Q8: Application-only scope, conditional `0081_experiment_search_core`. The integration head and file list are OPEN.

**Still required before any implementation can be authorized, in this order:**

1. Freeze inventory (Q1, Q2, Q6, Q8): exact names, types, bodies, vectors, bounds and the live integration head, generated from the live repository. Admission depends on this.
2. Trusted producer/evaluator identity (Q3) and the durable already-existing-work proof (Q4), defined and reviewed before freeze.
3. Explicit owner staging approval for omitting strategy material (Q2, draft line 128).
4. Owner confirmation whether the atomic amendment is unconditional or conditional (D1, draft lines 44 and 142).
5. Review the PROPOSED ADR-0026 draft and obtain admission of the four tables (G0-A), after item 1. The draft supplies no admission.
6. Before freeze: disposition both earlier independent reviews (RA, RB), define every MISSING assertion in §1.4 and add its exact node to its owning step's command block. The five previously named missing nodes are now selected in S1/S5/S7/S8, but their assertion definitions and execution remain MISSING / NOT RUN. Rewrite answer-dependent tests and authorization wording without changing accepted answers.
7. Independent review of r2, which is in progress.
8. Explicit owner approval of the freeze. Implementation then needs a separate authorization (G0-X).

Status: FROZEN r2 (owner approved 2026-10-26). F1 pending. Owner answers recorded in §1.2 and §6. Awaiting the items above. No implementation authorized.

## Appendix S — Repository source excerpts and provenance limits

The external P/R filesystem dependencies have been removed. R now names the tracked local review. P is unavailable in this repository; its original lines remain **UNVERIFIED** and are not represented as verbatim quotations. The following are exact excerpts from accessible repository sources, with original line numbers. The review's account of P is secondary evidence only. This pack's current G0 requirements are stated explicitly in §1.1; owner answers are preserved in the companion record, not inferred from a plan or review.

`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:12–14`:

```text
Read §§3–5 for the proposed interface, tables and transaction recipe. Owner
choices in §8 must be resolved in an ADR and a reviewed execution pack before
implementation. Approval of this draft alone does not enable execution.
```

`docs/phase3/PR3-16-plan-review.md:93–104`:

```text
Open questions are clearly separated from requirements: plan lines 71–95 label
all D1–D5 and Q1–Q8 **OPEN**, identify inferred questions, and forbid filling gaps
from the plan. G0 at line 509 requires their resolution, ADR/schema admission, a
reviewed execution pack and separate implementation authorization. This follows
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:12` and its decision table
at line 317. No owner decision was resolved by this review.

The plan **only plans implementation**. Lines 35–38, 158–164, 208–211 and
502–505 explicitly withhold implementation authority. Future command listings
and proposed gates are not executed evidence. PASS here means no P0/P1 in this
documentation review, not contract approval, PR acceptance or permission to
implement PR3-16/17.
```

`docs/phase3/PR3-16-plan-review.md:63–73`:

```text
Details added by the plan, rather than frozen by the draft, are explicitly
identified and remain proposals or owner questions:

- Module/fixture/test filenames and node IDs, S1–S8 sequencing, two-round
  estimates, common gates and evidence organization (plan 24–29, 174–211).
- Full constraint/helper/index inventory, exact DTO/vector/error precedence,
  strategy pinning, and any atomic accounting amendment (plan 84–86).
- Historical reconciliation cutoff proof, duplicate-branch semantics and
  consistency between optional version references (plan 87–88).
- Pagination/size bounds, corrupt-ancestry handling, AgentVersion lock/proof
  composition, revision assignment and transport/release inventory (plan 89–91).
```

These quotations preserve the historical review's wording, including its historical OPEN/PASS statements. They do not override the later accepted owner answers or assert a current review PASS. Original draft-to-answer quotation fidelity is UNVERIFIED in t322 because the external answers draft was not accessed; original quotation fidelity remains UNVERIFIED in t324 as well. Preservation of the repository record against t324's explicit Git baseline is checked in §5.2.
