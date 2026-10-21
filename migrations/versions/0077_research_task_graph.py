# ruff: noqa: E501
"""PR3-01 planning graph, exact frozen DDL and forward-only history guards."""

from alembic import op

revision = "0077_research_task_graph"
down_revision = "0076_agent_runtime_bootstrap"
branch_labels = None
depends_on = None

DDL = r"""
CREATE TABLE research_tasks (
  id uuid NOT NULL PRIMARY KEY,
  project_id uuid NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
  requested_by uuid NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  task_type text NOT NULL CHECK (task_type IN (
    'LITERATURE_RESEARCH','HYPOTHESIS_GENERATION','EXPERIMENT_DESIGN',
    'EXPERIMENT_EXECUTION','ANALYSIS','CLAIM_REVISION','MANUSCRIPT_DRAFTING',
    'INTERNAL_REVIEW','END_TO_END_RESEARCH','REPLICATION','OTHER')),
  objective text NOT NULL CHECK (length(btrim(objective)) BETWEEN 1 AND 8192
    AND objective IS NFC NORMALIZED),
  strategy_id text NOT NULL CHECK (length(btrim(strategy_id)) > 0
    AND strategy_id IS NFC NORMALIZED
    AND lower(btrim(strategy_id)) NOT IN ('latest','main','master')),
  strategy_version text NOT NULL CHECK (length(btrim(strategy_version)) > 0
    AND strategy_version IS NFC NORMALIZED
    AND lower(btrim(strategy_version)) NOT IN ('latest','main','master')),
  autonomy_level text NOT NULL CHECK (autonomy_level IN ('A0','A1','A2','A3')),
  status text NOT NULL CHECK (status IN ('CREATED','PLANNING','CANCELLED')),
  created_at timestamptz NOT NULL,
  started_at timestamptz NULL,
  finished_at timestamptz NULL,
  plan_sealed_at timestamptz NULL,
  current_step_id uuid NULL,
  row_version integer NOT NULL CHECK (row_version >= 1),
  UNIQUE (id, project_id),
  CHECK (started_at IS NULL AND current_step_id IS NULL),
  CHECK ((status = 'CANCELLED') = (finished_at IS NOT NULL)),
  CHECK (finished_at IS NULL OR finished_at >= created_at),
  CHECK (plan_sealed_at IS NULL OR
    (status IN ('PLANNING','CANCELLED') AND plan_sealed_at >= created_at))
);
CREATE INDEX pr301_tasks_project ON research_tasks(project_id, created_at, id);
CREATE INDEX pr301_tasks_requester ON research_tasks(requested_by);

CREATE TABLE research_task_steps (
  id uuid NOT NULL PRIMARY KEY,
  research_task_id uuid NOT NULL REFERENCES research_tasks(id) ON DELETE RESTRICT,
  step_type text NOT NULL CHECK (step_type IN (
    'PLAN','RESEARCH','RETRIEVE','HYPOTHESIZE','DESIGN_EXPERIMENT','CODE','DEBUG',
    'EXECUTE','ANALYZE','CRITIQUE','WRITE','REVIEW','HUMAN_CHECKPOINT','PROMOTE','OTHER')),
  ordinal integer NOT NULL CHECK (ordinal >= 1),
  parent_step_id uuid NULL,
  status text NOT NULL CHECK (status IN ('PENDING','CANCELLED')),
  agent_role text NULL CHECK (agent_role IS NULL OR
    (length(btrim(agent_role)) BETWEEN 1 AND 128 AND agent_role IS NFC NORMALIZED)),
  capability_id text NULL CHECK (capability_id IS NULL OR
    (length(btrim(capability_id)) BETWEEN 1 AND 128 AND capability_id IS NFC NORMALIZED)),
  started_at timestamptz NULL,
  finished_at timestamptz NULL,
  retry_count integer NOT NULL DEFAULT 0 CHECK (retry_count = 0),
  failure_code text NULL,
  row_version integer NOT NULL CHECK (row_version >= 1),
  UNIQUE (research_task_id, id),
  UNIQUE (research_task_id, ordinal),
  CHECK (parent_step_id IS DISTINCT FROM id),
  CHECK (started_at IS NULL AND failure_code IS NULL),
  CHECK ((status = 'CANCELLED') = (finished_at IS NOT NULL)),
  FOREIGN KEY (research_task_id, parent_step_id)
    REFERENCES research_task_steps(research_task_id, id) ON DELETE RESTRICT
    DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX pr301_steps_parent ON research_task_steps(research_task_id, parent_step_id);
ALTER TABLE research_tasks ADD CONSTRAINT pr301_current_step_same_task
  FOREIGN KEY (id, current_step_id)
  REFERENCES research_task_steps(research_task_id, id) ON DELETE RESTRICT;

CREATE TABLE research_task_step_dependencies (
  research_task_id uuid NOT NULL REFERENCES research_tasks(id) ON DELETE RESTRICT,
  predecessor_id uuid NOT NULL,
  dependent_id uuid NOT NULL,
  PRIMARY KEY (research_task_id, predecessor_id, dependent_id),
  CHECK (predecessor_id <> dependent_id),
  FOREIGN KEY (research_task_id, predecessor_id)
    REFERENCES research_task_steps(research_task_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (research_task_id, dependent_id)
    REFERENCES research_task_steps(research_task_id, id) ON DELETE RESTRICT
);
CREATE INDEX pr301_dependency_reverse ON research_task_step_dependencies
  (research_task_id, dependent_id, predecessor_id);

CREATE TABLE research_task_inputs (
  id uuid NOT NULL PRIMARY KEY,
  research_task_id uuid NOT NULL REFERENCES research_tasks(id) ON DELETE RESTRICT,
  research_question_version_id uuid NULL REFERENCES research_question_versions(id) ON DELETE RESTRICT,
  hypothesis_version_id uuid NULL REFERENCES hypothesis_versions(id) ON DELETE RESTRICT,
  claim_version_id uuid NULL REFERENCES claim_versions(id) ON DELETE RESTRICT,
  source_version_id uuid NULL REFERENCES source_versions(id) ON DELETE RESTRICT,
  artifact_version_id uuid NULL REFERENCES artifact_versions(id) ON DELETE RESTRICT,
  manuscript_version_id uuid NULL REFERENCES manuscript_versions(id) ON DELETE RESTRICT,
  content_hash text NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
  hash_scheme text NULL,
  CHECK (num_nonnulls(research_question_version_id, hypothesis_version_id,
    claim_version_id, source_version_id, artifact_version_id, manuscript_version_id) = 1),
  CHECK (CASE WHEN source_version_id IS NOT NULL OR manuscript_version_id IS NOT NULL
    THEN hash_scheme IS NOT NULL AND hash_scheme = 'sha256-cjson-v1'
    ELSE hash_scheme IS NULL END)
);
CREATE UNIQUE INDEX pr301_ti_research_question ON research_task_inputs
  (research_task_id, research_question_version_id) WHERE research_question_version_id IS NOT NULL;
CREATE INDEX pr301_ti_research_question_ref ON research_task_inputs
  (research_question_version_id) WHERE research_question_version_id IS NOT NULL;
CREATE UNIQUE INDEX pr301_ti_hypothesis ON research_task_inputs
  (research_task_id, hypothesis_version_id) WHERE hypothesis_version_id IS NOT NULL;
CREATE INDEX pr301_ti_hypothesis_ref ON research_task_inputs
  (hypothesis_version_id) WHERE hypothesis_version_id IS NOT NULL;
CREATE UNIQUE INDEX pr301_ti_claim ON research_task_inputs
  (research_task_id, claim_version_id) WHERE claim_version_id IS NOT NULL;
CREATE INDEX pr301_ti_claim_ref ON research_task_inputs
  (claim_version_id) WHERE claim_version_id IS NOT NULL;
CREATE UNIQUE INDEX pr301_ti_source ON research_task_inputs
  (research_task_id, source_version_id) WHERE source_version_id IS NOT NULL;
CREATE INDEX pr301_ti_source_ref ON research_task_inputs
  (source_version_id) WHERE source_version_id IS NOT NULL;
CREATE UNIQUE INDEX pr301_ti_artifact ON research_task_inputs
  (research_task_id, artifact_version_id) WHERE artifact_version_id IS NOT NULL;
CREATE INDEX pr301_ti_artifact_ref ON research_task_inputs
  (artifact_version_id) WHERE artifact_version_id IS NOT NULL;
CREATE UNIQUE INDEX pr301_ti_manuscript ON research_task_inputs
  (research_task_id, manuscript_version_id) WHERE manuscript_version_id IS NOT NULL;
CREATE INDEX pr301_ti_manuscript_ref ON research_task_inputs
  (manuscript_version_id) WHERE manuscript_version_id IS NOT NULL;

CREATE TABLE research_task_step_inputs (
  id uuid NOT NULL PRIMARY KEY,
  research_task_id uuid NOT NULL REFERENCES research_tasks(id) ON DELETE RESTRICT,
  step_id uuid NOT NULL,
  research_question_version_id uuid NULL REFERENCES research_question_versions(id) ON DELETE RESTRICT,
  hypothesis_version_id uuid NULL REFERENCES hypothesis_versions(id) ON DELETE RESTRICT,
  claim_version_id uuid NULL REFERENCES claim_versions(id) ON DELETE RESTRICT,
  source_version_id uuid NULL REFERENCES source_versions(id) ON DELETE RESTRICT,
  artifact_version_id uuid NULL REFERENCES artifact_versions(id) ON DELETE RESTRICT,
  manuscript_version_id uuid NULL REFERENCES manuscript_versions(id) ON DELETE RESTRICT,
  content_hash text NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
  hash_scheme text NULL,
  CHECK (num_nonnulls(research_question_version_id, hypothesis_version_id,
    claim_version_id, source_version_id, artifact_version_id, manuscript_version_id) = 1),
  CHECK (CASE WHEN source_version_id IS NOT NULL OR manuscript_version_id IS NOT NULL
    THEN hash_scheme IS NOT NULL AND hash_scheme = 'sha256-cjson-v1'
    ELSE hash_scheme IS NULL END),
  FOREIGN KEY (research_task_id, step_id)
    REFERENCES research_task_steps(research_task_id, id) ON DELETE RESTRICT
);
CREATE UNIQUE INDEX pr301_si_research_question ON research_task_step_inputs
  (research_task_id, step_id, research_question_version_id) WHERE research_question_version_id IS NOT NULL;
CREATE INDEX pr301_si_research_question_ref ON research_task_step_inputs
  (research_question_version_id) WHERE research_question_version_id IS NOT NULL;
CREATE UNIQUE INDEX pr301_si_hypothesis ON research_task_step_inputs
  (research_task_id, step_id, hypothesis_version_id) WHERE hypothesis_version_id IS NOT NULL;
CREATE INDEX pr301_si_hypothesis_ref ON research_task_step_inputs
  (hypothesis_version_id) WHERE hypothesis_version_id IS NOT NULL;
CREATE UNIQUE INDEX pr301_si_claim ON research_task_step_inputs
  (research_task_id, step_id, claim_version_id) WHERE claim_version_id IS NOT NULL;
CREATE INDEX pr301_si_claim_ref ON research_task_step_inputs
  (claim_version_id) WHERE claim_version_id IS NOT NULL;
CREATE UNIQUE INDEX pr301_si_source ON research_task_step_inputs
  (research_task_id, step_id, source_version_id) WHERE source_version_id IS NOT NULL;
CREATE INDEX pr301_si_source_ref ON research_task_step_inputs
  (source_version_id) WHERE source_version_id IS NOT NULL;
CREATE UNIQUE INDEX pr301_si_artifact ON research_task_step_inputs
  (research_task_id, step_id, artifact_version_id) WHERE artifact_version_id IS NOT NULL;
CREATE INDEX pr301_si_artifact_ref ON research_task_step_inputs
  (artifact_version_id) WHERE artifact_version_id IS NOT NULL;
CREATE UNIQUE INDEX pr301_si_manuscript ON research_task_step_inputs
  (research_task_id, step_id, manuscript_version_id) WHERE manuscript_version_id IS NOT NULL;
CREATE INDEX pr301_si_manuscript_ref ON research_task_step_inputs
  (manuscript_version_id) WHERE manuscript_version_id IS NOT NULL;

CREATE TABLE research_task_command_receipts (
  id uuid NOT NULL PRIMARY KEY,
  project_id uuid NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
  actor_id uuid NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  command_id uuid NOT NULL,
  command_name text NOT NULL CHECK (command_name IN (
    'create_research_task','create_task_plan','add_task_step',
    'add_task_step_dependency','seal_task_plan','cancel_research_task')),
  research_task_id uuid NOT NULL,
  request_hash text NOT NULL CHECK (request_hash ~ '^[0-9a-f]{64}$'),
  hash_scheme text NOT NULL CHECK (hash_scheme = 'sha256-cjson-v1'),
  material_version integer NOT NULL CHECK (material_version = 1),
  resulting_row_version integer NOT NULL CHECK (resulting_row_version >= 1),
  completed_at timestamptz NOT NULL,
  UNIQUE (project_id, actor_id, command_id),
  UNIQUE (research_task_id, id),
  UNIQUE (research_task_id, resulting_row_version),
  UNIQUE (research_task_id, actor_id, command_id, resulting_row_version),
  FOREIGN KEY (research_task_id, project_id)
    REFERENCES research_tasks(id, project_id) ON DELETE RESTRICT
);
CREATE INDEX pr301_receipts_actor ON research_task_command_receipts(actor_id);
CREATE INDEX pr301_receipts_project_time ON research_task_command_receipts
  (project_id, completed_at, id);

CREATE TABLE research_task_events (
  id uuid NOT NULL PRIMARY KEY,
  research_task_id uuid NOT NULL REFERENCES research_tasks(id) ON DELETE RESTRICT,
  actor_id uuid NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  command_id uuid NOT NULL,
  event_type text NOT NULL CHECK (event_type IN (
    'CREATED','PLAN_CREATED','STEP_ADDED','DEPENDENCY_ADDED','PLAN_SEALED','CANCELLED')),
  sequence integer NOT NULL CHECK (sequence >= 1),
  task_row_version integer NOT NULL CHECK (task_row_version >= 1),
  prior_status text NULL,
  new_status text NOT NULL,
  reason text NULL,
  occurred_at timestamptz NOT NULL,
  UNIQUE (research_task_id, id),
  UNIQUE (research_task_id, sequence),
  UNIQUE (research_task_id, task_row_version),
  CHECK (sequence = task_row_version),
  CHECK (
    (event_type = 'CREATED' AND prior_status IS NULL AND new_status = 'CREATED') OR
    (event_type = 'PLAN_CREATED' AND prior_status = 'CREATED' AND new_status = 'PLANNING') OR
    (event_type IN ('STEP_ADDED','DEPENDENCY_ADDED','PLAN_SEALED')
      AND prior_status = 'PLANNING' AND new_status = 'PLANNING') OR
    (event_type = 'CANCELLED' AND prior_status IN ('CREATED','PLANNING')
      AND new_status = 'CANCELLED')),
  CHECK (event_type = 'CREATED' OR prior_status IS NOT NULL),
  CHECK (CASE WHEN event_type = 'CANCELLED' THEN
    reason IS NOT NULL AND length(btrim(reason)) > 0 AND reason IS NFC NORMALIZED
    ELSE reason IS NULL END),
  FOREIGN KEY (research_task_id, actor_id, command_id, task_row_version)
    REFERENCES research_task_command_receipts
      (research_task_id, actor_id, command_id, resulting_row_version)
    ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX pr301_task_events_actor ON research_task_events(actor_id);

CREATE TABLE research_task_step_events (
  id uuid NOT NULL PRIMARY KEY,
  research_task_id uuid NOT NULL REFERENCES research_tasks(id) ON DELETE RESTRICT,
  step_id uuid NOT NULL,
  actor_id uuid NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  command_id uuid NOT NULL,
  event_type text NOT NULL CHECK (event_type IN ('PLANNED','CANCELLED')),
  sequence integer NOT NULL CHECK (sequence >= 1),
  step_row_version integer NOT NULL CHECK (step_row_version >= 1),
  task_row_version integer NOT NULL CHECK (task_row_version >= 1),
  prior_status text NULL,
  new_status text NOT NULL,
  reason text NULL,
  occurred_at timestamptz NOT NULL,
  UNIQUE (research_task_id, id),
  UNIQUE (research_task_id, step_id, sequence),
  CHECK (sequence = step_row_version),
  CHECK ((event_type = 'PLANNED' AND prior_status IS NULL AND new_status = 'PENDING'
      AND step_row_version = 1) OR
    (event_type = 'CANCELLED' AND prior_status IS NOT NULL
      AND prior_status = 'PENDING' AND new_status = 'CANCELLED' AND step_row_version = 2)),
  CHECK (CASE WHEN event_type = 'CANCELLED' THEN
    reason IS NOT NULL AND length(btrim(reason)) > 0 AND reason IS NFC NORMALIZED
    ELSE reason IS NULL END),
  FOREIGN KEY (research_task_id, step_id)
    REFERENCES research_task_steps(research_task_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (research_task_id, actor_id, command_id, task_row_version)
    REFERENCES research_task_command_receipts
      (research_task_id, actor_id, command_id, resulting_row_version)
    ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX pr301_step_events_actor ON research_task_step_events(actor_id);

CREATE TABLE research_task_receipt_events (
  receipt_id uuid NOT NULL PRIMARY KEY,
  research_task_id uuid NOT NULL REFERENCES research_tasks(id) ON DELETE RESTRICT,
  event_id uuid NOT NULL UNIQUE,
  FOREIGN KEY (research_task_id, receipt_id)
    REFERENCES research_task_command_receipts(research_task_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (research_task_id, event_id)
    REFERENCES research_task_events(research_task_id, id) ON DELETE RESTRICT
);
CREATE INDEX pr301_receipt_events_task ON research_task_receipt_events(research_task_id);

CREATE TABLE research_task_receipt_step_events (
  receipt_id uuid NOT NULL,
  research_task_id uuid NOT NULL REFERENCES research_tasks(id) ON DELETE RESTRICT,
  step_event_id uuid NOT NULL UNIQUE,
  PRIMARY KEY (receipt_id, step_event_id),
  FOREIGN KEY (research_task_id, receipt_id)
    REFERENCES research_task_command_receipts(research_task_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (research_task_id, step_event_id)
    REFERENCES research_task_step_events(research_task_id, id) ON DELETE RESTRICT
);
CREATE INDEX pr301_receipt_step_events_task ON research_task_receipt_step_events(research_task_id);
"""

CYCLES = r"""
CREATE FUNCTION pr301_dependency_acyclic() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM research_task_step_dependencies
      WHERE research_task_id = NEW.research_task_id
        AND predecessor_id = NEW.predecessor_id AND dependent_id = NEW.dependent_id) THEN
    RETURN NULL;
  END IF;
  IF EXISTS (
    WITH RECURSIVE reach(step_id) AS (
      SELECT NEW.dependent_id
      UNION
      SELECT d.dependent_id FROM reach r JOIN research_task_step_dependencies d
        ON d.research_task_id = NEW.research_task_id AND d.predecessor_id = r.step_id
    ) SELECT 1 FROM reach WHERE step_id = NEW.predecessor_id
  ) THEN
    RAISE EXCEPTION 'dependency cycle' USING ERRCODE = '23514',
      CONSTRAINT = 'pr301_validation';
  END IF;
  RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER pr301_dependency_acyclic_commit
  AFTER INSERT OR UPDATE ON research_task_step_dependencies
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
  EXECUTE FUNCTION pr301_dependency_acyclic();

CREATE FUNCTION pr301_parent_acyclic() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF EXISTS (
    WITH RECURSIVE ancestors(step_id) AS (
      SELECT parent_step_id FROM research_task_steps
        WHERE research_task_id = NEW.research_task_id AND id = NEW.id
          AND parent_step_id IS NOT NULL
      UNION
      SELECT s.parent_step_id FROM ancestors a JOIN research_task_steps s
        ON s.research_task_id = NEW.research_task_id AND s.id = a.step_id
        WHERE s.parent_step_id IS NOT NULL
    ) SELECT 1 FROM ancestors WHERE step_id = NEW.id
  ) THEN
    RAISE EXCEPTION 'parent cycle' USING ERRCODE = '23514',
      CONSTRAINT = 'pr301_validation';
  END IF;
  RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER pr301_parent_acyclic_commit
  AFTER INSERT OR UPDATE ON research_task_steps
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
  EXECUTE FUNCTION pr301_parent_acyclic();
"""

GUARDS = r"""

CREATE FUNCTION pr301_task_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_immutable'; END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.status<>'CREATED' OR NEW.row_version<>1 OR NEW.plan_sealed_at IS NOT NULL
    OR NEW.started_at IS NOT NULL OR NEW.finished_at IS NOT NULL OR NEW.current_step_id IS NOT NULL
    THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_state'; END IF;
 ELSE
  IF OLD.status='CANCELLED' OR
   ROW(NEW.id,NEW.project_id,NEW.requested_by,NEW.created_at,NEW.task_type,NEW.objective,
       NEW.strategy_id,NEW.strategy_version,NEW.autonomy_level)
    IS DISTINCT FROM ROW(OLD.id,OLD.project_id,OLD.requested_by,OLD.created_at,OLD.task_type,
       OLD.objective,OLD.strategy_id,OLD.strategy_version,OLD.autonomy_level)
   THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_immutable'; END IF;
  IF NEW.row_version<>OLD.row_version+1 THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_validation'; END IF;
  IF NOT ((OLD.status='CREATED' AND NEW.status IN ('PLANNING','CANCELLED')) OR
          (OLD.status='PLANNING' AND NEW.status IN ('PLANNING','CANCELLED')))
    THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_state'; END IF;
  IF OLD.plan_sealed_at IS NOT NULL AND (NEW.plan_sealed_at IS DISTINCT FROM OLD.plan_sealed_at
     OR NEW.status<>'CANCELLED') THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_immutable'; END IF;
  IF OLD.plan_sealed_at IS NULL AND NEW.plan_sealed_at IS NOT NULL AND
     NOT (OLD.status='PLANNING' AND NEW.status='PLANNING') THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_state'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER pr301_task_guard BEFORE INSERT OR UPDATE OR DELETE ON research_tasks
 FOR EACH ROW EXECUTE FUNCTION pr301_task_guard();

CREATE FUNCTION pr301_step_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE t research_tasks%ROWTYPE; fresh boolean; child_fresh boolean;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_immutable'; END IF;
 SELECT r.* INTO t FROM research_tasks r WHERE id=NEW.research_task_id;
 SELECT xmin=pg_current_xact_id()::xid INTO fresh FROM research_tasks WHERE id=NEW.research_task_id;
 IF fresh IS DISTINCT FROM true THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_immutable'; END IF;
 IF TG_OP='INSERT' THEN
  IF t.plan_sealed_at IS NOT NULL OR t.status='CANCELLED' THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_immutable'; END IF;
  IF t.status<>'PLANNING' OR NEW.status<>'PENDING' OR NEW.row_version<>1 THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_state'; END IF;
 ELSE
  IF OLD.status='CANCELLED' OR ROW(NEW.id,NEW.research_task_id) IS DISTINCT FROM
     ROW(OLD.id,OLD.research_task_id) THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_immutable'; END IF;
  IF NEW.status='CANCELLED' AND OLD.status='PENDING' AND t.status='CANCELLED'
     AND NEW.row_version=OLD.row_version+1 AND NEW.finished_at IS NOT DISTINCT FROM t.finished_at
     AND ROW(NEW.step_type,NEW.ordinal,NEW.parent_step_id,NEW.agent_role,NEW.capability_id,
       NEW.started_at,NEW.retry_count,NEW.failure_code) IS NOT DISTINCT FROM
       ROW(OLD.step_type,OLD.ordinal,OLD.parent_step_id,OLD.agent_role,OLD.capability_id,
       OLD.started_at,OLD.retry_count,OLD.failure_code) THEN RETURN NEW; END IF;
  SELECT xmin=pg_current_xact_id()::xid INTO child_fresh FROM research_task_steps WHERE id=OLD.id;
  IF child_fresh IS DISTINCT FROM true OR t.plan_sealed_at IS NOT NULL OR t.status<>'PLANNING'
    OR NEW.status<>'PENDING' OR OLD.row_version<>1 OR NEW.row_version<>1 THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_immutable'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER pr301_step_guard BEFORE INSERT OR UPDATE OR DELETE ON research_task_steps
 FOR EACH ROW EXECUTE FUNCTION pr301_step_guard();

CREATE FUNCTION pr301_dependency_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE t research_tasks%ROWTYPE; fresh boolean;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_immutable'; END IF;
 SELECT r.* INTO t FROM research_tasks r WHERE id=NEW.research_task_id;
 SELECT xmin=pg_current_xact_id()::xid INTO fresh FROM research_tasks WHERE id=NEW.research_task_id;
 IF fresh IS DISTINCT FROM true THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_immutable'; END IF;
 IF t.plan_sealed_at IS NOT NULL OR t.status='CANCELLED' THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_immutable'; END IF;
 IF t.status<>'PLANNING' THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_state'; END IF;
 IF TG_OP='UPDATE' THEN
  SELECT xmin=pg_current_xact_id()::xid INTO fresh FROM research_task_step_dependencies
    WHERE research_task_id=OLD.research_task_id AND predecessor_id=OLD.predecessor_id
      AND dependent_id=OLD.dependent_id;
  IF fresh IS DISTINCT FROM true OR NEW.research_task_id IS DISTINCT FROM OLD.research_task_id
    THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_immutable'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER pr301_dependency_guard BEFORE INSERT OR UPDATE OR DELETE ON research_task_step_dependencies
 FOR EACH ROW EXECUTE FUNCTION pr301_dependency_guard();

CREATE FUNCTION pr301_validate_input(p_task uuid, p_question uuid, p_hypothesis uuid, p_claim uuid,
 p_source uuid, p_artifact uuid, p_manuscript uuid, p_hash text, p_scheme text)
 RETURNS void LANGUAGE plpgsql AS $$
DECLARE project uuid; owner uuid; version_id uuid; saved_hash text; saved_scheme text;
 saved_status text; frozen timestamptz; scoped boolean;
BEGIN
 SELECT project_id INTO project FROM research_tasks WHERE id=p_task;
 IF num_nonnulls(p_question,p_hypothesis,p_claim,p_source,p_artifact,p_manuscript)<>1
 THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_validation'; END IF;
 CASE
 WHEN p_question IS NOT NULL THEN
 SELECT v.id,v.content_hash,NULL::text,v.status,v.frozen_at,o.project_id=project
 INTO version_id,saved_hash,saved_scheme,saved_status,frozen,scoped
 FROM research_question_versions v JOIN research_questions o ON o.id=v.research_question_id WHERE v.id=p_question;
 WHEN p_hypothesis IS NOT NULL THEN
 SELECT v.id,v.content_hash,NULL::text,v.status,v.frozen_at,o.project_id=project
 INTO version_id,saved_hash,saved_scheme,saved_status,frozen,scoped
 FROM hypothesis_versions v JOIN hypotheses o ON o.id=v.hypothesis_id WHERE v.id=p_hypothesis;
 WHEN p_claim IS NOT NULL THEN
 SELECT v.id,v.content_hash,NULL::text,v.status,v.frozen_at,o.project_id=project
 INTO version_id,saved_hash,saved_scheme,saved_status,frozen,scoped
 FROM claim_versions v JOIN claims o ON o.id=v.claim_id WHERE v.id=p_claim;
 WHEN p_source IS NOT NULL THEN
 SELECT v.id,v.content_hash,v.hash_scheme,v.status,v.frozen_at,EXISTS(SELECT 1 FROM literature_source_project_links l WHERE l.literature_source_id=o.id AND l.project_id=project)
 INTO version_id,saved_hash,saved_scheme,saved_status,frozen,scoped
 FROM source_versions v JOIN literature_sources o ON o.id=v.literature_source_id WHERE v.id=p_source;
 WHEN p_artifact IS NOT NULL THEN
 SELECT v.id,v.content_hash,NULL::text,v.status,v.frozen_at,o.project_id=project
 INTO version_id,saved_hash,saved_scheme,saved_status,frozen,scoped
 FROM artifact_versions v JOIN artifacts o ON o.id=v.artifact_id WHERE v.id=p_artifact;
 WHEN p_manuscript IS NOT NULL THEN
 SELECT v.id,v.content_hash,v.hash_scheme,v.status,v.frozen_at,o.project_id=project
 INTO version_id,saved_hash,saved_scheme,saved_status,frozen,scoped
 FROM manuscript_versions v JOIN publications o ON o.id=v.publication_id WHERE v.id=p_manuscript;
 ELSE RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_validation'; END CASE;
 IF version_id IS NULL THEN RAISE EXCEPTION 'missing exact input' USING ERRCODE='23503'; END IF;
 IF scoped IS DISTINCT FROM true THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_scope'; END IF;
 IF saved_status NOT IN ('FROZEN','SUPERSEDED') OR frozen IS NULL OR saved_hash IS NULL
   THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_not_frozen'; END IF;
 IF p_hash IS DISTINCT FROM saved_hash THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_provenance'; END IF;
 IF p_source IS NOT NULL OR p_manuscript IS NOT NULL THEN
  IF p_scheme IS DISTINCT FROM 'sha256-cjson-v1' OR p_scheme IS DISTINCT FROM saved_scheme
    THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_provenance'; END IF;
 ELSE IF p_scheme IS NOT NULL THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_provenance'; END IF;
 END IF;
END $$;

CREATE FUNCTION pr301_task_input_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE t research_tasks%ROWTYPE; fresh boolean;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_immutable'; END IF;
 SELECT r.* INTO t FROM research_tasks r WHERE id=NEW.research_task_id;
 SELECT xmin=pg_current_xact_id()::xid INTO fresh FROM research_tasks WHERE id=NEW.research_task_id;
 IF fresh IS DISTINCT FROM true THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_immutable'; END IF;
 IF t.plan_sealed_at IS NOT NULL OR t.status='CANCELLED' THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_immutable'; END IF;
 PERFORM pr301_validate_input(NEW.research_task_id,NEW.research_question_version_id,
 NEW.hypothesis_version_id,NEW.claim_version_id,NEW.source_version_id,NEW.artifact_version_id,
 NEW.manuscript_version_id,NEW.content_hash,NEW.hash_scheme);
 RETURN NEW;
END $$;
CREATE TRIGGER pr301_task_input_guard BEFORE INSERT OR UPDATE OR DELETE ON research_task_inputs
 FOR EACH ROW EXECUTE FUNCTION pr301_task_input_guard();

CREATE FUNCTION pr301_step_input_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE t research_tasks%ROWTYPE; fresh boolean;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_immutable'; END IF;
 SELECT r.* INTO t FROM research_tasks r WHERE id=NEW.research_task_id;
 SELECT xmin=pg_current_xact_id()::xid INTO fresh FROM research_tasks WHERE id=NEW.research_task_id;
 IF fresh IS DISTINCT FROM true THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_immutable'; END IF;
 IF t.plan_sealed_at IS NOT NULL OR t.status='CANCELLED' THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_immutable'; END IF;
 IF t.status<>'PLANNING' OR NOT EXISTS(SELECT 1 FROM research_task_steps
 WHERE id=NEW.step_id AND research_task_id=NEW.research_task_id AND status='PENDING')
 THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_state'; END IF;
 PERFORM pr301_validate_input(NEW.research_task_id,NEW.research_question_version_id,
 NEW.hypothesis_version_id,NEW.claim_version_id,NEW.source_version_id,NEW.artifact_version_id,
 NEW.manuscript_version_id,NEW.content_hash,NEW.hash_scheme);
 RETURN NEW;
END $$;
CREATE TRIGGER pr301_step_input_guard BEFORE INSERT OR UPDATE OR DELETE ON research_task_step_inputs
 FOR EACH ROW EXECUTE FUNCTION pr301_step_input_guard();

CREATE FUNCTION pr301_receipt_insert_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM research_tasks WHERE id=NEW.research_task_id AND project_id=NEW.project_id
  AND row_version=NEW.resulting_row_version AND xmin=pg_current_xact_id()::xid)
 THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_immutable'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER pr301_receipt_insert BEFORE INSERT ON research_task_command_receipts
 FOR EACH ROW EXECUTE FUNCTION pr301_receipt_insert_guard();

CREATE FUNCTION pr301_event_insert_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM research_task_command_receipts WHERE research_task_id=NEW.research_task_id
   AND actor_id=NEW.actor_id AND command_id=NEW.command_id AND resulting_row_version=NEW.task_row_version
   AND xmin=pg_current_xact_id()::xid) THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_immutable'; END IF;
 IF NOT EXISTS(SELECT 1 FROM research_tasks WHERE id=NEW.research_task_id AND row_version=NEW.task_row_version)
 THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_validation'; END IF;
 IF TG_TABLE_NAME='research_task_events' THEN
  IF NOT EXISTS(SELECT 1 FROM research_tasks WHERE id=NEW.research_task_id AND status=NEW.new_status
    AND (NEW.event_type<>'CREATED' OR (NEW.task_row_version=1 AND requested_by=NEW.actor_id)))
    THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_validation'; END IF;
 ELSE
  IF NOT EXISTS(SELECT 1 FROM research_task_steps WHERE id=NEW.step_id AND research_task_id=NEW.research_task_id
   AND row_version=NEW.step_row_version AND status=NEW.new_status) THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_validation'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER pr301_task_event_insert BEFORE INSERT ON research_task_events
 FOR EACH ROW EXECUTE FUNCTION pr301_event_insert_guard();
CREATE TRIGGER pr301_step_event_insert BEFORE INSERT ON research_task_step_events
 FOR EACH ROW EXECUTE FUNCTION pr301_event_insert_guard();

CREATE FUNCTION pr301_receipt_link_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r research_task_command_receipts%ROWTYPE; e record;
BEGIN
 SELECT x.* INTO r FROM research_task_command_receipts x WHERE id=NEW.receipt_id
  AND xmin=pg_current_xact_id()::xid;
 IF r.id IS NULL THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_immutable'; END IF;
 IF TG_TABLE_NAME='research_task_receipt_events' THEN
  SELECT * INTO e FROM research_task_events WHERE id=NEW.event_id AND xmin=pg_current_xact_id()::xid;
 ELSE
  SELECT * INTO e FROM research_task_step_events WHERE id=NEW.step_event_id AND xmin=pg_current_xact_id()::xid;
  IF NOT EXISTS(SELECT 1 FROM research_task_receipt_events l JOIN research_task_events te ON te.id=l.event_id
    WHERE l.receipt_id=r.id AND te.xmin=pg_current_xact_id()::xid) THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_immutable'; END IF;
 END IF;
 IF e.id IS NULL THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_immutable'; END IF;
 IF ROW(r.research_task_id,r.actor_id,r.command_id,r.resulting_row_version)
 IS DISTINCT FROM ROW(e.research_task_id,e.actor_id,e.command_id,e.task_row_version)
 OR NEW.research_task_id IS DISTINCT FROM r.research_task_id THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_validation'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER pr301_receipt_event_insert BEFORE INSERT ON research_task_receipt_events
 FOR EACH ROW EXECUTE FUNCTION pr301_receipt_link_guard();
CREATE TRIGGER pr301_receipt_step_event_insert BEFORE INSERT ON research_task_receipt_step_events
 FOR EACH ROW EXECUTE FUNCTION pr301_receipt_link_guard();

CREATE FUNCTION pr301_history_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr301_immutable'; END $$;
CREATE TRIGGER pr301_task_events_immutable BEFORE UPDATE OR DELETE ON research_task_events
 FOR EACH ROW EXECUTE FUNCTION pr301_history_immutable();
CREATE TRIGGER pr301_step_events_immutable BEFORE UPDATE OR DELETE ON research_task_step_events
 FOR EACH ROW EXECUTE FUNCTION pr301_history_immutable();
CREATE TRIGGER pr301_receipts_immutable BEFORE UPDATE OR DELETE ON research_task_command_receipts
 FOR EACH ROW EXECUTE FUNCTION pr301_history_immutable();
CREATE TRIGGER pr301_receipt_events_immutable BEFORE UPDATE OR DELETE ON research_task_receipt_events
 FOR EACH ROW EXECUTE FUNCTION pr301_history_immutable();
CREATE TRIGGER pr301_receipt_step_events_immutable BEFORE UPDATE OR DELETE ON research_task_receipt_step_events
 FOR EACH ROW EXECUTE FUNCTION pr301_history_immutable();

CREATE FUNCTION pr301_graph_final_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER pr301_task_final AFTER INSERT OR UPDATE ON research_tasks
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pr301_graph_final_guard();

CREATE FUNCTION pr301_receipt_complete() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r research_task_command_receipts%ROWTYPE; e research_task_events%ROWTYPE; mapped text;
 expected integer; actual integer;
BEGIN
 SELECT * INTO r FROM research_task_command_receipts WHERE id=NEW.id;
 SELECT te.* INTO e FROM research_task_receipt_events l JOIN research_task_events te ON te.id=l.event_id
  WHERE l.receipt_id=r.id;
 mapped:=CASE r.command_name WHEN 'create_research_task' THEN 'CREATED'
 WHEN 'create_task_plan' THEN 'PLAN_CREATED' WHEN 'add_task_step' THEN 'STEP_ADDED'
 WHEN 'add_task_step_dependency' THEN 'DEPENDENCY_ADDED' WHEN 'seal_task_plan' THEN 'PLAN_SEALED'
 WHEN 'cancel_research_task' THEN 'CANCELLED' END;
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
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER pr301_receipt_complete_commit AFTER INSERT ON research_task_command_receipts
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pr301_receipt_complete();

"""


def upgrade() -> None:
    op.execute(DDL)
    op.execute(CYCLES)
    op.execute(GUARDS)


def downgrade() -> None:
    raise RuntimeError("forward-only migration; use a reviewed forward repair")
