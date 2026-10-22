# PR3-03 capability gateway contract freeze and execution pack

Status: PACK DRAFT — pending director review; implementation NOT yet authorized by this file

Authority: AGENTS.md; architecture [01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md),
[02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md),
[03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md),
[08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md);
[Phase 3](../architecture/06_Phase3_Development_Specification_v1.1_Harness_Integrated.md)
§§7–9, 40–41 and both §85 sections; [Harness 09](../harness/09_Harness_Integration_Specification_v1.0.md);
[approved direction](../proposals/PR3-03_Capability_Gateway_Invocation_Contract_DRAFT.md)
(commit 8885f6b); [PR3-01](PR3-01-contract-freeze.md),
[PR3-04](PR3-04-contract-freeze.md), [S1](PR3-02-S1-contract-freeze.md);
[ADR-0021](../architecture/adr/ADR-0021-tdg3-phase3-technology-decisions.md),
[ADR-0023](../architecture/adr/ADR-0023-pr3-02-agent-identity-versions-executions.md),
[ADR-0024](../architecture/adr/ADR-0024-pr3-04-budget-termination-checkpoint.md).
Higher scientific invariants prevail. This is the complete proposed execution
contract for director review, not a review PASS, migration execution or Phase GO.

## 1. Baseline, decisions and scope

Owner approval on **2026-10-22** accepted the recommended contract direction and
authorized starting implementation subject to a frozen execution pack. This file
remains a PACK DRAFT until director review freezes it. The proposal's historical
“awaiting owner approval” line does not negate the recorded owner decision.

| Decision | Disposition on 2026-10-22 | Frozen consequence |
| --- | --- | --- |
| D303-01 | ACCEPTED-AS-RECOMMENDED | S1 + PR3-04 are prerequisites; task/version-owned CONTRACT_FAKE only. S2 later adds concrete execution FK/mode; no fake execution identity or backfill. |
| D303-02 | ACCEPTED-AS-RECOMMENDED | Five pattern tables and constrained existing receipt/event extensions below. |
| D303-03 | ACCEPTED-AS-RECOMMENDED | Exact immutable deny-by-default policy, default 50 calls / 1 parallel; retained pinned registry, reference-only Skills cannot execute. |
| D303-04 | ACCEPTED-AS-RECOMMENDED | Trusted accounting inside the command UoW, exact shared locks, replay before state/CAS after every wait. |
| D303-05 | ACCEPTED-AS-RECOMMENDED | Deterministic in-process fake only; real tool/MCP intake and activation require separate authorization; existing ErrorCodes only. |

Branch base requested: codex/phase3-wave3-base, main 2d6e347. Authoring checkout
is that branch at 3e724b2 (documentation commits follow the base). Database parent
is exactly `0079_agent_identity_versions`; new revision
`0080_capability_gateway`, down_revision=`0079_agent_identity_versions`,
branch_labels=None, depends_on=None. New migration path
`migrations/versions/0080_capability_gateway.py` is **new in PR3-03**.
Migration must leave 0080 as the sole head. If another migration lands first,
revise/review this pack before implementation; never edit accepted ancestors.
`downgrade()` raises RuntimeError before DDL or revision-pointer change on both
empty and populated databases. Only reviewed forward repair is permitted.

Every `pr303_` identifier, five new table names, new columns in §3, gateway
command/DTO/port/service identifiers and proposed implementation/test paths in
this pack are **new in PR3-03**, even where the architecture names the concept.
Unlisted SQL built-ins are PostgreSQL primitives, not repository APIs. Existing
identifiers and verification are inventoried in §10.

Schema admissions use existing patterns: immutable Policy Entity; exact
Permission Relation; stateful Invocation Entity; typed reference Relations;
append-only Invocation Events. Scientific Run, AgentExecution, Review, Decision,
Approval, Command and ExternalEffect stay distinct. No generic polymorphic JSON
semantic core. No new registry, fingerprint, usage, parameter or receipt table.

Explicit exclusions: S2 execution table/lifecycle, promotion, real provider or
model, real tool/MCP adapter, SDK, queue, worker, lease/recovery, network/process/
filesystem execution, secrets, new dependency, memory/search-lineage ownership,
scientific write, self-install, autonomous authority or Approval purpose.
Subscription CLIs, including Codex/agy, are prohibited product LLM backends;
a later real provider must be API-based under its named owning PR. Existing task
and step states and `execution_enabled=false` remain unchanged. A2/A3 executable
admission remains unavailable as in delivered safety rules. CONTRACT_FAKE is
not Agent execution or evidence of real containment/recovery readiness.

## 2. Complete additive DDL

PostgreSQL 18, UTF-8, synchronous I/O. Documentation only: do not execute this
SQL for the pack task. IDs are Application-generated UUIDv7. All timestamps are
aware UTC DB observations supplied by Application; no UUID/time defaults. Every
nullable column says NULL. All FKs are ON DELETE RESTRICT, ON UPDATE NO ACTION
(default); only explicit cycles are DEFERRABLE INITIALLY DEFERRED. PK/UNIQUE
supply B-tree indexes; all additional indexes are listed below. Text is NFC;
pins exclude aliases and are immutable exact identifiers. No JSON columns.

The three supporting UNIQUE constraints on accepted tables are additive; no
historical row is updated. They expose existing primary-key uniqueness in the
concrete tuples needed by the new foreign keys.

```sql
ALTER TABLE budget_reservations ADD CONSTRAINT pr303_reservation_operation_key
  UNIQUE (research_task_id, id, operation_id);
ALTER TABLE budget_usage_records ADD CONSTRAINT pr303_usage_reservation_key
  UNIQUE (research_task_id, reservation_id, id);
ALTER TABLE research_task_command_receipts ADD CONSTRAINT pr303_receipt_scope_key
  UNIQUE (research_task_id, project_id, id);

CREATE TABLE agent_tool_policies (
  id uuid NOT NULL PRIMARY KEY,
  project_id uuid NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
  registration_task_id uuid NOT NULL,
  receipt_id uuid NOT NULL,
  version text NOT NULL CHECK (length(btrim(version)) BETWEEN 1 AND 512
    AND version IS NFC NORMALIZED
    AND lower(btrim(version)) NOT IN ('latest','current','main','master')),
  capability_set_hash text NOT NULL CHECK (capability_set_hash ~ '^[0-9a-f]{64}$'),
  max_tool_calls integer NOT NULL CHECK (max_tool_calls > 0),
  max_parallel_invocations integer NOT NULL CHECK (max_parallel_invocations > 0
    AND max_parallel_invocations <= max_tool_calls),
  filesystem_scope text NOT NULL CHECK (filesystem_scope = 'DENY'),
  network_scope text NOT NULL CHECK (network_scope = 'DENY'),
  compute_scope text NOT NULL CHECK (compute_scope = 'DENY'),
  external_effect_scope text NOT NULL CHECK (external_effect_scope = 'DENY'),
  registry_artifact_version_id uuid NOT NULL REFERENCES artifact_versions(id) ON DELETE RESTRICT,
  registry_content_hash text NOT NULL CHECK (registry_content_hash ~ '^[0-9a-f]{64}$'),
  content_hash text NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
  hash_scheme text NOT NULL CHECK (hash_scheme = 'sha256-cjson-v1'),
  created_by uuid NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL,
  UNIQUE (project_id, version),
  UNIQUE (id, project_id),
  FOREIGN KEY (registration_task_id, project_id)
    REFERENCES research_tasks(id, project_id) ON DELETE RESTRICT,
  FOREIGN KEY (registration_task_id, project_id, receipt_id)
    REFERENCES research_task_command_receipts(research_task_id, project_id, id)
    ON DELETE RESTRICT
);
CREATE TABLE agent_tool_policy_permissions (
  id uuid NOT NULL PRIMARY KEY,
  policy_id uuid NOT NULL,
  project_id uuid NOT NULL,
  capability_id text NOT NULL,
  capability_version text NOT NULL,
  operation text NOT NULL,
  adapter_id text NOT NULL,
  adapter_version text NOT NULL,
  parameter_schema_hash text NOT NULL CHECK (parameter_schema_hash ~ '^[0-9a-f]{64}$'),
  effect text NOT NULL CHECK (effect IN ('ALLOW','DENY')),
  UNIQUE (policy_id, capability_id, capability_version, operation,
    adapter_id, adapter_version, parameter_schema_hash, effect),
  FOREIGN KEY (policy_id, project_id)
    REFERENCES agent_tool_policies(id, project_id) ON DELETE RESTRICT,
  CHECK (length(btrim(capability_id)) BETWEEN 1 AND 128 AND capability_id IS NFC NORMALIZED),
  CHECK (length(btrim(capability_version)) BETWEEN 1 AND 512 AND capability_version IS NFC NORMALIZED),
  CHECK (length(btrim(operation)) BETWEEN 1 AND 128 AND operation IS NFC NORMALIZED),
  CHECK (length(btrim(adapter_id)) BETWEEN 1 AND 128 AND adapter_id IS NFC NORMALIZED),
  CHECK (length(btrim(adapter_version)) BETWEEN 1 AND 512 AND adapter_version IS NFC NORMALIZED)
);
CREATE TABLE capability_invocations (
  id uuid NOT NULL PRIMARY KEY,
  project_id uuid NOT NULL,
  research_task_id uuid NOT NULL,
  step_id uuid NULL,
  agent_version_id uuid NOT NULL,
  agent_actor_id uuid NOT NULL,
  requested_by uuid NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  policy_id uuid NOT NULL,
  policy_content_hash text NOT NULL CHECK (policy_content_hash ~ '^[0-9a-f]{64}$'),
  mode text NOT NULL CHECK (mode = 'CONTRACT_FAKE'),
  capability_id text NOT NULL,
  capability_version text NOT NULL,
  operation text NOT NULL,
  adapter_id text NOT NULL,
  adapter_version text NOT NULL,
  parameter_schema_hash text NOT NULL CHECK (parameter_schema_hash ~ '^[0-9a-f]{64}$'),
  skill_id text NOT NULL,
  skill_version text NOT NULL,
  strategy_id text NOT NULL,
  strategy_version text NOT NULL,
  harness_artifact_version_id uuid NOT NULL REFERENCES artifact_versions(id) ON DELETE RESTRICT,
  harness_content_hash text NOT NULL CHECK (harness_content_hash ~ '^[0-9a-f]{64}$'),
  parameters_artifact_version_id uuid NOT NULL REFERENCES artifact_versions(id) ON DELETE RESTRICT,
  parameters_content_hash text NOT NULL CHECK (parameters_content_hash ~ '^[0-9a-f]{64}$'),
  requested_parameters_hash text NOT NULL CHECK (requested_parameters_hash ~ '^[0-9a-f]{64}$'),
  parameters_byte_size integer NOT NULL CHECK (parameters_byte_size BETWEEN 1 AND 65536),
  reservation_id uuid NOT NULL UNIQUE,
  usage_record_id uuid NULL UNIQUE,
  trace_artifact_version_id uuid NULL REFERENCES artifact_versions(id) ON DELETE RESTRICT,
  trace_content_hash text NULL CHECK (trace_content_hash ~ '^[0-9a-f]{64}$'),
  retry_parent_id uuid NULL,
  status text NOT NULL CHECK (status IN (
    'REQUESTED','RUNNING','SUCCEEDED','FAILED','UNKNOWN_OUTCOME','CANCELLED')),
  row_version integer NOT NULL CHECK (row_version BETWEEN 1 AND 3),
  created_at timestamptz NOT NULL,
  started_at timestamptz NULL,
  finished_at timestamptz NULL,
  request_receipt_id uuid NOT NULL UNIQUE,
  start_receipt_id uuid NULL UNIQUE,
  finish_receipt_id uuid NULL UNIQUE,
  result_summary text NULL CHECK (octet_length(result_summary) <= 8192
    AND result_summary IS NFC NORMALIZED),
  error_code text NULL,
  UNIQUE (research_task_id, project_id, id),
  UNIQUE (research_task_id, id),
  UNIQUE (research_task_id, id, reservation_id),
  FOREIGN KEY (research_task_id, project_id)
    REFERENCES research_tasks(id, project_id) ON DELETE RESTRICT,
  FOREIGN KEY (research_task_id, step_id)
    REFERENCES research_task_steps(research_task_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (agent_version_id, project_id, agent_actor_id)
    REFERENCES agent_versions(id, project_id, actor_id) ON DELETE RESTRICT,
  FOREIGN KEY (policy_id, project_id)
    REFERENCES agent_tool_policies(id, project_id) ON DELETE RESTRICT,
  FOREIGN KEY (research_task_id, reservation_id, id)
    REFERENCES budget_reservations(research_task_id, id, operation_id) ON DELETE RESTRICT,
  FOREIGN KEY (research_task_id, reservation_id, usage_record_id)
    REFERENCES budget_usage_records(research_task_id, reservation_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (research_task_id, retry_parent_id)
    REFERENCES capability_invocations(research_task_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (research_task_id, project_id, request_receipt_id)
    REFERENCES research_task_command_receipts(research_task_id, project_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (research_task_id, project_id, start_receipt_id)
    REFERENCES research_task_command_receipts(research_task_id, project_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (research_task_id, project_id, finish_receipt_id)
    REFERENCES research_task_command_receipts(research_task_id, project_id, id) ON DELETE RESTRICT,
  CHECK (retry_parent_id IS DISTINCT FROM id),
  CHECK ((trace_artifact_version_id IS NULL) = (trace_content_hash IS NULL)),
  CHECK (started_at IS NULL OR started_at >= created_at),
  CHECK (finished_at IS NULL OR finished_at >= coalesce(started_at, created_at)),
  CHECK (
    (status = 'REQUESTED' AND row_version = 1 AND num_nonnulls(started_at,
      finished_at,start_receipt_id,finish_receipt_id,usage_record_id,
      trace_artifact_version_id,result_summary,error_code) = 0) OR
    (status = 'RUNNING' AND row_version = 2 AND started_at IS NOT NULL
      AND start_receipt_id IS NOT NULL AND num_nonnulls(finished_at,
      finish_receipt_id,usage_record_id,trace_artifact_version_id,result_summary,error_code) = 0) OR
    (status = 'CANCELLED' AND row_version = 2 AND started_at IS NULL
      AND start_receipt_id IS NULL AND finished_at IS NOT NULL
      AND finish_receipt_id IS NOT NULL AND usage_record_id IS NOT NULL) OR
    (status IN ('SUCCEEDED','FAILED','UNKNOWN_OUTCOME','CANCELLED') AND row_version = 3
      AND num_nonnulls(started_at,start_receipt_id,finished_at,finish_receipt_id,usage_record_id) = 5)),
  CHECK (CASE WHEN status IN ('FAILED','UNKNOWN_OUTCOME') THEN
    error_code IS NOT NULL AND error_code IN ('ADAPTER_UNAVAILABLE','INVALID_STATE_TRANSITION')
    ELSE error_code IS NULL END),
  CHECK (length(btrim(capability_id)) BETWEEN 1 AND 128 AND capability_id IS NFC NORMALIZED),
  CHECK (length(btrim(capability_version)) BETWEEN 1 AND 512 AND capability_version IS NFC NORMALIZED),
  CHECK (length(btrim(operation)) BETWEEN 1 AND 128 AND operation IS NFC NORMALIZED),
  CHECK (length(btrim(adapter_id)) BETWEEN 1 AND 128 AND adapter_id IS NFC NORMALIZED),
  CHECK (length(btrim(adapter_version)) BETWEEN 1 AND 512 AND adapter_version IS NFC NORMALIZED),
  CHECK (length(btrim(skill_id)) BETWEEN 1 AND 128 AND skill_id IS NFC NORMALIZED),
  CHECK (length(btrim(skill_version)) BETWEEN 1 AND 512 AND skill_version IS NFC NORMALIZED),
  CHECK (length(btrim(strategy_id)) BETWEEN 1 AND 128 AND strategy_id IS NFC NORMALIZED),
  CHECK (length(btrim(strategy_version)) BETWEEN 1 AND 512 AND strategy_version IS NFC NORMALIZED)
);
CREATE TABLE capability_invocation_refs (
  id uuid NOT NULL PRIMARY KEY,
  project_id uuid NOT NULL,
  research_task_id uuid NOT NULL,
  invocation_id uuid NOT NULL,
  receipt_id uuid NOT NULL,
  direction text NOT NULL CHECK (direction IN ('INPUT','OUTPUT')),
  research_question_version_id uuid NULL REFERENCES research_question_versions(id) ON DELETE RESTRICT,
  hypothesis_version_id uuid NULL REFERENCES hypothesis_versions(id) ON DELETE RESTRICT,
  claim_version_id uuid NULL REFERENCES claim_versions(id) ON DELETE RESTRICT,
  source_version_id uuid NULL REFERENCES source_versions(id) ON DELETE RESTRICT,
  artifact_version_id uuid NULL REFERENCES artifact_versions(id) ON DELETE RESTRICT,
  manuscript_version_id uuid NULL REFERENCES manuscript_versions(id) ON DELETE RESTRICT,
  content_hash text NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
  hash_scheme text NULL,
  FOREIGN KEY (research_task_id, project_id, invocation_id)
    REFERENCES capability_invocations(research_task_id, project_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (research_task_id, project_id, receipt_id)
    REFERENCES research_task_command_receipts(research_task_id, project_id, id) ON DELETE RESTRICT,
  CHECK (num_nonnulls(research_question_version_id,hypothesis_version_id,
    claim_version_id,source_version_id,artifact_version_id,manuscript_version_id) = 1),
  CHECK (CASE WHEN source_version_id IS NOT NULL OR manuscript_version_id IS NOT NULL
    THEN hash_scheme IS NOT NULL AND hash_scheme = 'sha256-cjson-v1'
    ELSE hash_scheme IS NULL END),
  CHECK (direction <> 'OUTPUT' OR artifact_version_id IS NOT NULL)
);
CREATE TABLE capability_invocation_events (
  id uuid NOT NULL PRIMARY KEY,
  project_id uuid NOT NULL,
  research_task_id uuid NOT NULL,
  invocation_id uuid NOT NULL,
  reservation_id uuid NOT NULL,
  receipt_id uuid NOT NULL UNIQUE,
  sequence integer NOT NULL CHECK (sequence BETWEEN 1 AND 4),
  invocation_row_version integer NOT NULL CHECK (invocation_row_version BETWEEN 1 AND 3),
  event_type text NOT NULL CHECK (event_type IN ('REQUESTED','STARTED','FINISHED','RECONCILED')),
  prior_status text NULL,
  new_status text NOT NULL CHECK (new_status IN (
    'REQUESTED','RUNNING','SUCCEEDED','FAILED','UNKNOWN_OUTCOME','CANCELLED')),
  reconciled_outcome text NULL CHECK (reconciled_outcome IN ('SUCCEEDED','FAILED','CANCELLED')),
  usage_record_id uuid NULL UNIQUE,
  actor_id uuid NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  occurred_at timestamptz NOT NULL,
  reason text NOT NULL CHECK (length(btrim(reason)) BETWEEN 1 AND 8192 AND reason IS NFC NORMALIZED),
  UNIQUE (research_task_id, project_id, id),
  UNIQUE (invocation_id, sequence),
  FOREIGN KEY (research_task_id, project_id, invocation_id)
    REFERENCES capability_invocations(research_task_id, project_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (research_task_id, invocation_id, reservation_id)
    REFERENCES capability_invocations(research_task_id, id, reservation_id) ON DELETE RESTRICT,
  FOREIGN KEY (research_task_id, project_id, receipt_id)
    REFERENCES research_task_command_receipts(research_task_id, project_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (research_task_id, reservation_id, usage_record_id)
    REFERENCES budget_usage_records(research_task_id, reservation_id, id) ON DELETE RESTRICT,
  CHECK (
    (event_type = 'REQUESTED' AND sequence = 1 AND invocation_row_version = 1
      AND prior_status IS NULL AND new_status = 'REQUESTED' AND usage_record_id IS NULL) OR
    (event_type = 'STARTED' AND sequence = 2 AND invocation_row_version = 2
      AND prior_status = 'REQUESTED' AND new_status = 'RUNNING' AND usage_record_id IS NULL) OR
    (event_type = 'FINISHED' AND usage_record_id IS NOT NULL AND
      ((sequence = 2 AND invocation_row_version = 2 AND prior_status = 'REQUESTED' AND new_status = 'CANCELLED') OR
       (sequence = 3 AND invocation_row_version = 3 AND prior_status = 'RUNNING'
        AND new_status IN ('SUCCEEDED','FAILED','UNKNOWN_OUTCOME','CANCELLED')))) OR
    (event_type = 'RECONCILED' AND sequence = 4 AND invocation_row_version = 3
      AND prior_status = 'UNKNOWN_OUTCOME' AND new_status = 'UNKNOWN_OUTCOME'
      AND usage_record_id IS NOT NULL)),
  CHECK (event_type = 'REQUESTED' OR prior_status IS NOT NULL),
  CHECK ((event_type = 'RECONCILED') = (reconciled_outcome IS NOT NULL))
);
```

No unresolved S2 execution column exists. Reservation operation_id equals the
invocation ID; the composite FK enforces this. A nullable step must equal the
reservation step using IS NOT DISTINCT FROM in the guard (MATCH SIMPLE alone
would not prove NULL equality). The usage tuple cannot charge another reservation.
Actor attribution separates requested_by from the immutable AgentVersion actor.

### 2.1 Complete additional index inventory

These are in addition to all declared PK/UNIQUE indexes; no implicit ORM indexes.

```sql
CREATE INDEX pr303_policy_registration ON agent_tool_policies(registration_task_id,project_id,receipt_id);
CREATE INDEX pr303_policy_registry ON agent_tool_policies(registry_artifact_version_id);
CREATE INDEX pr303_policy_creator ON agent_tool_policies(created_by);
CREATE INDEX pr303_policy_time ON agent_tool_policies(project_id,created_at,id);
CREATE INDEX pr303_permission_scope ON agent_tool_policy_permissions(policy_id,project_id);
CREATE INDEX pr303_permission_project ON agent_tool_policy_permissions(project_id,policy_id);
CREATE INDEX pr303_invocation_task_time ON capability_invocations(research_task_id,created_at,id);
CREATE INDEX pr303_invocation_project ON capability_invocations(project_id,research_task_id,id);
CREATE INDEX pr303_invocation_step ON capability_invocations(research_task_id,step_id);
CREATE INDEX pr303_invocation_version ON capability_invocations(agent_version_id,project_id,agent_actor_id);
CREATE INDEX pr303_invocation_actor ON capability_invocations(agent_actor_id);
CREATE INDEX pr303_invocation_requester ON capability_invocations(requested_by);
CREATE INDEX pr303_invocation_policy ON capability_invocations(policy_id,project_id);
CREATE INDEX pr303_invocation_harness ON capability_invocations(harness_artifact_version_id);
CREATE INDEX pr303_invocation_parameters ON capability_invocations(parameters_artifact_version_id);
CREATE INDEX pr303_invocation_trace ON capability_invocations(trace_artifact_version_id) WHERE trace_artifact_version_id IS NOT NULL;
CREATE INDEX pr303_invocation_retry ON capability_invocations(research_task_id,retry_parent_id) WHERE retry_parent_id IS NOT NULL;
CREATE INDEX pr303_invocation_usage ON capability_invocations(research_task_id,reservation_id,usage_record_id);
CREATE INDEX pr303_refs_owner ON capability_invocation_refs(invocation_id,direction,id);
CREATE INDEX pr303_refs_scope ON capability_invocation_refs(research_task_id,project_id,invocation_id);
CREATE INDEX pr303_refs_receipt ON capability_invocation_refs(research_task_id,project_id,receipt_id);
CREATE INDEX pr303_events_scope ON capability_invocation_events(research_task_id,project_id,invocation_id);
CREATE INDEX pr303_events_reservation ON capability_invocation_events(research_task_id,invocation_id,reservation_id);
CREATE INDEX pr303_events_actor ON capability_invocation_events(actor_id);
CREATE INDEX pr303_events_usage ON capability_invocation_events(research_task_id,reservation_id,usage_record_id);
```

```sql
CREATE UNIQUE INDEX pr303_refs_research_question ON capability_invocation_refs
  (invocation_id,direction,research_question_version_id) WHERE research_question_version_id IS NOT NULL;
CREATE INDEX pr303_refs_research_question_target ON capability_invocation_refs
  (research_question_version_id) WHERE research_question_version_id IS NOT NULL;
CREATE UNIQUE INDEX pr303_refs_hypothesis ON capability_invocation_refs
  (invocation_id,direction,hypothesis_version_id) WHERE hypothesis_version_id IS NOT NULL;
CREATE INDEX pr303_refs_hypothesis_target ON capability_invocation_refs
  (hypothesis_version_id) WHERE hypothesis_version_id IS NOT NULL;
CREATE UNIQUE INDEX pr303_refs_claim ON capability_invocation_refs
  (invocation_id,direction,claim_version_id) WHERE claim_version_id IS NOT NULL;
CREATE INDEX pr303_refs_claim_target ON capability_invocation_refs
  (claim_version_id) WHERE claim_version_id IS NOT NULL;
CREATE UNIQUE INDEX pr303_refs_source ON capability_invocation_refs
  (invocation_id,direction,source_version_id) WHERE source_version_id IS NOT NULL;
CREATE INDEX pr303_refs_source_target ON capability_invocation_refs
  (source_version_id) WHERE source_version_id IS NOT NULL;
CREATE UNIQUE INDEX pr303_refs_artifact ON capability_invocation_refs
  (invocation_id,direction,artifact_version_id) WHERE artifact_version_id IS NOT NULL;
CREATE INDEX pr303_refs_artifact_target ON capability_invocation_refs
  (artifact_version_id) WHERE artifact_version_id IS NOT NULL;
CREATE UNIQUE INDEX pr303_refs_manuscript ON capability_invocation_refs
  (invocation_id,direction,manuscript_version_id) WHERE manuscript_version_id IS NOT NULL;
CREATE INDEX pr303_refs_manuscript_target ON capability_invocation_refs
  (manuscript_version_id) WHERE manuscript_version_id IS NOT NULL;
```

## 3. Constrained receipt and task-event extensions

Preserve original receipt identity, material_version, hashes, result links and
replay shapes. Add only nullable columns, with no historical UPDATE/backfill.
Old commands must have all new result fields NULL; old DTOs/hash vectors remain
unchanged. Gateway results are recovered from saved concrete IDs, not current
invocation projections. The event names below describe task bookkeeping, not
new task states.

Explicit forward replacement of the delivered **pr304_command_names** CHECK
(the 0077 autogenerated CHECK was already removed by 0078):

```sql
ALTER TABLE research_task_command_receipts DROP CONSTRAINT pr304_command_names;
ALTER TABLE research_task_command_receipts ADD CONSTRAINT pr303_command_names CHECK (command_name IN (
  'create_research_task','create_task_plan','add_task_step','add_task_step_dependency','seal_task_plan','cancel_research_task',
  'bind_task_policies','reserve_task_budget','settle_task_budget','evaluate_task_termination','request_human_checkpoint','respond_human_checkpoint',
  'register_agent_tool_policy','request_capability_invocation','start_capability_invocation','finish_capability_invocation'));
ALTER TABLE research_task_command_receipts
  ADD COLUMN result_tool_policy_id uuid NULL,
  ADD COLUMN result_capability_invocation_id uuid NULL,
  ADD COLUMN result_capability_event_id uuid NULL,
  ADD COLUMN resulting_invocation_revision integer NULL,
  ADD CONSTRAINT pr303_receipt_policy_fk FOREIGN KEY (result_tool_policy_id,project_id)
    REFERENCES agent_tool_policies(id,project_id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
  ADD CONSTRAINT pr303_receipt_invocation_fk FOREIGN KEY (research_task_id,project_id,result_capability_invocation_id)
    REFERENCES capability_invocations(research_task_id,project_id,id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
  ADD CONSTRAINT pr303_receipt_event_fk FOREIGN KEY (research_task_id,project_id,result_capability_event_id)
    REFERENCES capability_invocation_events(research_task_id,project_id,id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
  ADD CONSTRAINT pr303_receipt_shape CHECK (
    (command_name = 'register_agent_tool_policy' AND result_tool_policy_id IS NOT NULL
      AND num_nonnulls(result_capability_invocation_id,result_capability_event_id,resulting_invocation_revision) = 0) OR
    (command_name IN ('request_capability_invocation','start_capability_invocation','finish_capability_invocation')
      AND num_nonnulls(result_tool_policy_id,result_capability_invocation_id,result_capability_event_id,resulting_invocation_revision) = 4
      AND resulting_invocation_revision BETWEEN 1 AND 3) OR
    (command_name NOT IN ('register_agent_tool_policy','request_capability_invocation','start_capability_invocation','finish_capability_invocation')
      AND num_nonnulls(result_tool_policy_id,result_capability_invocation_id,result_capability_event_id,resulting_invocation_revision) = 0));
CREATE INDEX pr303_receipt_policy ON research_task_command_receipts(result_tool_policy_id,project_id);
CREATE INDEX pr303_receipt_invocation ON research_task_command_receipts(research_task_id,project_id,result_capability_invocation_id);
CREATE UNIQUE INDEX pr303_receipt_event ON research_task_command_receipts(result_capability_event_id) WHERE result_capability_event_id IS NOT NULL;

ALTER TABLE research_task_events
  DROP CONSTRAINT pr304_event_names,
  DROP CONSTRAINT pr304_event_states,
  DROP CONSTRAINT pr304_event_reason,
  DROP CONSTRAINT pr304_event_stop_kind;
ALTER TABLE research_task_events
  ADD COLUMN result_tool_policy_id uuid NULL,
  ADD COLUMN result_capability_invocation_id uuid NULL,
  ADD COLUMN result_capability_event_id uuid NULL,
  ADD CONSTRAINT pr303_task_event_policy_fk FOREIGN KEY (result_tool_policy_id)
    REFERENCES agent_tool_policies(id) ON DELETE RESTRICT,
  ADD CONSTRAINT pr303_task_event_invocation_fk FOREIGN KEY (research_task_id,result_capability_invocation_id)
    REFERENCES capability_invocations(research_task_id,id) ON DELETE RESTRICT,
  ADD CONSTRAINT pr303_task_event_capability_fk FOREIGN KEY (result_capability_event_id)
    REFERENCES capability_invocation_events(id) ON DELETE RESTRICT,
  ADD CONSTRAINT pr303_event_names CHECK (event_type IN (
    'CREATED','PLAN_CREATED','STEP_ADDED','DEPENDENCY_ADDED','PLAN_SEALED','CANCELLED',
    'POLICIES_BOUND','BUDGET_RESERVED','BUDGET_SETTLED','TERMINATION_EVALUATED','CHECKPOINT_REQUESTED','CHECKPOINT_RESPONDED',
    'TOOL_POLICY_REGISTERED','CAPABILITY_REQUESTED','CAPABILITY_STARTED','CAPABILITY_FINISHED')),
  ADD CONSTRAINT pr303_event_states CHECK (
    (event_type = 'CREATED' AND prior_status IS NULL AND new_status = 'CREATED') OR
    (event_type = 'PLAN_CREATED' AND prior_status = 'CREATED' AND new_status = 'PLANNING') OR
    (event_type IN ('STEP_ADDED','DEPENDENCY_ADDED','PLAN_SEALED') AND prior_status = 'PLANNING' AND new_status = 'PLANNING') OR
    (event_type = 'CANCELLED' AND prior_status IN ('CREATED','PLANNING') AND new_status = 'CANCELLED') OR
    (event_type IN ('POLICIES_BOUND','BUDGET_RESERVED','BUDGET_SETTLED','TERMINATION_EVALUATED','CHECKPOINT_REQUESTED','CHECKPOINT_RESPONDED',
      'TOOL_POLICY_REGISTERED','CAPABILITY_REQUESTED','CAPABILITY_STARTED','CAPABILITY_FINISHED')
      AND prior_status IN ('CREATED','PLANNING','CANCELLED') AND new_status = prior_status)),
  ADD CONSTRAINT pr303_event_reason CHECK (CASE WHEN event_type IN (
    'CANCELLED','POLICIES_BOUND','BUDGET_RESERVED','BUDGET_SETTLED','TERMINATION_EVALUATED','CHECKPOINT_REQUESTED','CHECKPOINT_RESPONDED',
    'TOOL_POLICY_REGISTERED','CAPABILITY_REQUESTED','CAPABILITY_STARTED','CAPABILITY_FINISHED')
    THEN reason IS NOT NULL AND length(btrim(reason)) BETWEEN 1 AND 8192 AND reason IS NFC NORMALIZED ELSE reason IS NULL END),
  ADD CONSTRAINT pr303_event_stop_kind CHECK (event_type IN (
    'BUDGET_RESERVED','BUDGET_SETTLED','TERMINATION_EVALUATED','CAPABILITY_REQUESTED','CAPABILITY_FINISHED')
    OR NOT (stop_human OR stop_policy OR stop_budget OR stop_repeated_failure OR stop_no_improvement OR stop_success)),
  ADD CONSTRAINT pr303_task_event_shape CHECK (
    (event_type = 'TOOL_POLICY_REGISTERED' AND result_tool_policy_id IS NOT NULL
      AND result_capability_invocation_id IS NULL AND result_capability_event_id IS NULL) OR
    (event_type IN ('CAPABILITY_REQUESTED','CAPABILITY_STARTED','CAPABILITY_FINISHED')
      AND num_nonnulls(result_tool_policy_id,result_capability_invocation_id,result_capability_event_id) = 3) OR
    (event_type NOT IN ('TOOL_POLICY_REGISTERED','CAPABILITY_REQUESTED','CAPABILITY_STARTED','CAPABILITY_FINISHED')
      AND num_nonnulls(result_tool_policy_id,result_capability_invocation_id,result_capability_event_id) = 0));
CREATE INDEX pr303_task_event_policy ON research_task_events(result_tool_policy_id);
CREATE INDEX pr303_task_event_invocation ON research_task_events(research_task_id,result_capability_invocation_id);
CREATE INDEX pr303_task_event_capability ON research_task_events(result_capability_event_id);
```

Retain pr304_event_prior and pr304_event_stop_slice, including NOT stop_success.
No state CHECK on research_tasks/research_task_steps changes. Receipt→result
cycles alone are deferred, so task revision, receipt, reservation/usage and result
rows can be flushed in that order. Policy registration's task is only the command
owner; its policy can be used by other tasks in the same project.

## 4. Guard functions, trigger attachment and whole-state validation

The algorithms below are normative bodies, as in PR3-04, not optional suggestions.
Every function uses PL/pgSQL invoker rights with fixed
`SET search_path = pg_catalog, public, pg_temp`; no SECURITY DEFINER, GUC,
trigger-depth exemption, stored transaction marker, savepoint or bypass token.
Trigger functions return NEW on immediate admission and NULL on deferred checks;
helpers return void. Nullable comparisons use IS DISTINCT FROM. Existing guards
not explicitly extended remain unchanged. No trigger acquires advisory locks
after row locks. Normal-role SQL uses the same §5 protocol and receives the same
constraint enforcement; SQL is not proof of authenticated credential possession.

### 4.1 New immediate functions and triggers

| New function | Exact required body behavior |
| --- | --- |
| pr303_immutable() | Reject every UPDATE, including no-op, and DELETE with 23514/pr301_immutable. |
| pr303_policy_insert_guard() | Require new policy's registration task and receipt each with xmin = pg_current_xact_id()::xid, exact project/revision and register_agent_tool_policy command; creator=receipt.actor_id and created_at=receipt.completed_at in [transaction_timestamp(),clock_timestamp()]. Task nonterminal CREATED/PLANNING. Verify current persisted HUMAN OWNER/binding/membership at advancing DB time as PR3-04 does; Application independently verifies credentials. Registry is exact same-project historically frozen ArtifactVersion with equal owning hash. Exact policy canonical/hash/set validation runs at task final check after all permission INSERTs. |
| pr303_permission_insert_guard() | Require policy xmin = pg_current_xact_id()::xid and its same-transaction registration receipt/task. Exact policy/project; reject aliases latest/current/main/master, wildcard/prefix/regex semantics and nontrimmed pins. Permission rows are insert-only, even during construction. |
| pr303_invocation_guard() | Reject DELETE. INSERT only REQUESTED/revision 1, request receipt/task/reservation all current xmin; reservation.operation_id=invocation.id, budget_id=bound task budget, same nullable step, same receipt/time. All pins and typed material in §§6–8 validated. UPDATE requires OLD not terminal and OLD.xmin different from current xid, new task and relevant start/finish receipt fresh; exactly revision+1 and legal §4.2 transition. Preserve all request fields, input pins, ID/project/task/step/version/actor/policy/reservation/retry parent/request receipt/created_at. Start may set only status,row_version,started_at,start_receipt_id. Finish may set only status,row_version,finished_at,finish_receipt_id,usage_record_id,trace artifact/hash,result_summary,error_code. Enforce exact receipt operation, actor/time, and fresh usage under same reservation for finish. No second invocation write in one command. |
| pr303_ref_insert_guard() | Require fresh task and receipt. INPUT requires fresh invocation REQUESTED and its request receipt; OUTPUT requires FINISHED SUCCEEDED event's finish receipt and fresh invocation terminal write, or its fresh RECONCILED SUCCEEDED event for an immutable UNKNOWN row. Require same project/task and output artifact family only. Call existing pr301_validate_input with task and six concrete targets/hash/scheme; no scientific write. No output on FAILED/CANCELLED/UNKNOWN observations. |
| pr303_event_insert_guard() | Require fresh task/receipt, exact result pointers and command mapping; same invocation/project/task/reservation, actor=receipt.actor_id, occurred_at=receipt.completed_at within DB transaction interval, reason=task event reason (deferred if not inserted yet). REQUESTED/STARTED/FINISHED require invocation current xmin, matching saved revision/status/receipt. RECONCILED requires committed UNKNOWN_OUTCOME revision 3, fresh final usage, no previous reconciliation or final usage; no invocation UPDATE. Check sequence/adjacent prior status, usage tuple and is_final/outcome correspondence. Indexed owning/previous-row lookups only. |

Exact new attachment inventory, all FOR EACH ROW and NOT DEFERRABLE:

```sql
CREATE TRIGGER pr303_policy_insert BEFORE INSERT ON agent_tool_policies FOR EACH ROW EXECUTE FUNCTION pr303_policy_insert_guard();
CREATE TRIGGER pr303_policy_immutable BEFORE UPDATE OR DELETE ON agent_tool_policies FOR EACH ROW EXECUTE FUNCTION pr303_immutable();
CREATE TRIGGER pr303_permission_insert BEFORE INSERT ON agent_tool_policy_permissions FOR EACH ROW EXECUTE FUNCTION pr303_permission_insert_guard();
CREATE TRIGGER pr303_permission_immutable BEFORE UPDATE OR DELETE ON agent_tool_policy_permissions FOR EACH ROW EXECUTE FUNCTION pr303_immutable();
CREATE TRIGGER pr303_invocation_write BEFORE INSERT OR UPDATE OR DELETE ON capability_invocations FOR EACH ROW EXECUTE FUNCTION pr303_invocation_guard();
CREATE TRIGGER pr303_ref_insert BEFORE INSERT ON capability_invocation_refs FOR EACH ROW EXECUTE FUNCTION pr303_ref_insert_guard();
CREATE TRIGGER pr303_ref_immutable BEFORE UPDATE OR DELETE ON capability_invocation_refs FOR EACH ROW EXECUTE FUNCTION pr303_immutable();
CREATE TRIGGER pr303_event_insert BEFORE INSERT ON capability_invocation_events FOR EACH ROW EXECUTE FUNCTION pr303_event_insert_guard();
CREATE TRIGGER pr303_event_immutable BEFORE UPDATE OR DELETE ON capability_invocation_events FOR EACH ROW EXECUTE FUNCTION pr303_immutable();
```

Existing receipt/event/link immutability stays unconditional, including within
its creation transaction. Existing reservation/usage UPDATE/DELETE denial stays
unconditional; settlement means new budget_usage_records, never editing usage.
Immediate guards on every new child force a fresh root; appending permissions,
refs or events to committed receipts therefore cannot evade deferred checks.

### 4.2 Lifecycle and reconciliation

| From | Command / event | To | Exact conditions |
| --- | --- | --- | --- |
| absent | request / REQUESTED | REQUESTED revision 1 | One new reservation and complete inputs. |
| REQUESTED | start / STARTED | RUNNING revision 2 | All fresh admission checks; reservation not final/expired; §6 exact-cap exception only. |
| REQUESTED | finish / FINISHED | CANCELLED revision 2 | Proven no dispatch; variable usage zero, admission counts retained; no start time. |
| RUNNING | finish / FINISHED | SUCCEEDED / FAILED / UNKNOWN_OUTCOME / CANCELLED revision 3 | Trusted bounded observation; cancelled only with confirmed action outcome, otherwise UNKNOWN_OUTCOME. |
| UNKNOWN_OUTCOME | finish(kind=RECONCILE) / RECONCILED | Stored UNKNOWN_OUTCOME unchanged | One attributable final usage and event sequence 4; effective reconciled outcome on event only. |

All other transitions reject. A start commits before fake execution. A proven
pre-action dispatch failure after start is FAILED. Crash/uncertain execution is
UNKNOWN_OUTCOME, never blindly redispatched. UNKNOWN maps to budget outcome
UNKNOWN/is_final=false, retains the full reserved charge and occupancy. At most
one subsequent reconciliation can supply SUCCEEDED/FAILED/CANCELLED final usage;
original unknown invocation/usage/event/receipt stay immutable. An ordinary
finish of an already terminal row is denied; exact command replay returns its
receipt. New retry requires a new invocation ID, command and reservation after
fresh admission, with retry_parent_id pointing to same-task terminal failure or
unknown; unknown must first be finally reconciled, never overlap its charge as
an implicit refund. No automated recovery is introduced.

### 4.3 Forward changes to delivered functions (no new deferred triggers)

| Existing function / retained trigger | Required forward delta |
| --- | --- |
| pr301_receipt_insert_guard / pr301_receipt_insert | Admit four §3 command names with exact new result shape. Preserve fresh task xmin, exact revision/project, old command checks and immutable receipt insertion. |
| pr301_task_guard / pr301_task_guard | Retain exactly one task write, material/seal/policy/terminal restrictions. Gateway uses status-preserving revision bump only; CANCELLED allows finish bookkeeping only. No gateway command may bind policies, edit graph or alter task intent/times. Deferred receipt proves the exact exception. |
| pr304_child_guard / pr304_reservation_guard, pr304_usage_guard and other existing safety child triggers | Add request_capability_invocation as an allowed reservation owner and finish_capability_invocation as an allowed usage owner, including CANCELLED bookkeeping for finish. Keep all original command cases and mutation denials. Fresh task/receipt, same observed timestamp, bound bundle, operation/step and accounting rules still mandatory. No public capability bypass. |
| pr304_validate_safety (existing helper) | Treat request as reserve, finish as settle for accounting, cap/stop/streak/history computation. Preserve exact old branches. Request event may set the computed budget/failure/progress flags; finish likewise. Start is zero new spend and never creates usage/reservation or clears sticky stops. Admission history still validated at each original receipt revision. |
| pr301_graph_final_guard / pr301_task_final | Preserve all existing graph/history checks and the one pr304_validate_safety call; call new pr303_validate_gateway(NEW.id) exactly once at the end. |
| pr301_receipt_complete / pr301_receipt_complete_commit | Preserve six planning and six safety cases, with new columns NULL for those cases; add four gateway mappings and cardinalities below. Safety result counting permits exactly one reservation for request and exactly one usage for finish in addition to old owners. All other old no-extra-effect checks remain. Gateway self-transitions require no step/input/dependency or policy-bundle changes. |

Existing pr301_event_insert_guard, pr301_receipt_link_guard and their task/step
history/link triggers keep fresh receipt attribution, task state equality and
immutability. §3 result pointers are compared by the extended receipt check.
pr301_validate_input and graph-cycle functions are unchanged.

New helper `pr303_validate_gateway(p_task uuid) RETURNS void` is the sole new
whole-gateway validator, called only from the existing task final guard. It must:

1. Validate every policy registered by this command: ≤256 permissions, exact
   normalized sets/hash/capability-set hash from §7; registry pin scope/hash;
   no orphan permission, no extra policy under any nonregistration receipt.
2. Validate each task invocation's immutable policy/version/actor binding,
   tool-policy token/capability-set hash equality, exact approved registry pins,
   parameters/harness/trace artifact scope/freeze/hash, reservation operation/
   nullable step/budget identity and saved byte size 1..65536. Total INPUT+OUTPUT
   rows ≤256 per invocation, including later reconciliation outputs. Revalidate
   owning frozen hashes with pr301_validate_input; outputs only candidate artifacts.
3. Require gapless event history 1..row_version, with an optional sequence 4 only
   for reconciled UNKNOWN; saved projection equals the last lifecycle event.
   Adjacent statuses/times and exact actor/command/receipt/result pointers agree.
   Every invocation has exactly its request reservation, one initial unknown or
   final usage on finish, and at most one final reconciliation on unknown. No
   second observation, post-final usage, missing charge, orphan ref or event.
4. Reconstruct admission in task receipt revision order, not from today's totals:
   task-wide calls count every request (including failed/cancelled/unknown/retries)
   across policy/version changes; occupied slots are REQUESTED/RUNNING or unknown
   without final usage, across policies. Compare historical occupancy/counts to
   each admitting policy limits. No policy switch resets counters. New request
   must fit both tool and existing resource caps and all checkpoints. Start
   proves §6, expiry/availability and policy admission without a second charge.
5. Require all new rows/effects owned by the current task mutation/receipt, correct
   timestamps and operation-specific cardinality. Registration authority is
   current HUMAN OWNER; fresh fake actions require trusted context in Application
   plus current persisted membership/version facts. SQL guards enforce facts but
   cannot create or serialize FakeConsumerCapability.

Deferred receipt mapping/cardinality (one task event, existing receipt-event
link, zero step events for every row):

| Command | Task event | Exact new effects |
| --- | --- | --- |
| register_agent_tool_policy | TOOL_POLICY_REGISTERED | One policy with registration_task_id/receipt; exactly its submitted permission set; policy-only result pointers. No invocation/reservation/usage. |
| request_capability_invocation | CAPABILITY_REQUESTED | One REQUESTED invocation, one REQUESTED event, exact INPUT refs, one reservation; result policy/invocation/event/revision=1. |
| start_capability_invocation | CAPABILITY_STARTED | One REQUESTED→RUNNING update, one STARTED event; no new refs/accounting; saved revision=2. |
| finish_capability_invocation | CAPABILITY_FINISHED | One finish update/event and one matching usage; or one RECONCILED event/final usage with zero invocation writes. Exactly declared OUTPUT refs if confirmed success. Saved revision is 2/3 per lifecycle, remains 3 on reconciliation. |

No extra safety policies/checkpoints or graph effects on gateway receipts. All
three task-event result IDs equal receipt result IDs; capability event points
back to that receipt/invocation/policy, same actor, task revision and time. New
registration policy matches receipt creator/project/task. Reason/time equality
applies to all gateway effects. The receipt must capture exactly its event and
charge IDs; subsequent events never enlarge its replay result.

Exactly-once means **one existing task final-state firing and one existing
receipt-completeness firing per successful command**, not one trigger for every
child. research_tasks is written once and one receipt inserted once; old guard
rejects a second task write even across flushes. Every new child checks
`xmin = pg_current_xact_id()::xid` on the correct root (and its new receipt), as
PR3-01/PR3-04 and migration 0057 require. No new deferred constraint trigger is
attached to any of the five tables. Existing per-row graph cycle checks remain.
Force SET CONSTRAINTS ALL IMMEDIATE before commit under locks. Denial/replay
write no task, receipt, event or charge. In particular a missing final effect
cannot be masked by an early flush or appending to an old receipt.

## 5. Exact lock, transaction, replay and read recipes

Use synchronous PostgreSQL 18 READ COMMITTED writes, autoflush off, existing
SqlAlchemyUnitOfWork. Connection startup lock_timeout=10s,
statement_timeout=30s, connect_timeout=10; restore pool defaults on return.
Before **any** Application SQL, including auth/clock/replay/SET, first statement:

```sql
LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts,
claim_versions, claims, hypothesis_versions, hypotheses,
literature_source_project_links, literature_sources, manuscript_versions,
project_memberships, project_role_assignments, projects, publications,
research_question_versions, research_questions, source_versions IN SHARE MODE;
```

This order matches the approved [draft §6](../proposals/PR3-03_Capability_Gateway_Invocation_Contract_DRAFT.md#6-exact-locks-transactions-budget-composition-and-replay):
project → pr301 command → pr301 task → pr302 actor → pr302 version → rows.
The key order in both §5 and the §6 accounting composition is exactly this draft
§6 order. Delivered safety lock_write is at
src/researchbase/persistence/task_safety_repository.py:51–74: first SHARE (56),
project (58), pr301 command/task (60–64), task/step rows (65–71).
Delivered S1 actor/version keys are at
src/researchbase/persistence/agent_version_repository.py:78–80.
These are two delivered sequences to compose, not a claim that the existing
safety repository already takes pr302 keys. §12 records their source evidence.
Then acquire in this exact order:

1. `SELECT rb_phase2_lock_project(:project_id)`.
2. `SELECT pg_advisory_xact_lock(hashtextextended(:key,0))` for
   `pr301:command:<project_uuid>:<authenticated_actor_uuid>:<command_uuid>`.
3. Same SQL for `pr301:task:<task_uuid>`, then `pr302:actor:<actor_uuid>`,
   then `pr302:version:<version_uuid>`. Actor in pr302 key is target Agent actor,
   not necessarily caller. Resolve immutable version→actor after project/command
   locks without row locking; reread under both keys before diagnostics. For
   registration there is no target version/actor and the two pr302 keys are
   inapplicable; do not invent dummy keys. UUID text is canonical lowercase.
4. research_tasks by ID FOR UPDATE; research_task_steps by ID FOR UPDATE in
   ascending ID; read research_task_step_dependencies by predecessor/dependent,
   research_task_inputs and research_task_step_inputs by ID.
5. Read safety rows in delivered order, each ascending primary key:
   budget_reservations, budget_usage_records, checkpoint_policies,
   checkpoint_policy_dataset_scopes, checkpoint_policy_metric_scopes,
   execution_budgets, human_checkpoints, termination_policies.
   Mutable human_checkpoints rows use FOR UPDATE; immutable rows need reads.
6. agent_availability by agent_version_id FOR UPDATE, then immutable
   agent_versions read under its version key. Registration has no target here.
7. Five new tables, each ascending primary key: agent_tool_policies,
   agent_tool_policy_permissions, capability_invocations,
   capability_invocation_refs, capability_invocation_events. Only mutable
   invocation row requires FOR UPDATE. Absent IDs are protected by earlier keys.

No advisory key after row locking, no SHARE on writable task/agent/policy/
invocation tables, no table-lock upgrade or competing availability namespace.
The existing safety repository's combined lock_write cannot simply be called
and followed by pr302 locks: compose the prefix so both pr302 keys precede
research_tasks row locking. In the implementation, factor the delivered prefix
and task-row phase into composable internal operations: existing safety callers
keep their combined lock_write recipe; the gateway inserts actor/version keys
between the same prefix and row phase. Preserve after_wait replay/entitlement
callbacks after each wait in both paths. This is a future implementation
obligation; no repository code changes in this documentation PR.
S1 availability writers retain their accepted keys;
two tasks sharing a version coordinate through the same actor/version keys.

After **every blocking wait**, including first SHARE, project/advisory/row locks,
DML waits and constraint forcing: revalidate trusted credentials and current read
entitlement; look up original receipt by project/authenticated actor/command.
Identical normalized hash returns its **saved** result before write role, task or
invocation CAS, lifecycle, availability, expiry, checkpoints or budget checks.
Different hash yields IDEMPOTENCY_CONFLICT after read entitlement. No receipt:
freshly check write role, project/archive scope, exact frozen hashes/pins,
advancing DB clock, policy, availability, gates, stop and revisions before effects.
Never disclose receipt/existence/conflict without current read entitlement.
A preliminary successful check never survives a later wait without reevaluation.
Mutation's own fresh receipt does not mean it is a completed replay: bypass is
only a prior committed receipt; current-xmin effects must finish validation.

Preallocate stable result IDs outside retry; verify retained artifact/registry
bytes before locks, then reread DB pins under locks. No ArtifactStore, provider,
filesystem, network, process or cancellation I/O under locks. Set one fresh
DB-observed command timestamp and copy to receipt/event/new rows; retain
transaction_timestamp() <= timestamp <= clock_timestamp(). Expiry/authority
checks use advancing clock_timestamp(), not the saved provenance timestamp.

Common successful write order: task revision once → receipt with deferred result
FKs → policy+permissions, or reservation then invocation+inputs, or invocation
start, or usage then invocation finish → capability event → reconciliation
outputs if any → task event → existing research_task_receipt_events link.
Ordinary finish outputs can be inserted after its capability event too. Flush as
needed; do not create another accepted command or nested UoW. Force all deferred
constraints and repeat final fresh local credential/authority checks after the
last possible wait; commit once. Error rolls all effects back.

Only SQLSTATE **40001 / 40P01** retries, **max 3 total attempts**, each a fresh
whole transaction with identical material/identity/stable IDs and fresh checks.
55P03/57014 never automatically retry; no adapter execution retry. An uncertain
commit uses formal receipt lookup with the original identity, never assumes
rollback or invents command IDs. A committed start is the only permission for
one finite fake call outside the transaction; a lost start response must be
reconciled, not interpreted as permission to redispatch. No persistent dispatcher
or unattended recovery is admitted.

All queries and explicit receipt reconciliation call existing begin_formal_read
before SQL: one REPEATABLE READ READ ONLY snapshot, autoflush off; no SHARE,
advisory/row locks, write/repair, nested session or second transaction. Entitlement,
policy, refs, charges and events come from that snapshot. Sort invocation list by
created_at/id, events by sequence, refs by direction/family/UUID. Project read
roles are existing OWNER/RESEARCHER/REVIEWER/APPROVER/VIEWER. Archived history
and disabled versions remain readable under current entitlement. Snapshot time
labels current projections; reads promise no later revocation visibility.

## 6. Trusted in-UoW accounting seam (D303-04)

This §6 composition uses exactly the draft §6 / pack §5 key order:
project → pr301 command → pr301 task → pr302 actor → pr302 version → rows.
Delivered safety sequence: src/researchbase/persistence/task_safety_repository.py:51–74;
delivered S1 keys: src/researchbase/persistence/agent_version_repository.py:78–80.
Factor the prefix as §5 specifies so pr302 keys precede task row locks.

New internal `GatewayAccounting` composition accepts an already open locked UoW,
repository ports, fresh receipt/task/time, verified principal and injected
**existing FakeConsumerCapability** by object identity. Its closed operations
are `reserve_in_uow` and `settle_in_uow` (both **new in PR3-03**). Neither owns
begin/commit/rollback, reacquires locks, increments task revision, inserts a second
receipt/event, nor calls TaskSafetyService.execute. Factor and reuse delivered
balances/causes/gates/settlement/streak rules; do not copy a second accounting
ledger or change SafetyCommand hashes. The gateway owns the one command receipt
and task event; the seam returns the reservation/usage row and computed stop
flags for that event. A failure leaves no gateway or safety effects.

Preserve identity-based trust at composition; an arbitrary new capability object,
JSON flag, actor type, public request argument or Agent constructor grants nothing.
Public reserve/settle and gateway request/start/finish cannot obtain fake trust;
HTTP/CLI use the same Application boundary and deny executable actions absent
injected trust. No Serializable fake capability field in any DTO/hash.

Request reserves worst case using operation_id=invocation.id and exact nullable
step; finish settles the same reservation. Existing finite six-place decimal
ResourceVector dimensions remain unchanged. Measurements cannot exceed reserved
upper bounds; count fields retain admitted attempt counts on failure/cancellation.
Proven no dispatch means zero variable consumption, **not** reversal of admitted
call counters. UNKNOWN observation equals full worst case, retains occupancy,
and never advances final failure/progress streaks. One final usage only under
existing pr304_usage_one_final; reconciliation is append-only. experiment_runs,
code_iterations and tree_nodes remain zero for this fake. Tool call count is a
policy cap, not a new ResourceVector dimension. Stop flags are historical OR,
never cleared by cheaper settlement, policy change, timeout or replay.

The only executable fake classification is one llm_calls admission per echo;
reserve agent_steps=0, llm_calls=1, search_calls=0, code_iterations=0,
experiment_runs=0, tree_nodes=0, gpu_hours="0.000000",
token_cost="0.125000", wall_time_seconds=60. Use existing fake-usd-v1 pricing
basis; no real provider pricing is implied. Request deadline_seconds is 1..60,
within remaining task wall bound. observed_depth and observed_parallel_branches
are rederived exactly as PR3-04; NULL step has depth 0. Trusted measured fake
variable consumption is zero cost/GPU/time; admitted integer counts stay reserved.
UNKNOWN uses the full vector. This fixture charges contracts, not model science.

### 6.1 Exact-cap sticky-stop start: separate frozen case

A **fresh reservation** after any sticky stop or an exhausted bound is denied.
Equality for an otherwise admitted request succeeds: existing charge+new worst
case <= every cap, tool request count <= max_tool_calls, occupancy <= parallel
cap. Its CAPABILITY_REQUESTED event records stop_budget when the reservation
exactly exhausts a positive resource bound. The invocation already owns that
capacity; start is not another reservation.

Start may disregard **only** the stop_budget flag first introduced by **that
invocation's own request receipt**, attributable solely to its exact-cap
reservation. Require no earlier sticky stop; no later event carrying any stop
flag (even a later BUDGET_EXHAUSTED evaluation); no HUMAN/POLICY/failure/progress
stop on its request; current task not CANCELLED; active Agent, unchanged exact
policy/registry, all required latest checkpoints approved, no final usage or
prior start, now strictly before reservation.deadline and task wall deadline.
All capacity bounds must still hold including this reservation. A tool-call cap
at equality likewise admits that one reserved call; it does not admit another.
Missing attribution fails closed. A newly observed timeout/revocation/checkpoint
block always denies start, including when the only historical flag was its own.

Start keeps task-event stop flags false and history sticky; it never clears the
request flag or reserves/charges again. This exception is serialized under the
same locks against stop/availability writers. An admitted finite fake may finish
after stop; later call admission is denied. Finish/reconciliation are attributable
bookkeeping after stop/cancellation and do not require active availability or
fresh spend authority; they still require current read entitlement, trusted
consumer context, exact charge ownership and no prior final settlement.

## 7. Policy, routing, retained material and hashes (D303-03)

Exact permission key is (capability_id, capability_version, operation, adapter_id,
adapter_version, parameter_schema_hash). Case-sensitive NFC exact equality only;
reject leading/trailing whitespace, unpinned aliases latest/current/main/master,
wildcards, prefix/regex patterns or inferred fallback. Duplicate complete
key+effect rejects; matching ALLOW and DENY rows may coexist and **DENY wins**.
No matching ALLOW, empty policy or absent binding denies. max_tool_calls defaults
50 and max_parallel_invocations defaults 1; both finite positive ints, not bools.
Counts span the task across policy/version changes. Description text, popularity,
model request, role, checkpoint and A0–A3 ceilings grant no tool authority.

Resolve agent_versions.tool_policy_version to exactly one project/version row;
require its capability_set_hash equals the version pin, saved policy_content_hash
and registry hash agree. No updating AgentVersion to attach a policy. Current
agent_availability must be ACTIVE on request/start. Exact artifacts resolve via
artifact_versions.artifact_id → artifacts.project_id; NULL/global project denies.
Require FROZEN or historically SUPERSEDED with frozen_at/content_hash and exact
owning hash. ArtifactVersion has no hash_scheme: never select or invent one.
Parameter and registry byte content is retained before the gateway commands;
read/verify bytes outside locks and compare immutable DB pins under locks.

`SkillRegistryLoader`, `SkillRouter`, `RoutingPolicy`, `CapabilityPolicy` are
**new in PR3-03**, bounded Application values/services, no package auto-discovery
or arbitrary import. Registry manifest has exactly schema_version=1 and entries
(a set of ≤256 RegistryEntry values). RegistryEntry closed fields: skill_id,
skill_version, strategy_id, strategy_version, executable:bool, allowed_phases
(sorted unique integer set; this slice requires 3), capability_id,
capability_version, operation, adapter_id, adapter_version, parameter_schema_hash,
license_id, intake_artifact_version_id, intake_content_hash. Pins nonblank NFC
≤512 (IDs/operation ≤128); intake is same-project frozen artifact. Entry key is
skill/version/strategy/version/permission key; duplicates reject. Manifest is
canonical JSON in a frozen ArtifactVersion; owning artifact content hash is
retained as registry_content_hash, not relabeled. Intake bytes document license,
exact executable revision, scripts, transitive capabilities, data exposure,
review and rollback; a reference-only executable=false entry can never execute.
Only the fake tuple below can have executable=true admitted in this slice.

Routing intersects current Phase, authenticated authority, project disclosure,
exact policy, pinned registry and task safety. No ranking can override exclusions.
Select exact requested eligible entry; ambiguous entries deny. Freeze skill,
strategy, adapter, schema and effective policy hashes in invocation. Reject
self-install, governing-file edits, changing pins, or same-execution policy/harness
weakening; reviewed changes require new retained registry/policy/version and new
admission. No config/library description is an executable locked dependency.
Harness pin must equal AgentVersion.configuration_artifact_version_id and its
configuration_content_hash; that retained S1 configuration supplies the existing
HarnessManifest. No new fingerprint entity or S2 identifier.

### 7.1 Closed fake parameters and canonical inputs

Only tuple: capability_id=`fake_capability`, capability_version=`1.0.0`,
operation=`echo`, adapter_id=`fake_in_process`, adapter_version=`1.0.0`.
The schema digest is SHA-256-canonical-JSON of this exact schema (schema_vector
below); manual closed validation requires no new dependency. Arguments have
exactly message:NFC string 0..1024 characters and outcome equal one of the four
terminal literals below, no extras. Fake is pure in-process deterministic echo;
success summary equals message, failure summary is `Fake failure.`, unknown
summary `Fake outcome unknown.`, cancellation summary `Fake cancelled.`.
FAILED returns existing ADAPTER_UNAVAILABLE; UNKNOWN_OUTCOME returns existing
INVALID_STATE_TRANSITION; others error_code=NULL. No arbitrary exception text.
Fake returns no output/trace by default. Fixtures may bind already retained
same-project frozen candidate artifacts; the fake never creates scientific rows.

Parameter bytes are the exact canonical JSON encoding of the normalized closed
arguments, ≤65536 bytes; requested_parameters_hash hashes that object with
sha256-cjson-v1. parameters_byte_size must equal owning artifact_versions.byte_size
(non-NULL) and verified retained bytes length. parameters_content_hash is the
ArtifactVersion owning hash; do not assume it equals the parameters hash.
Result summary is plain NFC text ≤8192 UTF-8 bytes, never a JSON semantic object.

All hashes use existing canonical_json_bytes / sha256_canonical_json. Normalize
NFC first (helpers do not normalize), UUIDs lowercase, finite exact decimals as
six-place strings, integers as JSON integers; reject bool-as-int, excess decimal
scale, NaN/infinity, duplicates and unknown fields before sorting. Fixed policy
hash envelope has exactly type="AgentToolPolicy", material_version=1, content.
Content has exactly project_id, version, capability_set_hash, permissions,
max_tool_calls, max_parallel_invocations, filesystem_scope, network_scope,
compute_scope, external_effect_scope, registry_artifact_version_id,
registry_content_hash. Permission elements have exactly the six key fields plus
effect, sorted by the six-key tuple then effect. Include every default and NULL;
exclude generated policy/permission IDs, registration task/receipt, creator/time,
content_hash and hash_scheme. Policy scientific scope is project material.

capability_set_hash has envelope type="CapabilitySet", material_version=1,
entries: sorted distinct six-key dictionaries **without effect** from permissions
(including denied keys). This deduplication is a projection across ALLOW/DENY,
not permission to accept duplicate submitted key+effect. The capability set grants
nothing; only exact effective permissions do. DB reconstructs both envelopes and
compares stored hashes using existing pr304_canonical_policy_json and built-in
encode(sha256(convert_to(serialized,'UTF8')),'hex'). No pgcrypto/dependency.
Cross-layer non-ASCII parity is mandatory.

### 7.1a Exact SQL reconstruction and Python parity

The existing serializer pr304_canonical_policy_json in 0078 lines 298–321
recursively sorts object keys with COLLATE "C", emits no separator whitespace,
preserves array ordinality, and uses JSONB text for strings/bools/null. Its number
branch accepts only text matching `^-?(0|[1-9][0-9]*)$`; noninteger JSON numbers
raise 23514/pr301_validation. It does not sort arrays or normalize NFC. Python
uses ensure_ascii=False, sort_keys=True, separators=(",", ":"); normalize NFC,
sets and exact decimal values before either serializer. Policy keys are ASCII,
so C ordering and Python ordering agree. Unicode values remain literal UTF-8.

The forward validator must reconstruct policy material from the typed rows with
this exact SELECT (p_policy is its UUID argument); JSONB is transient hash
material only. The six-key tuple order is capability_id, capability_version,
operation, adapter_id, adapter_version, parameter_schema_hash, followed by effect
for permissions. Duplicate submitted tuple+effect rejects before persistence;
the DISTINCT projection below intentionally removes effect for CapabilitySet.
Every textual sort uses COLLATE "C", independent of database locale.

```sql
WITH p AS (
  SELECT * FROM agent_tool_policies WHERE id = p_policy
), permission_rows AS (
  SELECT q.* FROM agent_tool_policy_permissions q JOIN p ON p.id = q.policy_id
), permission_set AS (
  SELECT coalesce(jsonb_agg(jsonb_build_object(
    'capability_id', capability_id, 'capability_version', capability_version,
    'operation', operation, 'adapter_id', adapter_id,
    'adapter_version', adapter_version, 'parameter_schema_hash', parameter_schema_hash,
    'effect', effect) ORDER BY capability_id COLLATE "C", capability_version COLLATE "C",
    operation COLLATE "C", adapter_id COLLATE "C", adapter_version COLLATE "C",
    parameter_schema_hash COLLATE "C", effect COLLATE "C"), '[]'::jsonb) AS value
  FROM permission_rows
), distinct_keys AS (
  SELECT DISTINCT capability_id, capability_version, operation, adapter_id,
    adapter_version, parameter_schema_hash FROM permission_rows
), capability_set AS (
  SELECT jsonb_build_object('type', 'CapabilitySet', 'material_version', 1,
    'entries', coalesce(jsonb_agg(jsonb_build_object(
      'capability_id', capability_id, 'capability_version', capability_version,
      'operation', operation, 'adapter_id', adapter_id,
      'adapter_version', adapter_version, 'parameter_schema_hash', parameter_schema_hash)
      ORDER BY capability_id COLLATE "C", capability_version COLLATE "C",
      operation COLLATE "C", adapter_id COLLATE "C", adapter_version COLLATE "C",
      parameter_schema_hash COLLATE "C"), '[]'::jsonb)) AS value
  FROM distinct_keys
), envelope AS (
  SELECT jsonb_build_object('type', 'AgentToolPolicy', 'material_version', 1,
    'content', jsonb_build_object(
      'project_id', p.project_id::text, 'version', p.version,
      'capability_set_hash', p.capability_set_hash, 'permissions', s.value,
      'max_tool_calls', p.max_tool_calls,
      'max_parallel_invocations', p.max_parallel_invocations,
      'filesystem_scope', p.filesystem_scope, 'network_scope', p.network_scope,
      'compute_scope', p.compute_scope, 'external_effect_scope', p.external_effect_scope,
      'registry_artifact_version_id', p.registry_artifact_version_id::text,
      'registry_content_hash', p.registry_content_hash)) AS value
  FROM p CROSS JOIN permission_set s
)
SELECT pr304_canonical_policy_json(e.value) AS policy_text,
  encode(sha256(convert_to(pr304_canonical_policy_json(e.value), 'UTF8')), 'hex')
    AS policy_digest,
  encode(sha256(convert_to(pr304_canonical_policy_json(c.value), 'UTF8')), 'hex')
    AS capability_set_digest
FROM envelope e CROSS JOIN capability_set c;
```

The validator compares policy_digest with p.content_hash and capability_set_digest
with p.capability_set_hash. Serialized envelope order is content, material_version,
type; content and permission object keys appear in exactly the lexical order
shown in §7.2, regardless of jsonb_build_object argument order. Arrays come from
the explicit tuple sorts above. There are no decimal fields in AgentToolPolicy.
Delivered PR3-04 numeric resource fields use six-place JSON **strings**, via
to_char(value,'FM99999999999990.000000') (0078 lines 421–422), matching Python
fixed-point six-place strings. Reject nonfinite values and excess scale before
formatting; do not use formatting to round accepted material. Counters remain
JSON integers. The generic Python serializer supports finite floats, but this
policy contract and delivered SQL serializer do not admit them as JSON numbers.
The PostgreSQL parity cases in §9 are required future evidence, NOT RUN here.

Gateway command hash has exactly type="GatewayCommand", material_version=1,
command_name, project_id, actor_id (authenticated), command_id, task_id,
expected_row_version, arguments (expanded exact associated DTO below). Include
expected invocation revision, every normalized argument/default/NULL, exact
artifact/policy/schema pins, normalized reference/hash sets and trusted result
observation. Do not include capability object, generated receipt/event/charge
IDs/times, resulting projections, transport/correlation IDs. Caller-stable policy
and invocation IDs are material. Preserve TaskCommand/SafetyCommand hashes and
old vectors unchanged. Reordering sets yields identical normalized material;
duplicate sets reject, never silently merge.

### 7.2 Computed fixed vectors

The following complete inputs and hex outputs are computed with repository
canonical_json_bytes / sha256_canonical_json, not invented. Schema and capability
set vectors pin the inner values of the two policy vectors. Empty policy grants
nothing; the nonempty vector contains both allow and deny of one exact key and
therefore denies. Hashing does not grant executable admission.

schema_vector, complete canonical UTF-8 input:

```json
{"additionalProperties":false,"properties":{"message":{"maxLength":1024,"type":"string"},"outcome":{"enum":["SUCCEEDED","FAILED","UNKNOWN_OUTCOME","CANCELLED"]}},"required":["message","outcome"],"type":"object"}
```

sha256-cjson-v1: `79fd29b8c5f855b2d2728a13ba245b96d2287fa52fd364646f4a155e40ff4d8f`.

empty_capability_set, complete canonical UTF-8 input:

```json
{"entries":[],"material_version":1,"type":"CapabilitySet"}
```

sha256-cjson-v1: `2be8fb87e16870441bee24424875c19e4bef7500ec600750924b2c00c8d778f1`.

fake_capability_set, complete canonical UTF-8 input:

```json
{"entries":[{"adapter_id":"fake_in_process","adapter_version":"1.0.0","capability_id":"fake_capability","capability_version":"1.0.0","operation":"echo","parameter_schema_hash":"79fd29b8c5f855b2d2728a13ba245b96d2287fa52fd364646f4a155e40ff4d8f"}],"material_version":1,"type":"CapabilitySet"}
```

sha256-cjson-v1: `2087127ad6ee04e51ebb37b6fb2f89af70209d3dd99a83645a8f803e7e6125f9`.

empty_policy, complete canonical UTF-8 input:

```json
{"content":{"capability_set_hash":"2be8fb87e16870441bee24424875c19e4bef7500ec600750924b2c00c8d778f1","compute_scope":"DENY","external_effect_scope":"DENY","filesystem_scope":"DENY","max_parallel_invocations":1,"max_tool_calls":50,"network_scope":"DENY","permissions":[],"project_id":"01900000-0000-7000-8000-000000000001","registry_artifact_version_id":"01900000-0000-7000-8000-000000000020","registry_content_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","version":"fake-policy-v1"},"material_version":1,"type":"AgentToolPolicy"}
```

sha256-cjson-v1: `dcbc9330ce3ba36e9bc0988395950922f278aba37cef35d37239d8f8b099cf7c`.

allow_and_deny_policy, complete canonical UTF-8 input:

```json
{"content":{"capability_set_hash":"2087127ad6ee04e51ebb37b6fb2f89af70209d3dd99a83645a8f803e7e6125f9","compute_scope":"DENY","external_effect_scope":"DENY","filesystem_scope":"DENY","max_parallel_invocations":1,"max_tool_calls":50,"network_scope":"DENY","permissions":[{"adapter_id":"fake_in_process","adapter_version":"1.0.0","capability_id":"fake_capability","capability_version":"1.0.0","effect":"ALLOW","operation":"echo","parameter_schema_hash":"79fd29b8c5f855b2d2728a13ba245b96d2287fa52fd364646f4a155e40ff4d8f"},{"adapter_id":"fake_in_process","adapter_version":"1.0.0","capability_id":"fake_capability","capability_version":"1.0.0","effect":"DENY","operation":"echo","parameter_schema_hash":"79fd29b8c5f855b2d2728a13ba245b96d2287fa52fd364646f4a155e40ff4d8f"}],"project_id":"01900000-0000-7000-8000-000000000001","registry_artifact_version_id":"01900000-0000-7000-8000-000000000020","registry_content_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","version":"fake-policy-v1"},"material_version":1,"type":"AgentToolPolicy"}
```

sha256-cjson-v1: `725ad2c4ac6b22c5f53ee1138b5d65d88b344e033d52df268db46afd7d3f293b`.

parameters_vector, complete canonical UTF-8 input:

```json
{"message":"Café","outcome":"SUCCEEDED"}
```

sha256-cjson-v1: `a6d9214ed01cfe46686c39829bde5d0a733d16c31d8b5297e48d245b70ce13b3`.

## 8. Closed Application commands, DTOs and gateway port

All types/operations in this section are **new in PR3-03** except explicitly
existing VerifiedPrincipal, FakeConsumerCapability, ResourceVector and underlying
TaskCommand/CommandResult/SafetyCommand. Immutable recursive DTOs reject unknown
fields. Required fields have no implicit defaults except those listed; include
expanded defaults/NULL in material. No caller actor, time, calculated charge,
trusted flag, arbitrary JSON payload, execution UUID or ORM object in public
requests. Trusted objects arrive through injected Application context only.

| Type | Exact fields and types |
| --- | --- |
| GatewayCommand | project_id:UUID, task_id:UUIDv7, command_id:UUID, expected_row_version:positive int, command_name:one of the four commands, arguments:its exact variant. Principal supplied separately. |
| PermissionSpec | capability_id, capability_version, operation, adapter_id, adapter_version, parameter_schema_hash, effect. Types/bounds per §2 and exact pins per §7. |
| ToolPolicySpec | version, permissions:tuple[PermissionSpec] ≤256, max_tool_calls=50, max_parallel_invocations=1, filesystem_scope=DENY, network_scope=DENY, compute_scope=DENY, external_effect_scope=DENY, registry_artifact_version_id:UUID, registry_content_hash:digest, capability_set_hash:digest. Other types per §2. DB independently verifies all hashes. |
| RegisterToolPolicyArguments | policy_id:UUIDv7, policy:ToolPolicySpec, reason:NFC nonblank text ≤8192. |
| GatewayRef | family:RESEARCH_QUESTION_VERSION/HYPOTHESIS_VERSION/CLAIM_VERSION/SOURCE_VERSION/ARTIFACT_VERSION/MANUSCRIPT_VERSION, version_id:UUID, content_hash:digest, hash_scheme:text or NULL. Hash scheme follows §2. This is a typed value mapped to concrete columns, never a soft-reference table. |
| FakeParameters | message:NFC text 0..1024, outcome:SUCCEEDED/FAILED/UNKNOWN_OUTCOME/CANCELLED; schema per §7.1. |
| RequestInvocationArguments | invocation_id:UUIDv7, step_id:UUID or NULL, agent_version_id:UUID, policy_id:UUID, policy_content_hash:digest, capability_id, capability_version, operation, adapter_id, adapter_version, parameter_schema_hash, skill_id, skill_version, strategy_id, strategy_version (bounded pins), harness_artifact_version_id:UUID, harness_content_hash:digest, parameters_artifact_version_id:UUID, parameters_content_hash:digest, requested_parameters_hash:digest, parameters_byte_size:int 1..65536, parameters:FakeParameters, input_refs:tuple[GatewayRef], retry_parent_id:UUID or NULL, deadline_seconds:int 1..60, reason:NFC nonblank ≤8192. Worst-case ResourceVector/gauges derived by trusted classification in §6, never caller-authoritative. |
| StartInvocationArguments | invocation_id:UUID, expected_invocation_revision:positive int, reason:NFC nonblank ≤8192. |
| FinishInvocationArguments | invocation_id:UUID, expected_invocation_revision:positive int, kind:FINISH/RECONCILE, outcome:SUCCEEDED/FAILED/UNKNOWN_OUTCOME/CANCELLED, measured:existing ResourceVector, output_refs:tuple[GatewayRef], trace_artifact_version_id:UUID or NULL, trace_content_hash:digest or NULL, result_summary:NFC text or NULL ≤8192 UTF-8 bytes, error_code:ADAPTER_UNAVAILABLE/INVALID_STATE_TRANSITION or NULL, reason:NFC nonblank ≤8192. Only trusted observation can supply this variant. RECONCILE outcome must be final; original unknown summary/trace/error stay unchanged; reconciliation cannot supply trace/summary/error (all NULL), outputs only if success. |
| GatewayCommandResult | receipt_id, project_id, task_id, actor_id, command_id, command_name, policy_id, invocation_id nullable, invocation_event_id nullable, reservation_id nullable, usage_record_id nullable, resulting_row_version, resulting_invocation_revision nullable, completed_at, replayed:bool. Registration has only policy ID; start returns saved invocation reservation; request returns reservation and no usage; finish returns its event's usage. Recovered from receipt-linked saved rows, no current-state fields. |
| CapabilityRequest | request_command_id:UUID, start_command_id:UUID, finish_command_id:UUID (distinct stable IDs), expected_row_version:positive int, arguments:RequestInvocationArguments. |
| AgentExecutionContext | principal:existing VerifiedPrincipal, project_id:UUID, task_id:UUID, step_id:UUID or NULL, agent_version_id:UUID, harness_artifact_version_id:UUID, harness_content_hash:digest, consumer_capability:existing FakeConsumerCapability. Entire context is trusted injected value, not serializable public DTO; all pins must agree with request and stored AgentVersion. No execution_id field until S2. |
| CapabilityResult | invocation_id:UUID, outcome:terminal invocation literal, output_refs:tuple[GatewayRef], trace_artifact_version_id:UUID or NULL, resource_usage:ResourceVector, error_code:existing permitted code or NULL, result_summary:text or NULL. Outcome from immutable finish event; does not assert scientific validity. |
| AgentToolPolicyRead | Every column of agent_tool_policies in §2, permissions:tuple[PermissionSpec] in canonical order. Closed list, no bytes or current/latest aliases. |
| CapabilityInvocationRead | Every column of capability_invocations in §2, refs:tuple[GatewayRefRead], events:tuple[CapabilityEventRead], effective_outcome:terminal literal or NULL, effective_usage_record_id:UUID or NULL, current_availability:existing availability status, execution_enabled:false. Last three are labeled snapshot projections; effective outcome uses RECONCILED event when present. |
| GatewayRefRead | Every column of capability_invocation_refs, validity_warnings:tuple[text] from owning-domain snapshot, never invented scientific truth. |
| CapabilityEventRead | Every column of capability_invocation_events. |
| InvocationListCursor | created_at:aware UTC timestamp, id:UUID. |
| TaskCapabilityInvocationsRead | task_id:UUID, invocations:tuple[CapabilityInvocationRead], next_cursor:InvocationListCursor or NULL. |

Invocation inputs/outputs sort by (family,version_id), reject duplicates first;
≤256 combined persisted refs. parameters in the request must exactly match the
retained parameter bytes, schema and digest; public blobs cannot replace retained
provenance. policy.capability_set_hash and registry_content_hash are assertions
independently verified, never authority supplied by caller. Command hash includes
their exact normalized fields. No generated IDs/timestamps in arguments.

| Operation | Exact boundary behavior |
| --- | --- |
| register_agent_tool_policy(principal, GatewayCommand) | Verified HUMAN OWNER, entitled nonterminal planning task; registration only. Never alters AgentVersion. |
| request_capability_invocation(principal, GatewayCommand, trusted context) | Common write admission, complete safety bundle, exact version/policy/registry/frozen inputs and fake trust; atomic reservation/invocation. |
| start_capability_invocation(principal, GatewayCommand, trusted context) | Common checks, expected task and invocation revisions, current gate/availability/reservation; §6.1 start distinction. Atomic RUNNING, no execution inside transaction. |
| finish_capability_invocation(principal, GatewayCommand, trusted context) | Atomic observation/settlement/event; after-stop bookkeeping; narrow pre-start cancel and unknown reconciliation per §4.2. |
| get_capability_invocation(principal, project_id, task_id, invocation_id) | Exact entitled snapshot with refs/events/charge IDs, no writes. |
| list_task_capability_invocations(principal, project_id, task_id, limit=100, after=NULL) | limit 1..256, after:InvocationListCursor or NULL; keyset (created_at,id) ascending, no offset or hidden repair. |
| get_agent_tool_policy(principal, project_id, policy_id) | Exact version/digest/permissions/intake pins under current project read entitlement. |
| CapabilityGateway.invoke(request:CapabilityRequest, context:AgentExecutionContext) -> CapabilityResult | Only admitted fake adapter. Request commit → start commit → one finite fake invocation outside UoW → finish command. Reuse stable command identities and receipt results. Advance expected task revision from saved results; no unrelated state projection substituted. Replay returns saved completion without calling fake. An unresolved prior start is unknown/reconciliation work, never automatic reexecution. |

Transport adapters may expose the four commands and three queries through existing
Application composition, using identical closed values/error envelopes and request
identity. They never instantiate executable adapters/repositories or deserialize
trusted context. Public executable actions without the injected capability deny.
The Application port accepts no vendor SDK. Proposed code modules are **new in
PR3-03**: agent_runtime/domain/capability_invocation.py and tool_policy.py;
agent_runtime/application/gateway_contracts.py, capability_gateway.py, routing.py;
agent_runtime/ports/capability_gateway.py and gateway_repository.py;
persistence/capability_gateway_repository.py and capability_gateway_queries.py
(all relative to src/researchbase). Adapt existing UoW/models/safety internals
only as specified above. Pure domain depends on no ORM, FastAPI, Typer or harness.

## 9. Existing ErrorCode mapping and required implementation evidence

No new ErrorCode, policy/budget/provider error enum or transport mapping. Use
fixed diagnostic constraint names, never parse SQL exception messages. Reuse
existing pr301 diagnostic labels so the UoW normalizer remains compatible.

| SQLSTATE / condition | Existing ErrorCode | Handling |
| --- | --- | --- |
| 23514 / pr301_validation; 23502; scalar CHECK/size/duplicate malformed submitted set | VALIDATION_ERROR | Closed shape, limits, malformed pins/JSON/decimal; no retry. |
| 23514 / pr301_state | INVALID_STATE_TRANSITION | Stop/gate/prerequisite/cap/lifecycle violation; no retry. |
| 23514 / pr301_immutable | IMMUTABLE_RECORD | Policy/permission/input/history/terminal rewrite or missing fresh root; no retry. |
| 23514 / pr301_scope | FORBIDDEN | Project/role/scope/fake trust denial; no retry. |
| 23514 / pr301_not_frozen | VERSION_NOT_FROZEN | Existing exact version not historically frozen. |
| 23514 / pr301_provenance | PROVENANCE_CLOSURE_VIOLATION | Hash/pin/receipt/effect contradiction. |
| 23503 | REFERENTIAL_INTEGRITY_ERROR | Concrete/composite FK contradiction after entitlement; unknown entitled input can be NOT_FOUND before persistence. |
| 23505 / original command uniqueness | IDEMPOTENCY_CONFLICT or saved replay | Under command lock: identical hash replays, changed hash conflicts. |
| 23505 / policy version or new invocation ID already occupied | CONCURRENT_MODIFICATION | Entitled identity conflict, never overwrite. Duplicate submitted permission/ref is VALIDATION_ERROR. |
| 40001 / 40P01 | CONCURRENT_MODIFICATION | Only retryable states; max three fresh whole attempts, then sanitized conflict. |
| 55P03 / 57014 | CONCURRENT_MODIFICATION | Lock/query timeout; no automatic retry. |
| No SQL: missing trusted principal | AUTHENTICATION_REQUIRED | Existing sanitized authentication failure. |
| No SQL: absent exact entitled object | NOT_FOUND | Do not disclose foreign IDs. |
| No SQL: live/unresolved dependency | FROZEN_REFERENCE_REQUIRED | Exact deterministic frozen ref required. |
| No SQL: no admitted adapter / wrong exact version or schema pin | ADAPTER_UNAVAILABLE / ADAPTER_VERSION_MISMATCH | No provider fallback; schema mismatch uses ADAPTER_VERSION_MISMATCH. |

A persisted FAILED/UNKNOWN result is separate from a transport failure. Unexpected
exceptions retain existing INTERNAL_ERROR fallback text (not an ErrorCode member).
Preserve current HTTP/CLI status/exit and sanitized envelopes; no raw SQL, credentials,
provider stack or untrusted description in errors.

### 9.1 Required suites (future implementation; NOT RUN for this pack)

Every new filename in this table is **new in PR3-03**. Tests exercise contracts,
including valid normal-role DML; no SQLite or trigger disabling. All integration,
constraint, migration, concurrency and replay suites require real PostgreSQL 18.

| Suite / file | Required cases |
| --- | --- |
| tests/unit/phase3/test_capability_gateway_contracts.py | Closed DTOs/defaults/NFC/UUID/decimal/bool rejection; exact six vectors plus GatewayCommand roundtrips; old TaskCommand/SafetyCommand and S1 vectors unchanged; set ordering/duplicate errors; parameter and summary UTF-8 byte boundaries. |
| tests/unit/phase3/test_agent_tool_policy.py | Exact tuple match, deny overrides allow, absence denies, empty policy, pins/schema mismatch, task-wide 50/1 caps below/equal/above, no counter reset on policy switch, aliases rejected. |
| tests/unit/phase3/test_capability_routing.py | Phase/authority/project/safety intersection, reference-only denies, unreviewed pins/scripts/transitive capability denies, descriptions/injection grant nothing, same-execution governing-file/policy change denies, only pure fake executable. |
| tests/unit/phase3/test_capability_gateway.py | Three commands/transactions; fake outside UoW; stable identities; common caller boundary; reserve/request and settle/finish atomic; failure/unknown/cancel; replay never calls fake; trusted object identity, no nested TaskSafetyService.execute/UoW; disabled S2 and no fake execution UUID. |
| tests/architecture/test_pr3_03_boundaries.py | NEW architecture boundary test: no domain ORM/transport/SDK imports, no Agent/vendor direct persistence/credentials, no hidden adapter subcalls, no queue/process/network/filesystem/real provider, no new dependency/scientific ownership/JSON refs/promotion, planning execution stays disabled. |
| tests/integration/phase3/test_pr3_03_schema.py | Required PostgreSQL hash parity: reconstruct both empty_policy and allow_and_deny_policy from typed rows using §7.1a, compare canonical UTF-8 text to §7.2 and SQL SHA-256 digests to dcbc9330ce3ba36e9bc0988395950922f278aba37cef35d37239d8f8b099cf7c and 725ad2c4ac6b22c5f53ee1138b5d65d88b344e033d52df268db46afd7d3f293b respectively; compare both derived CapabilitySet hashes too. Exercise reordered insertion, non-ASCII pins, six-place resource strings and rejected fractional JSON numbers against Python. Every column/null/check/index/FK; project/task/step/version/actor/policy/reservation/usage mismatches; exact-one six-family refs and unique indexes; no CASCADE; 256 refs and permissions, 65536 parameter bytes, 8192 summary bytes at boundary and +1; pinned ArtifactVersion byte_size/hash; valid same-project normal-role SQL. |
| tests/integration/phase3/test_pr3_03_guards.py | All immediate guards, current xmin checks, immutable no-op UPDATE/DELETE including receipt/event/settlement; naked revision, committed-receipt child append, missing/extra effects, multiple flush tampering; one task final and one receipt check per command at maximum bounded sets; every lifecycle/reconciliation invalid edge. |
| tests/integration/phase3/test_pr3_03_migration.py | Clean upgrade and populated 0079→0080 preserving old identity/scientific hashes/task receipts/events/replay; original six planning/six safety shapes; explicit CHECK replacement; sole head; empty/populated downgrade refusal before DDL; no UPDATE/backfill/dummy execution; forward repair obligations. |
| tests/integration/phase3/test_pr3_03_application.py | Human/eligible Agent same boundary, registration Human OWNER, fake-only trust, request/start/finish durable rollback atomicity, no scientific effects, current policy pin/version/manifest agreement, count and resource caps/gates, pre-start cancel, failed/unknown/final reconciliation, immutable old unknown, stop bookkeeping. |
| tests/integration/phase3/test_pr3_03_concurrency.py | Observe exact first SHARE and all advisory/row ordering; two tasks same AgentVersion versus availability writer; last budget unit/call/parallel slot races; actual observed lock wait with expiry/revocation/stop/checkpoint changes; exact-cap own-stop start versus prior/later/additional stop; post-start stop permits finite finish only; bounded retries and nonretryable timeouts; no over-admission. |
| tests/integration/phase3/test_pr3_03_replay.py | Same original key/hash saved IDs, changed material conflict; replay before task/invocation CAS/state/expiry/availability after every wait; current read entitlement; lost response/uncertain request/start/finish commit; no duplicate fake/charge/event, no unknown refund/redispatch; lock-free coherent repeatable-read queries. |

Focused future commands, run only after pack freeze and implementation. Disposable
PostgreSQL 18 admin/runtime configuration follows README and delivered phase3
fixtures. Record server version, exact commands/counts/failures/skips, DB role,
clean/populated baseline and lock-wait DB timestamps. Missing setup is NOT RUN,
never PASS. Future evidence path docs/phase3/PR3-03-evidence.md is **new in PR3-03**.

```sh
uv sync --locked --group dev
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run alembic heads
uv run pytest -o addopts='' -ra tests/unit/phase3
uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_03_schema.py tests/integration/phase3/test_pr3_03_guards.py tests/integration/phase3/test_pr3_03_migration.py
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_03_application.py tests/integration/phase3/test_pr3_03_concurrency.py tests/integration/phase3/test_pr3_03_replay.py
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_01_*.py tests/integration/phase3/test_pr3_04_*.py tests/integration/phase3/test_pr3_02_s1_*.py
```

Migration fixtures must test both clean base→head and accepted populated 0079→head
(including historical scientific trace/hash comparisons), not just ORM create_all.
CI's revision assertion must advance explicitly to 0080 in the implementation PR.
No new test/dependency/migration/code is created by this documentation task.

Final implementation gate is the existing deterministic **six-shard full suite**,
run by the external check loop/CI after focused evidence, never by this docs task.
Exact command recipe below runs once per shard index 0,1,2,3,4,5 on independent
PostgreSQL 18 databases (DATABASE_URL selects that shard's disposable database):

```bash
uv run python scripts/ci_pytest_files.py --index "$RB_PR303_SHARD" --count 6 --durations .github/pytest-durations.json > /tmp/pr303-pytest-files.txt
mapfile -t pr303_test_files < /tmp/pr303-pytest-files.txt
uv run pytest --junitxml=/tmp/pr303-pytest-results.xml "${pr303_test_files[@]}"
```

RB_PR303_SHARD is set by the CI matrix, one of the six exact indices above; use
per-job isolated /tmp paths and preserve six JUnit artifacts. Require exhaustive
file union, no overlap, counts for all shards and no required skipped case. The
loop's output is independent full-suite evidence; no guessed counts here.
Open P0 BLOCKER/P1 MAJOR prevents acceptance; P2 MINOR/P3 SUGGESTION retain named
disposition. Independent review uses authoritative specs + diff + test evidence.
No gate is passed by this pack. Stop after accepted PR3-03 fake slice; later
execution/provider owners require their own authorization.

## 10. Existing identifier anchors and documentation verification

Existing repository identifiers are verified with focused literal `rg -l -F --
<identifier> src/ migrations/ tests/`; a proposal-only occurrence never counts.
SQL built-ins and enum literals are language/value contracts. All new table,
column, pr303 function/trigger/index/constraint, operation/DTO, seam and proposed
path names above are **new in PR3-03**; S2 execution identifiers remain deferred
and are not claimed delivered. Existing source anchors:

| Existing identifiers | Delivered source |
| --- | --- |
| 0077_research_task_graph; task/step/input/event/receipt/link tables; pr301 functions/triggers; TaskCommand, CommandResult | migrations/versions/0077_research_task_graph.py; src/researchbase/agent_runtime/application/contracts.py; src/researchbase/persistence/research_task_repository.py |
| 0078_task_safety_policies; eight safety tables; pr304_command_names/event CHECKs/guards/validator; SafetyCommand, ResourceVector, TaskSafetyService, FakeConsumerCapability | migrations/versions/0078_task_safety_policies.py; src/researchbase/agent_runtime/application/safety_contracts.py, task_safety.py; src/researchbase/agent_runtime/ports/task_safety_repository.py; src/researchbase/persistence/task_safety_repository.py |
| 0079_agent_identity_versions; agent_versions, agent_availability, tool_policy_version, capability_set_hash; pr302 actor/version keys | migrations/versions/0079_agent_identity_versions.py; src/researchbase/persistence/agent_version_repository.py |
| Eighteen SHARE parents, six exact version families, owning parent/project/hash columns; byte_size | src/researchbase/persistence/models.py; migrations/versions/0006_artifact_version.py; migrations/versions/0077_research_task_graph.py |
| rb_phase2_lock_project, pr301 command/task keys, lock_write, pr302 actor/version keys | src/researchbase/persistence/research_task_repository.py, task_safety_repository.py, agent_version_repository.py |
| SqlAlchemyUnitOfWork, begin_formal_read, diagnostic mapping | src/researchbase/persistence/uow.py |
| canonical_json_bytes, sha256_canonical_json, sha256-cjson-v1 | src/researchbase/foundation/canonical_json.py; src/researchbase/foundation/hashing.py |
| ErrorCode and all codes in §9, INTERNAL_ERROR fallback; VerifiedPrincipal | src/researchbase/foundation/errors.py; src/researchbase/api/errors.py; src/researchbase/cli/errors.py; src/researchbase/domain/phase2_identity.py |
| Existing regression paths in §9 | tests/unit/phase3/; tests/architecture/; tests/unit/architecture/; tests/integration/phase3/ |

Current verification evidence, exact commands and captured outputs are in §12.
Earlier interrupted-pass checks are not substituted for this pass's evidence.

## 11. Review disposition and visibility

D303-01 through D303-05 remain **ACCEPTED-AS-RECOMMENDED, 2026-10-22**;
the full decision table and all exclusions remain in §1. The full future test
matrix, focused commands and external six-shard gate remain in §9.1. The SQL
parity requirement is part of that matrix, not a passing database result.
This is still PACK DRAFT pending director review; no implementation gate is passed.

The review follow-up explicitly authorizes one documentation-only commit with
message "Freeze PR3-03 capability gateway execution pack (documentation only)";
it supersedes the preceding turn's no-commit instruction. Commit result and
post-commit Git state are reported outside this file to avoid self-referential
commit metadata. Any index-lock or sandbox error must be quoted verbatim and
stops this task. No push or branch creation. No code, migration or test file
changes; no pytest or database suite execution in this documentation pass.

## 12. Verification evidence

Evidence below was captured on 2026-10-22 in the existing repository, without
pytest or migration execution. Commands search delivered src/, migrations/ and
tests/; documentation/proposal occurrences do not establish an existing API.

### 12.1 Delivered identifier audit

Exact script: 200 delivered names and four advisory-key prefixes; all 204 rg
commands exited 0. The -o flag prints matches with their real file:line. FK
constraint text is captured separately in §12.2. SQL/Python built-ins and value
literals are not repository APIs. Shared column spellings are audited as existing;
new table-qualified fields are inventoried in §12.3. INTERNAL_ERROR is transport
fallback text, not an ErrorCode member. No proposal occurrence establishes an API.

```sh
uv run python - <<'PYAUDIT'
from pathlib import Path
import subprocess

groups = {'src/researchbase/foundation/errors.py': 'ADAPTER_UNAVAILABLE ADAPTER_VERSION_MISMATCH '
                                          'AUTHENTICATION_REQUIRED CONCURRENT_MODIFICATION '
                                          'ErrorCode FORBIDDEN FROZEN_REFERENCE_REQUIRED '
                                          'IDEMPOTENCY_CONFLICT IMMUTABLE_RECORD '
                                          'INVALID_STATE_TRANSITION NOT_FOUND '
                                          'PROVENANCE_CLOSURE_VIOLATION '
                                          'REFERENTIAL_INTEGRITY_ERROR VALIDATION_ERROR '
                                          'VERSION_NOT_FROZEN canonical_json_bytes',
 'migrations/versions/0079_agent_identity_versions.py': 'AgentVersion agent_availability '
                                                        'agent_version_id agent_versions '
                                                        'capability_set_hash '
                                                        'configuration_artifact_version_id '
                                                        'configuration_content_hash created_by '
                                                        'tool_policy_version '
                                                        '0079_agent_identity_versions',
 'src/researchbase/agent_runtime/application/research_task.py': 'ArtifactStore',
 'src/researchbase/application/closure.py': 'ArtifactVersion',
 'src/researchbase/agent_runtime/application/contracts.py': 'CommandResult TaskCommand '
                                                            'execution_enabled',
 'src/researchbase/agent_runtime/application/task_safety.py': 'FakeConsumerCapability '
                                                              'ResourceVector SafetyCommand '
                                                              'TaskSafetyService actor_id '
                                                              'after_wait bind_task_policies '
                                                              'budget_id budget_reservations '
                                                              'budget_usage_records '
                                                              'checkpoint_policies '
                                                              'checkpoint_policy_dataset_scopes '
                                                              'checkpoint_policy_metric_scopes '
                                                              'code_iterations command_id '
                                                              'command_name completed_at '
                                                              'consumer_capability content_hash '
                                                              'created_at deadline_seconds '
                                                              'evaluate_task_termination '
                                                              'event_type execution_budgets '
                                                              'expected_row_version '
                                                              'experiment_runs hash_scheme '
                                                              'human_checkpoints is_final '
                                                              'lock_write material_version '
                                                              'new_status observed_depth '
                                                              'observed_parallel_branches '
                                                              'occurred_at operation_id '
                                                              'prior_status project_id receipt_id '
                                                              'request_human_checkpoint '
                                                              'research_task_command_receipts '
                                                              'research_task_events '
                                                              'research_task_id '
                                                              'research_task_receipt_events '
                                                              'reservation_id reserve_task_budget '
                                                              'respond_human_checkpoint '
                                                              'resulting_row_version row_version '
                                                              'settle_task_budget step_id '
                                                              'stop_budget stop_human '
                                                              'stop_no_improvement stop_policy '
                                                              'stop_repeated_failure stop_success '
                                                              'task_id termination_policies '
                                                              'tree_nodes wall_time_seconds',
 'src/researchbase/agent_runtime/domain/harness_manifest.py': 'HarnessManifest schema_version',
 'src/researchbase/persistence/uow.py': 'SqlAlchemyUnitOfWork agent_runtime '
                                        'agent_version_repository artifact_versions '
                                        'begin_formal_read connect_timeout lock_timeout '
                                        'pr301_immutable pr301_not_frozen pr301_provenance '
                                        'pr301_scope pr301_state pr301_validation '
                                        'research_questions research_tasks statement_timeout '
                                        'task_safety_repository',
 'src/researchbase/agent_runtime/application/agent_contracts.py': 'VerifiedPrincipal',
 'migrations/versions/0078_task_safety_policies.py': 'actor_subject_bindings agent_steps gpu_hours '
                                                     'llm_calls pr304_canonical_policy_json '
                                                     'pr304_child_guard pr304_command_names '
                                                     'pr304_event_names pr304_event_prior '
                                                     'pr304_event_reason pr304_event_states '
                                                     'pr304_event_stop_kind pr304_event_stop_slice '
                                                     'pr304_reservation_guard pr304_usage_guard '
                                                     'pr304_usage_one_final pr304_validate_safety '
                                                     'project_memberships project_role_assignments '
                                                     'search_calls token_cost outcome score '
                                                     '0078_task_safety_policies',
 'src/researchbase/application/native_research_strategy.py': 'adapter_id',
 'src/researchbase/adapters/crossref.py': 'adapter_version',
 'migrations/versions/0077_research_task_graph.py': 'add_task_step add_task_step_dependency '
                                                    'artifact_id artifact_version_id branch_labels '
                                                    'cancel_research_task capability_id '
                                                    'claim_version_id claim_versions '
                                                    'create_research_task create_task_plan '
                                                    'depends_on down_revision finished_at '
                                                    'frozen_at hypothesis_version_id '
                                                    'hypothesis_versions '
                                                    'literature_source_project_links '
                                                    'literature_sources manuscript_version_id '
                                                    'manuscript_versions pr301_event_insert_guard '
                                                    'pr301_graph_final_guard '
                                                    'pr301_receipt_complete '
                                                    'pr301_receipt_complete_commit '
                                                    'pr301_receipt_insert '
                                                    'pr301_receipt_insert_guard '
                                                    'pr301_receipt_link_guard pr301_task_final '
                                                    'pr301_task_guard pr301_validate_input '
                                                    'requested_by research_question_version_id '
                                                    'research_question_versions '
                                                    'research_task_inputs '
                                                    'research_task_step_dependencies '
                                                    'research_task_step_inputs research_task_steps '
                                                    'seal_task_plan source_version_id '
                                                    'source_versions started_at strategy_id '
                                                    'strategy_version version_id actors artifacts '
                                                    'claims hypotheses projects publications id '
                                                    'status reason sequence '
                                                    '0077_research_task_graph',
 'src/researchbase/persistence/models.py': 'byte_size',
 'src/researchbase/application/commands.py': 'error_code',
 'src/researchbase/application/metadata_observation.py': 'invocation_id',
 'src/researchbase/persistence/task_safety_repository.py': 'rb_phase2_lock_project pr301:command: '
                                                           'pr301:task:',
 'src/researchbase/foundation/hashing.py': 'sha256_canonical_json',
 'src/researchbase/persistence/agent_version_repository.py': 'pr302:actor: pr302:version:',
 'src/researchbase/api/errors.py': 'INTERNAL_ERROR'}
for path, names in groups.items():
    source = Path(path)
    print('# ' + path)
    for name in names.split():
        word = [] if ':' in name else ['-w']
        command = ['rg', '-n', '--with-filename', '-m', '1', '-o', '-F',
                   *word, '--', name, source.name]
        result = subprocess.run(command, cwd=source.parent,
                                capture_output=True, text=True, check=True)
        print(result.stdout, end='')
PYAUDIT
```

Captured stdout, in script order. Each # line gives the source path; subsequent
file:line matches come from rg run in that file's directory.

```text
# src/researchbase/foundation/errors.py
errors.py:61:ADAPTER_UNAVAILABLE
errors.py:61:ADAPTER_UNAVAILABLE
errors.py:62:ADAPTER_VERSION_MISMATCH
errors.py:62:ADAPTER_VERSION_MISMATCH
errors.py:23:AUTHENTICATION_REQUIRED
errors.py:23:AUTHENTICATION_REQUIRED
errors.py:19:CONCURRENT_MODIFICATION
errors.py:19:CONCURRENT_MODIFICATION
errors.py:12:ErrorCode
errors.py:24:FORBIDDEN
errors.py:24:FORBIDDEN
errors.py:17:FROZEN_REFERENCE_REQUIRED
errors.py:17:FROZEN_REFERENCE_REQUIRED
errors.py:33:IDEMPOTENCY_CONFLICT
errors.py:33:IDEMPOTENCY_CONFLICT
errors.py:16:IMMUTABLE_RECORD
errors.py:16:IMMUTABLE_RECORD
errors.py:14:INVALID_STATE_TRANSITION
errors.py:14:INVALID_STATE_TRANSITION
errors.py:13:NOT_FOUND
errors.py:13:NOT_FOUND
errors.py:18:PROVENANCE_CLOSURE_VIOLATION
errors.py:18:PROVENANCE_CLOSURE_VIOLATION
errors.py:21:REFERENTIAL_INTEGRITY_ERROR
errors.py:21:REFERENTIAL_INTEGRITY_ERROR
errors.py:22:VALIDATION_ERROR
errors.py:22:VALIDATION_ERROR
errors.py:15:VERSION_NOT_FROZEN
errors.py:15:VERSION_NOT_FROZEN
errors.py:9:canonical_json_bytes
# migrations/versions/0079_agent_identity_versions.py
0079_agent_identity_versions.py:282:AgentVersion
0079_agent_identity_versions.py:52:agent_availability
0079_agent_identity_versions.py:53:agent_version_id
0079_agent_identity_versions.py:15:agent_versions
0079_agent_identity_versions.py:36:capability_set_hash
0079_agent_identity_versions.py:36:capability_set_hash
0079_agent_identity_versions.py:37:configuration_artifact_version_id
0079_agent_identity_versions.py:39:configuration_content_hash
0079_agent_identity_versions.py:43:created_by
0079_agent_identity_versions.py:32:tool_policy_version
0079_agent_identity_versions.py:9:0079_agent_identity_versions
# src/researchbase/agent_runtime/application/research_task.py
research_task.py:126:ArtifactStore
# src/researchbase/application/closure.py
closure.py:559:ArtifactVersion
# src/researchbase/agent_runtime/application/contracts.py
contracts.py:445:CommandResult
contracts.py:191:TaskCommand
contracts.py:349:execution_enabled
# src/researchbase/agent_runtime/application/task_safety.py
task_safety.py:33:FakeConsumerCapability
task_safety.py:28:ResourceVector
task_safety.py:19:SafetyCommand
task_safety.py:122:TaskSafetyService
task_safety.py:164:actor_id
task_safety.py:174:after_wait
task_safety.py:645:bind_task_policies
task_safety.py:285:budget_id
task_safety.py:225:budget_reservations
task_safety.py:226:budget_usage_records
task_safety.py:222:checkpoint_policies
task_safety.py:223:checkpoint_policy_dataset_scopes
task_safety.py:224:checkpoint_policy_metric_scopes
task_safety.py:91:code_iterations
task_safety.py:172:command_id
task_safety.py:598:command_name
task_safety.py:598:command_name
task_safety.py:604:completed_at
task_safety.py:123:consumer_capability
task_safety.py:269:content_hash
task_safety.py:63:created_at
task_safety.py:425:deadline_seconds
task_safety.py:654:evaluate_task_termination
task_safety.py:619:event_type
task_safety.py:220:execution_budgets
task_safety.py:211:expected_row_version
task_safety.py:93:experiment_runs
task_safety.py:270:hash_scheme
task_safety.py:227:human_checkpoints
task_safety.py:43:is_final
task_safety.py:169:lock_write
task_safety.py:602:material_version
task_safety.py:623:new_status
task_safety.py:412:observed_depth
task_safety.py:412:observed_parallel_branches
task_safety.py:625:occurred_at
task_safety.py:379:operation_id
task_safety.py:379:operation_id
task_safety.py:622:prior_status
task_safety.py:170:project_id
task_safety.py:253:receipt_id
task_safety.py:657:request_human_checkpoint
task_safety.py:606:research_task_command_receipts
task_safety.py:631:research_task_events
task_safety.py:253:research_task_id
task_safety.py:633:research_task_receipt_events
task_safety.py:43:reservation_id
task_safety.py:648:reserve_task_budget
task_safety.py:660:respond_human_checkpoint
task_safety.py:474:resulting_row_version
task_safety.py:211:row_version
task_safety.py:651:settle_task_budget
task_safety.py:97:step_id
task_safety.py:69:stop_budget
task_safety.py:67:stop_human
task_safety.py:77:stop_no_improvement
task_safety.py:68:stop_policy
task_safety.py:70:stop_repeated_failure
task_safety.py:85:stop_success
task_safety.py:173:task_id
task_safety.py:221:termination_policies
task_safety.py:396:tree_nodes
task_safety.py:816:wall_time_seconds
# src/researchbase/agent_runtime/domain/harness_manifest.py
harness_manifest.py:26:HarnessManifest
harness_manifest.py:27:schema_version
# src/researchbase/persistence/uow.py
uow.py:483:SqlAlchemyUnitOfWork
uow.py:12:agent_runtime
uow.py:41:agent_version_repository
uow.py:498:artifact_versions
uow.py:647:begin_formal_read
uow.py:1317:connect_timeout
uow.py:1316:lock_timeout
uow.py:852:pr301_immutable
uow.py:853:pr301_not_frozen
uow.py:855:pr301_provenance
uow.py:854:pr301_scope
uow.py:851:pr301_state
uow.py:850:pr301_validation
uow.py:492:research_questions
uow.py:522:research_tasks
uow.py:1316:statement_timeout
uow.py:104:task_safety_repository
# src/researchbase/agent_runtime/application/agent_contracts.py
agent_contracts.py:20:VerifiedPrincipal
# migrations/versions/0078_task_safety_policies.py
0078_task_safety_policies.py:406:actor_subject_bindings
0078_task_safety_policies.py:149:agent_steps
0078_task_safety_policies.py:149:agent_steps
0078_task_safety_policies.py:155:gpu_hours
0078_task_safety_policies.py:155:gpu_hours
0078_task_safety_policies.py:155:gpu_hours
0078_task_safety_policies.py:150:llm_calls
0078_task_safety_policies.py:150:llm_calls
0078_task_safety_policies.py:298:pr304_canonical_policy_json
0078_task_safety_policies.py:354:pr304_child_guard
0078_task_safety_policies.py:264:pr304_command_names
0078_task_safety_policies.py:274:pr304_event_names
0078_task_safety_policies.py:284:pr304_event_prior
0078_task_safety_policies.py:285:pr304_event_reason
0078_task_safety_policies.py:277:pr304_event_states
0078_task_safety_policies.py:290:pr304_event_stop_kind
0078_task_safety_policies.py:289:pr304_event_stop_slice
0078_task_safety_policies.py:729:pr304_reservation_guard
0078_task_safety_policies.py:730:pr304_usage_guard
0078_task_safety_policies.py:201:pr304_usage_one_final
0078_task_safety_policies.py:467:pr304_validate_safety
0078_task_safety_policies.py:405:project_memberships
0078_task_safety_policies.py:405:project_role_assignments
0078_task_safety_policies.py:151:search_calls
0078_task_safety_policies.py:151:search_calls
0078_task_safety_policies.py:156:token_cost
0078_task_safety_policies.py:156:token_cost
0078_task_safety_policies.py:156:token_cost
0078_task_safety_policies.py:178:outcome
0078_task_safety_policies.py:178:outcome
0078_task_safety_policies.py:191:score
0078_task_safety_policies.py:191:score
0078_task_safety_policies.py:191:score
0078_task_safety_policies.py:6:0078_task_safety_policies
# src/researchbase/application/native_research_strategy.py
native_research_strategy.py:196:adapter_id
native_research_strategy.py:196:adapter_id
# src/researchbase/adapters/crossref.py
crossref.py:23:adapter_version
# migrations/versions/0077_research_task_graph.py
0077_research_task_graph.py:185:add_task_step
0077_research_task_graph.py:186:add_task_step_dependency
0077_research_task_graph.py:454:artifact_id
0077_research_task_graph.py:99:artifact_version_id
0077_research_task_graph.py:8:branch_labels
0077_research_task_graph.py:186:cancel_research_task
0077_research_task_graph.py:57:capability_id
0077_research_task_graph.py:57:capability_id
0077_research_task_graph.py:97:claim_version_id
0077_research_task_graph.py:97:claim_versions
0077_research_task_graph.py:185:create_research_task
0077_research_task_graph.py:185:create_task_plan
0077_research_task_graph.py:9:depends_on
0077_research_task_graph.py:7:down_revision
0077_research_task_graph.py:32:finished_at
0077_research_task_graph.py:436:frozen_at
0077_research_task_graph.py:96:hypothesis_version_id
0077_research_task_graph.py:96:hypothesis_versions
0077_research_task_graph.py:448:literature_source_project_links
0077_research_task_graph.py:450:literature_sources
0077_research_task_graph.py:100:manuscript_version_id
0077_research_task_graph.py:100:manuscript_versions
0077_research_task_graph.py:517:pr301_event_insert_guard
0077_research_task_graph.py:576:pr301_graph_final_guard
0077_research_task_graph.py:616:pr301_receipt_complete
0077_research_task_graph.py:663:pr301_receipt_complete_commit
0077_research_task_graph.py:514:pr301_receipt_insert
0077_research_task_graph.py:507:pr301_receipt_insert_guard
0077_research_task_graph.py:539:pr301_receipt_link_guard
0077_research_task_graph.py:613:pr301_task_final
0077_research_task_graph.py:348:pr301_task_guard
0077_research_task_graph.py:425:pr301_validate_input
0077_research_task_graph.py:15:requested_by
0077_research_task_graph.py:95:research_question_version_id
0077_research_task_graph.py:95:research_question_versions
0077_research_task_graph.py:92:research_task_inputs
0077_research_task_graph.py:78:research_task_step_dependencies
0077_research_task_graph.py:134:research_task_step_inputs
0077_research_task_graph.py:46:research_task_steps
0077_research_task_graph.py:186:seal_task_plan
0077_research_task_graph.py:98:source_version_id
0077_research_task_graph.py:98:source_versions
0077_research_task_graph.py:31:started_at
0077_research_task_graph.py:22:strategy_id
0077_research_task_graph.py:22:strategy_id
0077_research_task_graph.py:25:strategy_version
0077_research_task_graph.py:25:strategy_version
0077_research_task_graph.py:428:version_id
0077_research_task_graph.py:15:actors
0077_research_task_graph.py:454:artifacts
0077_research_task_graph.py:446:claims
0077_research_task_graph.py:442:hypotheses
0077_research_task_graph.py:14:projects
0077_research_task_graph.py:458:publications
0077_research_task_graph.py:13:id
0077_research_task_graph.py:29:status
0077_research_task_graph.py:29:status
0077_research_task_graph.py:215:reason
0077_research_task_graph.py:211:sequence
0077_research_task_graph.py:211:sequence
0077_research_task_graph.py:6:0077_research_task_graph
# src/researchbase/persistence/models.py
models.py:394:byte_size
models.py:394:byte_size
# src/researchbase/application/commands.py
commands.py:714:error_code
# src/researchbase/application/metadata_observation.py
metadata_observation.py:103:invocation_id
# src/researchbase/persistence/task_safety_repository.py
task_safety_repository.py:58:rb_phase2_lock_project
task_safety_repository.py:60:pr301:command:
task_safety_repository.py:60:pr301:task:
# src/researchbase/foundation/hashing.py
hashing.py:33:sha256_canonical_json
# src/researchbase/persistence/agent_version_repository.py
agent_version_repository.py:78:pr302:actor:
agent_version_repository.py:80:pr302:version:
# src/researchbase/api/errors.py
errors.py:163:INTERNAL_ERROR
```

### 12.2 Foreign-key backing keys

All key-audit commands below exited 0. Existing composite targets:

| Target | Delivered backing key |
| --- | --- |
| research_tasks(id, project_id) | 0077_research_task_graph.py:36 UNIQUE (id, project_id) |
| research_task_steps(research_task_id, id) | 0077_research_task_graph.py:64 UNIQUE (research_task_id, id) |
| agent_versions(id, project_id, actor_id) | 0079_agent_identity_versions.py:45 UNIQUE (id, project_id, actor_id) |

Three other targets on accepted tables lack their exact composite keys at 0079.
A single id PK or different UNIQUE tuple is not substituted. The forward §2 DDL
already supplies all three; this correction retains them:

| Target | Forward backing constraint (new in PR3-03) |
| --- | --- |
| budget_reservations(research_task_id, id, operation_id) | pr303_reservation_operation_key |
| budget_usage_records(research_task_id, reservation_id, id) | pr303_usage_reservation_key |
| research_task_command_receipts(research_task_id, project_id, id) | pr303_receipt_scope_key |

All five composite targets on new tables have explicit §2 backing keys:

| Target | Proposed backing key |
| --- | --- |
| agent_tool_policies(id, project_id) | UNIQUE (id, project_id) |
| capability_invocations(research_task_id, project_id, id) | UNIQUE (research_task_id, project_id, id) |
| capability_invocations(research_task_id, id) | UNIQUE (research_task_id, id) |
| capability_invocations(research_task_id, id, reservation_id) | UNIQUE (research_task_id, id, reservation_id) |
| capability_invocation_events(research_task_id, project_id, id) | UNIQUE (research_task_id, project_id, id) |

There are **11 distinct composite targets**: 3 delivered + 3 forward keys on
accepted tables + 5 on new tables. Repeated references count once. Every target
has a backing key; no further supporting UNIQUE is needed. New constraints are
for the future migrations/versions/0080_capability_gateway.py (**new in PR3-03**,
not present/executed). Its proposed declarations and document lines are captured
below. No accepted migration was edited.

Scalar targets actors(id), projects(id), artifact_versions(id),
research_question_versions(id), hypothesis_versions(id), claim_versions(id),
source_versions(id), manuscript_versions(id) have delivered PKs below. Proposed
agent_tool_policies(id) and capability_invocation_events(id) have §2 PKs. runs(id)
is supplemental evidence; the fake slice adds no Run FK or execution record.
No composite run/project target is used.

```sh
rg -n --with-filename -F -e 'CREATE TABLE research_tasks (' -e 'CREATE TABLE research_task_steps (' -e 'UNIQUE (id, project_id)' -e 'UNIQUE (research_task_id, id)' migrations/versions/0077_research_task_graph.py
rg -n --with-filename -F -e 'CREATE TABLE agent_versions (' -e 'UNIQUE (id, project_id, actor_id)' migrations/versions/0079_agent_identity_versions.py
rg -n --with-filename -F -e 'CREATE TABLE budget_reservations (' -e 'CREATE TABLE budget_usage_records (' -e 'UNIQUE (research_task_id, id)' -e 'UNIQUE (research_task_id, operation_id)' -e 'UNIQUE (research_task_id, reservation_id, receipt_id)' migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -A 1 -F -- '"actors",' migrations/versions/0002_actor_project_workspace.py
rg -n --with-filename -m 1 -A 1 -F -- '"projects",' migrations/versions/0002_actor_project_workspace.py
rg -n --with-filename -m 1 -A 1 -F -- '"artifact_versions",' migrations/versions/0006_artifact_version.py
rg -n --with-filename -m 1 -A 1 -F -- '"research_question_versions",' migrations/versions/0003_research_question_hypothesis.py
rg -n --with-filename -m 1 -A 1 -F -- '"hypothesis_versions",' migrations/versions/0003_research_question_hypothesis.py
rg -n --with-filename -m 1 -A 1 -F -- '"claim_versions",' migrations/versions/0014_claim_evidence.py
rg -n --with-filename -m 1 -A 1 -F -- '"source_versions",' migrations/versions/0022_source_version_and_merge_lineage.py
rg -n --with-filename -m 1 -A 1 -F -- '"runs",' migrations/versions/0008_run_core.py
rg -n --with-filename -m 1 -A 1 -F -- 'CREATE TABLE manuscript_versions (' migrations/versions/0035_pr2_12_publication_draft.py
rg -n --with-filename -F -e 'UNIQUE (' -e 'PRIMARY KEY' docs/phase3/PR3-03-contract-freeze.md | awk -F: '$2 < 600'
```

Captured stdout in command order (hyphens mark context lines):

```text
migrations/versions/0077_research_task_graph.py:12:CREATE TABLE research_tasks (
migrations/versions/0077_research_task_graph.py:36:  UNIQUE (id, project_id),
migrations/versions/0077_research_task_graph.py:46:CREATE TABLE research_task_steps (
migrations/versions/0077_research_task_graph.py:64:  UNIQUE (research_task_id, id),
migrations/versions/0077_research_task_graph.py:194:  UNIQUE (research_task_id, id),
migrations/versions/0077_research_task_graph.py:217:  UNIQUE (research_task_id, id),
migrations/versions/0077_research_task_graph.py:253:  UNIQUE (research_task_id, id),
migrations/versions/0079_agent_identity_versions.py:15:CREATE TABLE agent_versions (
migrations/versions/0079_agent_identity_versions.py:45:  UNIQUE (id, project_id, actor_id)
migrations/versions/0078_task_safety_policies.py:33:  UNIQUE (research_task_id, id),
migrations/versions/0078_task_safety_policies.py:63:  UNIQUE (research_task_id, id),
migrations/versions/0078_task_safety_policies.py:88:  UNIQUE (research_task_id, id),
migrations/versions/0078_task_safety_policies.py:140:CREATE TABLE budget_reservations (
migrations/versions/0078_task_safety_policies.py:160:  UNIQUE (research_task_id, id),
migrations/versions/0078_task_safety_policies.py:161:  UNIQUE (research_task_id, operation_id),
migrations/versions/0078_task_safety_policies.py:172:CREATE TABLE budget_usage_records (
migrations/versions/0078_task_safety_policies.py:196:  UNIQUE (research_task_id, id),
migrations/versions/0078_task_safety_policies.py:197:  UNIQUE (research_task_id, reservation_id, receipt_id),
migrations/versions/0078_task_safety_policies.py:226:  UNIQUE (research_task_id, id),
migrations/versions/0002_actor_project_workspace.py:18:        "actors",
migrations/versions/0002_actor_project_workspace.py-19-        sa.Column("id", actor_uuid, primary_key=True),
migrations/versions/0002_actor_project_workspace.py:38:        "projects",
migrations/versions/0002_actor_project_workspace.py-39-        sa.Column("id", actor_uuid, primary_key=True),
migrations/versions/0006_artifact_version.py:33:        "artifact_versions",
migrations/versions/0006_artifact_version.py-34-        sa.Column("id", uuid, primary_key=True),
migrations/versions/0003_research_question_hypothesis.py:42:        "research_question_versions",
migrations/versions/0003_research_question_hypothesis.py-43-        sa.Column("id", uuid, primary_key=True),
migrations/versions/0003_research_question_hypothesis.py:107:        "hypothesis_versions",
migrations/versions/0003_research_question_hypothesis.py-108-        sa.Column("id", uuid, primary_key=True),
migrations/versions/0014_claim_evidence.py:37:        "claim_versions",
migrations/versions/0014_claim_evidence.py-38-        sa.Column("id", uuid, primary_key=True),
migrations/versions/0022_source_version_and_merge_lineage.py:20:        "source_versions",
migrations/versions/0022_source_version_and_merge_lineage.py-21-        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
migrations/versions/0008_run_core.py:18:        "runs",
migrations/versions/0008_run_core.py-19-        sa.Column("id", uuid, primary_key=True),
migrations/versions/0035_pr2_12_publication_draft.py:29:    CREATE TABLE manuscript_versions (
migrations/versions/0035_pr2_12_publication_draft.py-30-      id UUID PRIMARY KEY,
docs/phase3/PR3-03-contract-freeze.md:84:  UNIQUE (research_task_id, id, operation_id);
docs/phase3/PR3-03-contract-freeze.md:86:  UNIQUE (research_task_id, reservation_id, id);
docs/phase3/PR3-03-contract-freeze.md:88:  UNIQUE (research_task_id, project_id, id);
docs/phase3/PR3-03-contract-freeze.md:91:  id uuid NOT NULL PRIMARY KEY,
docs/phase3/PR3-03-contract-freeze.md:112:  UNIQUE (project_id, version),
docs/phase3/PR3-03-contract-freeze.md:113:  UNIQUE (id, project_id),
docs/phase3/PR3-03-contract-freeze.md:121:  id uuid NOT NULL PRIMARY KEY,
docs/phase3/PR3-03-contract-freeze.md:131:  UNIQUE (policy_id, capability_id, capability_version, operation,
docs/phase3/PR3-03-contract-freeze.md:142:  id uuid NOT NULL PRIMARY KEY,
docs/phase3/PR3-03-contract-freeze.md:185:  UNIQUE (research_task_id, project_id, id),
docs/phase3/PR3-03-contract-freeze.md:186:  UNIQUE (research_task_id, id),
docs/phase3/PR3-03-contract-freeze.md:187:  UNIQUE (research_task_id, id, reservation_id),
docs/phase3/PR3-03-contract-freeze.md:238:  id uuid NOT NULL PRIMARY KEY,
docs/phase3/PR3-03-contract-freeze.md:264:  id uuid NOT NULL PRIMARY KEY,
docs/phase3/PR3-03-contract-freeze.md:281:  UNIQUE (research_task_id, project_id, id),
docs/phase3/PR3-03-contract-freeze.md:282:  UNIQUE (invocation_id, sequence),
```

### 12.3 New identifier labels and counts

Collective labels cover 246 distinct new names. The exact script below constructs
the inspectable inventory as set new, counting scoped columns by owning table,
proposed files by full path and DTOs by type. Repeated mentions, SQL built-ins,
enum literals and repeated DTO argument spellings do not add identifiers.

```sh
uv run python - <<'PYCOUNT'
from pathlib import Path
import re

s = Path('docs/phase3/PR3-03-contract-freeze.md').read_text()
body = s.split('## 10.', 1)[0]
new = set(re.findall(r'\bpr303_\w+', body))
new.update(re.findall(r'CREATE TABLE (\w+) \(', body))
new.add('0080_capability_gateway')
section8 = body.split('## 8.', 1)[1].split('## 9.', 1)[0]
new.update(re.findall(r'^\| (\w+) \|', section8, re.M))
new.difference_update({'Type', 'Operation'})
new.update('GatewayAccounting reserve_in_uow settle_in_uow SkillRegistryLoader '
           'SkillRouter RoutingPolicy CapabilityPolicy RegistryEntry'.split())
new.update('register_agent_tool_policy request_capability_invocation '
           'start_capability_invocation finish_capability_invocation '
           'get_capability_invocation list_task_capability_invocations '
           'get_agent_tool_policy CapabilityGateway CapabilityGateway.invoke'.split())
columns = []
for table, ddl in re.findall(r'CREATE TABLE (\w+) \((.*?)\n\);', body, re.S):
    columns += [f'{table}.{c}' for c in re.findall(
        r'^  (\w+) (?:uuid|text|integer|timestamptz)\b', ddl, re.M)]
for table, ddl in re.findall(r'ALTER TABLE (\w+)\n(.*?);', body, re.S):
    columns += [f'{table}.{c}' for c in re.findall(r'ADD COLUMN (\w+)', ddl)]
paths = ['migrations/versions/0080_capability_gateway.py',
         'docs/phase3/PR3-03-evidence.md']
paths += re.findall(r'^\| (tests/[^ |]+\.py) \|', body, re.M)
paths += ['src/researchbase/' + name for name in [
    'agent_runtime/domain/capability_invocation.py',
    'agent_runtime/domain/tool_policy.py',
    'agent_runtime/application/gateway_contracts.py',
    'agent_runtime/application/capability_gateway.py',
    'agent_runtime/application/routing.py',
    'agent_runtime/ports/capability_gateway.py',
    'agent_runtime/ports/gateway_repository.py',
    'persistence/capability_gateway_repository.py',
    'persistence/capability_gateway_queries.py']]
new.update(columns)
new.update(paths)
print('label markers:', s.count('new in ' + 'PR3-03'))
print('named new identifiers:', len(new))
print('qualified columns:', len(columns))
print('proposed paths:', len(paths))
PYCOUNT
```

Captured stdout (exit 0):

```text
label markers: 10
named new identifiers: 246
qualified columns: 106
proposed paths: 22
```

### 12.4 Reproducible six-vector evidence

Exact command run from the repository (exit 0). The uv cache location is a
process-only setting; no dependency or lockfile was changed. The script reads
exactly the six quoted JSON inputs in §7.2, asserts byte-for-byte canonical text
equality, calls both repository helpers and verifies every recorded digest.

```sh
export UV_CACHE_DIR=/private/tmp/researchbase-pr303-uv-cache
uv run python - <<'PY'
import json
import re
from pathlib import Path
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.hashing import sha256_canonical_json

section = Path('docs/phase3/PR3-03-contract-freeze.md').read_text().split('### 7.2 Computed fixed vectors', 1)[1].split('## 8.', 1)[0]
vectors = re.findall(r'```json\n(.*?)\n```\n\nsha256-cjson-v1: `([0-9a-f]{64})`', section, re.S)
assert len(vectors) == 6
for payload, expected in vectors:
    value = json.loads(payload)
    assert canonical_json_bytes(value).decode('utf-8') == payload
    actual = sha256_canonical_json(value)
    assert actual == expected
    print(actual)
PY
```

Captured stdout, in §7.2 input order:

```text
79fd29b8c5f855b2d2728a13ba245b96d2287fa52fd364646f4a155e40ff4d8f
2be8fb87e16870441bee24424875c19e4bef7500ec600750924b2c00c8d778f1
2087127ad6ee04e51ebb37b6fb2f89af70209d3dd99a83645a8f803e7e6125f9
dcbc9330ce3ba36e9bc0988395950922f278aba37cef35d37239d8f8b099cf7c
725ad2c4ac6b22c5f53ee1138b5d65d88b344e033d52df268db46afd7d3f293b
a6d9214ed01cfe46686c39829bde5d0a733d16c31d8b5297e48d245b70ce13b3
```

All six digests matched the existing §7.2 values; no digest discrepancy or
correction was needed. This is a documentation evidence run, not pytest.

§7.2 expected versus the captured §12.4 stdout:

| Input | Expected | Captured actual |
| --- | --- | --- |
| schema_vector | 79fd29b8c5f855b2d2728a13ba245b96d2287fa52fd364646f4a155e40ff4d8f | 79fd29b8c5f855b2d2728a13ba245b96d2287fa52fd364646f4a155e40ff4d8f |
| empty_capability_set | 2be8fb87e16870441bee24424875c19e4bef7500ec600750924b2c00c8d778f1 | 2be8fb87e16870441bee24424875c19e4bef7500ec600750924b2c00c8d778f1 |
| fake_capability_set | 2087127ad6ee04e51ebb37b6fb2f89af70209d3dd99a83645a8f803e7e6125f9 | 2087127ad6ee04e51ebb37b6fb2f89af70209d3dd99a83645a8f803e7e6125f9 |
| empty_policy | dcbc9330ce3ba36e9bc0988395950922f278aba37cef35d37239d8f8b099cf7c | dcbc9330ce3ba36e9bc0988395950922f278aba37cef35d37239d8f8b099cf7c |
| allow_and_deny_policy | 725ad2c4ac6b22c5f53ee1138b5d65d88b344e033d52df268db46afd7d3f293b | 725ad2c4ac6b22c5f53ee1138b5d65d88b344e033d52df268db46afd7d3f293b |
| parameters_vector | a6d9214ed01cfe46686c39829bde5d0a733d16c31d8b5297e48d245b70ce13b3 | a6d9214ed01cfe46686c39829bde5d0a733d16c31d8b5297e48d245b70ce13b3 |

### 12.5 Documentation checks, visibility and Git state

The §9.1 PostgreSQL 18 matrix explicitly requires two policy-vector cases:
empty_policy and allow_and_deny_policy. Each reconstructs typed rows using
§7.1a, compares canonical text with §7.2 and recomputes the corresponding SQL
digest shown side by side above; both derived CapabilitySet digests also compare.
Both §5 and §6 explicitly match draft §6: project → pr301 command → pr301 task
→ pr302 actor → pr302 version → rows. Delivered safety sequence is
src/researchbase/persistence/task_safety_repository.py:51–74; delivered S1 keys
are src/researchbase/persistence/agent_version_repository.py:78–80. Composing
those keys before task rows is a required future implementation change.

Run with UV_CACHE_DIR=/private/tmp/researchbase-pr303-uv-cache exported in the
process environment only. Exact static commands and observed results:

```sh
git diff --check HEAD && uv run ruff check .
```

Combined command: exit 0. git diff --check HEAD emitted no diagnostics;
uv run ruff check . emitted the following stdout, with no stderr:

```text
All checks passed!
```

The §12.4 uv run python stdin command exited 0: 6/6 vector comparisons.
The literal audit commands in §§12.1 and 12.2 exited 0; their stdout is
included in full. Unit tests: NOT RUN (no count). Architecture tests: NOT RUN
(no count). PostgreSQL/constraint/migration/concurrency/replay suites: NOT RUN
(no count). Full suite: NOT RUN (external check loop owns it). No pytest,
migration upgrade/downgrade or database execution was invoked for this task.
SQL/Python policy parity is a required implementation test, not verified PASS.

Exact visibility command (exit 0) and captured stdout (displayed with two
leading spaces per output line so this evidence does not match its own search):

```sh
sed -n '/^## /p' docs/phase3/PR3-03-contract-freeze.md
```

```text
  ## 1. Baseline, decisions and scope
  ## 2. Complete additive DDL
  ## 3. Constrained receipt and task-event extensions
  ## 4. Guard functions, trigger attachment and whole-state validation
  ## 5. Exact lock, transaction, replay and read recipes
  ## 6. Trusted in-UoW accounting seam (D303-04)
  ## 7. Policy, routing, retained material and hashes (D303-03)
  ## 8. Closed Application commands, DTOs and gateway port
  ## 9. Existing ErrorCode mapping and required implementation evidence
  ## 10. Existing identifier anchors and documentation verification
  ## 11. Review disposition and visibility
  ## 12. Verification evidence
```

§1 retains all exclusions and the complete ACCEPTED-AS-RECOMMENDED owner
decision table dated 2026-10-22; §9.1 retains the full test matrix and gate
commands. §12 is the final top-level section.

Commit result, real git log -1 --stat and git status --short will be reported
after the commit attempt outside this document. No old-HEAD log is substituted
for the required new commit. On any index-lock or sandbox error, quote it
verbatim and stop; no lock deletion or permission workaround is authorized.
