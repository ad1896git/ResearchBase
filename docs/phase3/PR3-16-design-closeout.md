# PR3-16 design closeout — t327

Documentation-only disposition of the twelve rows in
`docs/phase3/PR3-16-freeze-inventory.md:281` (the OPEN-items table at lines
287–298). This document does not reissue F1, freeze a design, admit schema, or
authorize S1. Base `pr316-s1` and inspected HEAD both resolve to
`01b5b63c9962ba120175bdee55ff1440ee8fc100`.

**Whole-item counts: RESOLVED 0; OWNER 12; NOT RUN 0.** Each inventory row has
at least one required decision that the available sources do not determine.
Established facts within a row are retained below but do not resolve the whole
row. Check execution is reported separately: every proposed PR3-16 check is
MISSING / NOT RUN, not implementation evidence.

The explicit owner decisions in
`docs/phase3/PR3-16-execution-pack-r2.md:497` through line 506 take precedence
over the preserved older OPEN wording in that pack and ADR-0026, as specified
by `docs/phase3/PR3-16-freeze-inventory.md:11`. ADR-0026 remains accepted
(`docs/architecture/adr/ADR-0026-pr3-16-experiment-search-core.md:3`). In
particular, the unconditional D1 amendment, approved strategy omission, trusted
producer definition, strict transaction-timestamp cutoff, and initial 10/3/1
bounds are answers, not choices reopened here. No frozen owner answer changes.

## Owner decision needed

### 1. Exact four-table DDL — OWNER

**Established design.** The four table names and field roles are specified at
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:152` through line 155.
All four reject even no-op UPDATE/DELETE; concrete same-project/task/session
RESTRICT references, four optional scientific-reference/saved-hash pairs, and
the uniqueness/index obligations remain required
(`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:157`, `:167`). These
requirements do not supply the complete declarations.

**Question for the project owner and architecture review:** what exact column
spellings, storage declarations, defaults, UUID acceptance rules, hash formats,
event-reason nullability, constraint/support-key/index names and SQL are to be
approved? F1 explicitly leaves these undetermined
(`docs/phase3/PR3-16-freeze-inventory.md:57`, `:127`, `:169`). An analogous
migration is evidence of an existing implementation, not a selection of new
search identifiers or declarations.

**Options:** commission and review the complete Q1 declarations for the existing
four-table proposal; or defer schema admission while that design is unavailable.
**Recommendation:** obtain the complete Q1 design before reissuing F1. Keep S1
blocked meanwhile; selecting conventional names or types here would invent the
missing contract. This follows the inventory-before-admission requirement at
`docs/phase3/PR3-16-execution-pack-r2.md:50` and `:506`.

**Check:** `tests/integration/phase3/test_pr3_16_schema.py::test_frozen_columns_keys_indexes_and_no_json_or_cascade`
is the proposed catalog comparison; it must fail for a mismatch in any approved
declaration, FK/index or deletion rule. **MISSING / NOT RUN**; until the exact
inventory exists, the complete expected catalog is also MISSING
(`docs/phase3/PR3-16-execution-pack-r2.md:155`).

### 2. Guard bodies and mutation manifest — OWNER

**Established design.** Fresh commands require exactly their declared effects,
and ordinary-role SQL must enforce scope, immutable history, acyclicity and
terminal predicates across flushes
(`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:174`). F1 identifies
`pr301_receipt_complete()` as a required extension seam, distinguishes conditional
changes from preservation, and includes the 0081 agent-intent guards and privilege
restrictions (`docs/phase3/PR3-16-freeze-inventory.md:201`, `:202`, `:214`, `:220`).

**Question for the project owner and architecture review:** which exact new and
replacement functions/triggers, attachments, timing and privilege/catalog deltas
implement those obligations without weakening the accepted 0081 baseline?
Neither a count nor a complete mutation manifest is supplied
(`docs/phase3/PR3-16-freeze-inventory.md:222`).

**Options:** review complete SQL bodies plus an explicit changed/unchanged-object
manifest; or defer dependent DDL until that package is available.
**Recommendation:** require that package before F1 review. Preserve the existing
success and rejection cases and attachment attributes, not merely function names;
F1 already requires this preservation protocol
(`docs/phase3/PR3-16-freeze-inventory.md:224`).

**Checks:** `tests/integration/phase3/test_pr3_16_schema.py::test_all_frozen_sql_definitions_compile_on_pg18`
and `tests/integration/phase3/test_pr3_16_guards.py::test_immutable_rows_and_receipt_effects_across_flushes`
are **MISSING / NOT RUN**. Compilation must reject invalid definitions; behavioral
checks must reject missing/extra effects, committed-receipt reuse, no-op mutation
and weakened old guards. Exact per-object assertions, including privileges,
remain MISSING (`docs/phase3/PR3-16-freeze-inventory.md:220`, `:224`).

### 3. Events/receipt shape — OWNER

**Established design.** Each fresh success increments task revision once and
creates one task receipt/event/result link. Additional search effects are:
create → session/event; append → node/event; link → relation/event;
failure/prune/close → event. Replay adds no effects
(`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:137`, `:174`). Created
result identities are recovered through concrete receipt FKs
(`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:127`). Search sequence is
unique per session; this does not establish equality with task-event sequence
(`docs/phase3/PR3-16-freeze-inventory.md:228`).

**Question for the project owner and architecture review:** which search/task
event literals, sequence type/start/allocation/gap policy, per-kind node/link/reason
shape, and result-pointer names/types/keys/cardinality/NULL/order/recovery layout
are approved? These are explicitly absent at
`docs/phase3/PR3-16-freeze-inventory.md:228`, `:234` through `:241`.

**Options:** specify a complete Q1/Q2 event and receipt contract within the existing
receipt family; or leave event/result implementation blocked.
**Recommendation:** settle the contract together with items 1 and 4, so DDL,
request vectors and replay cannot choose incompatible shapes. Do not infer event
names from status literals or introduce another receipt table
(`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:174`).

**Check:** `tests/integration/phase3/test_pr3_16_guards.py::test_immutable_rows_and_receipt_effects_across_flushes`
is **MISSING / NOT RUN**. Separate exact assertions for sequence allocation,
per-kind shape, result pointers and recovery remain **MISSING**
(`docs/phase3/PR3-16-freeze-inventory.md:228`, `:241`).

### 4. Command envelopes and literal vectors — OWNER

**Established design.** The six commands and argument roles are at
`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:95` through line 102.
Requests are closed and typed; stable caller session/node IDs are UUIDv7; reasons
are NFC, nonblank and 1–8192 characters. Complete normalized command material uses
version 1, lowercase UUID text and the existing canonical JSON/hash helpers,
including defaults/NULLs and authenticated actor, excluding generated values and
current projections (`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:87`,
`:130`). Strategy omission is approved
(`docs/phase3/PR3-16-execution-pack-r2.md:500`).

**Question for the project owner and contract review:** what exact field names,
types, defaults, NULL handling, normalization corner cases, remaining UUID rules,
independent literal inputs/bytes/digests/results and per-command multi-failure
precedence are approved? No complete search vector exists in the sources
(`docs/phase3/PR3-16-freeze-inventory.md:249`, `:253`, `:260`, `:279`).

**Options:** commission independent Q2 envelopes/vectors after item 3 is settled;
or keep command implementation blocked until they are specified.
**Recommendation:** obtain that independent contract first; do not manufacture
fixture literals or label existing task/gateway vectors as search vectors.
Preserve the settled entitlement → committed receipt/replay → fresh-write order;
the error table is not a total precedence order
(`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:137`,
`docs/phase3/PR3-16-freeze-inventory.md:279`).

**Checks:** `tests/unit/phase3/test_experiment_search_contracts.py::test_closed_envelopes_and_fixed_vectors`
and `tests/unit/phase3/test_experiment_search_contracts.py::test_nfc_uuid_defaults_and_reason_bounds`
are **MISSING / NOT RUN**. Complete multi-failure precedence assertions are
**MISSING** (`docs/phase3/PR3-16-execution-pack-r2.md:185`,
`docs/phase3/PR3-16-freeze-inventory.md:279`).

### 5. Remaining lifecycle matrix — OWNER

**Established design.** ACTIVE sessions close once as CANCELLED, EXHAUSTED or
TERMINATED_BUDGET; PROPOSED nodes become FAILED or PRUNED. Terminal ancestors
block new descendants, and session closure blocks node creation/failure/pruning
(`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:102`). Fresh repeated or
conflicting terminal commands fail without effects; original receipt replay is
retained (`docs/phase3/PR3-16-execution-pack-r2.md:518`). Post-close reconciliation
requires current write authority and a Run whose database transaction `created_at`
is strictly earlier than the closure event's transaction timestamp, read in one
snapshot; equal or undeterminable means deny
(`docs/phase3/PR3-16-execution-pack-r2.md:503`, `:518`).

**Question for the project owner and contract review:** how are all remaining
command × task/session/node/ancestor combinations disposed, especially
reconciliation involving terminal nodes/tasks, and how is the specified closure
transaction timestamp persisted and checked? The sources do not provide the
complete matrix or timestamp implementation
(`docs/phase3/PR3-16-freeze-inventory.md:243`, `:257`).

**Options:** complete and review Q4's matrix/timestamp contract within the frozen
lifecycle; or defer the dependent commands. **Recommendation:** complete Q4 before
implementation. Neither a universal terminal-state denial nor a universal
reconciliation allowance follows from the specified cases. Keep the strict cutoff
and repeated-terminal decisions unchanged.

**Checks:** `tests/integration/phase3/test_pr3_16_application.py::test_terminal_ancestor_blocks_child_in_database`
and `tests/unit/phase3/test_experiment_search.py::test_closure_blocks_mutations_and_allows_frozen_reconciliation`
are **MISSING / NOT RUN**. Full matrix, earlier/equal/undeterminable cutoff and
fresh repeated/conflicting terminal assertions remain **MISSING**
(`docs/phase3/PR3-16-execution-pack-r2.md:85`, `:106`, `:107`).

### 6. Remaining read bounds/envelopes — OWNER

**Established design.** Initial node/depth/parallel-branch bounds are **10/3/1**,
to be measured and revised at S8
(`docs/phase3/PR3-16-execution-pack-r2.md:504`). Whole-tree reads use one snapshot,
nodes in depth/ID order, lineage root-to-node, events by sequence and Run links by
link ID. Run status/seal are labeled current projections. Entitled missing targets,
corrupt ancestry and saved-hash contradictions retain the specified NOT_FOUND,
REFERENTIAL_INTEGRITY_ERROR and PROVENANCE_CLOSURE_VIOLATION classes with sanitized
envelopes (`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:119`, `:261`,
`docs/phase3/PR3-16-execution-pack-r2.md:520`).

**Question for the project owner:** what are the separate event/link limits,
overflow behavior, complete result envelopes, and meaning of parallel branches
for these reads? The 10/3/1 answer supplies none of those additional decisions
(`docs/phase3/PR3-16-freeze-inventory.md:256`, `:292`).

**Options:** define the remaining Q6 details while retaining whole-tree reads and
the approved bounds; or defer dependent reads pending that decision.
**Recommendation:** supply those details before F1 review, then measure at S8.
Do not import another subsystem's limit, turn parallel branches into a root/link
limit, silently truncate history, or choose pagination; those are not the frozen
answer (`docs/architecture/adr/ADR-0026-pr3-16-experiment-search-core.md:42`).

**Check:** `tests/integration/phase3/test_pr3_16_application.py::test_recheck_cadence_and_query_work_at_frozen_bounds`
is **MISSING / NOT RUN**. Exact parallel-read and event/link overflow assertions
remain **MISSING** (`docs/phase3/PR3-16-freeze-inventory.md:292`).

### 7. Exact actor-only lock composition — OWNER

**Established design.** The exact sorted 18-table SHARE is first, followed by
project/command/task coordination, required identity keys before row locks,
task/step rows, ordered safety/lineage/scientific reads and fresh validation after
waits, writes and forced constraints. Own uncommitted effects cannot replay
(`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:215`,
`docs/phase3/PR3-16-execution-pack-r2.md:56`). Actor-only verified Human/Agent
planning does not require AgentVersion or availability
(`docs/architecture/adr/ADR-0026-pr3-16-experiment-search-core.md:34`, `:43`).

**Repository evidence and remaining question:** the existing prefix and task-row
callbacks are explicit at
`src/researchbase/persistence/task_safety_repository.py:55` and `:70`.
The gateway composes actor/version keys, availability locking and broader safety
locking (`src/researchbase/persistence/capability_gateway_repository.py:104`,
`:115`, `:121`); `lock_safety` locks checkpoints
(`src/researchbase/persistence/task_safety_repository.py:86`). Those are not a
complete actor-only search recipe. Which exact per-caller identity-key/row
sequence and post-write callback composition will the project owner and
architecture review approve? Q7 expressly leaves this text pending
(`docs/phase3/PR3-16-execution-pack-r2.md:521`).

**Options:** review an explicit per-caller composition using the existing
coordination mechanisms; or defer S2 until it is supplied.
**Recommendation:** require that composition before S2. Copying the gateway helper
would add prerequisites/locks that the frozen planning contract does not permit;
omitting coordination because no AgentVersion is required is not justified either.

**Checks:** `tests/unit/phase3/test_experiment_search_repository.py::test_first_statement_and_complete_lock_order`
and `tests/unit/phase3/test_experiment_search_repository.py::test_every_blocking_stage_calls_fresh_validation`
are **MISSING / NOT RUN**. The exact per-caller expected trace is MISSING
(`docs/phase3/PR3-16-execution-pack-r2.md:171`).

### 8. D1 amendment delivery/evaluator details — OWNER

**Established design.** The atomic node-aware amendment is unconditional before
activation. A trusted producer is a registered consumer capability calling the
TaskSafetyService reservation path; TrustedFakeConsumer is test-only. No
production producer exists, so production node admission remains denied until
the D1 amendment is reviewed
(`docs/phase3/PR3-16-execution-pack-r2.md:499`, `:502`). The storage slice retains
committed same-task/active-budget proof or denial: `tree_nodes=1`, operation
identity equal to node ID, unused/nonfinal reservation and exact step/search depth.
Stopped admission is denied; gaps and UNKNOWN outcomes retain charges. No nested
reservation command, invented refund or PR3-16 settlement is permitted
(`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:184`).

**Question for the project owner and architecture review:** when should the
separate atomic amendment be pursued, and what producer/evaluator, full resource
vector, depth mapping, stop semantics, atomic receipt effects and settlement
ownership will its own contract and ADR approve? The required details are named
but not supplied at `docs/phase3/PR3-16-execution-pack-r2.md:52` and
`docs/architecture/adr/ADR-0026-pr3-16-experiment-search-core.md:39`.

**Options:** pursue a separately authorized contract and ADR next, before any
activation work; or defer that design and retain denied production node admission.
**Recommendation:** pursue the separate design now as the next owner-authorized
task, because the absent production producer blocks useful admission. It needs
its **own contract and ADR**, not an implicit extension of ADR-0026 or S1. This
recommendation schedules no implementation, assigns no ADR identifier, and does
not make the amendment conditional. Do not copy the gateway fake resource vector
(`docs/phase3/PR3-16-execution-pack-r2.md:45`).

**Check:** `tests/integration/phase3/test_pr3_16_budget.py::test_cross_session_caps_depth_gaps_and_terminal_no_refund`
is **MISSING / NOT RUN** for conservative storage rules. The atomic amendment's
own assertions are **MISSING**, to be defined in its separate contract; that
storage test cannot establish atomic admission
(`docs/phase3/PR3-16-freeze-inventory.md:294`).

### 9. Wider specification-material staging — OWNER

**Established design.** Wider staging is **not approved** and stays open
(`docs/phase3/PR3-16-execution-pack-r2.md:501`). Approved strategy omission is
distinct (`:500`). Typed optional exact references with paired saved hashes remain
required, and scoring structures remain deferred to PR3-17 under the recorded
answer (`docs/phase3/PR3-16-execution-pack-r2.md:514`). The broader Phase 3 model
includes session objective/scoring material and node score/execution material
(`docs/architecture/06_Phase3_Development_Specification_v1.1_Harness_Integrated.md:1181`,
`:1221`). Listing those fields does not authorize their omission or implementation.

**Question for the project owner and architecture review:** is any additional
specification material to be staged beyond the already accepted answers, and, if
so, exactly which obligations and later contract would own it?

**Options:** retain the not-approved disposition and reconcile each remaining
specification obligation before dependent implementation; or separately review an
explicitly delimited wider staging request. **Recommendation: not approved for
any D5 wider specification-material staging.** The sources give no approved wider
boundary or replacement contract; a broad omission would silently change scope.
This is a recommendation, not a new owner decision, and does not undo the already
accepted strategy/scoring/lifecycle/execution staging.

**Check: MISSING / NOT RUN.** Dependent S3/S8 assertions require the owner's exact
disposition (`docs/phase3/PR3-16-freeze-inventory.md:295`). No test name can grant
staging approval.

### 10. Semantic duplicate obligation disposition — OWNER

**Established design.** Structural duplicates are constrained now; semantic
detection is staged, while the Phase 3 duplicate-branch obligation stays open.
There is no inferred root/node equality, inheritance or Hypothesis/ExperimentSpec
relationship beyond owning-domain rules
(`docs/phase3/PR3-16-execution-pack-r2.md:519`). The outstanding obligation is
explicit in `docs/architecture/06_Phase3_Development_Specification_v1.1_Harness_Integrated.md:2327`.

**Question for the project owner and architecture review:** which later reviewed
contract owns semantic duplicate detection, with what definition and acceptance
evidence, and how will that obligation be tracked through release?

**Options:** approve an explicit later-contract disposition while retaining the
structural-only current slice; or leave the disposition open and withhold claims
of duplicate-branch conformance. **Recommendation:** obtain explicit later-contract
ownership and acceptance criteria. Do not select a fingerprint algorithm,
reference-pair relationship or PR assignment that the sources do not specify
(`docs/architecture/adr/ADR-0026-pr3-16-experiment-search-core.md:41`, `:49`).

**Check: MISSING / NOT RUN** for semantic duplicate detection.
`tests/unit/phase3/test_experiment_search.py::test_duplicate_id_and_link_constraints_enforced`
is itself **MISSING / NOT RUN** and is only the proposed structural check, not a
substitute for the semantic obligation
(`docs/phase3/PR3-16-execution-pack-r2.md:108`, `:110`).

### 11. Exact revision/release maintenance — OWNER

**Established current evidence.** Unlike F1's historical checkout, this base
contains `migrations/versions/0081_agent_execution_intents.py`; lines 7–8 declare
`0081_agent_execution_intents` after `0080_capability_gateway`. The source graph
check is reported below. Thus the conditional `0081_experiment_search_core` slot
cannot be assigned on this base. The draft requires integration-head assignment
and preservation of accepted ancestors
(`docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:34`,
`docs/phase3/PR3-16-execution-pack-r2.md:300`).

**Question for the project owner/integration owner and architecture review:** what
replacement revision/file identifier and complete release-maintenance/catalog
delta should be approved after rechecking the integration ref? No replacement is
assigned at `docs/phase3/PR3-16-freeze-inventory.md:51`. Current source evidence
does not supply that assignment or settle later integration changes.

**Options:** assign the revision and review the exact maintenance manifest during
a separately authorized F1 reissue; or leave the slot unassigned and S1 blocked.
**Recommendation:** revalidate the integration graph and approve the assignment
with Q1's completed catalog delta. Do not infer a next number. Use Appendix H as
the maintenance checklist, updating current-head assertions only and preserving
explicit historical fixture/byte pins
(`docs/phase3/PR3-16-execution-pack-r2.md:302` through line 317). This closeout
creates no ref. The current direct `git show main:migrations/versions/0081_agent_execution_intents.py`
also exits 128 with `fatal: invalid object name 'main'.`; the requested local-main
read remains unavailable. The checked-out migration and source graph are the
current evidence, not a successful local-main verification.

**Checks:** `tests/integration/phase3/test_pr3_16_migration.py::test_forward_only_migration_and_single_head`
is **MISSING / NOT RUN**. The existing source-head and CI-head checks below do not
prove an upgrade or the future catalog delta. Exact maintenance-delta assertions
remain **MISSING** (`docs/phase3/PR3-16-freeze-inventory.md:297`).

### 12. Acceptance assertions and review — OWNER

**Established design.** MISSING assertion definitions and exact node/step-command
mappings block freeze; proposed tests and old counts establish no search behavior
(`docs/phase3/PR3-16-execution-pack-r2.md:80`, `:125`). The acceptance gaps cover
verified Human/Agent admission and unverified denial; positive actor-only Agent
planning without AgentVersion/availability; same-project/spec-matching Run links;
reference/hash pairing and admission/read revalidation; sequence and terminal
uniqueness; strategy omission; cutoff/repeated terminal requests; independent
references and structural duplicates; read errors/bounds; and Application-only
scope (`docs/phase3/PR3-16-execution-pack-r2.md:85` through line 117).

**Question for the project owner and independent reviewers:** after the preceding
design decisions are supplied, are all assertion definitions/node mappings,
earlier RA/RB review dispositions, F1 review and remaining prerequisites adequate
for a separate freeze and implementation authorization? This document cannot
supply those approvals or a review result
(`docs/phase3/PR3-16-execution-pack-r2.md:531` through line 535).

**Options:** commission the missing design/assertion package and independent review
before seeking separate authorization; or retain the current blocked state.
**Recommendation:** complete that package and review first. Do not convert the
frozen r2 approval or accepted ADR into F1 acceptance/S1 authority; the explicit
owner answer limits G0-X to F1 and requires F1 review before S1
(`docs/phase3/PR3-16-execution-pack-r2.md:498`).

**Check: MISSING / NOT RUN** for complete assertion-to-node mapping and independent
F1 acceptance. All future nodes cited above remain absent. Existing regressions
can detect regressions in accepted seams, but cannot decide design, close reviews
or authorize implementation (`docs/phase3/PR3-16-freeze-inventory.md:23`, `:298`).

## Verification of this closeout

Measured on 2026-10-26 against the base above plus this new document, using
CPython 3.12.15 and pytest 8.4.2 on Darwin. Every `uv` command below was prefixed
with `UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"`. Commands are focused existing
regressions; none implements or tests the missing search contract.

| Exact command (with the stated prefix for `uv`) | Observed output/counts | Exit |
| --- | --- | --- |
| `uv sync --locked --group dev` | Resolved 38 packages; prepared and installed 34; dependency files unchanged | 0 |
| `uv run ruff check .` | `All checks passed!` | 0 |
| `uv run ruff format --check .` | `948 files already formatted` | 0 |
| `uv run pyright` | `0 errors, 0 warnings, 0 informations`; separate available-version notice v1.1.411 → v1.1.414 | 0 |
| `uv run alembic heads` | `0081_agent_execution_intents (head)`; source graph only | 0 |
| `uv run pytest -o addopts='' -ra tests/unit/phase3 tests/architecture tests/unit/architecture tests/unit/test_ci_migration_head.py` | Collected 1437; **1437 passed**, 0 failed, 0 errors, 0 skipped; 51 Alembic `path_separator` deprecation warnings; 30.57s | 0 |
| `git diff --exit-code pr316-s1 HEAD` | No output; checkout commit equals the requested base | 0 |
| `git show main:migrations/versions/0081_agent_execution_intents.py` | `fatal: invalid object name 'main'.`; unavailable ref, not verification | 128 |
| `git diff --check` | No output | 0 |
| `git diff --no-index --check -- /dev/null docs/phase3/PR3-16-design-closeout.md` | No whitespace diagnostics; exit 1 reports the added-file difference from `/dev/null`, not a zero-exit check | 1 |

The selected Phase 3 units cover the accepted task, safety, identity, execution
intent and gateway seams; the architecture selections cover existing layering
and migration constraints; the CI-head unit checks the current source head.
Static tools report no pytest counts. A source-reference audit found 71 explicit
file:line citations with existing files and valid line numbers, twelve ordered
OWNER dispositions, and eight distinct cited future PR3-16 test files, all absent.
That audit checks citation locations and coverage, not correctness of future code.

**PostgreSQL suites: NOT RUN (0 invoked).** This document changes no database
behavior or PostgreSQL suite; there is no PR3-16 migration/test implementation to
exercise. Source-graph inspection is not PostgreSQL compilation, upgrade or guard
evidence. **Whole suite: NOT RUN** by this task, as requested; the external loop's
subsequent output is its evidence and is not available here. Independent F1 review,
freeze acceptance and implementation authorization remain **NOT RUN / pending**.

Only `docs/phase3/PR3-16-design-closeout.md` is added to the deliverable; all existing
tracked files are unchanged. No code, migration, frozen answer, branch, commit or
push is changed by this task. S1 remains blocked by the OWNER dispositions above.
