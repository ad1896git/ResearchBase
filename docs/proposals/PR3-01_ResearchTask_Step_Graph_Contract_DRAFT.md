# PR3-01 ResearchTask / Step Graph Contract — DRAFT

> **Revision 2026-10-20 (director fix):** cycle backstop changed to per-edge targeted reachability + per-step ancestor walk; the earlier "already checked" marker was forgeable by normal SQL callers.
>
> **Revision 2026-10-20:** Rebased on delivered Phase 2 and head 0075; corrected first-SHARE writes and lock-free snapshot reads, forward-only migrations and AGENT-binding limits; identified proposed schema and required per-table rationale. This aligns the parked draft with actual exit evidence; implementation remains unauthorized. Director review: cited the committed Phase 2 acceptance record and final verification counts. Corrected per-family hash columns, batched cycle checks, input-layout options, SHARE rationale and the source-link table name; made policy staging an explicit owner choice.

**Status: APPROVED by owner 2026-10-20 (ADR-0022 decisions) — NOT yet authorized for implementation**

**Scope:** documentation proposal only. No code, migration, runtime dependency,
worker, provider or production policy is authorized. Proposed decisions require
owner approval, consistency review and a separately authorized execution pack.
Phase 2 director GO is recorded in the [Phase 2 acceptance record](../phase2/phase2_acceptance_2026-10-20.md);
TDG-3 and explicit Phase 3 GO remain required.

## Start here

ResearchTask stores research intent and an attributable dependency graph in
ResearchBase. It does not own Hypothesis, ExperimentSpec, Run, Measurement, Claim,
literature or publication facts. A planner's graph is a candidate until the same
Application service used by Human callers validates and persists it. Framework
checkpoints cannot be the only stored task/graph state.

This draft proposes a **planning slice**: create tasks, build/seal DAGs, cancel
unstarted tasks and read their graphs/progress. It specifies the full lifecycle
compatibility surface but disables execution commands pending the later budget,
execution, gateway and recovery contracts. This is an explicit scope decision
for owner approval, not acceptance of the whole Phase 3 runtime.

Read §4 for commands/states, §5 for typed persistence, §6 for exact lock order,
§7 for error mappings, §10 for build paths/DDL and §11 for tests. All implementation
instructions describe future work. [PR3-00](PR3-00_Agent_Runtime_Bootstrap_Contract_DRAFT.md)
is a prerequisite, and contains the common authority/entry summary.

The [Phase 2 exit report](../phase2/phase2_exit_report.md) records validate_exit
PASS (16 PASS + 3 DEFERRED); director GO is recorded in the
[Phase 2 acceptance record](../phase2/phase2_acceptance_2026-10-20.md) on 2026-10-20 after the independent review
and R1–R3 corrections. Its final baseline is `286cd9a`: **12,524 passed,
66 skipped, 0 failed** (historical evidence, not checks rerun for this draft).
B20 screening and B23 novelty review/revision first slices are delivered, alongside
prepared-package freeze, manuscript revision and reconsideration. The
[roadmap carry-over inventory](PHASE3_Roadmap_DRAFT.md#phase-2-completion-backlog)
maps B28, AQ-S3-08, Linux host evidence, B20/B23 exclusions and R4–R7 to Phase 3
consequences. None authorizes Phase 3 implementation.

## 1. Authority, ownership and inspected baseline

| Source | Contract carried forward |
| --- | --- |
| [AGENTS.md](../../AGENTS.md) and [System Architecture 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §§3, 55–57, 85–91, 97, Appendix H | Same Application boundary for Human/Agent; deterministic facts precede Agent output; complexity budget; candidate promotion; replaceable runtime. |
| [Correction Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A1, A4, A10–A14, A18–A22 | Typed strong references, relational ID collections, UPPER_SNAKE_CASE, immutable promotion later, TDG-3 and fresh post-lock authority. |
| [Global Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md), §§4, 6–12 | agent_runtime owns ResearchTask/Step workflow state; AgentExecutionInstance != Run != CapabilityInvocation; no new graph aggregate or generic reference entity. |
| [Cross-Phase Contracts 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), §§14–24, 31, 33, 38, 50, 52 | Retain history; stable exact references/errors; framework replacement preserves tasks; Project archive retains provenance. |
| [Phase 3 Specification 06](../architecture/06_Phase3_Development_Specification_v1.1_Harness_Integrated.md), §§4–5, 18, 21, 43–48, 69–74, 79, 86, final harness addendum | Task/step fields, states, dependency graph, commands/queries; later policy/execution/recovery ownership; no unbounded execution. |
| [TDG-2 11](../architecture/11_TDG2_Phase2_Technology_Decision_Gate_v1.0.md) | Accepted literature roles; activation still needs intake; B28 remains deferred. TDG-3 remains an owner decision. |
| [Harness Specification](../harness/09_Harness_Integration_Specification_v1.0.md), §§2, 12–17, 21, 23–29 | Routing constrained by phase/authority/capability; output candidate by default; no direct persistence access or self-weakening; fingerprint uses manifest/value. |

The current branch ends at `0075_m1_reconsideration`, not 0042. Existing
[Application ports](../../src/researchbase/application/ports.py) define `UnitOfWork`;
[SqlAlchemyUnitOfWork](../../src/researchbase/persistence/uow.py) implements
transaction ownership, `begin_formal_read()`, commit/rollback and error normalization.
[DecisionService](../../src/researchbase/application/decision.py) takes a UoW
factory and returns typed readbacks; repositories are used inside that boundary.
The [Decision repository](../../src/researchbase/persistence/decision_repository.py)
now documents SHARE snapshot locking before request/target locking. The
[identity repository](../../src/researchbase/persistence/phase2_identity_repository.py)
provides `rb_phase2_lock_project` coordination; it does not supply a new runtime.
Use these real patterns, not the old request→target→SHARE ordering.

**Existence convention:** all task/step tables, fields, constraints, event types,
request payload keys, lifecycle/task/step/autonomy enums, commands, queries,
DTOs, services, routes and CLI operations in §§2–11 are **new in PR3-01** unless
explicitly identified as existing. Execution-only states/commands are reserved
for the later owning PRs listed in §2, not currently available branch behavior.
The generic ErrorCodes and maps in §7, the six scientific version tables in §6,
and the cited Application/UoW/identity infrastructure already exist. No generic
Agent runtime or AGENT enrollment path exists; AQ-S3-08 remains an accepted gap.

[Phase 3 roadmap](PHASE3_Roadmap_DRAFT.md) proposes 01→(02 + 04)→03 and later worker
recovery. This draft makes that staging concrete without implementing missing
policy objects or unconstrained runtime behavior. No PR3-01 execution pack exists
in this checkout. Any new fields/operational relations below need bounded schema
review; they are proposals, not additional frozen architecture.

## 2. Scope and staged policy contract

PR3-01 owns ResearchTask, ResearchTaskStep, dependency/typed-input relations,
minimal append-only workflow events and command receipts using existing
Entity/Relation/Event patterns. TaskGraph is a query over these rows, not a second
canonical object, framework checkpoint blob or new top-level schema.

PR3-02 owns attributable AgentVersion/Execution, promotion and immutable harness
binding; PR3-03 owns invocation/gateway/routing; PR3-04 owns ExecutionBudget,
TerminationPolicy and HumanCheckpoint; PR3-05 owns context/memory; PR3-19 owns
outbox/inbox/leases/recovery. No provider/model, scientific-agent loop, search
manager, venue send, full authority engine or Phase 4 functionality in PR3-01.

**Proposed staging deviation requiring owner/architecture disposition:** 06 §4
shows mandatory `budget_policy_id`, `termination_policy_id` and
`checkpoint_policy_id`, before their PR3-04 schemas. The recommended owner option (a) in §9 omits these columns
entirely while only CREATED/PLANNING/CANCELLED tasks can be persisted. It creates
no unresolved policy UUID, dummy policy or weak FK. PR3-04 adds concrete policy
bindings and constraints in its own migration after a reviewed field contract;
checkpoint policy representation must be agreed there because the registry lists
HumanCheckpoint, not an independent canonical CheckpointPolicy entity. Legacy
planning rows remain execution-ineligible until explicitly configured through an
authorized Application command. No silent default/autonomy/budget backfill.

The final accepted layout must enforce non-null exact required policy bindings
for every executable task. Do not implement this staged omission without a
recorded ADR before any implementation; 06 §4 lists these fields as mandatory.
Section 9 also presents moving the three policy tables into PR3-01 or adding
nullable columns now. Those alternatives require explicit owner scope/contract
approval; implementers cannot select or expand the allocation by convenience.

## 3. Invariants and proposed defaults

1. Task is orchestration identity, never evidence or scientific truth. Persist
   objective, requester, exact inputs and graph; no duplicate scientific facts.
2. Every task/step/edge/input/event/receipt has a concrete task/project/actor
   relationship. Cross-task parent/dependency/current-step refs fail. Cross-project
   inputs deny by default; global SourceVersion access requires an existing
   same-project row in `literature_source_project_links` and current entitlement.
3. Task/step input bindings use six concrete relation families from 06 §4:
   ResearchQuestionVersion, HypothesisVersion, ClaimVersion, SourceVersion,
   ArtifactVersion and ManuscriptVersion. No polymorphic JSON semantic core.
   No ExperimentSpec/Run inputs are silently added; their later admission needs
   the owning contract. Formal task inputs must be exact frozen versions;
   SUPERSEDED remains acceptable only as preserved, previously frozen history.
   DRAFT input support requires a separately reviewed explicit context rule.
4. References retain owning-domain hash scheme/content hash where available;
   reverify exact hash/frozen state and authorization at plan admission/seal.
   Never resolve latest/current automatically. Binding a STALE/INVALID input
   for investigation is allowed with explicit validity warnings; it cannot be
   used to establish a valid scientific result. A warning is not gate success.
5. Ordinal is presentation order, not readiness. A dependency is
   `predecessor → dependent`; all predecessors must be SUCCEEDED for readiness.
   SKIPPED, FAILED, CANCELLED and WAITING do not satisfy it. No implicit skip.
6. No self-edge, duplicate edge, cycle, cross-task edge or parent cycle. Parent
   is hierarchy only, never an implicit dependency; parent forest and DAG are
   both checked. Dynamic loops later append new step IDs/edges, not back-edges
   that turn a persisted DAG into a cycle or overwrite failed attempts.
7. Task mutation is optimistic concurrency on task `row_version`; one accepted
   mutation increments once, including graph-only changes. Child revisions also
   increment once for actual child changes. Stale writes never win silently.
8. Seal makes task intent/inputs/strategy/autonomy and admitted graph material
   immutable. No ordinary deletion of task, step, edge, input, event or receipt,
   even before execution; correction is a new task referencing history in a
   separately contracted relation if needed. No unapproved amendment mechanism.
9. Terminal history is immutable. Preserve failures, cancellation, skipped steps
   and original attribution. A retry later creates a new attributable execution
   and attempt history; it must not erase a failed state or use a bare retry_count
   as the only evidence. This slice provides no retry command.
10. Planner text is untrusted input. It cannot set authority, timestamps, policy,
    readiness, scientific success, AgentExecution identity or approval. A0–A3
    are workflow limits, never authority. No A4 or self-escalation.
11. Normal-role SQL must not bypass same-task/FK/history/seal/DAG constraints.
    Architecture tests cover Caller→Application→Port/UoW→Persistence→PostgreSQL;
    runtime callers receive DTOs, not ORM/repository handles.

## 4. Commands, lifecycle and DTO contract

Commands are immutable closed typed DTOs (`extra=forbid` at transports). UUIDs
are canonical, enums UPPER_SNAKE_CASE; objective is NFC-normalized nonblank text,
max 8,192 characters. Proposed limits: 256 steps, 1,024 edges, 256 typed input
bindings total per task (task plus all steps). These admission limits are not
execution budgets. The pack must confirm limits before implementation.

Common mutation inputs: authenticated trusted context, `project_id`,
`command_id` UUID, and `expected_row_version` for existing tasks. `command_id`
is the logical mutation identity, distinct from HTTP request_id. Creator/actor,
event/receipt UUIDv7 IDs, timestamps, status, hashes and revisions are server-derived.
Create uses caller `task_id` UUIDv7 for stable retry identity; add/plan commands
supply stable step IDs. Each resulting ID is persisted, never regenerated on replay.

| Command | Specific input | Atomic result / admitted here |
| --- | --- | --- |
| `create_research_task` | `task_id`, task_type, objective, strategy_id/version, autonomy_level, six typed input sets | CREATED task, input rows, CREATED event and receipt. Empty inputs allowed; no agent call. |
| `create_task_plan` | task_id, complete proposed initial nodes/edges and step input sets | CREATED with no prior steps→PLANNING; inserts entire validated nonempty DAG and event/receipt. No partial graph. |
| `add_task_step` | task_id, one stable step_id/type/ordinal/parent/role/capability declaration, input sets, existing predecessor IDs | PLANNING/unsealed only; append node/edges atomically after complete cycle/scope validation. |
| `add_task_step_dependency` | task_id, predecessor/dependent IDs | Proposed bounded helper; PLANNING/unsealed only, validates resulting full graph. |
| `seal_task_plan` | task_id | Proposed planning helper; PLANNING/unsealed, nonempty DAG, complete valid bindings; set immutable `plan_sealed_at` and event. Status stays PLANNING; no READY/RUNNING steps. |
| `cancel_research_task` | task_id, nonblank reason | CREATED/PLANNING→CANCELLED; all PENDING children→CANCELLED with events; finished_at set once. No job to cancel in this slice. |
| `start_research_task`, `pause_research_task`, `resume_research_task` | task_id | Compatibility names reserved; execution prerequisites unmet → deny without writes. No fake RUNNING/PAUSED success. |
| `start_task_step`, `finish_task_step`, `fail_task_step` | task/step IDs and later execution result contract | Reserved; deny in this slice. Success cannot be caller-supplied text. |
| `get_research_task`, `get_task_graph`, `get_task_progress` | project_id, exact task_id | Currently entitled immutable DTO read, no lifecycle writes. |

Task types are exactly 06 §4 normalized to UPPER_SNAKE_CASE:
LITERATURE_RESEARCH, HYPOTHESIS_GENERATION, EXPERIMENT_DESIGN, EXPERIMENT_EXECUTION,
ANALYSIS, CLAIM_REVISION, MANUSCRIPT_DRAFTING, INTERNAL_REVIEW,
END_TO_END_RESEARCH, REPLICATION, OTHER. They describe intent, not installed abilities.
Step types are 06 §5 PLAN, RESEARCH, RETRIEVE, HYPOTHESIZE, DESIGN_EXPERIMENT,
CODE, DEBUG, EXECUTE, ANALYZE, CRITIQUE, WRITE, REVIEW, HUMAN_CHECKPOINT, PROMOTE,
OTHER. Agent role/capability declaration is a nonblank optional logical string,
max 128 characters, never a granted capability or canonical FK.
Strategy ID/version are exact nonblank immutable configuration identifiers,
not `latest`/`main`/`master`; resolution/intake enforcement is deferred to PR3-03.
No strategy table or provider-specific schema here. Changing a sealed selection
requires a new task; no same-execution harness modification.

Proposed default autonomy A0; store any explicit A0/A1/A2/A3 as **requested** level,
with `execution_enabled=false` derived for every task in this slice. No effective
policy or authority is inferred from it. Agents can persist attributable planning
metadata only if independently authorized by the existing principal boundary;
A0 still cannot create scientific DRAFTs. If current identity cannot authenticate
an Agent, deny; do not invent HUMAN provenance or add Agent enrollment in this PR.

Full compatibility transition table below is **future**, except the three admitted
planning transitions. All unlisted transitions deny. Later packs must freeze
wait/recovery/step attempt semantics before activation.

| State | Proposed successor(s) | Activation |
| --- | --- | --- |
| CREATED | PLANNING, CANCELLED | Planning slice. |
| PLANNING | CANCELLED; RUNNING after seal + execution gates | Cancellation here; RUNNING deferred. |
| RUNNING | WAITING_HUMAN, PAUSED, SUCCEEDED, FAILED, CANCELLED, TERMINATED_BUDGET, TERMINATED_POLICY | Deferred. |
| WAITING_HUMAN | RUNNING, PAUSED, CANCELLED, TERMINATED_POLICY, TERMINATED_BUDGET | Deferred; checkpoint response != scientific approval. |
| PAUSED | RUNNING, CANCELLED, TERMINATED_POLICY, TERMINATED_BUDGET | Deferred; resume rechecks all execution gates. |
| SUCCEEDED / FAILED / CANCELLED / TERMINATED_BUDGET / TERMINATED_POLICY | None | Terminal; new task for another research attempt. |

Future step transitions: PENDING→READY or CANCELLED; READY→RUNNING or CANCELLED;
RUNNING→WAITING/SUCCEEDED/FAILED/CANCELLED; WAITING→RUNNING/FAILED/CANCELLED.
SKIPPED needs explicit authorized skip policy and append-only reason; never
satisfies a successor's dependency in the default policy. This slice admits only
PENDING→CANCELLED. Deferred execution success requires all required nodes SUCCEEDED,
known outcomes, settled budget and policy/checkpoint gates; a framework “done”
message cannot finish a task. `current_step_id` is navigation only, NULL here;
future parallel execution queries derive active steps rather than using it as a
second source of graph state.

Read DTO: task material, immutable requester/time, status/row_version/seal time,
nullable started_at/finished_at/current_step_id, requested autonomy,
execution_enabled=false and unmet prerequisite labels. Graph DTO: nodes sorted
`(ordinal,id)`, explicit edges sorted `(predecessor_id,dependent_id)`, hierarchy,
exact typed inputs with original hashes and current validity warnings, events.
Progress counts statuses from persisted rows; empty graph is zero steps, never
100% complete. No ORM entities or mutable reverse lists as canonical fields.

## 5. Persistence and hash contract

**DO NOT ADD SCHEMA.** These are proposed **new in PR3-01** typed instances of
Entity + Relation + Event, not new scientific concepts. Existing scientific
entities/assessments/snapshots/events cannot represent workflow identity, graph
constraints and replay without changing their owning semantics. Every table
below needs explicit owner/architecture admission before migration; pattern reuse
does not itself authorize DDL. No generic JSON graph or reference table is admitted.
The two input layouts below are mutually exclusive owner options; all twelve
per-family rows belong to the alternative layout.

| Proposed new table | Material / reason existing rows are insufficient |
| --- | --- |
| `research_tasks` | Project/actor FKs, intent/strategy/requested autonomy, status/times, row_version/seal/current-step; scientific entities have no workflow identity or planning lifecycle. |
| `research_task_steps` | Task FK, same-task parent, ordinal/type/status/role/capability/times/revision; a Run cannot stand for an unexecuted workflow operation. |
| `research_task_step_dependencies` | Same-task endpoint FKs, unique non-self edge, reverse index, cycle guards; parent links/ordinals cannot represent DAG precedence. |
| `research_task_inputs` (recommended layout) | Task FK and six nullable concrete version FKs with exactly-one CHECK, per-family uniqueness and hash/scope guards; no existing task input relation owns these bindings. |
| `research_task_step_inputs` (recommended layout) | Same-task step FK with the same six concrete version FKs/guards; task-wide bindings cannot express step-specific inputs. |
| `research_task_input_questions` (alternative layout) | Concrete research_question_versions FK plus exact saved hash; no existing task→question binding exists. |
| `research_task_input_hypotheses` | Concrete hypothesis_versions FK plus exact saved hash; no existing task→hypothesis binding exists. |
| `research_task_input_claims` | Concrete claim_versions FK plus exact saved hash; no existing task→claim binding exists. |
| `research_task_input_sources` | Concrete source_versions FK plus exact saved hash/project-link access; no existing task→source binding exists. |
| `research_task_input_artifacts` | Concrete artifact_versions FK plus exact saved hash; scientific Run inputs cannot own task context. |
| `research_task_input_manuscripts` | Concrete manuscript_versions FK plus exact saved hash; manuscript placements cannot own task context. |
| `research_task_step_input_questions` | Same-task step FK and concrete research_question_versions FK/hash; task-wide bindings cannot express step-specific inputs. |
| `research_task_step_input_hypotheses` | Same-task step FK and concrete hypothesis_versions FK/hash; task-wide bindings cannot express step-specific inputs. |
| `research_task_step_input_claims` | Same-task step FK and concrete claim_versions FK/hash; task-wide bindings cannot express step-specific inputs. |
| `research_task_step_input_sources` | Same-task step FK and concrete source_versions FK/hash/project-link access; task-wide bindings cannot express step-specific inputs. |
| `research_task_step_input_artifacts` | Same-task step FK and concrete artifact_versions FK/hash; task-wide bindings cannot express step-specific inputs. |
| `research_task_step_input_manuscripts` | Same-task step FK and concrete manuscript_versions FK/hash; task-wide bindings cannot express step-specific inputs. |
| `research_task_events` | Immutable task/actor/command FKs, sequence, prior/new state or planning event, reason/time/revision; scientific lifecycle events do not own task history. |
| `research_task_step_events` | Immutable same-task step/actor/command FKs and sequence/state/time/revision; task-only events cannot enforce step-specific history. |
| `research_task_command_receipts` | Operational immutable project/actor/command uniqueness, task FK, normalized hash and saved result revision; scientific receipts do not identify planning-command outcomes. |
| `research_task_receipt_events` | Concrete receipt/task-event FKs with same-task enforcement; a receipt must retain exact saved task event IDs without a JSON ID array. |
| `research_task_receipt_step_events` | Concrete receipt/step-event FKs with same-task enforcement; task-event links cannot represent cancellation's exact child-event results. |

**Input layout is an explicit owner choice (§9).** Recommend two typed tables,
`research_task_inputs` and `research_task_step_inputs`, each with six nullable
concrete FKs (`research_question_version_id`, `hypothesis_version_id`,
`claim_version_id`, `source_version_id`, `artifact_version_id`,
`manuscript_version_id`) and `CHECK (num_nonnulls(research_question_version_id,
hypothesis_version_id, claim_version_id, source_version_id, artifact_version_id,
manuscript_version_id) = 1)`. Each has one partial unique index per family on
(owner, concrete version ID) WHERE that FK IS NOT NULL; owner is task ID or
(task ID, step ID), respectively. Step inputs also have the composite same-task FK.
Use `content_hash NOT NULL` and nullable `hash_scheme`, with a CHECK requiring
`hash_scheme = 'sha256-cjson-v1' AND hash_scheme IS NOT NULL` for source/manuscript
rows and `hash_scheme IS NULL` for the other four families. A NULL here means no
owning scheme column, never an invented scheme or an unhashable input.

The twelve per-family input tables listed above are the alternative layout, not
an additional allocation alongside the two tables. They separate family guards but
increase the DDL/trigger/test surface from about 2 tables to 12; the two-table
layout puts per-family guards into CASE logic. Recommend separate tables only
when a concrete per-family guard needs them. Both retain typed FKs, owner/version
uniqueness, RESTRICT deletes and frozen/project guards, with no
`target_type + target_id` soft reference. Freeze exactly one layout in the pack.
The artifact DDL example in §10 illustrates the twelve-table alternative only.

Saved hash columns are copied from the exact owning row as follows, identically
for task and step inputs in either layout; never synthesize an owning column:

| Family / owning version table | Copied hash columns | Per-family alternative task / step tables |
| --- | --- | --- |
| ResearchQuestion / `research_question_versions` | `content_hash` only; no `hash_scheme` column | `research_task_input_questions` / `research_task_step_input_questions` |
| Hypothesis / `hypothesis_versions` | `content_hash` only; no `hash_scheme` column | `research_task_input_hypotheses` / `research_task_step_input_hypotheses` |
| Claim / `claim_versions` | `content_hash` only; no `hash_scheme` column | `research_task_input_claims` / `research_task_step_input_claims` |
| Artifact / `artifact_versions` | `content_hash` only; no `hash_scheme` column | `research_task_input_artifacts` / `research_task_step_input_artifacts` |
| Source / `source_versions` | `content_hash`, `hash_scheme` (exactly `sha256-cjson-v1`) | `research_task_input_sources` / `research_task_step_input_sources` |
| Manuscript / `manuscript_versions` | `content_hash`, `hash_scheme` (exactly `sha256-cjson-v1`) | `research_task_input_manuscripts` / `research_task_step_input_manuscripts` |

Verified with focused grep (`rg`) of the four complete mapped class blocks in
[models.py](../../src/researchbase/persistence/models.py) and their creating
migrations [0003](../../migrations/versions/0003_research_question_hypothesis.py),
[0006](../../migrations/versions/0006_artifact_version.py) and
[0014](../../migrations/versions/0014_claim_evidence.py). Source/manuscript tables
are defined by migration DDL rather than mapped classes in that file: grep of
[0022](../../migrations/versions/0022_source_version_and_merge_lineage.py) and
[0035](../../migrations/versions/0035_pr2_12_publication_draft.py) confirms both
columns and the scheme CHECK. Frozen admission requires non-null saved hashes;
reverify under each owning contract, without relabeling Phase 1 hashes as Phase 2
canonical JSON. Events use no fictional prior state on creation. Receipts are
replay records, not scientific truth or an outbox. SQL enforces immutable
events/receipts and sealed inputs.

Step `output_refs` from 06 §5 are empty in this planning slice; no scientific
output-ingestion command or placeholder locator is admitted. Later execution/
promotion contracts must add concrete output relations before accepting outputs.
An input or graph event cannot substitute for AgentPromotionRecord.

No scientific `ON DELETE CASCADE`. All history FK deletes RESTRICT, plus explicit
UPDATE/DELETE guards where history
requires them. No physical deletion merely because task was cancelled. Frozen
input relations/sealed material are guarded in SQL as well as Application. Event
and receipt creation plus task/graph mutation are in one transaction. No event
is an outbox or dispatch instruction. No task outbox/inbox/lease schema yet.

Task workflow has no new scientific content_hash. Input hashes retain their
owning contract. Operational `request_hash` (new in PR3-01) uses the existing
`foundation/canonical_json.py` and `foundation/hashing.py` implementation and SHA-256 with `hash_scheme=sha256-cjson-v1` and
`material_version=1`. Fixed payload keys: `type=ResearchTaskCommand`,
`material_version`, `command_name`, `project_id`, authenticated `actor_id`,
`command_id`, `task_id`, `expected_row_version` (NULL create), `arguments`.
`arguments` is the command's closed typed fields from §4; type discriminants
are explicit in each typed binding. UUIDs canonical strings; inputs sorted by
(type,id); nodes by id; edges by (predecessor,dependent); duplicates rejected;
ordinal/parent stay material. Text normalized NFC; NULL retained; no timestamps,
request_id, correlation_id, computed status or provider metadata in request hash.
Unknown fields fail before hashing. These diagnostics/receipts are not scientific
truth and never replace concrete task inputs or promotion outputs. Publish fixed
hash vectors in the later authorized implementation tests.

## 6. Exact lock order, transactions and writer inventory

New PR3-01 repository/UoW methods must use synchronous PostgreSQL 18.x and one
READ COMMITTED transaction per mutation. No tool/network/model I/O under locks.
Isolation and bounded first-lock timeouts must be configured before SQL via the
connection setup; R5 is a carry-over style issue, not permission to leave the
first lock unbounded. Proposed limits are 10s lock and 30s statement timeout,
subject to the approved pack. Connection setup must restore pooled defaults.

1. **First application SQL statement:** `LOCK TABLE ... IN SHARE MODE` over the
   sorted, fixed input/authority inventory below. No preceding SET LOCAL,
   authorization SELECT, project/advisory lock, row lock, replay lookup or write.
   Selecting READ COMMITTED through connection options emits no preceding query.
2. Set transaction-local limits after the first SHARE statement if needed, then
   acquire existing `SELECT rb_phase2_lock_project(:project_id)` for one project.
   Multi-project task mutation is forbidden. Acquire proposed transaction advisory
   keys `pr301:command:<project_uuid>:<actor_uuid>:<command_uuid>` then
   `pr301:task:<task_uuid>` using existing PostgreSQL advisory-lock functions.
   These **new in PR3-01** key namespaces protect absent/existing task and replay.
3. Lock existing task `FOR UPDATE`, then children `ORDER BY id FOR UPDATE`;
   read dependency/input rows in table/PK order. A create's absent task is protected
   by the advisory key. No earlier business read is allowed.
4. Reread durable actor binding, membership, roles, project state and input scope;
   use fresh `clock_timestamp()` after all waits to check credential/expiry and
   current entitlement. No cached pre-wait authorization. Authorize before exposing
   existence/replay diagnostics; evaluate exact receipt replay as historical read
   entitlement, not renewed effect permission. A new replay query uses the read
   protocol below; duplicate mutation arrivals still use this write protocol.
5. Check expected task revision, plan seal/state, exact frozen inputs and hashes,
   limits, duplicates, same-task endpoints, dependency DAG and parent forest.
   Persist graph/task changes plus events/receipt atomically; force deferred
   constraints and commit once. New blocking waits require fresh authorization
   before effects. All failures roll back the entire UoW.

Existing tables in the proposed first SHARE inventory, verified in migrations/
persistence, are sorted below. Each protects a planning admission fact until commit:

| Table | Why a task mutation must block its writers |
| --- | --- |
| `actor_subject_bindings` | Keep the authenticated subject→actor binding stable through attribution/authorization. |
| `actors` | Keep actor identity/type stable for requester attribution and caller checks. |
| `artifact_versions` | Keep the exact artifact input hash/frozen state and parent FK stable. |
| `artifacts` | Keep artifact input project ownership stable. |
| `claim_versions` | Keep the exact claim input hash/frozen state and parent FK stable. |
| `claims` | Keep claim input project ownership stable. |
| `hypothesis_versions` | Keep the exact hypothesis input hash/frozen state and parent FK stable. |
| `hypotheses` | Keep hypothesis input project ownership stable. |
| `literature_source_project_links` | Keep the required project access link for global source inputs stable (real table name, migration 0020). |
| `literature_sources` | Keep the source identity referenced by a SourceVersion/project link stable. |
| `manuscript_versions` | Keep the exact manuscript input hash/frozen state and publication FK stable. |
| `project_memberships` | Prevent membership revocation/changes racing post-lock authorization. |
| `project_role_assignments` | Prevent role revocation/changes racing post-lock authorization. |
| `projects` | Keep project scope/archive state stable for new planning writes. |
| `publications` | Keep manuscript input project ownership stable through manuscript_versions.publication_id → publications.project_id; this is a scope check, not a publication lifecycle gate. |
| `research_question_versions` | Keep the exact question input hash/frozen state and parent FK stable. |
| `research_questions` | Keep question input project ownership stable. |
| `source_versions` | Keep the exact source input hash/scheme/frozen state and source FK stable. |

No table is retained solely for a later execution, promotion or publication gate;
all listed tables support this planning slice. Do not add placements, publications'
review/approval children or other scientific closure tables: current validity is a
read warning here. Freeze required parent/child writer interference in the pack.
SHARE locks are table-wide: **all writers of these tables wait**, including writers
for unrelated projects/versions. PR3-23 measures that contention cost before any
separately scoped narrowing. Do not SHARE-lock task tables being mutated and then
introduce cross-session lock upgrades. Existing input/authority writers retain
their accepted protocols.

Application graph validation uses Kahn's algorithm on the entire task DAG
(O(V+E), including isolated nodes); visited count != node count rejects
VALIDATION_ERROR with proposed `details.reason=DAG_CYCLE`. Three-color DFS checks
the parent forest separately. Ordinal does not imply dependency. Every graph
writer shares task/project exclusion through commit: the second of opposite-edge
writers validates the first's committed state. Deferred recursive SQL cycle checks
alone cannot serialize concurrent writers.

The new adapter uses ordinary SQLAlchemy DML behind the repository port. SQL
backstops include composite same-task FKs, no-self-edge CHECK, duplicate-edge PK,
seal/terminal/history UPDATE/DELETE guards and deferred reachability constraints.
Use `UNION` in recursive reachability to terminate cycles; reject any node reachable
from itself in dependency or parent graphs. Check each new or changed edge with a
**targeted reachability search**, not a whole-task closure: for edge
`predecessor → dependent`, search forward from `dependent` along this task's edges
and reject if `predecessor` is reachable. Any cycle in the final graph contains at
least one inserted/updated edge, so the deferred per-edge checks at commit, which
all see the final graph, reject every cycle. Each search is O(V+E) for this task
(at most 256 + 1,024 rows), so a 1,024-edge plan costs about 1.3 million row
visits at commit instead of O(E * V^2). For the parent forest, each new/changed
step walks its ancestors up to the root (at most 256 hops) and rejects if it
reaches itself. No transaction-local "already checked" marker is used: custom
settings and session state are writable by normal SQL callers, so a marker could
be forged to skip the check. The project/task advisory locks above remain held
through check and commit: a concurrent writer waits, then its own deferred
checks run against the committed graph plus its edits. Existing `pr215_complete_decision` /
`pr215_complete_basis()` in [0042](../../migrations/versions/0042_pr2_15_minimal_decision.py)
illustrate deferred constraint triggers, not current full writer ordering.
Normal-role SQL constraint tests and two-session tests must participate in the
same first-SHARE/project/task protocol. Never acquire advisory locks in triggers
after implicit row locks. If additional shared writer locks are needed, stop for
contract correction rather than silently rewriting accepted Phase 2 writers.

Retry only SQLSTATE 40001/40P01, at most three fresh whole transactions with the
same command identity/hash. Do not retry validation, permission, state or timeout.
Exhaustion and SQLSTATE 55P03/57014 map to sanitized CONCURRENT_MODIFICATION;
normalization belongs to the UoW. Failed attempts produce no success receipts.

**All reads, including replay-only lookups:** call existing
`uow.begin_formal_read()` before SQL. Its implementation selects one
REPEATABLE READ READ ONLY snapshot and disables autoflush. Authorization,
credential checks, exact task/graph/progress/events and nested input verification
must share that one UoW/session/snapshot. No SHARE table locks, project/task advisory
locks, row locks, writes, or second nested transaction. Return typed DTOs only.
Check read entitlement at trusted time within the snapshot; do not claim visibility
of changes committed after it began. Current validity warnings are labeled as
observed in that snapshot. A historical receipt read never re-executes mutation.
Long response streams are out of scope.

## 7. Error-code mappings — current adapters are the baseline

Values match [HTTP `_STATUS`](../../src/researchbase/api/errors.py),
[CLI_EXIT_CODES](../../src/researchbase/cli/errors.py) and the existing
[ErrorCode enum](../../src/researchbase/foundation/errors.py). No absent Phase 3
name is treated as an implemented code. Map conditions as follows for the planning
slice; adding stable task-specific public codes requires a separately approved
mapping change in the implementation pack.

| Existing code | HTTP | CLI exit | Trigger |
| --- | --- | --- | --- |
| VALIDATION_ERROR | 422 | 2 | Bad/unknown fields/literals, duplicates, oversized graph, blank objective, self-edge, cycle or parent cycle in proposed graph. |
| AUTHENTICATION_REQUIRED | 401 | 3 | Missing/unverified principal. |
| FORBIDDEN | 403 | 3 | Missing live role/membership/credential, archived project write, cross-project task/input disclosure or unavailable Agent principal binding. |
| NOT_FOUND | 404 | 3 | Currently entitled exact task/step/version ID absent. |
| INVALID_STATE_TRANSITION | 409 | 4 | Graph edit outside unsealed PLANNING, terminal action, deferred execution operation, duplicate lifecycle transition without exact receipt. |
| VERSION_NOT_FROZEN | 409 | 4 | Exact proposed version not historically frozen under its owning contract. |
| FROZEN_REFERENCE_REQUIRED | 409 | 5 | Caller supplied unresolved live/current reference where exact frozen input is required. |
| IMMUTABLE_RECORD | 409 | 4 | Attempt to change sealed intent/input/graph or terminal material/history. |
| CONCURRENT_MODIFICATION | 409 | 4 | Stale expected version, retry exhaustion, bounded lock/query timeout. |
| IDEMPOTENCY_CONFLICT | 409 | 4 | Same project/actor/command UUID with different normalized request material. |
| REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | Same-task composite FK violation or detected contradictory persisted strong reference. |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 | Persisted exact input hash/provenance contradiction. No claim that workflow graph itself is scientific closure. |

Authenticate and authorize before protected existence/conflict diagnostics; wrong
project denies without confirming foreign IDs. Transport validation may precede
authorization but must disclose only malformed submitted fields. Failed first
mutations produce no partial task, graph, event or receipt. API retains
`{error:{code,message,details}}` and X-Request-ID; CLI retains existing sanitized
error envelope and exit semantics. Diagnostics can use `details.reason` for
`EXECUTION_PREREQUISITES_UNMET` or `DAG_CYCLE`, never a fabricated ErrorCode.

06 §73 names `TASK_INVALID_STATE`, `TASK_BUDGET_EXCEEDED`, `TASK_POLICY_BLOCKED`,
`TASK_LEASE_CONFLICT`, `CHECKPOINT_REQUIRED`, `RECOVERY_NOT_ALLOWED` etc. They
remain future design vocabulary, absent from current enum/maps. Owner must
resolve whether PR3-01 introduces TASK_INVALID_STATE (with an explicitly agreed
409/4 mapping) or retains INVALID_STATE_TRANSITION before contract freeze;
this proposal defaults to the existing code. Budget/lease/checkpoint codes belong
to their owning PRs. No unsanitized KeyError from emitting an unmapped enum.

## 8. Replay and failure semantics

A committed receipt matches exact project, authenticated actor, command ID,
command name, task ID and normalized request hash. Under **current read entitlement**
return its saved task ID, resulting revision and immutable event IDs; optionally
return current task projection labeled separately. Do not recheck expected version,
re-execute mutation or manufacture a newer saved result. Revoked read entitlement
returns FORBIDDEN; authentication absence returns AUTHENTICATION_REQUIRED.
Changed hash returns IDEMPOTENCY_CONFLICT after entitlement, even if present
state would independently allow the changed action. Replay and cancelled-project
history are reads; archive denies new writes but retains permitted historical reads.

Crash before commit leaves no task mutation/receipt. Crash after commit and before
response replays the same receipt. Connection loss with uncertain commit is
reconciled by command lookup on a new transaction; never assume rollback and
create another task ID. Parallel commands on one task serialize and then CAS
admits at most one write from the same expected version. Parallel same-command
requests converge to one result; changed material conflicts. Cancellation retains
all steps/edges and marks only unstarted PENDING nodes here. Worker/job cancellation
and unknown external outcomes are deferred; no tool is dispatched by PR3-01.

## Glossary

| Term | Plain meaning |
| --- | --- |
| ResearchTask / Step / TaskGraph | Intent/workflow identity / one planned operation / projection of stored nodes and dependency edges. |
| DAG / parent | Directed graph without cycles / hierarchy relation, not scheduling dependency. |
| Candidate / promotion | Proposed agent output / validated attributable owning Application write; planning admission does not promote science. |
| Seal / frozen closure | Lock admitted plan material / resolve formal scientific dependencies to exact immutable versions. Distinct guarantees. |
| CAS / row_version | Reject writes from stale expected revision / monotonic concurrency counter. |
| UoW / receipt | One-command transaction / immutable saved outcome of a logical command. |
| Requested autonomy | Desired A0–A3 workflow limit; grants no execution or scientific authority. |
| SHARE / advisory lock | SQL lock blocking table writes / transaction-scoped named exclusion used by cooperating writers. |
| HumanCheckpoint | Workflow response; distinct from Decision/ApprovalGrant/scientific freeze. |
| AgentExecution / CapabilityInvocation / Run | Agent-role execution / tool invocation / scientific execution; separate records. |
| HarnessFingerprint | Immutable effective harness manifest/value, not evidence or a new top-level entity. |
| P0 / P1 / P2 / P3 | BLOCKER / MAJOR / MINOR / SUGGESTION findings. |

## 9. Proposed decisions for the owner

| Decision | Proposed default / freeze requirement |
| --- | --- |
| Planning before execution | Admit graph commands; execution disabled until accepted 02/03/04/19 contracts. Owner approves this narrowed slice explicitly. |
| Mandatory policy staging — explicit owner choice | **(a) Recommended:** omit the three policy columns in PR3-01 and add enforced bindings in PR3-04; keeps planning scope small but needs an ADR because 06 §4 lists them as mandatory. **(b)** Move the three policy tables into PR3-01; supplies concrete required FKs now but expands this PR and reallocates PR3-04 scope. **(c)** Nullable columns now; preserves field names but permits incomplete bindings and requires reviewed staging/nullability plus guards until enforcement. All choices leave planning rows execution-ineligible without exact enforced bindings; checkpoint policy representation still needs agreement. |
| Plan history | Seal graph before later start; no sealed amendment/row deletion/retry here. Later dynamic planning needs append-only extension contract. |
| Inputs — explicit owner choice | **Recommended:** two typed tables (task/step), each with six nullable concrete FKs, `CHECK num_nonnulls(...) = 1` and one partial unique index per family (§5); reduces DDL/trigger/test surface from ~12 tables to 2, with per-family guards in CASE logic. **Alternative:** twelve per-family tables as listed in §5, when a concrete per-family guard needs separation; simpler local guards cost more DDL/triggers/tests. Both satisfy typed FKs, no `target_type + target_id`; six exact frozen families, global-source project link, no draft/current shortcut. |
| Authority | Existing authenticated OWNER/RESEARCHER for writes, any effective project role entitled to these reads (OWNER/RESEARCHER/REVIEWER/APPROVER/VIEWER); positive AGENT admission awaits PR3-02 identity disposition (AQ-S3-08); no binding fabrication. Confirm policy with owner. |
| Autonomy / strategy | Store requested level/exact identifier only; no routing or activation; A0 default. |
| New fields/patterns | plan_sealed_at, child row_version, workflow event and operational receipt relations need bounded field/schema review, no new top-level canonical concept. |
| Error strategy | Current generic codes now; resolve TASK_INVALID_STATE compatibility before freeze. |
| Cycle guard | Application Kahn / three-color DFS under project/task exclusion; ordinary SQLAlchemy writes and deferred per-edge targeted reachability plus per-step ancestor-walk SQL checks, no forgeable marker (§6). |
| Locking / limits | One-project advisory exclusion, fixed SHARE inventory and three-attempt retry; graph limits 256/1024/256; verify writer matrix at the future accepted baseline. |

All unresolved dispositions block implementation, not drafting. No requirement is
waived by an owner approving prose without explicit scope/gate authorization.

## 10. Implementation guide — future authorization required

### 10.1 DDL sketch — illustrative, not an executable migration

```sql
-- Substitute approved migration/head; preserve existing table names and keys.
CREATE TABLE research_tasks (
  id uuid PRIMARY KEY,
  project_id uuid NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
  requested_by uuid NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  task_type text NOT NULL, objective text NOT NULL,
  strategy_id text NOT NULL, strategy_version text NOT NULL,
  autonomy_level text NOT NULL CHECK (autonomy_level IN ('A0','A1','A2','A3')),
  status text NOT NULL CHECK (status IN ('CREATED','PLANNING','CANCELLED')),
  created_at timestamptz NOT NULL, started_at timestamptz,
  finished_at timestamptz, plan_sealed_at timestamptz,
  current_step_id uuid,
  row_version integer NOT NULL CHECK (row_version >= 1),
  UNIQUE (id, project_id),
  CHECK (started_at IS NULL AND current_step_id IS NULL),
  CHECK ((status = 'CANCELLED') = (finished_at IS NOT NULL))
);
CREATE TABLE research_task_steps (
  id uuid PRIMARY KEY,
  research_task_id uuid NOT NULL REFERENCES research_tasks(id) ON DELETE RESTRICT,
  step_type text NOT NULL, ordinal integer NOT NULL CHECK (ordinal >= 1),
  parent_step_id uuid,
  status text NOT NULL CHECK (status IN ('PENDING','CANCELLED')),
  agent_role text, capability_id text,
  started_at timestamptz, finished_at timestamptz,
  retry_count integer NOT NULL DEFAULT 0 CHECK (retry_count = 0),
  failure_code text,
  row_version integer NOT NULL CHECK (row_version >= 1),
  UNIQUE (research_task_id, id), UNIQUE (research_task_id, ordinal),
  CHECK (parent_step_id IS DISTINCT FROM id),
  CHECK (started_at IS NULL AND failure_code IS NULL),
  CHECK ((status = 'CANCELLED') = (finished_at IS NOT NULL)),
  FOREIGN KEY (research_task_id, parent_step_id)
    REFERENCES research_task_steps(research_task_id, id) ON DELETE RESTRICT
);
ALTER TABLE research_tasks ADD CONSTRAINT current_step_same_task
  FOREIGN KEY (id, current_step_id)
  REFERENCES research_task_steps(research_task_id, id) ON DELETE RESTRICT;
CREATE TABLE research_task_step_dependencies (
  research_task_id uuid NOT NULL,
  predecessor_id uuid NOT NULL, dependent_id uuid NOT NULL,
  PRIMARY KEY (research_task_id, predecessor_id, dependent_id),
  CHECK (predecessor_id <> dependent_id),
  FOREIGN KEY (research_task_id, predecessor_id)
    REFERENCES research_task_steps(research_task_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (research_task_id, dependent_id)
    REFERENCES research_task_steps(research_task_id, id) ON DELETE RESTRICT
);
CREATE INDEX task_dependency_reverse ON research_task_step_dependencies
  (research_task_id, dependent_id, predecessor_id);
-- Twelve-table alternative only; §5 recommends the two-table layout.
CREATE TABLE research_task_input_artifacts (
  research_task_id uuid NOT NULL REFERENCES research_tasks(id) ON DELETE RESTRICT,
  artifact_version_id uuid NOT NULL REFERENCES artifact_versions(id) ON DELETE RESTRICT,
  content_hash text NOT NULL, -- artifact_versions has no hash_scheme column
  PRIMARY KEY (research_task_id, artifact_version_id)
);
-- Illustrative deferred validation: one targeted search per new/changed edge.
CREATE FUNCTION pr301_dependency_acyclic() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF EXISTS (
    WITH RECURSIVE reach(step_id) AS (
      SELECT NEW.dependent_id
      UNION
      SELECT d.dependent_id
      FROM reach r JOIN research_task_step_dependencies d
        ON d.research_task_id = NEW.research_task_id
       AND d.predecessor_id = r.step_id
    )
    SELECT 1 FROM reach WHERE step_id = NEW.predecessor_id
  ) THEN
    RAISE EXCEPTION 'task dependency cycle' USING ERRCODE = '23514';
  END IF;
  RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER pr301_dependency_acyclic_commit
  AFTER INSERT OR UPDATE ON research_task_step_dependencies
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
  EXECUTE FUNCTION pr301_dependency_acyclic();
-- Step INSERT/UPDATE of parent_step_id queues an analogous deferred ancestor walk
-- (same task, at most 256 hops) that rejects a step reaching itself.
-- No session/transaction marker: such state is forgeable by normal SQL callers.
-- Acquire §6 project/task advisory locks before DML; hold through flush/commit.
-- Never acquire them inside these triggers after implicit row locks.
-- BEFORE triggers reject sealed material changes and forbidden history mutation.
-- If the twelve-table alternative is selected, repeat for the other eleven §5 tables;
-- copy hash_scheme only for source/manuscript inputs, never for artifact inputs.
-- Step-input tables add composite (research_task_id,step_id) FK.
-- Event/receipt and the two receipt/event relation tables follow §5; no canonical IDs in JSON.
```

The sketch intentionally omits full enum/text/hash checks, receipt/event DDL,
the parent ancestor-walk trigger and
seal/terminal immutability triggers in §6,
plus frozen/scope input guards. They are mandatory implementation work, not
optional omissions.
The pack must enumerate every table/constraint/function/trigger/index before
migration authorization. Planning-state checks are deliberately narrow; later
execution migrations add states and policy constraints together. A static FK/CHECK
alone cannot enforce frozen state, access or acyclicity. Guard all through approved
SQLAlchemy adapter/constraint-trigger protocol in §6 plus Application validation
and adversarial SQL tests.

Migrations are **forward-only**. New downgrade entry points refuse before DDL or
revision-pointer changes, whether task tables are empty or populated. Correct
errors with a separately approved forward migration; never edit accepted 0075 or
its ancestors. Clean install, accepted-head upgrade, preserved historical hashes
and downgrade refusal are future disposable PostgreSQL 18 obligations. The new
parent is the accepted PR3-00 revision descended from 0075, assigned only in the
execution pack; retain one migration head.

### 10.2 Ordered build steps and paths

Existing composition/persistence paths below are present in the tree. All
`agent_runtime/` files are new under 06 §69's domain/application/ports layout;
`task_graph.py` is a pure validator, not another aggregate. The research-task
repository/query files, CLI command module, phase3 docs/tests and migration are
proposed new files under existing parent layouts. `docs/phase3/` and phase3 test
subdirectories are new. No separate API module is proposed.

1. Resolve §9 decisions and full policy staging in
   `docs/phase3/PR3-01-contract-freeze.md`; record Architecture Question/ADR under
   `planning/` / `docs/architecture/adr/` as appropriate. Inventory existing writers, accepted
   baseline and exact revision; do not modify accepted Phase 2 migrations.
2. Add pure models/validators in `src/researchbase/agent_runtime/domain/research_task.py`,
   `src/researchbase/agent_runtime/domain/task_step.py` and
   `src/researchbase/agent_runtime/domain/task_graph.py`; closed DTOs in
   `src/researchbase/agent_runtime/application/contracts.py`; repository/query
   protocols in `src/researchbase/agent_runtime/ports/task_repository.py`.
3. Add `src/researchbase/agent_runtime/application/research_task.py` for one-command
   UoW, permission, CAS, graph validation, seal, cancellation and receipts. Reuse
   existing principal/authentication and error types; no runtime framework import.
4. Add `src/researchbase/persistence/research_task_repository.py`,
   `src/researchbase/persistence/research_task_queries.py`; extend existing
   `src/researchbase/persistence/models.py` and `src/researchbase/persistence/uow.py`;
   implement ordinary SQLAlchemy writes behind the repository port using
   `decision_repository.py` as the model; keep §6 lock order and Application
   Kahn / three-color DFS checks. Add same-task FKs, self-edge CHECK, duplicate-edge
   PK, seal/history immutability triggers and deferred recursive cycle constraint
   triggers with per-edge targeted reachability and per-step ancestor walks as specified in §6
   (0042 illustrates deferred timing only). Add
   `migrations/versions/<approved_revision>_research_task_graph.py` with guards
   and forward-only downgrade refusal. Preserve earlier revision inventory.
5. Extend the existing `src/researchbase/api/routes.py`; wire services in
   `src/researchbase/api/app.py` and trusted context through
   `src/researchbase/api/context.py`. Add CLI commands in the new
   `src/researchbase/cli/commands/research_tasks.py`; register them through existing
   `src/researchbase/cli/app.py` and `src/researchbase/cli/composition.py`, using
   `src/researchbase/cli/transport.py`. Preserve existing API/CLI error maps. Planning REST: POST `/research-tasks`, POST `/{id}/plan`, POST
   `/{id}/steps`, POST `/{id}/dependencies`, POST `/{id}:seal-plan`, POST
   `/{id}:cancel`, GET `/{id}`, GET `/{id}/graph`, GET `/{id}/progress` under
   `/research-tasks`. CLI group `research-tasks` mirrors these operations.
   Deferred execution routes need not be published; any exposed reserved command
   must deterministically deny with §7, never return success.
6. Add tests in §11, readme commands and `docs/phase3/PR3-01-evidence.md`. Freeze
   transport/DDL/hash vectors in the approved pack; stop at this slice. No worker,
   promotion, checkpoint, budget, sandbox, compute or scientific command shortcut.

## 11. Required future tests and acceptance

| Proposed path | Required cases |
| --- | --- |
| `tests/unit/phase3/test_research_task_graph.py` | Full admitted transition matrix; terminal rejection; all declared types; parent forest; self/duplicate/cross-task/cycle rejection; diamonds/disconnected DAGs; ordinal != dependency; failed/skipped predecessor not readiness; graph limits. |
| `tests/unit/phase3/test_research_task_contracts.py` | Closed DTOs/NFC/UUID/enums; requested autonomy != authority; immutable intent/seal; fixed request-hash vectors and order independence; duplicate rejection; empty progress; disabled execution. |
| `tests/integration/phase3/test_pr3_01_schema.py` | PostgreSQL 18 clean/upgrade/sole head; same-task parent/current-step/dependency composite FKs; all six task/step inputs; frozen/hash/scope guards; no cascade; ordinary normal-role graph DML accepted when valid; self/duplicate/cross-task edges rejected; deferred cycles and parent cycles rejected at commit; 1,024-edge plan checked at commit within a recorded time bound; a cycle closed by the last edge of a batch is rejected; a cycle formed across an early flush and a later edit is rejected; seal/terminal/event/receipt tamper denied; index inventory. |
| `tests/integration/phase3/test_pr3_01_application.py` | Task/plan/add/edge/seal/cancel/query persisted atomically; failures leave zero protected effects; no scientific table/hash mutation; project/source-link isolation; attributable Human and eligible Agent use one boundary; denied Agent has no fabricated history. |
| `tests/integration/phase3/test_pr3_01_concurrency.py` | Two-session opposite-edge SQLAlchemy commands under project/task locks cannot both commit; deferred SQL trigger rejects a cyclic batch; plan versus seal; add versus cancel; same expected version yields one winner; normal-role SQL under the same graph lock protocol; valid direct DML and constraint/immutability violations; membership/link revoke versus write; first SHARE before all other SQL; lock-free repeatable-read queries concurrent with writers; actual lock-wait expiry with DB timestamps; timeout/retry exhaustion sanitized. |
| `tests/integration/phase3/test_pr3_01_replay.py` | Same command converges; changed hash conflicts; committed response lost then receipt replay; current read entitlement required; no re-execution on stale expected version; whole-transaction rollback; uncertain commit lookup. |
| `tests/integration/phase3/test_pr3_01_migration.py` | Accepted Phase 2/PR3-00 fixtures retained with identical hashes/trace; empty and populated downgrade refusal; forward repair evidence without data loss; no policy UUID fabricated; later-policy staging cannot activate execution. |
| `tests/unit/phase3/test_research_task_transports.py` | HTTP and CLI same DTO/results; every §7 code maps to exact current status/exit; request ID/diagnostics sanitized; auth before existence disclosure; unknown error still INTERNAL_ERROR. |
| `tests/architecture/test_pr3_01_boundaries.py` | Agent cannot reach persistence/ORM/credentials/vendor SDK; Human/Agent common Application; graph state recoverable without framework checkpoint; no JSON core refs; no scientific ownership in runtime. |

Future acceptance commands: `uv sync --locked`, `uv run ruff check .`,
`uv run ruff format --check .`, `uv run pyright`, `uv run alembic heads`, and
`uv run pytest -o addopts='' -ra tests/unit/phase3 tests/architecture tests/unit/architecture tests/integration/phase3`.
Supply safe disposable PostgreSQL 18 admin configuration as documented in README;
run the required accepted Phase 1/2 regression/exit commands from their packs.
No SQLite substitute. Exact results include counts, skips, failures and blocked
setup; graph tests alone cannot establish phase exit, sandbox safety or execution
provenance. Future start/finish/pause/resume and scientific golden E2Es remain
later acceptance obligations, never PASS from this planning slice.

Documentation-only revision. Future acceptance commands above are not current
execution evidence and do not establish Phase 3 GO.
