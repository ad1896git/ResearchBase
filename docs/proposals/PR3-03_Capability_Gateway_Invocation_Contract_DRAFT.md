# PR3-03 Capability Gateway / Invocation contract

Status: DRAFT — awaiting owner approval; not authorized for implementation

## Start here

Read §1, then decide §9 before commissioning an execution pack. This is a
contract proposal only. It authorizes no implementation, migration, dependency,
provider activation or Phase 3 gate success.

Delivered head: `0079_agent_identity_versions`, following
`0077_research_task_graph` and `0078_task_safety_policies`. Proposed migration:
**0080+ (number assigned at integration)**. Wave-3 siblings are drafted in
parallel; rebase on the accepted sole head, never reserve a number or edit an
accepted revision.

Notation: names, fields and literals in a proposal explicitly marked **new in
PR3-03** are proposed identifiers, even when the architecture already names the
concept. S2 execution identifiers are **new in PR3-02-S2**, not delivered by S1.
Existing identifiers have source anchors in §8.

## 1. Authority and ownership

| Authority | Binding consequence |
| --- | --- |
| [01 system architecture](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), [02 correction](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), [03 registry](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md), [08 compatibility](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md) | Exact provenance, immutable history, Application boundary and schema budget prevail. |
| [Phase 3 specification](../architecture/06_Phase3_Development_Specification_v1.1_Harness_Integrated.md) §§7–9, 40–41, 85; [Harness specification](../harness/09_Harness_Integration_Specification_v1.0.md) | Every tool call passes gateway policy; tool output is candidate material. Routing and executable intake cannot grant authority. |
| [Roadmap](PHASE3_Roadmap_DRAFT.md) PR3-03 row, ownership allocation and wave 3 | Own invocation, tool policy, typed refs, routing and supply-chain/self-modification enforcement. PR3-05 owns context, PR3-16 search lineage. Neither sibling is an implementation prerequisite for this fake slice. |
| [ADR-0021](../architecture/adr/ADR-0021-tdg3-phase3-technology-decisions.md) | Native runtime, bounded registry, pinned intake, fake providers until owner selection; each PR needs authorization. |
| [ADR-0023](../architecture/adr/ADR-0023-pr3-02-agent-identity-versions-executions.md), [S1 freeze](../phase3/PR3-02-S1-contract-freeze.md) | S1 delivered enrollment/versions/availability only. S2 executions and promotion wait for accepted PR3-03 and PR3-04 and separate authorization. |
| [ADR-0024](../architecture/adr/ADR-0024-pr3-04-budget-termination-checkpoint.md), [PR3-04 freeze](../phase3/PR3-04-contract-freeze.md) | Reuse hard budgets, trusted reservations/settlements, sticky stops and Human checkpoints. No second usage ledger. |
| [PR3-01 freeze](../phase3/PR3-01-contract-freeze.md) and delivered runtime | Preserve planning commands, hashes, receipt identity, locks and disabled execution. Delivered code resolves historical draft staging descriptions. |

## 2. Scope and exclusions

Implement only after approval: **CapabilityInvocation, AgentToolPolicy,
CapabilityGateway, CapabilityRequest, CapabilityResult, AgentExecutionContext,
SkillRegistryLoader, SkillRouter, RoutingPolicy and CapabilityPolicy (all new in
PR3-03)**. These are typed records/ports or bounded Application services, not new
scientific domains. Route every model/tool/Skill sub-call through the gateway;
no hidden adapter-to-adapter tool dispatch. The only executable capability in
this slice is a deterministic in-process fake without network, process, host
filesystem, secrets or scientific writes.

The roadmap's dependency on PR3-02 means accepted S1 contracts here; requiring S2
would create a cycle. D303-01 must approve the staging below. No execution table,
execution transition or promotion is implemented in PR3-03.

| Later owner | Real adapter / behavior excluded here |
| --- | --- |
| PR3-06 | Constrained sandbox backend and containment evidence. |
| PR3-07 | Compute submit/poll/cancel/reconcile adapter; jobs remain distinct from Run. |
| PR3-08 | Coding contract and coding-specific fake, artifacts and semantic checks. |
| PR3-09 / PR3-10 | Primary API coding adapter / explicitly deferred alternate. |
| PR3-12 / PR3-13 / PR3-14 | API model use for analysis / critique / independent review, respectively; each owning row requires provider intake. |
| PR3-17 | Optional API model for search decisions after its own intake. |
| PR3-19 | Durable dispatch, leases, crash recovery and reconciliation; required before unattended external dispatch. |
| PR3-03, separately authorized follow-up | Optional real tool/MCP adapter, as permitted by its roadmap row; absent from this fake contract. No other roadmap row assigns a standalone general model backend: name an owner and approve scope before adding one. |

**No subscription CLI (including Codex/agy) may be used as an LLM backend for
product features. Every real provider is API-based.** A development harness is
not a product provider. No real model, coding, compute or MCP provider, SDK,
queue or dependency is introduced here. No memory store, scientific promotion,
Run lifecycle change, external effect, self-install or autonomous authority.

## 3. Invariants and admission

1. Human and Agent callers use the same Application service. Authenticate and
   authorize current project access before protected existence or conflict
   disclosure. A role, tool description, prompt, Skill instruction, model choice
   or checkpoint never grants tool permissions. A0–A3 are ceilings, not authority.
2. Policy is an immutable project-scoped exact allow/deny list. Match capability,
   capability revision, operation, adapter revision and parameter-schema digest;
   no wildcard, prefix, regex or fallback provider. Deny overrides allow; absence
   denies. Empty policy permits nothing. Network, filesystem, compute and external
   effects are denied in this slice, even if a description asks for them.
3. Resolve existing `agent_versions.tool_policy_version` to exactly one policy
   in that project. Compare its pinned capability-set digest with existing
   `capability_set_hash`; compare the effective manifest/policy pins too. Do not
   rewrite an AgentVersion to attach a policy. Missing/ambiguous binding denies.
   Current `agent_availability` must be ACTIVE for new admission.
4. Routing takes the intersection of phase, current authority, project disclosure,
   exact policy, pinned registry and task safety. Freeze the selected Skill,
   strategy, adapter, schemas and effective policy digest in invocation material.
   Tool descriptions are untrusted data and grant **no permissions**. Reference-only
   Skills cannot execute. Intake reviews revision, license, scripts, transitive
   capabilities, data exposure and rollback; retain approved immutable pins.
5. Reject attempts to install tools, change governing files, substitute a pin or
   weaken the same execution's policy. A changed registry/policy needs fresh
   owner review and a new version; existing history stays unchanged. PR3-20 owns
   evaluation, not permission to activate an unreviewed tool.
6. Validate bounded typed parameters before dispatch. Resolve exact frozen inputs,
   project entitlement and owning hashes; no live/current/latest dependency and
   no generic target-type/ID or JSON provenance. Output is candidate material;
   success means the capability completed, never that a scientific claim is true.
7. Reserve worst-case usage before action through PR3-04. Include retries, failures
   and unknown outcomes. Unknown outcome retains full charge; timeout is not a
   refund or permission to redispatch. No caller-supplied authoritative usage.
8. Invocation outcome is distinct from AgentExecution and Run. No status mapping
   automatically creates/finishes a Run, promotes a candidate or grants Approval.
   Failed/cancelled/unknown calls and their history remain visible.

### 3.1 S2 reliance and staging

Before S2 exists, persist **CONTRACT_FAKE (new in PR3-03)** invocations owned by an
existing task and exact AgentVersion, admitted only by an injected nonserializable
fake-consumer capability. Public callers cannot set this mode or obtain the
capability. These calls exercise gateway/accounting contracts only; tasks remain
in delivered planning states and `execution_enabled` remains false. Never store
an unresolved execution UUID, dummy execution or fabricated FK.

**agent_execution_instances (new in PR3-02-S2)** and its concrete task/project/
version-consistent invocation FK are added by S2 before any Agent execution can
invoke a tool. S2 adds a separately constrained execution mode; historical fake
rows stay explicitly fake and unlinked, never backfilled as executions. This
staging is a proposed owner decision, not an already approved architecture change.

S2 may rely on the accepted typed gateway port, immutable policy lookup and pin
validation, same-project typed refs, admission/settlement atomicity, replay-safe
invocation identity, persisted outcomes/history and PR3-04 charge linkage. It must
supply verified execution context, enforce the concrete execution FK and mode,
and prove start/pause/stop/promotion integration under its own pack. It may not
rely on a provider, worker, automatic retry, external cancellation, real containment,
scientific validation or promotion from PR3-03. Missing context or any prerequisite
fails closed. No fixture-only production bypass enables S2.

## 4. Commands, queries, DTOs and outcomes

All identifiers and fields in this proposal table are **new in PR3-03**. These
are Application operations; HTTP/CLI never instantiate adapters or repositories.

| Contract | Closed material / behavior |
| --- | --- |
| register_agent_tool_policy | Verified Human OWNER; task-scoped command envelope creates project-scoped immutable policy and exact permission rows; does not bind/revise an AgentVersion. |
| request_capability_invocation | Exact task, optional step, AgentVersion, policy, capability/operation/adapter pins, schema digest, typed input set, parameters digest and retained parameter ArtifactVersion; trusted fake consumer only. Atomically save REQUESTED, reservation, receipt and event. |
| start_capability_invocation | Expected task and invocation revisions, invocation ID; recheck current admission and reservation, atomically save RUNNING. Only then execute the fake outside the transaction. |
| finish_capability_invocation | Invocation ID and revisions, typed result, trusted usage, output refs, sanitized existing error if applicable. Atomically settle and save outcome/event; permitted bookkeeping after stop. |
| get_capability_invocation / list_task_capability_invocations | Entitled immutable saved facts, refs, events, charge IDs and outcomes; list ordered by creation time/ID. Current availability/safety projections are separately labeled. |
| get_agent_tool_policy | Exact policy version/digest, permissions and intake pins, under current project read entitlement. |
| GatewayCommand / GatewayCommandResult | Project/task/command IDs, expected task revision, closed operation arguments; result includes saved receipt, policy/invocation/event/reservation/settlement IDs as applicable, task/invocation revisions and replay flag. |
| CapabilityGateway.invoke | CapabilityRequest plus trusted AgentExecutionContext returns CapabilityResult; orchestrates the three invocation commands, never holds a transaction across the fake call. |
| CapabilityRequest / AgentExecutionContext / CapabilityResult | Request contains exact pins, refs and typed bounded arguments. Context carries verified caller, project/task/optional step/version, immutable harness pins and injected admission capability; S2 adds exact execution context. Result contains invocation ID, outcome, typed refs, trace ArtifactVersion if present, trusted ResourceVector and sanitized error. |

Policy material (**new in PR3-03**): project, exact version token, permission
set, denied set, capability-set digest, maximum tool calls, maximum parallel
invocations, deny-only filesystem/network/compute/external-effect settings,
approved registry manifest ArtifactVersion/hash, creator/time/content hash.
Use positive finite call/parallel caps, recommended 50/1; count admitted attempts,
including failed and unknown, and unreconciled active calls. This tool limit is
not a new PR3-04 resource dimension. Model/search/code usage also charges existing
`ResourceVector` dimensions according to the pinned operation classification;
no fake scientific Run increments `experiment_runs`.

Invocation lifecycle (**new in PR3-03** literals): REQUESTED → RUNNING →
SUCCEEDED / FAILED / UNKNOWN_OUTCOME / CANCELLED. REQUESTED may cancel before
start with proven zero usage; post-start cancellation requires confirmed outcome,
otherwise UNKNOWN_OUTCOME. Terminal material is immutable. Unknown reconciliation
is a new attributable event with one eventual settlement, preserving the original
unknown outcome and full charge until resolved. No second final settlement.
A dispatch failure proven before action is FAILED, not success. A new retry is a
new linked invocation and reservation after policy admission; same-command replay
never reexecutes. Crash between start and result is unknown, never blindly retried;
PR3-19 later owns automated recovery.

Keep existing `TaskCommand`, `SafetyCommand` and accepted hash vectors unchanged.
The new envelope includes authenticated actor, project/task/command IDs, expected
revisions, operation, all normalized arguments/defaults/NULLs and pin/ref hashes.
Use existing `canonical_json_bytes`, `sha256_canonical_json` and
`sha256-cjson-v1`: NFC text, lowercase UUIDs, canonical exact decimals, sorted
set-valued refs/permissions, duplicate rejection, no NaN/infinity/unknown fields.
Exclude generated IDs, clock times and transport correlation fields from request
material. Retain parameters as exact versioned artifacts; do not hash an
unretained arbitrary blob. Freeze full examples and fixed vectors in the pack.

## 5. Persistence proposal

All tables/fields described here are **new in PR3-03** unless explicitly existing.
These are runtime Entity/Relation/Event patterns, not scientific truth stores.

| New table | Minimum concrete contract | DO-NOT-ADD-SCHEMA exception reason |
| --- | --- | --- |
| agent_tool_policies | UUID, project FK, version token, digest, typed limits/deny settings, manifest ArtifactVersion FK/hash, creator FK, UTC time; unique project/version and project/ID. | Existing scientific entities do not represent immutable exact runtime permissions. |
| agent_tool_policy_permissions | Policy/project composite FK, exact capability/version/operation/adapter/version/schema digest, typed allow/deny; unique complete permission key. | Relation rows enforce exact permissions without JSON policy semantics. |
| capability_invocations | UUID, project/task composite FK, optional same-task step FK, AgentVersion/project/actor composite FK, policy/project FK, fake mode, exact tool/adapter/pin hashes, parameter ArtifactVersion FK/hash, reservation FK, optional settlement/trace FKs, revisions/times/status/error, optional same-task retry-parent FK. | Run and task rows cannot represent distinct tool attempts and uncertain tool outcomes. |
| capability_invocation_refs | Invocation/project/task FK, input/output direction, exactly one concrete version FK and owning digest/scheme; unique invocation/direction/family/version. | Typed relations retain exact invocation provenance absent from scientific input relations. |
| capability_invocation_events | Invocation FK, sequence, prior/next outcome, trusted actor/time/reason, existing task receipt FK, optional reconciliation/usage link; unique invocation/sequence and receipt/effect. | Append-only Events retain failed/unknown transitions without rewriting terminal history. |

**No new table** for registry, Skill, routing, fingerprint, parameters, usage,
receipt or Run. Use retained ArtifactVersions, bounded registry services and
existing `budget_reservations`, `budget_usage_records`,
`research_task_command_receipts`, `research_task_events` and concrete receipt/event
links. Add constrained typed result FKs to existing receipts for policy/invocation/
event results; preserve old receipt shapes and replay. Policy registration uses
an entitled planning task as command owner, not scientific ownership.

Refs use the same six concrete targets as existing `research_task_inputs`:
`research_question_versions`, `hypothesis_versions`, `claim_versions`,
`source_versions`, `artifact_versions`, `manuscript_versions`; exactly-one CHECK,
no arbitrary target discriminator. Validate frozen state, scope and hashes with
the owning domain. Outputs here are frozen candidate artifacts, not claims of
new canonical scientific objects. No new generic StructuredValue semantic core.

All FKs RESTRICT; task/project/step, policy/project, AgentVersion/project/actor
and reservation/task consistency enforced in DB, not just Application code.
Index every FK and exact task/time/ID query; bound refs to 256 per invocation,
policy entries to 256, parameter bytes to 64 KiB and summary to 8 KiB (all new
PR3-03 limits). Large logs use ArtifactVersion. Deny ordinary deletion, policy/
permission mutation, input/pin changes after request, terminal rewrites and event/
receipt/settlement mutation. Deferred guards require complete receipt/event/ref/
charge effects and legal transitions at commit, including direct normal-role SQL.

Execution pack must freeze all columns, NULL rules, constraints, indexes, guard
functions, triggers and SQLSTATE mappings before DDL authorization. S2 owns the
later concrete execution FK, never a soft placeholder. Clean/populated upgrades,
one head and downgrade refusal before DDL are mandatory; repairs are forward-only.

## 6. Exact locks, transactions, budget composition and replay

Writes use synchronous PostgreSQL 18, READ COMMITTED, autoflush off. Retain
startup lock_timeout=10s, statement_timeout=30s, connect_timeout=10. Before any
Application SQL (including auth, clock, replay or SET), first statement is the
existing PR3-01/04 inventory, exactly:

```sql
LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts,
claim_versions, claims, hypothesis_versions, hypotheses,
literature_source_project_links, literature_sources, manuscript_versions,
project_memberships, project_role_assignments, projects, publications,
research_question_versions, research_questions, source_versions IN SHARE MODE;
```

Then, in order:

1. Existing `rb_phase2_lock_project(project_id)`.
2. Existing transaction advisory key
   `pr301:command:<project_uuid>:<authenticated_actor_uuid>:<command_uuid>`.
3. Existing transaction advisory key `pr301:task:<task_uuid>`, followed by
   existing S1 keys `pr302:actor:<actor_uuid>` and
   `pr302:version:<version_uuid>`. Use existing
   `pg_advisory_xact_lock(hashtextextended(:key,0))` for each key, with canonical
   lowercase UUID text. Do not create a parallel availability namespace.
4. `research_tasks` by ID FOR UPDATE, then `research_task_steps` by ID FOR UPDATE;
   read dependencies by predecessor/dependent and both input tables by ID.
5. Existing safety rows in delivered order: `budget_reservations`,
   `budget_usage_records`, `checkpoint_policies`, `checkpoint_policy_dataset_scopes`,
   `checkpoint_policy_metric_scopes`, `execution_budgets`, `human_checkpoints`,
   `termination_policies`; ascending primary key, mutable checkpoints FOR UPDATE.
6. Existing `agent_availability` by version FOR UPDATE; immutable `agent_versions`
   read under the version key. Proposed rows in exact order: agent_tool_policies,
   agent_tool_policy_permissions, capability_invocations, capability_invocation_refs,
   capability_invocation_events, each by primary key; only mutable invocation row
   needs FOR UPDATE. No new advisory key after row locking. No SHARE on writable
   task/agent/policy/invocation tables and no table-lock upgrade.

After **every** blocking wait, check current read entitlement and look up the
original receipt. Identical hash returns its saved result **before** write-role,
state, availability, expiry, budget or CAS checks; changed hash conflicts. If no
receipt, freshly recheck credentials, membership/role, scope/archive state, DB
time, policy/pins, exact hashes, required checkpoints and budget before mutation.
Never disclose saved results without current read entitlement. Final dispatch
admission is serialized against stop/availability changes; an admitted finite fake
may finish after stop, but no subsequent call is admitted. Settlement remains
bookkeeping after stop, not new spend.

Each Application command is one transaction. Add an **in-UoW trusted accounting
composition seam (new in PR3-03)** around existing PR3-04 rules; do not invoke
`TaskSafetyService.execute` inside another UoW. Preserve its nonserializable
`FakeConsumerCapability` protection; no JSON flag, Agent constructor or public
reserve/settle permission. Request saves reservation and invocation together;
finish saves settlement and outcome together. Increment task revision once,
write one receipt/event with concrete result links and force deferred constraints
before commit. Denial rolls all effects back. Recompute tool caps under the same
project/task locks, not an unlocked query. No duplicate usage ledger or cap reset.
An exact-cap reservation that succeeds may persist a sticky stop; the reserved
operation can start once against that reservation despite its own recorded cap
exhaustion; any additional stop or current revocation must block it. Freeze this
distinction from a fresh reservation in the pack.

Registry/artifact verification happens before locking against retained bytes;
recheck DB pins under locks. No provider, filesystem, ArtifactStore or cancellation
I/O under locks. Fake execution occurs between start commit and finish command.
Only 40001/40P01 allows at most three total fresh whole transaction attempts with
identical material and fresh authorization. No automatic retry on timeout.
Uncertain commit: formal receipt lookup using the original identity; never assume
rollback or issue a new command UUID.

All queries and explicit replay lookups call existing `begin_formal_read` before
SQL: one REPEATABLE READ READ ONLY snapshot, autoflush off, no SHARE/advisory/row
locks, writes, nested session or second transaction. Entitlement, policy, refs,
usage and history come from that snapshot. Reads neither repair unknown outcomes
nor promise visibility of a later revocation. Use snapshot time for projections;
mutations sample fresh DB time again after waits.

## 7. Existing errors and required future tests

No new ErrorCode. Preserve existing transport mappings and sanitized envelopes.

| Existing ErrorCode | Gateway use |
| --- | --- |
| VALIDATION_ERROR | Closed shape, bounds, duplicate refs, malformed parameters. |
| AUTHENTICATION_REQUIRED / FORBIDDEN | Missing trusted principal / entitlement, tool denial or fake capability missing. |
| NOT_FOUND | Entitled exact task, policy, invocation or reference absent. |
| INVALID_STATE_TRANSITION | Missing safety/S2 prerequisite, stop, blocked checkpoint, invalid lifecycle. |
| ADAPTER_UNAVAILABLE / ADAPTER_VERSION_MISMATCH | No admitted fake adapter / mismatched exact pin. |
| IMMUTABLE_RECORD | Policy, terminal material or history mutation. |
| CONCURRENT_MODIFICATION / IDEMPOTENCY_CONFLICT | Stale revision or bounded database conflict / changed material under same command identity. |
| VERSION_NOT_FROZEN / FROZEN_REFERENCE_REQUIRED | Unfrozen input / unresolved live dependency. |
| PROVENANCE_CLOSURE_VIOLATION / REFERENTIAL_INTEGRITY_ERROR | Exact hash contradiction / persisted concrete FK contradiction. |

A failed capability is a persisted outcome, not an HTTP success assertion about
science. Transport failures and sanitized domain errors remain distinct from
UNKNOWN_OUTCOME. Do not invent budget/policy/provider error enums. Any needed
new code requires a named owner decision and compatibility review first.

Future tests, **not executed for this draft**:

| Layer | Required evidence before implementation acceptance |
| --- | --- |
| Unit/contracts | Exact allow/deny matrix; descriptions/injection grant nothing; pin/schema mismatch; closed DTO/hash vectors; unchanged old vectors; caps at below/equal/above; routing/ref-only/self-modification denials; unknown and retry accounting. |
| Application/fakes | Common caller boundary; only trusted fake admission; reserve/request and settle/finish roll back atomically; no nested UoW; cancelled/failed/unknown history; replay does not call fake; stop versus already reserved start; no task execution/promotion enabled. |
| PostgreSQL 18 constraints/migration | Clean and populated upgrade from 0079 or intervening sole head; composite FKs, exact-one refs, immutable material/events/receipts, direct SQL guards, missing effects, deferred multi-flush checks, forward repair and downgrade refusal. No SQLite. |
| PostgreSQL concurrency/replay | Observe exact first SHARE and all keys/row order; two tasks sharing version versus availability writer; last budget unit and parallel slot races; stop/checkpoint/revocation during actual waits; replay before stale CAS/state/expiry after every wait; lost/uncertain commit; bounded retries/timeouts; one coherent lock-free formal read. |
| Architecture | No agent/vendor direct DB path, no real SDK/process/network, no description-based authority, no Run/outcome conflation, no fake execution UUID; S2 absent/disabled fails closed. |
| Later integration | S2 supplies concrete FK/context and execution tests; PR3-19 supplies crash recovery; real adapter owners prove containment/cancellation/overshoot. Fakes do not establish those gates. |

The future execution pack must name exact static/unit/architecture/PostgreSQL
commands, counts, failures/skips and environment. Independent review uses specs,
diff and evidence; open P0 BLOCKER or P1 MAJOR prevents acceptance. This draft
runs no tests and claims no implementation or gate PASS.

## 8. Existing identifier anchors and authoring verification

| Existing names | Delivered source |
| --- | --- |
| 0077_research_task_graph; task/input/event/receipt tables; TaskCommand | migrations/versions/0077_research_task_graph.py; src/researchbase/agent_runtime/application/contracts.py |
| 0078_task_safety_policies; safety tables; SafetyCommand, ResourceVector, TaskSafetyService, FakeConsumerCapability | migrations/versions/0078_task_safety_policies.py; src/researchbase/agent_runtime/application/safety_contracts.py, application/task_safety.py, domain/task_safety.py, ports/task_safety_repository.py |
| 0079_agent_identity_versions; agent_versions, agent_availability, tool_policy_version, capability_set_hash, pr302 keys | migrations/versions/0079_agent_identity_versions.py; src/researchbase/persistence/agent_version_repository.py |
| SHARE inventory, pr301 keys, rb_phase2_lock_project | src/researchbase/persistence/research_task_repository.py |
| begin_formal_read | src/researchbase/persistence/uow.py |
| canonical_json_bytes, sha256_canonical_json; ErrorCode | src/researchbase/foundation/canonical_json.py, hashing.py, errors.py |

Paths sharing a source directory above are relative to that directory. Existing
identifiers must be checked with focused `rg` across src/, migrations/, tests/
and docs/; a name appearing only in a proposal is not a delivered API. New names
are proposals explicitly labeled above. Authoring verification checks links,
identifier existence, whitespace and single-file scope only. Unit, architecture
and PostgreSQL suites: NOT RUN under the explicit documentation-only instruction;
the loop's later checks provide separate evidence.

## 9. Owner decisions with recommendations

| Decision — new in PR3-03 | Recommendation requiring explicit owner approval |
| --- | --- |
| D303-01 — break dependency cycle | Accept S1 + PR3-04 as this fake slice's prerequisites; permit only explicitly fake task/version-owned invocation records. S2 adds concrete execution FK/mode before execution; no soft placeholder or retroactive fake attribution. |
| D303-02 — schema | Approve the five pattern tables with §5 reasons and constrained receipt extensions. Freeze complete DDL/guards/hash vectors in the execution pack before implementation. |
| D303-03 — policy and routing | Exact immutable deny-by-default policies; 50 calls/1 parallel default; bounded retained registry; descriptions never grant permissions; no same-execution harness weakening. |
| D303-04 — accounting and locks | Approve trusted in-UoW reuse of PR3-04 accounting, exact lock recipe and atomic receipt effects; preserve replay before state/CAS after every wait. Resolve any lock-protocol change through review rather than inventing a competing key. |
| D303-05 — activation | Fakes only. Optional real tool/MCP follow-up needs separate authorization/intake; real models belong to the named consuming rows. Subscription CLI backends remain prohibited; no new ErrorCode is proposed. |

Owner approval of this contract alone is not implementation authorization.
