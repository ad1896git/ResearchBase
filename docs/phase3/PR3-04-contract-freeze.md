# PR3-04 contract freeze and execution pack

Status: FROZEN execution pack; passed two director reviews 2026-10-21 (identifier
check: 333 identifiers, 1 mismatch fixed). Implementation AUTHORIZED by the owner
(ADR-0024). This document grants no Phase 3 GO or runtime activation.

Authority: [approved contract](../proposals/PR3-04_Budget_Termination_Checkpoint_Contract_DRAFT.md)
and [ADR-0024](../architecture/adr/ADR-0024-pr3-04-budget-termination-checkpoint.md),
D1–D6. Read AGENTS.md, architecture 01, 02, 03, 08, Phase 3 specification 06,
Harness specification 09, then this pack. Preserve the
[PR3-01 freeze](PR3-01-contract-freeze.md), especially §3.4.

## 1. Baseline and scope

Delivered parent/head: `0077_research_task_graph`, with the delivered PR3-01
Application, repository, queries, transports and regression suites. NEW migration:
`migrations/versions/0078_task_safety_policies.py`, revision
`0078_task_safety_policies`, down_revision `0077_research_task_graph`,
branch_labels=None, depends_on=None. Verify sole head before implementation;
if it changes, STOP for pack revision. Never edit an accepted migration.
Downgrade raises RuntimeError before DDL or revision-pointer changes, on empty
and populated databases. Repair requires a reviewed forward migration.

Every `pr304_` name, every table/column introduced by §2, and every safety
command, argument class, DTO and file explicitly labeled NEW below is proposed
work. All enum literals introduced in the new safety schemas are NEW; existing
task states, autonomy levels and ErrorCodes retain their delivered meanings. Existing identifiers are inventoried in §8. SQL built-ins are
PostgreSQL primitives. No new dependency, public ErrorCode or scientific entity.

Scope: immutable task policy bundles, worst-case reservations, attributable
settlements, deterministic stop evaluation, Human checkpoints, read projections
and deterministic fake consumer evidence. The six core tables implement ADR-0024
D1. Two additional typed scope relations implement its explicitly approved D1
execution-pack requirement; their individual schema justifications are in §2.
No provider, dispatch, lease, worker, gateway, recovery, sandbox, promotion,
scientific freeze/release, tree-search execution or new Approval purpose.
Existing reserved execution commands remain disabled, with execution_enabled=false.
CREATED/PLANNING/CANCELLED and PENDING/CANCELLED remain the only task/step states.
TERMINATED_BUDGET, TERMINATED_POLICY and WAITING_HUMAN are NOT added to TaskStatus.

D2: an extension approves intent only. It never replaces an active budget,
clears a stop, refunds usage or reopens history. Continuation is a new explicitly
linked task under a separate reviewed pack; no continuation relation/command is
introduced here. All unresolved reservations must be reconciled before future
continuation spend. D3 optional evaluators are explicitly disabled in this slice;
enabling one requires its separately approved evaluator contract. D4 expiry is
86400 seconds by default and response is verified current Human OWNER only.
A1/A2 are policy defaults; existing create-task A0 default stays unchanged.
Autonomy is a ceiling independent of authority; A4 is rejected.

## 2. Exact table and index DDL

Documentation only; do not execute this DDL while authoring the pack. PostgreSQL
18, synchronous I/O, READ COMMITTED mutations. All IDs are Application-generated
UUIDv7; all timestamps are aware UTC from database clock observations, supplied
by the Application. No hidden ORM defaults/indexes. PK/UNIQUE create B-tree
indexes. FKs are ON DELETE RESTRICT, ON UPDATE NO ACTION; immediate except
explicitly deferred cycles. Nullable fields say NULL. No JSON semantic core.

Schema exceptions: execution_budgets is an immutable runtime limit Entity;
termination_policies an immutable typed policy Entity; checkpoint_policies an
immutable gate Entity; human_checkpoints a stateful request/response relation;
budget_reservations a capacity relation crossing the external-work boundary;
budget_usage_records immutable accounting Events. None is scientific evidence,
Decision or Approval. NEW checkpoint_policy_dataset_scopes and
checkpoint_policy_metric_scopes are concrete policy-to-frozen-reference Relations;
each is necessary to preserve multi-valued strong FKs instead of polymorphic IDs
or JSON. Code paths and network hosts are typed text arrays, not canonical refs.

### 2.1 Policy entities and scope relations

```sql
CREATE TABLE execution_budgets (
  id uuid NOT NULL PRIMARY KEY,
  research_task_id uuid NOT NULL REFERENCES research_tasks(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL,
  receipt_id uuid NOT NULL,
  max_wall_time_seconds integer NOT NULL CHECK (max_wall_time_seconds > 0),
  max_agent_steps bigint NOT NULL CHECK (max_agent_steps > 0),
  max_llm_calls bigint NOT NULL CHECK (max_llm_calls > 0),
  max_search_calls bigint NOT NULL CHECK (max_search_calls > 0),
  max_code_iterations bigint NOT NULL CHECK (max_code_iterations > 0),
  max_experiment_runs bigint NOT NULL CHECK (max_experiment_runs > 0),
  max_tree_nodes bigint NOT NULL CHECK (max_tree_nodes > 0),
  max_tree_depth integer NOT NULL CHECK (max_tree_depth > 0),
  max_parallel_branches integer NOT NULL CHECK (max_parallel_branches > 0),
  max_gpu_hours numeric(20,6) NOT NULL CHECK (max_gpu_hours >= 0 AND max_gpu_hours < 'Infinity'::numeric),
  max_token_cost numeric(20,6) NOT NULL CHECK (max_token_cost > 0 AND max_token_cost < 'Infinity'::numeric),
  currency text NOT NULL CHECK (currency = 'USD'),
  pricing_basis text NOT NULL CHECK (length(btrim(pricing_basis)) BETWEEN 1 AND 512 AND pricing_basis IS NFC NORMALIZED AND lower(btrim(pricing_basis)) NOT IN ('latest','main','master')),
  hard_stop boolean NOT NULL CHECK (hard_stop),
  content_hash text NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
  hash_scheme text NOT NULL CHECK (hash_scheme = 'sha256-cjson-v1'),
  UNIQUE (research_task_id, id),
  FOREIGN KEY (research_task_id, receipt_id) REFERENCES research_task_command_receipts(research_task_id, id) ON DELETE RESTRICT
);
CREATE INDEX pr304_budgets_receipt ON execution_budgets(research_task_id, receipt_id);
CREATE INDEX pr304_budgets_time ON execution_budgets(research_task_id, created_at, id);

CREATE TABLE termination_policies (
  id uuid NOT NULL PRIMARY KEY,
  research_task_id uuid NOT NULL REFERENCES research_tasks(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL,
  receipt_id uuid NOT NULL,
  repeated_failure_threshold integer NOT NULL CHECK (repeated_failure_threshold > 0),
  max_no_improvement_iterations integer NOT NULL CHECK (max_no_improvement_iterations > 0),
  budget_stop boolean NOT NULL CHECK (budget_stop),
  human_stop boolean NOT NULL CHECK (human_stop),
  policy_stop boolean NOT NULL CHECK (policy_stop),
  score_metric_version_id uuid NULL REFERENCES metric_definition_versions(id) ON DELETE RESTRICT,
  score_direction text NULL CHECK (score_direction IN ('MAXIMIZE','MINIMIZE')),
  evaluator_version text NULL CHECK (length(btrim(evaluator_version)) BETWEEN 1 AND 128 AND evaluator_version IS NFC NORMALIZED AND lower(btrim(evaluator_version)) NOT IN ('latest','main','master')),
  min_progress_enabled boolean NOT NULL CHECK (NOT min_progress_enabled),
  min_progress_score numeric(20,6) NULL CHECK (min_progress_score IS NULL),
  duplicate_hypothesis_enabled boolean NOT NULL CHECK (NOT duplicate_hypothesis_enabled),
  duplicate_hypothesis_threshold numeric(20,6) NULL CHECK (duplicate_hypothesis_threshold IS NULL),
  confidence_stop_enabled boolean NOT NULL CHECK (NOT confidence_stop_enabled),
  confidence_stop_threshold numeric(20,6) NULL CHECK (confidence_stop_threshold IS NULL),
  success_condition_enabled boolean NOT NULL CHECK (NOT success_condition_enabled),
  success_condition text NULL CHECK (success_condition IS NULL),
  content_hash text NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
  hash_scheme text NOT NULL CHECK (hash_scheme = 'sha256-cjson-v1'),
  CHECK (num_nonnulls(score_metric_version_id, score_direction, evaluator_version) IN (0,3)),
  UNIQUE (research_task_id, id),
  FOREIGN KEY (research_task_id, receipt_id) REFERENCES research_task_command_receipts(research_task_id, id) ON DELETE RESTRICT
);
CREATE INDEX pr304_termination_receipt ON termination_policies(research_task_id, receipt_id);
CREATE INDEX pr304_termination_time ON termination_policies(research_task_id, created_at, id);
CREATE INDEX pr304_termination_metric ON termination_policies(score_metric_version_id) WHERE score_metric_version_id IS NOT NULL;

CREATE TABLE checkpoint_policies (
  id uuid NOT NULL PRIMARY KEY,
  research_task_id uuid NOT NULL REFERENCES research_tasks(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL,
  receipt_id uuid NOT NULL,
  required_types text[] NOT NULL CHECK (required_types <@ ARRAY['plan_review','hypothesis_selection','experiment_approval','budget_extension','code_risk','claim_freeze','manuscript_release','exception']::text[] AND array_position(required_types,NULL) IS NULL),
  timeout_seconds integer NOT NULL CHECK (timeout_seconds > 0),
  maximum_autonomy text NOT NULL CHECK (maximum_autonomy IN ('A0','A1','A2','A3')),
  a3_authorized boolean NOT NULL,
  allowed_code_paths text[] NOT NULL CHECK (array_position(allowed_code_paths,NULL) IS NULL),
  network_mode text NOT NULL CHECK (network_mode IN ('DENY','ALLOWLIST')),
  allowed_network_hosts text[] NOT NULL CHECK (array_position(allowed_network_hosts,NULL) IS NULL),
  content_hash text NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
  hash_scheme text NOT NULL CHECK (hash_scheme = 'sha256-cjson-v1'),
  CHECK (a3_authorized = (maximum_autonomy = 'A3')),
  CHECK (network_mode <> 'DENY' OR cardinality(allowed_network_hosts) = 0),
  CHECK (network_mode <> 'ALLOWLIST' OR cardinality(allowed_network_hosts) > 0),
  CHECK (a3_authorized OR (cardinality(allowed_code_paths) = 0 AND network_mode = 'DENY')),
  UNIQUE (research_task_id, id),
  FOREIGN KEY (research_task_id, receipt_id) REFERENCES research_task_command_receipts(research_task_id, id) ON DELETE RESTRICT
);
CREATE INDEX pr304_checkpoint_policy_receipt ON checkpoint_policies(research_task_id, receipt_id);
CREATE INDEX pr304_checkpoint_policy_time ON checkpoint_policies(research_task_id, created_at, id);

CREATE TABLE checkpoint_policy_dataset_scopes (
  id uuid NOT NULL PRIMARY KEY,
  research_task_id uuid NOT NULL REFERENCES research_tasks(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL,
  receipt_id uuid NOT NULL,
  checkpoint_policy_id uuid NOT NULL,
  dataset_snapshot_id uuid NOT NULL REFERENCES dataset_snapshots(id) ON DELETE RESTRICT,
  content_hash text NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
  UNIQUE (checkpoint_policy_id, dataset_snapshot_id),
  FOREIGN KEY (research_task_id, checkpoint_policy_id) REFERENCES checkpoint_policies(research_task_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (research_task_id, receipt_id) REFERENCES research_task_command_receipts(research_task_id, id) ON DELETE RESTRICT
);
CREATE INDEX pr304_dataset_scope_policy ON checkpoint_policy_dataset_scopes(research_task_id, checkpoint_policy_id);
CREATE INDEX pr304_dataset_scope_receipt ON checkpoint_policy_dataset_scopes(research_task_id, receipt_id);
CREATE INDEX pr304_dataset_scope_ref ON checkpoint_policy_dataset_scopes(dataset_snapshot_id);
CREATE INDEX pr304_dataset_scope_time ON checkpoint_policy_dataset_scopes(research_task_id, created_at, id);

CREATE TABLE checkpoint_policy_metric_scopes (
  id uuid NOT NULL PRIMARY KEY,
  research_task_id uuid NOT NULL REFERENCES research_tasks(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL,
  receipt_id uuid NOT NULL,
  checkpoint_policy_id uuid NOT NULL,
  metric_definition_version_id uuid NOT NULL REFERENCES metric_definition_versions(id) ON DELETE RESTRICT,
  content_hash text NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
  UNIQUE (checkpoint_policy_id, metric_definition_version_id),
  FOREIGN KEY (research_task_id, checkpoint_policy_id) REFERENCES checkpoint_policies(research_task_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (research_task_id, receipt_id) REFERENCES research_task_command_receipts(research_task_id, id) ON DELETE RESTRICT
);
CREATE INDEX pr304_metric_scope_policy ON checkpoint_policy_metric_scopes(research_task_id, checkpoint_policy_id);
CREATE INDEX pr304_metric_scope_receipt ON checkpoint_policy_metric_scopes(research_task_id, receipt_id);
CREATE INDEX pr304_metric_scope_ref ON checkpoint_policy_metric_scopes(metric_definition_version_id);
CREATE INDEX pr304_metric_scope_time ON checkpoint_policy_metric_scopes(research_task_id, created_at, id);

ALTER TABLE research_tasks
  ADD COLUMN budget_policy_id uuid NULL,
  ADD COLUMN termination_policy_id uuid NULL,
  ADD COLUMN checkpoint_policy_id uuid NULL,
  ADD CONSTRAINT pr304_policy_bundle CHECK (num_nonnulls(budget_policy_id, termination_policy_id, checkpoint_policy_id) IN (0,3)),
  ADD CONSTRAINT pr304_task_budget_fk FOREIGN KEY (id, budget_policy_id) REFERENCES execution_budgets(research_task_id, id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
  ADD CONSTRAINT pr304_task_termination_fk FOREIGN KEY (id, termination_policy_id) REFERENCES termination_policies(research_task_id, id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
  ADD CONSTRAINT pr304_task_checkpoint_fk FOREIGN KEY (id, checkpoint_policy_id) REFERENCES checkpoint_policies(research_task_id, id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX pr304_tasks_budget ON research_tasks(id, budget_policy_id);
CREATE INDEX pr304_tasks_termination ON research_tasks(id, termination_policy_id);
CREATE INDEX pr304_tasks_checkpoint ON research_tasks(id, checkpoint_policy_id);
```

No migration UPDATE/backfill, not even NULL assignments. Existing rows retain
NULL bindings, row versions and historical hashes. Policies are task-owned;
only one bind is allowed. A proposed extension budget is a distinct unbound row.
Scope rows require the same receipt as their newly inserted checkpoint policy.
A3 requires explicit Human binding, nonempty datasets/metrics/code paths, finite
caps and deny/allowlist network configuration. Paths are normalized relative POSIX
paths without empty segments, '.', '..', glob, backslash, absolute prefixes or
symlink escape; host entries are lowercase exact ASCII DNS names (no URL, port,
IP literal, wildcard or suffix match). Empty allowlist denies all network.
All arrays are one-dimensional sorted duplicate-free sets, checked by §3 guards.
At most 256 entries in each array or scope relation per policy; strings ≤512
characters. Deny non-NFC/blank entries. Non-A3 policies have no scope rows.
DatasetSnapshot is immutable, has content_hash and dataset_id, and has no status
or frozen_at: validate its owning datasets.project_id. Metrics require exact
FROZEN/SUPERSEDED version, frozen_at/hash, with metric_definitions.project_id equal
to the task project or NULL (existing global definitions). Do not invent a
DatasetSnapshot frozen_at or metric-version project_id.

### 2.2 Reservation, usage and checkpoint DDL

```sql
CREATE TABLE budget_reservations (
  id uuid NOT NULL PRIMARY KEY,
  research_task_id uuid NOT NULL REFERENCES research_tasks(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL,
  receipt_id uuid NOT NULL,
  budget_id uuid NOT NULL,
  step_id uuid NULL,
  operation_id uuid NOT NULL,
  wall_time_seconds integer NOT NULL CHECK (wall_time_seconds > 0),
  agent_steps bigint NOT NULL CHECK (agent_steps >= 0),
  llm_calls bigint NOT NULL CHECK (llm_calls >= 0),
  search_calls bigint NOT NULL CHECK (search_calls >= 0),
  code_iterations bigint NOT NULL CHECK (code_iterations >= 0),
  experiment_runs bigint NOT NULL CHECK (experiment_runs >= 0),
  tree_nodes bigint NOT NULL CHECK (tree_nodes >= 0),
  gpu_hours numeric(20,6) NOT NULL CHECK (gpu_hours >= 0 AND gpu_hours < 'Infinity'::numeric),
  token_cost numeric(20,6) NOT NULL CHECK (token_cost >= 0 AND token_cost < 'Infinity'::numeric),
  observed_depth integer NOT NULL CHECK (observed_depth >= 0),
  observed_parallel_branches integer NOT NULL CHECK (observed_parallel_branches > 0),
  deadline timestamptz NOT NULL CHECK (deadline > created_at),
  UNIQUE (research_task_id, id),
  UNIQUE (research_task_id, operation_id),
  FOREIGN KEY (research_task_id, receipt_id) REFERENCES research_task_command_receipts(research_task_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (research_task_id, budget_id) REFERENCES execution_budgets(research_task_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (research_task_id, step_id) REFERENCES research_task_steps(research_task_id, id) ON DELETE RESTRICT
);
CREATE INDEX pr304_reservations_receipt ON budget_reservations(research_task_id, receipt_id);
CREATE INDEX pr304_reservations_budget ON budget_reservations(research_task_id, budget_id);
CREATE INDEX pr304_reservations_step ON budget_reservations(research_task_id, step_id);
CREATE INDEX pr304_reservations_time ON budget_reservations(research_task_id, created_at, id);
CREATE INDEX pr304_reservations_deadline ON budget_reservations(deadline, research_task_id, id);

CREATE TABLE budget_usage_records (
  id uuid NOT NULL PRIMARY KEY,
  research_task_id uuid NOT NULL REFERENCES research_tasks(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL,
  receipt_id uuid NOT NULL,
  reservation_id uuid NOT NULL,
  outcome text NOT NULL CHECK (outcome IN ('SUCCEEDED','FAILED','CANCELLED','PRUNED','UNKNOWN')),
  is_final boolean NOT NULL,
  wall_time_seconds integer NOT NULL CHECK (wall_time_seconds >= 0),
  agent_steps bigint NOT NULL CHECK (agent_steps >= 0),
  llm_calls bigint NOT NULL CHECK (llm_calls >= 0),
  search_calls bigint NOT NULL CHECK (search_calls >= 0),
  code_iterations bigint NOT NULL CHECK (code_iterations >= 0),
  experiment_runs bigint NOT NULL CHECK (experiment_runs >= 0),
  tree_nodes bigint NOT NULL CHECK (tree_nodes >= 0),
  gpu_hours numeric(20,6) NOT NULL CHECK (gpu_hours >= 0 AND gpu_hours < 'Infinity'::numeric),
  token_cost numeric(20,6) NOT NULL CHECK (token_cost >= 0 AND token_cost < 'Infinity'::numeric),
  failure_streak integer NOT NULL CHECK (failure_streak >= 0),
  no_improvement_streak integer NOT NULL CHECK (no_improvement_streak >= 0),
  score numeric(20,6) NULL CHECK (score > '-Infinity'::numeric AND score < 'Infinity'::numeric),
  evaluator_version text NULL CHECK (length(btrim(evaluator_version)) BETWEEN 1 AND 128 AND evaluator_version IS NFC NORMALIZED AND lower(btrim(evaluator_version)) NOT IN ('latest','main','master')),
  settled_at timestamptz NOT NULL CHECK (settled_at = created_at),
  CHECK (is_final = (outcome <> 'UNKNOWN')),
  CHECK ((score IS NULL) = (evaluator_version IS NULL)),
  UNIQUE (research_task_id, id),
  UNIQUE (research_task_id, reservation_id, receipt_id),
  FOREIGN KEY (research_task_id, receipt_id) REFERENCES research_task_command_receipts(research_task_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (research_task_id, reservation_id) REFERENCES budget_reservations(research_task_id, id) ON DELETE RESTRICT
);
CREATE UNIQUE INDEX pr304_usage_one_final ON budget_usage_records(research_task_id, reservation_id) WHERE is_final;
CREATE INDEX pr304_usage_receipt ON budget_usage_records(research_task_id, receipt_id);
CREATE INDEX pr304_usage_time ON budget_usage_records(research_task_id, created_at, id);

CREATE TABLE human_checkpoints (
  id uuid NOT NULL PRIMARY KEY,
  research_task_id uuid NOT NULL REFERENCES research_tasks(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL,
  receipt_id uuid NOT NULL,
  step_id uuid NULL,
  checkpoint_type text NOT NULL CHECK (checkpoint_type IN ('plan_review','hypothesis_selection','experiment_approval','budget_extension','code_risk','claim_freeze','manuscript_release','exception')),
  status text NOT NULL CHECK (status IN ('PENDING','APPROVED','REJECTED','MODIFIED','EXPIRED')),
  reason text NOT NULL CHECK (length(btrim(reason)) BETWEEN 1 AND 8192 AND reason IS NFC NORMALIZED),
  requested_at timestamptz NOT NULL CHECK (requested_at = created_at),
  expires_at timestamptz NOT NULL CHECK (expires_at > requested_at),
  responded_at timestamptz NULL,
  responded_by uuid NULL REFERENCES actors(id) ON DELETE RESTRICT,
  response_reason text NULL CHECK (length(btrim(response_reason)) BETWEEN 1 AND 8192 AND response_reason IS NFC NORMALIZED),
  row_version integer NOT NULL CHECK (row_version IN (1,2)),
  response_receipt_id uuid NULL,
  proposed_budget_id uuid NULL,
  CHECK ((status = 'PENDING' AND row_version = 1 AND num_nonnulls(responded_at,responded_by,response_reason,response_receipt_id) = 0)
    OR (status IN ('APPROVED','REJECTED','MODIFIED') AND row_version = 2 AND num_nonnulls(responded_at,responded_by,response_reason,response_receipt_id) = 4 AND responded_at >= requested_at AND responded_at < expires_at)
    OR (status = 'EXPIRED' AND row_version = 2 AND num_nonnulls(responded_at,response_reason,response_receipt_id) = 3 AND responded_at >= expires_at AND responded_by IS NULL)),
  CHECK ((checkpoint_type = 'budget_extension') = (proposed_budget_id IS NOT NULL)),
  UNIQUE (research_task_id, id),
  UNIQUE (research_task_id, proposed_budget_id),
  FOREIGN KEY (research_task_id, receipt_id) REFERENCES research_task_command_receipts(research_task_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (research_task_id, response_receipt_id) REFERENCES research_task_command_receipts(research_task_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (research_task_id, step_id) REFERENCES research_task_steps(research_task_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (research_task_id, proposed_budget_id) REFERENCES execution_budgets(research_task_id, id) ON DELETE RESTRICT
);
CREATE UNIQUE INDEX pr304_checkpoint_one_pending ON human_checkpoints(research_task_id, step_id, checkpoint_type) NULLS NOT DISTINCT WHERE status = 'PENDING';
CREATE INDEX pr304_checkpoint_receipt ON human_checkpoints(research_task_id, receipt_id);
CREATE INDEX pr304_checkpoint_response_receipt ON human_checkpoints(research_task_id, response_receipt_id) WHERE response_receipt_id IS NOT NULL;
CREATE INDEX pr304_checkpoint_step ON human_checkpoints(research_task_id, step_id);
CREATE INDEX pr304_checkpoint_responder ON human_checkpoints(responded_by) WHERE responded_by IS NOT NULL;
CREATE INDEX pr304_checkpoint_time ON human_checkpoints(research_task_id, created_at, id);
CREATE INDEX pr304_checkpoint_expiry ON human_checkpoints(expires_at, research_task_id, id) WHERE status = 'PENDING';
```

### 2.3 Existing receipt/event extensions

NEW safety commands map exactly to NEW event literals:

| Command | Event |
| --- | --- |
| bind_task_policies | POLICIES_BOUND |
| reserve_task_budget | BUDGET_RESERVED |
| settle_task_budget | BUDGET_SETTLED |
| evaluate_task_termination | TERMINATION_EVALUATED |
| request_human_checkpoint | CHECKPOINT_REQUESTED |
| respond_human_checkpoint | CHECKPOINT_RESPONDED |

The following catalog-directed SQL removes only the affected 0077 CHECKs,
without guessing PostgreSQL's generated names. Assert exactly one receipt CHECK
and four task-event CHECKs matched, otherwise abort the migration. The existing
sequence/version, status enum and step-event constraints remain intact.

```sql
DO $$
DECLARE c record; n integer := 0;
BEGIN
  FOR c IN SELECT DISTINCT con.conname FROM pg_constraint con
    JOIN pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = ANY(con.conkey)
    WHERE con.conrelid = 'research_task_command_receipts'::regclass
      AND con.contype = 'c' AND a.attname = 'command_name'
  LOOP
    EXECUTE format('ALTER TABLE research_task_command_receipts DROP CONSTRAINT %I',c.conname);
    n := n + 1;
  END LOOP;
  IF n <> 1 THEN RAISE EXCEPTION '0077 receipt baseline mismatch'; END IF;
  n := 0;
  FOR c IN SELECT DISTINCT con.conname FROM pg_constraint con
    JOIN pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = ANY(con.conkey)
    WHERE con.conrelid = 'research_task_events'::regclass AND con.contype = 'c'
      AND a.attname IN ('event_type','prior_status','new_status','reason')
  LOOP
    EXECUTE format('ALTER TABLE research_task_events DROP CONSTRAINT %I',c.conname);
    n := n + 1;
  END LOOP;
  IF n <> 4 THEN RAISE EXCEPTION '0077 event baseline mismatch'; END IF;
END $$;
ALTER TABLE research_task_command_receipts ADD CONSTRAINT pr304_command_names CHECK (command_name IN (
  'create_research_task','create_task_plan','add_task_step','add_task_step_dependency','seal_task_plan','cancel_research_task',
  'bind_task_policies','reserve_task_budget','settle_task_budget','evaluate_task_termination','request_human_checkpoint','respond_human_checkpoint'));
ALTER TABLE research_task_events
  ADD COLUMN stop_human boolean NOT NULL DEFAULT false,
  ADD COLUMN stop_policy boolean NOT NULL DEFAULT false,
  ADD COLUMN stop_budget boolean NOT NULL DEFAULT false,
  ADD COLUMN stop_repeated_failure boolean NOT NULL DEFAULT false,
  ADD COLUMN stop_no_improvement boolean NOT NULL DEFAULT false,
  ADD COLUMN stop_success boolean NOT NULL DEFAULT false,
  ADD CONSTRAINT pr304_event_names CHECK (event_type IN (
    'CREATED','PLAN_CREATED','STEP_ADDED','DEPENDENCY_ADDED','PLAN_SEALED','CANCELLED',
    'POLICIES_BOUND','BUDGET_RESERVED','BUDGET_SETTLED','TERMINATION_EVALUATED','CHECKPOINT_REQUESTED','CHECKPOINT_RESPONDED')),
  ADD CONSTRAINT pr304_event_states CHECK (
    (event_type = 'CREATED' AND prior_status IS NULL AND new_status = 'CREATED') OR
    (event_type = 'PLAN_CREATED' AND prior_status = 'CREATED' AND new_status = 'PLANNING') OR
    (event_type IN ('STEP_ADDED','DEPENDENCY_ADDED','PLAN_SEALED') AND prior_status = 'PLANNING' AND new_status = 'PLANNING') OR
    (event_type = 'CANCELLED' AND prior_status IN ('CREATED','PLANNING') AND new_status = 'CANCELLED') OR
    (event_type IN ('POLICIES_BOUND','BUDGET_RESERVED','BUDGET_SETTLED','TERMINATION_EVALUATED','CHECKPOINT_REQUESTED','CHECKPOINT_RESPONDED')
      AND prior_status IN ('CREATED','PLANNING','CANCELLED') AND new_status = prior_status)),
  ADD CONSTRAINT pr304_event_prior CHECK (event_type = 'CREATED' OR prior_status IS NOT NULL),
  ADD CONSTRAINT pr304_event_reason CHECK (
    CASE WHEN event_type IN ('CANCELLED','POLICIES_BOUND','BUDGET_RESERVED','BUDGET_SETTLED','TERMINATION_EVALUATED','CHECKPOINT_REQUESTED','CHECKPOINT_RESPONDED')
    THEN reason IS NOT NULL AND length(btrim(reason)) BETWEEN 1 AND 8192 AND reason IS NFC NORMALIZED
    ELSE reason IS NULL END),
  ADD CONSTRAINT pr304_event_stop_slice CHECK (NOT stop_success),
  ADD CONSTRAINT pr304_event_stop_kind CHECK (
    event_type IN ('BUDGET_RESERVED','BUDGET_SETTLED','TERMINATION_EVALUATED') OR
    NOT (stop_human OR stop_policy OR stop_budget OR stop_repeated_failure OR stop_no_improvement OR stop_success));
CREATE INDEX pr304_events_receipt_tuple ON research_task_events(research_task_id, actor_id, command_id, task_row_version);
```

Defaults on event booleans preserve historical planning events without UPDATE;
existing request hashes and event identity remain unchanged. No stop table, stop
JSON or extra receipt-result table is added. Result links are the concrete
same-task receipt_id and response_receipt_id FKs on the eight new tables; original
request and response receipt identities are both preserved. Ordinary planning
commands continue to use only their original result links.

## 3. Function and trigger inventory

All functions are PL/pgSQL, ordinary invoker privilege, no SECURITY DEFINER,
no trigger-acquired advisory lock, no bypass GUC or stored transaction marker.
Trigger functions return trigger; validation helpers return void and the canonical
serialization helper returns text. The following
algorithms are normative function bodies for implementation, not permission to
choose different enforcement. SQLSTATE 23514 uses existing diagnostic constraints
pr301_validation/state/immutable/not_frozen/scope/provenance so the delivered UoW
normalizer preserves §6. Native FK remains 23503. No exception-text parsing.

### 3.1 Existing functions and triggers retained or extended

Forward migration CREATE OR REPLACE, preserving the indicated existing triggers:

| Existing function | Existing trigger / timing | Required delta |
| --- | --- | --- |
| pr301_task_guard() | pr301_task_guard; BEFORE INSERT OR UPDATE OR DELETE ON research_tasks | Preserve identity/material/plan/terminal invariants with the narrow operational bookkeeping exceptions below; prohibit a second task-row write in this transaction. |
| pr301_graph_final_guard() | pr301_task_final; AFTER INSERT OR UPDATE ON research_tasks, DEFERRABLE INITIALLY DEFERRED | Preserve all graph/history/hash checks; call NEW pr304_validate_safety(NEW.id) once. |
| pr301_receipt_complete() | pr301_receipt_complete_commit; AFTER INSERT ON research_task_command_receipts, DEFERRABLE INITIALLY DEFERRED | Preserve original six cases; add §2.3 mapping, result cardinalities and effect checks in §3.4. |

No other existing function or trigger is replaced. Exact retained inventory:
pr301_step_guard / pr301_step_guard; pr301_dependency_guard /
pr301_dependency_guard; pr301_task_input_guard / pr301_task_input_guard;
pr301_step_input_guard / pr301_step_input_guard (all BEFORE INSERT OR UPDATE OR
DELETE on their corresponding existing child tables); pr301_validate_input
(helper, original nine parameters); pr301_receipt_insert_guard /
pr301_receipt_insert (BEFORE INSERT receipts); pr301_event_insert_guard /
pr301_task_event_insert and pr301_step_event_insert (BEFORE INSERT task/step
events); pr301_receipt_link_guard / pr301_receipt_event_insert and
pr301_receipt_step_event_insert (BEFORE INSERT the two existing link tables).
pr301_history_immutable remains attached BEFORE UPDATE OR DELETE as
pr301_task_events_immutable, pr301_step_events_immutable, pr301_receipts_immutable,
pr301_receipt_events_immutable and pr301_receipt_step_events_immutable.
pr301_dependency_acyclic / pr301_dependency_acyclic_commit remains AFTER INSERT
OR UPDATE on research_task_step_dependencies; pr301_parent_acyclic /
pr301_parent_acyclic_commit remains AFTER INSERT OR UPDATE on research_task_steps;
both are DEFERRABLE INITIALLY DEFERRED, row-local reachability checks.
All triggers in this pack are FOR EACH ROW. Retained timings are unchanged.

Task guard additions: INSERT requires three NULL policies and still CREATED at
revision 1. DELETE always rejects. Before UPDATE, select the stored row's xmin;
if `xmin = pg_current_xact_id()::xid`, reject (a task gets exactly one write per
command and one command per transaction, no savepoints). Old immutable material
includes id/project/requester/created/type/objective/strategy/autonomy, started_at,
current_step_id and finished_at except original cancellation. Policies change
only all-NULL to all-set on CREATED/PLANNING. Bound IDs cannot change again.
Permit CREATED→CREATED and sealed PLANNING→PLANNING for safety bookkeeping only;
permit CANCELLED→CANCELLED only for settlement or termination evaluation. These
exceptions change only row_version and, for binding, the three policy columns;
plan_sealed_at, scientific inputs and plan graph remain untouched. Existing cancellation
still works after binding/seal. The deferred receipt guard MUST prove the exact
safety command for each exception; writing a self-transition alone is insufficient.
CANCELLED creation/binding/reservation/request/response remains forbidden.

### 3.2 New immediate guards

NEW functions:

| Function | Contract |
| --- | --- |
| pr304_child_guard() RETURNS trigger | Reject UPDATE/DELETE even no-op on the seven immutable new tables; BEFORE INSERT require fresh owning task and same-task fresh receipt, then check receipt command and validate row-specific scalar material. Scope-dependent policy hashing waits for the one task final check. |
| pr304_checkpoint_guard() RETURNS trigger | INSERT requires PENDING revision 1 and fresh request receipt/task; UPDATE permits exactly one PENDING→final revision 2, with fresh response receipt/task; DELETE and all other changes reject. |
| pr304_canonical_policy_json(p_value jsonb) RETURNS text | Closed transient policy serialization only; exact definition in §5.2. No persistent JSON core. |
| pr304_validate_policy(p_task uuid, p_policy uuid, p_kind text) RETURNS void | Closed p_kind BUDGET/TERMINATION/CHECKPOINT. Validate canonical content hash, typed bounds/sets/scope and exact owning project references. |
| pr304_validate_safety(p_task uuid) RETURNS void | Deferred task-level validation in §3.4; not attached to child triggers. |

NEW immediate trigger inventory (all NOT DEFERRABLE):

```sql
CREATE TRIGGER pr304_budget_guard BEFORE INSERT OR UPDATE OR DELETE ON execution_budgets FOR EACH ROW EXECUTE FUNCTION pr304_child_guard();
CREATE TRIGGER pr304_termination_guard BEFORE INSERT OR UPDATE OR DELETE ON termination_policies FOR EACH ROW EXECUTE FUNCTION pr304_child_guard();
CREATE TRIGGER pr304_checkpoint_policy_guard BEFORE INSERT OR UPDATE OR DELETE ON checkpoint_policies FOR EACH ROW EXECUTE FUNCTION pr304_child_guard();
CREATE TRIGGER pr304_dataset_scope_guard BEFORE INSERT OR UPDATE OR DELETE ON checkpoint_policy_dataset_scopes FOR EACH ROW EXECUTE FUNCTION pr304_child_guard();
CREATE TRIGGER pr304_metric_scope_guard BEFORE INSERT OR UPDATE OR DELETE ON checkpoint_policy_metric_scopes FOR EACH ROW EXECUTE FUNCTION pr304_child_guard();
CREATE TRIGGER pr304_reservation_guard BEFORE INSERT OR UPDATE OR DELETE ON budget_reservations FOR EACH ROW EXECUTE FUNCTION pr304_child_guard();
CREATE TRIGGER pr304_usage_guard BEFORE INSERT OR UPDATE OR DELETE ON budget_usage_records FOR EACH ROW EXECUTE FUNCTION pr304_child_guard();
CREATE TRIGGER pr304_checkpoint_guard BEFORE INSERT OR UPDATE OR DELETE ON human_checkpoints FOR EACH ROW EXECUTE FUNCTION pr304_checkpoint_guard();
```

Immediate guards use cheap indexed owning-row checks, not whole-task scans.
For safety rows, receipt.completed_at and the new created_at/responded_at must
lie between transaction_timestamp() and the guard's clock_timestamp(), with the
required receipt-time equality. Future/backdated caller clocks cannot extend
wall budgets or checkpoint expiry. The receipt-completeness check enforces the
same range for evaluations that create no child rows. Command timestamps are
observations of database time, never evidence supplied by an Agent.
Both owning research_tasks and linked research_task_command_receipts must have
`xmin = pg_current_xact_id()::xid`; the receipt's resulting revision must equal
the task's current revision. Missing/fake/committed owners reject immediately as
IMMUTABLE_RECORD. Scope rows additionally require a policy inserted in this
transaction and identical receipt_id. Request rows only under request command;
responses only under response command; EXPIRED updates only under evaluate command
with database now>=expires_at and no responder. Budget rows only under bind or
extension request; termination/checkpoint policy rows only under bind; reservation
only under reserve; usage only under settle. Checkpoint response's original request
fields, including proposed budget, reason and request receipt, cannot change.
Human response must use the receipt actor, whose existing actors.actor_type is
HUMAN and whose current verified credential, membership and OWNER role remain
valid. DB verifies persisted authority; Application also verifies its trusted
principal. A normal-role SQL writer has no credential bypass into the Application.

Expiry is `requested_at + timeout_seconds * interval '1 second'`; human response
uses fresh clock_timestamp() strictly before expiry. Once elapsed, a response
command fails with no writes. An evaluate command can durably expire all elapsed
PENDING rows in its one task mutation; the EXPIRED response_reason is the NEW
fixed diagnostic `Checkpoint expired.` and responded_by is NULL. Pending expired
rows still occupy the partial unique until evaluation expires them. Querying
expiry never writes. New request after denial/modification/expiry is explicit;
it cannot silently satisfy another request or erase its history.

### 3.3 Exact accounting, autonomy and stop semantics

Pilot budget defaults are 1800 seconds, 50 steps, 50 LLM calls, 20 search calls,
3 code iterations, 5 experiment runs, 10 tree nodes, depth 3, parallelism 1,
GPU 0.000000 hours, token cost 5.000000 USD, hard_stop=true. Termination defaults
are two consecutive same-logical-step failures and two comparable non-improving
iterations, with all three mandatory stops true. Checkpoint default maximum A2,
a3_authorized=false, timeout 86400, required_types=[plan_review], empty scopes,
paths/hosts and network DENY. These defaults enter request material explicitly;
no dummy policy or unpriced production default is inserted by a migration.
pricing_basis must identify an immutable approved pricing schedule. Fake tests
use NEW test-only `fake-usd-v1`; it grants no real adapter admission.

Count fields agent_steps/llm_calls/search_calls/code_iterations/experiment_runs/
tree_nodes, gpu_hours and token_cost are additive. Effective charged total per
reservation is its one final measured vector if present, otherwise its entire
requested vector (including UNKNOWN observations). Sum charged totals across the
active budget. New amount + existing charged <= cap in every additive dimension.
Never subtract UNKNOWN or time out a reservation into a refund. UNKNOWN records
are immutable nonfinal observations and may precede one attributable final
reconciliation; pr304_usage_one_final enforces at most one final, and no further
observations are permitted after final. Repeated observations do not add another
charge or advance failure/progress streaks. A final measurement cannot exceed
its reservation; a later adapter lacking a valid upper bound must deny dispatch.
Excess/unattributable observations fail closed; never truncate measured cost to
fit. Overshoot containment evidence belongs to the later adapter pack.

Decimals are finite, nonnegative, fixed six decimal places; reject excess-scale
public values rather than silently rounding them through numeric(20,6). Adapter
cost/GPU conversion rounds UP to 0.000001 before reservation and attributable
settlement. Exact integer usage never rounds. Failed/pruned/cancelled attempts
retain charged admission counters: final agent_steps, call/cycle/run/node counts
must equal their requested counts, while variable GPU/cost/time may reconcile
downward with trusted evidence. Success is not required for charging a call.
Retries require a new operation UUID and another charged attempt. Unique task /
operation UUID prevents a different command from charging that operation again;
only exact command receipt replay is idempotent.

Wall time is a gauge of database elapsed UTC, not sum of worker times. Its origin
is the earliest reservation.created_at, immutable thereafter, never task.started_at
(which remains NULL in this slice). It includes Human waits and stops. Admission
requires now < origin+cap, deadline <= origin+cap, and deadline <= now+requested
wall_time_seconds; the first reservation uses now as origin. All reservations
bound duration, positive wall_time_seconds and future deadline. Expiry stops
new spend but does not settle external work. No reservation means elapsed=0.
Depth is the proposed node's actual parent depth (root=0); parallelism is one
plus number of not-final reservations. Observed gauges must match DB-derived
values, within max_tree_depth/max_parallel_branches. Depth/occupancy are never
summed as costs. No step implies depth=0. UNKNOWN retains occupancy until final.

Equality is admissible. A reservation that exactly consumes the last additive
unit succeeds and its event records budget stop for subsequent work. At/above a
positive cap stops subsequent admission; a zero GPU cap only forbids positive
GPU requests, and never stops CPU-only work. Stop is sticky, even if settlement
later releases a conservative variable charge. Settlements and termination
checks remain allowed after stop/cancellation; new reservations do not.

Final failures count consecutively per reservation.step_id (NULL is the one
explicit task-level logical step), ordered by receipt.resulting_row_version.
SUCCEEDED resets that step's failure streak; FAILED increments; CANCELLED/PRUNED
retain it and UNKNOWN does not advance it. Progress counts only completed
SUCCEEDED comparable iterations under the termination policy's exact metric,
direction and evaluator_version; strict improvement resets no-improvement to 0;
first comparable score is the baseline at 0; ties/worse increment. Other outcomes
retain its prior value. Comparisons never cross steps, metrics or evaluators.
No approved metric/evaluator or missing score denies autonomous code/experiment/
tree iteration; other bounded work can be admitted. Score is operational,
never a Measurement. Streaks in usage rows are DB-recomputed, not caller-supplied.

All currently detected causes persist as typed event flags. Priority is human,
policy, budget, repeated failure, no improvement, success. Primary reason is the
first true flag; all others remain visible. Historical OR of flags is the sticky
stop, even when a later non-evaluation event has false flags. success remains
false in this slice. Human stop requires Human OWNER; policy violation requires
a trusted consumer observation. Evaluate recomputes budget/streak causes from
persisted accounting and database clock; no caller invents them. A newly recorded
stop is a successful command/event/receipt, never an exception that rolls it back.
A subsequent reserve denies without writing. An evaluated no-stop is also a
successful recorded evaluation.

A0 suggestion and A1 draft work still require resource bounds; A1 cannot freeze.
A2 additionally requires sealed Human-approved plan and owning frozen scientific
inputs before real execution. A3 additionally requires exact explicit bounded
scope. Neither seal nor checkpoint is a frozen scientific spec or an Approval.
Required checkpoints are conjunctive: plan_review before dispatch; experiment_approval
for experiment runs; code_risk for code cycles; hypothesis_selection before a
selection; claim_freeze/manuscript_release before corresponding actions, with
owning scientific governance independently required. Policy-required types add
to these minimum gates. A task-level APPROVED checkpoint covers task-level gates;
step-level gates require that exact step, never another step. Any required pending,
expired, rejected or modified request blocks; latest request by created_at/id must
be APPROVED for each required scope/type. An older approval cannot bypass a new
unanswered or denied request. Budget-extension approval never grants spend.

This PR exposes reserve/settle only to an in-process deterministic fake consumer
via a trusted injected repository-port capability. It is not a bool, token,
actor type, flag or field supplied in public DTOs. Public HTTP/CLI reserve/settle
and trusted-policy observations fail closed until a later consumer authorization
pack. Fake calls exercise durable accounting without external dispatch. They
never enable the existing reserved execution commands, even with all policies
and approvals present. Enforcement of prerequisites at a real gateway remains
an explicit later activation gate.

### 3.4 Deferred final-state and receipt guards: exactly once

Every successful old or new command writes research_tasks EXACTLY ONCE and
inserts EXACTLY ONE research_task_command_receipts row. Replay/denial write
neither. Only existing pr301_task_final and pr301_receipt_complete_commit do
whole-task final-state and whole-receipt validation: once each per command,
regardless of child count, multiple flushes or checkpoint expirations. Extend
their functions, not their attachment sites. No new deferred child/history
whole-state triggers; original per-row graph-cycle checks remain unchanged.

Use the migration 0057 established check `xmin = pg_current_xact_id()::xid` in
all immediate guards, including scope rows and checkpoint response receipts.
No forgeable session marker, custom transaction-ID column, GUC, pg_trigger_depth
bypass or superuser trigger disabling. A new child cannot attach to an old
receipt; a response uses its NEW response receipt, preserving its OLD request
receipt. This forces the owning task/receipt writes that queue the two checks.
No whole-task revalidation is run per reservation/usage/checkpoint/history row.

pr304_validate_safety, called once by pr301_graph_final_guard, verifies:

- All-NULL/all-set and same-task policy bindings. CREATED/PLANNING may remain
  NULL. Any future executable status must have all bindings; here the unchanged
  planning-only CHECK rejects such statuses first. Reservations/settlements and
  bound checkpoint requests require complete active bundle in this slice.
- Exactly one active bundle, immutable policy content/hash, exact A3 scope and
  saved scientific hashes, no orphan new policies except extension budgets
  owned by a budget_extension checkpoint. Policies inserted by bind equal all
  three task pointers; no extra policy rows under that receipt.
- Total final measured plus outstanding worst-case amounts <= every cap, all
  gauge/deadline rules, measurements <= reservation, correct operation identity,
  no post-final observation, accurate per-step streaks, all receipt-linked results.
- Historical stop monotonicity and admission order: no reservation after a prior
  stop, or while contemporaneously exhausted/blocked; a newly exhausted final
  unit has a matching stop_budget event. Recompute against history up to each
  relevant receipt revision, not today's balance as a substitute for prior
  admission validity. Final settlement can occur after stop.
- Pending/final checkpoint shapes, fixed expiry, immutable request provenance,
  authorized response, extension-budget separation, blocked rejected/modified/
  expired gates. No scientific table is mutated by any safety command.

pr301_receipt_complete adds exactly these result cardinalities, with the §2.3
matching event, same actor/command/task/revision, one task event and no step events:

| Safety command | Rows linked by this receipt |
| --- | --- |
| bind_task_policies | One execution budget, one termination policy, one checkpoint policy; exactly its declared scope rows. All three pointers equal those IDs. |
| reserve_task_budget | One reservation, no other new child result. |
| settle_task_budget | One usage record for the named reservation, no other child result. |
| evaluate_task_termination | Zero new policy/accounting/request rows; zero or more checkpoint EXPIRED transitions using this response receipt, exactly the pending elapsed set at evaluation time. |
| request_human_checkpoint | One checkpoint; exactly one new proposed execution budget iff type=budget_extension, never an active replacement. |
| respond_human_checkpoint | One checkpoint transitioned with this response receipt, no new request/policy/usage row. |

Reject unrelated or additional result rows, mismatch of event type/reason/time,
wrong task revision, naked revision bumps, counterfeit self-transitions and
binding changes attached to a planning receipt. For safety commands event time,
receipt.completed_at and newly created/response row times are the same observed
DB time; event.reason equals command reason. Sealed-plan and CANCELLED operational
exceptions in §3.1 are valid only with the exact linked safety effect above.
For old commands, preserve original cardinalities and require no new safety
effects. Creation must still start unbound. Current projections are never saved
as replay results. Force SET CONSTRAINTS ALL IMMEDIATE under locks before commit.

## 4. First SHARE, advisory keys and transaction recipes

Connection startup lock_timeout=10s, statement_timeout=30s, connect_timeout=10;
use existing research_task_uow_factory / SqlAlchemyUnitOfWork.begin_research_task.
Restore pool defaults on return; no preliminary SET LOCAL, auth SELECT, receipt
lookup, advisory lock, write or autoflush. First Application SQL is exactly:

```sql
LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts,
claim_versions, claims, hypothesis_versions, hypotheses,
literature_source_project_links, literature_sources, manuscript_versions,
project_memberships, project_role_assignments, projects, publications,
research_question_versions, research_questions, source_versions IN SHARE MODE;
```

Do not narrow the 18-table SHARE or add task-table SHARE/lock upgrades. Then:

1. `SELECT rb_phase2_lock_project(:project_id)` (existing project lock).
2. `SELECT pg_advisory_xact_lock(hashtextextended(:key,0))` with exact key
   `pr301:command:<project_uuid>:<authenticated_actor_uuid>:<command_uuid>`.
3. Same SQL with exact key `pr301:task:<task_uuid>`. UUID text is lowercase canonical.
4. research_tasks by id FOR UPDATE; research_task_steps by id FOR UPDATE.
5. Read research_task_step_dependencies by predecessor_id/dependent_id;
   research_task_inputs and research_task_step_inputs by id, as delivered.
6. Read/lock new rows in this exact table order, then ascending primary key id:
   budget_reservations, budget_usage_records, checkpoint_policies,
   checkpoint_policy_dataset_scopes, checkpoint_policy_metric_scopes,
   execution_budgets, human_checkpoints, termination_policies. Immutable rows
   need only reads; human_checkpoints to update use FOR UPDATE. Never acquire
   new advisory locks after these row locks. Scope reads add no SHARE inventory.
7. After EVERY blocking wait, fresh credentials, current membership/role,
   Human type when needed, scope, archive state, exact input hashes and DB
   clock/expiry checks. Authorize current read before existence or conflict
   disclosure. Look up receipt; identical normalized hash returns original
   result BEFORE CAS/write-authority/state/expiry checks. Different hash raises
   IDEMPOTENCY_CONFLICT. No receipt: require current write authority and CAS.
8. Validate the command-specific predicates below. Choose one fresh DB time for
   the command; revalidate expiry at the actual response UPDATE. No network,
   provider, artifact-store or cancellation I/O occurs under any locks.
9. Write task row once (revision+1, optional binding). Insert receipt. Flush.
   Insert policies, then scope relations; or reservation/usage/checkpoint; or
   update checkpoint response/expiry. Insert task event, then existing concrete
   receipt/event link. New rows reference that fresh receipt. Flush as needed.
10. SET CONSTRAINTS ALL IMMEDIATE, commit once, return immutable saved result.
    Any denial/constraint failure rolls everything back. No nested UoW/savepoint.

Original planning commands retain their delivered child/event ordering. There
is no new advisory namespace: old/new commands must exclude each other.
Only SQLSTATE 40001/40P01 permits at most THREE TOTAL fresh whole attempts with
identical command identity/material and fresh authorization. 55P03/57014 never
automatically retry. Lost/uncertain commit reconciles exact original receipt
in a fresh formal read; never assume rollback or issue a new command UUID.

| Command (NEW) | Additional transaction steps before common writes |
| --- | --- |
| bind_task_policies | Human OWNER; nonterminal CREATED/PLANNING, even sealed; all existing bindings NULL; validate complete policy bundle and hashes, A3 references and scope; set three pointers together. Seal/graph unchanged. |
| reserve_task_budget | Trusted fake consumer only in this slice; complete bundle, nonterminal task; check ceiling, required gates, sealed/approved plan and exact inputs for A2/A3; recompute all charges/gauges/deadlines/stop with now; validate unique operation and requested worst case. Reserve atomically; if equality exhausts a bound record its stop in this successful reservation event. |
| settle_task_budget | Trusted fake consumer; same-task reservation under active budget, no final settlement; verify bounded attributable vector/outcome/score; derive streaks; UNKNOWN retains full vector. Recompute all causes and persist them on settlement event. Permit stop/CANCELLED bookkeeping with unchanged status/material. |
| evaluate_task_termination | Entitled Human OWNER for human_stop; trusted fake consumer for policy_violation; an entitled Human OWNER can request ordinary deterministic evaluation. Recompute current persisted causes and sticky history; expire elapsed pending checkpoints in id order; append event even if no stop. CANCELLED may only gain bookkeeping, never resume. |
| request_human_checkpoint | Human OWNER or trusted consumer; nonterminal with bound checkpoint policy; check one-open uniqueness and exact same-task step. For extension require typed new budget ID/content and explicit reason; it must be new, unbound and linked only to this checkpoint. Derive fixed expiry; persist PENDING. |
| respond_human_checkpoint | Human OWNER; nonterminal; exact checkpoint PENDING, expected checkpoint row_version=1, DB now<expiry; response APPROVED/REJECTED/MODIFIED only; preserve request and record response receipt actor/time/reason. MODIFIED carries no replacement command or payload. |

Queries get_task_safety / get_task_checkpoint_history and explicit receipt lookup
call existing begin_formal_read BEFORE any SQL. Use one REPEATABLE READ READ ONLY
snapshot, autoflush disabled, no row/SHARE/advisory lock, nested session or write.
Entitlement, policies, balances, sticky stops, scope hashes and checkpoint expiry
projection come from that one snapshot. Capture `transaction_timestamp()` for the
snapshot's time projection; a later mutation always checks clock_timestamp()
again. Reads do not promise visibility of later revocation. History sorts
created_at/id. Expiry projection includes effective_status=EXPIRED while stored
status may remain PENDING; no implicit UPDATE during query.

## 5. Closed DTOs, commands, queries and hashing

Keep existing TaskCommand, CommandResult, create_research_task material/version 1
and its three fixed hashes unchanged. NEW SafetyCommand is a separate closed
immutable envelope. No caller-supplied actor, trusted flag, created/responded
clock, status, calculated streaks, hash, row version result or arbitrary payload.
HTTP and CLI share Application services and immutable DTOs; never expose ORM.
Unknown fields and extra nested fields reject. All defaults and NULLs below are
material. Reject bool in integer fields, nonfinite numbers and live/latest refs.

### 5.1 Exact fields and transports

All names in this table are NEW unless explicitly marked existing. Argument
names match §2 column names; aliases are not accepted.

| Type | Exact fields |
| --- | --- |
| SafetyCommand | project_id:UUID, task_id:UUIDv7, command_id:UUID, expected_row_version:positive int, command_name:one of §2.3, arguments:exact associated argument type. Authenticated context is passed separately by the boundary. |
| BudgetSpec | max_wall_time_seconds, max_agent_steps, max_llm_calls, max_search_calls, max_code_iterations, max_experiment_runs, max_tree_nodes, max_tree_depth, max_parallel_branches, max_gpu_hours, max_token_cost, currency, pricing_basis, hard_stop. Types, bounds and defaults per §§2–3; all fields material after default expansion. |
| TerminationSpec | repeated_failure_threshold=2, max_no_improvement_iterations=2, budget_stop=true, human_stop=true, policy_stop=true, score_metric_version_id=NULL, score_direction=NULL, evaluator_version=NULL; min_progress_enabled=false, min_progress_score=NULL, duplicate_hypothesis_enabled=false, duplicate_hypothesis_threshold=NULL, confidence_stop_enabled=false, confidence_stop_threshold=NULL, success_condition_enabled=false, success_condition=NULL. Types/checks per DDL. |
| CheckpointPolicySpec | required_types=[plan_review], timeout_seconds=86400, maximum_autonomy=A2, a3_authorized=false, allowed_dataset_snapshot_ids=[], allowed_metric_version_ids=[], allowed_code_paths=[], network_mode=DENY, allowed_network_hosts=[]. Scientific references are exact UUIDs; content hashes are resolved by Application and saved in scope rows. |
| ResourceVector | wall_time_seconds:positive int (nonnegative for measurement), agent_steps:nonnegative int, llm_calls:nonnegative int, search_calls:nonnegative int, code_iterations:nonnegative int, experiment_runs:nonnegative int, tree_nodes:nonnegative int, gpu_hours:exact decimal, token_cost:exact decimal. No field omitted. |
| BindPoliciesArguments | budget_id:UUIDv7, budget:BudgetSpec, termination_policy_id:UUIDv7, termination:TerminationSpec, checkpoint_policy_id:UUIDv7, checkpoint:CheckpointPolicySpec, reason:nonblank NFC text ≤8192. |
| ReserveBudgetArguments | operation_id:UUIDv7, step_id:UUIDv7 or NULL, resources:ResourceVector, observed_depth:nonnegative int, observed_parallel_branches:positive int, deadline_seconds:positive int, reason:NFC text ≤8192. Deadline is DB now+deadline_seconds, never caller timestamp; duration <= resources.wall_time_seconds and remaining wall bound. Gauges are assertions rederived from DB. |
| SettleBudgetArguments | reservation_id:UUIDv7, measured:ResourceVector, outcome:SUCCEEDED/FAILED/CANCELLED/PRUNED/UNKNOWN, score:decimal or NULL, evaluator_version:text or NULL, reason:NFC text ≤8192. Trusted consumer input only; is_final and streaks are derived. UNKNOWN measured vector must equal reserved worst case; score/evaluator NULL. |
| EvaluateTerminationArguments | human_stop:bool=false, policy_violation:bool=false, reason:NFC text ≤8192. Trusted context required for policy_violation; no caller-supplied budget/streak/success flags. |
| RequestCheckpointArguments | checkpoint_id:UUIDv7, step_id:UUIDv7 or NULL, checkpoint_type:§2 enum, reason:NFC text ≤8192, proposed_budget_id:UUIDv7 or NULL, proposed_budget:BudgetSpec or NULL. Both proposed fields non-NULL iff budget_extension. |
| RespondCheckpointArguments | checkpoint_id:UUIDv7, expected_checkpoint_row_version:positive int, response:APPROVED/REJECTED/MODIFIED, reason:NFC text ≤8192. |
| TaskSafetyRead | task_id, task_row_version, budget_policy_id/termination_policy_id/checkpoint_policy_id (nullable), budget:BudgetPolicyRead or NULL, termination:TerminationPolicyRead or NULL, checkpoint_policy:CheckpointPolicyRead or NULL, consumed:ResourceVector, reserved:ResourceVector, remaining:ResourceVector, elapsed_wall_seconds:decimal, depth:int, parallel_branches:int, stop_causes:ordered tuple, primary_stop_cause:enum or NULL, required_gates:GateRead tuple, unmet_prerequisites:string tuple, execution_enabled=false. ResourceVector wall value in read totals is nonnegative; depth/parallel are separate gauges. |
| BudgetPolicyRead | id, research_task_id, created_at, receipt_id, content_hash, hash_scheme and every BudgetSpec field. |
| TerminationPolicyRead | id, research_task_id, created_at, receipt_id, content_hash, hash_scheme and every TerminationSpec field. score_metric_version_id is the concrete column, never a free text metric name. |
| CheckpointPolicyRead | id, research_task_id, created_at, receipt_id, content_hash, hash_scheme, every CheckpointPolicySpec field, dataset_scope:ScopeRead tuple, metric_scope:ScopeRead tuple. |
| ScopeRead | id, research_task_id, created_at, receipt_id, checkpoint_policy_id, exact referenced ID (dataset_snapshot_id for dataset scope, metric_definition_version_id for metric scope), content_hash. Distinct closed dataset/metric variants; no target_type/target_id persistence. |
| GateRead | step_id nullable, checkpoint_type, checkpoint_id nullable, effective_status nullable, satisfied:bool, reason:string. Missing gate has no fabricated checkpoint ID. |
| CheckpointRead | Every human_checkpoints column from §2.2, plus effective_status:checkpoint enum. Preserve original status, request receipt/reason and exact response provenance; proposed budget uses BudgetPolicyRead or NULL in a separate proposed_budget field. |
| CheckpointHistoryRead | task_id, task_row_version, checkpoints:CheckpointRead tuple in created_at/id order. |
| SafetyCommandResult | command_result:existing CommandResult; budget_ids, termination_policy_ids, checkpoint_policy_ids, dataset_scope_ids, metric_scope_ids, reservation_ids, usage_record_ids, requested_checkpoint_ids, responded_checkpoint_ids:immutable UUID tuples recovered from concrete receipt FKs, sorted by UUID. No current projection is required. |

NEW result IDs are generated by Application except proposed policy/checkpoint IDs
and operation_id explicitly in arguments. Reservation/usage/scope row IDs are not
request material. Extend existing TaskRead only with optional budget_policy_id,
termination_policy_id, checkpoint_policy_id defaults NULL. Its existing
execution_enabled=false stays. Safety fields do not alter old request hashes.

get_task_safety and get_task_checkpoint_history accept only project_id/task_id
plus trusted principal. No query mutates expiry or acknowledges a stop. Safety
consumed sums final measurements; reserved sums not-final worst cases; remaining
is cap minus both for additive dimensions. Wall fields in consumed/reserved/
remaining are respectively elapsed, maximum outstanding remaining duration and
max(0,cap-elapsed); they are labeled gauges and NOT added as accounting costs.
Before any bundle, resource values are zero, policies NULL and missing-bindings
prerequisite retained. Other unmet labels remain the existing execution/gateway/
recovery diagnostics. Stop cause literals NEW: HUMAN_STOP, POLICY_VIOLATION,
BUDGET_EXHAUSTED, REPEATED_FAILURE, NO_IMPROVEMENT, SUCCESS, in that priority.

NEW HTTP actions under existing /research-tasks/{id}: `:bind-policies`,
`:reserve-budget`, `:settle-budget`, `:evaluate-termination`,
`/checkpoints` POST and `/checkpoints/{checkpoint_id}:respond` POST;
GET `/safety` and `/checkpoints` for the two reads. Path IDs must equal body IDs.
CLI existing research-tasks group gains bind-policies, reserve-budget,
settle-budget, evaluate-termination, request-checkpoint, respond-checkpoint,
safety, checkpoint-history. Reserve/settle public transport stays denied as
specified in §3.3; fake consumer calls the same Application boundary with trusted
in-process capability. Never deserialize or expose that capability as a field.

### 5.2 Exact material and policy hashing

NEW request material has exactly these top-level keys:

```json
{"type":"SafetyCommand","material_version":1,"command_name":"<name>","project_id":"<uuid>","actor_id":"<authenticated uuid>","command_id":"<uuid>","task_id":"<uuid>","expected_row_version":1,"arguments":{}}
```

Hash with existing canonical_json_bytes and sha256_canonical_json, scheme
sha256-cjson-v1. NFC-normalize all text BEFORE serialization (the foundation does
not normalize). UUIDs lowercase canonical; decimals fixed SIX-place strings,
including zero as "0.000000"; integers remain JSON integers. Sort set arrays by
canonical string (required_types, paths, hosts and exact reference IDs), rejecting
duplicates before sorting. All optional defaults and NULLs are included. Hash
trusted observation input on settlement, not subsequently calculated totals,
streaks or result fields. Exclude request/correlation IDs, generated timestamps,
provider metadata, receipt/result IDs, derived status and saved scientific hashes.
Caller-proposed policy/checkpoint IDs ARE material. deadline_seconds is material;
derived deadline timestamp is not. No arbitrary JSON command variant.

Policy hashes use NEW envelopes with exactly type, material_version=1, content:
ExecutionBudgetPolicy / TerminationPolicy / CheckpointPolicy respectively.
content is exactly expanded BudgetSpec / TerminationSpec / CheckpointPolicySpec.
For CheckpointPolicy ONLY, replace allowed_dataset_snapshot_ids with
allowed_dataset_snapshots:[{id,content_hash}] and allowed_metric_version_ids with
allowed_metric_versions:[{id,content_hash}], sorted by id from exact persisted
references. These two member names are NEW hash-only fields, not DB columns.
Include all remaining spec fields unchanged. Exclude row/task/receipt IDs and
clock fields; policy content, not row identity, is hashed. No old hash migration.
pr304_validate_policy independently reconstructs the content from stored columns
and scope relations. Decimal columns become strings using
`to_char(value, 'FM99999999999990.000000')`; optional decimals stay NULL. Other
scalar types retain their types. Scope content hashes come from the exact
referenced canonical rows, compared against saved scope hashes. For each policy,
start with to_jsonb(policy_row) minus id/research_task_id/created_at/receipt_id/
content_hash/hash_scheme, replace decimal members as above, and for checkpoint
policies add the two sorted reference/hash arrays (empty arrays when absent).
required_types/paths/hosts must already be normalized sorted sets. The persisted
column score_metric_version_id is the TerminationSpec member of that same name.
Thus the exact object contains only §5.1 fields, with §5.2 scope substitutions.
Construct jsonb_build_object('type', the exact policy envelope literal,
'material_version', 1, 'content', content). Compare stored content_hash to
`encode(sha256(convert_to(pr304_canonical_policy_json(envelope),'UTF8')),'hex')`.
Use PostgreSQL's built-in bytea sha256; no pgcrypto extension or dependency.
The transient JSON serialization is a hash encoding, not a canonical JSON schema.

NEW exact helper definition (no trigger attachment):

```sql
CREATE FUNCTION pr304_canonical_policy_json(p_value jsonb) RETURNS text
LANGUAGE plpgsql IMMUTABLE STRICT AS $$
DECLARE result text;
BEGIN
  CASE jsonb_typeof(p_value)
  WHEN 'object' THEN
    SELECT '{' || coalesce(string_agg(to_jsonb(e.key)::text || ':' ||
      pr304_canonical_policy_json(e.value), ',' ORDER BY e.key COLLATE "C"),'') || '}'
      INTO result FROM jsonb_each(p_value) e;
  WHEN 'array' THEN
    SELECT '[' || coalesce(string_agg(pr304_canonical_policy_json(e.value),
      ',' ORDER BY e.ordinality),'') || ']'
      INTO result FROM jsonb_array_elements(p_value) WITH ORDINALITY e(value,ordinality);
  WHEN 'number' THEN
    IF p_value::text !~ '^-?(0|[1-9][0-9]*)$' THEN
      RAISE EXCEPTION 'integer policy JSON number required'
        USING ERRCODE='23514', CONSTRAINT='pr301_validation';
    END IF;
    result := p_value::text;
  ELSE result := p_value::text;
  END CASE;
  RETURN result;
END $$;
```

Only closed policy objects reach this helper; object keys are the ASCII member
names above. UTF-8 database encoding is required. Native jsonb scalar quoting
must match the foundation for all admitted NFC strings, including control
character escapes; cross-layer fixtures verify this rather than accepting
jsonb::text's object spacing. No caller-provided digest is authoritative.

Replay uses existing project/actor/command uniqueness, saved hash/material_version
and same-task receipt effects. Current read entitlement is mandatory; exact replay
precedes write-role, task/checkpoint CAS, state and expiry checks. A previously
successful response replay after expiry returns its saved checkpoint ID even if
OWNER write authority was removed but read entitlement remains. Changed material
conflicts after read entitlement. No response/reservation/charge repeats. Explicit
uncertain-commit lookup uses the original identity in a new begin_formal_read.

### 5.3 Fixed request-hash vectors

Three vectors are computed with the repository interpreter and foundation
modules, not a reimplementation. The complete canonical UTF-8 texts and outputs
below are the actual throwaway computation. Vector 1 binds the default bundle;
vector 2 reserves exact decimals; vector 3 responds to an extension checkpoint
(the response's budget intent never substitutes for a new task/budget command).
All NULLs/defaults are included.

Vector 1, complete input / canonical UTF-8 text:

```json
{"actor_id":"01900000-0000-7000-8000-000000000002","arguments":{"budget":{"currency":"USD","hard_stop":true,"max_agent_steps":50,"max_code_iterations":3,"max_experiment_runs":5,"max_gpu_hours":"0.000000","max_llm_calls":50,"max_parallel_branches":1,"max_search_calls":20,"max_token_cost":"5.000000","max_tree_depth":3,"max_tree_nodes":10,"max_wall_time_seconds":1800,"pricing_basis":"fake-usd-v1"},"budget_id":"01900000-0000-7000-8000-000000000010","checkpoint":{"a3_authorized":false,"allowed_code_paths":[],"allowed_dataset_snapshot_ids":[],"allowed_metric_version_ids":[],"allowed_network_hosts":[],"maximum_autonomy":"A2","network_mode":"DENY","required_types":["plan_review"],"timeout_seconds":86400},"checkpoint_policy_id":"01900000-0000-7000-8000-000000000012","reason":"Café pilot limits.","termination":{"budget_stop":true,"confidence_stop_enabled":false,"confidence_stop_threshold":null,"duplicate_hypothesis_enabled":false,"duplicate_hypothesis_threshold":null,"evaluator_version":null,"human_stop":true,"max_no_improvement_iterations":2,"min_progress_enabled":false,"min_progress_score":null,"policy_stop":true,"repeated_failure_threshold":2,"score_direction":null,"score_metric_version_id":null,"success_condition":null,"success_condition_enabled":false},"termination_policy_id":"01900000-0000-7000-8000-000000000011"},"command_id":"01900000-0000-7000-8000-000000000004","command_name":"bind_task_policies","expected_row_version":1,"material_version":1,"project_id":"01900000-0000-7000-8000-000000000001","task_id":"01900000-0000-7000-8000-000000000003","type":"SafetyCommand"}
```

Output request_hash: `89dd196e873985a5caffb868135bf79efc841f387d1b8836fa5b7e27fc19313e`.

Vector 2, complete input / canonical UTF-8 text:

```json
{"actor_id":"01900000-0000-7000-8000-000000000002","arguments":{"deadline_seconds":60,"observed_depth":0,"observed_parallel_branches":1,"operation_id":"01900000-0000-7000-8000-000000000020","reason":"Bounded fake call.","resources":{"agent_steps":1,"code_iterations":0,"experiment_runs":0,"gpu_hours":"0.000000","llm_calls":1,"search_calls":0,"token_cost":"0.125000","tree_nodes":0,"wall_time_seconds":60},"step_id":"01900000-0000-7000-8000-000000000021"},"command_id":"01900000-0000-7000-8000-000000000005","command_name":"reserve_task_budget","expected_row_version":4,"material_version":1,"project_id":"01900000-0000-7000-8000-000000000001","task_id":"01900000-0000-7000-8000-000000000003","type":"SafetyCommand"}
```

Output request_hash: `10710e357af6f0e4ec592ba079aae570a60e78b2b26e85b82259a74ba935c0ab`.

Vector 3, complete input / canonical UTF-8 text:

```json
{"actor_id":"01900000-0000-7000-8000-000000000002","arguments":{"checkpoint_id":"01900000-0000-7000-8000-000000000030","expected_checkpoint_row_version":1,"reason":"Extension intent only; new task required.","response":"APPROVED"},"command_id":"01900000-0000-7000-8000-000000000006","command_name":"respond_human_checkpoint","expected_row_version":7,"material_version":1,"project_id":"01900000-0000-7000-8000-000000000001","task_id":"01900000-0000-7000-8000-000000000003","type":"SafetyCommand"}
```

Output request_hash: `a364746081f6cfe74e4102f9efd1f2da2751311a05228f748d06dd4853df687e`.

Complete extension request envelope (fourth shape example; no fourth hash
vector computed, per the three-vector authoring scope):

```json
{"actor_id":"01900000-0000-7000-8000-000000000002","arguments":{"checkpoint_id":"01900000-0000-7000-8000-000000000030","checkpoint_type":"budget_extension","proposed_budget":{"currency":"USD","hard_stop":true,"max_agent_steps":50,"max_code_iterations":3,"max_experiment_runs":5,"max_gpu_hours":"0.000000","max_llm_calls":50,"max_parallel_branches":1,"max_search_calls":20,"max_token_cost":"5.000000","max_tree_depth":3,"max_tree_nodes":10,"max_wall_time_seconds":1800,"pricing_basis":"fake-usd-v1"},"proposed_budget_id":"01900000-0000-7000-8000-000000000031","reason":"Request continuation budget intent.","step_id":null},"command_id":"01900000-0000-7000-8000-000000000007","command_name":"request_human_checkpoint","expected_row_version":6,"material_version":1,"project_id":"01900000-0000-7000-8000-000000000001","task_id":"01900000-0000-7000-8000-000000000003","type":"SafetyCommand"}
```

Computation command:
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -` (throwaway stdin).
The script constructed the closed dictionaries above, NFC-normalized vector 1's
initial decomposed Cafe\u0301 text, called canonical_json_bytes(v).decode('utf-8')
and str(sha256_canonical_json(v)) for each of the three vectors. Both inputs and
outputs are pasted in full. No committed script or fixture was created. Future
fixtures must also assert array-order independence, duplicate rejection, extension
request hashing and all three unchanged PR3-01 hashes.

## 6. Existing ErrorCode mapping

Existing enum and transport maps are foundation/errors.py, api/errors.py _STATUS,
cli/errors.py CLI_EXIT_CODES. Add no safety-specific public code. Guard diagnostic
names remain existing pr301_* strings interpreted by the delivered research-task
UoW. NEW reason labels are details only, never new enums.

| Existing code | HTTP / CLI exit | Mapping |
| --- | --- | --- |
| VALIDATION_ERROR | 422 / 2 | Closed shapes, fields, decimals, scale, bounds, duplicate set/operation input, evaluator observations, bad gauges, SQL 23502/23514 and scoped native uniqueness errors. pr301_validation. |
| AUTHENTICATION_REQUIRED | 401 / 3 | Missing/unverified principal. |
| FORBIDDEN | 403 / 3 | Revoked credentials/entitlement, wrong project, archive write, Agent human action, untrusted consumer or scope escalation; pr301_scope. |
| NOT_FOUND | 404 / 3 | Entitled exact task/policy/checkpoint/reservation missing. |
| INVALID_STATE_TRANSITION | 409 / 4 | Missing bundle, exhaustion/stop, checkpoint blocking/expiry/already answered, disabled execution, unsupported optional evaluator; pr301_state. |
| IMMUTABLE_RECORD | 409 / 4 | Policy/history no-op UPDATE/DELETE, rebinding, sealed graph/terminal material, child attach to committed receipt; pr301_immutable. |
| CONCURRENT_MODIFICATION | 409 / 4 | Stale task/checkpoint revision, exhausted 40001/40P01 attempts, 55P03/57014 timeout; occupied generated/proposed row ID after entitlement. |
| IDEMPOTENCY_CONFLICT | 409 / 4 | Same project/actor/command identity, different normalized hash after current read entitlement. |
| REFERENTIAL_INTEGRITY_ERROR | 409 / 5 | Same-task FK contradiction or native 23503. |
| VERSION_NOT_FROZEN | 409 / 4 | Scope/input metric or scientific version not frozen; pr301_not_frozen. |
| FROZEN_REFERENCE_REQUIRED | 409 / 5 | Live/latest unresolved reference; malformed UUID is validation. |
| PROVENANCE_CLOSURE_VIOLATION | 409 / 5 | Persisted exact scope/input/policy hash contradiction; pr301_provenance. |

Normalize receipt collisions under the existing command lock: identical hash
replays; changed material conflicts. One-open checkpoint or final-settlement
collision under an entitled scoped command is INVALID_STATE_TRANSITION after
explicit state validation; raw 23505 never leaks. No broad retry on integrity or
timeout errors. Authenticate/authorize before protected existence/conflict;
wrong project denies without confirming foreign IDs. Unexpected failure uses
existing INTERNAL_ERROR fallback text (HTTP 500 / CLI 1), not a new enum.
Preserve `{error:{code,message,details}}`, X-Request-ID, CLI identity and bounded
sanitized diagnostics. Do not expose constraint text, credentials or SQL.

## 7. Required future tests and acceptance

These are NEW planned files/cases; none is created or run by this documentation
change. Each database test uses disposable real PostgreSQL 18, never SQLite.
Normal-role adversarial DML follows the same first-SHARE/project/command/task
protocol; no superuser bypass, disabled triggers or forgeable session marker.

| NEW exact test file | Required cases |
| --- | --- |
| tests/unit/phase3/test_task_safety_policies.py | Every budget cap below/equal/above, finite limits, zero GPU CPU admission, wall clock including checkpoint waits, six-place exact decimals and round-up adapter boundary, no A4, A0/A1 bounds, A2 plan/governance matrix, A3 exact bounded scope, optional evaluator disablement, default policies. |
| tests/unit/phase3/test_task_budget_accounting.py | Consumed+reserved+proposed math; last-unit equality; parallel/depth gauges; worst-case output cost/time; failed/pruned/cancelled admission counters retained; retry new charge; UNKNOWN nonfinal retains full vector and occupancy; multiple observations one charge; one final reconciliation; no post-final usage; measured-over-bound denied; per-step streaks, reset/tie/first score/absent metric and evaluator mismatch. |
| tests/unit/phase3/test_task_safety_contracts.py | Every closed envelope/argument/DTO; extra nested fields and trusted flag reject; NFC, lowercase UUIDs, six-place strings, all defaults/NULLs; three fixed vectors; complete extension material; set reorder same hash and duplicates reject; old PR3-01 vectors unchanged; no generated IDs/clocks/streaks in material; typed immutable results. |
| tests/unit/phase3/test_task_checkpoints.py | All eight types; conjunctive task/step gates; default 24h; boundary just before/at/after expiry; pending one-time response; no Agent response/extension/escalation; rejection/modification/expiry blocks; latest request defeats old approval; budget intent cannot replace active budget; no checkpoint scientific authorization; all simultaneous causes in priority order. |
| tests/unit/phase3/test_task_safety_transports.py | HTTP/CLI common services, exact codes/status/exit and request identity, no ORM/capability deserialization, public reserve/settle denied, auth before existence, replay before write-role/CAS/expiry, unknown error sanitized. |
| tests/integration/phase3/test_pr3_04_schema.py | Exact eight table/column/index/FK inventories; RESTRICT/no cascade; null/mixed/foreign binding; same-task step/budget/receipt/scope links; NULL-step one-pending uniqueness; one final usage; policy/usage/receipt/history no-op tamper denied; scope hash/frozen/owning-project/global metric rules; disabled optional thresholds; SQL NaN/Infinity rejection. |
| tests/integration/phase3/test_pr3_04_application.py | Six commands persist atomically; one task revision/event/receipt and concrete results; sealed CREATED/PLANNING binding without plan edits; complete bundle gate; proposed extension budget unbound; settlement/evaluation after stop/cancel only bookkeeping; evaluate persists stop without rollback, no-stop evaluation recorded; expiry transitions in one command; all denied operations have zero effects; scientific hashes/trace unchanged. |
| tests/integration/phase3/test_pr3_04_accounting.py | Durable multi-attempt resource totals, last-unit exhaustion, zero GPU, equality stop before next spend, failed/unknown retention, final reconciliation, sticky stop after refund, deadline elapsed through Human wait, unknown occupancy, same-step failure/progress history ordered by receipt revision; chronological admission validation across flushes. |
| tests/integration/phase3/test_pr3_04_concurrency.py | Two sessions reserve last unit (one winner); response/response, response/expiry, response/revoke, bind/cancel/seal, stop/admission, settlement/stop; fresh credential and clock after actual blocking wait; exact first 18-table SHARE before other Application SQL; old/new commands share keys; 10s/30s startup timeout sanitization; only 40001/40P01 up to three fresh attempts; no automatic timeout retry. |
| tests/integration/phase3/test_pr3_04_replay.py | Same-command convergence, changed hash, lost response, uncertain commit formal receipt read; read entitlement required; exact replay despite stale task/checkpoint CAS or post-success expiry; no duplicate reservation/response/charge; original concrete IDs/results immutable; current projection separate. |
| tests/integration/phase3/test_pr3_04_guards.py | Valid direct normal-role SQL under protocol; fresh task AND receipt required immediately for every new row and checkpoint response; candidate scopes need fresh same-receipt policy; committed-receipt insert attacks reject; task second-write rejection; forged GUC irrelevant; rollback/flush adversaries; naked self-transition/revision, orphan policies/results, counterfeit stop totals and extra effects reject at forced constraints. Instrument exactly ONE task final and ONE receipt check for each safety command (including batch expiry), not one per child; maximum 256-scope bundle and 256-node/1024-edge baseline with recorded bounds. |
| tests/integration/phase3/test_pr3_04_queries.py | One lock-free REPEATABLE READ READ ONLY snapshot across entitlement/policies/balances/history under writers; no autoflush/second session/expiry write; effective vs stored expiry; original request/response provenance; NULL planning policies backward reads; safety does not enable execution. |
| tests/integration/phase3/test_pr3_04_migration.py | Clean chain and populated 0077→0078, exact down_revision and sole head; old NULL binding rows unchanged, no backfill; unchanged Phase 1/2/PR3-01 hashes/receipts/trace; catalog CHECK replacement matches 1+4; old planning commands survive; executable status still CHECK-rejected; empty/populated downgrade refuses before changes; separately reviewed forward-repair procedure. |
| tests/integration/phase3/test_pr3_04_fake_consumer.py | Trusted in-process deterministic fake reserves before acting; restart reconstructs gates/balances from DB; stop prevents fake dispatch; bounded fake cancellation with UNKNOWN retained until attributable settlement; no external/provider activation; default missing scientific approvals fail A2/A3; checkpoints cannot scientific freeze/release. |
| tests/architecture/test_pr3_04_boundaries.py | Human/Agent common Application/UoW; pure domain no SQLAlchemy/FastAPI/Typer/SDK; fake capability cannot arrive in public fields; no runtime direct ORM/vendor/credential path, no JSON primary refs, no scientific Decision/Approval mutation, no framework-owned canonical state, existing reserved execution commands still disabled. |

Existing regression anchors (all delivered, not NEW):

- tests/unit/phase3/test_research_task_contracts.py
- tests/unit/phase3/test_research_task_graph.py
- tests/unit/phase3/test_research_task_transports.py
- tests/architecture/test_pr3_01_boundaries.py
- tests/integration/phase3/test_pr3_01_schema.py
- tests/integration/phase3/test_pr3_01_application.py
- tests/integration/phase3/test_pr3_01_concurrency.py
- tests/integration/phase3/test_pr3_01_replay.py
- tests/integration/phase3/test_pr3_01_migration.py
- tests/integration/phase3/test_pr3_00_bootstrap.py

Future focused acceptance commands, only AFTER the two director reviews have
authorized implementation. Supply README's disposable PostgreSQL admin setup.
Do not infer test counts in advance; report actual passed/failed/skipped counts,
PostgreSQL server version, timings/environment and blocked setup in NEW proposed
`docs/phase3/PR3-04-evidence.md` at implementation acceptance:

```sh
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pyright
.venv/bin/alembic heads
.venv/bin/pytest -o addopts='' -ra tests/unit/phase3
.venv/bin/pytest -o addopts='' -ra tests/architecture tests/unit/architecture
.venv/bin/pytest -o addopts='' -ra tests/integration/phase3/test_pr3_04_schema.py tests/integration/phase3/test_pr3_04_guards.py tests/integration/phase3/test_pr3_04_migration.py
.venv/bin/pytest -o addopts='' -ra tests/integration/phase3/test_pr3_04_application.py tests/integration/phase3/test_pr3_04_accounting.py tests/integration/phase3/test_pr3_04_concurrency.py tests/integration/phase3/test_pr3_04_replay.py tests/integration/phase3/test_pr3_04_queries.py tests/integration/phase3/test_pr3_04_fake_consumer.py
.venv/bin/pytest -o addopts='' -ra tests/integration/phase3/test_pr3_00_bootstrap.py tests/integration/phase3/test_pr3_01_schema.py tests/integration/phase3/test_pr3_01_application.py tests/integration/phase3/test_pr3_01_concurrency.py tests/integration/phase3/test_pr3_01_replay.py tests/integration/phase3/test_pr3_01_migration.py
```

The check loop owns the full-suite run; do not run it as author. Future evidence
must record SET CONSTRAINTS ALL IMMEDIATE timing and exact firing counts for
both final guards; no unmeasured performance PASS. No fake test proves real
containment, cancellation, gateway authority, recovery or Phase 3 exit.

Two independent director reviews must inspect authoritative contract/ADR, this
pack, source inventory and authoring evidence. Each finding gives concrete
location, evidence, violated rule, impact and action at P0 BLOCKER / P1 MAJOR /
P2 MINOR / P3 SUGGESTION. Both review dispositions must be recorded; open P0/P1
blocks pack acceptance. This file does not assert either review happened.
After documentation delivery STOP; do not implement 0078 or later work.

## 8. Existing-identifier source inventory and authoring verification

Focused rg/read inspection of src/, migrations/ and tests/ checks delivered
names; neither architectural pseudocode nor the older proposal counts as code.

| Existing names | Source inspected |
| --- | --- |
| 0077_research_task_graph, down_revision=0076_agent_runtime_bootstrap, ten research_task tables; all retained pr301 functions/triggers, CHECKs and receipt tuples | migrations/versions/0077_research_task_graph.py |
| TaskStatus CREATED/PLANNING/CANCELLED; AutonomyLevel A0–A3, EXECUTION_COMMANDS, COMMAND_EVENTS, existing prerequisite labels | src/researchbase/agent_runtime/domain/research_task.py |
| TaskCommand, TaskRead, CommandResult; original closed material and decimals-independent planning hashes | src/researchbase/agent_runtime/application/contracts.py; tests/unit/phase3/test_research_task_contracts.py |
| create_research_task, shared command/query boundary and disabled execution | src/researchbase/agent_runtime/application/research_task.py |
| SHARE_TABLES/SHARE_SQL, exact 18 table names, existing advisory key strings and SQL, row/input ordering | src/researchbase/persistence/research_task_repository.py |
| rb_phase2_lock_project | migrations/versions/0019_phase2_bootstrap_membership.py |
| actors.actor_type HUMAN/AGENT/SERVICE, project_memberships, project_role_assignments, actor_subject_bindings, OWNER, authority/credential joins and projects.lifecycle_status | src/researchbase/persistence/models.py; literature_search_plan_repository.py and phase2_identity_repository.py in that directory |
| datasets.project_id; dataset_snapshots.id/dataset_id/content_hash, no frozen_at/status; metric_definition_versions.metric_definition_id/status/frozen_at/content_hash; metric_definitions.project_id nullable | src/researchbase/persistence/models.py; migrations/versions/0005_dataset_snapshot.py, 0007_metric_definition.py |
| SqlAlchemyUnitOfWork, begin_research_task, begin_formal_read, research_task_uow_factory, _command_database_error, pr301 diagnostic mapping | src/researchbase/persistence/uow.py |
| xmin = pg_current_xact_id()::xid precedent | migrations/versions/0057_xid_wraparound_guards.py; delivered 0077 immediate guards |
| canonical_json_bytes, sha256_canonical_json, sha256-cjson-v1 | src/researchbase/foundation/canonical_json.py, hashing.py |
| ErrorCode, _STATUS, CLI_EXIT_CODES, INTERNAL_ERROR fallback | src/researchbase/foundation/errors.py; api/errors.py; cli/errors.py under src/researchbase |
| Delivered regression paths listed in §7 | rg --files tests/unit/phase3 tests/integration/phase3 tests/architecture tests/unit/architecture |

NEW proposed implementation paths, not created here:
`src/researchbase/agent_runtime/domain/task_safety.py`,
`src/researchbase/agent_runtime/application/safety_contracts.py`,
`src/researchbase/agent_runtime/application/task_safety.py`,
`src/researchbase/agent_runtime/ports/task_safety_repository.py`,
`src/researchbase/persistence/task_safety_repository.py`,
`src/researchbase/persistence/task_safety_queries.py`.
Extend existing models.py, uow.py, API/CLI composition and research-tasks command
adapter without changing old request material. All names declared NEW in this
pack must remain distinct from delivered names until implementation.

Authoring verification: documentation/identifier inspection, whitespace and
single-file scope, three throwaway hashes and installed static tools only.
Specific task instruction forbids tests except hash computation; unit,
architecture and PostgreSQL suites are NOT RUN, not zero-pass evidence. Full
suite belongs to the subsequent check loop. This is a documentation review
candidate, not implementation evidence or an accepted gate. No commit, push,
branch, migration execution, dependencies or runtime changes.

Observed authoring results (no test suites):

| Exact command / inspection | Actual result |
| --- | --- |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -` | Exit 0; three request hashes computed using the two repository foundation modules, pasted in §5.3. |
| `.venv/bin/ruff check .` | Exit 0; All checks passed! |
| `.venv/bin/ruff format --check .` | Exit 0; 837 files already formatted. |
| `.venv/bin/pyright` | Exit 0; 0 errors, 0 warnings, 0 informations. Tool also printed a version-update notice; no dependency update performed. |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/alembic heads` | Exit 0; 0077_research_task_graph (head), sole head. |
| Unit / architecture / PostgreSQL suites | NOT RUN under the specific documentation-only restriction; no test counts or PASS claimed. |

The schema inventory is eight CREATE TABLE statements, nine added columns
(three task bindings and six event flags), five NEW functions, three existing
function replacements and eight NEW immediate triggers. Existing 19 triggers
remain: 15 immediate and four deferred. Thus implementation has 27 triggers,
23 immediate and four deferred, with exactly two whole-state deferred sites.
There are 34 explicit CREATE INDEX/CREATE UNIQUE INDEX statements.
Primary-key/UNIQUE backing indexes are additional to these explicit §2 indexes.
Only this Markdown file is delivered; no test file or migration is created.
