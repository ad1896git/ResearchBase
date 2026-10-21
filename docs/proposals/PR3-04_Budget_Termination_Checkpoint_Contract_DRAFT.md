# PR3-04 Budget / Termination / HumanCheckpoint contract

Status: DRAFT — awaiting owner approval; not authorized for implementation

## Start here

Read the authority table, then approve the decisions in §9 before authorizing an
execution pack. This file proposes enforceable workflow limits; it authorizes no
code, migration, dependency, provider activation or scientific release.

The delivered baseline is `0077_research_task_graph`, not the older PR3-01 proposal.
It admits only CREATED, PLANNING and CANCELLED tasks. Policy bindings do not by
themselves enable execution. A future migration must be 0078+ on the actual sole
head; never edit 0077 or assume that 0078 remains available.

Notation: every proposed identifier in a table labeled **new in PR3-04**, including
its fields and literals, is new in PR3-04 unless explicitly called existing.
Architecture concept names below describe proposals, not delivered classes.

## 1. Authority, scope and exclusions

| Authority | Effect on this contract |
| --- | --- |
| [System architecture](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), [correction](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), [registry](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md) | Scientific facts, exact references, immutable history and schema discipline remain binding. |
| [Cross-phase contracts](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md) | Preserve Application boundaries, earlier command semantics and history. |
| [06](../architecture/06_Phase3_Development_Specification_v1.1_Harness_Integrated.md) §§4, 21–24 | Three task policy IDs; A0–A3; checkpoint, budget and termination semantics. |
| [Harness specification](../harness/09_Harness_Integration_Specification_v1.0.md) | Harness cannot own or directly mutate canonical state. |
| [Approved roadmap](PHASE3_Roadmap_DRAFT.md), PR3-04 row | This PR owns workflow safety policies, not the gateway or workers. |
| [ADR-0021](../architecture/adr/ADR-0021-tdg3-phase3-technology-decisions.md), TDG3-08/09/10 | A1/A2 default, separately authorized A3, pilot caps, first-bound stop and human-only extension. |
| [ADR-0022](../architecture/adr/ADR-0022-pr3-01-policy-staging-input-layout.md) | End staged omission with enforced bindings for executable tasks; no fabricated policy or planning-row backfill. |
| [PR3-01 freeze](../phase3/PR3-01-contract-freeze.md), delivered migration and runtime (§8) | Preserve planning, locks, receipts, exact inputs, errors and backward reads. |

In scope: ExecutionBudget, TerminationPolicy and HumanCheckpoint (all **new in
PR3-04**), a minimal typed checkpoint policy, binding admission, budget reservation
and settlement, stop evaluation, checkpoint responses, and deterministic fake
consumer tests. These are Application services behind repository ports/UoW.

Excluded: dispatch/leases, gateway implementation, real model/coding/compute
calls, sandbox activation, recovery, tree-search execution, promotion, working
memory, scientific freeze/release, new scientific Approval purposes, A4 and new
infrastructure. Later consumers must enforce this contract before activation.
PR3-04 alone must leave the existing reserved execution commands disabled.

## 2. Invariants and enforcement rules

1. Human and Agent callers share the Application boundary. Autonomy is a ceiling,
   never authority. Current identity, membership, role and project entitlement
   apply independently. OWNER is the existing role recommended for policy binding,
   checkpoint response and extensions; it must belong to a verified Human.
2. A0 suggests only; A1 may create scientific drafts but cannot freeze them; A2
   executes only a human-approved plan with required frozen scientific inputs;
   A3 additionally requires separately human-authorized bounded scope. A checkpoint
   response cannot substitute for the owning scientific command or Approval.
   No self-escalation, agent response, agent extension or A4.
3. All three exact policy bindings are required together before any execution
   admission. Missing bindings fail closed. A0/A1 tasks also need bounds if they
   consume runtime resources. A sealed workflow plan is not a frozen scientific spec.
4. Policy content is immutable once inserted. Bindings may be set once on a
   nonterminal planning task, including a sealed plan as an explicitly approved
   operational addition; this never changes plan inputs/edges. Terminal history
   and existing request hashes stay unchanged. No ordinary policy replacement.
5. Reserve worst-case resource use atomically before a consumer may act. Include
   outstanding reservations, retries and failed/unknown outcomes. Unknown usage
   retains the full reservation until attributable reconciliation; no timeout
   automatically refunds it. Agents cannot supply authoritative usage.
6. Admission requires every consumed-plus-reserved amount plus the proposed amount
   to be within its cap. An action may reach a cap exactly; no subsequent action
   may consume that dimension. Stop on the first exhausted bound. GPU cap zero
   denies GPU use but does not stop CPU-only work. Depth and parallelism are gauges,
   not cumulative costs; wall time uses database UTC elapsed time, including waits.
7. Stop blocks new reservations immediately. Keep failed, cancelled, pruned and
   unknown work visible. Never equate a stop request with confirmed external
   cancellation. Reconciliation/settlement remains allowed after stop.
8. A denied operation raises an error with no success receipt. A stop evaluation
   that records a newly detected stop is a successful mutation with receipt/event;
   do not roll it back by raising the denial that subsequent work receives.

### 2.1 Pilot defaults and termination

All cap fields below are **new in PR3-04**; the values are approved ADR-0021 defaults.
No NULL, infinity, negative limits or agent-raised values. Cost uses exact decimal
USD equivalents with a pinned pricing basis; never binary floating point.

| Budget fields — new in PR3-04 | Default |
| --- | --- |
| max_wall_time_seconds, max_agent_steps, max_llm_calls | 1800, 50, 50 |
| max_search_calls, max_code_iterations, max_experiment_runs | 20, 3, 5 |
| max_tree_nodes, max_tree_depth, max_parallel_branches | 10, 3, 1 |
| max_gpu_hours, max_token_cost, hard_stop | 0, 5 USD equivalent, true |

Count a step on admitted execution attempt, a model/search call before dispatch,
a code iteration per admitted code/debug cycle, a Run before creation, and a tree
node before insertion. Failed attempts count. Reservations must bound provider
output tokens and execution time, not just input estimates. A later adapter unable
to bound cost/time must deny admission. No actual provider containment is claimed here.

TerminationPolicy (**new in PR3-04**) defaults: repeated_failure_threshold=2 and
max_no_improvement_iterations=2; budget_stop, human_stop and policy_stop=true.
Repeated failure means consecutive failures of the same logical step; a success
resets that streak. No-improvement counts completed comparable iterations without
a strictly greater score under a pinned metric/direction; equality counts. Without
an approved comparable score, autonomous iteration is denied, not assumed improving.

The remaining 06 §24 controls (min_progress_score, duplicate_hypothesis_threshold,
confidence_stop_threshold, success_condition; all **new in PR3-04**) are disabled
explicitly by default, with typed enabled flags and typed thresholds when enabled.
A confidence/success stop never establishes scientific truth. Owner decision D3
must freeze their evaluator contract before any nondefault use.

Simultaneous causes are all retained, ordered human stop, policy violation,
budget exhaustion, repeated failure, no improvement, success. Operational stop
reason is deterministic; scientific failure/success is never inferred from it.
TERMINATED_BUDGET, TERMINATED_POLICY and WAITING_HUMAN are **new in PR3-04** runtime
state proposals from 06, not existing TaskStatus members. Their activation and
transitions require the later execution pack; PR3-04 can persist a stop/checkpoint
without pretending the delivered planning state machine already runs.

## 3. Persistence proposal

Every table and column in this table is **new in PR3-04**. UUIDv7 IDs and UTC times
are generated by the Application. Each row has id, research_task_id, created_at,
and a concrete same-task receipt FK to existing research_task_command_receipts.
Policy rows belong to exactly one task; no cross-project sharing or mutable latest.

| Table — new in PR3-04 | Typed material and DO-NOT-ADD-SCHEMA exception |
| --- | --- |
| execution_budgets | §2.1 caps, currency, pricing_basis, content_hash, hash_scheme. DO-NOT-ADD-SCHEMA: an immutable runtime limit entity is not scientific evidence or an Approval. |
| termination_policies | §2.1 termination fields, score_metric, score_direction, evaluator_version, content_hash, hash_scheme. DO-NOT-ADD-SCHEMA: typed runtime stop rules cannot be represented by a scientific Decision. |
| checkpoint_policies | required checkpoint-type set, timeout_seconds, maximum_autonomy, A3 scope fields, content_hash, hash_scheme. DO-NOT-ADD-SCHEMA: the task's concrete policy FK needs an immutable runtime gate definition, not generic JSON. |
| human_checkpoints | step_id nullable, checkpoint_type, status, reason, requested_at, expires_at, responded_at/by nullable, response_reason nullable, row_version, response_receipt_id nullable, proposed_budget_id nullable. DO-NOT-ADD-SCHEMA: request/response lifecycle is a runtime gate, distinct from scientific Decision/Approval. |
| budget_reservations | budget_id, step_id nullable, requested resource vector, observed depth/parallel occupancy, deadline, operation_id. DO-NOT-ADD-SCHEMA: a typed relation reserves capacity across the transaction/external-work boundary without inventing scientific usage. |
| budget_usage_records | reservation_id, measured resource vector, outcome, failure streak, no-improvement streak, score nullable, evaluator_version, settled_at. DO-NOT-ADD-SCHEMA: immutable settlement events provide auditable accounting; scientific records cannot double as runtime charges. |

Vectors have separate numeric columns for each §2.1 dimension, not a JSON map.
A3 scope is typed exact allowed dataset snapshot and metric version IDs plus
allowed code paths and network deny/allowlist settings; concrete relation storage
for multi-valued canonical references must be named and justified in D1's execution
pack before implementation. Do not silently add tables or use soft references.

Add budget_policy_id, termination_policy_id and checkpoint_policy_id (**new in
PR3-04**) to existing research_tasks, with concrete same-task composite FKs to the
three policies. Additive nullable physical columns preserve planning-only rows;
a CHECK requires either all three NULL or all three non-NULL. Execution admission
and deferred final-state guards require all non-NULL for any executable state,
regardless of task type/autonomy. No migration UPDATE/backfill, dummy policy or
unresolved UUID. Future execution-state expansion must extend these guards.

Keep current planning CHECKs until that expansion is separately authorized. Modify
0077's binding-immutability/event/receipt guards only through a forward migration;
they currently reject added command/event kinds and sealed material changes.

Checkpoint types (**new in PR3-04**) use 06 §22's plan_review,
hypothesis_selection, experiment_approval, budget_extension, code_risk,
claim_freeze, manuscript_release and exception. Statuses (**new in PR3-04**) are
PENDING, APPROVED, REJECTED, MODIFIED, EXPIRED; those are checkpoint statuses,
not scientific authorizations. Only PENDING may acquire one final response.
MODIFIED denies continuation pending a new reviewed request; REJECTED/EXPIRED
also block continuation. Expiry uses database time, including time spent waiting.
Multiple required checkpoints are conjunctive. Retain the original recommendation
and reason; no arbitrary payload can carry an executable command.

Use RESTRICT throughout, same-task step/receipt/budget/checkpoint composite FKs,
unique operation_id per task, at most one final usage settlement per reservation,
and one open checkpoint per task/step/type (including NULL-step uniqueness).
Index each referencing FK, task/time reads and pending expiry scans. Immutable
rows reject UPDATE/DELETE, including no-op writes; checkpoint transition is the
sole one-time update exception with attributable response receipt. Deferred guards
verify binding completeness, resource totals, result links and one task revision/
event/receipt per mutation across multiple flushes. No session bypass flag.
Stops and all causes use existing research_task_events with typed added columns
and added event literals (**new in PR3-04**); no separate stop table or JSON core.
Migration pack must enumerate all new columns, checks, indexes and triggers before
approval, retain historical hashes, and refuse destructive downgrade.

## 4. Exact locking, transactions and reads

One mutation is one synchronous READ COMMITTED transaction using existing
SqlAlchemyUnitOfWork. Connection startup lock_timeout=10s and
statement_timeout=30s bound the first wait; restore pooled defaults. No preliminary
SET LOCAL, authorization SELECT, receipt SELECT, advisory lock or write.
The first Application SQL statement locks this exact sorted 18-table inventory
in SHARE mode (existing names, identical to PR3-01):

actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions,
claims, hypothesis_versions, hypotheses, literature_source_project_links,
literature_sources, manuscript_versions, project_memberships,
project_role_assignments, projects, publications, research_question_versions,
research_questions, source_versions.

Then, in order:

1. Existing rb_phase2_lock_project(project_id).
2. Existing transaction advisory command key
   `pr301:command:<project_uuid>:<authenticated_actor_uuid>:<command_uuid>`.
3. Existing transaction advisory task key `pr301:task:<task_uuid>`.
4. Existing research_tasks row FOR UPDATE, then research_task_steps by id FOR
   UPDATE; read existing dependencies and inputs in PR3-01 order.
5. New policy/accounting/checkpoint rows in table-name then primary-key order:
   budget_reservations, budget_usage_records, checkpoint_policies,
   execution_budgets, human_checkpoints, termination_policies (**new in PR3-04**).
   Immutable rows need only reads; any row locks follow this order.

Do not introduce a different advisory namespace: old and new commands must exclude
one another. No task-table SHARE, lock upgrades or trigger-acquired advisory locks.
The 18-table SHARE blocks unrelated writers too; do not narrow it in this PR.
After every blocking wait, recheck current credentials, Human type when required,
roles, scope, archive state, expiry and exact input hashes with fresh database time.
Authorize before protected existence/conflict disclosure. Perform no network,
provider, artifact-store or cancellation I/O under locks.

Write task revision once, children/policies, receipt, task event, concrete result
links; force all deferred constraints before commit while locks remain held.
Existing receipt/event tables must cover new effects, not merely trust Application
code. Failures roll back the whole transaction. SQLSTATE 40001/40P01 alone permits
up to three fresh whole attempts with identical identity/material and fresh
authorization; timeouts never retry automatically.

All queries and explicit replay lookups call existing begin_formal_read before
SQL: one REPEATABLE READ READ ONLY snapshot, autoflush disabled, no SHARE,
advisory or row locks, writes, nested sessions or second transaction. Entitlement,
usage, policies, checkpoint expiry projection and history use that snapshot.
Querying an expired checkpoint does not write its EXPIRED transition. A subsequent
mutation rechecks time; reads do not promise visibility of later revocation.

## 5. Commands, queries, DTOs and replay

Keep existing TaskCommand, TaskRead and CommandResult compatible. Old planning
request material/version 1 and fixed hashes stay unchanged. New commands use a
separate closed envelope, not newly mandatory arguments on create_research_task.
HTTP and CLI call the same service and return immutable DTOs, never ORM entities.

Each command below is **new in PR3-04**. Common fields: project_id, task_id,
command_id, expected_row_version plus trusted authenticated context; caller cannot
supply actor, timestamps, status, usage truth or resulting revisions.

| Command — new in PR3-04 | Arguments and effect |
| --- | --- |
| bind_task_policies | Exact three proposed policy IDs and typed contents; verified Human OWNER creates immutable bundle and sets all bindings once. Nonterminal CREATED/PLANNING only. Existing plan seal is preserved. |
| reserve_task_budget | operation_id, step_id nullable, typed worst-case resource vector and bounded deadline; trusted runtime consumer only, never arbitrary agent declarations. Validate all gates before durable reservation. |
| settle_task_budget | reservation_id, trusted measured vector, outcome and typed evaluator observations; exactly one final settlement. Unknown outcome cannot release capacity. |
| evaluate_task_termination | reason and trusted observations; persist newly detected stop and all causes, or an evaluated no-stop event. Repeated evaluation under another command retains history. Human stop requires verified Human OWNER. |
| request_human_checkpoint | checkpoint_id, step_id nullable, type, reason, proposed_budget_id nullable; trusted runtime or entitled Human; policy determines expiry and required gate. |
| respond_human_checkpoint | checkpoint_id, expected checkpoint revision, response and reason; verified Human OWNER, one unexpired pending response. No scientific writes. |

Policy content includes the proposed budget/checkpoint schemas above; no caller
may weaken mandatory stops. An extension request creates an immutable proposed
budget tied to a budget_extension checkpoint (**new in PR3-04**), never rewrites
the active budget. D2 must settle continuation/binding semantics before enabling
extensions. Until then approval records human intent but grants no spend.

Queries get_task_safety and get_task_checkpoint_history and DTOs TaskSafetyRead,
CheckpointRead, SafetyCommandResult are **new in PR3-04**. Safety read returns exact
policy IDs/hashes, caps, consumed/reserved/remaining values, stop causes, required
pending gates and unmet prerequisites. History returns checkpoint request/response
identities/times and original reasons in created_at/id order. Command result
contains existing CommandResult plus immutable newly created policy/reservation/
settlement/checkpoint IDs, derived through concrete same-task receipt FKs; response
receipt links recover the same checkpoint ID. Optional current projections are
separately labeled. Extend existing TaskRead with optional policy IDs only;
execution_enabled remains false until all later prerequisites are implemented.

New envelope type SafetyCommand (**new in PR3-04**), material_version=1, includes
command name, authenticated actor, project/task/command IDs, expected revision and
all arguments/defaults/NULLs. Use existing canonical_json_bytes and
sha256_canonical_json, sha256-cjson-v1. NFC-normalize text first; lowercase UUIDs,
exact decimals as canonical strings, sort set-valued references/paths, reject
duplicates before sorting, forbid unknown fields, NaN/infinity and live/latest
references. No request IDs, timestamps, computed usage or result IDs in material.
Before implementation freeze complete envelope examples and fixed hash vectors
for binding, response, reservation and extension; old vectors must remain identical.

Replay uses existing project/actor/command uniqueness and saved normalized hash.
After current read entitlement, return original result before CAS/state/expiry
checks, even when current write authority is gone. Different hash conflicts.
Same response retried after expiry still replays its prior success; a new response
command after expiry fails. Lost response never repeats a reservation or response.
Uncertain commit reconciles receipts in a new formal read; no new command UUID.

## 6. Existing errors only

All codes and transport mappings below exist; add no budget/checkpoint ErrorCode.
Diagnostic reason strings, if needed, are **new in PR3-04**, not public error enums.

| Existing ErrorCode | HTTP / CLI | Use |
| --- | --- | --- |
| VALIDATION_ERROR | 422 / 2 | Bad fields, bounds, duplicate inputs, decimal or evaluator shape. |
| AUTHENTICATION_REQUIRED | 401 / 3 | Untrusted/missing principal. |
| FORBIDDEN | 403 / 3 | Wrong scope, revoked entitlement, Agent attempting human action or authority escalation. |
| NOT_FOUND | 404 / 3 | Entitled exact task/policy/checkpoint missing. |
| INVALID_STATE_TRANSITION | 409 / 4 | Missing bindings, blocked/exhausted gate, expired/already answered checkpoint, disabled execution. |
| IMMUTABLE_RECORD | 409 / 4 | Policy/settlement/history mutation or forbidden rebinding. |
| CONCURRENT_MODIFICATION | 409 / 4 | Stale task/checkpoint revision, exhausted serialization/deadlock retries, lock/query timeout. |
| IDEMPOTENCY_CONFLICT | 409 / 4 | Same command identity with different normalized material. |
| REFERENTIAL_INTEGRITY_ERROR | 409 / 5 | Persisted same-task concrete FK contradiction. |
| VERSION_NOT_FROZEN | 409 / 4 | Proposed scientific version not frozen. |
| FROZEN_REFERENCE_REQUIRED | 409 / 5 | Unresolved current/latest scientific reference. |
| PROVENANCE_CLOSURE_VIOLATION | 409 / 5 | Saved exact input/hash contradiction. |

Preserve sanitized HTTP/CLI envelopes and request identity. No foreign-ID,
constraint-text, credential or raw SQL leakage. Exact entitled replay precedes
state/revision checks; sealed scientific material remains immutable.

## 7. Required future tests and acceptance

These are obligations for a separately authorized implementation, not test results.
No tests were run to author this document.

| Layer | Required cases |
| --- | --- |
| Unit | Every cap below/equal/above boundary; zero GPU; exact cost rounding; concurrent reservation math; failures/retries/unknowns count; wall time includes human waits; two-failure/two-no-improvement thresholds; score ties/absent metric; deterministic simultaneous causes; A0–A3 deny matrix; checkpoint response cannot freeze/release. |
| Contracts/transports | Closed DTOs, trusted actor/usage, fixed new hash vectors and unchanged PR3-01 vectors; identical HTTP/CLI results/errors; replay before expiry/CAS; current read entitlement and sanitized denial. |
| PostgreSQL 18 schema/migration | Clean and populated 0077 upgrade, sole head, unchanged scientific hashes/trace; planning bindings remain NULL; zero/mixed/foreign bindings and executable NULL denial; immutable policy/receipt/history; same-task FKs; uniqueness including NULL-step checkpoints; downgrade refusal; multiple-flush deferred guards and direct normal-role SQL. |
| PostgreSQL concurrency/application | First statement exact SHARE; reserve versus reserve at last unit; response versus response/expiry/revoke; bind versus cancel/seal; stop versus admission; settlement after stop; fresh authorization after waits; timeout evidence; whole rollback; lost/uncertain commit replay; no duplicate charges; lock-free coherent repeatable reads under writers. |
| Architecture/fake consumer | Common Human/Agent Application boundary; no direct ORM/vendor path; restart reconstructs gates from DB; stop prevents dispatch; bounded fake cancellation with unknown outcome retained; no real execution enabled; no scientific Decision/Approval or canonical mutation from checkpoint response. |

Future pack must list exact focused static/unit/architecture/PostgreSQL commands,
counts, failures/skips and environment, with independent review. Reuse existing
PR3-01 suites in §8 as regression anchors; add named PR3-04 suites only after their
paths are frozen (**new in PR3-04**). Use real disposable PostgreSQL 18, never SQLite.
Real overshoot/cancel/recovery evidence belongs to later adapter/worker PRs; fake
accounting is not evidence of external containment. Open P0/P1 blocks acceptance.

## 8. Existing-identifier inventory and authoring verification

Existing identifiers above were checked with focused rg against src/, migrations/
and tests/, not inferred from architecture pseudocode:

| Existing identifiers | Delivered source / regression anchors |
| --- | --- |
| 0077_research_task_graph, research_tasks, research_task_steps, research_task_command_receipts, research_task_events, research_task_step_events, research_task_receipt_events, research_task_receipt_step_events; planning columns/statuses and CHECKs | migrations/versions/0077_research_task_graph.py |
| TaskCommand, TaskRead, CommandResult; existing autonomy literals A0–A3 | src/researchbase/agent_runtime/application/contracts.py; domain/research_task.py under the same agent_runtime root |
| create_research_task and reserved execution commands; OWNER; current authority | src/researchbase/agent_runtime/application/research_task.py; domain/research_task.py |
| Exact 18-table inventory, advisory key strings, rb_phase2_lock_project | src/researchbase/persistence/research_task_repository.py; migrations/versions/0019_phase2_bootstrap_membership.py |
| SqlAlchemyUnitOfWork, begin_formal_read | src/researchbase/persistence/uow.py |
| canonical_json_bytes, sha256_canonical_json, sha256-cjson-v1 | src/researchbase/foundation/canonical_json.py, hashing.py; migrations/versions/0077_research_task_graph.py |
| ErrorCode and §6 mappings | src/researchbase/foundation/errors.py; src/researchbase/api/errors.py; src/researchbase/cli/errors.py |
| Existing regression tests | tests/unit/phase3/test_research_task_contracts.py, test_research_task_graph.py, test_research_task_transports.py; tests/architecture/test_pr3_01_boundaries.py; tests/integration/phase3/test_pr3_01_schema.py, test_pr3_01_application.py, test_pr3_01_concurrency.py, test_pr3_01_replay.py, test_pr3_01_migration.py (basenames share their preceding directory). |

Only this new Markdown file is delivered. Whitespace/scope and installed static
tools are checked separately; unit, architecture and PostgreSQL tests: NOT RUN
under the explicit documentation-only instruction. No implementation/gate PASS
is claimed. Exact observed static results are reported with the delivery summary.

## 9. Owner decisions with recommendations

| Decision | Recommendation requiring explicit owner approval |
| --- | --- |
| D1 — schema and execution-pack freeze | Approve the six typed runtime tables as pattern-based exceptions, nullable planning/all-required execution bindings and sealed-plan operational binding. Freeze concrete A3 scope relation tables with one DO-NOT-ADD-SCHEMA reason each, full columns/index/trigger inventory and hash vectors before implementation; no schema inferred from this draft. |
| D2 — new budget after stop | Keep terminal task history terminal. Prefer a new explicitly linked continuation task with a Human-approved new budget; carry prior usage/history visibly and require no active unknown reservations before resuming spend. Freeze the concrete continuation relation in a separate reviewed pack. Do not reset counters or let an APPROVED checkpoint silently replace an active budget. |
| D3 — progress and accounting | Use consecutive per-logical-step failures and pinned comparable progress scoring as §2.1; disable optional confidence/duplicate/success thresholds until typed evaluator semantics are approved. Freeze rounding, pricing basis and trusted usage source at adapter intake. Unknown outcomes retain worst-case charges. |
| D4 — checkpoint authority and expiry | Verified current Human OWNER only; default timeout 24 hours (**new in PR3-04** default), fail closed on expiry/rejection/modification, and immutable response provenance. Required types derive from action risk; scientific freeze/release always use existing governance independently. |
| D5 — autonomy and activation | Keep A1/A2 defaults and A3 disabled without explicit bounded policy. Approve separate execution-pack transitions before exposing running states; PR3-04 binding/accounting tests alone enable no provider or worker. |
| D6 — safety integration | Retain PR3-01 exact lock protocol/error codes. Require later gateway/worker admission, cancellation, reconciliation and measured overshoot evidence before real execution; no new error enum or infrastructure in this PR. |

Approval of recommendations is a contract decision only. Obtain separate named
PR3-04 implementation authorization after the execution-pack gaps above close.
