# ruff: noqa: E501
"""PR3-04 immutable safety policies and accounting; forward only."""

from alembic import op

revision = "0078_task_safety_policies"
down_revision = "0077_research_task_graph"
branch_labels = None
depends_on = None

DDL = r"""
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

"""

GUARDS = r"""
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

CREATE OR REPLACE FUNCTION pr301_task_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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

CREATE FUNCTION pr304_child_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r research_task_command_receipts%ROWTYPE; t research_tasks%ROWTYPE; now_at timestamptz := clock_timestamp(); allowed text[];
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'immutable safety history' USING ERRCODE='23514',CONSTRAINT='pr301_immutable'; END IF;
 SELECT * INTO t FROM research_tasks WHERE id=NEW.research_task_id AND xmin=pg_current_xact_id()::xid;
 SELECT * INTO r FROM research_task_command_receipts WHERE id=NEW.receipt_id AND research_task_id=NEW.research_task_id AND xmin=pg_current_xact_id()::xid;
 IF t.id IS NULL OR r.id IS NULL OR r.resulting_row_version<>t.row_version
 THEN RAISE EXCEPTION 'fresh owners required' USING ERRCODE='23514',CONSTRAINT='pr301_immutable'; END IF;
 allowed:=CASE TG_TABLE_NAME WHEN 'execution_budgets' THEN ARRAY['bind_task_policies','request_human_checkpoint']
 WHEN 'budget_reservations' THEN ARRAY['reserve_task_budget'] WHEN 'budget_usage_records' THEN ARRAY['settle_task_budget']
 ELSE ARRAY['bind_task_policies'] END;
 IF NOT r.command_name=ANY(allowed) OR NEW.created_at IS DISTINCT FROM r.completed_at OR
   NEW.created_at<transaction_timestamp() OR NEW.created_at>now_at
 THEN RAISE EXCEPTION 'invalid safety effect' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;
 IF TG_TABLE_NAME IN ('checkpoint_policy_dataset_scopes','checkpoint_policy_metric_scopes') THEN
  IF NOT EXISTS(SELECT 1 FROM checkpoint_policies WHERE id=NEW.checkpoint_policy_id AND research_task_id=t.id AND receipt_id=r.id AND xmin=pg_current_xact_id()::xid)
  THEN RAISE EXCEPTION 'fresh scope owner required' USING ERRCODE='23514',CONSTRAINT='pr301_immutable'; END IF;
 END IF;
 IF t.status='CANCELLED' AND r.command_name<>'settle_task_budget'
 THEN RAISE EXCEPTION 'cancelled task' USING ERRCODE='23514',CONSTRAINT='pr301_state'; END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION pr304_checkpoint_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r research_task_command_receipts%ROWTYPE; t research_tasks%ROWTYPE; now_at timestamptz := clock_timestamp(); stamp timestamptz; receipt uuid;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'immutable checkpoint' USING ERRCODE='23514',CONSTRAINT='pr301_immutable'; END IF;
 IF TG_OP='INSERT' THEN stamp:=NEW.created_at; receipt:=NEW.receipt_id;
 ELSE stamp:=NEW.responded_at; receipt:=NEW.response_receipt_id;
  IF OLD.status<>'PENDING' OR NEW.status='PENDING' OR NEW.row_version<>2 OR
   (to_jsonb(NEW)-ARRAY['status','row_version','responded_at','responded_by','response_reason','response_receipt_id']) IS DISTINCT FROM
   (to_jsonb(OLD)-ARRAY['status','row_version','responded_at','responded_by','response_reason','response_receipt_id'])
  THEN RAISE EXCEPTION 'immutable checkpoint material' USING ERRCODE='23514',CONSTRAINT='pr301_immutable'; END IF;
 END IF;
 SELECT * INTO t FROM research_tasks WHERE id=NEW.research_task_id AND xmin=pg_current_xact_id()::xid;
 SELECT * INTO r FROM research_task_command_receipts WHERE id=receipt AND research_task_id=NEW.research_task_id AND xmin=pg_current_xact_id()::xid;
 IF t.id IS NULL OR r.id IS NULL OR r.resulting_row_version<>t.row_version
 THEN RAISE EXCEPTION 'fresh owners required' USING ERRCODE='23514',CONSTRAINT='pr301_immutable'; END IF;
 IF stamp IS DISTINCT FROM r.completed_at OR stamp<transaction_timestamp() OR stamp>now_at
 THEN RAISE EXCEPTION 'invalid clock' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;
 IF TG_OP='INSERT' THEN
  IF r.command_name<>'request_human_checkpoint' OR NEW.status<>'PENDING' OR NEW.row_version<>1 OR t.status='CANCELLED'
  THEN RAISE EXCEPTION 'invalid request' USING ERRCODE='23514',CONSTRAINT='pr301_state'; END IF;
  IF NEW.expires_at IS DISTINCT FROM NEW.requested_at+(SELECT timeout_seconds*interval '1 second' FROM checkpoint_policies WHERE id=t.checkpoint_policy_id)
  THEN RAISE EXCEPTION 'invalid expiry' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;
 ELSIF NEW.status='EXPIRED' THEN
  IF r.command_name<>'evaluate_task_termination' OR now_at<NEW.expires_at OR NEW.responded_by IS NOT NULL OR NEW.response_reason<>'Checkpoint expired.'
  THEN RAISE EXCEPTION 'invalid expiry' USING ERRCODE='23514',CONSTRAINT='pr301_state'; END IF;
 ELSE
  IF r.command_name<>'respond_human_checkpoint' OR t.status='CANCELLED' OR now_at>=NEW.expires_at OR NEW.responded_by IS DISTINCT FROM r.actor_id
  THEN RAISE EXCEPTION 'response blocked' USING ERRCODE='23514',CONSTRAINT='pr301_state'; END IF;
  IF NOT EXISTS(SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id JOIN project_role_assignments p ON p.membership_id=m.id
   JOIN actor_subject_bindings b ON b.actor_id=a.id WHERE a.id=r.actor_id AND a.actor_type='HUMAN' AND a.retired_at IS NULL
   AND m.project_id=t.project_id AND m.status='ACTIVE' AND p.role='OWNER' AND p.effective_from<=now_at AND (p.effective_until IS NULL OR now_at<p.effective_until)
   AND b.status='ACTIVE' AND b.bound_at<=now_at AND (b.revoked_at IS NULL OR now_at<b.revoked_at))
  THEN RAISE EXCEPTION 'human owner required' USING ERRCODE='23514',CONSTRAINT='pr301_scope'; END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION pr304_validate_policy(p_task uuid,p_policy uuid,p_kind text) RETURNS void LANGUAGE plpgsql AS $$
DECLARE content jsonb; saved text; envelope text; project uuid; c checkpoint_policies%ROWTYPE; vals text[]; v text; b record; n integer;
BEGIN
 SELECT project_id INTO project FROM research_tasks WHERE id=p_task;
 CASE p_kind
 WHEN 'BUDGET' THEN
  SELECT to_jsonb(x)-ARRAY['id','research_task_id','created_at','receipt_id','content_hash','hash_scheme'] || jsonb_build_object(
   'max_gpu_hours',to_char(max_gpu_hours,'FM99999999999990.000000'),'max_token_cost',to_char(max_token_cost,'FM99999999999990.000000')),content_hash
   INTO content,saved FROM execution_budgets x WHERE id=p_policy AND research_task_id=p_task;
  envelope:='ExecutionBudgetPolicy';
 WHEN 'TERMINATION' THEN
  SELECT to_jsonb(x)-ARRAY['id','research_task_id','created_at','receipt_id','content_hash','hash_scheme'],content_hash INTO content,saved
   FROM termination_policies x WHERE id=p_policy AND research_task_id=p_task;
  envelope:='TerminationPolicy';
  IF EXISTS(SELECT 1 FROM termination_policies x JOIN metric_definition_versions v ON v.id=x.score_metric_version_id
   JOIN metric_definitions d ON d.id=v.metric_definition_id WHERE x.id=p_policy AND
   ((d.project_id IS NOT NULL AND d.project_id<>project) OR v.status NOT IN ('FROZEN','SUPERSEDED') OR v.frozen_at IS NULL OR v.content_hash IS NULL))
  THEN RAISE EXCEPTION 'invalid metric binding' USING ERRCODE='23514',CONSTRAINT='pr301_not_frozen'; END IF;
 WHEN 'CHECKPOINT' THEN
  SELECT * INTO c FROM checkpoint_policies WHERE id=p_policy AND research_task_id=p_task;
  content:=to_jsonb(c)-ARRAY['id','research_task_id','created_at','receipt_id','content_hash','hash_scheme']; saved:=c.content_hash;
  envelope:='CheckpointPolicy';
  FOR vals IN SELECT c.required_types UNION ALL SELECT c.allowed_code_paths UNION ALL SELECT c.allowed_network_hosts LOOP
   IF cardinality(vals)>256 OR array_ndims(vals)>1 OR vals IS DISTINCT FROM ARRAY(SELECT DISTINCT u COLLATE "C" FROM unnest(vals) u ORDER BY u COLLATE "C")
   THEN RAISE EXCEPTION 'sorted bounded set required' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;
   FOREACH v IN ARRAY vals LOOP
    IF length(btrim(v)) NOT BETWEEN 1 AND 512 OR v IS NOT NFC NORMALIZED THEN RAISE EXCEPTION 'invalid text' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;
   END LOOP;
  END LOOP;
  FOREACH v IN ARRAY c.allowed_code_paths LOOP
   IF v ~ '(^/|(^|/)\.{1,2}(/|$)|//|/$|[\\*?\[\]])' THEN RAISE EXCEPTION 'invalid code path' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;
  END LOOP;
  FOREACH v IN ARRAY c.allowed_network_hosts LOOP
   IF length(v)>253 OR v !~ '^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)*[a-z]([a-z0-9-]{0,61}[a-z0-9])?$'
   THEN RAISE EXCEPTION 'invalid exact host' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;
  END LOOP;
  IF EXISTS(SELECT 1 FROM checkpoint_policy_dataset_scopes s JOIN dataset_snapshots v ON v.id=s.dataset_snapshot_id JOIN datasets d ON d.id=v.dataset_id
   WHERE s.checkpoint_policy_id=p_policy AND (d.project_id<>project OR s.content_hash IS DISTINCT FROM v.content_hash))
   OR EXISTS(SELECT 1 FROM checkpoint_policy_metric_scopes s JOIN metric_definition_versions v ON v.id=s.metric_definition_version_id JOIN metric_definitions d ON d.id=v.metric_definition_id
   WHERE s.checkpoint_policy_id=p_policy AND ((d.project_id IS NOT NULL AND d.project_id<>project) OR s.content_hash IS DISTINCT FROM v.content_hash OR v.frozen_at IS NULL OR v.status NOT IN ('FROZEN','SUPERSEDED')))
  THEN RAISE EXCEPTION 'invalid scope provenance' USING ERRCODE='23514',CONSTRAINT='pr301_provenance'; END IF;
  SELECT count(*) INTO n FROM checkpoint_policy_dataset_scopes WHERE checkpoint_policy_id=p_policy;
  IF n>256 OR c.a3_authorized<>(n>0) THEN RAISE EXCEPTION 'invalid dataset scope' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;
  SELECT count(*) INTO n FROM checkpoint_policy_metric_scopes WHERE checkpoint_policy_id=p_policy;
  IF n>256 OR c.a3_authorized<>(n>0) OR (c.a3_authorized AND cardinality(c.allowed_code_paths)=0)
  THEN RAISE EXCEPTION 'invalid metric scope' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;
  content:=content || jsonb_build_object('allowed_dataset_snapshots',coalesce((SELECT jsonb_agg(jsonb_build_object('id',dataset_snapshot_id,'content_hash',content_hash) ORDER BY dataset_snapshot_id) FROM checkpoint_policy_dataset_scopes WHERE checkpoint_policy_id=p_policy),'[]'::jsonb),
   'allowed_metric_versions',coalesce((SELECT jsonb_agg(jsonb_build_object('id',metric_definition_version_id,'content_hash',content_hash) ORDER BY metric_definition_version_id) FROM checkpoint_policy_metric_scopes WHERE checkpoint_policy_id=p_policy),'[]'::jsonb));
 ELSE RAISE EXCEPTION 'invalid policy kind' USING ERRCODE='23514',CONSTRAINT='pr301_validation';
 END CASE;
 IF content IS NULL OR saved IS DISTINCT FROM encode(sha256(convert_to(pr304_canonical_policy_json(jsonb_build_object('type',envelope,'material_version',1,'content',content)),'UTF8')),'hex')
 THEN RAISE EXCEPTION 'policy hash contradiction' USING ERRCODE='23514',CONSTRAINT='pr301_provenance'; END IF;
END $$;
CREATE FUNCTION pr304_validate_safety(p_task uuid) RETURNS void LANGUAGE plpgsql AS $$
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
  IF history.command_name IN ('reserve_task_budget','settle_task_budget','evaluate_task_termination') THEN
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

"""

FINAL_GUARDS = r"""
CREATE OR REPLACE FUNCTION pr301_graph_final_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
 RETURN NULL;
END $$;
CREATE OR REPLACE FUNCTION pr301_receipt_complete() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r research_task_command_receipts%ROWTYPE; e research_task_events%ROWTYPE; mapped text;
 expected integer; actual integer;
BEGIN
 SELECT * INTO r FROM research_task_command_receipts WHERE id=NEW.id;
 SELECT te.* INTO e FROM research_task_receipt_events l JOIN research_task_events te ON te.id=l.event_id
  WHERE l.receipt_id=r.id;
 mapped:=CASE r.command_name WHEN 'create_research_task' THEN 'CREATED'
 WHEN 'create_task_plan' THEN 'PLAN_CREATED' WHEN 'add_task_step' THEN 'STEP_ADDED'
 WHEN 'add_task_step_dependency' THEN 'DEPENDENCY_ADDED' WHEN 'seal_task_plan' THEN 'PLAN_SEALED'
 WHEN 'cancel_research_task' THEN 'CANCELLED' WHEN 'bind_task_policies' THEN 'POLICIES_BOUND' WHEN 'reserve_task_budget' THEN 'BUDGET_RESERVED' WHEN 'settle_task_budget' THEN 'BUDGET_SETTLED' WHEN 'evaluate_task_termination' THEN 'TERMINATION_EVALUATED' WHEN 'request_human_checkpoint' THEN 'CHECKPOINT_REQUESTED' WHEN 'respond_human_checkpoint' THEN 'CHECKPOINT_RESPONDED' END;
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

 IF (SELECT count(*) FROM budget_reservations WHERE receipt_id=r.id)<>(CASE WHEN r.command_name='reserve_task_budget' THEN 1 ELSE 0 END) THEN RAISE EXCEPTION 'wrong safety result count' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;

 IF (SELECT count(*) FROM budget_usage_records WHERE receipt_id=r.id)<>(CASE WHEN r.command_name='settle_task_budget' THEN 1 ELSE 0 END) THEN RAISE EXCEPTION 'wrong safety result count' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;

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
 IF r.command_name IN ('bind_task_policies','reserve_task_budget','settle_task_budget','evaluate_task_termination','request_human_checkpoint','respond_human_checkpoint') THEN
  IF r.completed_at<transaction_timestamp() OR r.completed_at>clock_timestamp() OR e.occurred_at IS DISTINCT FROM r.completed_at
   OR EXISTS(SELECT 1 FROM research_task_steps WHERE research_task_id=r.research_task_id AND xmin=pg_current_xact_id()::xid)
   OR EXISTS(SELECT 1 FROM research_task_inputs WHERE research_task_id=r.research_task_id AND xmin=pg_current_xact_id()::xid)
   OR EXISTS(SELECT 1 FROM research_task_step_dependencies WHERE research_task_id=r.research_task_id AND xmin=pg_current_xact_id()::xid)
   OR EXISTS(SELECT 1 FROM research_task_step_inputs WHERE research_task_id=r.research_task_id AND xmin=pg_current_xact_id()::xid)
  THEN RAISE EXCEPTION 'unrelated safety effect' USING ERRCODE='23514',CONSTRAINT='pr301_validation'; END IF;
  IF e.prior_status='CANCELLED' AND r.command_name NOT IN ('settle_task_budget','evaluate_task_termination')
  THEN RAISE EXCEPTION 'terminal safety effect' USING ERRCODE='23514',CONSTRAINT='pr301_state'; END IF;
 END IF;
 RETURN NULL;
END $$;
CREATE TRIGGER pr304_budget_guard BEFORE INSERT OR UPDATE OR DELETE ON execution_budgets FOR EACH ROW EXECUTE FUNCTION pr304_child_guard();
CREATE TRIGGER pr304_termination_guard BEFORE INSERT OR UPDATE OR DELETE ON termination_policies FOR EACH ROW EXECUTE FUNCTION pr304_child_guard();
CREATE TRIGGER pr304_checkpoint_policy_guard BEFORE INSERT OR UPDATE OR DELETE ON checkpoint_policies FOR EACH ROW EXECUTE FUNCTION pr304_child_guard();
CREATE TRIGGER pr304_dataset_scope_guard BEFORE INSERT OR UPDATE OR DELETE ON checkpoint_policy_dataset_scopes FOR EACH ROW EXECUTE FUNCTION pr304_child_guard();
CREATE TRIGGER pr304_metric_scope_guard BEFORE INSERT OR UPDATE OR DELETE ON checkpoint_policy_metric_scopes FOR EACH ROW EXECUTE FUNCTION pr304_child_guard();
CREATE TRIGGER pr304_reservation_guard BEFORE INSERT OR UPDATE OR DELETE ON budget_reservations FOR EACH ROW EXECUTE FUNCTION pr304_child_guard();
CREATE TRIGGER pr304_usage_guard BEFORE INSERT OR UPDATE OR DELETE ON budget_usage_records FOR EACH ROW EXECUTE FUNCTION pr304_child_guard();
CREATE TRIGGER pr304_checkpoint_guard BEFORE INSERT OR UPDATE OR DELETE ON human_checkpoints FOR EACH ROW EXECUTE FUNCTION pr304_checkpoint_guard();

"""


def upgrade() -> None:
    op.execute(DDL)
    op.execute(GUARDS)
    op.execute(FINAL_GUARDS)


def downgrade() -> None:
    raise RuntimeError("forward-only migration; use a reviewed forward repair")
