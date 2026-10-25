# ruff: noqa: E501
"""PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged."""

import sqlalchemy as sa
from alembic import op

revision = "0081_agent_execution_intents"
down_revision = "0080_capability_gateway"
branch_labels = None
depends_on = None

DDL = r"""
CREATE TABLE agent_execution_instances (
  id uuid NOT NULL,
  project_id uuid NOT NULL,
  research_task_id uuid NOT NULL,
  research_task_step_id uuid NULL,
  task_revision_at_creation integer NOT NULL,
  agent_version_id uuid NOT NULL,
  actor_id uuid NOT NULL,
  status text NOT NULL,
  revision integer NOT NULL,
  created_at timestamptz NOT NULL,
  input_ref_hash text NOT NULL,
  input_ref_hash_scheme text NOT NULL,
  harness_artifact_version_id uuid NOT NULL,
  harness_content_hash text NOT NULL,
  harness_hash_scheme text NOT NULL
);
CREATE TABLE agent_execution_events (
  id uuid NOT NULL,
  execution_id uuid NOT NULL,
  sequence integer NOT NULL,
  prior_status text NULL,
  new_status text NOT NULL,
  actor_id uuid NOT NULL,
  occurred_at timestamptz NOT NULL,
  reason text NOT NULL,
  receipt_id uuid NOT NULL
);
ALTER TABLE agent_command_receipts ADD COLUMN result_execution_id uuid NULL, ADD COLUMN result_execution_event_id uuid NULL;
ALTER TABLE agent_execution_instances ADD CONSTRAINT pr302s2_exec_pk PRIMARY KEY (id);
ALTER TABLE agent_execution_instances ADD CONSTRAINT pr302s2_exec_project_fk FOREIGN KEY (project_id) REFERENCES projects(id) MATCH SIMPLE ON UPDATE NO ACTION ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE agent_execution_instances ADD CONSTRAINT pr302s2_exec_task_fk FOREIGN KEY (research_task_id, project_id) REFERENCES research_tasks(id, project_id) MATCH SIMPLE ON UPDATE NO ACTION ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE agent_execution_instances ADD CONSTRAINT pr302s2_exec_step_fk FOREIGN KEY (research_task_id, research_task_step_id) REFERENCES research_task_steps(research_task_id, id) MATCH SIMPLE ON UPDATE NO ACTION ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE agent_execution_instances ADD CONSTRAINT pr302s2_exec_version_fk FOREIGN KEY (agent_version_id, project_id, actor_id) REFERENCES agent_versions(id, project_id, actor_id) MATCH SIMPLE ON UPDATE NO ACTION ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE agent_execution_instances ADD CONSTRAINT pr302s2_exec_actor_fk FOREIGN KEY (actor_id) REFERENCES actors(id) MATCH SIMPLE ON UPDATE NO ACTION ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE agent_execution_instances ADD CONSTRAINT pr302s2_exec_harness_fk FOREIGN KEY (harness_artifact_version_id) REFERENCES artifact_versions(id) MATCH SIMPLE ON UPDATE NO ACTION ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE agent_execution_events ADD CONSTRAINT pr302s2_event_pk PRIMARY KEY (id);
ALTER TABLE agent_execution_events ADD CONSTRAINT pr302s2_event_execution_uq UNIQUE (execution_id);
ALTER TABLE agent_execution_events ADD CONSTRAINT pr302s2_event_receipt_uq UNIQUE (receipt_id);
ALTER TABLE agent_execution_events ADD CONSTRAINT pr302s2_event_execution_fk FOREIGN KEY (execution_id) REFERENCES agent_execution_instances(id) MATCH SIMPLE ON UPDATE NO ACTION ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE agent_execution_events ADD CONSTRAINT pr302s2_event_actor_fk FOREIGN KEY (actor_id) REFERENCES actors(id) MATCH SIMPLE ON UPDATE NO ACTION ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE agent_execution_events ADD CONSTRAINT pr302s2_event_receipt_fk FOREIGN KEY (receipt_id) REFERENCES agent_command_receipts(id) MATCH SIMPLE ON UPDATE NO ACTION ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE agent_command_receipts ADD CONSTRAINT pr302s2_receipt_execution_fk FOREIGN KEY (result_execution_id) REFERENCES agent_execution_instances(id) MATCH SIMPLE ON UPDATE NO ACTION ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE agent_command_receipts ADD CONSTRAINT pr302s2_receipt_event_fk FOREIGN KEY (result_execution_event_id) REFERENCES agent_execution_events(id) MATCH SIMPLE ON UPDATE NO ACTION ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE agent_execution_instances ADD CONSTRAINT pr302s2_exec_id_ck CHECK (substring(id::text from 15 for 1) = '7' AND substring(id::text from 20 for 1) IN ('8','9','a','b'));
ALTER TABLE agent_execution_instances ADD CONSTRAINT pr302s2_exec_status_ck CHECK (status = 'CREATED');
ALTER TABLE agent_execution_instances ADD CONSTRAINT pr302s2_exec_revision_ck CHECK (revision = 1);
ALTER TABLE agent_execution_instances ADD CONSTRAINT pr302s2_exec_task_revision_ck CHECK (task_revision_at_creation BETWEEN 1 AND 2147483647);
ALTER TABLE agent_execution_instances ADD CONSTRAINT pr302s2_exec_time_ck CHECK (isfinite(created_at));
ALTER TABLE agent_execution_instances ADD CONSTRAINT pr302s2_exec_hashes_ck CHECK (input_ref_hash ~ '^[0-9a-f]{64}$' AND harness_content_hash ~ '^[0-9a-f]{64}$');
ALTER TABLE agent_execution_instances ADD CONSTRAINT pr302s2_exec_schemes_ck CHECK (input_ref_hash_scheme = 'sha256-cjson-v1' AND harness_hash_scheme = 'sha256-bytes-v1');
ALTER TABLE agent_execution_events ADD CONSTRAINT pr302s2_event_id_ck CHECK (substring(id::text from 15 for 1) = '7' AND substring(id::text from 20 for 1) IN ('8','9','a','b'));
ALTER TABLE agent_execution_events ADD CONSTRAINT pr302s2_event_initial_ck CHECK (sequence = 1 AND prior_status IS NULL AND new_status = 'CREATED');
ALTER TABLE agent_execution_events ADD CONSTRAINT pr302s2_event_time_ck CHECK (isfinite(occurred_at));
ALTER TABLE agent_execution_events ADD CONSTRAINT pr302s2_event_reason_ck CHECK (reason = 'Execution intent created.');
ALTER TABLE agent_command_receipts ADD CONSTRAINT pr302s2_receipt_operation_ck CHECK (operation IN ('provision_project_agent','register_agent_version','change_agent_availability','create_agent_execution'));
ALTER TABLE agent_command_receipts ADD CONSTRAINT pr302s2_receipt_shape_ck CHECK ((
  operation = 'provision_project_agent'
  AND num_nonnulls(result_actor_id, result_binding_id, result_membership_id,
    result_role_assignment_id, result_binding_event_id,
    result_membership_event_id, result_role_event_id) = 7
  AND result_agent_version_id IS NULL AND result_availability_event_id IS NULL
  AND result_execution_id IS NULL AND result_execution_event_id IS NULL
  AND resulting_revision = 1
) OR (
  operation IN ('register_agent_version','change_agent_availability')
  AND num_nonnulls(result_actor_id, result_binding_id, result_membership_id,
    result_role_assignment_id, result_binding_event_id,
    result_membership_event_id, result_role_event_id) = 0
  AND result_agent_version_id IS NOT NULL AND result_availability_event_id IS NOT NULL
  AND result_execution_id IS NULL AND result_execution_event_id IS NULL
  AND ((operation = 'register_agent_version' AND resulting_revision = 1)
    OR (operation = 'change_agent_availability' AND resulting_revision >= 2))
) OR (
  operation = 'create_agent_execution'
  AND num_nonnulls(result_actor_id, result_binding_id, result_membership_id,
    result_role_assignment_id, result_binding_event_id,
    result_membership_event_id, result_role_event_id,
    result_agent_version_id, result_availability_event_id) = 0
  AND result_execution_id IS NOT NULL AND result_execution_event_id IS NOT NULL
  AND resulting_revision = 1
)
);
CREATE INDEX pr302s2_exec_project_task ON agent_execution_instances (project_id, research_task_id, id);
CREATE INDEX pr302s2_exec_task_step ON agent_execution_instances (research_task_id, research_task_step_id);
CREATE INDEX pr302s2_exec_version ON agent_execution_instances (agent_version_id, project_id, actor_id);
CREATE INDEX pr302s2_exec_actor ON agent_execution_instances (actor_id);
CREATE INDEX pr302s2_exec_harness ON agent_execution_instances (harness_artifact_version_id);
CREATE INDEX pr302s2_event_actor ON agent_execution_events (actor_id);
CREATE UNIQUE INDEX pr302s2_receipt_execution_uq ON agent_command_receipts (result_execution_id) WHERE result_execution_id IS NOT NULL;
CREATE UNIQUE INDEX pr302s2_receipt_event_uq ON agent_command_receipts (result_execution_event_id) WHERE result_execution_event_id IS NOT NULL;
"""

BASELINE_CHECKS = {
    "agent_command_receipts_operation_check": "CHECK ((operation = ANY (ARRAY['provision_project_agent'::text, 'register_agent_version'::text, 'change_agent_availability'::text])))",
    "agent_command_receipts_check": "CHECK ((((operation = 'provision_project_agent'::text) AND (result_actor_id IS NOT NULL) AND (result_binding_id IS NOT NULL) AND (result_membership_id IS NOT NULL) AND (result_role_assignment_id IS NOT NULL) AND (result_binding_event_id IS NOT NULL) AND (result_membership_event_id IS NOT NULL) AND (result_role_event_id IS NOT NULL) AND (result_agent_version_id IS NULL) AND (result_availability_event_id IS NULL) AND (resulting_revision = 1)) OR ((operation = ANY (ARRAY['register_agent_version'::text, 'change_agent_availability'::text])) AND (result_actor_id IS NULL) AND (result_binding_id IS NULL) AND (result_membership_id IS NULL) AND (result_role_assignment_id IS NULL) AND (result_binding_event_id IS NULL) AND (result_membership_event_id IS NULL) AND (result_role_event_id IS NULL) AND (result_agent_version_id IS NOT NULL) AND (result_availability_event_id IS NOT NULL) AND ((operation <> 'register_agent_version'::text) OR (resulting_revision = 1)) AND ((operation <> 'change_agent_availability'::text) OR (resulting_revision >= 2)))))",
}

FUNCTIONS = r"""

CREATE FUNCTION pr302s2_cjson(value jsonb) RETURNS text
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE result text;
BEGIN
 IF value IS NULL THEN RAISE EXCEPTION 'unsupported canonical value' USING ERRCODE='22023',CONSTRAINT='pr302s2_value_type'; END IF;
 CASE jsonb_typeof(value)
 WHEN 'null' THEN RETURN 'null';
 WHEN 'boolean' THEN RETURN value::text;
 WHEN 'number' THEN RETURN value::text;
 WHEN 'string' THEN RETURN value::text;
 WHEN 'array' THEN
 SELECT '['||COALESCE(string_agg(pr302s2_cjson(v),',' ORDER BY n),'')||']' INTO result FROM jsonb_array_elements(value) WITH ORDINALITY a(v,n);
 WHEN 'object' THEN
 SELECT '{'||COALESCE(string_agg(to_jsonb(k)::text||':'||pr302s2_cjson(v),',' ORDER BY k COLLATE "C"),'')||'}' INTO result FROM jsonb_each(value) e(k,v);
 ELSE RAISE EXCEPTION 'unsupported canonical value' USING ERRCODE='22023',CONSTRAINT='pr302s2_value_type';
 END CASE;
 RETURN result;
END $$;
CREATE FUNCTION pr302s2_value_digest(value jsonb) RETURNS text
LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,public,pg_temp AS $$
 SELECT encode(sha256(convert_to(pr302s2_cjson(value),'UTF8')),'hex')
$$;
CREATE FUNCTION pr302s2_preheld() RETURNS void
LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE relation_name text;
BEGIN
 IF current_setting('transaction_isolation')<>'read committed' THEN
 RAISE EXCEPTION 'intent isolation' USING ERRCODE='23514',CONSTRAINT='pr302s2_preheld'; END IF;
 FOR relation_name IN SELECT unnest(ARRAY['actor_subject_bindings','actors','artifact_versions','artifacts',
 'claim_versions','claims','hypothesis_versions','hypotheses','literature_source_project_links','literature_sources',
 'manuscript_versions','project_membership_events','project_memberships','project_role_assignments','projects',
 'publications','research_question_versions','research_questions','source_versions','strategy_candidate_captures',
 'strategy_candidate_sources','strategy_hypothesis_admissions','strategy_question_admissions']) LOOP
 IF NOT EXISTS(SELECT 1 FROM pg_locks WHERE pid=pg_backend_pid() AND locktype='relation' AND granted
 AND relation=to_regclass('public.'||relation_name) AND mode IN ('ShareLock','ShareRowExclusiveLock','ExclusiveLock','AccessExclusiveLock')) THEN
 RAISE EXCEPTION 'intent SHARE protection absent' USING ERRCODE='23514',CONSTRAINT='pr302s2_preheld'; END IF;
 END LOOP;
END $$;
CREATE FUNCTION pr302s2_input_material(p_execution uuid) RETURNS jsonb
LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE x agent_execution_instances%ROWTYPE; input_row record; project uuid; owner uuid; version_id uuid; saved_hash text; saved_scheme text;
 saved_status text; frozen timestamptz; scoped boolean; material_items jsonb; material jsonb;
BEGIN
 SELECT * INTO x FROM agent_execution_instances WHERE id=p_execution;
 IF NOT FOUND THEN RAISE EXCEPTION 'intent absent' USING ERRCODE='23514',CONSTRAINT='pr302s2_unresolved'; END IF;
 IF NOT EXISTS(SELECT 1 FROM research_tasks WHERE id=x.research_task_id AND project_id=x.project_id AND plan_sealed_at IS NOT NULL)
 OR (x.research_task_step_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM research_task_steps WHERE id=x.research_task_step_id AND research_task_id=x.research_task_id))
 THEN RAISE EXCEPTION 'input scope' USING ERRCODE='23514',CONSTRAINT='pr302s2_binding'; END IF;
project:=x.project_id;
 material_items:='[]'::jsonb;
 FOR input_row IN SELECT 'TASK'::text owner_kind,research_task_id owner_id,
 research_question_version_id,hypothesis_version_id,claim_version_id,source_version_id,artifact_version_id,manuscript_version_id,content_hash,hash_scheme
 FROM research_task_inputs WHERE research_task_id=x.research_task_id
 UNION ALL SELECT 'STEP',step_id,research_question_version_id,hypothesis_version_id,claim_version_id,source_version_id,artifact_version_id,manuscript_version_id,content_hash,hash_scheme
 FROM research_task_step_inputs WHERE research_task_id=x.research_task_id AND step_id=x.research_task_step_id LOOP
 CASE
 WHEN input_row.research_question_version_id IS NOT NULL THEN
 SELECT v.id,v.content_hash,NULL::text,v.status,v.frozen_at,o.project_id=project
 INTO version_id,saved_hash,saved_scheme,saved_status,frozen,scoped
 FROM research_question_versions v JOIN research_questions o ON o.id=v.research_question_id WHERE v.id=input_row.research_question_version_id;
 WHEN input_row.hypothesis_version_id IS NOT NULL THEN
 SELECT v.id,v.content_hash,NULL::text,v.status,v.frozen_at,o.project_id=project
 INTO version_id,saved_hash,saved_scheme,saved_status,frozen,scoped
 FROM hypothesis_versions v JOIN hypotheses o ON o.id=v.hypothesis_id WHERE v.id=input_row.hypothesis_version_id;
 WHEN input_row.claim_version_id IS NOT NULL THEN
 SELECT v.id,v.content_hash,NULL::text,v.status,v.frozen_at,o.project_id=project
 INTO version_id,saved_hash,saved_scheme,saved_status,frozen,scoped
 FROM claim_versions v JOIN claims o ON o.id=v.claim_id WHERE v.id=input_row.claim_version_id;
 WHEN input_row.source_version_id IS NOT NULL THEN
 SELECT v.id,v.content_hash,v.hash_scheme,v.status,v.frozen_at,EXISTS(SELECT 1 FROM literature_source_project_links l WHERE l.literature_source_id=o.id AND l.project_id=project)
 INTO version_id,saved_hash,saved_scheme,saved_status,frozen,scoped
 FROM source_versions v JOIN literature_sources o ON o.id=v.literature_source_id WHERE v.id=input_row.source_version_id;
 WHEN input_row.artifact_version_id IS NOT NULL THEN
 SELECT v.id,v.content_hash,NULL::text,v.status,v.frozen_at,o.project_id=project
 INTO version_id,saved_hash,saved_scheme,saved_status,frozen,scoped
 FROM artifact_versions v JOIN artifacts o ON o.id=v.artifact_id WHERE v.id=input_row.artifact_version_id;
 WHEN input_row.manuscript_version_id IS NOT NULL THEN
 SELECT v.id,v.content_hash,v.hash_scheme,v.status,v.frozen_at,o.project_id=project
 INTO version_id,saved_hash,saved_scheme,saved_status,frozen,scoped
 FROM manuscript_versions v JOIN publications o ON o.id=v.publication_id WHERE v.id=input_row.manuscript_version_id;
 ELSE RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr302s2_binding'; END CASE;
 IF version_id IS NULL THEN RAISE EXCEPTION 'missing exact input' USING ERRCODE='23514', CONSTRAINT='pr302s2_unresolved'; END IF;
 IF scoped IS DISTINCT FROM true THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr302s2_binding'; END IF;
 IF saved_status NOT IN ('FROZEN','SUPERSEDED') OR frozen IS NULL OR saved_hash IS NULL
   THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr302s2_not_frozen'; END IF;
 IF input_row.content_hash IS DISTINCT FROM saved_hash THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr302s2_provenance'; END IF;
 IF input_row.source_version_id IS NOT NULL OR input_row.manuscript_version_id IS NOT NULL THEN
  IF input_row.hash_scheme IS DISTINCT FROM 'sha256-cjson-v1' OR input_row.hash_scheme IS DISTINCT FROM saved_scheme
    THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr302s2_provenance'; END IF;
 ELSE IF input_row.hash_scheme IS NOT NULL THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr302s2_provenance'; END IF;
 END IF;
 material_items:=material_items||jsonb_build_array(jsonb_build_object(
 'owner_kind',input_row.owner_kind,'owner_id',input_row.owner_id::text,
 'target_kind',CASE WHEN input_row.research_question_version_id IS NOT NULL THEN 'RESEARCH_QUESTION_VERSION'
 WHEN input_row.hypothesis_version_id IS NOT NULL THEN 'HYPOTHESIS_VERSION' WHEN input_row.claim_version_id IS NOT NULL THEN 'CLAIM_VERSION'
 WHEN input_row.source_version_id IS NOT NULL THEN 'SOURCE_VERSION' WHEN input_row.artifact_version_id IS NOT NULL THEN 'ARTIFACT_VERSION' ELSE 'MANUSCRIPT_VERSION' END,
 'target_id',version_id::text,'content_hash',input_row.content_hash,'hash_scheme',input_row.hash_scheme));
 END LOOP;
 SELECT COALESCE(jsonb_agg(v ORDER BY v->>'owner_kind' COLLATE "C",v->>'owner_id' COLLATE "C",v->>'target_kind' COLLATE "C",v->>'target_id' COLLATE "C"),'[]'::jsonb)
 INTO material_items FROM jsonb_array_elements(material_items) v;
 material:=jsonb_build_object('type','AgentExecutionInputs','material_version',1,'project_id',x.project_id::text,
 'research_task_id',x.research_task_id::text,'research_task_step_id',x.research_task_step_id::text,'inputs',material_items);
 RETURN material;
END $$;
CREATE FUNCTION pr302s2_immutable() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$ BEGIN
 RAISE EXCEPTION 'immutable intent history' USING ERRCODE='23514',CONSTRAINT='pr302s2_immutable';
END $$;
CREATE FUNCTION pr302s2_execution_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE x agent_execution_instances%ROWTYPE:=NEW; r agent_command_receipts%ROWTYPE;
 task research_tasks%ROWTYPE; t timestamptz:=clock_timestamp(); pin record; artifact record; key text; h bigint; input_row record; project uuid; owner uuid; version_id uuid; saved_hash text; saved_scheme text;
 saved_status text; frozen timestamptz; scoped boolean; material_items jsonb; material jsonb;
BEGIN
 PERFORM pr302s2_preheld();
 SELECT * INTO r FROM agent_command_receipts WHERE result_execution_id=x.id AND operation='create_agent_execution';
 IF NOT FOUND THEN RAISE EXCEPTION 'intent receipt missing' USING ERRCODE='23514',CONSTRAINT='pr302s2_completeness'; END IF;
 IF NOT EXISTS(SELECT 1 FROM agent_command_receipts WHERE id=r.id AND xmin=pg_current_xact_id()::xid)
 THEN RAISE EXCEPTION 'historical receipt' USING ERRCODE='23514',CONSTRAINT='pr302s2_late_history'; END IF;
FOR key IN SELECT unnest(ARRAY[
 'researchbase-project:'||r.project_id,
 'pr302:command:'||r.project_id||':'||r.caller_actor_id||':'||r.command_id,
 'pr302:actor:'||x.actor_id,'pr301:task:'||x.research_task_id,
 'pr302:version:'||x.agent_version_id,'pr302:execution:'||x.id]) LOOP
 h:=hashtextextended(key,0);
 IF NOT EXISTS(SELECT 1 FROM pg_locks WHERE pid=pg_backend_pid() AND locktype='advisory' AND granted
 AND mode='ExclusiveLock' AND classid=((h>>32)&4294967295)::oid AND objid=(h&4294967295)::oid AND objsubid=1)
 THEN RAISE EXCEPTION 'intent advisory protection absent' USING ERRCODE='23514',CONSTRAINT='pr302s2_preheld'; END IF;
 END LOOP;IF NOT EXISTS (
 SELECT 1 FROM projects p JOIN project_memberships m ON m.project_id=p.id
 JOIN project_role_assignments ro ON ro.membership_id=m.id JOIN actors a ON a.id=m.actor_id
 JOIN actor_subject_bindings b ON b.actor_id=a.id
 WHERE p.id=r.project_id AND p.lifecycle_status='ACTIVE' AND a.id=r.caller_actor_id
 AND a.retired_at IS NULL AND m.status='ACTIVE' AND m.started_at<=t
 AND ro.effective_from<=t AND (ro.effective_until IS NULL OR ro.effective_until>t)
 AND b.status='ACTIVE' AND b.bound_at<=t AND (b.revoked_at IS NULL OR b.revoked_at>t)
 AND ((a.actor_type='HUMAN' AND ro.role IN ('OWNER','RESEARCHER')) OR
 (a.actor_type='AGENT' AND ro.role='RESEARCHER' AND b.subject_kind='MTLS_URI'
 AND b.proof_kind='MTLS_CHALLENGE' AND EXISTS(SELECT 1 FROM agent_command_receipts enrolled
 WHERE enrolled.operation='provision_project_agent' AND enrolled.result_actor_id=a.id
 AND enrolled.project_id=p.id AND enrolled.result_binding_id=b.id)))
 ) THEN RAISE EXCEPTION 'intent caller unavailable' USING ERRCODE='23514',CONSTRAINT='pr302s2_scope'; END IF;
IF NOT EXISTS (
 SELECT 1 FROM actors a JOIN agent_command_receipts enrolled ON enrolled.result_actor_id=a.id
 JOIN actor_subject_bindings b ON b.id=enrolled.result_binding_id
 JOIN project_memberships m ON m.actor_id=a.id AND m.project_id=enrolled.project_id
 JOIN project_role_assignments ro ON ro.membership_id=m.id
 WHERE a.id=x.actor_id AND a.actor_type='AGENT' AND a.retired_at IS NULL
 AND enrolled.operation='provision_project_agent' AND enrolled.project_id=x.project_id
 AND b.status='ACTIVE' AND b.subject_kind='MTLS_URI' AND b.proof_kind='MTLS_CHALLENGE'
 AND b.bound_at<=t AND (b.revoked_at IS NULL OR b.revoked_at>t)
 AND m.status='ACTIVE' AND m.started_at<=t AND ro.role='RESEARCHER'
 AND ro.effective_from<=t AND (ro.effective_until IS NULL OR ro.effective_until>t)
 ) OR EXISTS (SELECT 1 FROM actors WHERE id=r.caller_actor_id AND actor_type='AGENT' AND id<>x.actor_id)
 THEN RAISE EXCEPTION 'exact live Agent required' USING ERRCODE='23514',CONSTRAINT='pr302s2_scope'; END IF;
 SELECT * INTO task FROM research_tasks WHERE id=x.research_task_id;
 IF task.id IS NULL OR task.project_id<>x.project_id OR NOT EXISTS (
 SELECT 1 FROM agent_versions WHERE id=x.agent_version_id AND project_id=x.project_id AND actor_id=x.actor_id)
 OR (x.research_task_step_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM research_task_steps WHERE id=x.research_task_step_id AND research_task_id=x.research_task_id))
 THEN RAISE EXCEPTION 'intent scope binding' USING ERRCODE='23514',CONSTRAINT='pr302s2_binding'; END IF;
 IF task.status<>'PLANNING' OR task.plan_sealed_at IS NULL
 OR (x.research_task_step_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM research_task_steps WHERE id=x.research_task_step_id AND status='PENDING'))
 OR NOT EXISTS(SELECT 1 FROM agent_availability WHERE agent_version_id=x.agent_version_id AND status='ACTIVE')
 THEN RAISE EXCEPTION 'intent state' USING ERRCODE='23514',CONSTRAINT='pr302s2_state'; END IF;
 IF task.row_version<>x.task_revision_at_creation THEN RAISE EXCEPTION 'task revision' USING ERRCODE='23514',CONSTRAINT='pr302s2_cas'; END IF;
FOR pin IN SELECT x.harness_artifact_version_id id,x.harness_content_hash hash
 UNION ALL SELECT configuration_artifact_version_id,configuration_content_hash FROM agent_versions WHERE id=x.agent_version_id LOOP
 SELECT av.*,a.project_id INTO artifact FROM artifact_versions av JOIN artifacts a ON a.id=av.artifact_id WHERE av.id=pin.id;
 IF NOT FOUND THEN RAISE EXCEPTION 'pin absent' USING ERRCODE='23514',CONSTRAINT='pr302s2_unresolved'; END IF;
 IF artifact.project_id IS DISTINCT FROM x.project_id THEN RAISE EXCEPTION 'pin scope' USING ERRCODE='23514',CONSTRAINT='pr302s2_binding'; END IF;
 IF artifact.status NOT IN ('FROZEN','SUPERSEDED') OR artifact.frozen_at IS NULL THEN RAISE EXCEPTION 'pin not frozen' USING ERRCODE='23514',CONSTRAINT='pr302s2_not_frozen'; END IF;
 IF artifact.content_hash IS DISTINCT FROM pin.hash OR artifact.locator IS DISTINCT FROM 'sha256:'||pin.hash OR artifact.byte_size IS NULL
 THEN RAISE EXCEPTION 'pin metadata' USING ERRCODE='23514',CONSTRAINT='pr302s2_provenance'; END IF;
 END LOOP;
project:=x.project_id;
 material_items:='[]'::jsonb;
 FOR input_row IN SELECT 'TASK'::text owner_kind,research_task_id owner_id,
 research_question_version_id,hypothesis_version_id,claim_version_id,source_version_id,artifact_version_id,manuscript_version_id,content_hash,hash_scheme
 FROM research_task_inputs WHERE research_task_id=x.research_task_id
 UNION ALL SELECT 'STEP',step_id,research_question_version_id,hypothesis_version_id,claim_version_id,source_version_id,artifact_version_id,manuscript_version_id,content_hash,hash_scheme
 FROM research_task_step_inputs WHERE research_task_id=x.research_task_id AND step_id=x.research_task_step_id LOOP
 CASE
 WHEN input_row.research_question_version_id IS NOT NULL THEN
 SELECT v.id,v.content_hash,NULL::text,v.status,v.frozen_at,o.project_id=project
 INTO version_id,saved_hash,saved_scheme,saved_status,frozen,scoped
 FROM research_question_versions v JOIN research_questions o ON o.id=v.research_question_id WHERE v.id=input_row.research_question_version_id;
 WHEN input_row.hypothesis_version_id IS NOT NULL THEN
 SELECT v.id,v.content_hash,NULL::text,v.status,v.frozen_at,o.project_id=project
 INTO version_id,saved_hash,saved_scheme,saved_status,frozen,scoped
 FROM hypothesis_versions v JOIN hypotheses o ON o.id=v.hypothesis_id WHERE v.id=input_row.hypothesis_version_id;
 WHEN input_row.claim_version_id IS NOT NULL THEN
 SELECT v.id,v.content_hash,NULL::text,v.status,v.frozen_at,o.project_id=project
 INTO version_id,saved_hash,saved_scheme,saved_status,frozen,scoped
 FROM claim_versions v JOIN claims o ON o.id=v.claim_id WHERE v.id=input_row.claim_version_id;
 WHEN input_row.source_version_id IS NOT NULL THEN
 SELECT v.id,v.content_hash,v.hash_scheme,v.status,v.frozen_at,EXISTS(SELECT 1 FROM literature_source_project_links l WHERE l.literature_source_id=o.id AND l.project_id=project)
 INTO version_id,saved_hash,saved_scheme,saved_status,frozen,scoped
 FROM source_versions v JOIN literature_sources o ON o.id=v.literature_source_id WHERE v.id=input_row.source_version_id;
 WHEN input_row.artifact_version_id IS NOT NULL THEN
 SELECT v.id,v.content_hash,NULL::text,v.status,v.frozen_at,o.project_id=project
 INTO version_id,saved_hash,saved_scheme,saved_status,frozen,scoped
 FROM artifact_versions v JOIN artifacts o ON o.id=v.artifact_id WHERE v.id=input_row.artifact_version_id;
 WHEN input_row.manuscript_version_id IS NOT NULL THEN
 SELECT v.id,v.content_hash,v.hash_scheme,v.status,v.frozen_at,o.project_id=project
 INTO version_id,saved_hash,saved_scheme,saved_status,frozen,scoped
 FROM manuscript_versions v JOIN publications o ON o.id=v.publication_id WHERE v.id=input_row.manuscript_version_id;
 ELSE RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr302s2_binding'; END CASE;
 IF version_id IS NULL THEN RAISE EXCEPTION 'missing exact input' USING ERRCODE='23514', CONSTRAINT='pr302s2_unresolved'; END IF;
 IF scoped IS DISTINCT FROM true THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr302s2_binding'; END IF;
 IF saved_status NOT IN ('FROZEN','SUPERSEDED') OR frozen IS NULL OR saved_hash IS NULL
   THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr302s2_not_frozen'; END IF;
 IF input_row.content_hash IS DISTINCT FROM saved_hash THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr302s2_provenance'; END IF;
 IF input_row.source_version_id IS NOT NULL OR input_row.manuscript_version_id IS NOT NULL THEN
  IF input_row.hash_scheme IS DISTINCT FROM 'sha256-cjson-v1' OR input_row.hash_scheme IS DISTINCT FROM saved_scheme
    THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr302s2_provenance'; END IF;
 ELSE IF input_row.hash_scheme IS NOT NULL THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE='23514', CONSTRAINT='pr302s2_provenance'; END IF;
 END IF;
 material_items:=material_items||jsonb_build_array(jsonb_build_object(
 'owner_kind',input_row.owner_kind,'owner_id',input_row.owner_id::text,
 'target_kind',CASE WHEN input_row.research_question_version_id IS NOT NULL THEN 'RESEARCH_QUESTION_VERSION'
 WHEN input_row.hypothesis_version_id IS NOT NULL THEN 'HYPOTHESIS_VERSION' WHEN input_row.claim_version_id IS NOT NULL THEN 'CLAIM_VERSION'
 WHEN input_row.source_version_id IS NOT NULL THEN 'SOURCE_VERSION' WHEN input_row.artifact_version_id IS NOT NULL THEN 'ARTIFACT_VERSION' ELSE 'MANUSCRIPT_VERSION' END,
 'target_id',version_id::text,'content_hash',input_row.content_hash,'hash_scheme',input_row.hash_scheme));
 END LOOP;
 SELECT COALESCE(jsonb_agg(v ORDER BY v->>'owner_kind' COLLATE "C",v->>'owner_id' COLLATE "C",v->>'target_kind' COLLATE "C",v->>'target_id' COLLATE "C"),'[]'::jsonb)
 INTO material_items FROM jsonb_array_elements(material_items) v;
 material:=jsonb_build_object('type','AgentExecutionInputs','material_version',1,'project_id',x.project_id::text,
 'research_task_id',x.research_task_id::text,'research_task_step_id',x.research_task_step_id::text,'inputs',material_items);

 IF x.project_id<>r.project_id OR x.status<>'CREATED' OR x.revision<>1 OR x.created_at<>r.recorded_at
 OR x.input_ref_hash<>pr302s2_value_digest(material) THEN
 RAISE EXCEPTION 'intent material contradiction' USING ERRCODE='23514',CONSTRAINT='pr302s2_provenance'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION pr302s2_event_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE x agent_execution_instances%ROWTYPE; r agent_command_receipts%ROWTYPE; key text; h bigint;
BEGIN
 PERFORM pr302s2_preheld();
 SELECT * INTO r FROM agent_command_receipts WHERE id=NEW.receipt_id;
 SELECT * INTO x FROM agent_execution_instances WHERE id=NEW.execution_id;
 IF r.id IS NULL OR x.id IS NULL THEN RAISE EXCEPTION 'intent event scope missing' USING ERRCODE='23514',CONSTRAINT='pr302s2_completeness'; END IF;
 IF NOT EXISTS(SELECT 1 FROM agent_command_receipts WHERE id=r.id AND xmin=pg_current_xact_id()::xid)
 OR NOT EXISTS(SELECT 1 FROM agent_execution_instances WHERE id=x.id AND xmin=pg_current_xact_id()::xid)
 THEN RAISE EXCEPTION 'historical event attachment' USING ERRCODE='23514',CONSTRAINT='pr302s2_late_history'; END IF;
FOR key IN SELECT unnest(ARRAY[
 'researchbase-project:'||r.project_id,
 'pr302:command:'||r.project_id||':'||r.caller_actor_id||':'||r.command_id,
 'pr302:actor:'||x.actor_id,'pr301:task:'||x.research_task_id,
 'pr302:version:'||x.agent_version_id,'pr302:execution:'||x.id]) LOOP
 h:=hashtextextended(key,0);
 IF NOT EXISTS(SELECT 1 FROM pg_locks WHERE pid=pg_backend_pid() AND locktype='advisory' AND granted
 AND mode='ExclusiveLock' AND classid=((h>>32)&4294967295)::oid AND objid=(h&4294967295)::oid AND objsubid=1)
 THEN RAISE EXCEPTION 'intent advisory protection absent' USING ERRCODE='23514',CONSTRAINT='pr302s2_preheld'; END IF;
 END LOOP;
 IF r.operation<>'create_agent_execution' OR r.result_execution_id IS DISTINCT FROM x.id
 OR r.result_execution_event_id IS DISTINCT FROM NEW.id OR r.project_id<>x.project_id
 OR NEW.sequence<>1 OR NEW.prior_status IS NOT NULL OR NEW.new_status<>'CREATED'
 OR NEW.actor_id<>r.caller_actor_id OR NEW.occurred_at<>r.recorded_at OR x.created_at<>r.recorded_at
 OR NEW.reason<>'Execution intent created.' THEN
 RAISE EXCEPTION 'initial intent event contradiction' USING ERRCODE='23514',CONSTRAINT='pr302s2_completeness'; END IF;
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION pr302_receipt_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE t timestamptz := clock_timestamp(); r agent_command_receipts%ROWTYPE; key text; h bigint;
BEGIN
 NEW.recorded_at := t;
 IF NEW.operation='create_agent_execution' THEN
 r:=NEW;
 PERFORM pr302s2_preheld();
 IF NOT EXISTS (
 SELECT 1 FROM projects p JOIN project_memberships m ON m.project_id=p.id
 JOIN project_role_assignments ro ON ro.membership_id=m.id JOIN actors a ON a.id=m.actor_id
 JOIN actor_subject_bindings b ON b.actor_id=a.id
 WHERE p.id=r.project_id AND p.lifecycle_status='ACTIVE' AND a.id=r.caller_actor_id
 AND a.retired_at IS NULL AND m.status='ACTIVE' AND m.started_at<=t
 AND ro.effective_from<=t AND (ro.effective_until IS NULL OR ro.effective_until>t)
 AND b.status='ACTIVE' AND b.bound_at<=t AND (b.revoked_at IS NULL OR b.revoked_at>t)
 AND ((a.actor_type='HUMAN' AND ro.role IN ('OWNER','RESEARCHER')) OR
 (a.actor_type='AGENT' AND ro.role='RESEARCHER' AND b.subject_kind='MTLS_URI'
 AND b.proof_kind='MTLS_CHALLENGE' AND EXISTS(SELECT 1 FROM agent_command_receipts enrolled
 WHERE enrolled.operation='provision_project_agent' AND enrolled.result_actor_id=a.id
 AND enrolled.project_id=p.id AND enrolled.result_binding_id=b.id)))
 ) THEN RAISE EXCEPTION 'intent caller unavailable' USING ERRCODE='23514',CONSTRAINT='pr302s2_scope'; END IF;
 key:='pr302:command:'||NEW.project_id||':'||NEW.caller_actor_id||':'||NEW.command_id;
 h:=hashtextextended(key,0);
 IF NOT EXISTS(SELECT 1 FROM pg_locks WHERE pid=pg_backend_pid() AND locktype='advisory' AND granted AND mode='ExclusiveLock'
 AND classid=((h>>32)&4294967295)::oid AND objid=(h&4294967295)::oid AND objsubid=1)
 THEN RAISE EXCEPTION 'intent command protection absent' USING ERRCODE='23514',CONSTRAINT='pr302s2_preheld'; END IF;
 RETURN NEW;
 END IF;

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

CREATE OR REPLACE FUNCTION pr302_receipt_complete() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE r agent_command_receipts%ROWTYPE; t timestamptz := clock_timestamp(); n integer; x agent_execution_instances%ROWTYPE; initial_event agent_execution_events%ROWTYPE; task research_tasks%ROWTYPE;
BEGIN
 SELECT * INTO r FROM agent_command_receipts WHERE id=NEW.id;
 IF r.operation='create_agent_execution' THEN
 SELECT * INTO x FROM agent_execution_instances WHERE id=r.result_execution_id;
 SELECT * INTO initial_event FROM agent_execution_events WHERE id=r.result_execution_event_id;
 IF x.id IS NULL OR initial_event.id IS NULL OR NOT EXISTS(SELECT 1 FROM agent_command_receipts WHERE id=r.id AND xmin=pg_current_xact_id()::xid)
 OR NOT EXISTS(SELECT 1 FROM agent_execution_instances WHERE id=x.id AND xmin=pg_current_xact_id()::xid)
 OR NOT EXISTS(SELECT 1 FROM agent_execution_events WHERE id=initial_event.id AND xmin=pg_current_xact_id()::xid)
 OR x.project_id IS DISTINCT FROM r.project_id OR initial_event.execution_id IS DISTINCT FROM x.id OR initial_event.receipt_id IS DISTINCT FROM r.id
 OR initial_event.actor_id IS DISTINCT FROM r.caller_actor_id OR initial_event.occurred_at IS DISTINCT FROM r.recorded_at OR x.created_at IS DISTINCT FROM r.recorded_at
 OR r.resulting_revision<>1 OR x.revision<>1 OR x.status<>'CREATED' OR initial_event.sequence<>1 OR initial_event.prior_status IS NOT NULL OR initial_event.new_status<>'CREATED'
 OR (SELECT count(*) FROM agent_execution_events WHERE execution_id=x.id OR receipt_id=r.id)<>1
 THEN RAISE EXCEPTION 'intent closure incomplete' USING ERRCODE='23514',CONSTRAINT='pr302s2_completeness'; END IF;
 IF NOT EXISTS (
 SELECT 1 FROM projects p JOIN project_memberships m ON m.project_id=p.id
 JOIN project_role_assignments ro ON ro.membership_id=m.id JOIN actors a ON a.id=m.actor_id
 JOIN actor_subject_bindings b ON b.actor_id=a.id
 WHERE p.id=r.project_id AND p.lifecycle_status='ACTIVE' AND a.id=r.caller_actor_id
 AND a.retired_at IS NULL AND m.status='ACTIVE' AND m.started_at<=t
 AND ro.effective_from<=t AND (ro.effective_until IS NULL OR ro.effective_until>t)
 AND b.status='ACTIVE' AND b.bound_at<=t AND (b.revoked_at IS NULL OR b.revoked_at>t)
 AND ((a.actor_type='HUMAN' AND ro.role IN ('OWNER','RESEARCHER')) OR
 (a.actor_type='AGENT' AND ro.role='RESEARCHER' AND b.subject_kind='MTLS_URI'
 AND b.proof_kind='MTLS_CHALLENGE' AND EXISTS(SELECT 1 FROM agent_command_receipts enrolled
 WHERE enrolled.operation='provision_project_agent' AND enrolled.result_actor_id=a.id
 AND enrolled.project_id=p.id AND enrolled.result_binding_id=b.id)))
 ) THEN RAISE EXCEPTION 'intent caller unavailable' USING ERRCODE='23514',CONSTRAINT='pr302s2_scope'; END IF;
IF NOT EXISTS (
 SELECT 1 FROM actors a JOIN agent_command_receipts enrolled ON enrolled.result_actor_id=a.id
 JOIN actor_subject_bindings b ON b.id=enrolled.result_binding_id
 JOIN project_memberships m ON m.actor_id=a.id AND m.project_id=enrolled.project_id
 JOIN project_role_assignments ro ON ro.membership_id=m.id
 WHERE a.id=x.actor_id AND a.actor_type='AGENT' AND a.retired_at IS NULL
 AND enrolled.operation='provision_project_agent' AND enrolled.project_id=x.project_id
 AND b.status='ACTIVE' AND b.subject_kind='MTLS_URI' AND b.proof_kind='MTLS_CHALLENGE'
 AND b.bound_at<=t AND (b.revoked_at IS NULL OR b.revoked_at>t)
 AND m.status='ACTIVE' AND m.started_at<=t AND ro.role='RESEARCHER'
 AND ro.effective_from<=t AND (ro.effective_until IS NULL OR ro.effective_until>t)
 ) OR EXISTS (SELECT 1 FROM actors WHERE id=r.caller_actor_id AND actor_type='AGENT' AND id<>x.actor_id)
 THEN RAISE EXCEPTION 'exact live Agent required' USING ERRCODE='23514',CONSTRAINT='pr302s2_scope'; END IF;
 SELECT * INTO task FROM research_tasks WHERE id=x.research_task_id;
 IF task.id IS NULL OR task.project_id<>x.project_id OR NOT EXISTS (
 SELECT 1 FROM agent_versions WHERE id=x.agent_version_id AND project_id=x.project_id AND actor_id=x.actor_id)
 OR (x.research_task_step_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM research_task_steps WHERE id=x.research_task_step_id AND research_task_id=x.research_task_id))
 THEN RAISE EXCEPTION 'intent scope binding' USING ERRCODE='23514',CONSTRAINT='pr302s2_binding'; END IF;
 IF task.status<>'PLANNING' OR task.plan_sealed_at IS NULL
 OR (x.research_task_step_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM research_task_steps WHERE id=x.research_task_step_id AND status='PENDING'))
 OR NOT EXISTS(SELECT 1 FROM agent_availability WHERE agent_version_id=x.agent_version_id AND status='ACTIVE')
 THEN RAISE EXCEPTION 'intent state' USING ERRCODE='23514',CONSTRAINT='pr302s2_state'; END IF;
 IF task.row_version<>x.task_revision_at_creation THEN RAISE EXCEPTION 'task revision' USING ERRCODE='23514',CONSTRAINT='pr302s2_cas'; END IF;

 IF NOT EXISTS (
 SELECT 1 FROM artifact_versions harness JOIN artifacts ha ON ha.id=harness.artifact_id
 JOIN agent_versions version ON version.id=x.agent_version_id
 JOIN artifact_versions config ON config.id=version.configuration_artifact_version_id
 JOIN artifacts ca ON ca.id=config.artifact_id
 WHERE harness.id=x.harness_artifact_version_id AND ha.project_id=x.project_id AND ca.project_id=x.project_id
 AND harness.status IN ('FROZEN','SUPERSEDED') AND harness.frozen_at IS NOT NULL
 AND config.status IN ('FROZEN','SUPERSEDED') AND config.frozen_at IS NOT NULL
 AND harness.content_hash=x.harness_content_hash AND config.content_hash=version.configuration_content_hash
 AND harness.locator='sha256:'||x.harness_content_hash AND config.locator='sha256:'||version.configuration_content_hash
 AND harness.byte_size IS NOT NULL AND config.byte_size IS NOT NULL
 ) THEN RAISE EXCEPTION 'intent final pin contradiction' USING ERRCODE='23514',CONSTRAINT='pr302s2_provenance'; END IF;
 IF x.input_ref_hash<>pr302s2_value_digest(pr302s2_input_material(x.id)) OR r.request_hash<>pr302s2_value_digest(jsonb_build_object(
 'type','AgentCommandMaterial','material_version',1,'operation','create_agent_execution',
 'project_id',r.project_id::text,'caller_actor_id',r.caller_actor_id::text,'command_id',r.command_id::text,
 'expected_revision',NULL,'arguments',jsonb_build_object('execution_id',x.id::text,'agent_version_id',x.agent_version_id::text,
 'research_task_id',x.research_task_id::text,'research_task_step_id',x.research_task_step_id::text,
 'expected_task_revision',x.task_revision_at_creation,'harness_artifact_version_id',x.harness_artifact_version_id::text)))
 THEN RAISE EXCEPTION 'intent digest contradiction' USING ERRCODE='23514',CONSTRAINT='pr302s2_provenance'; END IF;
 RETURN NULL;
 END IF;

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
CREATE TRIGGER pr302s2_execution_insert BEFORE INSERT ON agent_execution_instances FOR EACH ROW EXECUTE FUNCTION pr302s2_execution_guard();
CREATE TRIGGER pr302s2_execution_immutable BEFORE UPDATE OR DELETE ON agent_execution_instances FOR EACH ROW EXECUTE FUNCTION pr302s2_immutable();
CREATE TRIGGER pr302s2_event_insert BEFORE INSERT ON agent_execution_events FOR EACH ROW EXECUTE FUNCTION pr302s2_event_guard();
CREATE TRIGGER pr302s2_event_immutable BEFORE UPDATE OR DELETE ON agent_execution_events FOR EACH ROW EXECUTE FUNCTION pr302s2_immutable();
REVOKE INSERT,UPDATE,DELETE,TRUNCATE ON agent_execution_instances,agent_execution_events FROM PUBLIC;
"""


def upgrade() -> None:
    connection = op.get_bind()
    actual = dict(
        connection.execute(
            sa.text(
                "SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='agent_command_receipts'::regclass AND conname IN ('agent_command_receipts_operation_check','agent_command_receipts_check')"
            )
        ).all()
    )
    if actual != BASELINE_CHECKS:
        raise RuntimeError("S2 receipt CHECK catalog drift; forward migration refused")
    for name in BASELINE_CHECKS:
        op.execute(f"ALTER TABLE agent_command_receipts DROP CONSTRAINT {name}")
    op.execute(DDL)
    op.execute(FUNCTIONS)
    # Cover explicit and default privileges of pre-existing normal roles as well as PUBLIC.
    roles = (
        connection.execute(
            sa.text(
                "SELECT DISTINCT grantee FROM information_schema.table_privileges WHERE table_schema='public' AND table_name IN ('agent_execution_instances','agent_execution_events') AND grantee<>current_user AND grantee<>'PUBLIC'"
            )
        )
        .scalars()
        .all()
    )
    for role in roles:
        quoted = connection.dialect.identifier_preparer.quote(role)
        op.execute(
            f"REVOKE INSERT,UPDATE,DELETE,TRUNCATE ON agent_execution_instances,agent_execution_events FROM {quoted}"
        )


def downgrade() -> None:
    raise RuntimeError("0081 is forward-only; approved forward repair required")
