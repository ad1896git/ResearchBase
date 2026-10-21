# ruff: noqa: E501
"""Owner-authorized ADR-0023 S1 identity and immutable versions.

Re-parented to accepted 0078_task_safety_policies at integration, as planned.
"""

from alembic import op

revision = "0079_agent_identity_versions"
down_revision = "0078_task_safety_policies"
branch_labels = None
depends_on = None

DDL = r"""
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
"""

MEMBERSHIP_EVENT = r"""
CREATE OR REPLACE FUNCTION rb_phase2_validate_membership_event() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
            v_status varchar(16);
            v_actor uuid;
        BEGIN
            SELECT status, actor_id INTO v_status, v_actor
              FROM project_memberships WHERE id = NEW.membership_id;
            IF NEW.actor_id IS DISTINCT FROM v_actor OR
               (NEW.prior_status IS NULL AND NOT (
                    NEW.event_kind IN ('FIRST_BOOTSTRAP', 'PROJECT_ENROLLMENT', 'ACTIVATED')
                    AND NEW.new_status = 'ACTIVE'
               )) OR
               (NEW.prior_status IS NULL AND NOT EXISTS (
                    SELECT 1 FROM project_memberships m
                     WHERE m.id = NEW.membership_id AND m.started_at = NEW.occurred_at
               )) OR
               (NEW.event_kind = 'SUSPENDED' AND NEW.new_status <> 'SUSPENDED') OR
               (NEW.event_kind = 'ENDED' AND NEW.new_status <> 'ENDED') OR
               (NEW.event_kind IN ('SUSPENDED', 'ENDED') AND NEW.prior_status <> 'ACTIVE') OR
               (NEW.event_kind IN ('SUSPENDED', 'ENDED') AND NEW.new_status IS DISTINCT FROM v_status) OR
               (NEW.event_kind IN ('FIRST_BOOTSTRAP', 'PROJECT_ENROLLMENT', 'ACTIVATED') AND
                    v_status NOT IN ('ACTIVE', 'SUSPENDED', 'ENDED')) OR
               (NEW.event_kind = 'PROJECT_ENROLLMENT' AND NOT (EXISTS (
                    SELECT 1 FROM project_memberships m
                    JOIN projects p ON p.id = m.project_id AND p.created_by = m.actor_id
                    JOIN actor_subject_bindings b ON b.actor_id = m.actor_id AND b.status = 'ACTIVE'
                     WHERE m.id = NEW.membership_id
               ) OR EXISTS (
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
))) OR
               (NEW.event_kind = 'FIRST_BOOTSTRAP' AND (
                    (SELECT count(*) FROM actors) <> 1 OR
                    (SELECT count(*) FROM projects) <> 1 OR
                    NOT EXISTS (SELECT 1 FROM actors a WHERE a.id = v_actor AND a.actor_type = 'HUMAN') OR
                    NOT EXISTS (SELECT 1 FROM bootstrap_records br WHERE br.first_membership_id = NEW.membership_id)
               )) THEN
                RAISE EXCEPTION 'invalid membership event transition'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_membership_event_transition';
            END IF;
            RETURN NULL;
        END
        $$;
"""

FUNCTIONS = r"""
CREATE FUNCTION pr302_immutable() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
BEGIN
 RAISE EXCEPTION 'immutable S1 history' USING ERRCODE='23514', CONSTRAINT='pr302_immutable';
END $$;

CREATE FUNCTION pr302_receipt_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE t timestamptz := clock_timestamp();
BEGIN
 NEW.recorded_at := t;
 IF NOT EXISTS (
  SELECT 1 FROM projects p JOIN project_memberships m ON m.project_id=p.id
  JOIN project_role_assignments ro ON ro.membership_id=m.id
  JOIN actors a ON a.id=m.actor_id
  JOIN actor_subject_bindings b ON b.actor_id=a.id
  WHERE p.id=NEW.project_id AND p.lifecycle_status='ACTIVE'
   AND a.id=NEW.caller_actor_id AND a.actor_type='HUMAN' AND a.retired_at IS NULL
   AND m.status='ACTIVE' AND m.started_at<=t AND ro.role='OWNER'
   AND ro.effective_from<=t AND (ro.effective_until IS NULL OR ro.effective_until>t)
   AND b.status='ACTIVE' AND b.bound_at<=t AND (b.revoked_at IS NULL OR b.revoked_at>t)
 ) THEN
  RAISE EXCEPTION 'effective HUMAN OWNER required' USING ERRCODE='23514', CONSTRAINT='pr302_scope';
 END IF;
 IF NEW.operation='register_agent_version' AND EXISTS (
   SELECT 1 FROM agent_versions WHERE id=NEW.result_agent_version_id
 ) THEN
  RAISE EXCEPTION 'version identity occupied' USING ERRCODE='23514', CONSTRAINT='pr302_provenance';
 END IF;
 IF NEW.operation='change_agent_availability' AND NOT EXISTS (
   SELECT 1 FROM agent_versions WHERE id=NEW.result_agent_version_id AND project_id=NEW.project_id
 ) THEN
  RAISE EXCEPTION 'version scope mismatch' USING ERRCODE='23514', CONSTRAINT='pr302_scope';
 END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION pr302_version_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE c record; t timestamptz := clock_timestamp();
BEGIN
 IF NOT EXISTS (
  SELECT 1 FROM agent_command_receipts r WHERE r.operation='register_agent_version'
   AND r.result_agent_version_id=NEW.id AND r.project_id=NEW.project_id
   AND r.caller_actor_id=NEW.created_by AND r.resulting_revision=1
   AND r.recorded_at=NEW.created_at AND r.xmin = pg_current_xact_id()::xid
 ) THEN
  RAISE EXCEPTION 'fresh registration receipt required' USING ERRCODE='23514', CONSTRAINT='pr302_immutable';
 END IF;
 IF NOT EXISTS (
  SELECT 1 FROM actors a JOIN actor_subject_bindings b ON b.actor_id=a.id
   JOIN project_memberships m ON m.actor_id=a.id
   JOIN project_role_assignments ro ON ro.membership_id=m.id
   JOIN agent_command_receipts r ON r.result_actor_id=a.id
  WHERE a.id=NEW.actor_id AND a.actor_type='AGENT' AND a.retired_at IS NULL
   AND b.id=r.result_binding_id AND b.status='ACTIVE' AND b.subject_kind='MTLS_URI'
   AND b.proof_kind='MTLS_CHALLENGE' AND b.bound_at<=t
   AND (b.revoked_at IS NULL OR b.revoked_at>t)
   AND r.operation='provision_project_agent' AND r.project_id=NEW.project_id
   AND m.project_id=NEW.project_id AND m.status='ACTIVE' AND m.started_at<=t
   AND ro.role='RESEARCHER' AND ro.effective_from<=t
   AND (ro.effective_until IS NULL OR ro.effective_until>t)
 ) THEN
  RAISE EXCEPTION 'enrolled live AGENT required' USING ERRCODE='23514', CONSTRAINT='pr302_scope';
 END IF;
 SELECT av.*, a.project_id INTO c FROM artifact_versions av JOIN artifacts a ON a.id=av.artifact_id
  WHERE av.id=NEW.configuration_artifact_version_id;
 IF NOT FOUND THEN
  RAISE EXCEPTION 'configuration absent' USING ERRCODE='23503';
 END IF;
 IF c.project_id<>NEW.project_id THEN
  RAISE EXCEPTION 'configuration scope' USING ERRCODE='23514', CONSTRAINT='pr302_scope';
 END IF;
 IF c.status NOT IN ('FROZEN','SUPERSEDED') OR c.frozen_at IS NULL OR c.content_hash IS NULL THEN
  RAISE EXCEPTION 'configuration not frozen' USING ERRCODE='23514', CONSTRAINT='pr302_not_frozen';
 END IF;
 IF c.content_hash<>NEW.configuration_content_hash OR NEW.content_hash<>pr216_hash(jsonb_build_object(
  'type','AgentVersion','material_version',1,
  'project_id',NEW.project_id::text,'actor_id',NEW.actor_id::text,
  'agent_role',NEW.agent_role,'runtime_type',NEW.runtime_type,
  'prompt_template_version',NEW.prompt_template_version,'model_profile_id',NEW.model_profile_id,
  'tool_policy_version',NEW.tool_policy_version,'capability_set_hash',NEW.capability_set_hash,
  'configuration_artifact_version_id',NEW.configuration_artifact_version_id::text,
  'configuration_content_hash',NEW.configuration_content_hash)) THEN
  RAISE EXCEPTION 'version material contradiction' USING ERRCODE='23514', CONSTRAINT='pr302_provenance';
 END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION pr302_availability_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE r agent_command_receipts%ROWTYPE; v agent_versions%ROWTYPE;
BEGIN
 IF TG_OP='DELETE' THEN
  RAISE EXCEPTION 'immutable availability history' USING ERRCODE='23514', CONSTRAINT='pr302_immutable';
 END IF;
 SELECT * INTO v FROM agent_versions WHERE id=NEW.agent_version_id;
 IF NOT FOUND THEN RAISE EXCEPTION 'version absent' USING ERRCODE='23503'; END IF;
 SELECT * INTO r FROM agent_command_receipts WHERE result_agent_version_id=NEW.agent_version_id
  AND resulting_revision=NEW.revision AND caller_actor_id=NEW.changed_by
  AND recorded_at=NEW.changed_at AND xmin = pg_current_xact_id()::xid;
 IF NOT FOUND OR r.project_id<>v.project_id THEN
  RAISE EXCEPTION 'fresh availability receipt required' USING ERRCODE='23514', CONSTRAINT='pr302_immutable';
 END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.status<>'ACTIVE' OR NEW.revision<>1 OR r.operation<>'register_agent_version'
   OR NOT EXISTS (SELECT 1 FROM agent_versions WHERE id=NEW.agent_version_id AND xmin = pg_current_xact_id()::xid) THEN
   RAISE EXCEPTION 'invalid initial availability' USING ERRCODE='23514', CONSTRAINT='pr302_state';
  END IF;
 ELSE
  IF OLD.xmin = pg_current_xact_id()::xid THEN
   RAISE EXCEPTION 'one availability write per transaction' USING ERRCODE='23514', CONSTRAINT='pr302_immutable';
  END IF;
  IF NEW.agent_version_id<>OLD.agent_version_id OR NEW.revision<>OLD.revision+1
   OR NEW.changed_at<OLD.changed_at OR NEW.status=OLD.status OR OLD.status='RETIRED'
   OR r.operation<>'change_agent_availability' THEN
   RAISE EXCEPTION 'invalid availability transition' USING ERRCODE='23514', CONSTRAINT='pr302_state';
  END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION pr302_event_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE r agent_command_receipts%ROWTYPE; a agent_availability%ROWTYPE; p agent_availability_events%ROWTYPE;
BEGIN
 SELECT * INTO r FROM agent_command_receipts WHERE id=NEW.receipt_id
  AND xmin = pg_current_xact_id()::xid;
 IF NOT FOUND THEN
  RAISE EXCEPTION 'fresh event receipt required' USING ERRCODE='23514', CONSTRAINT='pr302_immutable';
 END IF;
 SELECT * INTO a FROM agent_availability WHERE agent_version_id=NEW.agent_version_id
  AND xmin = pg_current_xact_id()::xid;
 IF NOT FOUND OR r.result_availability_event_id<>NEW.id OR r.result_agent_version_id<>NEW.agent_version_id
  OR a.revision<>NEW.sequence OR r.resulting_revision<>NEW.sequence
  OR a.status<>NEW.new_status OR a.changed_by<>NEW.actor_id OR r.caller_actor_id<>NEW.actor_id
  OR a.changed_at<>NEW.occurred_at OR r.recorded_at<>NEW.occurred_at
  OR NOT EXISTS (SELECT 1 FROM agent_versions WHERE id=NEW.agent_version_id AND project_id=r.project_id) THEN
  RAISE EXCEPTION 'event contradiction' USING ERRCODE='23514', CONSTRAINT='pr302_provenance';
 END IF;
 IF NEW.sequence=1 THEN
  IF r.operation<>'register_agent_version' OR NEW.reason<>'version registered'
   OR NEW.prior_status IS NOT NULL OR NEW.new_status<>'ACTIVE' THEN
   RAISE EXCEPTION 'initial event contradiction' USING ERRCODE='23514', CONSTRAINT='pr302_provenance';
  END IF;
 ELSE
  SELECT * INTO p FROM agent_availability_events WHERE agent_version_id=NEW.agent_version_id AND sequence=NEW.sequence-1
   AND xmin <> pg_current_xact_id()::xid;
  IF NOT FOUND OR p.new_status<>NEW.prior_status OR p.occurred_at>NEW.occurred_at
   OR r.operation<>'change_agent_availability' THEN
   RAISE EXCEPTION 'history contradiction' USING ERRCODE='23514', CONSTRAINT='pr302_provenance';
  END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION pr302_binding_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
BEGIN
 IF EXISTS (SELECT 1 FROM actors WHERE id=NEW.actor_id AND actor_type='HUMAN') THEN RETURN NEW; END IF;
 IF NOT EXISTS (SELECT 1 FROM actors WHERE id=NEW.actor_id AND actor_type='AGENT' AND xmin = pg_current_xact_id()::xid)
  OR NEW.subject_kind<>'MTLS_URI' OR NEW.status<>'ACTIVE' OR NEW.proof_kind<>'MTLS_CHALLENGE'
  OR NEW.enrollment_challenge_id IS NOT NULL OR NEW.row_version<>1 OR NEW.revoked_at IS NOT NULL
  OR NOT EXISTS (SELECT 1 FROM agent_command_receipts WHERE operation='provision_project_agent'
   AND result_actor_id=NEW.actor_id AND result_binding_id=NEW.id AND xmin = pg_current_xact_id()::xid) THEN
  RAISE EXCEPTION 'fresh AGENT MTLS enrollment required' USING ERRCODE='23514', CONSTRAINT='pr302_scope';
 END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION pr302_identity_insert_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE a uuid; r agent_command_receipts%ROWTYPE; j jsonb := to_jsonb(NEW); parent_fresh boolean;
BEGIN
 IF TG_TABLE_NAME='actors' THEN
  IF TG_OP='UPDATE' THEN
   IF OLD.actor_type IS DISTINCT FROM NEW.actor_type AND (OLD.actor_type='AGENT' OR NEW.actor_type='AGENT') THEN
    RAISE EXCEPTION 'actor classification immutable' USING ERRCODE='23514', CONSTRAINT='pr302_immutable';
   END IF;
   RETURN NEW;
  END IF;
  IF NEW.actor_type<>'AGENT' THEN RETURN NEW; END IF;
  a:=NEW.id;
 ELSIF TG_TABLE_NAME='actor_subject_binding_events' THEN
  SELECT actor_id INTO a FROM actor_subject_bindings WHERE id=NEW.binding_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'binding absent' USING ERRCODE='23503'; END IF;
 ELSIF TG_TABLE_NAME='project_membership_events' THEN
  SELECT actor_id INTO a FROM project_memberships WHERE id=NEW.membership_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'membership absent' USING ERRCODE='23503'; END IF;
 ELSIF TG_TABLE_NAME='project_role_events' THEN
  SELECT actor_id INTO a FROM project_role_assignments WHERE id=NEW.role_assignment_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'role absent' USING ERRCODE='23503'; END IF;
 ELSE a:=(j->>'actor_id')::uuid;
 END IF;
 IF TG_TABLE_NAME<>'actors' AND NOT EXISTS (SELECT 1 FROM actors WHERE id=a AND actor_type='AGENT') THEN RETURN NEW; END IF;
 IF TG_TABLE_NAME<>'actors' AND (j->>'actor_id')::uuid IS DISTINCT FROM a THEN
  RAISE EXCEPTION 'subject actor mismatch' USING ERRCODE='23514', CONSTRAINT='pr302_provenance';
 END IF;
 SELECT * INTO r FROM agent_command_receipts WHERE result_actor_id=a AND operation='provision_project_agent';
 IF TG_TABLE_NAME='project_role_assignments' AND j->>'role'<>'RESEARCHER' THEN
  RAISE EXCEPTION 'Agent role ceiling' USING ERRCODE='23514', CONSTRAINT='pr302_scope';
 END IF;
 IF TG_TABLE_NAME='project_role_assignments' AND TG_OP='UPDATE' THEN RETURN NEW; END IF;
 IF TG_TABLE_NAME='actors' THEN
  IF NEW.retired_at IS NOT NULL OR NEW.external_key IS NOT NULL OR NOT EXISTS (
   SELECT 1 FROM agent_command_receipts WHERE id=r.id AND xmin = pg_current_xact_id()::xid
  ) THEN RAISE EXCEPTION 'fresh actor receipt required' USING ERRCODE='23514', CONSTRAINT='pr302_scope'; END IF;
 ELSIF TG_TABLE_NAME IN ('project_memberships','project_role_assignments') THEN
  IF r.id IS NULL OR (j->>'project_id')::uuid<>r.project_id
   OR NOT EXISTS (SELECT 1 FROM actor_subject_bindings WHERE id=r.result_binding_id AND actor_id=a
     AND status='ACTIVE' AND subject_kind='MTLS_URI')
   OR (j->>'row_version')::integer<>1 THEN
   RAISE EXCEPTION 'original project/binding and ceiling required' USING ERRCODE='23514', CONSTRAINT='pr302_scope';
  END IF;
  IF EXISTS (SELECT 1 FROM actors WHERE id=a AND xmin = pg_current_xact_id()::xid) THEN
   IF NOT EXISTS (SELECT 1 FROM agent_command_receipts WHERE id=r.id AND xmin = pg_current_xact_id()::xid)
    OR (TG_TABLE_NAME='project_memberships' AND (NEW.id<>r.result_membership_id OR j->>'status'<>'ACTIVE'))
    OR (TG_TABLE_NAME='project_role_assignments' AND NEW.id<>r.result_role_assignment_id) THEN
    RAISE EXCEPTION 'initial identity mismatch' USING ERRCODE='23514', CONSTRAINT='pr302_immutable';
   END IF;
  END IF;
 ELSE
  IF (TG_TABLE_NAME='actor_subject_binding_events' AND NEW.event_kind='PROVISIONED')
   OR (TG_TABLE_NAME='project_membership_events' AND NEW.event_kind='PROJECT_ENROLLMENT')
   OR (TG_TABLE_NAME='project_role_events' AND NEW.event_kind='ASSIGNED'
    AND (j->>'role_assignment_id')::uuid=r.result_role_assignment_id) THEN
   parent_fresh:=false;
   IF TG_TABLE_NAME='actor_subject_binding_events' THEN
    SELECT EXISTS (SELECT 1 FROM actor_subject_bindings WHERE id=r.result_binding_id AND id=(j->>'binding_id')::uuid
     AND xmin = pg_current_xact_id()::xid) INTO parent_fresh;
   ELSIF TG_TABLE_NAME='project_membership_events' THEN
    SELECT EXISTS (SELECT 1 FROM project_memberships WHERE id=r.result_membership_id AND id=(j->>'membership_id')::uuid
     AND xmin = pg_current_xact_id()::xid) INTO parent_fresh;
   ELSE
    SELECT EXISTS (SELECT 1 FROM project_role_assignments WHERE id=r.result_role_assignment_id AND id=(j->>'role_assignment_id')::uuid
     AND xmin = pg_current_xact_id()::xid) INTO parent_fresh;
   END IF;
   IF NOT parent_fresh OR NEW.request_id<>r.command_id
    OR NEW.id<>(CASE TG_TABLE_NAME WHEN 'actor_subject_binding_events' THEN r.result_binding_event_id
     WHEN 'project_membership_events' THEN r.result_membership_event_id ELSE r.result_role_event_id END)
    OR NOT EXISTS (SELECT 1 FROM agent_command_receipts WHERE id=r.id AND xmin = pg_current_xact_id()::xid) THEN
    RAISE EXCEPTION 'initial event immutable' USING ERRCODE='23514', CONSTRAINT='pr302_immutable';
   END IF;
  END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION pr302_receipt_complete() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE r agent_command_receipts%ROWTYPE; t timestamptz := clock_timestamp(); n integer;
BEGIN
 SELECT * INTO r FROM agent_command_receipts WHERE id=NEW.id;
 IF NOT EXISTS (
  SELECT 1 FROM projects p JOIN project_memberships m ON m.project_id=p.id
   JOIN project_role_assignments ro ON ro.membership_id=m.id JOIN actors a ON a.id=m.actor_id
   JOIN actor_subject_bindings b ON b.actor_id=a.id
  WHERE p.id=r.project_id AND p.lifecycle_status='ACTIVE' AND a.id=r.caller_actor_id
   AND a.actor_type='HUMAN' AND a.retired_at IS NULL AND m.status='ACTIVE' AND m.started_at<=t
   AND ro.role='OWNER' AND ro.effective_from<=t AND (ro.effective_until IS NULL OR ro.effective_until>t)
   AND b.status='ACTIVE' AND b.bound_at<=t AND (b.revoked_at IS NULL OR b.revoked_at>t)
 ) THEN RAISE EXCEPTION 'OWNER unavailable' USING ERRCODE='23514', CONSTRAINT='pr302_scope'; END IF;
 IF r.operation='provision_project_agent' THEN
  IF NOT EXISTS (
   SELECT 1 FROM actors a JOIN actor_subject_bindings b ON b.actor_id=a.id
    JOIN project_memberships m ON m.actor_id=a.id JOIN project_role_assignments ro ON ro.membership_id=m.id
    JOIN actor_subject_binding_events be ON be.binding_id=b.id
    JOIN project_membership_events me ON me.membership_id=m.id
    JOIN project_role_events re ON re.role_assignment_id=ro.id
   WHERE a.id=r.result_actor_id AND a.actor_type='AGENT' AND a.retired_at IS NULL AND a.external_key IS NULL
    AND a.row_version=1 AND a.created_at=r.recorded_at AND a.xmin = pg_current_xact_id()::xid
    AND b.id=r.result_binding_id AND b.status='ACTIVE' AND b.subject_kind='MTLS_URI' AND b.proof_kind='MTLS_CHALLENGE'
    AND b.enrollment_challenge_id IS NULL AND b.row_version=1 AND b.revoked_at IS NULL
    AND b.created_at=r.recorded_at AND b.bound_at=r.recorded_at AND b.xmin = pg_current_xact_id()::xid
    AND m.id=r.result_membership_id AND m.project_id=r.project_id AND m.status='ACTIVE'
    AND m.row_version=1 AND m.ended_at IS NULL AND m.created_by=r.caller_actor_id
    AND m.started_at=r.recorded_at AND m.created_at=r.recorded_at AND m.xmin = pg_current_xact_id()::xid
    AND ro.id=r.result_role_assignment_id AND ro.actor_id=a.id AND ro.project_id=r.project_id AND ro.role='RESEARCHER'
    AND ro.row_version=1 AND ro.effective_until IS NULL AND ro.assigned_by=r.caller_actor_id
    AND ro.effective_from=r.recorded_at AND ro.created_at=r.recorded_at AND ro.xmin = pg_current_xact_id()::xid
    AND be.id=r.result_binding_event_id AND be.event_kind='PROVISIONED' AND be.actor_id=a.id
    AND be.request_id=r.command_id AND be.occurred_at=r.recorded_at AND be.xmin = pg_current_xact_id()::xid
    AND be.proof_sha256=b.proof_sha256 AND be.proof_record_ref=b.proof_record_ref
    AND be.operator_credential_id=b.operator_credential_id AND be.subject_credential_id=b.subject_credential_id
    AND be.proof_kind=b.proof_kind
    AND me.id=r.result_membership_event_id AND me.actor_id=a.id AND me.event_kind='PROJECT_ENROLLMENT'
    AND me.prior_status IS NULL AND me.new_status='ACTIVE' AND me.request_id=r.command_id
    AND me.occurred_at=r.recorded_at AND me.xmin = pg_current_xact_id()::xid
    AND re.id=r.result_role_event_id AND re.actor_id=a.id AND re.event_kind='ASSIGNED'
    AND re.request_id=r.command_id AND re.occurred_at=r.recorded_at AND re.xmin = pg_current_xact_id()::xid
  ) OR (SELECT count(*) FROM actor_subject_bindings WHERE actor_id=r.result_actor_id)<>1
    OR (SELECT count(*) FROM project_memberships WHERE actor_id=r.result_actor_id)<>1
    OR (SELECT count(*) FROM project_role_assignments WHERE actor_id=r.result_actor_id)<>1
    OR (SELECT count(*) FROM actor_subject_binding_events WHERE actor_id=r.result_actor_id)<>1
    OR (SELECT count(*) FROM project_membership_events WHERE actor_id=r.result_actor_id)<>1
    OR (SELECT count(*) FROM project_role_events WHERE actor_id=r.result_actor_id)<>1 THEN
   RAISE EXCEPTION 'incomplete enrollment' USING ERRCODE='23514', CONSTRAINT='pr302_provenance';
  END IF;
 ELSE
  IF NOT EXISTS (
   SELECT 1 FROM agent_versions v JOIN agent_availability a ON a.agent_version_id=v.id
    JOIN agent_availability_events e ON e.agent_version_id=v.id AND e.sequence=a.revision
   WHERE v.id=r.result_agent_version_id AND v.project_id=r.project_id AND a.revision=r.resulting_revision
    AND a.xmin = pg_current_xact_id()::xid AND e.xmin = pg_current_xact_id()::xid
    AND e.receipt_id=r.id AND e.id=r.result_availability_event_id
    AND a.status=e.new_status AND a.changed_by=r.caller_actor_id AND e.actor_id=r.caller_actor_id
    AND a.changed_at=r.recorded_at AND e.occurred_at=r.recorded_at
    AND (r.operation<>'register_agent_version' OR (v.xmin = pg_current_xact_id()::xid
     AND v.created_by=r.caller_actor_id AND v.created_at=r.recorded_at AND a.revision=1))
    AND (r.operation<>'change_agent_availability' OR v.xmin <> pg_current_xact_id()::xid)
  ) THEN RAISE EXCEPTION 'incomplete version command' USING ERRCODE='23514', CONSTRAINT='pr302_provenance'; END IF;
  SELECT count(*) INTO n FROM agent_availability_events WHERE agent_version_id=r.result_agent_version_id;
  IF n<>r.resulting_revision OR EXISTS (
   SELECT 1 FROM agent_availability_events e LEFT JOIN agent_availability_events p
    ON p.agent_version_id=e.agent_version_id AND p.sequence=e.sequence-1
   LEFT JOIN agent_command_receipts cr ON cr.id=e.receipt_id
   WHERE e.agent_version_id=r.result_agent_version_id AND (
    (e.sequence>1 AND (p.id IS NULL OR p.new_status<>e.prior_status OR p.occurred_at>e.occurred_at))
    OR cr.result_availability_event_id IS DISTINCT FROM e.id
    OR cr.result_agent_version_id IS DISTINCT FROM e.agent_version_id
    OR cr.resulting_revision IS DISTINCT FROM e.sequence)
  ) OR (SELECT count(*) FROM agent_availability_events WHERE agent_version_id=r.result_agent_version_id
     AND xmin = pg_current_xact_id()::xid)<>1 THEN
   RAISE EXCEPTION 'history contradiction' USING ERRCODE='23514', CONSTRAINT='pr302_provenance';
  END IF;
 END IF;
 RETURN NULL;
END $$;
"""


def upgrade() -> None:
    op.execute(DDL)
    op.execute(FUNCTIONS)
    op.execute(MEMBERSHIP_EVENT)
    triggers = (
        ("pr302_receipt_insert", "agent_command_receipts", "INSERT", "pr302_receipt_guard"),
        (
            "pr302_receipt_immutable",
            "agent_command_receipts",
            "UPDATE OR DELETE",
            "pr302_immutable",
        ),
        ("pr302_version_insert", "agent_versions", "INSERT", "pr302_version_guard"),
        ("pr302_version_immutable", "agent_versions", "UPDATE OR DELETE", "pr302_immutable"),
        (
            "pr302_availability_write",
            "agent_availability",
            "INSERT OR UPDATE OR DELETE",
            "pr302_availability_guard",
        ),
        ("pr302_event_insert", "agent_availability_events", "INSERT", "pr302_event_guard"),
        (
            "pr302_event_immutable",
            "agent_availability_events",
            "UPDATE OR DELETE",
            "pr302_immutable",
        ),
        ("pr302_agent_actor_write", "actors", "INSERT OR UPDATE", "pr302_identity_insert_guard"),
        (
            "pr302_agent_membership_insert",
            "project_memberships",
            "INSERT",
            "pr302_identity_insert_guard",
        ),
        (
            "pr302_agent_role_write",
            "project_role_assignments",
            "INSERT OR UPDATE",
            "pr302_identity_insert_guard",
        ),
        (
            "pr302_agent_binding_event_insert",
            "actor_subject_binding_events",
            "INSERT",
            "pr302_identity_insert_guard",
        ),
        (
            "pr302_agent_membership_event_insert",
            "project_membership_events",
            "INSERT",
            "pr302_identity_insert_guard",
        ),
        (
            "pr302_agent_role_event_insert",
            "project_role_events",
            "INSERT",
            "pr302_identity_insert_guard",
        ),
    )
    for name, table, timing, function in triggers:
        op.execute(
            f"CREATE TRIGGER {name} BEFORE {timing} ON {table} FOR EACH ROW EXECUTE FUNCTION {function}()"
        )
    op.execute(
        "CREATE CONSTRAINT TRIGGER pr302_receipt_complete_commit AFTER INSERT ON agent_command_receipts DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pr302_receipt_complete()"
    )
    op.execute("DROP TRIGGER trg_actor_binding_human ON actor_subject_bindings")
    op.execute(
        "CREATE TRIGGER trg_actor_binding_human BEFORE INSERT ON actor_subject_bindings FOR EACH ROW EXECUTE FUNCTION pr302_binding_guard()"
    )


def downgrade() -> None:
    raise RuntimeError("0079 is forward-only; approved forward repair required")
