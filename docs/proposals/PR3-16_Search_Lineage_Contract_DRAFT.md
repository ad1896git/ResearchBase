# PR3-16 Search Session / Node Lineage Contract

Status: DRAFT — awaiting owner approval; not authorized for implementation

## Start here

PR3-16 stores a search tree and its exact links to ordinary Runs. A branch that
fails or is pruned remains readable, including branches that never produced a
Run. This is lineage storage, not a search engine. All requirements below describe
future work; this change delivers only this document.

Read §§3–5 for the proposed interface, tables and transaction recipe. Owner
choices in §8 must be resolved in an ADR and a reviewed execution pack before
implementation. Approval of this draft alone does not enable execution.

**Identifier convention:** every proposed table, column, constraint, event literal,
command, query, DTO and request/result field below is **new in PR3-16**, including
names borrowed from architecture examples. Explicitly labeled existing names are
verified baseline identifiers. SearchDecisionRecord is **new in PR3-17**, not a
PR3-16 table. No proposed SQL helper, transport path or test filename is implied.

## 1. Authority and delivered baseline

| Source | Binding requirement |
| --- | --- |
| [AGENTS.md](../../AGENTS.md); architecture [01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), [02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), [03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md), [08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md) | Application boundary, typed FKs, complexity budget, immutable history, no scientific cascade deletion; Run remains scientific execution, tree state is workflow lineage. |
| [Phase 3 specification](../architecture/06_Phase3_Development_Specification_v1.1_Harness_Integrated.md), §§29–33, 61, 69, 72, 75.4 | Session/node identity, same-session parent, relational Run IDs, all failed/pruned branches retained. §32 decisions belong to PR3-17. |
| [Harness specification](../harness/09_Harness_Integration_Specification_v1.0.md), §§2, 15, 17, 23 | No direct canonical writes, candidate output is not truth, reproducible attribution, no self-weakening. |
| [Roadmap](PHASE3_Roadmap_DRAFT.md), PR3-16/17 rows and schema justification | Session/node/Run relations retain lineage absent from individual Runs; heuristics and their decision basis are separate PR3-17 work. No provider dependency for PR3-16. |
| [ADR-0021](../architecture/adr/ADR-0021-tdg3-phase3-technology-decisions.md) | Native runtime, bounded task budgets, no branch deletion, owning-PR schemas and serial migrations; product providers are API-based. |
| [ADR-0024](../architecture/adr/ADR-0024-pr3-04-budget-termination-checkpoint.md) | Immutable budget binding, sticky stops, unknown charges retained; continuation uses a new task and approved budget. |
| PR3-01 [contract](PR3-01_ResearchTask_Step_Graph_Contract_DRAFT.md) and [freeze](../phase3/PR3-01-contract-freeze.md); PR3-04 [contract](PR3-04_Budget_Termination_Checkpoint_Contract_DRAFT.md) and [freeze](../phase3/PR3-04-contract-freeze.md); PR3-02-S1 [freeze](../phase3/PR3-02-S1-contract-freeze.md) | Reuse delivered task receipts/revisions/events, exact first-SHARE protocol, current read entitlement before replay, lock-free formal reads. Historical “absent” statements in packs do not override delivered code. |

Existing head is `0079_agent_identity_versions`, after existing
`0077_research_task_graph` and `0078_task_safety_policies`. Proposed migration:
**0080+ (number assigned at integration)**. Verify the sole integration head and
re-parent there; sibling wave-3 drafts do not reserve a revision. No migration is
created here; accepted ancestors must not be edited.

Existing implementation anchors (paths relative to repository root):

| Existing identifiers | Source |
| --- | --- |
| `Run`, `RunStatus`, `inputs_sealed_at`, `experiment_spec_version_id`; `runs`, `run_dataset_inputs`, `run_artifact_inputs` | `src/researchbase/domain/run.py`; `migrations/versions/0008_run_core.py`, `0009_run_input_seal_fix.py` |
| `create_run`, `start_run`, `finish_run`, `get_run`; `SqlAlchemyRunRepository` | `src/researchbase/application/commands.py`; `src/researchbase/persistence/repositories.py` |
| `research_tasks`, `research_task_steps`, `research_task_command_receipts`, `research_task_events`, `research_task_receipt_events`; `CommandResult` | migration 0077; `src/researchbase/agent_runtime/application/contracts.py` |
| `execution_budgets`, `budget_reservations`, `budget_usage_records`, `human_checkpoints`; `reserve_task_budget`, `settle_task_budget`, `get_task_safety` | migration 0078; `src/researchbase/agent_runtime/application/task_safety.py` |
| `agent_versions`, `agent_availability`; no execution table delivered by S1 | migration 0079; `src/researchbase/agent_runtime/application/agent_versions.py` |
| `SHARE_TABLES`, `rb_phase2_lock_project`, existing advisory keys in §5 | `src/researchbase/persistence/research_task_repository.py`; `migrations/versions/0019_phase2_bootstrap_membership.py` |
| `SqlAlchemyUnitOfWork`, `begin_research_task`, `begin_formal_read` | `src/researchbase/persistence/uow.py` |

## 2. Scope and invariants

1. Human and Agent use the same Application → port/UoW → persistence → PostgreSQL
   boundary. Domain code has no ORM, transport, provider or framework dependency.
2. A session belongs to exactly one existing task/project and its active immutable
   budget. A node belongs to one session. A parent belongs to that same session;
   exactly one root is allowed, root depth is zero, child depth is parent plus one.
   Parent and material references never change. Appending only beneath an existing
   parent prevents cycles; direct SQL must enforce the same rule.
3. Each Run link names an existing `runs.id` with a real FK. Session, node, Run and
   optional scientific versions must agree on project. No `target_type + target_id`,
   JSON reference, current/latest lookup or copied Run truth.
4. Runs retain their existing input seal, status machine and terminal immutability.
   Linking a Run does not start, finish, cancel or edit it. Negative results remain
   ordinary scientific results; no search status or score can rewrite them.
5. Failure and pruning append attributable event rows. Never delete a node, detach
   a Run, reparent, reuse an ID or overwrite a reason. A retry is a new node and,
   when actually executed elsewhere, a new Run; the prior attempt remains visible.
6. Session/node status is derived from ordered immutable events, not a second
   mutable truth. Closed sessions and terminal branches never reopen. Historical
   Run links may still be appended after closure to reconcile already-existing
   work; this grants no new spend or execution.
7. No node-count/depth/Run budget copy or reset. All sessions of a task share its
   existing PR3-04 accounting. Failure, pruning and closure never refund charges.
   New sessions cannot bypass a task stop or exhausted cap.

Excluded: selection, expansion policy, scoring/objective policy evaluation,
SearchDecisionRecord (**new in PR3-17**), candidate ranking, winner designation,
Agent execution/promotion, Run creation/execution, workers, cancellation I/O,
providers, new dependencies and Phase 4. No subscription CLI, including Codex or
agy, may be an LLM backend for product features. Any real provider must be
API-based and is outside this roadmap row's scope.

## 3. Commands, queries, DTOs and replay

All names and fields in this section are **new in PR3-16**, except labeled existing
ones. Closed immutable typed requests reject unknown fields. Common mutation
material: project/task/command IDs, expected task revision, normalized arguments
and trusted authenticated context. Reuse existing task `row_version` as CAS;
there is no independent session CAS counter. Caller supplies stable UUIDv7 session
and node IDs; actor, timestamps, event IDs and resulting revision are server-owned.
Use NFC nonblank reasons of 1–8192 characters and exact UUIDs. No arbitrary JSON.

| Command — new in PR3-16 | Arguments and atomic effect |
| --- | --- |
| `create_search_session` | Session ID, optional exact frozen root Hypothesis/ExperimentSpec version IDs. Require a nonterminal task, complete existing policy bundle, no stop and current gates; bind its active budget and append session plus creation event. No root node or execution implied. |
| `append_search_node` | Session/node IDs, existing parent node ID or NULL for root, branch kind, mutation reason, optional exact frozen Hypothesis/ExperimentSpec version IDs, reservation ID. Derive depth; append node plus creation event after §4 budget proof. |
| `link_search_node_run` | Session/node IDs and exact Run ID. Append one immutable relation and event. Run must already exist in the same project; when node has an ExperimentSpec version it must equal the Run's version. Any Run status, including PLANNED/FAILED/CANCELLED, is readable lineage; only a sealed Run establishes frozen execution inputs. |
| `record_search_node_failure` | Session/node IDs and reason. Append failure event; records a branch failure, never invents a Run failure. Existing linked Run outcomes remain separately visible. |
| `prune_search_node` | Session/node IDs and reason. Append pruning event for this branch only. No descendant rewrite or implicit Run cancellation. Explicitly close each descendant if desired. |
| `close_search_session` | Session ID, reason and close kind CANCELLED, EXHAUSTED or TERMINATED_BUDGET. Budget termination requires durable PR3-04 stop evidence. Append closure event; never claim scientific success. |

Proposed branch kinds: NEW_DIRECTION, REFINEMENT, ABLATION, BASELINE, SCALE_UP,
DEBUG, REPLICATION (**new in PR3-16**, normalized from specification §30).
Session projection: ACTIVE until one closure event. Node projection: PROPOSED
until one FAILED or PRUNED event. No READY/RUNNING/EVALUATED/SELECTED transitions
in this slice. An ancestor terminal event blocks new descendants; existing
children and their outcomes remain distinct and visible. Closure blocks node
creation/failure/pruning; reconciliation links remain allowed. D2 covers this
bounded staging of the wider architecture lifecycle.

Existing OWNER/RESEARCHER may mutate; existing OWNER/RESEARCHER/REVIEWER/APPROVER/
VIEWER may read, subject to current project entitlement and archive policy.
Terminal reconciliation is bookkeeping, not authority to change a scientific
record. Current Agent identity verification is required; never attribute an Agent
to a Human. No public caller supplies a trusted-consumer flag or usage truth.

Queries `get_experiment_search_tree`, `get_branch_lineage`, `get_search_budget`
and DTOs `SearchTreeRead`, `BranchLineageRead`, `SearchCommandResult` are **new in
PR3-16**. Tree returns session/budget identity, nodes ordered by depth/ID, exact
parents, ordered events and Run links, including all losers. Lineage returns the
root-to-node path plus that node's links/events. Budget query projects existing
`get_task_safety` data in the same UoW/snapshot; it creates no search balance.
Run status and seal state are labeled current snapshot projections. Unsealed
inputs are explicit; no fabricated historic seal/hash. Empty tree is empty,
never a successful search. Command result includes existing `CommandResult` plus
created session/node/link/event IDs recovered from concrete receipt FKs.

Hash the complete closed command envelope with existing `canonical_json_bytes`,
`sha256_canonical_json` and `sha256-cjson-v1`: command name, authenticated actor,
project/task/command IDs, expected revision, material version 1 and every argument,
including defaults/NULLs. Lowercase UUID text, NFC text; no generated IDs, times,
current projections or request correlation ID. Preserve all old request vectors.
Freeze new fixed vectors and result cardinalities in the execution pack.

After **every wait**, authenticate and require current read entitlement, then
look up the project/actor/command receipt: equal hash returns the original IDs
**before write-role, state, stop, expiry or CAS checks**; unequal hash yields
existing IDEMPOTENCY_CONFLICT. With no receipt, check current write authority and
all fresh predicates. A new command duplicating a Run link fails without effects;
only exact receipt replay is success. Uncertain commit reconciles that same
receipt in a fresh formal read; never generate a replacement command identity.

## 4. Persistence and budget binding

**DO NOT ADD SCHEMA** is the default. These four proposed tables are bounded
Entity + Relation + Event instances, requiring owner/architecture admission:

| Table — new in PR3-16 | Material and one-line DO-NOT-ADD-SCHEMA reason |
| --- | --- |
| `experiment_search_sessions` | ID, project/task/budget IDs, optional two root version FKs, creator actor/time, receipt FK. DO-NOT-ADD-SCHEMA: individual Runs cannot identify a bounded search containing branches with no Run. |
| `experiment_search_nodes` | ID, task/session/parent IDs, depth, branch kind, mutation reason, optional Hypothesis/ExperimentSpec version FKs, reservation FK, creator actor/time, receipt FK. DO-NOT-ADD-SCHEMA: task steps and Runs do not retain the search-specific parent relation for failed/unexecuted candidates. |
| `experiment_search_node_runs` | ID, project/task/session/node/Run IDs, creator actor/time, receipt FK. DO-NOT-ADD-SCHEMA: a concrete relation preserves exact multiple Run attempts without an ID list or changing Run ownership. |
| `experiment_search_events` | ID, task/session IDs, optional node ID, optional Run-link ID, sequence, event kind, bounded reason, actor/time, receipt FK. DO-NOT-ADD-SCHEMA: typed branch failure/pruning and session closure facts cannot be reconstructed from task-wide events or Run outcomes. |

All four tables reject UPDATE/DELETE, including no-op mutation. FKs use RESTRICT,
never cascade. Composite FKs tie node-parent to the same session, session/node/link/
event/receipt/budget/reservation to the same task, and session to its project.
Scientific version IDs use concrete existing `hypothesis_versions` and
`experiment_spec_versions` FKs; verify owning project, frozen history and exact
owning-domain content hashes. Persist a separate nullable saved hash beside each
optional scientific version FK (hash present iff reference present), and reverify
it on admission/read. Never rewrite saved hashes. No candidate blob or soft
execution reference.

Add only required UNIQUE support keys to existing tables if absent, including
`runs(id, project_id)` for a composite Run/project FK; this is a **new in PR3-16**
constraint, not a new table. Freeze full support-key inventory before DDL. Require
unique session/node/Run link, one root per session, unique session event sequence,
unique reservation consumption per node, and at most one terminal event per node
and per session. Index every referencing FK and session/node ordered reads.

Reuse existing `research_task_command_receipts`, `research_task_events` and
`research_task_receipt_events`: **no new table** for replay. Extend their allowed
commands/events and deferred effect guards through a forward migration. Each
accepted command increments task revision once, creates one receipt and one task
event, plus exactly its declared lineage rows. Creation adds one session/event;
node append one node/event; link one relation/event; failure/prune/close one event.
Each new row references that command's fresh receipt; committed receipts cannot
admit extra rows. Direct normal-role SQL must enforce FKs, immutability, acyclicity,
terminal predicates and exact effect cardinalities across multiple flushes.

**Proposed budget interface (D1):** require a previously committed, same-task,
active-budget reservation with existing `tree_nodes=1`, not consumed by another
node and not finally settled. Its operation identity must equal the new node ID.
Verify existing `observed_depth` equals actual search depth AND the reservation's
existing task-step ancestor depth (NULL step permits root depth zero only).
Check current clock/deadline, checkpoints, task stop and caps; stop denies a new
append even if a reservation remains charged. PR3-04's last-unit budget stop may
therefore leave a charged reservation without a node; never fabricate a refund.
A post-stop append under a new command is not reconciliation.

This deliberately conservative binding uses existing reservation semantics.
Existing PR3-04 derives depth from `research_task_steps`, not search nodes, and
requires a comparable evaluator for positive node charges. It does not already
provide a node-aware admission API. If these conditions cannot be met, deny;
do not skip its guards, nest `reserve_task_budget` inside another command, settle
usage here, or silently change accounting. A separately reviewed atomic node-aware
admission amendment is the recommended long-term D1 resolution before activation.
Reservation gaps/unknown outcomes retain charges until existing trusted settlement.

Existing `runs` has no task FK. A Run link proves project and lineage attribution,
not that a Run was executed under a particular reservation. PR3-11's later Run
execution contract must prove that accounting; PR3-16 must not counterfeit it.

No Agent execution table/FK exists at 0079. Proposed actor attribution is a
planning-only staging choice (D3), not a substitute for execution provenance.
Specification §30's execution attribution must use an exact FK supplied by the
separately delivered PR3-02 execution slice (**new in PR3-02**) before any
agent-executed search is admitted. Do not create a placeholder UUID column here.

## 5. Exact transaction and read recipes

One command = one synchronous READ COMMITTED transaction using existing
`SqlAlchemyUnitOfWork.begin_research_task`. Startup timeouts: lock 10s, statement
30s, connect 10s; restore pooled defaults. No preliminary auth/receipt SELECT,
SET LOCAL, advisory lock, write or autoflush. First Application SQL is exactly the
existing sorted 18-table inventory:

```sql
LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts,
claim_versions, claims, hypothesis_versions, hypotheses,
literature_source_project_links, literature_sources, manuscript_versions,
project_memberships, project_role_assignments, projects, publications,
research_question_versions, research_questions, source_versions IN SHARE MODE;
```

Then, in this order:

1. Existing `rb_phase2_lock_project(project_id)`.
2. Existing transaction advisory key
   `pr301:command:<project_uuid>:<authenticated_actor_uuid>:<command_uuid>`.
3. Existing transaction advisory key `pr301:task:<task_uuid>`.
4. Existing `research_tasks` row FOR UPDATE, then `research_task_steps` ascending
   ID FOR UPDATE; read dependencies by predecessor/dependent and both input
   tables by ID as in delivered PR3-01.
5. Read existing safety rows in order: `budget_reservations`,
   `budget_usage_records`, `checkpoint_policies`, `checkpoint_policy_dataset_scopes`,
   `checkpoint_policy_metric_scopes`, `execution_budgets`, `human_checkpoints`,
   `termination_policies`, each ascending ID. Immutable rows need no row lock;
   this slice never updates a checkpoint.
6. Read proposed lineage tables in table-name/ID order: events, node_runs, nodes,
   sessions (the full names are in §4). They are immutable; task advisory locking
   serializes inserts. Then read exact referenced scientific versions and Runs.
   No Run row lock: linking makes no lifecycle decision from mutable Run status.
7. Apply §3's fresh entitlement/receipt/replay rule after EVERY blocking wait,
   including constraint/FK waits. Replay precedes state/CAS checks. With no receipt,
   revalidate authority, archive, task revision, parent chain, exact references,
   reservation proof and fresh database clock before effects.
8. Update task once, insert receipt, declared lineage rows and task event/result
   link; force all deferred constraints while holding locks, then commit once.
   Any failure rolls back everything. No external/provider/artifact I/O under locks.

No new advisory namespace, task-table SHARE, lock upgrade or trigger-acquired
advisory lock. Only SQLSTATE 40001/40P01 allows up to three total fresh whole
attempts with unchanged identity/material. Timeouts never automatically retry.
A new constraint wait requires fresh validation before commit, not reuse of a
pre-wait authorization/expiry result.

All queries and explicit receipt recovery use existing `begin_formal_read` before
SQL: **one REPEATABLE READ READ ONLY snapshot, no locks** (no SHARE, advisory or
row locks), no autoflush, writes, nested sessions or second transaction. Entitlement,
parents, events, Run projections and budget are read in that same snapshot. Reads
never expire checkpoints, settle reservations or materialize status into writes.

## 6. Existing ErrorCodes only

Mappings below already exist in `src/researchbase/foundation/errors.py`,
`src/researchbase/api/errors.py` and `src/researchbase/cli/errors.py`.

| Existing ErrorCode | HTTP / CLI | Use |
| --- | --- | --- |
| VALIDATION_ERROR | 422 / 2 | Malformed fields, duplicate IDs, bad branch kind or self-parent. |
| AUTHENTICATION_REQUIRED | 401 / 3 | No verified principal. |
| FORBIDDEN | 403 / 3 | Scope/role/credential denial; no protected existence disclosure. |
| NOT_FOUND | 404 / 3 | Entitled exact task/session/node/Run/reference absent. |
| INVALID_STATE_TRANSITION | 409 / 4 | Closed branch/session, duplicate relation, stopped/blocked admission or missing accounting/execution prerequisite. |
| IMMUTABLE_RECORD | 409 / 4 | Reparent, detach, rewrite or delete history. |
| CONCURRENT_MODIFICATION | 409 / 4 | Stale task CAS, exhausted deadlock/serialization attempts or timeout. |
| IDEMPOTENCY_CONFLICT | 409 / 4 | Same command identity, different normalized material. |
| REFERENTIAL_INTEGRITY_ERROR | 409 / 5 | Concrete FK/same-session contradiction in persisted effects. |
| VERSION_NOT_FROZEN | 409 / 4 | Scientific version not frozen. |
| FROZEN_REFERENCE_REQUIRED | 409 / 5 | Current/latest supplied instead of an exact scientific reference. |
| PROVENANCE_CLOSURE_VIOLATION | 409 / 5 | Exact version/hash contradiction. |

No new public code is proposed. Preserve sanitized error envelopes; never expose
foreign-project IDs, SQL or constraint text. Owner approval would be required for
any future code addition, explicitly recorded as a separate decision.

## 7. Required future tests and acceptance

These are implementation obligations, not executed results or gate evidence.

| Layer | Required evidence |
| --- | --- |
| Unit/contracts | Closed envelopes, fixed normalized hash vectors, unchanged old vectors, root/child depth, every terminal predicate, ancestor blocking, no implicit descendant prune, failed branch without Run, no score/scientific-success semantics. |
| Architecture | Same Human/Agent Application boundary, DTOs rather than ORM, no direct SQL/provider/framework path from callers, no subscription CLI backend, no premature Agent execution/promotion. |
| PostgreSQL 18 schema/migration | Clean/populated upgrade from accepted head, sole head, forward-only repair; concrete same-project/task/session FKs, one root, cycle/duplicate/reservation reuse attacks; immutable no-op UPDATE/DELETE rejection; no cascade; old scientific hashes unchanged. |
| PostgreSQL commands/guards | Exact receipt effects across multiple flushes and direct normal-role SQL; no orphan/extra rows or committed-receipt reuse; failed/pruned/unexecuted/negative lineage survives; closure reconciliation retains exact Run IDs; whole rollback. |
| PostgreSQL budget | Shared task cap across sessions, matching step/search depth or denial, node unit proof, reservation gap retains charge, stop/expiry/checkpoint failure blocks append, last-unit sticky stop, no refunds on prune/failure; no Run budget claim without later evidence. |
| PostgreSQL concurrency/replay/queries | First exact SHARE, common advisory keys, append versus append/stop/cancel/revoke, fresh validation and replay before CAS after waits, lost/uncertain commit, changed hash, bounded retries/timeouts; coherent lock-free repeatable-read tree/lineage/budget under writers. |

Existing regression anchors: `tests/unit/phase3/test_research_task_contracts.py`,
`tests/unit/phase3/test_task_safety_contracts.py`,
`tests/unit/phase3/test_agent_identity_contracts.py`,
`tests/architecture/test_pr3_01_boundaries.py`,
`tests/architecture/test_pr3_04_boundaries.py`,
`tests/architecture/test_pr3_02_s1_boundaries.py`, and existing
`tests/integration/phase3/test_pr3_01_replay.py`, `test_pr3_04_accounting.py`,
`test_pr3_04_concurrency.py`, `test_pr3_04_queries.py`,
`test_pr3_02_s1_schema.py` (last four share that integration directory).
New suite paths are **new in PR3-16**, to be frozen in the implementation pack.
Record exact focused commands/counts/environment and independent review there;
use real PostgreSQL 18, not SQLite. Open P0/P1 blocks acceptance.

## 8. Owner decisions and recommendations

| Decision | Recommendation requiring owner approval |
| --- | --- |
| D1 — schema and budget admission | Approve four pattern-based tables only after full FK/index/trigger/hash/result inventory is frozen. Prefer a separately reviewed amendment giving atomic node-aware admission through existing PR3-04 accounting; preserve old commands/vectors. Until then use §4's conservative pre-reservation proof or deny; never claim full node-aware budgeting is delivered. |
| D2 — lifecycle staging | Approve append-only recording with the limited states above; defer scoring, selection, success and heuristic decisions to PR3-17. Preserve existing branches after pruning/closure; allow exact Run reconciliation without spend. Freeze explicit subtree termination semantics before adding a bulk operation. |
| D3 — execution attribution | Allow attributable Human/verified Agent planning records using existing actors, with real execution disabled. Require the separately delivered PR3-02 execution FK and reviewed admission contract before agent-executed search; no dummy execution ID. |
| D4 — Run relation cardinality | Permit multiple distinct Runs per node and reuse of an existing Run across nodes as explicit lineage; unique per node/Run. Such reuse is not a fresh experiment or new evidence. Do not infer task budget attribution from project membership. |
| D5 — material and release boundary | Use typed optional frozen root/node references and mutation reason; defer objective/scoring policy structures to PR3-17 instead of JSON. Preserve existing errors, migration seriality and no-provider scope. Require a separately authorized PR3-16 execution pack after decisions close. |

Authoring verification: identifiers/paths checked with focused repository searches;
whitespace, single-file scope and installed static tools checked separately.
Unit, architecture and PostgreSQL tests: **NOT RUN**, per the explicit
“No tests run” documentation-only instruction. No implementation or gate PASS is
claimed. No code, migration, test, dependency, branch, commit or push is delivered.
