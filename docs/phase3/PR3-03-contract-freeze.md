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

### 4.4 Normative new function definitions

The following SQL is documentation for the future 0080 migration, never an
instruction to execute it during this freeze. These complete bodies, together
with the §2/§3 CHECK/FK constraints, replace any interpretation of the preceding
behavior tables as sufficient executable specifications. JSONB below is transient
comparison/hash material, not persisted semantic state.

These bodies have not yet been compile-checked or verified against PostgreSQL 18.
The FIRST implementation step is to apply 0080 to a disposable PostgreSQL 18
database and run each body's `CREATE OR REPLACE`; only after every body compiles
may DDL/integration tests be authorized. Failure to compile blocks implementation
acceptance. This is a documented future gate; do not execute it for this pack.

Delivered callable signatures (argument order and return type are binding):

- `pr301_validate_input(p_task uuid, p_question uuid, p_hypothesis uuid,
  p_claim uuid, p_source uuid, p_artifact uuid, p_manuscript uuid,
  p_hash text, p_scheme text) RETURNS void`: migrations/versions/0077_research_task_graph.py:425–427;
  branches 433–469 distinguish scope, frozen status and provenance.
- `pr304_validate_safety(p_task uuid) RETURNS void`:
  migrations/versions/0078_task_safety_policies.py:467; complete delivered body 467–579.
- `pr304_canonical_policy_json(p_value jsonb) RETURNS text LANGUAGE plpgsql
  IMMUTABLE STRICT`: migrations/versions/0078_task_safety_policies.py:298–299;
  complete body 298–320. It accepts transient integer-valued JSON, not registry
  bytes or ArtifactVersion IDs. No new serializer or registry SQL helper is assumed.

Registry entry eligibility, retained-byte canonical JSON validation, requested
parameter hash versus byte content, and identity-based FakeConsumerCapability
are Application obligations in §§6–8: the delivered schema stores artifact pins,
not artifact bytes. SQL validates the exact owning pins, byte size and allowed
fake tuple; it cannot parse an external ArtifactStore through a nonexistent SQL
helper. Candidate OUTPUT here means an artifact reference admitted as candidate
by Application, never promotion of scientific truth. SQL never writes its target.

```sql
CREATE OR REPLACE FUNCTION pr303_immutable() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, public, pg_temp AS $$
BEGIN
 RAISE EXCEPTION 'immutable gateway history'
  USING ERRCODE='23514', CONSTRAINT='pr301_immutable';
END $$;

CREATE OR REPLACE FUNCTION pr303_policy_insert_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE t research_tasks%ROWTYPE; r research_task_command_receipts%ROWTYPE;
 now_at timestamptz := clock_timestamp();
BEGIN
 SELECT * INTO t FROM research_tasks WHERE id=NEW.registration_task_id
  AND xmin=pg_current_xact_id()::xid;
 SELECT * INTO r FROM research_task_command_receipts WHERE id=NEW.receipt_id
  AND research_task_id=t.id AND xmin=pg_current_xact_id()::xid;
 IF t.id IS NULL OR r.id IS NULL THEN
  RAISE EXCEPTION 'fresh registration owners required' USING ERRCODE='23514', CONSTRAINT='pr301_immutable';
 END IF;
 IF ROW(NEW.project_id,NEW.created_by,NEW.created_at,t.row_version)
  IS DISTINCT FROM ROW(r.project_id,r.actor_id,r.completed_at,r.resulting_row_version)
  OR t.project_id IS DISTINCT FROM NEW.project_id
  OR r.command_name<>'register_agent_tool_policy' OR r.result_tool_policy_id IS DISTINCT FROM NEW.id
  OR NEW.created_at<transaction_timestamp() OR NEW.created_at>now_at THEN
  RAISE EXCEPTION 'registration attribution' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
 END IF;
 IF t.status NOT IN ('CREATED','PLANNING') THEN
  RAISE EXCEPTION 'registration task state' USING ERRCODE='23514', CONSTRAINT='pr301_state';
 END IF;
 IF NOT EXISTS(SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id
  JOIN project_role_assignments p ON p.membership_id=m.id JOIN actor_subject_bindings b ON b.actor_id=a.id
  WHERE a.id=r.actor_id AND a.actor_type='HUMAN' AND a.retired_at IS NULL
  AND m.project_id=t.project_id AND m.status='ACTIVE' AND p.role='OWNER'
  AND p.effective_from<=now_at AND (p.effective_until IS NULL OR now_at<p.effective_until)
  AND b.status='ACTIVE' AND b.bound_at<=now_at AND (b.revoked_at IS NULL OR now_at<b.revoked_at)) THEN
  RAISE EXCEPTION 'current Human owner required' USING ERRCODE='23514', CONSTRAINT='pr301_scope';
 END IF;
 IF NEW.version<>btrim(NEW.version) OR lower(NEW.version) IN ('latest','current','main','master')
  OR NEW.version ~ '[*?\[\]{}()^$|\\]' THEN
  RAISE EXCEPTION 'exact policy pin required' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
 END IF;
 PERFORM pr301_validate_input(t.id,NULL,NULL,NULL,NULL,NEW.registry_artifact_version_id,NULL,NEW.registry_content_hash,NULL);
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION pr303_permission_insert_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE p agent_tool_policies%ROWTYPE; v text;
BEGIN
 SELECT * INTO p FROM agent_tool_policies WHERE id=NEW.policy_id AND xmin=pg_current_xact_id()::xid;
 IF p.id IS NULL OR NOT EXISTS(SELECT 1 FROM research_tasks t
  JOIN research_task_command_receipts r ON r.research_task_id=t.id
  WHERE t.id=p.registration_task_id AND t.project_id=p.project_id AND r.id=p.receipt_id
  AND r.project_id=p.project_id AND r.resulting_row_version=t.row_version
  AND r.command_name='register_agent_tool_policy' AND r.result_tool_policy_id=p.id
  AND t.xmin=pg_current_xact_id()::xid AND r.xmin=pg_current_xact_id()::xid) THEN
  RAISE EXCEPTION 'fresh permission owners required' USING ERRCODE='23514', CONSTRAINT='pr301_immutable';
 END IF;
 IF NEW.project_id IS DISTINCT FROM p.project_id THEN
  RAISE EXCEPTION 'permission scope' USING ERRCODE='23514', CONSTRAINT='pr301_scope';
 END IF;
 FOREACH v IN ARRAY ARRAY[NEW.capability_id,NEW.capability_version,NEW.operation,NEW.adapter_id,NEW.adapter_version] LOOP
  IF v<>btrim(v) OR lower(v) IN ('latest','current','main','master') OR v ~ '[*?\[\]{}()^$|\\]' THEN
   RAISE EXCEPTION 'exact permission pin required' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
  END IF;
 END LOOP;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION pr303_invocation_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE t research_tasks%ROWTYPE; r research_task_command_receipts%ROWTYPE;
 br budget_reservations%ROWTYPE; u budget_usage_records%ROWTYPE;
 receipt uuid; stamp timestamptz; op text; permitted text[];
BEGIN
 IF TG_OP='DELETE' THEN
  RAISE EXCEPTION 'immutable invocation' USING ERRCODE='23514', CONSTRAINT='pr301_immutable';
 END IF;
 IF TG_OP='INSERT' THEN
  receipt:=NEW.request_receipt_id; stamp:=NEW.created_at; op:='request_capability_invocation';
  IF NEW.status<>'REQUESTED' OR NEW.row_version<>1 THEN
   RAISE EXCEPTION 'initial invocation state' USING ERRCODE='23514', CONSTRAINT='pr301_state';
  END IF;
 ELSE
  IF OLD.status NOT IN ('REQUESTED','RUNNING') OR EXISTS(SELECT 1 FROM capability_invocations
   WHERE id=OLD.id AND xmin=pg_current_xact_id()::xid) THEN
   RAISE EXCEPTION 'committed nonterminal invocation required' USING ERRCODE='23514', CONSTRAINT='pr301_immutable';
  END IF;
  IF OLD.status='REQUESTED' AND NEW.status='RUNNING' THEN
   receipt:=NEW.start_receipt_id; stamp:=NEW.started_at; op:='start_capability_invocation';
   permitted:=ARRAY['status','row_version','started_at','start_receipt_id'];
  ELSIF (OLD.status='REQUESTED' AND NEW.status='CANCELLED') OR
   (OLD.status='RUNNING' AND NEW.status IN ('SUCCEEDED','FAILED','UNKNOWN_OUTCOME','CANCELLED')) THEN
   receipt:=NEW.finish_receipt_id; stamp:=NEW.finished_at; op:='finish_capability_invocation';
   permitted:=ARRAY['status','row_version','finished_at','finish_receipt_id','usage_record_id',
    'trace_artifact_version_id','trace_content_hash','result_summary','error_code'];
  ELSE
   RAISE EXCEPTION 'illegal invocation transition' USING ERRCODE='23514', CONSTRAINT='pr301_state';
  END IF;
  IF NEW.row_version<>OLD.row_version+1 THEN
   RAISE EXCEPTION 'invocation revision' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
  END IF;
  IF to_jsonb(NEW)-permitted IS DISTINCT FROM to_jsonb(OLD)-permitted THEN
   RAISE EXCEPTION 'immutable invocation material' USING ERRCODE='23514', CONSTRAINT='pr301_immutable';
  END IF;
 END IF;
 SELECT * INTO t FROM research_tasks WHERE id=NEW.research_task_id AND xmin=pg_current_xact_id()::xid;
 SELECT * INTO r FROM research_task_command_receipts WHERE id=receipt AND xmin=pg_current_xact_id()::xid;
 IF t.id IS NULL OR r.id IS NULL THEN
  RAISE EXCEPTION 'fresh invocation owners required' USING ERRCODE='23514', CONSTRAINT='pr301_immutable';
 END IF;
 IF ROW(r.research_task_id,r.project_id,r.resulting_row_version,r.command_name,r.result_capability_invocation_id,
   r.result_tool_policy_id,r.resulting_invocation_revision,r.completed_at)
  IS DISTINCT FROM ROW(t.id,NEW.project_id,t.row_version,op,NEW.id,NEW.policy_id,NEW.row_version,stamp)
  OR t.project_id IS DISTINCT FROM NEW.project_id OR stamp IS NULL
  OR stamp<transaction_timestamp() OR stamp>clock_timestamp() THEN
  RAISE EXCEPTION 'invocation receipt attribution' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
 END IF;
 IF op<>'finish_capability_invocation' AND t.status NOT IN ('CREATED','PLANNING') THEN
  RAISE EXCEPTION 'invocation admission state' USING ERRCODE='23514', CONSTRAINT='pr301_state';
 END IF;
 SELECT * INTO br FROM budget_reservations WHERE id=NEW.reservation_id;
 IF br.id IS NULL OR ROW(br.research_task_id,br.operation_id,br.step_id,br.budget_id)
  IS DISTINCT FROM ROW(t.id,NEW.id,NEW.step_id,t.budget_policy_id) THEN
  RAISE EXCEPTION 'reservation ownership' USING ERRCODE='23514', CONSTRAINT='pr301_provenance';
 END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.requested_by IS DISTINCT FROM r.actor_id OR br.receipt_id IS DISTINCT FROM r.id
   OR br.created_at IS DISTINCT FROM stamp OR NOT EXISTS(SELECT 1 FROM budget_reservations
    WHERE id=br.id AND xmin=pg_current_xact_id()::xid) THEN
   RAISE EXCEPTION 'fresh request reservation' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
  END IF;
 ELSIF op='finish_capability_invocation' THEN
  SELECT * INTO u FROM budget_usage_records WHERE id=NEW.usage_record_id AND xmin=pg_current_xact_id()::xid;
  IF u.id IS NULL OR ROW(u.research_task_id,u.reservation_id,u.receipt_id,u.created_at,u.outcome,u.is_final)
   IS DISTINCT FROM ROW(t.id,br.id,r.id,stamp,CASE WHEN NEW.status='UNKNOWN_OUTCOME' THEN 'UNKNOWN' ELSE NEW.status END,
    NEW.status<>'UNKNOWN_OUTCOME') THEN
   RAISE EXCEPTION 'fresh finish usage' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
  END IF;
  IF OLD.status='REQUESTED' AND (u.wall_time_seconds<>0 OR u.gpu_hours<>0 OR u.token_cost<>0) THEN
   RAISE EXCEPTION 'undispatched cancellation variable charge' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
  END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION pr303_ref_insert_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE i capability_invocations%ROWTYPE; r research_task_command_receipts%ROWTYPE;
BEGIN
 SELECT * INTO i FROM capability_invocations WHERE id=NEW.invocation_id;
 SELECT * INTO r FROM research_task_command_receipts WHERE id=NEW.receipt_id AND xmin=pg_current_xact_id()::xid;
 IF r.id IS NULL OR NOT EXISTS(SELECT 1 FROM research_tasks WHERE id=NEW.research_task_id
  AND row_version=r.resulting_row_version AND xmin=pg_current_xact_id()::xid) THEN
  RAISE EXCEPTION 'fresh reference owners required' USING ERRCODE='23514', CONSTRAINT='pr301_immutable';
 END IF;
 IF ROW(i.research_task_id,i.project_id,r.research_task_id,r.project_id,r.result_capability_invocation_id)
  IS DISTINCT FROM ROW(NEW.research_task_id,NEW.project_id,NEW.research_task_id,NEW.project_id,i.id) THEN
  RAISE EXCEPTION 'reference scope' USING ERRCODE='23514', CONSTRAINT='pr301_scope';
 END IF;
 IF NEW.direction='INPUT' THEN
  IF i.status<>'REQUESTED' OR i.request_receipt_id IS DISTINCT FROM r.id
   OR r.command_name<>'request_capability_invocation' OR NOT EXISTS(SELECT 1 FROM capability_invocations
    WHERE id=i.id AND xmin=pg_current_xact_id()::xid) THEN
   RAISE EXCEPTION 'request inputs only' USING ERRCODE='23514', CONSTRAINT='pr301_state';
  END IF;
 ELSE
  IF NEW.artifact_version_id IS NULL OR r.command_name<>'finish_capability_invocation'
   OR NOT EXISTS(SELECT 1 FROM capability_invocation_events e WHERE e.id=r.result_capability_event_id
    AND e.invocation_id=i.id AND e.receipt_id=r.id AND e.xmin=pg_current_xact_id()::xid AND
    ((e.event_type='FINISHED' AND e.new_status='SUCCEEDED' AND i.status='SUCCEEDED'
      AND i.finish_receipt_id=r.id AND EXISTS(SELECT 1 FROM capability_invocations WHERE id=i.id AND xmin=pg_current_xact_id()::xid))
     OR (e.event_type='RECONCILED' AND e.reconciled_outcome='SUCCEEDED' AND i.status='UNKNOWN_OUTCOME'
      AND EXISTS(SELECT 1 FROM capability_invocations WHERE id=i.id AND xmin<>pg_current_xact_id()::xid)))) THEN
   RAISE EXCEPTION 'confirmed candidate outputs only' USING ERRCODE='23514', CONSTRAINT='pr301_state';
  END IF;
 END IF;
 PERFORM pr301_validate_input(NEW.research_task_id,NEW.research_question_version_id,NEW.hypothesis_version_id,
  NEW.claim_version_id,NEW.source_version_id,NEW.artifact_version_id,NEW.manuscript_version_id,NEW.content_hash,NEW.hash_scheme);
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION pr303_event_insert_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE i capability_invocations%ROWTYPE; r research_task_command_receipts%ROWTYPE;
 prev capability_invocation_events%ROWTYPE; u budget_usage_records%ROWTYPE;
 op text; saved_receipt uuid; stamp timestamptz;
BEGIN
 SELECT * INTO i FROM capability_invocations WHERE id=NEW.invocation_id;
 SELECT * INTO r FROM research_task_command_receipts WHERE id=NEW.receipt_id AND xmin=pg_current_xact_id()::xid;
 IF r.id IS NULL OR NOT EXISTS(SELECT 1 FROM research_tasks WHERE id=NEW.research_task_id
  AND row_version=r.resulting_row_version AND xmin=pg_current_xact_id()::xid) THEN
  RAISE EXCEPTION 'fresh event owners required' USING ERRCODE='23514', CONSTRAINT='pr301_immutable';
 END IF;
 op:=CASE NEW.event_type WHEN 'REQUESTED' THEN 'request_capability_invocation'
  WHEN 'STARTED' THEN 'start_capability_invocation' ELSE 'finish_capability_invocation' END;
 IF ROW(i.research_task_id,i.project_id,i.reservation_id,r.research_task_id,r.project_id,r.command_name,
  r.actor_id,r.completed_at,r.result_capability_event_id,r.result_capability_invocation_id,r.result_tool_policy_id,r.resulting_invocation_revision)
  IS DISTINCT FROM ROW(NEW.research_task_id,NEW.project_id,NEW.reservation_id,NEW.research_task_id,NEW.project_id,op,
   NEW.actor_id,NEW.occurred_at,NEW.id,i.id,i.policy_id,NEW.invocation_row_version)
  OR NEW.occurred_at<transaction_timestamp() OR NEW.occurred_at>clock_timestamp() THEN
  RAISE EXCEPTION 'event attribution' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
 END IF;
 IF NEW.sequence>1 THEN
  SELECT * INTO prev FROM capability_invocation_events WHERE invocation_id=i.id AND sequence=NEW.sequence-1;
  IF prev.id IS NULL OR prev.new_status IS DISTINCT FROM NEW.prior_status OR prev.occurred_at>NEW.occurred_at THEN
   RAISE EXCEPTION 'adjacent event history' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
  END IF;
 END IF;
 IF NEW.event_type='RECONCILED' THEN
  IF i.status<>'UNKNOWN_OUTCOME' OR i.row_version<>3 OR NOT EXISTS(SELECT 1 FROM capability_invocations
   WHERE id=i.id AND xmin<>pg_current_xact_id()::xid) OR EXISTS(SELECT 1 FROM capability_invocation_events
   WHERE invocation_id=i.id AND sequence=4) OR EXISTS(SELECT 1 FROM budget_usage_records
    WHERE reservation_id=i.reservation_id AND is_final AND id<>NEW.usage_record_id) THEN
   RAISE EXCEPTION 'one reconciliation of committed unknown' USING ERRCODE='23514', CONSTRAINT='pr301_state';
  END IF;
 ELSE
  saved_receipt:=CASE NEW.event_type WHEN 'REQUESTED' THEN i.request_receipt_id WHEN 'STARTED' THEN i.start_receipt_id ELSE i.finish_receipt_id END;
  stamp:=CASE NEW.event_type WHEN 'REQUESTED' THEN i.created_at WHEN 'STARTED' THEN i.started_at ELSE i.finished_at END;
  IF NOT EXISTS(SELECT 1 FROM capability_invocations WHERE id=i.id AND xmin=pg_current_xact_id()::xid)
   OR ROW(i.row_version,i.status,saved_receipt,stamp) IS DISTINCT FROM
      ROW(NEW.invocation_row_version,NEW.new_status,r.id,NEW.occurred_at)
   OR (NEW.event_type='FINISHED' AND i.usage_record_id IS DISTINCT FROM NEW.usage_record_id) THEN
   RAISE EXCEPTION 'fresh lifecycle projection' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
  END IF;
 END IF;
 IF NEW.usage_record_id IS NOT NULL THEN
  SELECT * INTO u FROM budget_usage_records WHERE id=NEW.usage_record_id AND xmin=pg_current_xact_id()::xid;
  IF u.id IS NULL OR ROW(u.research_task_id,u.reservation_id,u.receipt_id,u.created_at,u.outcome,u.is_final)
   IS DISTINCT FROM ROW(i.research_task_id,i.reservation_id,r.id,NEW.occurred_at,
    CASE WHEN NEW.event_type='RECONCILED' THEN NEW.reconciled_outcome
     WHEN NEW.new_status='UNKNOWN_OUTCOME' THEN 'UNKNOWN' ELSE NEW.new_status END,
    NEW.event_type='RECONCILED' OR NEW.new_status<>'UNKNOWN_OUTCOME') THEN
   RAISE EXCEPTION 'event usage correspondence' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
  END IF;
 END IF;
 RETURN NEW;
END $$;
```

Insert lifecycle rows in this order: task → receipt → reservation/usage →
invocation (except reconciliation) → capability event → refs → task event/link.
The task event's reason equality is checked by the existing deferred receipt
check below, so an event inserted before its task event is supported. No new
trigger or exemption is required for this flush order.

```sql
CREATE OR REPLACE FUNCTION pr303_validate_gateway(p_task uuid) RETURNS void
LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE t research_tasks%ROWTYPE; policy_row agent_tool_policies%ROWTYPE; p_policy uuid;
 i capability_invocations%ROWTYPE; v agent_versions%ROWTYPE; br budget_reservations%ROWTYPE;
 r research_task_command_receipts%ROWTYPE; e capability_invocation_events%ROWTYPE;
 te research_task_events%ROWTYPE; u budget_usage_records%ROWTYPE; ref record; hashes record;
 history record; prev capability_invocation_events%ROWTYPE; parent capability_invocations%ROWTYPE;
 pin text; n integer; calls integer; occupied integer; k text; total numeric; bound numeric;
 b execution_budgets%ROWTYPE; c checkpoint_policies%ROWTYPE; origin timestamptz;
BEGIN
 SELECT * INTO t FROM research_tasks WHERE id=p_task;
 FOR policy_row IN SELECT ap.* FROM agent_tool_policies ap WHERE ap.registration_task_id=p_task
  OR EXISTS(SELECT 1 FROM capability_invocations ci WHERE ci.research_task_id=p_task AND ci.policy_id=ap.id) LOOP
  p_policy:=policy_row.id;
  IF (SELECT count(*) FROM agent_tool_policy_permissions WHERE policy_id=policy_row.id)>256 THEN
   RAISE EXCEPTION 'bounded permission set' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
  END IF;
  PERFORM pr301_validate_input(p_task,NULL,NULL,NULL,NULL,policy_row.registry_artifact_version_id,NULL,policy_row.registry_content_hash,NULL);
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
SELECT pr304_canonical_policy_json(env.value) AS policy_text,
  encode(sha256(convert_to(pr304_canonical_policy_json(env.value), 'UTF8')), 'hex')
    AS policy_digest,
  encode(sha256(convert_to(pr304_canonical_policy_json(cset.value), 'UTF8')), 'hex')
    AS capability_set_digest
INTO hashes FROM envelope env CROSS JOIN capability_set cset;
  IF hashes.policy_digest IS DISTINCT FROM policy_row.content_hash OR hashes.capability_set_digest IS DISTINCT FROM policy_row.capability_set_hash THEN
   RAISE EXCEPTION 'policy envelope contradiction' USING ERRCODE='23514', CONSTRAINT='pr301_provenance';
  END IF;
 END LOOP;
 FOR i IN SELECT * FROM capability_invocations WHERE research_task_id=p_task ORDER BY id LOOP
  SELECT * INTO policy_row FROM agent_tool_policies WHERE id=i.policy_id;
  SELECT * INTO v FROM agent_versions WHERE id=i.agent_version_id;
  SELECT * INTO br FROM budget_reservations WHERE id=i.reservation_id;
  IF ROW(policy_row.project_id,v.project_id,v.actor_id,v.tool_policy_version,v.capability_set_hash,
    policy_row.content_hash,v.configuration_artifact_version_id,v.configuration_content_hash,
    br.research_task_id,br.operation_id,br.budget_id,br.step_id,br.receipt_id,br.created_at)
   IS DISTINCT FROM ROW(t.project_id,t.project_id,i.agent_actor_id,policy_row.version,policy_row.capability_set_hash,
    i.policy_content_hash,i.harness_artifact_version_id,i.harness_content_hash,
    t.id,i.id,t.budget_policy_id,i.step_id,i.request_receipt_id,i.created_at) THEN
   RAISE EXCEPTION 'exact version policy reservation binding' USING ERRCODE='23514', CONSTRAINT='pr301_provenance';
  END IF;
  IF ROW(i.capability_id,i.capability_version,i.operation,i.adapter_id,i.adapter_version,i.parameter_schema_hash)
   IS DISTINCT FROM ROW('fake_capability'::text,'1.0.0'::text,'echo'::text,'fake_in_process'::text,'1.0.0'::text,
    '79fd29b8c5f855b2d2728a13ba245b96d2287fa52fd364646f4a155e40ff4d8f'::text)
   OR i.mode<>'CONTRACT_FAKE' THEN
   RAISE EXCEPTION 'closed fake tuple' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
  END IF;
  FOREACH pin IN ARRAY ARRAY[i.capability_id,i.capability_version,i.operation,i.adapter_id,i.adapter_version,
    i.skill_id,i.skill_version,i.strategy_id,i.strategy_version] LOOP
   IF pin<>btrim(pin) OR lower(pin) IN ('latest','current','main','master') OR pin ~ '[*?\[\]{}()^$|\\]' THEN
    RAISE EXCEPTION 'exact invocation pins' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
   END IF;
  END LOOP;
  IF NOT EXISTS(SELECT 1 FROM agent_tool_policy_permissions q WHERE q.policy_id=policy_row.id AND q.effect='ALLOW'
   AND ROW(q.capability_id,q.capability_version,q.operation,q.adapter_id,q.adapter_version,q.parameter_schema_hash)
    =ROW(i.capability_id,i.capability_version,i.operation,i.adapter_id,i.adapter_version,i.parameter_schema_hash))
   OR EXISTS(SELECT 1 FROM agent_tool_policy_permissions q WHERE q.policy_id=policy_row.id AND q.effect='DENY'
   AND ROW(q.capability_id,q.capability_version,q.operation,q.adapter_id,q.adapter_version,q.parameter_schema_hash)
    =ROW(i.capability_id,i.capability_version,i.operation,i.adapter_id,i.adapter_version,i.parameter_schema_hash)) THEN
   RAISE EXCEPTION 'exact allow absent or deny wins' USING ERRCODE='23514', CONSTRAINT='pr301_scope';
  END IF;
  PERFORM pr301_validate_input(t.id,NULL,NULL,NULL,NULL,i.harness_artifact_version_id,NULL,i.harness_content_hash,NULL);
  PERFORM pr301_validate_input(t.id,NULL,NULL,NULL,NULL,i.parameters_artifact_version_id,NULL,i.parameters_content_hash,NULL);
  IF ROW(br.agent_steps,br.llm_calls,br.search_calls,br.code_iterations,br.experiment_runs,br.tree_nodes,
    br.gpu_hours,br.token_cost,br.wall_time_seconds)
   IS DISTINCT FROM ROW(0::bigint,1::bigint,0::bigint,0::bigint,0::bigint,0::bigint,0.000000::numeric,0.125000::numeric,60)
   OR (SELECT pricing_basis FROM execution_budgets WHERE id=br.budget_id) IS DISTINCT FROM 'fake-usd-v1'
   OR br.deadline>br.created_at+interval '60 seconds' OR br.deadline<br.created_at+interval '1 second' THEN
   RAISE EXCEPTION 'closed fake reservation vector' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
  END IF;
  IF i.parameters_byte_size NOT BETWEEN 1 AND 65536 OR i.parameters_byte_size IS DISTINCT FROM
    (SELECT byte_size FROM artifact_versions WHERE id=i.parameters_artifact_version_id) THEN
   RAISE EXCEPTION 'parameter byte size' USING ERRCODE='23514', CONSTRAINT='pr301_provenance';
  END IF;
  IF i.trace_artifact_version_id IS NOT NULL THEN
   PERFORM pr301_validate_input(t.id,NULL,NULL,NULL,NULL,i.trace_artifact_version_id,NULL,i.trace_content_hash,NULL);
  END IF;
  IF i.retry_parent_id IS NOT NULL THEN
   SELECT * INTO parent FROM capability_invocations WHERE id=i.retry_parent_id AND research_task_id=t.id;
   IF parent.id IS NULL OR parent.id=i.id OR parent.status NOT IN ('FAILED','UNKNOWN_OUTCOME')
    OR NOT EXISTS(SELECT 1 FROM budget_usage_records bu JOIN research_task_command_receipts ur ON ur.id=bu.receipt_id
      JOIN research_task_command_receipts qr ON qr.id=i.request_receipt_id
      WHERE bu.reservation_id=parent.reservation_id AND bu.is_final AND ur.resulting_row_version<qr.resulting_row_version) THEN
    RAISE EXCEPTION 'retry requires prior final failure observation' USING ERRCODE='23514', CONSTRAINT='pr301_state';
   END IF;
  END IF;
  IF (SELECT count(*) FROM capability_invocation_refs WHERE invocation_id=i.id)>256 THEN
   RAISE EXCEPTION 'bounded invocation reference set' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
  END IF;
  FOR ref IN SELECT * FROM capability_invocation_refs WHERE invocation_id=i.id LOOP
   PERFORM pr301_validate_input(t.id,ref.research_question_version_id,ref.hypothesis_version_id,ref.claim_version_id,
    ref.source_version_id,ref.artifact_version_id,ref.manuscript_version_id,ref.content_hash,ref.hash_scheme);
   IF ref.direction='INPUT' AND ref.receipt_id IS DISTINCT FROM i.request_receipt_id
    OR ref.direction='OUTPUT' AND (ref.artifact_version_id IS NULL OR NOT EXISTS(
      SELECT 1 FROM capability_invocation_events ce WHERE ce.invocation_id=i.id AND ce.receipt_id=ref.receipt_id
       AND ((ce.event_type='FINISHED' AND ce.new_status='SUCCEEDED')
        OR (ce.event_type='RECONCILED' AND ce.reconciled_outcome='SUCCEEDED')))) THEN
    RAISE EXCEPTION 'reference lifecycle attribution' USING ERRCODE='23514', CONSTRAINT='pr301_state';
   END IF;
  END LOOP;
  n:=0; prev:=NULL;
  FOR e IN SELECT * FROM capability_invocation_events WHERE invocation_id=i.id ORDER BY sequence LOOP
   n:=n+1;
   SELECT * INTO r FROM research_task_command_receipts WHERE id=e.receipt_id;
   SELECT * INTO te FROM research_task_events WHERE research_task_id=t.id AND task_row_version=r.resulting_row_version;
   IF e.sequence<>n OR (n>1 AND (e.prior_status IS DISTINCT FROM prev.new_status OR e.occurred_at<prev.occurred_at))
    OR ROW(e.actor_id,e.occurred_at,e.reason,r.result_capability_event_id,r.result_capability_invocation_id,
       r.result_tool_policy_id,r.resulting_invocation_revision,r.research_task_id,r.project_id)
     IS DISTINCT FROM ROW(r.actor_id,r.completed_at,te.reason,e.id,i.id,i.policy_id,e.invocation_row_version,t.id,t.project_id)
    OR r.command_name IS DISTINCT FROM CASE e.event_type WHEN 'REQUESTED' THEN 'request_capability_invocation'
     WHEN 'STARTED' THEN 'start_capability_invocation' ELSE 'finish_capability_invocation' END THEN
    RAISE EXCEPTION 'gapless attributable event history' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
   END IF;
   IF e.sequence<=i.row_version AND (
    (e.sequence=1 AND ROW(e.receipt_id,e.occurred_at,e.actor_id) IS DISTINCT FROM ROW(i.request_receipt_id,i.created_at,i.requested_by))
    OR (e.event_type='STARTED' AND ROW(e.receipt_id,e.occurred_at) IS DISTINCT FROM ROW(i.start_receipt_id,i.started_at))
    OR (e.event_type='FINISHED' AND ROW(e.receipt_id,e.occurred_at,e.usage_record_id) IS DISTINCT FROM
      ROW(i.finish_receipt_id,i.finished_at,i.usage_record_id))
    OR (e.sequence=i.row_version AND ROW(e.new_status,e.invocation_row_version) IS DISTINCT FROM ROW(i.status,i.row_version))) THEN
    RAISE EXCEPTION 'saved projection contradiction' USING ERRCODE='23514', CONSTRAINT='pr301_provenance';
   END IF;
   IF e.event_type='RECONCILED' AND (i.status<>'UNKNOWN_OUTCOME' OR i.row_version<>3) THEN
    RAISE EXCEPTION 'reconciled unknown only' USING ERRCODE='23514', CONSTRAINT='pr301_state';
   END IF;
   IF e.usage_record_id IS NOT NULL THEN
    SELECT * INTO u FROM budget_usage_records WHERE id=e.usage_record_id;
    IF u.id IS NULL OR ROW(u.research_task_id,u.reservation_id,u.receipt_id,u.created_at,u.is_final,u.outcome)
     IS DISTINCT FROM ROW(t.id,i.reservation_id,r.id,e.occurred_at,
      e.event_type='RECONCILED' OR e.new_status<>'UNKNOWN_OUTCOME',
      CASE WHEN e.event_type='RECONCILED' THEN e.reconciled_outcome
       WHEN e.new_status='UNKNOWN_OUTCOME' THEN 'UNKNOWN' ELSE e.new_status END) THEN
     RAISE EXCEPTION 'one exact charge per observation' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
    END IF;
    IF u.outcome<>'UNKNOWN' AND (u.wall_time_seconds<>0 OR u.gpu_hours<>0 OR u.token_cost<>0) THEN
     RAISE EXCEPTION 'fake variable consumption is zero' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
    END IF;
   END IF;
   prev:=e;
  END LOOP;
  IF n<>i.row_version+CASE WHEN EXISTS(SELECT 1 FROM capability_invocation_events
    WHERE invocation_id=i.id AND sequence=4 AND event_type='RECONCILED') THEN 1 ELSE 0 END
   OR (SELECT count(*) FROM budget_usage_records WHERE reservation_id=i.reservation_id)<>
      (SELECT count(*) FROM capability_invocation_events WHERE invocation_id=i.id AND usage_record_id IS NOT NULL) THEN
   RAISE EXCEPTION 'missing event or extra charge' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
  END IF;
 END LOOP;
 -- Historical counts use admitting receipt revisions, never today's totals.
 FOR history IN SELECT cr.*,ci.id AS invocation_id,ci.policy_id,ce.event_type,ce.reservation_id
  FROM research_task_command_receipts cr JOIN capability_invocation_events ce ON ce.receipt_id=cr.id
  JOIN capability_invocations ci ON ci.id=ce.invocation_id
  WHERE cr.research_task_id=t.id AND ce.event_type IN ('REQUESTED','STARTED') ORDER BY cr.resulting_row_version LOOP
  SELECT * INTO policy_row FROM agent_tool_policies WHERE id=history.policy_id;
  SELECT * INTO i FROM capability_invocations WHERE id=history.invocation_id;
  SELECT count(*) INTO calls FROM capability_invocations ci JOIN research_task_command_receipts qr ON qr.id=ci.request_receipt_id
   WHERE ci.research_task_id=t.id AND qr.resulting_row_version<=history.resulting_row_version;
  SELECT count(*) INTO occupied FROM capability_invocations ci JOIN research_task_command_receipts qr ON qr.id=ci.request_receipt_id
   WHERE ci.research_task_id=t.id AND qr.resulting_row_version<=history.resulting_row_version AND NOT EXISTS(
    SELECT 1 FROM budget_usage_records bu JOIN research_task_command_receipts ur ON ur.id=bu.receipt_id
    WHERE bu.reservation_id=ci.reservation_id AND bu.is_final AND ur.resulting_row_version<=history.resulting_row_version);
  IF calls>policy_row.max_tool_calls OR occupied>policy_row.max_parallel_invocations THEN
   RAISE EXCEPTION 'task-wide tool admission caps' USING ERRCODE='23514', CONSTRAINT='pr301_state';
  END IF;
  IF history.event_type='STARTED' THEN
   SELECT * INTO br FROM budget_reservations WHERE id=i.reservation_id;
   SELECT * INTO b FROM execution_budgets WHERE id=br.budget_id;
   SELECT min(created_at) INTO origin FROM budget_reservations WHERE research_task_id=t.id;
   SELECT * INTO c FROM checkpoint_policies WHERE id=t.checkpoint_policy_id;
   IF history.completed_at>=br.deadline OR history.completed_at>=origin+b.max_wall_time_seconds*interval '1 second'
    OR t.autonomy_level IN ('A2','A3') OR EXISTS(SELECT 1 FROM budget_usage_records bu
     JOIN research_task_command_receipts ur ON ur.id=bu.receipt_id WHERE bu.reservation_id=br.id
      AND ur.resulting_row_version<=history.resulting_row_version)
    OR EXISTS(SELECT 1 FROM research_task_events se WHERE se.research_task_id=t.id AND se.task_row_version<history.resulting_row_version
     AND (se.stop_human OR se.stop_policy OR se.stop_budget OR se.stop_repeated_failure OR se.stop_no_improvement)
     AND NOT (se.event_type='CAPABILITY_REQUESTED' AND se.result_capability_invocation_id=i.id
      AND se.stop_budget AND NOT (se.stop_human OR se.stop_policy OR se.stop_repeated_failure OR se.stop_no_improvement))) THEN
    RAISE EXCEPTION 'start deadline or sticky stop' USING ERRCODE='23514', CONSTRAINT='pr301_state';
   END IF;
   IF EXISTS(SELECT 1 FROM unnest(c.required_types || ARRAY['plan_review']::text[]) gate
    WHERE NOT EXISTS(SELECT 1 FROM human_checkpoints h JOIN research_task_command_receipts hr ON hr.id=h.response_receipt_id
     WHERE h.id=(SELECT hh.id FROM human_checkpoints hh JOIN research_task_command_receipts qr ON qr.id=hh.receipt_id
      WHERE hh.research_task_id=t.id AND hh.step_id IS NOT DISTINCT FROM i.step_id AND hh.checkpoint_type=gate
       AND qr.resulting_row_version<history.resulting_row_version ORDER BY hh.created_at DESC,hh.id DESC LIMIT 1)
      AND h.status='APPROVED' AND hr.resulting_row_version<history.resulting_row_version)) THEN
    RAISE EXCEPTION 'latest start checkpoint required' USING ERRCODE='23514', CONSTRAINT='pr301_state';
   END IF;
   FOREACH k IN ARRAY ARRAY['agent_steps','llm_calls','search_calls','code_iterations','experiment_runs','tree_nodes','gpu_hours','token_cost'] LOOP
    SELECT coalesce(sum(CASE WHEN bu.id IS NULL THEN (to_jsonb(res)->>k)::numeric ELSE (to_jsonb(bu)->>k)::numeric END),0) INTO total
     FROM budget_reservations res JOIN research_task_command_receipts qr ON qr.id=res.receipt_id
     LEFT JOIN (budget_usage_records bu JOIN research_task_command_receipts ur ON ur.id=bu.receipt_id
      AND ur.resulting_row_version<=history.resulting_row_version) ON bu.reservation_id=res.id AND bu.is_final
     WHERE res.research_task_id=t.id AND qr.resulting_row_version<=history.resulting_row_version;
    bound:=(to_jsonb(b)->>('max_'||k))::numeric;
    IF total>bound THEN
     RAISE EXCEPTION 'start capacity exceeded' USING ERRCODE='23514', CONSTRAINT='pr301_state';
    END IF;
   END LOOP;
  END IF;
  -- Current persisted availability/entitlement is only rechecked for fresh admission;
  -- later disable/revocation cannot invalidate completed historical admissions.
  IF EXISTS(SELECT 1 FROM research_task_command_receipts WHERE id=history.id AND xmin=pg_current_xact_id()::xid) THEN
   IF t.status='CANCELLED' OR NOT EXISTS(SELECT 1 FROM agent_availability av JOIN actors a ON a.id=i.agent_actor_id
     JOIN project_memberships m ON m.actor_id=a.id WHERE av.agent_version_id=i.agent_version_id AND av.status='ACTIVE'
      AND a.actor_type='AGENT' AND a.retired_at IS NULL AND m.project_id=t.project_id AND m.status='ACTIVE')
    OR NOT EXISTS(SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id
      JOIN actor_subject_bindings ab ON ab.actor_id=a.id WHERE a.id=history.actor_id AND a.retired_at IS NULL
      AND m.project_id=t.project_id AND m.status='ACTIVE' AND ab.status='ACTIVE'
      AND ab.bound_at<=clock_timestamp() AND (ab.revoked_at IS NULL OR clock_timestamp()<ab.revoked_at)) THEN
    RAISE EXCEPTION 'current admission entitlement' USING ERRCODE='23514', CONSTRAINT='pr301_scope';
   END IF;
  END IF;
 END LOOP;
END $$;
```

### 4.5 Complete forward replacements and retained trigger identities

Names in the §4.3 right column sometimes name triggers, not functions.
`pr301_task_final` calls `pr301_graph_final_guard()`;
`pr301_receipt_complete_commit` calls `pr301_receipt_complete()`;
`pr304_reservation_guard` and `pr304_usage_guard` both call `pr304_child_guard()`.
There are no delivered functions with those four trigger names. The bodies below
replace their actual callees in place, retaining trigger OIDs and attachment
semantics. No DROP/CREATE trigger or redundant wrapper function is needed.

Every original conditional branch is retained. The following preservation map
uses delivered migration lines, not shifting lines in this document. Changed
command-set branches include their old cases and add only gateway owners.

| Function | Delivered complete body | Preserved branches and exact limited change |
| --- | --- | --- |
| pr301_task_guard | 0078_task_safety_policies.py:322–352 (supersedes 0077:348–372) | DELETE 324; initial state/bundle 325–329; one-write/material 331–334; revision 335; bound bundle 336–338; terminal material 339–340; transitions 341–343; finish 344–345; seal 346–349. All unchanged: status-preserving gateway bumps already fit. Deferred receipt adds command attribution. |
| pr301_receipt_insert_guard | 0077_research_task_graph.py:507–514 | Fresh task/project/revision 509–511 unchanged; new receipt shape is also checked by §3 CHECK. No command filter existed to remove. |
| pr304_child_guard | 0078_task_safety_policies.py:354–375 | Mutation denial 357; fresh owners 358–361; table owner cases 362–364 extended only for reservation/usage; observed clock 365–367; scope owner 368–371; cancelled 372–373 extended only for finish. |
| pr304_validate_safety | 0078_task_safety_policies.py:467–579 | Policy validation/orphans 474–485; unbound/bundle/autonomy 486–495; ordered history 496–499; admission/deadline/origin 500–506; occupancy/depth 507–517; evaluator 518–519; checkpoints 520–526; A2/A3 denial 527–529; post-final 535–537; measured vector 538–542; score 543–546; streak reconstruction 547–558; cap and stop reconstruction 559–576; sticky accumulation 577. Only 559's command set gains request/finish. Reservations/usages are already discovered by receipt ownership at 500/532. Start admission is checked by pr303_validate_gateway without adding a reservation or changing sticky history. |
| pr301_graph_final_guard | 0078_task_safety_policies.py:584–621 (extends 0077:576–612) | Size limits 589–592; states 593–596; task history 597–602; step history 603–610; sealed inputs 611–618; safety call 619 all unchanged; one gateway call appended before return. |
| pr301_receipt_complete | 0078_task_safety_policies.py:622–723 (extends 0077:616–662) | Planning/safety mapping 629–632 extended; attribution 633–635; create/seal time 636–645; dependency count 646–650; history 651–652; step attribution/count 653–664; cancel time 665–666; policy/scope counts 668–676; reservation/usage counts 678–680 extended; checkpoint count 682; seal/create 685–688; owner 689–695; explicit stops 696–697; reasons/binding 698–702; response/expiry 703–711; no graph effects/time/terminal rules 712–721 extended only for gateway bookkeeping. New gateway cardinalities follow all preserved branches. |

Exact changes within the delivered branches called out above, all in
`migrations/versions/0078_task_safety_policies.py`:

| Function / delivered line range | Before | After in the complete replacement below (document line range) |
| --- | --- | --- |
| pr304_child_guard:363–363 | Reservation owners `ARRAY['reserve_task_budget']`; usage owners `ARRAY['settle_task_budget']`. | Reservation owners gain `request_capability_invocation`; usage owners gain `finish_capability_invocation`. §4.5 lines 1248–1248. Lines 362 and 364 are unchanged. |
| pr304_child_guard:372–372 | Cancelled-task predicate `r.command_name<>'settle_task_budget'`. | Predicate `r.command_name NOT IN ('settle_task_budget','finish_capability_invocation')`. §4.5 lines 1257–1257. Line 373 remains unchanged. |
| pr301_receipt_complete:622–622 | Default invoker rights/search path. | Explicit `SECURITY INVOKER` and fixed search path. §4.5 lines 1424–1425; the same hardening applies to all replacement definitions. |
| pr301_receipt_complete:623–624 | Receipt/event records, mapped text and expected/actual counters. | Retain those locals; add `gateway boolean`, `ci capability_invocations%ROWTYPE` and `ce capability_invocation_events%ROWTYPE`. §4.5 lines 1426–1427. |
| pr301_receipt_complete:629–632 | Mapped CASE contains six planning and six safety commands. | Preserve all mappings; add `register_agent_tool_policy → TOOL_POLICY_REGISTERED`, `request_capability_invocation → CAPABILITY_REQUESTED`, `start_capability_invocation → CAPABILITY_STARTED`, `finish_capability_invocation → CAPABILITY_FINISHED`. §4.5 lines 1432–1439. |
| pr301_receipt_complete:678–678 | Reservation count is one only for `r.command_name='reserve_task_budget'`. | Predicate becomes `r.command_name IN ('reserve_task_budget','request_capability_invocation')`. §4.5 lines 1485–1485. |
| pr301_receipt_complete:680–680 | Usage count is one only for `r.command_name='settle_task_budget'`. | Predicate becomes `r.command_name IN ('settle_task_budget','finish_capability_invocation')`. §4.5 lines 1487–1487. |
| pr301_receipt_complete:712–718 | Unrelated-safety-effect check covers the six delivered safety commands. | Extend its command set with `register_agent_tool_policy`, `request_capability_invocation`, `start_capability_invocation` and `finish_capability_invocation`. The time and no-graph-effect predicates remain unchanged. §4.5 lines 1519–1525. |
| pr301_receipt_complete:719–721 | Cancelled-task exceptions `('settle_task_budget','evaluate_task_termination')`. | Append `finish_capability_invocation`; rejection, diagnostic and closing branch remain unchanged. §4.5 lines 1526–1528. |
| pr301_receipt_complete:721–722 (insertion between these lines) | Closing safety branch is followed immediately by `RETURN NULL`. | Insert the entire gateway block from `gateway:=r.command_name IN (...)` through its closing `END IF` before `RETURN NULL`: exact result pointers/cardinalities, old-command exclusions, current entitlement, task/seal/policy restrictions, event counts, registration/invocation/ref/accounting attribution and fresh-write/reconciliation checks. §4.5 lines 1530–1616. |

All file names above are under `migrations/versions/`. All replacement definitions
explicitly use invoker rights and the fixed search path, including unchanged
bodies reproduced here for a complete reviewable replacement.

```sql
CREATE OR REPLACE FUNCTION pr301_task_guard() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, public, pg_temp AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'immutable task' USING ERRCODE='23514',CONSTRAINT='pr301_immutable'; END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.status<>'CREATED' OR NEW.row_version<>1 OR NEW.plan_sealed_at IS NOT NULL OR
   NEW.started_at IS NOT NULL OR NEW.finished_at IS NOT NULL OR NEW.current_step_id IS NOT NULL OR
   num_nonnulls(NEW.budget_policy_id,NEW.termination_policy_id,NEW.checkpoint_policy_id)<>0
  THEN RAISE EXCEPTION 'invalid initial task' USING ERRCODE='23514',CONSTRAINT='pr301_state'; END IF;
 ELSE
  IF EXISTS(SELECT 1 FROM research_tasks WHERE id=OLD.id AND xmin=pg_current_xact_id()::xid)
   OR (to_jsonb(NEW)-ARRAY['row_version','status','finished_at','plan_sealed_at','budget_policy_id','termination_policy_id','checkpoint_policy_id'])
     IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['row_version','status','finished_at','plan_sealed_at','budget_policy_id','termination_policy_id','checkpoint_policy_id'])
  THEN RAISE EXCEPTION 'immutable task material' USING ERRCODE='23514',CONSTRAINT='pr301_immutable'; END IF;
  IF NEW.row_version<>OLD.row_version+1 THEN RAISE EXCEPTION 'invalid revision' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;
  IF OLD.budget_policy_id IS NOT NULL AND ROW(NEW.budget_policy_id,NEW.termination_policy_id,NEW.checkpoint_policy_id)
   IS DISTINCT FROM ROW(OLD.budget_policy_id,OLD.termination_policy_id,OLD.checkpoint_policy_id)
  THEN RAISE EXCEPTION 'immutable policy binding' USING ERRCODE='23514',CONSTRAINT='pr301_immutable'; END IF;
  IF OLD.status='CANCELLED' AND to_jsonb(NEW)-'row_version' IS DISTINCT FROM to_jsonb(OLD)-'row_version'
  THEN RAISE EXCEPTION 'terminal material' USING ERRCODE='23514',CONSTRAINT='pr301_immutable'; END IF;
  IF NOT ((NEW.status=OLD.status) OR (OLD.status='CREATED' AND NEW.status='PLANNING') OR
   (OLD.status IN ('CREATED','PLANNING') AND NEW.status='CANCELLED'))
  THEN RAISE EXCEPTION 'invalid state' USING ERRCODE='23514',CONSTRAINT='pr301_state'; END IF;
  IF NEW.finished_at IS DISTINCT FROM OLD.finished_at AND NOT (OLD.status<>'CANCELLED' AND NEW.status='CANCELLED')
  THEN RAISE EXCEPTION 'immutable finish' USING ERRCODE='23514',CONSTRAINT='pr301_immutable'; END IF;
  IF OLD.plan_sealed_at IS NOT NULL AND NEW.plan_sealed_at IS DISTINCT FROM OLD.plan_sealed_at
  THEN RAISE EXCEPTION 'immutable seal' USING ERRCODE='23514',CONSTRAINT='pr301_immutable'; END IF;
  IF OLD.plan_sealed_at IS NULL AND NEW.plan_sealed_at IS NOT NULL AND NOT (OLD.status='PLANNING' AND NEW.status='PLANNING')
  THEN RAISE EXCEPTION 'invalid seal' USING ERRCODE='23514',CONSTRAINT='pr301_state'; END IF;
 END IF;
 RETURN NEW;
END $$;
```

```sql
CREATE OR REPLACE FUNCTION pr301_receipt_insert_guard() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, public, pg_temp AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM research_tasks WHERE id=NEW.research_task_id AND project_id=NEW.project_id
  AND row_version=NEW.resulting_row_version AND xmin=pg_current_xact_id()::xid)
 THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_immutable'; END IF;
 RETURN NEW;
END $$;
```

```sql
CREATE OR REPLACE FUNCTION pr304_child_guard() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE r research_task_command_receipts%ROWTYPE; t research_tasks%ROWTYPE; now_at timestamptz := clock_timestamp(); allowed text[];
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'immutable safety history' USING ERRCODE='23514',CONSTRAINT='pr301_immutable'; END IF;
 SELECT * INTO t FROM research_tasks WHERE id=NEW.research_task_id AND xmin=pg_current_xact_id()::xid;
 SELECT * INTO r FROM research_task_command_receipts WHERE id=NEW.receipt_id AND research_task_id=NEW.research_task_id AND xmin=pg_current_xact_id()::xid;
 IF t.id IS NULL OR r.id IS NULL OR r.resulting_row_version<>t.row_version
 THEN RAISE EXCEPTION 'fresh owners required' USING ERRCODE='23514',CONSTRAINT='pr301_immutable'; END IF;
 allowed:=CASE TG_TABLE_NAME WHEN 'execution_budgets' THEN ARRAY['bind_task_policies','request_human_checkpoint']
 WHEN 'budget_reservations' THEN ARRAY['reserve_task_budget','request_capability_invocation'] WHEN 'budget_usage_records' THEN ARRAY['settle_task_budget','finish_capability_invocation']
 ELSE ARRAY['bind_task_policies'] END;
 IF NOT r.command_name=ANY(allowed) OR NEW.created_at IS DISTINCT FROM r.completed_at OR
   NEW.created_at<transaction_timestamp() OR NEW.created_at>now_at
 THEN RAISE EXCEPTION 'invalid safety effect' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;
 IF TG_TABLE_NAME IN ('checkpoint_policy_dataset_scopes','checkpoint_policy_metric_scopes') THEN
  IF NOT EXISTS(SELECT 1 FROM checkpoint_policies WHERE id=NEW.checkpoint_policy_id AND research_task_id=t.id AND receipt_id=r.id AND xmin=pg_current_xact_id()::xid)
  THEN RAISE EXCEPTION 'fresh scope owner required' USING ERRCODE='23514',CONSTRAINT='pr301_immutable'; END IF;
 END IF;
 IF t.status='CANCELLED' AND r.command_name NOT IN ('settle_task_budget','finish_capability_invocation')
 THEN RAISE EXCEPTION 'cancelled task' USING ERRCODE='23514',CONSTRAINT='pr301_state'; END IF;
 RETURN NEW;
END $$;
```

```sql
CREATE OR REPLACE FUNCTION pr304_validate_safety(p_task uuid) RETURNS void LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE t research_tasks%ROWTYPE; b execution_budgets%ROWTYPE; c checkpoint_policies%ROWTYPE; term termination_policies%ROWTYPE;
 r record; u record; e record; pol record; k text; total numeric; bound numeric; measured numeric;
 origin timestamptz; n integer; depth integer; occupancy integer; stopped boolean:=false; budget_stop boolean; failure_stop boolean; progress_stop boolean;
 history record; fs integer; ns integer; best numeric; val numeric; current_outcome text; current_score numeric;
BEGIN
 SELECT * INTO t FROM research_tasks WHERE id=p_task;
 FOR pol IN SELECT id FROM execution_budgets WHERE research_task_id=p_task LOOP PERFORM pr304_validate_policy(p_task,pol.id,'BUDGET'); END LOOP;
 FOR pol IN SELECT id FROM termination_policies WHERE research_task_id=p_task LOOP
  IF pol.id IS DISTINCT FROM t.termination_policy_id THEN RAISE EXCEPTION 'orphan termination policy' USING ERRCODE='23514',CONSTRAINT='pr301_state'; END IF;
  PERFORM pr304_validate_policy(p_task,pol.id,'TERMINATION');
 END LOOP;
 FOR pol IN SELECT id FROM checkpoint_policies WHERE research_task_id=p_task LOOP
  IF pol.id IS DISTINCT FROM t.checkpoint_policy_id THEN RAISE EXCEPTION 'orphan checkpoint policy' USING ERRCODE='23514',CONSTRAINT='pr301_state'; END IF;
  PERFORM pr304_validate_policy(p_task,pol.id,'CHECKPOINT');
 END LOOP;
 IF EXISTS(SELECT 1 FROM execution_budgets x WHERE research_task_id=p_task AND x.id IS DISTINCT FROM t.budget_policy_id
   AND NOT EXISTS(SELECT 1 FROM human_checkpoints h WHERE h.proposed_budget_id=x.id AND h.receipt_id=x.receipt_id AND h.research_task_id=p_task))
 THEN RAISE EXCEPTION 'orphan extension budget' USING ERRCODE='23514',CONSTRAINT='pr301_state'; END IF;
 IF t.budget_policy_id IS NULL THEN
  IF EXISTS(SELECT 1 FROM budget_reservations WHERE research_task_id=p_task) OR EXISTS(SELECT 1 FROM human_checkpoints WHERE research_task_id=p_task)
  THEN RAISE EXCEPTION 'complete bundle required' USING ERRCODE='23514',CONSTRAINT='pr301_state'; END IF;
  RETURN;
 END IF;
 SELECT * INTO b FROM execution_budgets WHERE id=t.budget_policy_id AND research_task_id=p_task;
 SELECT * INTO c FROM checkpoint_policies WHERE id=t.checkpoint_policy_id AND research_task_id=p_task;
 SELECT * INTO term FROM termination_policies WHERE id=t.termination_policy_id AND research_task_id=p_task;
 IF b.id IS NULL OR c.id IS NULL OR term.id IS NULL THEN RAISE EXCEPTION 'same-task bundle required' USING ERRCODE='23503'; END IF;
 IF t.autonomy_level>c.maximum_autonomy THEN RAISE EXCEPTION 'autonomy ceiling' USING ERRCODE='23514',CONSTRAINT='pr301_state'; END IF;
 FOR history IN SELECT cr.*,te.stop_human,te.stop_policy,te.stop_budget,te.stop_repeated_failure,te.stop_no_improvement,te.stop_success
  FROM research_task_command_receipts cr JOIN research_task_events te ON te.research_task_id=cr.research_task_id AND te.task_row_version=cr.resulting_row_version
  WHERE cr.research_task_id=p_task ORDER BY cr.resulting_row_version LOOP
  budget_stop:=false; failure_stop:=false; progress_stop:=false;
  SELECT * INTO r FROM budget_reservations WHERE receipt_id=history.id;
  IF r.id IS NOT NULL THEN
   IF stopped OR r.budget_id<>b.id OR r.deadline>r.created_at+r.wall_time_seconds*interval '1 second' OR r.deadline<=r.created_at
   THEN RAISE EXCEPTION 'admission blocked' USING ERRCODE='23514',CONSTRAINT='pr301_state'; END IF;
   IF origin IS NULL THEN origin:=r.created_at; END IF;
   IF r.created_at>=origin+b.max_wall_time_seconds*interval '1 second' OR r.deadline>origin+b.max_wall_time_seconds*interval '1 second'
   THEN RAISE EXCEPTION 'wall budget exceeded' USING ERRCODE='23514',CONSTRAINT='pr301_state'; END IF;
   SELECT count(*) INTO occupancy FROM budget_reservations br JOIN research_task_command_receipts cr ON cr.id=br.receipt_id
    WHERE br.research_task_id=p_task AND cr.resulting_row_version<=history.resulting_row_version AND NOT EXISTS(
     SELECT 1 FROM budget_usage_records bu JOIN research_task_command_receipts ur ON ur.id=bu.receipt_id WHERE bu.reservation_id=br.id AND bu.is_final AND ur.resulting_row_version<history.resulting_row_version);
   depth:=0;
   IF r.step_id IS NOT NULL THEN
    WITH RECURSIVE ancestors AS (SELECT id,parent_step_id,0 AS d FROM research_task_steps WHERE id=r.step_id AND research_task_id=p_task
      UNION ALL SELECT s.id,s.parent_step_id,a.d+1 FROM research_task_steps s JOIN ancestors a ON s.id=a.parent_step_id WHERE s.research_task_id=p_task)
     SELECT max(d) INTO depth FROM ancestors;
   END IF;
   IF depth IS NULL OR r.observed_depth<>depth OR depth>b.max_tree_depth OR r.observed_parallel_branches<>occupancy OR occupancy>b.max_parallel_branches
   THEN RAISE EXCEPTION 'invalid gauges' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;
   IF (r.code_iterations>0 OR r.experiment_runs>0 OR r.tree_nodes>0) AND term.score_metric_version_id IS NULL
   THEN RAISE EXCEPTION 'comparable evaluator required' USING ERRCODE='23514',CONSTRAINT='pr301_state'; END IF;
   IF EXISTS(SELECT 1 FROM unnest(c.required_types || ARRAY['plan_review']::text[] || CASE WHEN r.code_iterations>0 THEN ARRAY['code_risk'] ELSE ARRAY[]::text[] END || CASE WHEN r.experiment_runs>0 THEN ARRAY['experiment_approval'] ELSE ARRAY[]::text[] END) gate
    WHERE NOT EXISTS(SELECT 1 FROM human_checkpoints h JOIN research_task_command_receipts hr ON hr.id=h.response_receipt_id
     WHERE h.id=(SELECT hh.id FROM human_checkpoints hh JOIN research_task_command_receipts qr ON qr.id=hh.receipt_id
       WHERE hh.research_task_id=p_task AND hh.step_id IS NOT DISTINCT FROM r.step_id AND hh.checkpoint_type=gate AND qr.resulting_row_version<history.resulting_row_version
       ORDER BY hh.created_at DESC,hh.id DESC LIMIT 1)
     AND h.status='APPROVED' AND hr.resulting_row_version<history.resulting_row_version))
   THEN RAISE EXCEPTION 'checkpoint required' USING ERRCODE='23514',CONSTRAINT='pr301_state'; END IF;
   IF t.autonomy_level IN ('A2','A3') THEN
    RAISE EXCEPTION 'scientific execution prerequisites unavailable in fake slice' USING ERRCODE='23514',CONSTRAINT='pr301_state';
   END IF;
  END IF;
  SELECT bu.*,br.step_id,br.agent_steps AS reserved_agent_steps,br.llm_calls AS reserved_llm_calls,br.search_calls AS reserved_search_calls,
   br.code_iterations AS reserved_code_iterations,br.experiment_runs AS reserved_experiment_runs,br.tree_nodes AS reserved_tree_nodes,
   to_jsonb(br) AS reserved FROM budget_usage_records bu JOIN budget_reservations br ON br.id=bu.reservation_id WHERE bu.receipt_id=history.id INTO u;
  IF u.id IS NOT NULL THEN
   IF EXISTS(SELECT 1 FROM budget_usage_records bu JOIN research_task_command_receipts cr ON cr.id=bu.receipt_id
     WHERE bu.reservation_id=u.reservation_id AND bu.is_final AND cr.resulting_row_version<history.resulting_row_version)
   THEN RAISE EXCEPTION 'post-final observation' USING ERRCODE='23514',CONSTRAINT='pr301_state'; END IF;
   FOREACH k IN ARRAY ARRAY['wall_time_seconds','agent_steps','llm_calls','search_calls','code_iterations','experiment_runs','tree_nodes','gpu_hours','token_cost'] LOOP
    measured:=(to_jsonb(u)->>k)::numeric; bound:=(u.reserved->>k)::numeric;
    IF measured>bound OR (k IN ('agent_steps','llm_calls','search_calls','code_iterations','experiment_runs','tree_nodes') AND measured<>bound) OR (u.outcome='UNKNOWN' AND measured<>bound)
    THEN RAISE EXCEPTION 'invalid measured vector' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;
   END LOOP;
   IF u.outcome='SUCCEEDED' AND u.score IS NULL AND ((u.reserved->>'code_iterations')::numeric>0 OR (u.reserved->>'experiment_runs')::numeric>0 OR (u.reserved->>'tree_nodes')::numeric>0)
   THEN RAISE EXCEPTION 'comparable iteration score required' USING ERRCODE='23514',CONSTRAINT='pr301_state'; END IF;
   IF u.score IS NOT NULL AND (term.evaluator_version IS NULL OR u.evaluator_version<>term.evaluator_version OR u.outcome<>'SUCCEEDED')
   THEN RAISE EXCEPTION 'incomparable score' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;
   fs:=0; ns:=0; best:=NULL;
   FOR pol IN SELECT bu.* FROM budget_usage_records bu JOIN budget_reservations br ON br.id=bu.reservation_id JOIN research_task_command_receipts cr ON cr.id=bu.receipt_id
    WHERE bu.research_task_id=p_task AND br.step_id IS NOT DISTINCT FROM u.step_id AND bu.is_final AND cr.resulting_row_version<=history.resulting_row_version ORDER BY cr.resulting_row_version LOOP
    IF pol.outcome='FAILED' THEN fs:=fs+1; ELSIF pol.outcome='SUCCEEDED' THEN
     fs:=0;
     IF pol.score IS NOT NULL THEN
      IF best IS NULL OR (term.score_direction='MAXIMIZE' AND pol.score>best) OR (term.score_direction='MINIMIZE' AND pol.score<best) THEN best:=pol.score; ns:=0;
      ELSE ns:=ns+1; END IF;
     END IF;
    END IF;
   END LOOP;
   IF u.failure_streak<>fs OR u.no_improvement_streak<>ns THEN RAISE EXCEPTION 'counterfeit streak' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;
  END IF;
  IF history.command_name IN ('reserve_task_budget','settle_task_budget','evaluate_task_termination','request_capability_invocation','finish_capability_invocation') THEN
   FOREACH k IN ARRAY ARRAY['agent_steps','llm_calls','search_calls','code_iterations','experiment_runs','tree_nodes','gpu_hours','token_cost'] LOOP
    SELECT coalesce(sum(CASE WHEN bu.id IS NULL THEN (to_jsonb(br)->>k)::numeric ELSE (to_jsonb(bu)->>k)::numeric END),0) INTO total
     FROM budget_reservations br JOIN research_task_command_receipts cr ON cr.id=br.receipt_id LEFT JOIN (
      budget_usage_records bu JOIN research_task_command_receipts ur ON ur.id=bu.receipt_id AND ur.resulting_row_version<=history.resulting_row_version)
      ON bu.reservation_id=br.id AND bu.is_final
     WHERE br.research_task_id=p_task AND cr.resulting_row_version<=history.resulting_row_version;
    bound:=(to_jsonb(b)->>('max_'||k))::numeric;
    IF total>bound THEN RAISE EXCEPTION 'budget exceeded' USING ERRCODE='23514',CONSTRAINT='pr301_state'; END IF;
    budget_stop:=budget_stop OR (bound>0 AND total>=bound);
   END LOOP;
   budget_stop:=budget_stop OR (origin IS NOT NULL AND history.completed_at>=origin+b.max_wall_time_seconds*interval '1 second');
   SELECT coalesce(bool_or(bu.failure_streak>=term.repeated_failure_threshold),false),coalesce(bool_or(bu.no_improvement_streak>=term.max_no_improvement_iterations),false)
    INTO failure_stop,progress_stop FROM budget_usage_records bu JOIN research_task_command_receipts cr ON cr.id=bu.receipt_id WHERE bu.research_task_id=p_task AND bu.is_final AND cr.resulting_row_version<=history.resulting_row_version;
   IF history.stop_budget IS DISTINCT FROM budget_stop OR history.stop_repeated_failure IS DISTINCT FROM failure_stop OR history.stop_no_improvement IS DISTINCT FROM progress_stop
   THEN RAISE EXCEPTION 'counterfeit stop causes' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;
  END IF;
  stopped:=stopped OR history.stop_human OR history.stop_policy OR history.stop_budget OR history.stop_repeated_failure OR history.stop_no_improvement;
 END LOOP;
END $$;
```

```sql
CREATE OR REPLACE FUNCTION pr301_graph_final_guard() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE t research_tasks%ROWTYPE; s research_task_steps%ROWTYPE; b record; n integer;
BEGIN
 SELECT * INTO t FROM research_tasks WHERE id=NEW.id;
 SELECT count(*) INTO n FROM research_task_steps WHERE research_task_id=t.id;
 IF n>256 OR (SELECT count(*) FROM research_task_step_dependencies WHERE research_task_id=t.id)>1024
 OR ((SELECT count(*) FROM research_task_inputs WHERE research_task_id=t.id)+
     (SELECT count(*) FROM research_task_step_inputs WHERE research_task_id=t.id))>256
 THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_validation'; END IF;
 IF (t.status='CREATED' AND n<>0) OR (t.status='PLANNING' AND (n=0 OR EXISTS(
  SELECT 1 FROM research_task_steps WHERE research_task_id=t.id AND status<>'PENDING')))
 OR (t.status='CANCELLED' AND EXISTS(SELECT 1 FROM research_task_steps WHERE research_task_id=t.id
   AND (status<>'CANCELLED' OR finished_at IS DISTINCT FROM t.finished_at))) THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_state'; END IF;
 IF (SELECT count(*) FROM research_task_events WHERE research_task_id=t.id)<>t.row_version
 OR (SELECT count(*) FROM research_task_command_receipts WHERE research_task_id=t.id)<>t.row_version
 OR EXISTS(SELECT 1 FROM generate_series(1,t.row_version) v WHERE NOT EXISTS(
   SELECT 1 FROM research_task_events WHERE research_task_id=t.id AND sequence=v)
   OR NOT EXISTS(SELECT 1 FROM research_task_command_receipts WHERE research_task_id=t.id
     AND resulting_row_version=v)) THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_validation'; END IF;
 FOR s IN SELECT * FROM research_task_steps WHERE research_task_id=t.id LOOP
  IF (SELECT count(*) FROM research_task_step_events WHERE step_id=s.id AND research_task_id=t.id)<>s.row_version
  OR NOT EXISTS(SELECT 1 FROM research_task_step_events WHERE step_id=s.id AND research_task_id=t.id
    AND event_type='PLANNED' AND sequence=1)
  OR (s.status='CANCELLED' AND NOT EXISTS(SELECT 1 FROM research_task_step_events
    WHERE step_id=s.id AND research_task_id=t.id AND event_type='CANCELLED' AND sequence=2
      AND occurred_at=t.finished_at)) THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_validation'; END IF;
 END LOOP;
 IF t.plan_sealed_at IS NOT NULL THEN
  FOR b IN SELECT research_question_version_id,hypothesis_version_id,claim_version_id,source_version_id,
    artifact_version_id,manuscript_version_id,content_hash,hash_scheme FROM research_task_inputs WHERE research_task_id=t.id
    UNION ALL SELECT research_question_version_id,hypothesis_version_id,claim_version_id,source_version_id,
    artifact_version_id,manuscript_version_id,content_hash,hash_scheme FROM research_task_step_inputs WHERE research_task_id=t.id
  LOOP PERFORM pr301_validate_input(t.id,b.research_question_version_id,b.hypothesis_version_id,b.claim_version_id,
    b.source_version_id,b.artifact_version_id,b.manuscript_version_id,b.content_hash,b.hash_scheme); END LOOP;
 END IF;
 PERFORM pr304_validate_safety(NEW.id);
 PERFORM pr303_validate_gateway(NEW.id);
 RETURN NULL;
END $$;
```

```sql
CREATE OR REPLACE FUNCTION pr301_receipt_complete() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE r research_task_command_receipts%ROWTYPE; e research_task_events%ROWTYPE; mapped text;
 expected integer; actual integer; gateway boolean; ci capability_invocations%ROWTYPE; ce capability_invocation_events%ROWTYPE;
BEGIN
 SELECT * INTO r FROM research_task_command_receipts WHERE id=NEW.id;
 SELECT te.* INTO e FROM research_task_receipt_events l JOIN research_task_events te ON te.id=l.event_id
  WHERE l.receipt_id=r.id;
 mapped:=CASE r.command_name WHEN 'create_research_task' THEN 'CREATED'
 WHEN 'create_task_plan' THEN 'PLAN_CREATED' WHEN 'add_task_step' THEN 'STEP_ADDED'
 WHEN 'add_task_step_dependency' THEN 'DEPENDENCY_ADDED' WHEN 'seal_task_plan' THEN 'PLAN_SEALED'
 WHEN 'cancel_research_task' THEN 'CANCELLED' WHEN 'bind_task_policies' THEN 'POLICIES_BOUND' WHEN 'reserve_task_budget' THEN 'BUDGET_RESERVED' WHEN 'settle_task_budget' THEN 'BUDGET_SETTLED' WHEN 'evaluate_task_termination' THEN 'TERMINATION_EVALUATED' WHEN 'request_human_checkpoint' THEN 'CHECKPOINT_REQUESTED' WHEN 'respond_human_checkpoint' THEN 'CHECKPOINT_RESPONDED'
 WHEN 'register_agent_tool_policy' THEN 'TOOL_POLICY_REGISTERED'
 WHEN 'request_capability_invocation' THEN 'CAPABILITY_REQUESTED'
 WHEN 'start_capability_invocation' THEN 'CAPABILITY_STARTED'
 WHEN 'finish_capability_invocation' THEN 'CAPABILITY_FINISHED' END;
 IF e.id IS NULL OR e.event_type IS DISTINCT FROM mapped OR
  ROW(e.research_task_id,e.actor_id,e.command_id,e.task_row_version) IS DISTINCT FROM
  ROW(r.research_task_id,r.actor_id,r.command_id,r.resulting_row_version) THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_validation'; END IF;
 IF mapped='CREATED' AND e.occurred_at IS DISTINCT FROM
   (SELECT created_at FROM research_tasks WHERE id=r.research_task_id) THEN
   RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514',
     CONSTRAINT='pr301_validation';
 END IF;
 IF mapped='PLAN_SEALED' AND e.occurred_at IS DISTINCT FROM
   (SELECT plan_sealed_at FROM research_tasks WHERE id=r.research_task_id) THEN
   RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514',
     CONSTRAINT='pr301_validation';
 END IF;
 IF mapped='DEPENDENCY_ADDED' AND (SELECT count(*) FROM research_task_step_dependencies
   WHERE research_task_id=r.research_task_id AND xmin=pg_current_xact_id()::xid)<>1 THEN
   RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514',
     CONSTRAINT='pr301_validation';
 END IF;
 IF e.sequence>1 AND e.prior_status IS DISTINCT FROM (SELECT new_status FROM research_task_events
   WHERE research_task_id=r.research_task_id AND sequence=e.sequence-1) THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_validation'; END IF;
 IF EXISTS(SELECT 1 FROM research_task_step_events se LEFT JOIN research_task_receipt_step_events l
   ON l.step_event_id=se.id WHERE se.research_task_id=r.research_task_id AND se.command_id=r.command_id
   AND se.actor_id=r.actor_id AND (l.receipt_id IS DISTINCT FROM r.id OR
     se.task_row_version<>r.resulting_row_version OR se.occurred_at IS DISTINCT FROM e.occurred_at
     OR se.reason IS DISTINCT FROM e.reason OR
     se.event_type IS DISTINCT FROM CASE WHEN mapped='CANCELLED' THEN 'CANCELLED' ELSE 'PLANNED' END))
 THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_validation'; END IF;
 SELECT count(*) INTO actual FROM research_task_receipt_step_events WHERE receipt_id=r.id;
 expected:=CASE WHEN mapped='PLAN_CREATED' THEN (SELECT count(*) FROM research_task_steps WHERE research_task_id=r.research_task_id)
 WHEN mapped='STEP_ADDED' THEN 1 WHEN mapped='CANCELLED' THEN (SELECT count(*) FROM research_task_steps WHERE research_task_id=r.research_task_id)
 ELSE 0 END;
 IF actual<>expected THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_validation'; END IF;
 IF mapped='CANCELLED' AND e.occurred_at IS DISTINCT FROM (SELECT finished_at FROM research_tasks WHERE id=r.research_task_id)
 THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_validation'; END IF;

 IF (SELECT count(*) FROM execution_budgets WHERE receipt_id=r.id)<>(CASE r.command_name WHEN 'bind_task_policies' THEN 1 WHEN 'request_human_checkpoint' THEN (SELECT count(*) FROM human_checkpoints WHERE receipt_id=r.id AND checkpoint_type='budget_extension') ELSE 0 END) THEN RAISE EXCEPTION 'wrong safety result count' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;

 IF (SELECT count(*) FROM termination_policies WHERE receipt_id=r.id)<>(CASE WHEN r.command_name='bind_task_policies' THEN 1 ELSE 0 END) THEN RAISE EXCEPTION 'wrong safety result count' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;

 IF (SELECT count(*) FROM checkpoint_policies WHERE receipt_id=r.id)<>(CASE WHEN r.command_name='bind_task_policies' THEN 1 ELSE 0 END) THEN RAISE EXCEPTION 'wrong safety result count' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;

 IF r.command_name<>'bind_task_policies' AND EXISTS(SELECT 1 FROM checkpoint_policy_dataset_scopes WHERE receipt_id=r.id) THEN RAISE EXCEPTION 'extra scope effect' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;

 IF r.command_name<>'bind_task_policies' AND EXISTS(SELECT 1 FROM checkpoint_policy_metric_scopes WHERE receipt_id=r.id) THEN RAISE EXCEPTION 'extra scope effect' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;

 IF (SELECT count(*) FROM budget_reservations WHERE receipt_id=r.id)<>(CASE WHEN r.command_name IN ('reserve_task_budget','request_capability_invocation') THEN 1 ELSE 0 END) THEN RAISE EXCEPTION 'wrong safety result count' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;

 IF (SELECT count(*) FROM budget_usage_records WHERE receipt_id=r.id)<>(CASE WHEN r.command_name IN ('settle_task_budget','finish_capability_invocation') THEN 1 ELSE 0 END) THEN RAISE EXCEPTION 'wrong safety result count' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;

 IF (SELECT count(*) FROM human_checkpoints WHERE receipt_id=r.id)<>(CASE WHEN r.command_name='request_human_checkpoint' THEN 1 ELSE 0 END) THEN RAISE EXCEPTION 'wrong safety result count' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;


 IF mapped='PLAN_SEALED' AND EXISTS(SELECT 1 FROM research_task_events WHERE research_task_id=r.research_task_id AND event_type='PLAN_SEALED' AND task_row_version<r.resulting_row_version)
 THEN RAISE EXCEPTION 'plan already sealed' USING ERRCODE='23514',CONSTRAINT='pr301_immutable'; END IF;
 IF mapped='CREATED' AND EXISTS(SELECT 1 FROM research_tasks WHERE id=r.research_task_id AND budget_policy_id IS NOT NULL)
 THEN RAISE EXCEPTION 'creation must be unbound' USING ERRCODE='23514',CONSTRAINT='pr301_state'; END IF;
 IF r.command_name IN ('bind_task_policies','respond_human_checkpoint') OR e.stop_human THEN
  IF NOT EXISTS(SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id JOIN project_role_assignments p ON p.membership_id=m.id
   JOIN actor_subject_bindings b ON b.actor_id=a.id WHERE a.id=r.actor_id AND a.actor_type='HUMAN' AND a.retired_at IS NULL
   AND m.project_id=r.project_id AND m.status='ACTIVE' AND p.role='OWNER' AND p.effective_from<=r.completed_at AND (p.effective_until IS NULL OR r.completed_at<p.effective_until)
   AND b.status='ACTIVE' AND b.bound_at<=r.completed_at AND (b.revoked_at IS NULL OR r.completed_at<b.revoked_at))
  THEN RAISE EXCEPTION 'Human owner required' USING ERRCODE='23514',CONSTRAINT='pr301_scope'; END IF;
 END IF;
 IF (e.stop_human OR e.stop_policy) AND r.command_name<>'evaluate_task_termination'
 THEN RAISE EXCEPTION 'invalid explicit stop' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;
 IF EXISTS(SELECT 1 FROM human_checkpoints h WHERE h.receipt_id=r.id AND h.reason IS DISTINCT FROM e.reason)
 OR EXISTS(SELECT 1 FROM human_checkpoints h WHERE h.response_receipt_id=r.id AND h.status<>'EXPIRED' AND h.response_reason IS DISTINCT FROM e.reason)
 THEN RAISE EXCEPTION 'checkpoint reason mismatch' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;
 IF r.command_name='bind_task_policies' AND NOT EXISTS(SELECT 1 FROM research_tasks t JOIN execution_budgets b ON b.id=t.budget_policy_id AND b.receipt_id=r.id JOIN termination_policies p ON p.id=t.termination_policy_id AND p.receipt_id=r.id JOIN checkpoint_policies c ON c.id=t.checkpoint_policy_id AND c.receipt_id=r.id WHERE t.id=r.research_task_id)
 THEN RAISE EXCEPTION 'wrong policy binding' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;
 IF r.command_name='respond_human_checkpoint' THEN
  IF (SELECT count(*) FROM human_checkpoints WHERE response_receipt_id=r.id AND status IN ('APPROVED','REJECTED','MODIFIED'))<>1
  THEN RAISE EXCEPTION 'wrong response effect' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;
 ELSIF r.command_name='evaluate_task_termination' THEN
  IF EXISTS(SELECT 1 FROM human_checkpoints WHERE research_task_id=r.research_task_id AND
    ((response_receipt_id=r.id AND status<>'EXPIRED') OR (status='PENDING' AND expires_at<=r.completed_at)))
  THEN RAISE EXCEPTION 'wrong expiry effects' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;
 ELSIF EXISTS(SELECT 1 FROM human_checkpoints WHERE response_receipt_id=r.id)
 THEN RAISE EXCEPTION 'extra response effect' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;
 IF r.command_name IN ('bind_task_policies','reserve_task_budget','settle_task_budget','evaluate_task_termination','request_human_checkpoint','respond_human_checkpoint','register_agent_tool_policy','request_capability_invocation','start_capability_invocation','finish_capability_invocation') THEN
  IF r.completed_at<transaction_timestamp() OR r.completed_at>clock_timestamp() OR e.occurred_at IS DISTINCT FROM r.completed_at
   OR EXISTS(SELECT 1 FROM research_task_steps WHERE research_task_id=r.research_task_id AND xmin=pg_current_xact_id()::xid)
   OR EXISTS(SELECT 1 FROM research_task_inputs WHERE research_task_id=r.research_task_id AND xmin=pg_current_xact_id()::xid)
   OR EXISTS(SELECT 1 FROM research_task_step_dependencies WHERE research_task_id=r.research_task_id AND xmin=pg_current_xact_id()::xid)
   OR EXISTS(SELECT 1 FROM research_task_step_inputs WHERE research_task_id=r.research_task_id AND xmin=pg_current_xact_id()::xid)
  THEN RAISE EXCEPTION 'unrelated safety effect' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;
  IF e.prior_status='CANCELLED' AND r.command_name NOT IN ('settle_task_budget','evaluate_task_termination','finish_capability_invocation')
  THEN RAISE EXCEPTION 'terminal safety effect' USING ERRCODE='23514',CONSTRAINT='pr301_state'; END IF;
 END IF;

 gateway:=r.command_name IN ('register_agent_tool_policy','request_capability_invocation','start_capability_invocation','finish_capability_invocation');
 IF ROW(e.result_tool_policy_id,e.result_capability_invocation_id,e.result_capability_event_id)
  IS DISTINCT FROM ROW(r.result_tool_policy_id,r.result_capability_invocation_id,r.result_capability_event_id) THEN
  RAISE EXCEPTION 'task event result pointers' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
 END IF;
 IF (SELECT count(*) FROM agent_tool_policies WHERE receipt_id=r.id)<>
    CASE WHEN r.command_name='register_agent_tool_policy' THEN 1 ELSE 0 END
  OR (SELECT count(*) FROM capability_invocations WHERE request_receipt_id=r.id)<>
    CASE WHEN r.command_name='request_capability_invocation' THEN 1 ELSE 0 END
  OR (SELECT count(*) FROM capability_invocation_events WHERE receipt_id=r.id)<>
    CASE WHEN r.command_name IN ('request_capability_invocation','start_capability_invocation','finish_capability_invocation') THEN 1 ELSE 0 END THEN
  RAISE EXCEPTION 'gateway result cardinality' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
 END IF;
 IF NOT gateway THEN
  IF num_nonnulls(r.result_tool_policy_id,r.result_capability_invocation_id,r.result_capability_event_id,r.resulting_invocation_revision)<>0
   OR EXISTS(SELECT 1 FROM capability_invocation_refs WHERE receipt_id=r.id) THEN
   RAISE EXCEPTION 'extra gateway effect on old command' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
  END IF;
 ELSE
  IF EXISTS(SELECT 1 FROM research_task_command_receipts WHERE id=r.id AND xmin=pg_current_xact_id()::xid)
   AND NOT EXISTS(SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id
    JOIN project_role_assignments pa ON pa.membership_id=m.id JOIN actor_subject_bindings ab ON ab.actor_id=a.id
    WHERE a.id=r.actor_id AND a.retired_at IS NULL AND m.project_id=r.project_id AND m.status='ACTIVE'
     AND pa.role IN ('OWNER','RESEARCHER','REVIEWER','APPROVER','VIEWER')
     AND pa.effective_from<=clock_timestamp() AND (pa.effective_until IS NULL OR clock_timestamp()<pa.effective_until)
     AND ab.status='ACTIVE' AND ab.bound_at<=clock_timestamp() AND (ab.revoked_at IS NULL OR clock_timestamp()<ab.revoked_at)) THEN
   RAISE EXCEPTION 'current gateway read entitlement' USING ERRCODE='23514', CONSTRAINT='pr301_scope';
  END IF;
  IF e.prior_status IS DISTINCT FROM e.new_status OR e.stop_human OR e.stop_policy
   OR EXISTS(SELECT 1 FROM research_tasks t WHERE t.id=r.research_task_id AND t.plan_sealed_at IS NOT NULL
     AND NOT EXISTS(SELECT 1 FROM research_task_events se WHERE se.research_task_id=t.id
      AND se.event_type='PLAN_SEALED' AND se.occurred_at=t.plan_sealed_at AND se.task_row_version<r.resulting_row_version))
   OR EXISTS(SELECT 1 FROM research_tasks t JOIN execution_budgets eb ON eb.id=t.budget_policy_id
      WHERE t.id=r.research_task_id AND eb.receipt_id=r.id) THEN
   RAISE EXCEPTION 'gateway task intent seal or policy effect' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
  END IF;
  IF (SELECT count(*) FROM research_task_events WHERE research_task_id=r.research_task_id
     AND task_row_version=r.resulting_row_version)<>1
   OR (SELECT count(*) FROM research_task_receipt_events WHERE receipt_id=r.id)<>1
   OR EXISTS(SELECT 1 FROM research_task_receipt_step_events WHERE receipt_id=r.id) THEN
   RAISE EXCEPTION 'one gateway task event and no step events' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
  END IF;
  IF r.command_name='register_agent_tool_policy' THEN
   IF NOT EXISTS(SELECT 1 FROM agent_tool_policies p WHERE p.id=r.result_tool_policy_id
    AND p.registration_task_id=r.research_task_id AND p.project_id=r.project_id AND p.receipt_id=r.id
    AND p.created_by=r.actor_id AND p.created_at=r.completed_at)
    OR EXISTS(SELECT 1 FROM capability_invocation_refs WHERE receipt_id=r.id) THEN
    RAISE EXCEPTION 'policy registration result' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
   END IF;
  ELSE
   SELECT * INTO ci FROM capability_invocations WHERE id=r.result_capability_invocation_id;
   SELECT * INTO ce FROM capability_invocation_events WHERE id=r.result_capability_event_id;
   IF ci.id IS NULL OR ce.id IS NULL OR ROW(ci.policy_id,ci.research_task_id,ci.project_id,
     ce.invocation_id,ce.receipt_id,ce.invocation_row_version,ce.actor_id,ce.occurred_at,ce.reason)
    IS DISTINCT FROM ROW(r.result_tool_policy_id,r.research_task_id,r.project_id,
     ci.id,r.id,r.resulting_invocation_revision,r.actor_id,r.completed_at,e.reason)
    OR ce.event_type IS DISTINCT FROM CASE r.command_name WHEN 'request_capability_invocation' THEN 'REQUESTED'
     WHEN 'start_capability_invocation' THEN 'STARTED' ELSE ce.event_type END
    OR (r.command_name='finish_capability_invocation' AND ce.event_type NOT IN ('FINISHED','RECONCILED')) THEN
    RAISE EXCEPTION 'saved gateway result' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
   END IF;
   IF r.command_name='start_capability_invocation' AND EXISTS(SELECT 1 FROM capability_invocation_refs WHERE receipt_id=r.id)
    OR EXISTS(SELECT 1 FROM capability_invocation_refs ref WHERE ref.receipt_id=r.id AND
      (ref.invocation_id<>ci.id OR ref.direction IS DISTINCT FROM
       CASE WHEN r.command_name='request_capability_invocation' THEN 'INPUT' ELSE 'OUTPUT' END)) THEN
    RAISE EXCEPTION 'extra gateway reference effect' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
   END IF;
   IF EXISTS(SELECT 1 FROM budget_reservations br WHERE br.receipt_id=r.id AND
      ROW(br.id,br.operation_id,br.step_id) IS DISTINCT FROM ROW(ci.reservation_id,ci.id,ci.step_id))
    OR EXISTS(SELECT 1 FROM budget_usage_records bu WHERE bu.receipt_id=r.id AND
      ROW(bu.id,bu.reservation_id) IS DISTINCT FROM ROW(ce.usage_record_id,ci.reservation_id)) THEN
    RAISE EXCEPTION 'extra gateway accounting effect' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
   END IF;
   -- This check is on the fresh receipt only; replay uses saved event revision,
   -- not a later invocation projection.
   IF EXISTS(SELECT 1 FROM research_task_command_receipts WHERE id=r.id AND xmin=pg_current_xact_id()::xid) THEN
    IF ce.event_type='RECONCILED' THEN
     IF EXISTS(SELECT 1 FROM capability_invocations WHERE id=ci.id AND xmin=pg_current_xact_id()::xid) THEN
      RAISE EXCEPTION 'reconciliation cannot rewrite invocation' USING ERRCODE='23514', CONSTRAINT='pr301_immutable';
     END IF;
    ELSIF NOT EXISTS(SELECT 1 FROM capability_invocations WHERE id=ci.id AND xmin=pg_current_xact_id()::xid)
     OR ci.row_version IS DISTINCT FROM ce.invocation_row_version OR ci.status IS DISTINCT FROM ce.new_status THEN
     RAISE EXCEPTION 'missing invocation write' USING ERRCODE='23514', CONSTRAINT='pr301_validation';
    END IF;
   END IF;
  END IF;
 END IF;
 RETURN NULL;
END $$;
```

### 4.6 Existing trigger attachment audit

CREATE OR REPLACE changes the callees in place. These are all existing triggers
whose function body is replaced; none is silently re-pointed to a different
function. If “re-point” includes replacing its callee, this is the complete list.
All paths are under `migrations/versions/`.

| Retained trigger | Table and attachment | Existing source | Callee above |
| --- | --- | --- | --- |
| pr301_task_guard | research_tasks BEFORE INSERT/UPDATE/DELETE | 0077_research_task_graph.py:373–374 | pr301_task_guard() |
| pr301_receipt_insert | research_task_command_receipts BEFORE INSERT | 0077_research_task_graph.py:513–514 | pr301_receipt_insert_guard() |
| pr301_task_final | research_tasks AFTER INSERT/UPDATE, DEFERRABLE INITIALLY DEFERRED | 0077_research_task_graph.py:613–614 | pr301_graph_final_guard() |
| pr301_receipt_complete_commit | research_task_command_receipts AFTER INSERT, DEFERRABLE INITIALLY DEFERRED | 0077_research_task_graph.py:663–664 | pr301_receipt_complete() |
| pr304_budget_guard | execution_budgets BEFORE INSERT/UPDATE/DELETE | 0078_task_safety_policies.py:724 | pr304_child_guard() |
| pr304_termination_guard | termination_policies BEFORE INSERT/UPDATE/DELETE | 0078_task_safety_policies.py:725 | pr304_child_guard() |
| pr304_checkpoint_policy_guard | checkpoint_policies BEFORE INSERT/UPDATE/DELETE | 0078_task_safety_policies.py:726 | pr304_child_guard() |
| pr304_dataset_scope_guard | checkpoint_policy_dataset_scopes BEFORE INSERT/UPDATE/DELETE | 0078_task_safety_policies.py:727 | pr304_child_guard() |
| pr304_metric_scope_guard | checkpoint_policy_metric_scopes BEFORE INSERT/UPDATE/DELETE | 0078_task_safety_policies.py:728 | pr304_child_guard() |
| pr304_reservation_guard | budget_reservations BEFORE INSERT/UPDATE/DELETE | 0078_task_safety_policies.py:729 | pr304_child_guard() |
| pr304_usage_guard | budget_usage_records BEFORE INSERT/UPDATE/DELETE | 0078_task_safety_policies.py:730 | pr304_child_guard() |

Conceptual signature review: all pr301_validate_input calls supply exactly the
nine typed arguments in the delivered order; ArtifactVersion calls supply NULL
scheme. Both whole-state helpers take one task UUID and return void. The hash
reconstruction passes a JSONB envelope to pr304_canonical_policy_json and hashes
its returned text as UTF-8; it requires no extension. Artifact byte_size is a
nullable bigint (0006_artifact_version.py:42), checked with IS DISTINCT FROM;
no ArtifactVersion.hash_scheme or nonexistent registry-byte helper is selected.
Trigger-returning functions remain attached only to triggers. SQL compilation
and execution are NOT RUN in this documentation task; PostgreSQL parity and
constraint behavior remain future implementation evidence in §9.1.

The nine new immediate triggers are exactly §4.1. No additional trigger is
needed by these bodies. pr304_validate_safety is a void helper called once by
pr301_graph_final_guard, not a trigger; pr303_validate_gateway is likewise called
once from that guard. The unchanged pr304_checkpoint_guard and all original
history/link/cycle triggers retain their attachments and mutation denials.

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

The FIRST implementation step is to apply 0080 to a disposable PostgreSQL 18
database and run each body's `CREATE OR REPLACE`; only after every body compiles
may DDL/integration tests be authorized. Failure to compile blocks implementation
acceptance. This is a documented future gate; do not execute it for this pack.

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

### 12.1a Identifiers used by §4.4 bodies

This supplements §12.1 after the complete §4.4 bodies were added. It includes
all newly used delivered names plus the requested shared accounting spellings
already present in §12.1; policy/streak names also cover the §4.5 replacements.
Each command below runs from the repository root. Matches in 0077/0078/0079
anchor delivered definitions or inherited use; identity interval/role fields
are inherited from earlier migrations, not newly defined by these migrations.
The required `-F` search prints the first matching full line, so a shared spelling
such as `gpu_hours` can first match its `max_gpu_hours` policy column.
The eight `max_*` resource fields are included because §4.4 constructs their
names dynamically from the resource keys.

All names created by PR3-03 (`pr303_*`, new table names, `result_tool_policy_id`,
`resulting_invocation_revision` and the other §3 columns) are labelled **new in PR3-03**,
not audited against delivered migrations. The DDL in §2 defines five new tables:
`agent_tool_policies`, `agent_tool_policy_permissions`, `capability_invocations`,
`capability_invocation_refs`, `capability_invocation_events`; no sixth table is
specified or introduced by this audit. New table-qualified columns remain new
even when their unqualified spelling is shared with a delivered column.
SQL built-ins, local variables, CTE names and aliases are not delivered APIs.

Exact commands:

```sh
rg -n --with-filename -m 1 -F -- max_tree_depth migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- max_parallel_branches migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- score_metric_version_id migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- evaluator_version migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- score_direction migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- repeated_failure_threshold migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- max_no_improvement_iterations migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- proposed_budget_id migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- expires_at migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- response_reason migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- failure_streak migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- no_improvement_streak migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- maximum_autonomy migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- pricing_basis migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- max_wall_time_seconds migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- required_types migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- checkpoint_type migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- response_receipt_id migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- bound_at migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- revoked_at migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- effective_from migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- effective_until migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- membership_id migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- retired_at migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- byte_size migrations/versions/0077_research_task_graph.py
rg -n --with-filename -m 1 -F -- byte_size migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- byte_size migrations/versions/0079_agent_identity_versions.py
rg -n --with-filename -m 1 -F -- deadline migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- budget_id migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- receipt_id migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- is_final migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- outcome migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- reservation_id migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- wall_time_seconds migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- gpu_hours migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- token_cost migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- code_iterations migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- experiment_runs migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- tree_nodes migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- agent_steps migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- search_calls migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- task_row_version migrations/versions/0077_research_task_graph.py
rg -n --with-filename -m 1 -F -- completed_at migrations/versions/0077_research_task_graph.py
rg -n --with-filename -m 1 -F -- budget_policy_id migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- checkpoint_policy_id migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- autonomy_level migrations/versions/0077_research_task_graph.py
rg -n --with-filename -m 1 -F -- actor_type migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- role migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- max_agent_steps migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- max_llm_calls migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- max_search_calls migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- max_code_iterations migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- max_experiment_runs migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- max_tree_nodes migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- max_gpu_hours migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- max_token_cost migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- termination_policy_id migrations/versions/0078_task_safety_policies.py
rg -n --with-filename -m 1 -F -- plan_sealed_at migrations/versions/0077_research_task_graph.py
```

Captured stdout, in command order (all matching commands exit 0):

```text
migrations/versions/0078_task_safety_policies.py:24:  max_tree_depth integer NOT NULL CHECK (max_tree_depth > 0),
migrations/versions/0078_task_safety_policies.py:25:  max_parallel_branches integer NOT NULL CHECK (max_parallel_branches > 0),
migrations/versions/0078_task_safety_policies.py:49:  score_metric_version_id uuid NULL REFERENCES metric_definition_versions(id) ON DELETE RESTRICT,
migrations/versions/0078_task_safety_policies.py:51:  evaluator_version text NULL CHECK (length(btrim(evaluator_version)) BETWEEN 1 AND 128 AND evaluator_version IS NFC NORMALIZED AND lower(btrim(evaluator_version)) NOT IN ('latest','main','master')),
migrations/versions/0078_task_safety_policies.py:50:  score_direction text NULL CHECK (score_direction IN ('MAXIMIZE','MINIMIZE')),
migrations/versions/0078_task_safety_policies.py:44:  repeated_failure_threshold integer NOT NULL CHECK (repeated_failure_threshold > 0),
migrations/versions/0078_task_safety_policies.py:45:  max_no_improvement_iterations integer NOT NULL CHECK (max_no_improvement_iterations > 0),
migrations/versions/0078_task_safety_policies.py:221:  proposed_budget_id uuid NULL,
migrations/versions/0078_task_safety_policies.py:215:  expires_at timestamptz NOT NULL CHECK (expires_at > requested_at),
migrations/versions/0078_task_safety_policies.py:218:  response_reason text NULL CHECK (length(btrim(response_reason)) BETWEEN 1 AND 8192 AND response_reason IS NFC NORMALIZED),
migrations/versions/0078_task_safety_policies.py:189:  failure_streak integer NOT NULL CHECK (failure_streak >= 0),
migrations/versions/0078_task_safety_policies.py:190:  no_improvement_streak integer NOT NULL CHECK (no_improvement_streak >= 0),
migrations/versions/0078_task_safety_policies.py:77:  maximum_autonomy text NOT NULL CHECK (maximum_autonomy IN ('A0','A1','A2','A3')),
migrations/versions/0078_task_safety_policies.py:29:  pricing_basis text NOT NULL CHECK (length(btrim(pricing_basis)) BETWEEN 1 AND 512 AND pricing_basis IS NFC NORMALIZED AND lower(btrim(pricing_basis)) NOT IN ('latest','main','master')),
migrations/versions/0078_task_safety_policies.py:17:  max_wall_time_seconds integer NOT NULL CHECK (max_wall_time_seconds > 0),
migrations/versions/0078_task_safety_policies.py:75:  required_types text[] NOT NULL CHECK (required_types <@ ARRAY['plan_review','hypothesis_selection','experiment_approval','budget_extension','code_risk','claim_freeze','manuscript_release','exception']::text[] AND array_position(required_types,NULL) IS NULL),
migrations/versions/0078_task_safety_policies.py:211:  checkpoint_type text NOT NULL CHECK (checkpoint_type IN ('plan_review','hypothesis_selection','experiment_approval','budget_extension','code_risk','claim_freeze','manuscript_release','exception')),
migrations/versions/0078_task_safety_policies.py:220:  response_receipt_id uuid NULL,
migrations/versions/0078_task_safety_policies.py:408:   AND b.status='ACTIVE' AND b.bound_at<=now_at AND (b.revoked_at IS NULL OR now_at<b.revoked_at))
migrations/versions/0078_task_safety_policies.py:408:   AND b.status='ACTIVE' AND b.bound_at<=now_at AND (b.revoked_at IS NULL OR now_at<b.revoked_at))
migrations/versions/0078_task_safety_policies.py:407:   AND m.project_id=t.project_id AND m.status='ACTIVE' AND p.role='OWNER' AND p.effective_from<=now_at AND (p.effective_until IS NULL OR now_at<p.effective_until)
migrations/versions/0078_task_safety_policies.py:407:   AND m.project_id=t.project_id AND m.status='ACTIVE' AND p.role='OWNER' AND p.effective_from<=now_at AND (p.effective_until IS NULL OR now_at<p.effective_until)
migrations/versions/0078_task_safety_policies.py:405:  IF NOT EXISTS(SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id JOIN project_role_assignments p ON p.membership_id=m.id
migrations/versions/0078_task_safety_policies.py:406:   JOIN actor_subject_bindings b ON b.actor_id=a.id WHERE a.id=r.actor_id AND a.actor_type='HUMAN' AND a.retired_at IS NULL
migrations/versions/0078_task_safety_policies.py:159:  deadline timestamptz NOT NULL CHECK (deadline > created_at),
migrations/versions/0078_task_safety_policies.py:145:  budget_id uuid NOT NULL,
migrations/versions/0078_task_safety_policies.py:16:  receipt_id uuid NOT NULL,
migrations/versions/0078_task_safety_policies.py:179:  is_final boolean NOT NULL,
migrations/versions/0078_task_safety_policies.py:178:  outcome text NOT NULL CHECK (outcome IN ('SUCCEEDED','FAILED','CANCELLED','PRUNED','UNKNOWN')),
migrations/versions/0078_task_safety_policies.py:177:  reservation_id uuid NOT NULL,
migrations/versions/0078_task_safety_policies.py:17:  max_wall_time_seconds integer NOT NULL CHECK (max_wall_time_seconds > 0),
migrations/versions/0078_task_safety_policies.py:26:  max_gpu_hours numeric(20,6) NOT NULL CHECK (max_gpu_hours >= 0 AND max_gpu_hours < 'Infinity'::numeric),
migrations/versions/0078_task_safety_policies.py:27:  max_token_cost numeric(20,6) NOT NULL CHECK (max_token_cost > 0 AND max_token_cost < 'Infinity'::numeric),
migrations/versions/0078_task_safety_policies.py:21:  max_code_iterations bigint NOT NULL CHECK (max_code_iterations > 0),
migrations/versions/0078_task_safety_policies.py:22:  max_experiment_runs bigint NOT NULL CHECK (max_experiment_runs > 0),
migrations/versions/0078_task_safety_policies.py:23:  max_tree_nodes bigint NOT NULL CHECK (max_tree_nodes > 0),
migrations/versions/0078_task_safety_policies.py:18:  max_agent_steps bigint NOT NULL CHECK (max_agent_steps > 0),
migrations/versions/0078_task_safety_policies.py:20:  max_search_calls bigint NOT NULL CHECK (max_search_calls > 0),
migrations/versions/0077_research_task_graph.py:212:  task_row_version integer NOT NULL CHECK (task_row_version >= 1),
migrations/versions/0077_research_task_graph.py:192:  completed_at timestamptz NOT NULL,
migrations/versions/0078_task_safety_policies.py:129:  ADD COLUMN budget_policy_id uuid NULL,
migrations/versions/0078_task_safety_policies.py:99:  checkpoint_policy_id uuid NOT NULL,
migrations/versions/0077_research_task_graph.py:28:  autonomy_level text NOT NULL CHECK (autonomy_level IN ('A0','A1','A2','A3')),
migrations/versions/0078_task_safety_policies.py:406:   JOIN actor_subject_bindings b ON b.actor_id=a.id WHERE a.id=r.actor_id AND a.actor_type='HUMAN' AND a.retired_at IS NULL
migrations/versions/0078_task_safety_policies.py:405:  IF NOT EXISTS(SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id JOIN project_role_assignments p ON p.membership_id=m.id
migrations/versions/0078_task_safety_policies.py:18:  max_agent_steps bigint NOT NULL CHECK (max_agent_steps > 0),
migrations/versions/0078_task_safety_policies.py:19:  max_llm_calls bigint NOT NULL CHECK (max_llm_calls > 0),
migrations/versions/0078_task_safety_policies.py:20:  max_search_calls bigint NOT NULL CHECK (max_search_calls > 0),
migrations/versions/0078_task_safety_policies.py:21:  max_code_iterations bigint NOT NULL CHECK (max_code_iterations > 0),
migrations/versions/0078_task_safety_policies.py:22:  max_experiment_runs bigint NOT NULL CHECK (max_experiment_runs > 0),
migrations/versions/0078_task_safety_policies.py:23:  max_tree_nodes bigint NOT NULL CHECK (max_tree_nodes > 0),
migrations/versions/0078_task_safety_policies.py:26:  max_gpu_hours numeric(20,6) NOT NULL CHECK (max_gpu_hours >= 0 AND max_gpu_hours < 'Infinity'::numeric),
migrations/versions/0078_task_safety_policies.py:27:  max_token_cost numeric(20,6) NOT NULL CHECK (max_token_cost > 0 AND max_token_cost < 'Infinity'::numeric),
migrations/versions/0078_task_safety_policies.py:130:  ADD COLUMN termination_policy_id uuid NULL,
migrations/versions/0077_research_task_graph.py:33:  plan_sealed_at timestamptz NULL,
```

`byte_size`: **not found** in 0077/0078/0079 (each command exits 1 with empty stdout); inherited `artifact_versions.byte_size` is defined in `migrations/versions/0006_artifact_version.py:42`, so the body has no identifier defect and needs no correction.
The earlier definition is confirmed by this additional read-only command:

```sh
rg -n --with-filename -m 1 -F -- byte_size migrations/versions/0006_artifact_version.py
```

Captured stdout (exit 0):

```text
migrations/versions/0006_artifact_version.py:42:        sa.Column("byte_size", sa.BigInteger(), nullable=True),
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

The recorded 246 figure is an approximate regex count, not a per-identifier
label proof. The script below constructs a heuristic inventory as set new,
counting scoped columns by owning table,
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
export UV_CACHE_DIR=<any writable dir>
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

Run with UV_CACHE_DIR=<any writable dir> exported in the
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
