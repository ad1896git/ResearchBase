# PR3-02 AgentVersion / Execution contract

Status: APPROVED by owner 2026-10-21 (ADR-0023). PR3-02-S1 AUTHORIZED for implementation after its execution pack passes two director reviews; PR3-02-S2 not yet authorized.

## Start here

Read AGENTS.md, architecture 01 → 02 → 03 → 08 → Phase 3 specification 06 →
Harness specification 09, then the authorities below. This is a documentation-only
proposal. Approval of the roadmap does not authorize this PR's implementation.

PR3-01 is delivered: migration `0077_research_task_graph`,
`src/researchbase/agent_runtime/`, and its contract freeze are the baseline.
The freeze pack's historical statements that these objects are absent are no
longer checkout facts. A future migration must follow 0077 at **0078+**, reconcile
any intervening migrations, and retain one head; never edit 0077. S2's migration
number follows whatever head exists when S2 is authorized; do not reserve 0078
for S2.

**Naming rule:** every proposed table, column, DTO, command, query, key, hash
material and diagnostic label defined below is **new in PR3-02**, including names
already present as concepts in architecture documents. Existing implementation
identifiers are explicitly inventoried in §10. SQL isolation levels, lock modes
and SQLSTATEs below are PostgreSQL primitives, not proposed repository identifiers.
No code, DDL, dependency, test or other document is changed by this proposal.

## Slices

This draft retains the full contract but assigns implementation and acceptance to
two separately authorized slices. Promotion requires a SUCCEEDED execution;
implementing it while transitions remain denied would leave untested dead code.

| Slice | Prerequisites and assigned content | Owner decisions required (§9) |
| --- | --- | --- |
| **PR3-02-S1** | Can follow accepted PR3-01 directly. §4 `provision_project_agent`, including AQ-S3-08 closure through positive B02 G2 AGENT Application evidence; §5 `register_agent_version`, `change_agent_availability`, AgentVersionDTO, `get_agent_version` and their command results; §6 `agent_versions`, `agent_availability`, `agent_availability_events` and `agent_command_receipts` for these three operations; §7 HarnessManifest value definition and S1 transaction inventory. | D302-01 and D302-02; D302-05 for S1's four tables, receipt links and reduced SHARE inventory only. |
| **PR3-02-S2** | Only after PR3-03 (gateway) and PR3-04 (policies) are accepted. §5 `create_agent_execution`, `transition_agent_execution`, `promote_agent_candidate`, execution/promotion DTOs and queries; §6 `agent_execution_instances`, `agent_execution_events`, `agent_promotion_records`, `agent_promotion_outputs`, atomic promotion composition and outputs; extend receipts with these operations and typed result FKs; §7 execution harness binding and S2 transaction inventory. | D302-03 and D302-04; D302-05 for the remaining four tables, receipt extensions and S2 SHARE recipe; preserve accepted D302-01/02 contracts. |

§§1–3 supply shared authority, scope and invariants, applied to each slice's
objects. §§5–8 share DTO/envelope, persistence, transaction, error and replay rules
only for the assigned operations. In §7, define/validate the manifest value in S1;
its execution FK, saved digest and admission binding belong to S2. §9 acceptance
cases split on the same object/operation boundary: S1 proves identity, versions,
availability, manifests and their receipts/races/migration; S2 proves execution
lifecycle, atomic promotion, typed outputs and their receipts/races/migration,
including positive SUCCEEDED-to-promotion coverage with accepted gateway/policies.
§10 is shared reference/authoring evidence. S1 adds no execution/promotion tables,
commands or placeholder receipt FKs, and does not use disabled transitions as
positive coverage. S2 extends the accepted S1 schema in a migration following
whatever head exists then, retaining one head and never editing accepted migrations.

## 1. Authority

| Authority | Binding effect |
| --- | --- |
| [Architecture 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), [02 A1–A4](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), [03 §4](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md), [08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md) | Immutable versions/history; separate availability; concrete provenance FKs; atomic promotion; common Application boundary. Addendum corrections override older examples. |
| [Approved roadmap](PHASE3_Roadmap_DRAFT.md), PR3-02 row and schema allocation | Own version, availability, execution, typed promotion and fingerprint binding; identity gap disposition. Later PRs own invocation, policy, context, workers and providers. |
| [ADR-0021](../architecture/adr/ADR-0021-tdg3-phase3-technology-decisions.md) | Native runtime, no new broker/framework; typed atomic promotion; separate PR authorization; fake adapters until provider intake. |
| [ADR-0022](../architecture/adr/ADR-0022-pr3-01-policy-staging-input-layout.md) | Policy bindings absent until PR3-04; no executable task before enforced policies; no invented policy UUIDs. |
| [06 §6, §6.1, §6.2 and §85.4](../architecture/06_Phase3_Development_Specification_v1.1_Harness_Integrated.md) | Version material and per-attempt execution provenance; immutable effective harness binding. Registry separation of availability controls the older §6.1 status example. |
| [Harness 09 §17](../harness/09_Harness_Integration_Specification_v1.0.md) | Fingerprint is a manifest/value, not a new scientific entity. |
| [PR3-01 freeze](../phase3/PR3-01-contract-freeze.md), delivered migration/source | Preserve planning commands, frozen inputs, receipts and disabled execution; match transaction/replay discipline. |
| [AQ-S3-08](B30S3_Architecture_Questions_2026-10-20.md) | Close the missing bound-Agent Application path; no SQL-forged actor type, subject binding or membership. Acceptance of this draft alone does not close the evidence gap. |

## 2. Scope and exclusions

Propose immutable **AgentVersion (new in PR3-02)**, separate **AgentAvailability
(new in PR3-02)**, attributable **AgentExecutionInstance (new in PR3-02)** and
immutable **AgentPromotionRecord (new in PR3-02)**. Include identity enrollment,
closed DTOs, lifecycle history, replay receipts, typed targets and harness manifests.

No scheduler, lease, gateway, CapabilityInvocation implementation, provider,
sandbox, working-memory engine, tool-policy registry, budget/checkpoint schema or
scientific ownership change. Run remains the existing scientific execution.
**CapabilityInvocation (new in PR3-03, excluded here)** will represent a tool call;
one Agent execution can later have many such calls and can produce zero or many
scientific objects. An execution succeeding never proves a Run succeeded.

PR3-02-S2 may store CREATED execution intent for a sealed PLANNING task. It must not
advance the task/steps or start work while PR3-01's execution gate is closed.
Lifecycle/provenance interfaces are defined here for S2; their positive running
and promotion cases require accepted PR3-03 gateway and PR3-04 policy integration
before S2 implementation. No temporary switch or fixture-only production bypass
opens that gate.

## 3. Invariants

1. Agent identity is an existing `actors` row of existing `ActorType.AGENT`,
   resolved from a proven, live subject binding. A role, version ID, request body
   or human credential cannot select or impersonate an Agent principal.
2. Version content is immutable from insertion. Availability changes never change
   its hash. RETIRED is final; ACTIVE ↔ DISABLED is allowed. No hard deletion.
3. An execution binds one exact version, its Agent actor, project, task, optional
   same-task step, frozen input digest and effective harness manifest before work.
   These fields never change. Terminal material, events and receipts are immutable.
4. Current authority and ACTIVE availability admit new starts. Disabling/retiring
   blocks starts, not entitled history reads. Existing attempts retain their
   original material; a disable is not permission to erase them or silently kill
   an external process. Later cancellation/recovery must record actual outcomes.
5. Human confirmation never erases producer identity. Promotion records producer
   execution separately from the authenticated promoter and exact canonical target.
6. Every admitted PR3-02 promotion and canonical write commits together. Failure of
   either rolls both back. No later attach command, generic target locator, direct
   Agent repository access, autonomous freeze or approval bypass.
7. Historical versions remain readable after retirement, supersession or credential
   revocation, subject to the reader's current entitlement. Never invent missing
   historical executions, fingerprints, policies or scientific hashes.

## 4. Real identity binding: AQ-S3-08 disposition

Extend existing `Phase2IdentityService` through **provision_project_agent (new in
PR3-02)**, an additive operation. Do not relax HUMAN-only legacy enrollment,
bootstrap, project ownership or B03 admission. Existing `ProvisionActor` remains
HUMAN provisioning. `resolve_bound_subject` needs an explicit AGENT path for proven
MTLS_URI subjects; `resolve_local_binding` remains the local HUMAN bootstrap path.

The new operation takes an authenticated HUMAN project OWNER, independently
verified subject, operator attestation, requested fresh actor ID, display name,
project and command ID. Recommend **MTLS_URI only**, dedicated to the Agent;
reuse existing `VerifiedSubject`, `ProvisioningAttestation`, subject-credential,
operator and attestation verifier boundaries. The trusted adapter must verify
possession, deployment, subject, credential, actor ID and owner-approved enrollment
intent; its proof must bind those values and the command/project. A body-supplied
principal or unverified URI is never evidence. No fallback to the owner's OS_UID.
A trusted Agent subject resolver/verifier implementation is **new in PR3-02**;
there is no claim that a deployed mTLS adapter already exists. Without configured
proof verification, fail closed. Do not add credentials to the repository.

In one transaction create a fresh AGENT actor, ACTIVE subject binding with existing
PROVISIONED event, ACTIVE project membership with existing PROJECT_ENROLLMENT event,
and RESEARCHER assignment with existing ASSIGNED event. Preserve the existing
binding uniqueness, proof fields, temporal intervals and owner-coverage guards.
Return exact IDs, not secrets. No OWNER/APPROVER grant or owner-coverage reliance
on the Agent. No reuse/retyping of an existing HUMAN, SERVICE or legacy actor.
Revoke/suspend/end through existing identity commands; reactivation must preserve
the Agent's original RESEARCHER ceiling and never manufacture a new binding.

Recheck owner, operator and subject credentials after waits and immediately before
commit, using advancing database time. Existing HUMAN behavior remains unchanged.
Integration evidence must enroll through this operation, resolve the subject to
existing `VerifiedPrincipal`, and call the existing B02 G2 Application commands.
G2's positive Agent case can close AQ-S3-08 without pretending it is a Phase 3
execution. B03 G4 stays HUMAN-only. Do not retrospectively attach PR3-02 records to
Phase 2 history. Pending trusted-adapter configuration is reported as pending,
not positive Agent evidence.

## 5. Commands, queries and DTOs

All names and fields defined in this section are **new in PR3-02**. DTOs are
immutable and closed; reject unknown fields. Normalize text to NFC, reject blank
required text and malformed UUIDs/digests, and use aware UTC timestamps. Transport
composition must expose the same Application operations to Humans and Agents;
no vendor/framework imports in domain or runtime callers reaching persistence.

Every command envelope contains project, authenticated caller (injected, never
accepted from the body), command ID, operation, arguments and expected revision
where mutable state is touched. Caller supplies stable subject IDs; server creates
history/receipt IDs and timestamps. No command accepts caller-supplied result hashes.

| Operation (new in PR3-02) | Arguments and result / admission |
| --- | --- |
| provision_project_agent | §4 material; HUMAN OWNER plus trusted operator/proof. Returns actor/binding/membership/role IDs. |
| register_agent_version | Version ID, Agent actor ID, role, runtime type, pinned prompt/model/tool-policy identifiers, capability-set digest, frozen configuration ArtifactVersion. HUMAN OWNER registers; creates immutable version plus ACTIVE availability/revision 1. |
| change_agent_availability | Version ID, expected availability revision, ACTIVE/DISABLED/RETIRED, reason. HUMAN OWNER only; writes one transition event and increments revision once. Same-state distinct command is invalid. |
| create_agent_execution | Execution ID, exact version, task, optional step, expected task revision, frozen harness manifest ArtifactVersion. Current OWNER/RESEARCHER; an Agent caller must be the version's actor. Copies verified input hash; creates CREATED/revision 1 without changing task state. |
| transition_agent_execution | Execution ID, expected revision, next status, reason, optional frozen result/trace/memory ArtifactVersion IDs, summary and existing ErrorCode on failure. Denied until executable policies and gateway prerequisites exist. Caller is bound producing Agent or authorized HUMAN controller; no success assertion substitutes for owning-domain validation. |
| promote_agent_candidate | Execution ID, exact B02 capture ID, candidate selector/index, expected execution revision, rationale and closed owning-command arguments. Requires SUCCEEDED producer execution and exact captured candidate artifact. First supported targets are B02 question/hypothesis DRAFT creation only; §6 defines composition. |

**AgentVersionDTO (new in PR3-02)** exposes immutable material/hash and separately
labeled current availability/revision. **AgentExecutionDTO (new in PR3-02)** exposes
binding IDs, saved input/harness/result hashes, status/revision/times, sanitized
summary/error, ordered lifecycle events and execution-enabled prerequisites.
**AgentPromotionDTO (new in PR3-02)** exposes producer, promoter, candidate, policy
basis and concrete target IDs; a DRAFT target has no invented scientific hash.
**AgentCommandResult (new in PR3-02)** returns original receipt/result/event IDs,
resulting revisions and replay metadata; current projections are separately labeled.

Queries **get_agent_version**, **get_agent_execution**, **list_task_executions**,
**get_agent_promotion**, **list_execution_promotions** (each **new in PR3-02**)
use project-scoped exact IDs, stable ID ordering and bounded pages (1–100 rows,
after-ID cursor). Read roles are existing OWNER/RESEARCHER/REVIEWER/APPROVER/VIEWER.
No raw credentials, hidden scratchpads, ORM entities or provider exceptions in DTOs.

Execution transitions (all lifecycle fields **new in PR3-02**): CREATED → RUNNING
or CANCELLED; RUNNING → WAITING_TOOL, WAITING_HUMAN, SUCCEEDED, FAILED or CANCELLED;
either WAITING state → RUNNING, FAILED or CANCELLED. No other transition. Creation
sets creation time only; first RUNNING sets start time once; terminal sets finish
time once. A pre-start cancellation has no start time. FAILED requires an existing
ErrorCode and reason. SUCCEEDED requires frozen result manifest and output digest;
FAILED/CANCELLED retain any available partial result/trace. Terminal is final;
retry means a new execution ID, never an UPDATE of the prior attempt.

## 6. Persistence and atomic promotion

All eight table names and their proposed columns below are **new in PR3-02**.
Use PostgreSQL 18, concrete RESTRICT FKs, UUIDv7 IDs, aware UTC, positive revisions,
indexed referencing FKs and scoped list indexes. No cascade or polymorphic main
chain. Required fields are non-null except those explicitly called optional.

| Proposed table (new in PR3-02) | Minimum material / constraints | DO-NOT-ADD-SCHEMA insufficiency reason |
| --- | --- | --- |
| agent_versions | ID, project/Agent actor FKs, role/runtime literals from 06 §6.1, exact prompt/model/tool-policy identifiers, capability-set digest, configuration ArtifactVersion FK, content hash/scheme, creator/time. Unique ID/project/actor tuple; reject live/latest aliases. Actor type/project access/configuration freeze checked on insert. | Existing Version pattern needs an Agent-owned behavior version; scientific versions cannot own it. |
| agent_availability | Version FK as PK, ACTIVE/DISABLED/RETIRED, revision, changed-by/time; one row per version. | Existing stateful relation pattern separates mutable admission from immutable behavior. |
| agent_availability_events | ID, version FK, sequence, prior/next status, actor/time/reason, receipt FK; unique version/sequence. | Existing Event pattern must retain availability history absent from the current projection. |
| agent_execution_instances | ID, project/task FKs, optional step FK, version/Agent tuple FK, controller actor FK, status/revision, creation/start/finish times; input digest, harness ArtifactVersion FK and digest; optional result/trace/memory ArtifactVersion FKs and output digest, optional sanitized summary/error. Task/project and step/task composite FKs; same-project artifacts. | Existing attempt/record pattern retains Agent provenance that neither Run nor task planning records represent. |
| agent_execution_events | ID, execution FK, sequence, prior/next status, actor/time/reason, receipt FK; unique execution/sequence. | Existing Event pattern retains intermediate/failed attempt history without rewriting terminal provenance. |
| agent_promotion_records | ID, project/task/execution composite FKs, candidate ArtifactVersion FK, B02 capture FK, selector/index/candidate digest, promoter FK/time, owning command identity, promotion mode, optional policy snapshot digest, receipt FK. Unique execution/candidate/owning-operation selection. | Existing immutable Record pattern must bind candidate attribution to the canonical transaction. |
| agent_promotion_outputs | ID, promotion FK, nullable research_question_version_id and hypothesis_version_id concrete FKs, exactly one non-null, optional saved scientific hash. One output per initial promotion, partial unique target indexes. | Existing typed Relation pattern gives promoted targets FK integrity absent from logs/JSON. |
| agent_command_receipts | ID, project/caller/command unique key, operation, normalized request hash/scheme, optional typed actor/version/execution/promotion result FKs, optional binding/membership/role result FKs, resulting revision and time. Operation-specific exact result combinations, never a generic result JSON blob. | Existing receipt pattern is needed for non-task commands; task receipts cannot safely describe identity/version/promotion results. |

Project-scoped versions are the recommended initial limit; cross-project reuse
requires a separately approved access contract. Version hash material contains
project, Agent actor, role/runtime, all pinned behavior identifiers, capability
set digest and configuration version/hash. It excludes ID, availability, creator
and timestamps. Hashes use existing `canonical_json_bytes` /
`sha256_canonical_json` with `sha256-cjson-v1`; NFC normalization occurs first.
Prompt/model/tool identifiers are immutable manifest values, not fake FKs to
future registries. Relevant executable content must be pinned and resolvable.

No execution-input tables: copy the verified PR3-01 task and selected-step typed
inputs into a normalized digest, sorted by owner/type/exact ID with saved hash
and owning hash scheme (including NULL). Their sealed rows remain the concrete
FK source. CREATED execution requires a sealed PLANNING task; later activation
must verify the same digest, task scope and non-cancelled executable state.
Candidate/result manifests are frozen ArtifactVersions. Their bytes may describe
candidates but cannot replace promoted-target FKs or introduce scientific truth.

Database guards reject version/history/receipt/output UPDATE or DELETE, including
no-op edits. Availability/execution projection updates require one same-transaction
receipt and event, exact revision+1 and an admitted transition. Deferred checks
require one initial availability/event per version, one initial event per execution,
and complete operation-specific receipt results. Composite keys enforce execution
actor/version equality and promotion task/execution/project equality. No trigger
acquires advisory locks after row locks. Normal-role SQL cannot commit partial
history or append outputs to a previously committed promotion.

For initial promotion reuse existing `StrategyCandidatePromotionService` B02
validation and DRAFT writes through an **in-UoW composition entry (new in PR3-02)**.
The existing public command signatures/receipt/hash domains remain compatible;
do not call their transaction-opening wrappers from another command. Lock and
validate the capture, selector and adaptation exactly as B02 requires, including
source access and duplicate admission. The execution's result ArtifactVersion
must equal the capture's saved artifact, and its frozen bytes/digest must verify.
The producer cannot be selected by the promoter or guessed from the artifact.

In the SAME UoW write the B02 DRAFT identity/version and admission, then promotion,
typed output and receipt; force deferred checks before committing once. Failures
leave neither side. Scientific DRAFT hash stays NULL under B02. A Human promoter
uses HUMAN_CONFIRMED or HUMAN_CREATED_FROM_CANDIDATE; an eligible Agent uses
AGENT_POLICY with a resolved policy snapshot digest. AUTOMATIC_UNDER_POLICY is
reserved until later policy approval. A0 cannot create canonical state. No existing
standalone attach/legacy promotion route becomes an attribution bypass. Broader
create/revise target families need their owning PR's typed FK and composition
review; no generic placeholder columns now.

## 7. Harness binding and exact transaction order

**HarnessManifest (new in PR3-02)** is a closed, versioned value in a frozen
ArtifactVersion, not a new table/entity. Required material: immutable ResearchBase
and runtime revisions, exact model/profile and prompt revision, AGENTS/config
hashes, strategy revision and ordered effective Skill, Plugin, adapter, Hook and
MCP revision/content-hash entries. Empty collections mean none used; unresolved
material dependencies reject admission. Reference-only libraries stay explicitly
reference-only, never falsely recorded as executable pins. No secrets or mutable
branch/latest locators. Store artifact FK plus byte digest on execution; verify
manifest and artifact digest before admission. A changed effective harness needs
a new execution. Retain bytes/pins sufficient to reconstruct it; reproducibility
identifies inputs, not a promise of identical stochastic output.

Every write uses one synchronous READ COMMITTED UoW. Set connection startup
lock_timeout=10s and statement_timeout=30s before SQL; no earlier SET, authorization,
replay query or advisory lock. The **first Application SQL** acquires SHARE on
the slice's fixed inventory, even for empty inputs and replay, in the stated order
(existing table names).

**S1 inventory (8 tables, ordered):** actor_subject_bindings, actors,
artifact_versions, artifacts, project_membership_events, project_memberships,
project_role_assignments, projects.

| S1 protected table | Why S1 operations need SHARE protection |
| --- | --- |
| actor_subject_bindings | Live caller/OWNER and Agent subject binding, credential revocation and enrollment subject uniqueness. |
| actors | Caller/OWNER and target Agent type/retirement checks; fresh Agent identity insertion. |
| artifact_versions | Exact frozen configuration version, project binding and saved hash for registration. |
| artifacts | Configuration artifact parent identity and project scope. |
| project_membership_events | Membership interval/history evidence used by existing identity role checks and enrollment's initial event. |
| project_memberships | Current OWNER/Agent project entitlement and new Agent membership. |
| project_role_assignments | HUMAN OWNER authorization and the new Agent's RESEARCHER ceiling. |
| projects | Project identity and lifecycle admission for all three commands. |

S1 needs no task-input, literature-source, candidate-capture/admission or promoted
scientific-target SHARE locks. Its manifest value definition adds no write command
or table. Positive B02 G2 AGENT evidence calls existing B02 commands with their
own accepted transaction recipe; it does not broaden the S1 command inventory.
New S1 version/availability/receipt rows use the advisory/row locks and guards below.

**S2 inventory (23 tables, ordered):**

actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions,
claims, hypothesis_versions, hypotheses, literature_source_project_links,
literature_sources, manuscript_versions, project_membership_events,
project_memberships, project_role_assignments, projects, publications,
research_question_versions, research_questions, source_versions,
strategy_candidate_captures, strategy_candidate_sources,
strategy_hypothesis_admissions, strategy_question_admissions.

S2 retains the union of delivered PR3-01 and B02 protected inventories, 23 tables;
fixed even for empty inputs and replay. It protects identity, scope, frozen input
and candidate admission facts. It is deliberately broad; SHARE-to-write upgrades
for enrollment/promotion can deadlock under concurrent arrivals, so no claim of
contention-free operation. Use the bounded whole-transaction retry below and test
these exact races. Do not alter accepted Phase 2 writer ordering in this PR.

Then acquire, in order, skipping locks for objects/operations outside the slice:

1. Existing `rb_phase2_lock_project` for the single project.
2. Command advisory key **pr302:command:<project>:<caller>:<command> (new in PR3-02)**.
3. For enrollment, existing deployment lock via `lock_deployment`, then subject
   advisory key **pr302:subject:<deployment>:<kind>:<subject> (new in PR3-02)**;
   for other operations, skip these two locks.
4. Agent actor advisory key **pr302:actor:<actor> (new in PR3-02)**.
5. If task-bound, existing **pr301:task:<task>** key; then version key
   **pr302:version:<version> (new in PR3-02)** if present; then execution key
   **pr302:execution:<execution> (new in PR3-02)** if present.
6. Promotion only: existing **b02:question:<command>** or
   **b02:hypothesis:<command>**, matching the owning B02 operation identity.
7. Row locks: actors by ID, then task, task steps by ID, availability, execution,
   then applicable B02 admission rows by ID. Absent rows remain protected by keys.

All advisory keys use existing PostgreSQL transaction-scoped
`pg_advisory_xact_lock(hashtextextended(key,0))`; UUIDs are canonical lowercase.
Enrollment's target actor is fresh and belongs to this one project, so it must
not invoke the existing multi-project owner-provisioning lock recipe inside this
UoW. Existing identity commands keep their own recipes. Cross-protocol deadlocks
are retried, never treated as success. New blocking waits require fresh checks.

After all waits, re-read authority, project lifecycle, binding/credentials,
availability, revisions and exact material. Use advancing database time for
expiry, not transaction-start time. Authenticate/authorize before existence,
receipt or conflict disclosure. Entitled exact replay precedes write/state/CAS
checks. Fresh writes require current write authority. Flush canonical dependencies
before records/events/receipt links; defer cyclic receipt/result FKs only until
final completeness checks. Commit once, rollback everything on any failure.

No model, network, subprocess or ArtifactStore I/O under database locks. Read and
verify immutable artifact bytes before the write transaction, then recheck their
frozen database bindings/digests inside it. External effects remain later work.

All queries and explicit replay lookups use existing `begin_formal_read`: **one
REPEATABLE READ READ ONLY snapshot**, autoflush off, no SHARE/advisory/row locks,
second session, writes or repair. Entitlement, reference resolution and history
use that same snapshot. Do not claim observation of a later revocation.

## 8. Existing ErrorCodes and replay

Use existing `ErrorCode` only; reasons are sanitized details, not new public codes.
Retain existing HTTP/CLI envelopes and mappings. Wrong-project access denies
before foreign-object disclosure; NOT_FOUND applies only after entitlement.

| Existing code | Contract mapping |
| --- | --- |
| VALIDATION_ERROR | Unknown fields, bad hashes/literals, duplicate submitted items, missing required material. |
| AUTHENTICATION_REQUIRED / FORBIDDEN | Untrusted principal / missing live entitlement, forbidden self-enrollment, wrong project or actor impersonation. |
| SUBJECT_BINDING_UNPROVEN / SUBJECT_ALREADY_BOUND | Invalid possession/attestation / already-bound identity subject. |
| OWNER_CREDENTIAL_UNAVAILABLE | Required current OWNER credential/authority unavailable during enrollment. |
| NOT_FOUND | Entitled exact object absent. |
| INVALID_STATE_TRANSITION | Closed execution gate, unavailable version, illegal lifecycle or no-op availability action. |
| IMMUTABLE_RECORD | Version, sealed binding, terminal/history/receipt/output mutation. |
| VERSION_NOT_FROZEN / FROZEN_REFERENCE_REQUIRED | Exact artifact exists but is unfrozen / unresolved current/latest reference. |
| PROVENANCE_CLOSURE_VIOLATION / REFERENTIAL_INTEGRITY_ERROR | Saved hash/manifest contradiction / concrete FK or same-task binding violation. |
| DUPLICATE_CONTENT | Different command repeats an already admitted candidate; preserve B02's owning duplicate semantics. |
| IDEMPOTENCY_CONFLICT | Same receipt key with different normalized material. |
| CONCURRENT_MODIFICATION | Stale expected revision, occupied fresh ID, exhausted serialization/deadlock retry, lock/query timeout. |

Request material (**AgentCommandMaterial, new in PR3-02**) has exactly type,
material_version=1, operation, project_id, caller_actor_id, command_id,
expected_revision (explicit NULL for creates), and arguments. Arguments are exactly
the command table's fields, with explicit nullable/default values, canonical UUIDs
and NFC text. Include target IDs, binding proof identity/digest, expected task
revision and owning-command material. Exclude server timestamps/result IDs,
transport request/correlation IDs, raw credentials, computed results and replayed.
Hash using the existing canonical JSON/hash helpers and sha256-cjson-v1. Arrays
representing sets sort by exact type/ID; reject duplicates before sorting. Candidate
index/order and summary text are material. Freeze literal vectors before any
implementation approval; never change existing B02 or scientific hash domains.

Receipt key is project/caller/command. After current read entitlement, matching
hash returns original typed results/events/revisions even after retirement,
archival or stale expected revision; changed material conflicts. Replaying never
creates new output, event, binding or canonical object. Other actors cannot replay
as the original caller. Keep owning B02 replay/duplicate rules intact when the
new composition is used. Archived projects permit entitled history, not new writes.

Retry only SQLSTATE 40001/40P01, at most three fresh whole transactions with the
same IDs/material and renewed authorization; no partial retry. No automatic retry
of permission/state/validation failures or 55P03/57014 timeouts. Lost response or
uncertain commit requires lock-free receipt reconciliation with the same identity;
never infer rollback or mint replacement IDs. Unclassified faults retain existing
sanitized transport fallback; do not expose SQL, constraint text or credentials.

## 9. Required future tests and owner decisions

These are acceptance obligations for separately authorized implementation, **not
executed tests** or evidence of a gate passing:

| Area | Required cases |
| --- | --- |
| Unit/static/architecture | Full lifecycle/availability matrices; terminal rejection; closed DTOs; independent literal hash vectors; fingerprint order/pinning/change detection; common Human/Agent boundary; no runtime ORM/vendor access or new scientific entity. |
| Identity | Application-only enrollment and subject resolution; positive B02 G2 AGENT composition; unchanged HUMAN bootstrap/enrollment; B03 Agent denial; proof/subject/credential mismatch, expiry, revocation, duplicate binding, self-enrollment and role escalation. No actor-type UPDATE fixture. |
| PostgreSQL schema/application | Real PostgreSQL 18, normal-role SQL; strong composite FKs, XOR targets, immutable/no-op UPDATE/DELETE, complete events/receipts, same-transaction canonical/promotion success and forced failure on each side. DRAFT hashes stay NULL. All cross-project/wrong-actor/artifact mismatches reject. |
| Concurrency/replay | Observe first S1 8-table / S2 23-table SHARE before other SQL; actual availability/credential/membership/source-link revoke races, enrollment lock upgrade, promotion upgrade, same candidate/same command races, stale revisions, lost response and uncertain commit. One winner or explicit sanitized bounded failure; no partial history. Read snapshots take no locks. |
| Migration/compatibility | S1 clean/populated upgrade from 0077 or intervening head; S2 upgrade from the then-current head after accepted PR3-03/04 and S1, sole head, unchanged PR3-01/Phase 1/2 IDs/hashes/trace. Forward repair; downgrade refuses before destructive action. Policy-gated operations remain denied until owning prerequisites land; that denial is not positive execution coverage. |

Future verification: existing static commands `.venv/bin/ruff check .`,
`.venv/bin/ruff format --check .`, `.venv/bin/pyright`; focused unit/architecture
and PostgreSQL suites from the implementation pack, including existing
`tests/unit/phase3`, `tests/architecture/test_pr3_01_boundaries.py`,
`tests/integration/phase3`, `tests/integration/phase2/test_b02_identity_boundary.py`
and owning identity/B02 regressions. New test names are to be frozen in that pack,
not cited here as delivered files. Record exact commands, counts, skips and blocked
setup; delegate the full suite to the authorized check loop. No SQLite substitutes.

| Owner decision required | Recommendation / consequence |
| --- | --- |
| D302-01 (new in PR3-02): Agent identity | Approve additive project enrollment and MTLS_URI proof/resolution through the existing identity boundary. Require independent verifier intake and positive Application-only G2 evidence before marking AQ-S3-08 closed. |
| D302-02 (new in PR3-02): version scope/material | Project-scoped immutable versions; separate availability; artifacts/manifests carry pinned behavior. No separate fingerprint or model-policy entity. |
| D302-03 (new in PR3-02): staged execution | S2 only: permit CREATED intent only; nullable start time until first RUNNING. Require PR3-04 policy and PR3-03 gateway integration before start/promotion; no weakening of ADR-0022 or 0077 task checks. Freeze the enabling contract in the owning later pack. |
| D302-04 (new in PR3-02): atomic targets | Start with two B02 DRAFT target families and additive in-UoW composition. Human/Agent promotion modes retain producer identity; other canonical families expand through explicit typed review in their owning PR. |
| D302-05 (new in PR3-02): schema/locking | Admit S1's four pattern-based tables, scoped receipt result links and 8-table SHARE recipe; S2 adds the remaining four tables, execution/promotion receipt links and broad 23-table SHARE recipe; require contention/deadlock evidence. Review exact columns, bounds, indexes, trigger inventory, hash vectors and sanitized error translations in the execution pack before DDL authorization. |

These are recommendations awaiting owner decisions, not implicit approval. No new
ErrorCode is requested. Approval must identify these decisions and a subsequent
execution pack; implementation still requires a separate explicit authorization.
Open P0/P1 findings block acceptance. Stop after the authorized PR's evidence.

## 10. Existing-identifier inventory and authoring evidence

Existing implementation names used above were checked with focused `rg` against
`src/`, `migrations/` and `tests/`; documentary authorities are linked in §1.

| Existing identifiers | Repository evidence |
| --- | --- |
| 0077_research_task_graph; actors, projects and all 23 first-SHARE tables | migrations/versions/0077_research_task_graph.py; src/researchbase/persistence/research_task_repository.py (SHARE_TABLES); src/researchbase/persistence/strategy_candidate_promotion_repository.py (S). |
| pr301:task; rb_phase2_lock_project; b02:question / b02:hypothesis key construction | src/researchbase/persistence/research_task_repository.py; src/researchbase/persistence/strategy_candidate_promotion_repository.py; migrations/versions/0019_phase2_bootstrap_membership.py. |
| Phase2IdentityService, ProvisionActor, VerifiedSubject, ProvisioningAttestation | src/researchbase/application/phase2_identity.py. |
| resolve_bound_subject, resolve_local_binding, lock_deployment; actor_subject_binding_events, project_role_events; PROVISIONED, PROJECT_ENROLLMENT, ASSIGNED | src/researchbase/persistence/phase2_identity_repository.py; migrations/versions/0019_phase2_bootstrap_membership.py. |
| VerifiedPrincipal, MTLS_URI, OS_UID; ActorType.AGENT; Run; ArtifactVersion | src/researchbase/domain/phase2_identity.py; src/researchbase/domain/identity.py; src/researchbase/domain/run.py; src/researchbase/domain/artifact.py. |
| StrategyCandidatePromotionService and B02 public question/hypothesis commands; research_question_version_id, hypothesis_version_id; DRAFT NULL hash behavior | src/researchbase/application/strategy_candidate_promotion.py; src/researchbase/domain/strategy_candidate_promotion.py; tests/integration/phase2/test_b02_identity_boundary.py and test_b02_strategy_admission.py. |
| begin_formal_read; canonical_json_bytes, sha256_canonical_json, sha256-cjson-v1; every ErrorCode in §8 | src/researchbase/persistence/uow.py; src/researchbase/foundation/canonical_json.py; src/researchbase/foundation/hashing.py; src/researchbase/foundation/errors.py. |
| Focused existing test paths in §9 | tests/unit/phase3; tests/architecture/test_pr3_01_boundaries.py; tests/integration/phase3; tests/integration/phase2/test_b02_identity_boundary.py. |

Original draft authoring verification (historical, before this slice revision):
identifier/source inspection, change-scope and trailing
whitespace checks only, plus these static checks (no dependency changes):

| Exact command | Observed result |
| --- | --- |
| .venv/bin/ruff check . | Exit 0; All checks passed! |
| .venv/bin/ruff format --check . | Exit 0; 837 files already formatted. |
| .venv/bin/pyright | Exit 0; 0 errors, 0 warnings, 0 informations (tool also printed a version-update notice). |

Focused authoring inspection used `python3 -` with literal identifier searches
through `rg -l -F <identifier> src migrations tests`: 51 identifiers checked,
zero missing; zero trailing-whitespace lines; exact Status and final newline
confirmed. `git status --short --untracked-files=all` showed only this new file;
`git diff --check` exited 0 (the separate whitespace check covers this untracked file).

Unit, architecture and PostgreSQL tests: **NOT RUN**, per this task's specific
“No tests run” instruction. No pass counts are claimed. This draft does not prove
Agent enrollment, migration safety, execution readiness or Phase 3 gate success.
Only this document is the deliverable; no commit, branch or push.

Slice-revision verification: `.venv/bin/ruff check .` exited 0 (all checks
passed); `.venv/bin/ruff format --check .` exited 0 (837 files already formatted);
`.venv/bin/pyright` exited 0 (0 errors, 0 warnings, 0 informations; separate
version-update notice). `git diff --check` exited 0; only this tracked document
changed, with zero trailing-whitespace lines. Unit, architecture and PostgreSQL
tests remain **NOT RUN** under the specific “No tests run” instruction.
