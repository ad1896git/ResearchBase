# PR3-02-S1 contract freeze and execution pack

Status: FROZEN execution pack; passed two director reviews 2026-10-21 (identifier
check: 239 identifiers, 0 mismatches; lock-refinement attribution corrected, ADR-0023
amendment). Implementation AUTHORIZED by the owner (ADR-0023, S1 only). This document
does not claim AQ-S3-08 closure, implementation acceptance or Phase 3 GO.

Authority: [approved contract](../proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md),
**S1 only**, [ADR-0023](../architecture/adr/ADR-0023-pr3-02-agent-identity-versions-executions.md),
and the delivered [PR3-01 pack](PR3-01-contract-freeze.md), especially §3.4.
Read AGENTS.md, architecture 01 → 02 → 03 → 08 → Phase 3 specification 06 →
Harness specification 09 before this pack. ADR-0023 resolves the proposal's
historical “awaiting owner decisions” wording; the two-review condition remains.
For locking, §4 refines contract §7 and ADR-0023 D302-05's uniform S1 SHARE
recipe into per-command modes: enrollment writes identity tables it would
otherwise only SHARE-lock, so two concurrent enrollments could each hold SHARE and
deadlock on the write upgrade. The refinement came from the pipeline's automated
review, not from an owner instruction; the director accepted it and recorded it as
the ADR-0023 amendment of 2026-10-21.

## 1. Baseline and scope

Inspected baseline: `0077_research_task_graph`, parent
`0076_agent_runtime_bootstrap`, and delivered PR3-01 source/tests under
`src/researchbase/agent_runtime/` and `tests/*/phase3/`. PR3-01 pack statements
that these are absent are historical. PR3-04 lands first: NEW migration
`migrations/versions/0079_agent_identity_versions.py`, revision
`0079_agent_identity_versions`, down_revision `0078_task_safety_policies`.
0078 is an expected prerequisite, not an existing checkout identifier. At
implementation time verify accepted PR3-04 evidence and the sole head; if the
head differs, re-parent only. Never edit accepted migrations or their revision
IDs; no branch head or duplicate revision. Downgrade refuses before any DDL or
revision-pointer change, for empty and populated databases. Forward repair needs
separate approval.

Only provision_project_agent, register_agent_version, change_agent_availability,
get_agent_version, their closed values/results, four tables and S1 receipts are
in scope. All identifiers introduced below, including `pr302_` SQL names,
`AgentCommandMaterial`, DTO/command names and proposed paths, are **NEW S1**
unless explicitly labeled existing in §8. SQL built-ins are PostgreSQL primitives.
No execution/promotion table, receipt placeholder FK, worker, provider, gateway,
policy schema, fingerprint entity or scientific ownership change. PR3-04 policy
delivery does not authorize S2 or open PR3-01 execution on its own.

ADR-0023 D302-05 admits four existing architecture patterns: Agent-owned Version
material cannot belong to a scientific version; separate Availability preserves
immutable behavior; Event retains admission history absent from its projection;
Receipt records non-task command results that task receipts cannot represent.
This is the approved DO-NOT-ADD-SCHEMA exception, not authority for another entity.

## 2. Exact table and index DDL

PostgreSQL 18; documentation, not executable work in this change. No new column
on an existing table. No JSON semantic core, DB enum, UUID/time default or
unlisted index. Application supplies UUIDv7 IDs. The receipt INSERT guard supplies
one DB-derived command timestamp per transaction attempt, returned to Application
for every new/changed row's aware UTC timestamp (§4); no client clock is used. PKs
and UNIQUE constraints create B-tree indexes. All FKs are RESTRICT on delete,
NO ACTION on update; only explicitly marked result FKs are deferred. All text
must be NFC before hashing/persistence. CHECKs do not authenticate a principal;
the trusted Application boundary and proof verification remain mandatory.

```sql
CREATE TABLE agent_versions (
  id uuid NOT NULL PRIMARY KEY,
  project_id uuid NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
  actor_id uuid NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  agent_role text NOT NULL CHECK (agent_role IN (
    'planner','research','hypothesis','experiment_designer','coder','debugger',
    'executor','analyst','critic','writer','reviewer','orchestrator','general')),
  runtime_type text NOT NULL CHECK (runtime_type IN (
    'native','langgraph','deepagents','openhands','external_service','other')),
  prompt_template_version text NOT NULL CHECK (
    length(btrim(prompt_template_version)) BETWEEN 1 AND 512
    AND prompt_template_version IS NFC NORMALIZED
    AND lower(btrim(prompt_template_version)) NOT IN ('latest','current','main','master')),
  model_profile_id text NOT NULL CHECK (
    length(btrim(model_profile_id)) BETWEEN 1 AND 512
    AND model_profile_id IS NFC NORMALIZED
    AND lower(btrim(model_profile_id)) NOT IN ('latest','current','main','master')),
  tool_policy_version text NOT NULL CHECK (
    length(btrim(tool_policy_version)) BETWEEN 1 AND 512
    AND tool_policy_version IS NFC NORMALIZED
    AND lower(btrim(tool_policy_version)) NOT IN ('latest','current','main','master')),
  capability_set_hash text NOT NULL CHECK (capability_set_hash ~ '^[0-9a-f]{64}$'),
  configuration_artifact_version_id uuid NOT NULL
    REFERENCES artifact_versions(id) ON DELETE RESTRICT,
  configuration_content_hash text NOT NULL
    CHECK (configuration_content_hash ~ '^[0-9a-f]{64}$'),
  content_hash text NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
  hash_scheme text NOT NULL CHECK (hash_scheme = 'sha256-cjson-v1'),
  created_by uuid NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL,
  UNIQUE (id, project_id, actor_id)
);
CREATE INDEX pr302_versions_project ON agent_versions(project_id, id);
CREATE INDEX pr302_versions_actor ON agent_versions(actor_id, id);
CREATE INDEX pr302_versions_configuration ON agent_versions(configuration_artifact_version_id);
CREATE INDEX pr302_versions_creator ON agent_versions(created_by);

CREATE TABLE agent_availability (
  agent_version_id uuid NOT NULL PRIMARY KEY
    REFERENCES agent_versions(id) ON DELETE RESTRICT,
  status text NOT NULL CHECK (status IN ('ACTIVE','DISABLED','RETIRED')),
  revision integer NOT NULL CHECK (revision >= 1),
  changed_by uuid NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  changed_at timestamptz NOT NULL
);
CREATE INDEX pr302_availability_actor ON agent_availability(changed_by);

CREATE TABLE agent_command_receipts (
  id uuid NOT NULL PRIMARY KEY,
  project_id uuid NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
  caller_actor_id uuid NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  command_id uuid NOT NULL,
  operation text NOT NULL CHECK (operation IN (
    'provision_project_agent','register_agent_version','change_agent_availability')),
  request_hash text NOT NULL CHECK (request_hash ~ '^[0-9a-f]{64}$'),
  hash_scheme text NOT NULL CHECK (hash_scheme = 'sha256-cjson-v1'),
  result_actor_id uuid NULL REFERENCES actors(id) ON DELETE RESTRICT
    DEFERRABLE INITIALLY DEFERRED,
  result_binding_id uuid NULL REFERENCES actor_subject_bindings(id) ON DELETE RESTRICT
    DEFERRABLE INITIALLY DEFERRED,
  result_membership_id uuid NULL REFERENCES project_memberships(id) ON DELETE RESTRICT
    DEFERRABLE INITIALLY DEFERRED,
  result_role_assignment_id uuid NULL REFERENCES project_role_assignments(id) ON DELETE RESTRICT
    DEFERRABLE INITIALLY DEFERRED,
  result_binding_event_id uuid NULL REFERENCES actor_subject_binding_events(id) ON DELETE RESTRICT
    DEFERRABLE INITIALLY DEFERRED,
  result_membership_event_id uuid NULL REFERENCES project_membership_events(id) ON DELETE RESTRICT
    DEFERRABLE INITIALLY DEFERRED,
  result_role_event_id uuid NULL REFERENCES project_role_events(id) ON DELETE RESTRICT
    DEFERRABLE INITIALLY DEFERRED,
  result_agent_version_id uuid NULL REFERENCES agent_versions(id) ON DELETE RESTRICT
    DEFERRABLE INITIALLY DEFERRED,
  result_availability_event_id uuid NULL,
  resulting_revision integer NOT NULL CHECK (resulting_revision >= 1),
  recorded_at timestamptz NOT NULL,
  UNIQUE (project_id, caller_actor_id, command_id),
  CHECK (
    (operation = 'provision_project_agent'
      AND result_actor_id IS NOT NULL AND result_binding_id IS NOT NULL
      AND result_membership_id IS NOT NULL AND result_role_assignment_id IS NOT NULL
      AND result_binding_event_id IS NOT NULL AND result_membership_event_id IS NOT NULL
      AND result_role_event_id IS NOT NULL AND result_agent_version_id IS NULL
      AND result_availability_event_id IS NULL AND resulting_revision = 1)
    OR
    (operation IN ('register_agent_version','change_agent_availability')
      AND result_actor_id IS NULL AND result_binding_id IS NULL
      AND result_membership_id IS NULL AND result_role_assignment_id IS NULL
      AND result_binding_event_id IS NULL AND result_membership_event_id IS NULL
      AND result_role_event_id IS NULL AND result_agent_version_id IS NOT NULL
      AND result_availability_event_id IS NOT NULL
      AND (operation <> 'register_agent_version' OR resulting_revision = 1)
      AND (operation <> 'change_agent_availability' OR resulting_revision >= 2)))
);
CREATE INDEX pr302_receipts_caller ON agent_command_receipts(caller_actor_id);
CREATE INDEX pr302_receipts_actor ON agent_command_receipts(result_actor_id);
CREATE INDEX pr302_receipts_binding ON agent_command_receipts(result_binding_id);
CREATE INDEX pr302_receipts_membership ON agent_command_receipts(result_membership_id);
CREATE INDEX pr302_receipts_role ON agent_command_receipts(result_role_assignment_id);
CREATE INDEX pr302_receipts_binding_event ON agent_command_receipts(result_binding_event_id);
CREATE INDEX pr302_receipts_membership_event ON agent_command_receipts(result_membership_event_id);
CREATE INDEX pr302_receipts_role_event ON agent_command_receipts(result_role_event_id);
CREATE INDEX pr302_receipts_version ON agent_command_receipts(result_agent_version_id);
CREATE UNIQUE INDEX pr302_receipts_availability_event
  ON agent_command_receipts(result_availability_event_id)
  WHERE result_availability_event_id IS NOT NULL;
CREATE UNIQUE INDEX pr302_receipts_enrolled_actor ON agent_command_receipts(result_actor_id)
  WHERE operation = 'provision_project_agent';

CREATE TABLE agent_availability_events (
  id uuid NOT NULL PRIMARY KEY,
  agent_version_id uuid NOT NULL REFERENCES agent_versions(id) ON DELETE RESTRICT,
  sequence integer NOT NULL CHECK (sequence >= 1),
  prior_status text NULL CHECK (prior_status IN ('ACTIVE','DISABLED','RETIRED')),
  new_status text NOT NULL CHECK (new_status IN ('ACTIVE','DISABLED','RETIRED')),
  actor_id uuid NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  occurred_at timestamptz NOT NULL,
  reason text NOT NULL CHECK (length(btrim(reason)) BETWEEN 1 AND 8192
    AND reason IS NFC NORMALIZED),
  receipt_id uuid NOT NULL UNIQUE REFERENCES agent_command_receipts(id) ON DELETE RESTRICT,
  UNIQUE (agent_version_id, sequence),
  CHECK ((sequence = 1 AND prior_status IS NULL AND new_status = 'ACTIVE')
    OR (sequence > 1 AND prior_status IS NOT NULL AND prior_status <> new_status
      AND prior_status IN ('ACTIVE','DISABLED')
      AND new_status IN ('ACTIVE','DISABLED','RETIRED')))
);
CREATE INDEX pr302_events_actor ON agent_availability_events(actor_id);
ALTER TABLE agent_command_receipts ADD CONSTRAINT pr302_receipt_event_fk
  FOREIGN KEY (result_availability_event_id) REFERENCES agent_availability_events(id)
  ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
```

The version's project/actor tuple is the future concrete S2 target; no S2 FK now.
FK project scope of artifacts and receipt result tuples is checked by §3 guards;
do not invent `artifact_versions.project_id`. No unique content hash: distinct
stable version IDs may carry identical behavior. Aliases embedded in locators
(for example a branch URL ending in main) also reject in value validation;
the simple SQL exclusion is only the literal minimum. Runtime literals describe
provenance, not installed adapters or permission to invoke a framework.

## 3. Functions, triggers and frozen invariants

All NEW functions below are PL/pgSQL, invoker rights, fixed
`SET search_path = pg_catalog, public, pg_temp`; no SECURITY DEFINER or writable
session marker. Trigger functions return NEW for admitted immediate writes and
NULL for deferred checks; DELETE/immutable UPDATE raise before effects. They
raise SQLSTATE 23514 with the diagnostic constraint label from §6. Missing
concrete references use native 23503. Explicit normal-role valid DML under the
same lock/receipt protocol must work; SQL alone is not authentication evidence.

### 3.1 Exact trigger inventory

Every row trigger is FOR EACH ROW. There are 14 NEW triggers and one replacement
of an existing binding trigger, not stacked with its old HUMAN-only check. The
last row inventories an existing retained trigger whose function changes.
Existing unrelated identity guards remain installed. There are eight NEW
functions and one narrowly replaced existing function.

| Trigger (NEW unless labeled) | Table / timing | Function |
| --- | --- | --- |
| pr302_receipt_insert | agent_command_receipts BEFORE INSERT | pr302_receipt_guard() |
| pr302_receipt_immutable | agent_command_receipts BEFORE UPDATE OR DELETE | pr302_immutable() |
| pr302_version_insert | agent_versions BEFORE INSERT | pr302_version_guard() |
| pr302_version_immutable | agent_versions BEFORE UPDATE OR DELETE | pr302_immutable() |
| pr302_availability_write | agent_availability BEFORE INSERT OR UPDATE OR DELETE | pr302_availability_guard() |
| pr302_event_insert | agent_availability_events BEFORE INSERT | pr302_event_guard() |
| pr302_event_immutable | agent_availability_events BEFORE UPDATE OR DELETE | pr302_immutable() |
| pr302_receipt_complete_commit | agent_command_receipts AFTER INSERT, CONSTRAINT, DEFERRABLE INITIALLY DEFERRED | pr302_receipt_complete() |
| trg_actor_binding_human (existing name, replace target function) | actor_subject_bindings BEFORE INSERT | pr302_binding_guard() |
| pr302_agent_actor_write | actors BEFORE INSERT OR UPDATE | pr302_identity_insert_guard() |
| pr302_agent_membership_insert | project_memberships BEFORE INSERT | pr302_identity_insert_guard() |
| pr302_agent_role_write | project_role_assignments BEFORE INSERT OR UPDATE | pr302_identity_insert_guard() |
| pr302_agent_binding_event_insert | actor_subject_binding_events BEFORE INSERT | pr302_identity_insert_guard() |
| pr302_agent_membership_event_insert | project_membership_events BEFORE INSERT | pr302_identity_insert_guard() |
| pr302_agent_role_event_insert | project_role_events BEFORE INSERT | pr302_identity_insert_guard() |
| trg_project_membership_event_transition (existing trigger, unchanged timing/target) | project_membership_events AFTER INSERT, CONSTRAINT, DEFERRABLE INITIALLY DEFERRED | rb_phase2_validate_membership_event() (existing function, narrowly replace body below) |

Exact replacement DDL:

```sql
DROP TRIGGER trg_actor_binding_human ON actor_subject_bindings;
CREATE TRIGGER trg_actor_binding_human BEFORE INSERT ON actor_subject_bindings
  FOR EACH ROW EXECUTE FUNCTION pr302_binding_guard();
```

Do not replace existing `rb_phase2_guard_human_actor()` itself: existing
`trg_actor_challenge_human` must keep calling it and keep legacy challenges
HUMAN-only. No new identity lifecycle deferred triggers or task triggers.

Existing `rb_phase2_validate_membership_event()` currently requires the
PROJECT_ENROLLMENT member to be projects.created_by. An enrolled Agent is not
that Human. Migration 0079 must CREATE OR REPLACE this existing function, preserving
every existing branch and error (`ck_membership_event_transition`), changing
only the PROJECT_ENROLLMENT eligibility predicate from the old EXISTS to
`(old EXISTS OR agent_enrollment_exists)`. Here agent_enrollment_exists is exactly:

```sql
EXISTS (
  SELECT 1 FROM agent_command_receipts r
  JOIN project_memberships m ON m.id = r.result_membership_id
  JOIN actors a ON a.id = m.actor_id
  JOIN actor_subject_bindings b ON b.id = r.result_binding_id
  WHERE r.operation = 'provision_project_agent'
    AND r.result_membership_event_id = NEW.id
    AND m.id = NEW.membership_id AND r.project_id = m.project_id
    AND r.result_actor_id = m.actor_id AND a.actor_type = 'AGENT'
    AND b.actor_id = m.actor_id AND b.subject_kind = 'MTLS_URI'
    AND b.status = 'ACTIVE' AND b.proof_kind = 'MTLS_CHALLENGE'
    AND r.xmin = pg_current_xact_id()::xid
    AND m.xmin = pg_current_xact_id()::xid
    AND b.xmin = pg_current_xact_id()::xid
)
```

Its existing trigger remains installed. This is an exact initial-event
eligibility extension, not another whole-Agent final check. In particular
FIRST_BOOTSTRAP and ACTIVATED rules are unchanged. Final S1 receipt checking
still runs only once on its root.

### 3.2 Immediate function contracts

`pr302_immutable()` rejects every UPDATE (including no-op) and DELETE with
pr302_immutable. No construction UPDATE exception for versions, receipts or events.

`pr302_receipt_guard()` validates operation/result shape and current database
HUMAN OWNER/project ACTIVE facts at advancing clock_timestamp(), after the lock
protocol. It unconditionally assigns NEW.recorded_at := clock_timestamp() once
on INSERT; caller-supplied timestamps cannot select that value. INSERT ...
RETURNING recorded_at gives Application the command timestamp (§4). Receipt is
the command root and is inserted exactly once before its
result rows; deferred result FKs permit that order. Existing caller/project FKs
remain immediate. Registration requires result version ID absent; target Agent
validation occurs at version insertion because its row does not yet exist.
Availability change resolves the existing version's exact project. The
Application has already resolved the target under its actor key. Entitled replay
is handled before insertion. Native
unique collisions are reconciled under the command lock, never blindly leaked.

`pr302_version_guard()` requires a matching register receipt with result version
ID, project, creator, revision 1 and `xmin = pg_current_xact_id()::xid`. Require
target actor type AGENT, not retired, proven ACTIVE MTLS_URI binding and live
ACTIVE project membership/RESEARCHER entitlement. This actor must originate
through a complete provision_project_agent receipt, not a legacy SQL AGENT row.
Configuration resolves `artifact_versions.artifact_id → artifacts.id`; parent
project equals version project, status FROZEN or historically SUPERSEDED,
frozen_at/content_hash non-NULL, and configuration_content_hash exactly equals
the owning content_hash. ArtifactVersion has no hash_scheme column; never select
one or relabel that hash as sha256-cjson-v1. Validate pinned material and version
hash with the exact §5.2 domain; the Application computes from material, never
caller hash input. The DB independently rejects a wrong content_hash using
existing pr216_hash on this exact string/integer-only object:

```sql
pr216_hash(jsonb_build_object(
  'type','AgentVersion','material_version',1,
  'project_id',NEW.project_id::text,'actor_id',NEW.actor_id::text,
  'agent_role',NEW.agent_role,'runtime_type',NEW.runtime_type,
  'prompt_template_version',NEW.prompt_template_version,
  'model_profile_id',NEW.model_profile_id,
  'tool_policy_version',NEW.tool_policy_version,
  'capability_set_hash',NEW.capability_set_hash,
  'configuration_artifact_version_id',NEW.configuration_artifact_version_id::text,
  'configuration_content_hash',NEW.configuration_content_hash))
```

Require equality to NEW.content_hash; contradiction is pr302_provenance. This
uses JSON only for canonical serialization, not for persisted semantic references.

`pr302_availability_guard()` rejects DELETE. INSERT requires ACTIVE/revision 1,
same-transaction version and register receipt. UPDATE allows only status,
revision, changed_by, changed_at to change; agent_version_id is immutable. Require
OLD.revision+1, changed_at >= OLD.changed_at, ACTIVE↔DISABLED or either→RETIRED;
RETIRED and same-state reject. Find exactly one change receipt matching version,
revision, actor/time with current transaction xmin. Already-written OLD.xmin in
this transaction rejects a second availability write, including a transition
after registration in one transaction. Every command is one transaction; no
batching multiple accepted commands or savepoints.

`pr302_event_guard()` requires receipt and availability current transaction xmin,
exact version/revision/actor/time, receipt.result_availability_event_id=NEW.id,
and operation. Sequence 1 has NULL prior, ACTIVE next and fixed reason
`version registered`; later event prior equals sequence-1 new_status, next equals
current availability. Prior event must be committed history, timestamp must not
decrease. Require version project matches receipt. Indexed lookups only here;
no full-history scan or whole-state deferred check on an event row.

`pr302_binding_guard()` retains the old HUMAN branch verbatim (accept here;
all existing proof/challenge guards still apply). For AGENT only, require fresh
actor xmin in this transaction, MTLS_URI, ACTIVE, MTLS_CHALLENGE, no challenge
ID, revision 1, no revoked_at, and matching provision receipt result binding/
actor with current transaction xmin. SERVICE and OS_UID AGENT deny. The receipt's
trusted verifier has bound proof digest/record, subject, credential, owner,
operator, project, command and fresh actor. SQL cannot verify credential
possession and must not be presented as doing so.

`pr302_identity_insert_guard()` dispatches on TG_TABLE_NAME, resolving an event's
subject actor via binding/membership/role FK where necessary; these existing
identity event actor_id fields name the subject Agent, while created_by and
assigned_by name the acting Human. HUMAN behavior passes unchanged. On actors UPDATE reject
actor_type changes if either OLD or NEW is AGENT; preserve ordinary identity
edits/retirement and existing owner-coverage checks. For an AGENT actors
INSERT require provision receipt.result_actor_id=NEW.id with current xmin,
retired_at/external_key NULL; never UPDATE actor_type to enroll. Initial membership
and role inserts for that fresh actor require current-xmin receipt and matching
result IDs/project/actor; membership ACTIVE/revision 1 and role RESEARCHER/
revision 1. Existing Agent reactivation may use existing identity commands but
only for its original project and with a proven active original binding; roles
must be RESEARCHER and cannot exceed the recorded enrollment ceiling. On role
UPDATE enforce RESEARCHER and preserve existing close-only guard. No OWNER,
APPROVER, REVIEWER, VIEWER grants to this enrolled Agent.

For each initial identity event named by a provision receipt, require that exact
receipt and its binding/membership/role parent have
`xmin = pg_current_xact_id()::xid`, exact result event ID and matching request_id
(the S1 command_id). Reject a second initial event or an event added to a
committed enrollment receipt immediately. PROVISIONED, PROJECT_ENROLLMENT and
ASSIGNED map respectively to binding, membership and role. Other existing revoke,
suspend/end/reactivate/close history continues through its existing identity
protocol and guards; it does not attach to or enlarge the S1 receipt. New initial
AGENT binding remains impossible through legacy HUMAN enrollment.

### 3.3 Once-per-command final check

`pr302_receipt_complete()` is the **only NEW whole-state deferred function**.
Every successful S1 command writes exactly one agent_command_receipts row once;
thus pr302_receipt_complete_commit fires ONCE per command on that root. No
deferred whole-version, whole-task or history check is attached per child row.
The immediate guards above force each new child/initial history row to find the
same-transaction root using `xmin = pg_current_xact_id()::xid`, following
`migrations/versions/0057_xid_wraparound_guards.py`. The xid cast handles epochs.
No GUC, stored xid column, forgeable success marker or trigger-depth permission.

At final check, resolve NEW.id from stored receipt, and require:

* Provision: exactly its fresh AGENT, one initial binding/membership/RESEARCHER
  assignment and three exact events, all same-transaction xmin; IDs, project,
  actor, request, proof fields and time match. Binding ACTIVE MTLS_URI/
  MTLS_CHALLENGE, no challenge; role/membership revision 1, no end; initial events
  PROVISIONED, PROJECT_ENROLLMENT (NULL→ACTIVE), ASSIGNED. Caller is the HUMAN
  created_by/assigned_by. No extra initial membership, binding, role or initial
  event for that actor in the transaction; no owner coverage contribution.
* Register: exactly its same-transaction version, availability revision 1 and
  event; version creator/time and event actor/time equal receipt caller/time;
  all material checks of §3.2 still hold. One availability row, one event at
  sequence 1 and no missing history.
* Change: immutable existing version, exactly one current-xmin matching event
  and availability at resulting_revision. History sequence is gapless 1..revision,
  adjacent statuses match, last status/actor/time equals projection. Saved prior
  events and receipts remain unchanged. Require no other current-transaction
  event for this version. One receipt per event and reverse result pointer agree.

Each branch verifies current DB OWNER/scope facts at clock_timestamp(). Current
external credential/proof checks run in Application immediately before commit,
after the final possible wait. A trigger cannot call an external verifier.
Missing/extra/mismatched results fail pr302_provenance or pr302_immutable. This
one final check sees all flushed results; child immediate lookups do not
rescan the whole history. Existing identity deferred guards remain, but are not
new repeated whole-Agent checks. Force all constraints before commit under locks.

## 4. First SHARE, advisory keys and transaction recipes

Each new mutation is one synchronous READ COMMITTED UoW using existing
SqlAlchemyUnitOfWork. Legacy Phase2IdentityService operations retain their own
SERIALIZABLE recipes; adding provision_project_agent must not call provision_actor
inside its transaction. Set connection startup lock_timeout=10s and
statement_timeout=30s before Application SQL; restore pooled defaults. The
command's lock prefix is fixed even for replay. No preceding SET/SHOW,
authorization/replay SELECT, clock read, advisory/row lock or write.

For provision_project_agent, the first Application statement takes the
self-conflicting mode on every existing table this command writes in the
protected inventory; the second takes SHARE only on its read-only dependency:

```sql
LOCK TABLE actor_subject_bindings, actors, project_membership_events,
  project_memberships, project_role_assignments IN SHARE ROW EXCLUSIVE MODE;
LOCK TABLE projects IN SHARE MODE;
```

For register_agent_version and change_agent_availability, the first Application
statement remains exactly the eight-table SHARE inventory. These commands write
only NEW S1 tables and do not write any of these eight existing tables:

```sql
LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts,
  project_membership_events, project_memberships, project_role_assignments,
  projects IN SHARE MODE;
```

| Existing table, in ordered inventory | Enrollment mode / statement | Both version commands / statement | Protected fact |
| --- | --- | --- | --- |
| actor_subject_bindings | SHARE ROW EXCLUSIVE / first | SHARE / first | Live caller/Agent attribution, subject uniqueness, revocation |
| actors | SHARE ROW EXCLUSIVE / first | SHARE / first | HUMAN OWNER and fresh/retired Agent identity |
| artifact_versions | Not locked | SHARE / first | Frozen exact configuration hash/state for registration |
| artifacts | Not locked | SHARE / first | Configuration parent/project scope for registration |
| project_membership_events | SHARE ROW EXCLUSIVE / first | SHARE / first | Identity interval/history evidence and initial enrollment event |
| project_memberships | SHARE ROW EXCLUSIVE / first | SHARE / first | OWNER/Agent current entitlement and enrollment |
| project_role_assignments | SHARE ROW EXCLUSIVE / first | SHARE / first | OWNER authorization and Agent RESEARCHER ceiling |
| projects | SHARE / second | SHARE / first | Project identity/lifecycle |

Enrollment protects six existing tables: five SHARE ROW EXCLUSIVE plus one
SHARE; configuration tables are outside its dependency set. Each version command
protects exactly eight tables in SHARE. Complete the applicable lock prefix
before advisory keys or any other Application SQL. SHARE is never acquired on
an inventory table the command writes. Enrollment's additional binding/role
event tables retain their existing immutable-history guards; no SHARE lock is
added on those write targets.

SHARE ROW EXCLUSIVE conflicts with itself and with ROW EXCLUSIVE. Two arriving
enrollments therefore serialize at actor_subject_bindings, before either can
hold a compatible SHARE lock and later request a mutually blocked write upgrade.
The holder can acquire its own ROW EXCLUSIVE write locks without a competing
enrollment holding SHARE. An enrollment and a version command also contend at
that first common table. This intentionally serializes enrollments across
projects. SHARE protection still blocks unrelated writers. Existing legacy
identity protocols can have different table/advisory acquisition orders; their
cross-protocol deadlocks still require bounded whole-transaction retry evidence,
but retries are not the solution to a symmetric S1 enrollment upgrade cycle.
No task/candidate/scientific target locks are added. B02 positive evidence uses
B02's own accepted transaction recipe in separate commands.

Acquire these transaction advisory locks in this order:

1. Existing `rb_phase2_lock_project(project_id)`, key
   `researchbase-project:<project>`.
2. NEW `pr302:command:<project>:<caller>:<command>`.
3. Enrollment only: existing lock_deployment, key
   `researchbase-deployment:<deployment>`, then NEW
   `pr302:subject:<deployment>:MTLS_URI:<subject>`.
4. NEW `pr302:actor:<agent_actor>`.
5. Version commands only: NEW `pr302:version:<agent_version>`.
6. Row locks: existing actors ORDER BY id (caller, target, operator if present),
   then existing availability FOR UPDATE for change. Read identity dependencies
   in table-name/ID order. New object absence is protected by advisory keys.

All use `pg_advisory_xact_lock(hashtextextended(key,0))`; UUIDs canonical lowercase.
Deployment/subject strings are NFC, exact case-sensitive verified values; key
collisions only over-serialize. Enrollment creates a fresh actor in one project;
do not nest existing multi-project owner provisioning or reverse lock order.
For version commands discover immutable version.actor_id without locking only
after SHARE/project/command locks, acquire actor then version keys, and reread
under keys before diagnostics; an absent ID yields entitled NOT_FOUND.

Common steps after waits: re-read authority, project, bindings and expiry at
advancing clock_timestamp(); authenticate and authorize before existence,
receipt or conflict disclosure. Matching receipt under current **read** entitlement
returns original result before CAS/state/new-write checks. Changed hash yields
IDEMPOTENCY_CONFLICT. Fresh commands require effective HUMAN OWNER and ACTIVE
project. Readers: current OWNER/RESEARCHER/REVIEWER/APPROVER/VIEWER. Retired
versions/archived projects remain entitled history; read entitlement never
requires target Agent credential liveness. Fresh writes recheck all relevant
credentials, owner, operator and exact material after any additional wait.

Command record time has one source: pr302_receipt_guard samples DB
clock_timestamp() once when inserting a fresh receipt. Application omits
recorded_at from that INSERT and receives it via RETURNING recorded_at, converts
it to aware UTC, and copies it to every creation/event/changed timestamp written
by that command. Existing rows' untouched timestamps remain unchanged. This
single sample is for stored provenance; authorization/expiry checks continue to
sample advancing DB time after waits and before commit and never reuse it as
current time. A failed transaction discards its sampled time; each fresh retry
samples a new one while retaining the same IDs and request material. A committed
receipt replay returns its original timestamp without sampling a replacement.

| Command | Exact additional steps |
| --- | --- |
| provision_project_agent | Verify trusted proof outside locks; within transaction recheck HUMAN OWNER, distinct allowlisted operator, live subject/owner/operator credentials and proof validity. Fresh requested actor, unbound subject (including conflicting historical identity), no self-enrollment or credential substitution. Preallocate server UUIDv7 binding/membership/role/three-event/receipt IDs. Insert receipt first and obtain recorded_at via RETURNING; actors AGENT/external_key NULL; ACTIVE binding MTLS_CHALLENGE/no challenge; ACTIVE membership; RESEARCHER role; exact three events. All new record times equal that receipt.recorded_at; row_version 1. No OWNER/APPROVER role or owner coverage reliance. |
| register_agent_version | Pre-read and verify immutable configuration/pinned bytes outside locks; recheck exact frozen DB parent/project/hash, enrolled live target Agent and material. Version ID absent, expected_revision NULL. Compute version hash server-side. Insert receipt, version, ACTIVE availability/revision 1, then one event (NULL→ACTIVE, sequence 1, reason `version registered`). |
| change_agent_availability | Exact project version/availability, expected_revision equals current revision. Validate legal different status and nonblank reason. Preallocate event/receipt IDs; insert receipt and obtain recorded_at via RETURNING, then UPDATE availability exactly once to revision+1 and changed_at=recorded_at/changed_by=caller, then insert matching event with occurred_at=recorded_at. Version content/hash unchanged. RETIRED is final. Disable/retire does not delete, cancel a process or fabricate execution. |

Flush in stated order (receipt result FKs deferred); before commit run
SET CONSTRAINTS ALL IMMEDIATE, then repeat current external credential/proof
checks using fresh DB time and freshly read DB authority after any wait; commit
once. No further writes/waits after the final authority check. Rollback all effects
on failure. Receipt IDs/event IDs are allocated once outside retries and reused.
No model/network/subprocess/ArtifactStore I/O while holding database locks;
trusted verifier rechecks must use locally available verified credential state,
fail closed if unavailable. Pin resolution/bytes are preflight, then DB facts
are rechecked. Proof expiration during a lock wait denies.

Retry only 40001/40P01, at most three fresh whole transactions with same stable
IDs/material and renewed checks. No retry on 55P03/57014 or validation/permission/
state failure. Exhaustion maps CONCURRENT_MODIFICATION; no partial retry.
Lost response/uncertain commit: lock-free receipt reconciliation using original
caller/material; never infer rollback or mint new IDs. All queries/reconciliation
use existing begin_formal_read, one REPEATABLE READ READ ONLY snapshot, autoflush
off, no SHARE/advisory/row locks, writes, repair or second session. Entitlement,
results and history resolve within that snapshot, not a claim of later revocation.

## 5. Closed commands, DTOs, manifest and hash domains

### 5.1 Exact public values

All NEW request/response objects are immutable and closed recursively, reject
unknown fields, normalize text to NFC before hash, reject blanks, malformed UUIDs
and digests; UTC aware timestamps only. UUID strings canonical lowercase;
digests lowercase 64 hex. No body-supplied principal. Envelope fields exactly
project_id, injected caller (existing VerifiedPrincipal), command_id, operation,
expected_revision, arguments. expected_revision is NULL for creates, positive
integer for change. Version/actor IDs are caller-stable; all result/history IDs
are server-created. Required fields have no implicit defaults except explicit
NULL as listed. Bounds: display_name 1..200, reason 1..8192, pin 1..512 characters.

| NEW command / operation | Closed arguments |
| --- | --- |
| ProvisionProjectAgent / provision_project_agent | actor_id, display_name, subject (existing VerifiedSubject), attestation (existing ProvisioningAttestation), enrollment_proof (new AgentEnrollmentProof below). All required; subject.subject_kind must be MTLS_URI. |
| RegisterAgentVersion / register_agent_version | agent_version_id, actor_id, agent_role, runtime_type, prompt_template_version, model_profile_id, tool_policy_version, capability_set_hash, configuration_artifact_version_id. All required. |
| ChangeAgentAvailability / change_agent_availability | agent_version_id, status, reason. All required; expected_revision in envelope. |
| GetAgentVersion / get_agent_version | project_id, agent_version_id and injected caller only. Exact ID query, no list/page or latest alias. |

NEW AgentEnrollmentProof is a trusted-adapter value: project_id, command_id,
actor_id, owner_actor_id, operator_actor_id, deployment_id, subject_kind,
subject_value, subject_credential_id, proof_sha256, proof_record_ref,
verified_at, expires_at. The verifier binds the **entire** normalized enrollment
intent (including display_name, attestation and owner) to this proof, with
verified_at <= current DB time < expires_at. Proof digest/record reference
identifies a retained verifiable record, not client-asserted truth. Verify matches
to VerifiedSubject/ProvisioningAttestation, allowlisted operator, distinct
owner/operator/Agent subjects and actor IDs, same deployment, command/project,
and fresh actor. Reuse existing verifier protocols; NEW AgentEnrollmentVerifier
and trusted MTLS resolver are injected ports with deny-all default. No deployed
mTLS integration is claimed. No credential material or secrets in config/repo.
If production verifier intake is missing, report it blocked; deterministic test
verifier evidence is not production mTLS readiness.

Extend existing Phase2IdentityService additively for enrollment. Existing
ProvisionActor, bootstrap, legacy HUMAN enrollment, resolve_local_binding and
B03 HUMAN-only admission retain their contracts. Existing resolve_bound_subject
adds an explicit AGENT MTLS_URI branch joined to completed enrollment receipt,
active binding, unretired actor and current trusted subject credential checks;
HUMAN branch preserved. It returns existing VerifiedPrincipal through trusted
Application composition, never accepting an actor ID as authentication.
Existing revoke/suspend/end/close commands retain identity history. Reactivation
uses original project/binding and RESEARCHER ceiling; never manufactures binding.

| NEW result/read DTO | Exact fields |
| --- | --- |
| AgentVersionDTO | id, project_id, actor_id, agent_role, runtime_type, prompt_template_version, model_profile_id, tool_policy_version, capability_set_hash, configuration_artifact_version_id, configuration_content_hash, content_hash, hash_scheme, created_by, created_at, current_availability |
| AgentAvailabilityDTO | status, revision, changed_by, changed_at (explicit current projection) |
| AgentCommandResult | receipt_id, project_id, caller_actor_id, command_id, operation, result_actor_id, result_binding_id, result_membership_id, result_role_assignment_id, result_binding_event_id, result_membership_event_id, result_role_event_id, result_agent_version_id, result_availability_event_id, resulting_revision, recorded_at, replayed |

Result nullable fields exactly follow receipt CHECK. No joined current state in
replay result; query it separately. No proof/credential IDs, hidden prompts,
provider exceptions or ORM entities in public DTOs. AgentVersionDTO exposes
pinned identifiers, not configuration bytes. HTTP NEW routes under
`/projects/{project_id}`: POST `/agents`, POST `/agent-versions`,
POST `/agent-versions/{agent_version_id}/availability`, GET
`/agent-versions/{agent_version_id}`. NEW CLI `agents provision`,
`agents register-version`, `agents change-availability`, `agents get-version`
mirror these commands through the same services, existing error/request-ID
envelopes. Proof adapter input is trusted context, not an arbitrary JSON proof
accepted as verified; missing verification denies on both transports.

### 5.2 Exact material and HarnessManifest value

Request hash uses existing canonical_json_bytes / sha256_canonical_json,
sha256-cjson-v1. Exact AgentCommandMaterial keys:

```json
{"type":"AgentCommandMaterial","material_version":1,"operation":"<operation>","project_id":"<uuid>","caller_actor_id":"<authenticated uuid>","command_id":"<uuid>","expected_revision":null,"arguments":{}}
```

Arguments for register/change are exactly §5.1 fields. Enrollment normalized
arguments replace trusted objects with these exact closed dictionaries:
subject = {deployment_id, subject_kind, subject_value, credential_id};
attestation = {actor_id, deployment_id, subject_kind, subject_value,
subject_credential_id, operator_actor_id, proof_sha256, proof_record_ref, reason};
enrollment_proof = {project_id, command_id, actor_id, owner_actor_id,
operator_actor_id, deployment_id, subject_kind, subject_value,
subject_credential_id, proof_sha256, proof_record_ref}.
Include actor_id/display_name as well. Credential **identifiers** and proof
identity/digest are material; raw credentials and verifier freshness timestamps
are excluded. The attestation operator is projected to authenticated actor ID;
reverify its subject/credential against retained proof. The proof digest binds
all intent and credential identities; refreshing verification of the same proof
does not change request hash. Different proof/intent must conflict on same key.
Retain explicit NULL expected_revision. Exclude transport request/correlation ID,
server result/event/receipt IDs/times, replay metadata, derived configuration
hash, version hash and current availability. Hash closed normalized requests,
not current projections. Reject duplicate set members before sorting.

Version content hash exact domain (NEW): {type:"AgentVersion",
material_version:1, project_id, actor_id, agent_role, runtime_type,
prompt_template_version, model_profile_id, tool_policy_version,
capability_set_hash, configuration_artifact_version_id, configuration_content_hash}.
Values are the saved version material, all present; exclude id/creator/time/
availability/content_hash/hash_scheme. Version hash scheme is sha256-cjson-v1;
embedded configuration_content_hash retains its owning ArtifactVersion meaning.
Pinned identifiers resolve immutable, retained manifests/content; syntactically
nonblank names alone do not prove pinning. Reject mutable branch/latest/current
locators and unresolved executable dependencies. No new registry/FK is invented.

NEW HarnessManifest is a closed immutable value, schema_version=1, with exactly:
researchbase_revision, agent_runtime_revision, model_profile_id,
prompt_template_version, agents_md_sha256, config_sha256, strategy_id,
strategy_revision, skills, plugins, adapters, hooks, mcp_capabilities,
reference_libraries. Each of the six arrays is required (empty means none).
Each entry has exactly id, revision, content_sha256, ordinal; ordinal is positive,
unique and contiguous 1..n per collection; IDs unique in a collection. Normalize
by ordinal (effective order is material), never sort away execution order.
Revisions/IDs are NFC pinned strings 1..512, digests 64 lowercase hex. Reference
libraries use the same entry shape but are explicitly non-executable through
the collection name; executable use must also be pinned in its effective
collection. ResearchBase/runtime/strategy revisions must be immutable retained
revisions; model/profile and prompt pinned. No secrets, latest/current/branch
aliases, unresolved imports or free extra keys. Digest = sha256_canonical_json
of the complete normalized value. Artifact byte digest remains a separate raw
byte hash; do not equate the two for noncanonical JSON bytes. S1 validates the
value only; no manifest command, table, execution FK or saved execution digest.
S2 owns admission/binding. Changed effective material changes its digest; a
fingerprint does not promise deterministic model output.

### 5.3 Fixed request-hash vectors

The following are COMPLETE normalized inputs (canonical UTF-8 JSON), not
abbreviations. Vector 1 enrollment, vector 2 registration, vector 3 availability.
Computed using the throwaway stdin script recorded in §8, importing the repository
helpers with PYTHONPATH=src and .venv/bin/python. Future tests must use literal
expected digests, NFC normalization before hashing, and reject extra fields.

Vector 1 input / canonical UTF-8 text:

```json
{"arguments":{"actor_id":"01900000-0000-7000-8000-000000000003","attestation":{"actor_id":"01900000-0000-7000-8000-000000000003","deployment_id":"researchbase-test","operator_actor_id":"01900000-0000-7000-8000-000000000004","proof_record_ref":"test-proof:agent-1","proof_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","reason":"Enroll research Agent.","subject_credential_id":"agent-cert-1","subject_kind":"MTLS_URI","subject_value":"spiffe://researchbase.test/agents/research"},"display_name":"Café researcher","enrollment_proof":{"actor_id":"01900000-0000-7000-8000-000000000003","command_id":"01900000-0000-7000-8000-000000000005","deployment_id":"researchbase-test","operator_actor_id":"01900000-0000-7000-8000-000000000004","owner_actor_id":"01900000-0000-7000-8000-000000000002","project_id":"01900000-0000-7000-8000-000000000001","proof_record_ref":"test-proof:enrollment-1","proof_sha256":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","subject_credential_id":"agent-cert-1","subject_kind":"MTLS_URI","subject_value":"spiffe://researchbase.test/agents/research"},"subject":{"credential_id":"agent-cert-1","deployment_id":"researchbase-test","subject_kind":"MTLS_URI","subject_value":"spiffe://researchbase.test/agents/research"}},"caller_actor_id":"01900000-0000-7000-8000-000000000002","command_id":"01900000-0000-7000-8000-000000000005","expected_revision":null,"material_version":1,"operation":"provision_project_agent","project_id":"01900000-0000-7000-8000-000000000001","type":"AgentCommandMaterial"}
```

Output request_hash: `4cc1af5312be685ea559d09e0f2e6ff459e920b03fb7ba82218172346278d3d7`.

Vector 2 input / canonical UTF-8 text:

```json
{"arguments":{"actor_id":"01900000-0000-7000-8000-000000000003","agent_role":"research","agent_version_id":"01900000-0000-7000-8000-000000000006","capability_set_hash":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","configuration_artifact_version_id":"01900000-0000-7000-8000-000000000007","model_profile_id":"model-profile@1.0.0","prompt_template_version":"research-prompt@1.0.0","runtime_type":"native","tool_policy_version":"tool-policy@1.0.0"},"caller_actor_id":"01900000-0000-7000-8000-000000000002","command_id":"01900000-0000-7000-8000-000000000008","expected_revision":null,"material_version":1,"operation":"register_agent_version","project_id":"01900000-0000-7000-8000-000000000001","type":"AgentCommandMaterial"}
```

Output request_hash: `19b7537803f35a6c1395c4b48abf8af8e2eb85b5da6d7b804c9881bb548224a8`.

Vector 3 input / canonical UTF-8 text:

```json
{"arguments":{"agent_version_id":"01900000-0000-7000-8000-000000000006","reason":"Maintenance window.","status":"DISABLED"},"caller_actor_id":"01900000-0000-7000-8000-000000000002","command_id":"01900000-0000-7000-8000-000000000009","expected_revision":1,"material_version":1,"operation":"change_agent_availability","project_id":"01900000-0000-7000-8000-000000000001","type":"AgentCommandMaterial"}
```

Output request_hash: `b9c60b8b598d025aab9f0fceaeabfc1f11173eb58f8084e2043fb1a224359416`.


## 6. Existing ErrorCode mapping

Existing ErrorCode only; labels `pr302_validation`, `pr302_scope`,
`pr302_state`, `pr302_immutable`, `pr302_not_frozen`, `pr302_provenance` are NEW
SQL diagnostic constraint labels/details, not enum members. Trigger SQLSTATE
23514 dispatches by those labels. Declarative CHECK failures on the four §2
tables map VALIDATION_ERROR; existing identity checks retain their accepted
translations. Duplicate event sequence/receipt or contradictory saved result
uniqueness maps PROVENANCE_CLOSURE_VIOLATION after scoped diagnosis (public
CAS failures are caught as CONCURRENT_MODIFICATION first). Sanitize messages,
never expose SQL/proof or
constraint text. Authenticate/authorize before protected existence/conflict;
malformed submitted fields may fail without persisted-state disclosure.

| Existing code | HTTP / CLI exit | Exact S1 mapping |
| --- | --- | --- |
| VALIDATION_ERROR | 422 / 2 | Closed shape, limits, literal/digest/UUID/pin/manifest errors; pr302_validation |
| AUTHENTICATION_REQUIRED | 401 / 3 | No verified principal |
| FORBIDDEN | 403 / 3 | Wrong project, non-HUMAN OWNER, self/impersonation, role ceiling or archive new-write denial; pr302_scope |
| SUBJECT_BINDING_UNPROVEN | 403 / 3 | Missing/mismatched/expired proof or subject/operator credential; unavailable trusted verifier |
| SUBJECT_ALREADY_BOUND | 409 / 4 | Subject bound or duplicate binding under subject lock |
| OWNER_CREDENTIAL_UNAVAILABLE | 409 / 4 | Required OWNER credential/authority expired or unavailable in enrollment |
| NOT_FOUND | 404 / 3 | Entitled exact version/availability/artifact absent |
| INVALID_STATE_TRANSITION | 409 / 4 | Same-state, RETIRED exit, illegal availability; pr302_state |
| IMMUTABLE_RECORD | 409 / 4 | Version/event/receipt mutation, late child/history attachment; pr302_immutable |
| VERSION_NOT_FROZEN | 409 / 4 | Exact configuration not historically frozen; pr302_not_frozen |
| FROZEN_REFERENCE_REQUIRED | 409 / 5 | Unresolved current/latest reference (malformed transport UUID stays VALIDATION_ERROR) |
| PROVENANCE_CLOSURE_VIOLATION | 409 / 5 | Saved hash, manifest or receipt/result/history contradiction; pr302_provenance |
| REFERENTIAL_INTEGRITY_ERROR | 409 / 5 | Native 23503 / contradictory concrete FK |
| IDEMPOTENCY_CONFLICT | 409 / 4 | Same project/caller/command, different normalized request hash |
| CONCURRENT_MODIFICATION | 409 / 4 | Stale revision, occupied requested actor/version ID, exhausted 40001/40P01, 55P03/57014 |

No new duplicate-content rule for registering identical behavior under distinct
IDs. DUPLICATE_CONTENT remains existing B02 semantics only. Native 23505 receipt
collision is reconciled under command lock: identical material replays, changed
material conflicts. Other uniqueness failures translate after scoped diagnosis,
never overwrite. Existing owner-coverage errors keep their existing semantics.
Unexpected failures retain existing INTERNAL_ERROR fallback (HTTP 500/CLI 1),
which is not an ErrorCode member. HTTP `{error:{code,message,details}}` and
X-Request-ID, CLI sanitized envelope and request identity remain unchanged.

## 7. Required future tests and acceptance

No tests are created or run by this pack. Exact NEW implementation test files:

| NEW file | Required cases |
| --- | --- |
| tests/unit/phase3/test_agent_version_contracts.py | Closed recursive DTOs/command matrices; NFC/UUID/digest/bounds; all role/runtime literals; ACTIVE↔DISABLED and terminal RETIRED; same-state rejection; every §5.3 literal vector; material includes project/caller/command/CAS/target/proof identity, excludes generated/freshness data; version hash availability independence; distinct stable IDs/same content accepted |
| tests/unit/phase3/test_harness_manifest.py | Exact fields/empty arrays; unknown fields; ordinal order/duplicates/gaps; pin resolution and alias rejection; reference-only versus executable pins; changed prompt/model/config/skill/plugin/adapter/hook/MCP changes digest; bytes versus canonical digest distinction; no secret serialization |
| tests/unit/phase3/test_agent_identity_contracts.py | Verifier deny default, immutable proof value, intent/credential/operator/owner/project/command/display mismatch, expiry/revocation, no OS_UID fallback, reactivation ceiling and original project/binding; existing HUMAN behavior |
| tests/unit/phase3/test_agent_version_transports.py | HTTP/CLI same Application DTOs/results; trusted context injection; body principal rejected; every §6 HTTP/exit mapping, sanitized diagnostics/request IDs/INTERNAL_ERROR; auth before existence; no proof/credential output |
| tests/architecture/test_pr3_02_s1_boundaries.py | Human/Agent common boundary; pure domain no ORM/transport/vendor imports; no runtime direct DB or credential access; no new scientific ownership, fingerprint entity, S2 schema/API or provider dependency; existing identity proof ports reused |
| tests/integration/phase3/test_pr3_02_s1_schema.py | All DDL types/null/CHECK/RESTRICT/uniques/indexes; 14 new triggers plus 1 replacement, 8 new functions plus 1 replaced existing body and its retained trigger; normal-role valid command protocol; fresh AGENT MTLS only; no-op UPDATE/DELETE immutability; cross-project/config/actor mismatches and wrong computed version hash; positive non-ASCII SQL/Python version-hash parity case specified below; declarative rejection of change receipt resulting_revision=1; receipt guard replaces any supplied recorded_at with its DB sample and results copy that time; incomplete/extra results/events; late inserts against committed receipts; same-xact xmin guard and wraparound-safe expression; exactly one deferred root firing per command and no per-child whole-state triggers; force checks across multiple flushes |
| tests/integration/phase3/test_pr3_02_s1_identity.py | Application-only enrollment→trusted subject resolution→existing VerifiedPrincipal; proof/subject/operator/credential/owner mismatch, expiry, revoke, self-enroll, duplicate, fresh-ID collision, Agent role escalation; revoke/suspend/end/reactivate preserve ceiling; unchanged HUMAN bootstrap/ProvisionActor/legacy; no actor_type UPDATE fixtures |
| tests/integration/phase3/test_pr3_02_s1_application.py | Register/change/read; all availability transitions; frozen configuration scope/hash; literal/mutable pin refusal; retirement history; injected failure after each flush leaves zero new rows/history/receipts; no scientific hash mutation |
| tests/integration/phase3/test_pr3_02_s1_b02_agent.py | Owner enrolls through new Application command, trusted MTLS resolution, then existing capture_native_strategy/promote_strategy_question/promote_strategy_hypothesis positive G2 AGENT boundary with actual provenance; B03 Agent denied; no SQL-forged type/binding/membership or fabricated execution; AQ-S3-08 evidence qualified by verifier intake |
| tests/integration/phase3/test_pr3_02_s1_concurrency.py | Trace enrollment's first five-table SHARE ROW EXCLUSIVE and second projects SHARE before all other SQL, with no artifact table locks; both version commands retain first eight-table SHARE; two concurrent distinct enrollments in same and different projects wait at the first common table and both commit serially with zero 40P01/retries when the controlled holder releases within lock_timeout; enrollment versus version command serializes at actor_subject_bindings; no SHARE-to-write upgrade on enrollment targets; actual legacy identity protocol races retain bounded whole-transaction handling; same subject/actor/version/command races; availability CAS/retire versus register/change; owner/subject/operator credential expiry during actual lock wait and membership/binding revoke versus write; 40001/40P01 three-transaction bound; 55P03/57014 no retry; one winner or sanitized failure for conflicts, no partial history; lock-free repeatable-read query under writer |
| tests/integration/phase3/test_pr3_02_s1_replay.py | Same material converges, changed proof/target/CAS conflicts, lost response/uncertain commit reconciliation; failed-attempt timestamp rolls back, successful retry resamples DB time with stable IDs/material, and replay preserves saved time; no effects on replay; stale CAS/retired version/archived project replay under current read entitlement; current read revocation denies; another caller cannot replay original; saved exact IDs/revision survive later changes |
| tests/integration/phase3/test_pr3_02_s1_migration.py | PostgreSQL 18 empty and populated upgrade through accepted 0078 to 0079, sole head/parent; accepted Phase 1/2/PR3-01 IDs/hashes/trace and PR3-04 policies unchanged; both downgrade refusal modes before DDL/pointer change; separately approved forward repair; S2 absent and execution gate remains closed |

The positive schema parity case uses resolved retained NFC pins
prompt_template_version=`café-研究@1.0.0`, model_profile_id=`modèle-模型@1.0.0`
and tool_policy_version=`outils-策略@1.0.0`, a real frozen configuration and
Application-enrolled Agent. Build the complete §5.2 AgentVersion material;
compare existing pr216_cjson SQL serialization converted to UTF-8 bytes with
Python canonical_json_bytes, and compare existing pr216_hash with Python
sha256_canonical_json. Register under the normal command/lock/receipt protocol
and assert DB acceptance with content_hash equal to both digests and unchanged
NFC pins. A syntactic pin string without resolver evidence is not a positive
case. This must run against PostgreSQL 18; an ASCII-only fixture, pure-Python
test or a comment about string/integer material does not establish parity.

Existing regression files to run/update as needed during authorized implementation:
`tests/integration/phase2/test_b02_identity_boundary.py` (preserve legacy rejection
reproduction pinned to 0077; at new head assert unceremonied AGENT denial through
the replacement guard plus new positive Application evidence, not obsolete
function-body text), `tests/integration/phase2/test_pr2_00_identity.py`,
`tests/integration/phase2/test_pr2_00_identity_guards.py`,
`tests/integration/phase2/test_pr2_00_bootstrap.py`,
`tests/integration/phase2/test_pr2_00_temporal_auth.py`,
`tests/integration/phase2/test_pr2_00_ownership.py`,
`tests/integration/phase2/test_pr2_00_challenges.py`,
`tests/integration/phase2/test_pr2_00_concurrency.py`,
`tests/integration/phase2/test_pr2_00_transaction_isolation.py`,
`tests/integration/phase2/test_pr2_00_migration.py`,
`tests/integration/phase2/test_b02_strategy_admission.py`,
`tests/integration/phase2/test_b02_strategy_capture.py`,
`tests/integration/phase2/test_b02_strategy_replay.py`,
`tests/integration/phase2/test_b02_strategy_schema.py`,
`tests/integration/phase2/test_b02_strategy_concurrency.py`,
`tests/integration/phase2/test_b03_discussion_hypothesis.py`,
`tests/integration/phase2/test_b03_discussion_hypothesis_guards.py`,
`tests/architecture/test_b02_strategy_promotion_boundaries.py`,
`tests/architecture/test_b03_discussion_hypothesis_boundaries.py`,
`tests/unit/phase3/`, `tests/architecture/test_pr3_01_boundaries.py` and
`tests/integration/phase3/`. Accepted legacy fixtures are not permission to forge
the new positive Agent case. Existing B03 tests and admission code must retain
their HUMAN-only rule.

All DB/constraint/migration/concurrency cases use disposable real PostgreSQL 18,
normal roles with triggers enabled, not SQLite or privileged trigger bypass.
Record actual first-SQL traces, retry/wait timings, DB timestamps, final-check
firing counts and authority races. Explicitly force SET CONSTRAINTS ALL IMMEDIATE
to measure deferred work. No unexplained timing/performance claim. S1 enrollment
is not an execution and positive B02 evidence does not prove S2 promotion.

After both director reviews and implementation, required focused commands:

```sh
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pyright
.venv/bin/alembic heads
.venv/bin/pytest -o addopts='' -ra tests/unit/phase3 tests/architecture
.venv/bin/pytest -o addopts='' -ra tests/integration/phase3
.venv/bin/pytest -o addopts='' -ra tests/integration/phase2/test_pr2_00_*.py tests/integration/phase2/test_b02_*.py tests/integration/phase2/test_b03_*.py
```

Supply disposable DB configuration per existing README. Full-suite evidence
belongs to the authorized check loop, not a local whole-suite run. Future NEW
`docs/phase3/PR3-02-S1-evidence.md` records exact commands/counts/skips/failures,
DB/version/head, regression preservation, independent verifier intake and
Application G2 evidence, plus two pack director reviews and implementation review
findings. Open P0/P1 blocks acceptance. Missing production verifier intake must
remain explicitly pending; no assertion that deterministic test proofs deploy
mTLS. STOP after S1 acceptance evidence; S2 needs separate authorization.

## 8. Existing-identifier source inventory and authoring verification

Existing identifiers were checked by focused literal rg through src/, migrations/
and tests/, rather than inferred from architecture concepts:

| Existing names / facts | Source evidence |
| --- | --- |
| 0077_research_task_graph / 0076_agent_runtime_bootstrap; delivered task graph, pr301:task and task receipt protocol | migrations/versions/0077_research_task_graph.py; src/researchbase/persistence/research_task_repository.py; tests/integration/phase3/test_pr3_01_schema.py |
| All eight protected tables in the per-command lock inventory; actors actor_type/display_name/external_key/retired_at; projects lifecycle_status | src/researchbase/persistence/models.py; migrations/versions/0019_phase2_bootstrap_membership.py |
| artifact_versions artifact_id/status/frozen_at/content_hash (no hash_scheme), artifacts project_id | src/researchbase/persistence/models.py; migrations/versions/0006_artifact_version.py |
| actor_subject_bindings proof/credential/challenge/interval fields; actor_subject_binding_events; project_memberships/project_membership_events; project_role_assignments/project_role_events | migrations/versions/0019_phase2_bootstrap_membership.py |
| rb_phase2_lock_project, rb_phase2_guard_human_actor, trg_actor_binding_human, trg_actor_challenge_human; PROVISIONED, PROJECT_ENROLLMENT, ASSIGNED, MTLS_CHALLENGE | migrations/versions/0019_phase2_bootstrap_membership.py |
| rb_phase2_validate_membership_event, trg_project_membership_event_transition, ck_membership_event_transition, FIRST_BOOTSTRAP, ACTIVATED; projects.created_by eligibility | migrations/versions/0019_phase2_bootstrap_membership.py |
| lock_deployment, resolve_bound_subject (currently HUMAN only), resolve_local_binding; researchbase-project / researchbase-deployment | src/researchbase/persistence/phase2_identity_repository.py; migrations/versions/0019_phase2_bootstrap_membership.py |
| Phase2IdentityService, ProvisionActor, VerifiedSubject, ProvisioningAttestation; SubjectCredentialVerifier, OnboardingAttestationVerifier, OperatorPolicy; reactivate_project_membership | src/researchbase/application/phase2_identity.py |
| VerifiedPrincipal, ActorType.AGENT, MTLS_URI, OS_UID | src/researchbase/domain/phase2_identity.py; src/researchbase/domain/identity.py |
| StrategyCandidatePromotionService, capture_native_strategy, promote_strategy_question, promote_strategy_hypothesis; existing B02 G2 gap reproduction | src/researchbase/application/strategy_candidate_promotion.py; tests/integration/phase2/test_b02_identity_boundary.py |
| SqlAlchemyUnitOfWork, begin_formal_read | src/researchbase/persistence/uow.py |
| xmin = pg_current_xact_id()::xid | migrations/versions/0057_xid_wraparound_guards.py |
| pr216_hash / pr216_cjson (existing canonical SQL hash helpers, used only for the frozen string/integer version material) | migrations/versions/0045_pr2_16_basic_approval.py |
| canonical_json_bytes, sha256_canonical_json, sha256-cjson-v1; ErrorCode and §6 values; _STATUS, CLI_EXIT_CODES, INTERNAL_ERROR fallback | src/researchbase/foundation/canonical_json.py; src/researchbase/foundation/hashing.py; src/researchbase/foundation/errors.py; src/researchbase/api/errors.py; src/researchbase/cli/errors.py |
| Existing focused regression/test paths in §7 | tests/unit/phase3/; tests/architecture/; tests/integration/phase3/; tests/integration/phase2/ |

NEW planned implementation paths: agent_runtime/domain/agent_version.py and
harness_manifest.py; agent_runtime/application/agent_versions.py and
agent_contracts.py; agent_runtime/ports/agent_repository.py (all relative to
src/researchbase/); src/researchbase/persistence/agent_version_repository.py and
agent_version_queries.py. Extend existing identity Application/ports/repository,
models/UoW, API/CLI composition additively; transport route/module choices must
preserve §5.1 operations. No new dependency is required.

Authoring verification is limited to static checks, source/identifier inspection,
whitespace/scope inspection and the three hash computations. No unit,
architecture, migration or PostgreSQL suites run for this documentation-only
request under its specific “No tests run except the throwaway hash computation”
instruction. Future commands above are obligations, not PASS evidence.

Initial authoring results, retained as historical evidence (no test suites):

| Exact command / inspection | Observed result |
| --- | --- |
| `.venv/bin/ruff check .` | Exit 0; All checks passed! |
| `.venv/bin/ruff format --check .` | Exit 0; 837 files already formatted |
| `.venv/bin/pyright` | Exit 0; 0 errors, 0 warnings, 0 informations; separate tool-version update notice |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -` (throwaway hash script below) | Exit 0; three canonical inputs and three SHA-256 outputs in §5.3 |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -` (static inventory invoking `rg -l -F -- <identifier> src/ migrations/ tests/`) | 121 existing literal identifiers checked, zero missing; DISABLED explicitly NEW S1, not claimed existing |
| Static path/DDL inspection | 39 existing literal .py paths; 14 explicitly NEW planned literal .py paths; 4 CREATE TABLE statements; 17 explicit indexes in addition to PK/UNIQUE backing indexes; 8 new functions, 14 new triggers, 1 replaced trigger, 1 retained existing trigger with narrowly replaced function; 3 request-hash outputs |
| `git diff --check` | Exit 0 |
| `rg -n '[[:blank:]]+$' docs/phase3/PR3-02-S1-contract-freeze.md` and explicit file inspection | No matches (rg exit 1); 0 trailing-whitespace lines; final newline present |
| `git status --short --untracked-files=all` | Only `?? docs/phase3/PR3-02-S1-contract-freeze.md` |

Reproducible throwaway computation, reading exactly the pasted normalized inputs:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python - <<'PY'
import json
import re
from pathlib import Path
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.hashing import sha256_canonical_json

text = Path('docs/phase3/PR3-02-S1-contract-freeze.md').read_text()
section = text.split('### 5.3 Fixed request-hash vectors', 1)[1].split('## 6.', 1)[0]
for index, payload in enumerate(re.findall(r'```json\n(.*?)\n```', section, re.S), 1):
    material = json.loads(payload)
    print(f'Vector {index} canonical: {canonical_json_bytes(material).decode("utf-8")}')
    print(f'Vector {index} request_hash: {sha256_canonical_json(material)}')
PY
```

Whitespace/scope checks originally covered the then-untracked document
explicitly; the review correction also checks all changes against HEAD below.
No unit/architecture/PostgreSQL pass counts are claimed. Only this new file is
delivered; no branch, commit or push.

Reviewer-correction verification (documentation only): enrollment now uses the
five-table SHARE ROW EXCLUSIVE prefix followed by projects SHARE; the two version
commands retain eight-table SHARE. Stored time is sampled by the receipt guard
per attempt, change receipts require revision >=2 declaratively, and the future
schema suite includes positive non-ASCII PostgreSQL/Python hash parity. These
are revised contracts and test obligations, not executed concurrency/parity tests
or a director-review PASS.

Static checks repeated after correction: `.venv/bin/ruff check .` exited 0
(All checks passed!); `.venv/bin/ruff format --check .` exited 0 (837 files already
formatted); `.venv/bin/pyright` exited 0 (0 errors, 0 warnings, 0 informations;
separate version-update notice). The requested scope/whitespace command exited 0:

```sh
git diff --check HEAD && test -z "$(git status --porcelain | grep -vE "^.. docs/")"
```

Only docs/phase3/PR3-02-S1-contract-freeze.md changed. Unit, architecture and
PostgreSQL suites remain NOT RUN under the documentation-only instruction;
the new parity and lock-serialization cases are future implementation acceptance
requirements. No branch, commit or push.
