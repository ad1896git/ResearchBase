# PR3-05 Context Reload / Task Memory Contract

Status: DRAFT — awaiting owner approval; not authorized for implementation

## Start here

Reload permitted canonical facts before each material action. Conversation and
saved task memory are suggestions, never scientific evidence or permission.
Build each response from one database snapshot and exact frozen versions.

This file authorizes documentation only. The roadmap allocates no new schema.
The read contract below is concrete; durable save/replay has an owner blocker
in §9. Do not invent receipt columns, relation tables or a lock upgrade to fill
that gap. No code, migration, dependency, provider or execution is enabled.

## 1. Authority and delivered baseline

Read AGENTS.md and architecture 01, 02, 03, 08, then Phase 3 specification 06,
Harness specification 09 and the applicable freezes in the prescribed order.
Links below identify authority, not additional implementation authorization.

| Authority | Rule used here |
| --- | --- |
| [System architecture](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), [correction addendum](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), [registry](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md), [compatibility](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md) | One scientific owner; exact frozen provenance; addendum A4 permits operational working-memory locators but not soft scientific provenance. |
| [Roadmap](PHASE3_Roadmap_DRAFT.md), PR3-05 row and ownership notes | Context and rebuildable memory artifacts; no new schema; PR3-05 owns promotion validation/context services, not promotion records. |
| [ADR-0021](../architecture/adr/ADR-0021-tdg3-phase3-technology-decisions.md) | Native runtime, fake adapters until API-provider intake; development subscription CLIs are not product backends. |
| [ADR-0023](../architecture/adr/ADR-0023-pr3-02-agent-identity-versions-executions.md) | S1 enrollment/versions delivered; S2 owns executions and atomic promotion. S1 is not execution admission. |
| [ADR-0024](../architecture/adr/ADR-0024-pr3-04-budget-termination-checkpoint.md) | Limits/checkpoints remain authoritative; memory cannot reset budgets or resume stopped tasks. |
| [Phase 3 specification](../architecture/06_Phase3_Development_Specification_v1.1_Harness_Integrated.md), §§17, 26–28, 51–52, 85.5; [Harness specification](../harness/09_Harness_Integration_Specification_v1.0.md) | Separate scratchpad, task memory and canonical facts; project isolation, untrusted content and independent reviewer reconstruction. |
| [PR3-01 contract](PR3-01_ResearchTask_Step_Graph_Contract_DRAFT.md) / [freeze](../phase3/PR3-01-contract-freeze.md); [PR3-04 contract](PR3-04_Budget_Termination_Checkpoint_Contract_DRAFT.md) / [freeze](../phase3/PR3-04-contract-freeze.md); [S1 freeze](../phase3/PR3-02-S1-contract-freeze.md) | Delivered task inputs, safety policy, identity, replay and locking are the baseline; historical statements about absent code are superseded by delivered sources. |

Current migration head is `0079_agent_identity_versions`, following
`0078_task_safety_policies` and `0077_research_task_graph`. PR3-02-S2 execution
and promotion persistence is absent. Do not fabricate an execution ID, backfill
one, claim positive promotion evidence or broaden its two initial target families.
The roadmap's full PR3-02 dependency remains unmet until S2 acceptance.

## 2. Scope and exclusions

Include a typed Application context query; principal/project disclosure checks;
exact task and step input reconstruction; permitted provenance/validity reads;
rebuildable working-memory artifact content; and validation interfaces for later
promotion, gateway and reviewer consumers. Human and Agent callers use the same
Application boundary and return immutable DTOs, never ORM objects.

Exclude provider calls, LLM summaries, subscription CLI backends (including
Codex/agy), vector indexes, cross-project grants, long-term memory entities,
workers, gateway execution, new scientific targets and automatic scientific
freeze/release. Any real provider must be API-based and belongs to separate
roadmap-authorized intake. PR3-05 has no such provider scope.

## 3. Invariants and disclosure

1. Authenticate a trusted `VerifiedPrincipal`; resolve current credentials,
   binding, membership and project role before protected existence, hashes,
   locators, counts or conflict information. Use delivered read roles OWNER,
   RESEARCHER, REVIEWER, APPROVER, VIEWER; writes require OWNER/RESEARCHER and an
   active project. Agent enrollment confers no extra authority.
2. Task, optional step, every expanded source and every artifact must belong to
   the requested project or satisfy its existing owning-domain project-access
   rule. A global artifact with NULL project is not automatically readable.
   Literature access uses existing project links, not global source existence.
   Cross-project memory is denied; do not invent a grant mechanism here.
3. Use `research_task_inputs` and `research_task_step_inputs` as canonical input
   bindings. Preserve exact IDs, owning hashes and applicable hash schemes.
   Never resolve latest/current as a substitute. Historically frozen SUPERSEDED
   versions remain historical inputs; return current snapshot validity separately.
   DRAFT scientific objects are excluded from this slice. Candidate artifacts
   are explicitly separate from canonical facts.
4. Authorize every node before traversing or serializing its provenance. An
   unreadable required dependency fails the entire query with sanitized denial;
   no partial graph, foreign identifiers or omission disguised as complete context.
   Stale/invalid facts retain their values and explicit warnings; memory cannot
   repair them or turn an unknown projection into VALID.
5. A saved context is not an authorization token. Reload before promotion, tool
   disclosure and other material actions. Permissions changing after a read's
   snapshot are checked by the subsequent action, not guessed by the reader.
6. Task memory may be lost and rebuilt. Deleting its bytes must not delete task
   history or scientific truth. Rebuild canonical facts from Core; private notes
   may be lost explicitly. Never fabricate equivalent notes or an LLM summary.

## 4. Queries, commands and DTOs

Every API/service/DTO identifier introduced in this section is **new in PR3-05**;
none is claimed delivered. Existing `TaskInput`, `InputType`, `TaskRead` and
`CommandResult` keep their meanings. No transport route is frozen by this draft.
All DTO members described below are **new in PR3-05** projections/envelope fields,
not proposed database columns.

| Interface — new in PR3-05 | Request and result |
| --- | --- |
| `CanonicalContextLoader.load_for_task` / `get_canonical_context_for_task` | Trusted principal, project/task, optional same-task step. Return `CanonicalContext`: task revision/seal, exact typed input IDs/hashes, permitted evidence/trace, explicit validity/closure warnings, exact safety policy IDs and snapshot gate projections. Deterministic ordering by input type/ID and relation identity. No model or artifact write. |
| `get_task_working_memory` | Same scope plus an exact artifact version ID. Return `TaskMemoryRead`: verified bytes/content identity, scope, saved source manifest and an explicitly derived trust label. Reauthorize and reload sources; never return raw bytes merely because the caller knows a hash. No implicit latest selection. |
| `create_working_memory_snapshot` | `SaveTaskMemoryCommand`: trusted principal plus project/task, optional step, command UUID, expected task revision and bounded typed memory content. Return `TaskMemorySaveResult` with exact artifact/version/content identity and saved request identity. Durable replay/persistence is BLOCKED by D1; this is a required behavior, not an available command. |
| `validate_promotion_context` | Exact candidate artifact, admitted target family, task revision and typed canonical references. Return `PromotionContextValidation`: admissibility, exact validated basis and explicit failures. This is a query/validation service, never a canonical write or reusable approval. |

A task memory manifest is a closed, versioned artifact format **new in PR3-05**:
project/task/optional-step locators, format version, creator attribution, exact
source references and hashes, `source_refs`, `trust_level`, `validity_status`,
`project_scope`, plus bounded plan notes, candidate notes and tool summaries.
The four compatibility field names are preserved. Typed source entries use the
six delivered `InputType` families; arbitrary type strings are rejected.
These are operational locators under addendum A4, not formal scientific edges.

Recommended bounds **new in PR3-05**: 1 MiB encoded manifest, at most 256 source
entries, and 8,192 characters per note; reject duplicates, unknown fields,
nonfinite numbers and oversize content before storage. Normalize text to NFC;
canonical lowercase UUIDs and sorted source sets. Store exact UTF-8 bytes using
`canonical_json_bytes`; artifact `content_hash` is SHA-256 of those bytes.
Do not add a hash-scheme column to artifact versions. Saved validity is only an
observation at save time; consumers recompute it from their read snapshot.
No credentials, raw hidden scratchpad, executable instructions or authority claims.
Untrusted source text remains data even when it says to change policy.

## 5. Persistence: no new table

**DO NOT ADD SCHEMA — no new table:** existing Artifact/ArtifactVersion and
ArtifactStore represent immutable, rebuildable bytes; existing typed task inputs
remain the scientific bindings. No separate context, memory, fingerprint or
promotion-validation entity is needed.

Use project-scoped `Artifact` and frozen `ArtifactVersion`; a frozen memory
artifact remains non-scientific. `WorkingMemorySnapshot` is an existing registry
role, not a delivered command or table. Use `ArtifactStore.put_verified`, `open`
and `verify` with exact content identity. A locator is not identity or permission.
Store only derived operational content in its manifest; do not place canonical
facts or formal provenance edges in artifact JSON as a replacement for Core.

The delivered artifact commands create identity, create a DRAFT version and freeze
it in separate transactions. Version creation can move `current_version_id` and
supersede a prior frozen version. They do not supply a principal-scoped atomic
task-memory receipt. Do not nest those commands and call it one transaction.
`research_task_command_receipts` has a closed command set and no memory result FK;
`research_task_inputs` cannot become mutable memory history after plan sealing.
Those are concrete gaps, not permission to add fields or weaken guards.

D1 must settle a schema-free save/replay recipe or seek an explicit owner change
to the roadmap. If a new table, column, relation or constraint is truly required,
STOP that persistence design and implementation; list it for owner decision,
without designing it here. No migration is proposed. Any later approved migration
must be labeled **0080+ (number assigned at integration)**, verify the then-current
sole head, preserve accepted ancestors/hashes and merge serially with siblings.

Artifact I/O must precede write locks, after a scoped read preflight. Verify and
fsync bytes before committing a database reference; a failed DB transaction may
leave unreferenced bytes, never a successful reference to unwritten content.
No new garbage collector or retention mechanism is in scope. Owner-selected save
composition must preserve artifact lifecycle, atomic result attribution and replay.

## 6. Exact transactions, locks and replay requirements

Reads, including explicit replay lookup, call existing `begin_formal_read` before
SQL: **one REPEATABLE READ READ ONLY snapshot**, autoflush disabled, no table,
advisory or row locks, writes, second session or nested transaction. Entitlement,
inputs, source/project links, validity and policy projections use that snapshot.
Exact immutable artifact bytes may be verified locally during the read; no
provider/network fetch or repair write. Missing/corrupt memory is unusable;
canonical context can still be rebuilt without it, with an explicit diagnostic.
A required canonical artifact failure fails the query rather than substituting
memory. Never silently truncate the required input set.

For later composed validation inside an owning command, retain that command's
transaction and lock protocol; do not call this read query to start another UoW.
A prior query result never exempts the writer from fresh authorization or checks.

The delivered task mutation baseline is synchronous READ COMMITTED with startup
lock_timeout=10s, statement_timeout=30s, connect_timeout=10. First Application SQL
is SHARE on this exact sorted 18-table inventory, before authorization SELECT,
receipt SELECT, SET LOCAL, advisory lock, write or autoflush:

actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions,
claims, hypothesis_versions, hypotheses, literature_source_project_links,
literature_sources, manuscript_versions, project_memberships,
project_role_assignments, projects, publications, research_question_versions,
research_questions, source_versions.

Then acquire, in order:

1. `rb_phase2_lock_project(project_id)`.
2. Transaction advisory key `pr301:command:<project_uuid>:<authenticated_actor_uuid>:<command_uuid>`.
3. Transaction advisory key `pr301:task:<task_uuid>`.
4. `research_tasks` by ID FOR UPDATE, then `research_task_steps` by ID FOR UPDATE.
5. Read dependencies by predecessor/dependent, then task/step inputs by ID.
   Safety rows follow PR3-04's exact order: budget_reservations,
   budget_usage_records, checkpoint_policies, checkpoint_policy_dataset_scopes,
   checkpoint_policy_metric_scopes, execution_budgets, human_checkpoints,
   termination_policies. Immutable rows need reads; only checkpoint mutation
   requires its row lock. No advisory lock acquired after row locks.

After **every wait**, revalidate current credentials/read entitlement and look up
saved normalized request material. Exact replay returns the original result
**before** write authority, task state, CAS, archive, expiry or budget checks;
a different hash conflicts. Only an absent receipt proceeds to fresh write
admission, scope/input-hash checks and advancing database time. Do not gate a
successful old replay on the current safety state. Authorization precedes
protected result/existence/conflict disclosure.

**Save lock blocker (D2):** the baseline's SHARE locks include both artifact
tables. A save that subsequently writes them would upgrade those locks; two
such transactions can deadlock. No artifact-store/provider I/O under locks and
no silent narrowing of the accepted inventory. There is no approved write-lock
recipe for the blocked save command. Freeze its complete first-lock inventory,
artifact-writer serialization and mixed legacy-command races before enabling it;
do not advertise the baseline recipe as sufficient for an artifact write.

An admitted save must use one command/one database transaction; on failure roll
back all database effects. Stable normalized request material includes trusted
actor, scope, command identity, expected revision, exact sources and content hash;
exclude generated times/results. Use `sha256_canonical_json` and existing
sha256-cjson-v1 for request material; freeze fixed vectors before implementation.
At most three total fresh attempts for SQLSTATE 40001/40P01 only, retaining command
identity/material and rechecking authorization. No automatic timeout retry.
Reconcile uncertain commits through a fresh formal receipt read, never a new
command UUID or a guess that storage failure implies rollback. D1 must identify
where the exact durable result is recovered; manifest scanning is not assumed
unique or sufficient.

## 7. Downstream consumers and existing errors

`ReviewerContextBuilder` is **new in PR3-14** (named architecturally, not delivered).
It may consume a newly reconstructed permitted canonical context, exact frozen
review target/evidence, relevant specs/diffs and explicitly supplied candidate
artifacts or execution evidence. It must not ingest author hidden scratchpad,
conversation condensations or task memory by default. Use a separate reviewer
execution and independently pinned reviewer configuration when those exist;
never invent execution records on S1. Review promotion remains explicit and
cannot mutate the reviewed scientific target or authorize release.

`CapabilityGateway` is **new in PR3-03** as a product implementation. It may
consume exact context identities and gate projections as inputs, never as an
access token, tool grant or proof of budget reservation. Before dispatch it must
reload/revalidate current principal, project disclosure, applicable tool/data
policy, budget and checkpoints through its owning admission protocol. No secrets
or foreign-project bytes in prompts, logs, error messages or model requests.
A read permission is not permission to disclose to an external provider.

PR3-05 validation supplies no promotion record. PR3-02-S2 must revalidate within
the canonical write transaction and atomically record producer, promoter,
execution and concrete output provenance. `AgentPromotionRecord` is **new in
PR3-02-S2**, not a delivered table. No extra promotion target is admitted here.

Use only existing `ErrorCode` members; no new public code or transport mapping:

| Existing code | Use |
| --- | --- |
| AUTHENTICATION_REQUIRED / FORBIDDEN | Missing trusted principal / unavailable scope, credentials or disclosure authority; sanitized before protected details. |
| NOT_FOUND | Entitled exact object unavailable. |
| VALIDATION_ERROR | Malformed/oversize manifest, unknown fields, corrupt or missing memory bytes. |
| FROZEN_REFERENCE_REQUIRED / VERSION_NOT_FROZEN | Live/unresolved reference / unsealed scientific version. |
| PROVENANCE_CLOSURE_VIOLATION | Owning source/hash/closure contradiction. |
| INVALID_STATE_TRANSITION / IMMUTABLE_RECORD | Save/promotion admission blocked / attempt to rewrite frozen history. |
| CONCURRENT_MODIFICATION / IDEMPOTENCY_CONFLICT | Stale revision or bounded transaction conflict/timeout / reused command identity with different material. |
| REFERENTIAL_INTEGRITY_ERROR | Persisted concrete-reference contradiction. |

Preserve mappings in `api/errors.py` and `cli/errors.py`; do not expose raw SQL,
constraint text, credentials or denied identifiers. New diagnostic text is
**new in PR3-05**, not an error enum. No implementation acceptance is claimed.

## 8. Future tests and authoring verification

These are requirements for separately authorized work, not executed evidence.

| Layer | Required evidence |
| --- | --- |
| Unit/contracts | Closed DTOs/bounds/NFC/deterministic ordering and fixed request hashes; exact frozen and historically frozen inputs; stale/invalid warnings; memory cannot override facts, gate state or evidence; source text cannot change policy. |
| Architecture | Common Application boundary; no Domain ORM/vendor imports, direct agent persistence, provider dependency or subscription CLI backend; reviewer excludes author scratchpad; replacing memory needs no scientific migration. |
| PostgreSQL 18 queries | One lock-free read-only repeatable snapshot across entitlement/input/validity/policy reads under concurrent writers; every expanded source scoped; denied hash/locator guesses; global and foreign artifacts denied; revoked binding/membership and archive behavior. |
| Artifact durability | Verified exact bytes and size; missing/corrupt optional memory versus required input; restart rebuild; partial storage failure; no persisted success to missing bytes; no orphan cleanup deleting referenced history. |
| Save/replay, after D1/D2 | Actual first-SQL trace; mixed planning/safety/identity/artifact writers; after-wait revocation; replay before CAS/state/archive/expiry; same/different material, lost response and uncertain commit; no duplicate artifact/result; atomic rollback; direct normal-role guard and deferred-constraint evidence for any approved persistence change. |
| Later integration | Gateway fresh disclosure/admission; independent reviewer reconstruction; S2 atomic promotion and producer/promoter distinction. Fakes do not prove provider isolation or live execution. |

Existing anchors: `tests/unit/phase3/`, `tests/architecture/test_pr3_01_boundaries.py`,
`tests/architecture/test_pr3_04_boundaries.py`,
`tests/architecture/test_pr3_02_s1_boundaries.py`, `tests/integration/phase3/`,
`tests/test_artifact_store.py`, `tests/unit/domain/test_pr07_artifact.py` and
`tests/unit/test_m2_artifact_durability.py`. Future PR3-05 test identifiers are
not allocated here. Use real disposable PostgreSQL 18, never SQLite.

Authoring verification: inspect identifiers, paths, whitespace and the one-file
scope; run installed static tools only. Unit, architecture and PostgreSQL tests
are **NOT RUN**, following the explicit documentation-only “No tests run” rule.
The loop owns whole-suite evidence. Report exact observed static commands/results
separately; do not copy historical pass counts as current verification.

## 9. Owner decisions with recommendations

| Decision | Recommendation |
| --- | --- |
| D1 — durable save/result allocation; BLOCKER | Keep the roadmap's no-schema allocation. Require a reviewed schema-free replay/attribution design using existing artifacts before approving the save command. Existing task receipts cannot currently express that result, and artifact commands alone are insufficient. If no compliant reuse exists, STOP and request an explicit roadmap/ADR scope change; no new schema is designed here. |
| D2 — artifact-write locking; BLOCKER | Preserve accepted task/identity protocols. Require a separately reviewed save inventory that serializes artifact writers before project/task locks, without SHARE-to-write upgrades; prove mixed-writer races. Do not copy the task recipe and assume it is safe. |
| D3 — first read slice | Approve only the six delivered typed input families, frozen/historically frozen versions, one read snapshot and explicit validity warnings. Expand to DRAFT targets or additional reference families only with a named later contract. |
| D4 — isolation and size | Approve deny-by-default cross-project disclosure, optional unusable-memory diagnostics, exact-version memory reads and §4 bounds. Reviewer reconstruction excludes author working memory. |
| D5 — prerequisites and activation | Full PR3-05 acceptance waits for PR3-02-S2 and PR3-04 plus resolved D1/D2. Read-only work may be separately authorized as a named slice; validation never enables execution/promotion/providers. |

Approval of this draft would approve a contract direction, not implementation.
Resolve blockers and freeze the execution pack before authorizing any write work.

## 10. Existing-identifier source inventory

Every claimed delivered identifier is anchored below; conceptual/new components
are labeled with their owning PR above. Existing paths are repository-relative.

| Existing identifiers | Source |
| --- | --- |
| TaskInput, InputType, TaskRead, CommandResult; six input families | src/researchbase/agent_runtime/application/contracts.py |
| VerifiedPrincipal; OWNER/RESEARCHER and read-role checks; exact frozen input resolution | src/researchbase/domain/phase2_identity.py; src/researchbase/agent_runtime/application/research_task.py |
| SHARE inventory, task tables/input/receipt names and pr301 advisory keys | src/researchbase/persistence/research_task_repository.py; migrations/versions/0077_research_task_graph.py |
| Safety table order and waits | src/researchbase/persistence/task_safety_repository.py; migrations/versions/0078_task_safety_policies.py |
| rb_phase2_lock_project; project/source access tables | migrations/versions/0019_phase2_bootstrap_membership.py; src/researchbase/persistence/research_task_queries.py |
| 0079_agent_identity_versions and its parent | migrations/versions/0079_agent_identity_versions.py |
| Artifact, ArtifactVersion, current_version_id; DRAFT/FROZEN/SUPERSEDED | src/researchbase/domain/artifact.py; src/researchbase/foundation/versioning.py |
| ArtifactStore, put_verified, open, verify | src/researchbase/foundation/artifact_store.py |
| Separate artifact create/version/freeze transactions and store verification | src/researchbase/application/commands.py |
| begin_formal_read; synchronous UoW/startup bounds | src/researchbase/persistence/uow.py |
| canonical_json_bytes, sha256_canonical_json, sha256-cjson-v1 | src/researchbase/foundation/canonical_json.py; src/researchbase/foundation/hashing.py; migrations/versions/0077_research_task_graph.py |
| ErrorCode and existing mappings | src/researchbase/foundation/errors.py; src/researchbase/api/errors.py; src/researchbase/cli/errors.py |
| WorkingMemorySnapshot role and compatibility memory fields | docs/architecture/03_Global_Schema_and_Contract_Registry_v1.0.md; docs/architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md |
