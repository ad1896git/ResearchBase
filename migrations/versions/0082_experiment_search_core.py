"""PR3-16 bounded storage, frozen by ADR-0029; no production node activation.

The SQL comes from the admitted four-table design at 13fc58a. The identity-key
clarification is ADR-0029 clause 2. Existing migration bytes are never modified.
"""

import hashlib
import json

import sqlalchemy as sa
from alembic import op

revision = "0082_experiment_search_core"
down_revision = "0081_agent_execution_intents"
branch_labels = None
depends_on = None

SCALAR_FUNCTIONS = r"""
CREATE FUNCTION pr316_uuid7(v uuid) RETURNS boolean
LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,public,pg_temp AS $$
SELECT substring(v::text from 15 for 1)= '7'
AND substring(v::text from 20 for 1) IN ( '8' , '9' , 'a' , 'b' )
$$;
CREATE FUNCTION pr316_reason(v text) RETURNS boolean
LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,public,pg_temp AS $$
SELECT char_length(v) BETWEEN 1 AND 8192 AND v IS NFC NORMALIZED
AND btrim(v,U&'\0009\000A\000B\000C\000D\001C\001D\001E\001F\0020\0085\00A0\1680\2000\2001' ||
 U&'\2002\2003\2004\2005\2006'
 ||
U&'\2007\2008\2009\200A\2028\2029\202F\205F\3000' )<> ''
$$;
CREATE FUNCTION pr316_command_event(v text) RETURNS text
LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,public,pg_temp AS $$
SELECT CASE v
WHEN 'create_search_session' THEN 'SEARCH_SESSION_CREATED'
WHEN 'append_search_node' THEN 'SEARCH_NODE_APPENDED' END
$$;
"""

SESSIONS = r"""
CREATE TABLE experiment_search_sessions (
id uuid CONSTRAINT pr316_session_id_nn NOT NULL,
project_id uuid CONSTRAINT pr316_session_project_id_nn NOT NULL,
research_task_id uuid CONSTRAINT pr316_session_research_task_id_nn NOT NULL,
budget_id uuid CONSTRAINT pr316_session_budget_id_nn NOT NULL,
root_hypothesis_version_id uuid NULL,
root_hypothesis_content_hash text NULL,
root_experiment_spec_version_id uuid NULL,
root_experiment_spec_content_hash text NULL,
created_by uuid CONSTRAINT pr316_session_created_by_nn NOT NULL,
created_at timestamptz CONSTRAINT pr316_session_created_at_nn NOT NULL,
receipt_id uuid CONSTRAINT pr316_session_receipt_id_nn NOT NULL
);
ALTER TABLE experiment_search_sessions ADD CONSTRAINT pr316_session_pk PRIMARY KEY (id);
ALTER TABLE experiment_search_sessions ADD CONSTRAINT pr316_session_id_ck CHECK
 (pr316_uuid7(id));
ALTER TABLE experiment_search_sessions ADD CONSTRAINT pr316_session_time_ck CHECK
 (isfinite(created_at));
ALTER TABLE experiment_search_sessions ADD CONSTRAINT pr316_session_receipt_uq UNIQUE
 (receipt_id);
ALTER TABLE experiment_search_sessions ADD CONSTRAINT pr316_session_actor_fk FOREIGN KEY
 (created_by) REFERENCES actors(id) ON UPDATE NO ACTION ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE experiment_search_sessions ADD CONSTRAINT pr316_session_receipt_fk FOREIGN KEY
 (research_task_id,receipt_id) REFERENCES research_task_command_receipts(research_task_id,id) ON
 UPDATE NO ACTION ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE experiment_search_sessions ADD CONSTRAINT pr316_session_scope_uq UNIQUE
 (research_task_id,id);
ALTER TABLE experiment_search_sessions ADD CONSTRAINT pr316_session_project_uq UNIQUE
 (research_task_id,project_id,id);
ALTER TABLE experiment_search_sessions ADD CONSTRAINT pr316_session_task_fk FOREIGN KEY
 (research_task_id,project_id) REFERENCES research_tasks(id,project_id) ON UPDATE NO ACTION ON
 DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE experiment_search_sessions ADD CONSTRAINT pr316_session_budget_fk FOREIGN KEY
 (research_task_id,budget_id) REFERENCES execution_budgets(research_task_id,id) ON UPDATE NO
 ACTION ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE experiment_search_sessions ADD CONSTRAINT pr316_session_hypothesis_fk FOREIGN KEY
 (root_hypothesis_version_id) REFERENCES hypothesis_versions(id) ON UPDATE NO ACTION ON DELETE
 RESTRICT NOT DEFERRABLE;
ALTER TABLE experiment_search_sessions ADD CONSTRAINT pr316_session_hypothesis_pair_ck CHECK
 ((root_hypothesis_version_id IS NULL AND root_hypothesis_content_hash IS NULL) OR
 (root_hypothesis_version_id IS NOT NULL AND root_hypothesis_content_hash IS NOT NULL AND
 root_hypothesis_content_hash ~ '^[0-9a-f]{64}$' ));
ALTER TABLE experiment_search_sessions ADD CONSTRAINT pr316_session_experiment_spec_fk FOREIGN
 KEY (root_experiment_spec_version_id) REFERENCES experiment_spec_versions(id) ON UPDATE NO
 ACTION ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE experiment_search_sessions ADD CONSTRAINT pr316_session_experiment_spec_pair_ck
 CHECK ((root_experiment_spec_version_id IS NULL AND root_experiment_spec_content_hash IS NULL)
 OR (root_experiment_spec_version_id IS NOT NULL AND root_experiment_spec_content_hash IS NOT
 NULL AND root_experiment_spec_content_hash ~ '^[0-9a-f]{64}$' ));
"""

NODES = r"""
CREATE TABLE experiment_search_nodes (
id uuid CONSTRAINT pr316_node_id_nn NOT NULL,
research_task_id uuid CONSTRAINT pr316_node_research_task_id_nn NOT NULL,
search_session_id uuid CONSTRAINT pr316_node_search_session_id_nn NOT NULL,
parent_node_id uuid NULL,
depth integer CONSTRAINT pr316_node_depth_nn NOT NULL,
branch_kind text CONSTRAINT pr316_node_branch_kind_nn NOT NULL,
mutation_reason text CONSTRAINT pr316_node_mutation_reason_nn NOT NULL,
hypothesis_version_id uuid NULL,
hypothesis_content_hash text NULL,
experiment_spec_version_id uuid NULL,
experiment_spec_content_hash text NULL,
reservation_id uuid CONSTRAINT pr316_node_reservation_id_nn NOT NULL,
created_by uuid CONSTRAINT pr316_node_created_by_nn NOT NULL,
created_at timestamptz CONSTRAINT pr316_node_created_at_nn NOT NULL,
receipt_id uuid CONSTRAINT pr316_node_receipt_id_nn NOT NULL
);
ALTER TABLE experiment_search_nodes ADD CONSTRAINT pr316_node_pk PRIMARY KEY (id);
ALTER TABLE experiment_search_nodes ADD CONSTRAINT pr316_node_id_ck CHECK (pr316_uuid7(id));
ALTER TABLE experiment_search_nodes ADD CONSTRAINT pr316_node_time_ck CHECK
 (isfinite(created_at));
ALTER TABLE experiment_search_nodes ADD CONSTRAINT pr316_node_receipt_uq UNIQUE (receipt_id);
ALTER TABLE experiment_search_nodes ADD CONSTRAINT pr316_node_actor_fk FOREIGN KEY (created_by)
 REFERENCES actors(id) ON UPDATE NO ACTION ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE experiment_search_nodes ADD CONSTRAINT pr316_node_receipt_fk FOREIGN KEY
 (research_task_id,receipt_id) REFERENCES research_task_command_receipts(research_task_id,id) ON
 UPDATE NO ACTION ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE experiment_search_nodes ADD CONSTRAINT pr316_node_scope_uq UNIQUE
 (research_task_id,search_session_id,id);
ALTER TABLE experiment_search_nodes ADD CONSTRAINT pr316_node_session_fk FOREIGN KEY
 (research_task_id,search_session_id) REFERENCES experiment_search_sessions(research_task_id,id)
 ON UPDATE NO ACTION ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE experiment_search_nodes ADD CONSTRAINT pr316_node_parent_fk FOREIGN KEY
 (research_task_id,search_session_id,parent_node_id) REFERENCES
 experiment_search_nodes(research_task_id,search_session_id,id) ON UPDATE NO ACTION ON DELETE
 RESTRICT NOT DEFERRABLE;
ALTER TABLE experiment_search_nodes ADD CONSTRAINT pr316_node_reservation_fk FOREIGN KEY
 (research_task_id,reservation_id,id) REFERENCES
 budget_reservations(research_task_id,id,operation_id) ON UPDATE NO ACTION ON DELETE RESTRICT
 NOT DEFERRABLE;
ALTER TABLE experiment_search_nodes ADD CONSTRAINT pr316_node_reservation_uq UNIQUE
 (reservation_id);
ALTER TABLE experiment_search_nodes ADD CONSTRAINT pr316_node_depth_ck CHECK ((parent_node_id IS
 NULL AND depth=0) OR (parent_node_id IS NOT NULL AND parent_node_id<>id AND depth>0));
ALTER TABLE experiment_search_nodes ADD CONSTRAINT pr316_node_branch_ck CHECK (branch_kind IN (
 'NEW_DIRECTION' , 'REFINEMENT' , 'ABLATION' , 'BASELINE' , 'SCALE_UP' , 'DEBUG' , 'REPLICATION'
 ));
ALTER TABLE experiment_search_nodes ADD CONSTRAINT pr316_node_reason_ck CHECK
 (pr316_reason(mutation_reason));
ALTER TABLE experiment_search_nodes ADD CONSTRAINT pr316_node_hypothesis_fk FOREIGN KEY
 (hypothesis_version_id) REFERENCES hypothesis_versions(id) ON UPDATE NO ACTION ON DELETE
 RESTRICT NOT DEFERRABLE;
ALTER TABLE experiment_search_nodes ADD CONSTRAINT pr316_node_hypothesis_pair_ck CHECK
 ((hypothesis_version_id IS NULL AND hypothesis_content_hash IS NULL) OR (hypothesis_version_id
 IS NOT NULL AND hypothesis_content_hash IS NOT NULL AND hypothesis_content_hash ~
 '^[0-9a-f]{64}$' ));
ALTER TABLE experiment_search_nodes ADD CONSTRAINT pr316_node_experiment_spec_fk FOREIGN KEY
 (experiment_spec_version_id) REFERENCES experiment_spec_versions(id) ON UPDATE NO ACTION ON
 DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE experiment_search_nodes ADD CONSTRAINT pr316_node_experiment_spec_pair_ck CHECK
 ((experiment_spec_version_id IS NULL AND experiment_spec_content_hash IS NULL) OR
 (experiment_spec_version_id IS NOT NULL AND experiment_spec_content_hash IS NOT NULL AND
 experiment_spec_content_hash ~ '^[0-9a-f]{64}$' ));
"""

NODE_RUNS = r"""
ALTER TABLE runs ADD CONSTRAINT pr316_run_project_uq UNIQUE (id,project_id);
CREATE TABLE experiment_search_node_runs (
id uuid CONSTRAINT pr316_link_id_nn NOT NULL,
project_id uuid CONSTRAINT pr316_link_project_id_nn NOT NULL,
research_task_id uuid CONSTRAINT pr316_link_research_task_id_nn NOT NULL,
search_session_id uuid CONSTRAINT pr316_link_search_session_id_nn NOT NULL,
node_id uuid CONSTRAINT pr316_link_node_id_nn NOT NULL,
run_id uuid CONSTRAINT pr316_link_run_id_nn NOT NULL,
created_by uuid CONSTRAINT pr316_link_created_by_nn NOT NULL,
created_at timestamptz CONSTRAINT pr316_link_created_at_nn NOT NULL,
receipt_id uuid CONSTRAINT pr316_link_receipt_id_nn NOT NULL
);
ALTER TABLE experiment_search_node_runs ADD CONSTRAINT pr316_link_pk PRIMARY KEY (id);
ALTER TABLE experiment_search_node_runs ADD CONSTRAINT pr316_link_id_ck CHECK (pr316_uuid7(id));
ALTER TABLE experiment_search_node_runs ADD CONSTRAINT pr316_link_time_ck CHECK
 (isfinite(created_at));
ALTER TABLE experiment_search_node_runs ADD CONSTRAINT pr316_link_receipt_uq UNIQUE
 (receipt_id);
ALTER TABLE experiment_search_node_runs ADD CONSTRAINT pr316_link_actor_fk FOREIGN KEY
 (created_by) REFERENCES actors(id) ON UPDATE NO ACTION ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE experiment_search_node_runs ADD CONSTRAINT pr316_link_receipt_fk FOREIGN KEY
 (research_task_id,receipt_id) REFERENCES research_task_command_receipts(research_task_id,id) ON
 UPDATE NO ACTION ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE experiment_search_node_runs ADD CONSTRAINT pr316_link_scope_uq UNIQUE
 (research_task_id,search_session_id,node_id,id);
ALTER TABLE experiment_search_node_runs ADD CONSTRAINT pr316_link_pair_uq UNIQUE
 (search_session_id,node_id,run_id);
ALTER TABLE experiment_search_node_runs ADD CONSTRAINT pr316_link_session_fk FOREIGN KEY
 (research_task_id,project_id,search_session_id) REFERENCES
 experiment_search_sessions(research_task_id,project_id,id) ON UPDATE NO ACTION ON DELETE
 RESTRICT NOT DEFERRABLE;
ALTER TABLE experiment_search_node_runs ADD CONSTRAINT pr316_link_node_fk FOREIGN KEY
 (research_task_id,search_session_id,node_id) REFERENCES
 experiment_search_nodes(research_task_id,search_session_id,id) ON UPDATE NO ACTION ON DELETE
 RESTRICT NOT DEFERRABLE;
ALTER TABLE experiment_search_node_runs ADD CONSTRAINT pr316_link_run_fk FOREIGN KEY
 (run_id,project_id) REFERENCES runs(id,project_id) ON UPDATE NO ACTION ON DELETE RESTRICT NOT
 DEFERRABLE;
"""

EVENTS = r"""
CREATE TABLE experiment_search_events (
id uuid CONSTRAINT pr316_event_id_nn NOT NULL,
research_task_id uuid CONSTRAINT pr316_event_research_task_id_nn NOT NULL,
search_session_id uuid CONSTRAINT pr316_event_search_session_id_nn NOT NULL,
node_id uuid NULL,
sequence integer CONSTRAINT pr316_event_sequence_nn NOT NULL,
event_type text CONSTRAINT pr316_event_event_type_nn NOT NULL,
reason text CONSTRAINT pr316_event_reason_nn NOT NULL,
actor_id uuid CONSTRAINT pr316_event_actor_id_nn NOT NULL,
occurred_at timestamptz CONSTRAINT pr316_event_occurred_at_nn NOT NULL,
receipt_id uuid CONSTRAINT pr316_event_receipt_id_nn NOT NULL
);
ALTER TABLE experiment_search_events ADD CONSTRAINT pr316_event_pk PRIMARY KEY (id);
ALTER TABLE experiment_search_events ADD CONSTRAINT pr316_event_id_ck CHECK (pr316_uuid7(id));
ALTER TABLE experiment_search_events ADD CONSTRAINT pr316_event_time_ck CHECK
 (isfinite(occurred_at));
ALTER TABLE experiment_search_events ADD CONSTRAINT pr316_event_receipt_uq UNIQUE (receipt_id);
ALTER TABLE experiment_search_events ADD CONSTRAINT pr316_event_actor_fk FOREIGN KEY (actor_id)
 REFERENCES actors(id) ON UPDATE NO ACTION ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE experiment_search_events ADD CONSTRAINT pr316_event_receipt_fk FOREIGN KEY
 (research_task_id,receipt_id) REFERENCES research_task_command_receipts(research_task_id,id) ON
 UPDATE NO ACTION ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE experiment_search_events ADD CONSTRAINT pr316_event_scope_uq UNIQUE
 (research_task_id,search_session_id,id);
ALTER TABLE experiment_search_events ADD CONSTRAINT pr316_event_sequence_uq UNIQUE
 (search_session_id,sequence);
ALTER TABLE experiment_search_events ADD CONSTRAINT pr316_event_sequence_ck CHECK (sequence>=1);
ALTER TABLE experiment_search_events ADD CONSTRAINT pr316_event_kind_ck CHECK (event_type IN (
 'SESSION_CREATED' , 'NODE_APPENDED' ));
ALTER TABLE experiment_search_events ADD CONSTRAINT pr316_event_reason_ck CHECK
 (pr316_reason(reason));
ALTER TABLE experiment_search_events ADD CONSTRAINT pr316_event_shape_ck CHECK ((event_type=
 'SESSION_CREATED' AND node_id IS NULL) OR (event_type= 'NODE_APPENDED' AND node_id IS NOT
 NULL));
ALTER TABLE experiment_search_events ADD CONSTRAINT pr316_event_session_fk FOREIGN KEY
 (research_task_id,search_session_id) REFERENCES experiment_search_sessions(research_task_id,id)
 ON UPDATE NO ACTION ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE experiment_search_events ADD CONSTRAINT pr316_event_node_fk FOREIGN KEY
 (research_task_id,search_session_id,node_id) REFERENCES
 experiment_search_nodes(research_task_id,search_session_id,id) ON UPDATE NO ACTION ON DELETE
 RESTRICT NOT DEFERRABLE;
"""

INDEXES = r"""
CREATE UNIQUE INDEX pr316_node_one_root ON experiment_search_nodes(search_session_id) WHERE
 parent_node_id IS NULL;
CREATE UNIQUE INDEX pr316_event_one_creation ON experiment_search_events(search_session_id)
 WHERE event_type= 'SESSION_CREATED' ;
CREATE UNIQUE INDEX pr316_event_one_node_creation ON experiment_search_events(node_id) WHERE
 event_type= 'NODE_APPENDED' ;
CREATE INDEX pr316_session_task_project ON
 experiment_search_sessions(research_task_id,project_id);
CREATE INDEX pr316_session_budget ON experiment_search_sessions(research_task_id,budget_id);
CREATE INDEX pr316_session_project ON experiment_search_sessions(project_id,id);
CREATE INDEX pr316_session_hypothesis ON experiment_search_sessions(root_hypothesis_version_id);
CREATE INDEX pr316_session_spec ON experiment_search_sessions(root_experiment_spec_version_id);
CREATE INDEX pr316_node_parent ON
 experiment_search_nodes(research_task_id,search_session_id,parent_node_id);
CREATE INDEX pr316_node_order ON experiment_search_nodes(search_session_id,depth,id);
CREATE INDEX pr316_node_hypothesis ON experiment_search_nodes(hypothesis_version_id);
CREATE INDEX pr316_node_spec ON experiment_search_nodes(experiment_spec_version_id);
CREATE INDEX pr316_node_reservation ON
 experiment_search_nodes(research_task_id,reservation_id,id);
CREATE INDEX pr316_link_session_project ON
 experiment_search_node_runs(research_task_id,project_id,search_session_id);
CREATE INDEX pr316_link_run ON experiment_search_node_runs(run_id,project_id);
CREATE INDEX pr316_link_order ON experiment_search_node_runs(node_id,id);
CREATE INDEX pr316_link_actor ON experiment_search_node_runs(created_by);
CREATE INDEX pr316_link_receipt ON experiment_search_node_runs(research_task_id,receipt_id);
CREATE INDEX pr316_event_node ON
 experiment_search_events(research_task_id,search_session_id,node_id);
CREATE INDEX pr316_session_actor ON experiment_search_sessions(created_by);
CREATE INDEX pr316_session_receipt ON experiment_search_sessions(research_task_id,receipt_id);
CREATE INDEX pr316_node_actor ON experiment_search_nodes(created_by);
CREATE INDEX pr316_node_receipt ON experiment_search_nodes(research_task_id,receipt_id);
CREATE INDEX pr316_event_actor ON experiment_search_events(actor_id);
CREATE INDEX pr316_event_receipt ON experiment_search_events(research_task_id,receipt_id);
"""

RECEIPTS = r"""
ALTER TABLE research_task_command_receipts DROP CONSTRAINT pr303_command_names;
ALTER TABLE research_task_events DROP CONSTRAINT pr303_event_names,
DROP CONSTRAINT pr303_event_states, DROP CONSTRAINT pr303_event_reason;
ALTER TABLE research_task_command_receipts ADD CONSTRAINT pr316_command_names CHECK
 (command_name IN (
'create_research_task' , 'create_task_plan' , 'add_task_step' , 'add_task_step_dependency' ,
 'seal_task_plan' , 'cancel_research_task' ,
'bind_task_policies' , 'reserve_task_budget' , 'settle_task_budget' ,
 'evaluate_task_termination' , 'request_human_checkpoint' , 'respond_human_checkpoint' ,
'register_agent_tool_policy' , 'request_capability_invocation' , 'start_capability_invocation' ,
 'finish_capability_invocation' , 'create_search_session' , 'append_search_node' ));
ALTER TABLE research_task_events
ADD CONSTRAINT pr316_task_event_names CHECK (event_type IN (
'CREATED' , 'PLAN_CREATED' , 'STEP_ADDED' , 'DEPENDENCY_ADDED' , 'PLAN_SEALED' , 'CANCELLED' ,
'POLICIES_BOUND' , 'BUDGET_RESERVED' , 'BUDGET_SETTLED' , 'TERMINATION_EVALUATED' ,
 'CHECKPOINT_REQUESTED' , 'CHECKPOINT_RESPONDED' ,
'TOOL_POLICY_REGISTERED' , 'CAPABILITY_REQUESTED' , 'CAPABILITY_STARTED' , 'CAPABILITY_FINISHED'
 , 'SEARCH_SESSION_CREATED' , 'SEARCH_NODE_APPENDED' )),
ADD CONSTRAINT pr316_task_event_states CHECK (
(event_type = 'CREATED' AND prior_status IS NULL AND new_status = 'CREATED' ) OR
(event_type = 'PLAN_CREATED' AND prior_status = 'CREATED' AND new_status = 'PLANNING' ) OR
(event_type IN ( 'STEP_ADDED' , 'DEPENDENCY_ADDED' , 'PLAN_SEALED' ) AND prior_status =
 'PLANNING' AND new_status = 'PLANNING' ) OR
(event_type = 'CANCELLED' AND prior_status IN ( 'CREATED' , 'PLANNING' ) AND new_status =
 'CANCELLED' ) OR
(event_type IN ( 'POLICIES_BOUND' , 'BUDGET_RESERVED' , 'BUDGET_SETTLED' ,
 'TERMINATION_EVALUATED' , 'CHECKPOINT_REQUESTED' , 'CHECKPOINT_RESPONDED' ,
'TOOL_POLICY_REGISTERED' , 'CAPABILITY_REQUESTED' , 'CAPABILITY_STARTED' , 'CAPABILITY_FINISHED'
 )
AND prior_status IN ( 'CREATED' , 'PLANNING' , 'CANCELLED' ) AND new_status = prior_status) OR
(event_type IN ( 'SEARCH_SESSION_CREATED' , 'SEARCH_NODE_APPENDED' )
AND prior_status IN ( 'CREATED' , 'PLANNING' ) AND new_status = prior_status)),
ADD CONSTRAINT pr316_task_event_reason CHECK (CASE WHEN event_type IN (
'CANCELLED' , 'POLICIES_BOUND' , 'BUDGET_RESERVED' , 'BUDGET_SETTLED' , 'TERMINATION_EVALUATED'
 , 'CHECKPOINT_REQUESTED' , 'CHECKPOINT_RESPONDED' ,
'TOOL_POLICY_REGISTERED' , 'CAPABILITY_REQUESTED' , 'CAPABILITY_STARTED' , 'CAPABILITY_FINISHED'
 , 'SEARCH_SESSION_CREATED' , 'SEARCH_NODE_APPENDED' )
THEN reason IS NOT NULL AND length(btrim(reason)) BETWEEN 1 AND 8192 AND reason IS NFC
 NORMALIZED ELSE reason IS NULL END);

ALTER TABLE research_task_command_receipts
ADD COLUMN result_search_session_id uuid NULL,
ADD COLUMN result_search_node_id uuid NULL,
ADD COLUMN result_search_event_id uuid NULL,
ADD CONSTRAINT pr316_receipt_session_fk FOREIGN KEY
 (research_task_id,project_id,result_search_session_id)
REFERENCES experiment_search_sessions(research_task_id,project_id,id) ON UPDATE NO ACTION ON
 DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
ADD CONSTRAINT pr316_receipt_node_fk FOREIGN KEY
 (research_task_id,result_search_session_id,result_search_node_id)
REFERENCES experiment_search_nodes(research_task_id,search_session_id,id) ON UPDATE NO ACTION ON
 DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
ADD CONSTRAINT pr316_receipt_event_fk FOREIGN KEY
 (research_task_id,result_search_session_id,result_search_event_id)
REFERENCES experiment_search_events(research_task_id,search_session_id,id) ON UPDATE NO ACTION
 ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
ADD CONSTRAINT pr316_receipt_shape_ck CHECK (
(pr316_command_event(command_name) IS NULL AND
 num_nonnulls(result_search_session_id,result_search_node_id,result_search_event_id)=0)
OR (pr316_command_event(command_name) IS NOT NULL
AND result_search_session_id IS NOT NULL AND result_search_event_id IS NOT NULL
AND resulting_row_version>=2
AND ((command_name= 'create_search_session' AND result_search_node_id IS NULL)
OR (command_name= 'append_search_node' AND result_search_node_id IS NOT NULL))));
CREATE INDEX pr316_receipt_session ON
 research_task_command_receipts(research_task_id,project_id,result_search_session_id);
CREATE INDEX pr316_receipt_node ON
 research_task_command_receipts(research_task_id,result_search_session_id,result_search_node_id);
CREATE INDEX pr316_receipt_event_scope ON
 research_task_command_receipts(research_task_id,result_search_session_id,result_search_event_id);
CREATE UNIQUE INDEX pr316_receipt_event_uq ON
 research_task_command_receipts(result_search_event_id) WHERE result_search_event_id IS NOT
 NULL;
"""

GUARDS = r"""
CREATE FUNCTION pr316_immutable() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
BEGIN
RAISE EXCEPTION 'immutable search history' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_immutable'
 ;
END $$;

CREATE FUNCTION pr316_preheld(r research_task_command_receipts) RETURNS void
LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE rel text; k text; h bigint; keys text[];
BEGIN
IF current_setting( 'transaction_isolation' )<> 'read committed' THEN
RAISE EXCEPTION 'search isolation' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_preheld' ;
END IF;
FOREACH rel IN ARRAY ARRAY[ 'actor_subject_bindings' , 'actors' , 'artifact_versions' ,
 'artifacts' ,
'claim_versions' , 'claims' , 'hypothesis_versions' , 'hypotheses' ,
 'literature_source_project_links' ,
'literature_sources' , 'manuscript_versions' , 'project_memberships' ,
 'project_role_assignments' ,
'projects' , 'publications' , 'research_question_versions' , 'research_questions' ,
 'source_versions' ] LOOP
IF NOT EXISTS(SELECT 1 FROM pg_locks WHERE pid=pg_backend_pid() AND locktype= 'relation'
AND granted AND relation=to_regclass( 'public.' ||rel)
AND mode IN ( 'ShareLock' , 'ShareRowExclusiveLock' , 'ExclusiveLock' , 'AccessExclusiveLock' ))
 THEN
RAISE EXCEPTION 'search SHARE absent' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_preheld' ;
END IF;
END LOOP;
keys:=ARRAY[ 'researchbase-project:' ||r.project_id,
'pr301:command:' ||r.project_id|| ':' ||r.actor_id|| ':' ||r.command_id,
'pr301:task:' ||r.research_task_id];
IF EXISTS(SELECT 1 FROM actors WHERE id=r.actor_id AND actor_type= 'AGENT' ) THEN
keys:=array_append(keys, 'pr302:actor:' ||r.actor_id);
END IF;
FOREACH k IN ARRAY keys LOOP
h:=hashtextextended(k,0);
IF NOT EXISTS(SELECT 1 FROM pg_locks WHERE pid=pg_backend_pid() AND locktype= 'advisory'
AND granted AND mode= 'ExclusiveLock' AND classid=((h>>32)&4294967295)::oid
AND objid=(h&4294967295)::oid AND objsubid=1) THEN
RAISE EXCEPTION 'search key absent' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_preheld' ;
END IF;
END LOOP;
END $$;

CREATE FUNCTION pr316_live(r research_task_command_receipts) RETURNS void
LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE at_time timestamptz:=clock_timestamp();
BEGIN
PERFORM pr316_preheld(r);
IF NOT EXISTS(SELECT 1 FROM projects p JOIN project_memberships m ON m.project_id=p.id
JOIN project_role_assignments ro ON ro.membership_id=m.id JOIN actors a ON a.id=m.actor_id
JOIN actor_subject_bindings b ON b.actor_id=a.id
WHERE p.id=r.project_id AND p.lifecycle_status= 'ACTIVE' AND a.id=r.actor_id
AND a.retired_at IS NULL AND m.status= 'ACTIVE' AND m.started_at<=at_time
AND ro.effective_from<=at_time AND (ro.effective_until IS NULL OR ro.effective_until>at_time)
AND b.status= 'ACTIVE' AND b.bound_at<=at_time AND (b.revoked_at IS NULL OR
 b.revoked_at>at_time)
AND ((a.actor_type= 'HUMAN' AND ro.role IN ( 'OWNER' , 'RESEARCHER' )) OR
(a.actor_type= 'AGENT' AND ro.role= 'RESEARCHER' AND b.subject_kind= 'MTLS_URI'
AND b.proof_kind= 'MTLS_CHALLENGE' AND EXISTS(SELECT 1 FROM agent_command_receipts enrolled
WHERE enrolled.operation= 'provision_project_agent' AND enrolled.result_actor_id=a.id
AND enrolled.project_id=p.id AND enrolled.result_binding_id=b.id)))) THEN
RAISE EXCEPTION 'search authority' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_scope' ;
END IF;
IF NOT EXISTS(SELECT 1 FROM research_tasks WHERE id=r.research_task_id AND
 project_id=r.project_id
AND row_version=r.resulting_row_version AND xmin=pg_current_xact_id()::xid) THEN
RAISE EXCEPTION 'fresh task required' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_completeness' ;
END IF;
IF EXISTS(SELECT 1 FROM research_tasks WHERE id=r.research_task_id AND status= 'CANCELLED' )
 THEN
RAISE EXCEPTION 'create/append require nonterminal task' USING ERRCODE= '23514' ,CONSTRAINT=
 'pr316_state' ;
END IF;
END $$;

CREATE FUNCTION pr316_receipt_insert() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
BEGIN
IF pr316_command_event(NEW.command_name) IS NOT NULL THEN
PERFORM pr316_live(NEW);
IF NOT pr316_uuid7(NEW.id) THEN
RAISE EXCEPTION 'receipt UUIDv7 required' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_validation'
 ;
END IF;
NEW.completed_at:=transaction_timestamp();
END IF;
RETURN NEW;
END $$;

CREATE FUNCTION pr316_refs(p_project uuid,h_id uuid,h_hash text,e_id uuid,e_hash text) RETURNS
 void
LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE v record;
BEGIN
IF (h_id IS NULL)<>(h_hash IS NULL) OR (e_id IS NULL)<>(e_hash IS NULL) THEN
RAISE EXCEPTION 'reference/hash pair' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_provenance' ;
END IF;
IF h_id IS NOT NULL THEN
SELECT h.project_id,vv.status,vv.frozen_at,vv.content_hash INTO v
FROM hypothesis_versions vv JOIN hypotheses h ON h.id=vv.hypothesis_id WHERE vv.id=h_id;
IF NOT FOUND THEN RAISE EXCEPTION 'exact hypothesis absent' USING ERRCODE= '23503' ,CONSTRAINT=
 'pr316_reference' ; END IF;
IF v.project_id<>p_project THEN RAISE EXCEPTION 'hypothesis scope' USING ERRCODE= '23514'
 ,CONSTRAINT= 'pr316_scope' ; END IF;
IF v.status NOT IN ( 'FROZEN' , 'SUPERSEDED' ) OR v.frozen_at IS NULL OR v.content_hash IS NULL
 THEN
RAISE EXCEPTION 'hypothesis not frozen' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_not_frozen' ;
 END IF;
IF v.content_hash IS DISTINCT FROM h_hash THEN
RAISE EXCEPTION 'hypothesis hash' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_provenance' ; END
 IF;
END IF;
IF e_id IS NOT NULL THEN
SELECT e.project_id,vv.status,vv.frozen_at,vv.content_hash INTO v
FROM experiment_spec_versions vv JOIN experiment_specs e ON e.id=vv.experiment_spec_id WHERE
 vv.id=e_id;
IF NOT FOUND THEN RAISE EXCEPTION 'exact spec absent' USING ERRCODE= '23503' ,CONSTRAINT=
 'pr316_reference' ; END IF;
IF v.project_id<>p_project THEN RAISE EXCEPTION 'spec scope' USING ERRCODE= '23514' ,CONSTRAINT=
 'pr316_scope' ; END IF;
IF v.status NOT IN ( 'FROZEN' , 'SUPERSEDED' ) OR v.frozen_at IS NULL OR v.content_hash IS NULL
 THEN
RAISE EXCEPTION 'spec not frozen' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_not_frozen' ; END
 IF;
IF v.content_hash IS DISTINCT FROM e_hash THEN
RAISE EXCEPTION 'spec hash' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_provenance' ; END IF;
END IF;
END $$;

CREATE FUNCTION pr316_chain(p_task uuid,p_session uuid,p_node uuid) RETURNS integer
LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE cur uuid:=p_node; seen uuid[]:=ARRAY[]::uuid[]; n experiment_search_nodes%ROWTYPE;
expected integer; first_depth integer;
BEGIN
IF cur IS NULL THEN RETURN -1; END IF;
LOOP
IF cur=ANY(seen) THEN RAISE EXCEPTION 'search cycle' USING ERRCODE= '23514' ,CONSTRAINT=
 'pr316_reference' ; END IF;
seen:=array_append(seen,cur);
SELECT * INTO n FROM experiment_search_nodes WHERE id=cur AND research_task_id=p_task AND
 search_session_id=p_session;
IF NOT FOUND THEN RAISE EXCEPTION 'ancestry absent' USING ERRCODE= '23503' ,CONSTRAINT=
 'pr316_reference' ; END IF;
IF first_depth IS NULL THEN first_depth:=n.depth; expected:=n.depth; END IF;
IF n.depth<>expected OR (n.parent_node_id IS NULL AND n.depth<>0) THEN
RAISE EXCEPTION 'ancestry depth' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_reference' ; END IF;
EXIT WHEN n.parent_node_id IS NULL;
expected:=expected-1; cur:=n.parent_node_id;
END LOOP;
RETURN first_depth;
END $$;

CREATE FUNCTION pr316_admission(p_task uuid,p_step uuid,p_code boolean,p_run boolean) RETURNS
 void
LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE t research_tasks%ROWTYPE; b execution_budgets%ROWTYPE; c checkpoint_policies%ROWTYPE;
term termination_policies%ROWTYPE; k text; total numeric; cap numeric; origin timestamptz;
at_time timestamptz:=clock_timestamp(); required text[]; gate text; gate_status text;
BEGIN
SELECT * INTO t FROM research_tasks WHERE id=p_task;
SELECT * INTO b FROM execution_budgets WHERE id=t.budget_policy_id AND research_task_id=p_task;
SELECT * INTO c FROM checkpoint_policies WHERE id=t.checkpoint_policy_id AND
 research_task_id=p_task;
SELECT * INTO term FROM termination_policies WHERE id=t.termination_policy_id AND
 research_task_id=p_task;
IF t.id IS NULL OR t.status NOT IN ( 'CREATED' , 'PLANNING' ) OR b.id IS NULL OR c.id IS NULL OR
 term.id IS NULL
OR t.autonomy_level>c.maximum_autonomy THEN
RAISE EXCEPTION 'search policy bundle' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_state' ; END
 IF;
PERFORM pr304_validate_safety(p_task);
IF EXISTS(SELECT 1 FROM research_task_events WHERE research_task_id=p_task
AND (stop_human OR stop_policy OR stop_budget OR stop_repeated_failure OR stop_no_improvement OR
 stop_success)) THEN
RAISE EXCEPTION 'sticky task stop' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_state' ; END IF;
FOREACH k IN ARRAY ARRAY[ 'agent_steps' , 'llm_calls' , 'search_calls' , 'code_iterations' ,
 'experiment_runs' , 'tree_nodes' , 'gpu_hours' , 'token_cost' ] LOOP
SELECT coalesce(sum(CASE WHEN u.id IS NULL THEN (to_jsonb(r)->>k)::numeric ELSE
 (to_jsonb(u)->>k)::numeric END),0)
INTO total FROM budget_reservations r LEFT JOIN budget_usage_records u ON u.reservation_id=r.id
 AND u.is_final
WHERE r.research_task_id=p_task;
cap:=(to_jsonb(b)->>( 'max_' ||k))::numeric;
IF total>cap OR (cap>0 AND total>=cap) THEN
RAISE EXCEPTION 'charged cap reached' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_state' ; END
 IF;
END LOOP;
SELECT min(created_at) INTO origin FROM budget_reservations WHERE research_task_id=p_task;
IF (origin IS NOT NULL AND at_time>=origin+b.max_wall_time_seconds*interval '1 second' )
OR EXISTS(SELECT 1 FROM budget_usage_records u WHERE u.research_task_id=p_task AND u.is_final
AND (u.failure_streak>=term.repeated_failure_threshold OR
 u.no_improvement_streak>=term.max_no_improvement_iterations)) THEN
RAISE EXCEPTION 'derived task stop' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_state' ; END IF;
required:=c.required_types||ARRAY[ 'plan_review' ];
IF p_code THEN required:=array_append(required, 'code_risk' ); END IF;
IF p_run THEN required:=array_append(required, 'experiment_approval' ); END IF;
FOREACH gate IN ARRAY required LOOP
SELECT status INTO gate_status FROM human_checkpoints WHERE research_task_id=p_task
AND step_id IS NOT DISTINCT FROM p_step AND checkpoint_type=gate ORDER BY created_at DESC,id
 DESC LIMIT 1;
IF gate_status IS DISTINCT FROM 'APPROVED' THEN
RAISE EXCEPTION 'checkpoint required' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_state' ; END
 IF;
END LOOP;
END $$;

CREATE FUNCTION pr316_node_proof(n experiment_search_nodes) RETURNS void
LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE s experiment_search_sessions%ROWTYPE; r budget_reservations%ROWTYPE;
step research_task_steps%ROWTYPE; cur uuid; seen uuid[]:=ARRAY[]::uuid[]; d integer:=0;
BEGIN
SELECT * INTO s FROM experiment_search_sessions WHERE id=n.search_session_id AND
 research_task_id=n.research_task_id;
SELECT * INTO r FROM budget_reservations WHERE id=n.reservation_id AND
 research_task_id=n.research_task_id
AND xmin<>pg_current_xact_id()::xid;
IF r.id IS NULL OR r.budget_id IS DISTINCT FROM s.budget_id OR r.operation_id IS DISTINCT FROM
 n.id
OR r.tree_nodes<>1 OR r.observed_depth<>n.depth OR r.deadline<=clock_timestamp()
OR EXISTS(SELECT 1 FROM budget_usage_records WHERE reservation_id=r.id AND is_final)
OR EXISTS(SELECT 1 FROM experiment_search_nodes WHERE reservation_id=r.id AND id<>n.id)
OR NOT EXISTS(SELECT 1 FROM research_tasks WHERE id=n.research_task_id AND
 budget_policy_id=r.budget_id) THEN
RAISE EXCEPTION 'conservative reservation proof' USING ERRCODE= '23514' ,CONSTRAINT=
 'pr316_state' ; END IF;
cur:=r.step_id;
WHILE cur IS NOT NULL LOOP
IF cur=ANY(seen) THEN RAISE EXCEPTION 'step cycle' USING ERRCODE= '23514' ,CONSTRAINT=
 'pr316_reference' ; END IF;
seen:=array_append(seen,cur);
SELECT * INTO step FROM research_task_steps WHERE id=cur AND
 research_task_id=n.research_task_id;
IF NOT FOUND THEN RAISE EXCEPTION 'step absent' USING ERRCODE= '23503' ,CONSTRAINT=
 'pr316_reference' ; END IF;
cur:=step.parent_step_id;
IF cur IS NOT NULL THEN d:=d+1; END IF;
END LOOP;
IF d<>n.depth OR (r.step_id IS NULL AND n.depth<>0) THEN
RAISE EXCEPTION 'step/search depth mismatch' USING ERRCODE= '23514' ,CONSTRAINT=
 'pr316_validation' ; END IF;
IF NOT EXISTS(SELECT 1 FROM research_tasks t JOIN execution_budgets b ON b.id=t.budget_policy_id
JOIN termination_policies p ON p.id=t.termination_policy_id WHERE t.id=n.research_task_id
AND n.depth<=b.max_tree_depth AND p.score_metric_version_id IS NOT NULL) THEN
RAISE EXCEPTION 'depth/evaluator prerequisite' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_state'
 ; END IF;
PERFORM pr316_admission(n.research_task_id,r.step_id,r.code_iterations>0,r.experiment_runs>0);
 -- Binding owner decision: no production producer or approved atomic amendment exists.
 -- This is intentionally unconditional; no caller flag, GUC or test-role bypass.
RAISE EXCEPTION 'D1 activation prerequisite unavailable' USING ERRCODE= '23514' ,CONSTRAINT=
 'pr316_activation' ;
END $$;

CREATE FUNCTION pr316_state(r research_task_command_receipts,e experiment_search_events) RETURNS
 void
LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE s experiment_search_sessions%ROWTYPE; n experiment_search_nodes%ROWTYPE;
expected_kind text;
BEGIN
SELECT * INTO s FROM experiment_search_sessions WHERE id=r.result_search_session_id;
IF s.id IS NULL OR ROW(s.research_task_id,s.project_id) IS DISTINCT FROM
 ROW(r.research_task_id,r.project_id) THEN
RAISE EXCEPTION 'session scope' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_reference' ; END IF;
IF ROW(e.research_task_id,e.search_session_id,e.node_id,e.actor_id,e.receipt_id,e.occurred_at)
IS DISTINCT FROM
 ROW(r.research_task_id,s.id,r.result_search_node_id,r.actor_id,r.id,r.completed_at) THEN
RAISE EXCEPTION 'search event pointers' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_completeness'
 ; END IF;
PERFORM pr316_refs(r.project_id,s.root_hypothesis_version_id,s.root_hypothesis_content_hash,
s.root_experiment_spec_version_id,s.root_experiment_spec_content_hash);
IF r.result_search_node_id IS NOT NULL THEN
SELECT * INTO n FROM experiment_search_nodes WHERE id=r.result_search_node_id;
IF n.id IS NULL OR ROW(n.research_task_id,n.search_session_id) IS DISTINCT FROM
 ROW(r.research_task_id,s.id) THEN
RAISE EXCEPTION 'node scope' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_reference' ; END IF;
PERFORM
 pr316_refs(r.project_id,n.hypothesis_version_id,n.hypothesis_content_hash,n.experiment_spec_version_id,n.experiment_spec_content_hash);
END IF;
CASE r.command_name
WHEN 'create_search_session' THEN
expected_kind:= 'SESSION_CREATED' ;
IF e.reason<> 'Search session created.' OR s.receipt_id<>r.id
OR NOT EXISTS(SELECT 1 FROM research_tasks WHERE id=r.research_task_id AND
 budget_policy_id=s.budget_id) THEN
RAISE EXCEPTION 'session creation shape' USING ERRCODE= '23514' ,CONSTRAINT=
 'pr316_completeness' ; END IF;
PERFORM pr316_admission(r.research_task_id,NULL,false,false);
WHEN 'append_search_node' THEN
expected_kind:= 'NODE_APPENDED' ;
IF n.receipt_id<>r.id OR e.reason<>n.mutation_reason
OR n.depth<>pr316_chain(r.research_task_id,s.id,n.parent_node_id)+1 THEN
RAISE EXCEPTION 'append shape' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_validation' ; END IF;
PERFORM pr316_node_proof(n);
ELSE RAISE EXCEPTION 'unknown search command' USING ERRCODE= '23514' ,CONSTRAINT=
 'pr316_validation' ;
END CASE;
IF e.event_type<>expected_kind THEN
RAISE EXCEPTION 'search event kind' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_completeness' ;
 END IF;
END $$;

CREATE FUNCTION pr316_link_write_disabled() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
BEGIN
RAISE EXCEPTION 'No Run-link writer in this slice'
USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_no_link_writer' ;
END $$;

CREATE FUNCTION pr316_lineage_insert() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE r research_task_command_receipts%ROWTYPE; s experiment_search_sessions%ROWTYPE;
next_sequence integer;
BEGIN
SELECT * INTO r FROM research_task_command_receipts WHERE id=NEW.receipt_id
AND research_task_id=NEW.research_task_id AND xmin=pg_current_xact_id()::xid;
IF r.id IS NULL OR pr316_command_event(r.command_name) IS NULL OR
 r.completed_at<>transaction_timestamp() THEN
RAISE EXCEPTION 'fresh search receipt required' USING ERRCODE= '23514' ,CONSTRAINT=
 'pr316_completeness' ; END IF;
PERFORM pr316_live(r);
IF TG_TABLE_NAME= 'experiment_search_events' THEN
IF NEW.id IS DISTINCT FROM r.result_search_event_id THEN
RAISE EXCEPTION 'event result mismatch' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_completeness'
 ; END IF;
SELECT coalesce(max(sequence),0)+1 INTO next_sequence FROM experiment_search_events WHERE
 search_session_id=NEW.search_session_id;
IF NEW.sequence<>next_sequence THEN RAISE EXCEPTION 'event sequence' USING ERRCODE= '23514'
 ,CONSTRAINT= 'pr316_validation' ; END IF;
PERFORM pr316_state(r,NEW);
ELSE
IF NEW.created_at<>r.completed_at OR NEW.created_by<>r.actor_id THEN
RAISE EXCEPTION 'creator/time mismatch' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_completeness'
 ; END IF;
IF TG_TABLE_NAME= 'experiment_search_sessions' THEN
IF r.command_name<> 'create_search_session' OR NEW.id IS DISTINCT FROM
 r.result_search_session_id OR NEW.project_id<>r.project_id THEN
RAISE EXCEPTION 'session result mismatch' USING ERRCODE= '23514' ,CONSTRAINT=
 'pr316_completeness' ; END IF;
IF NOT EXISTS(SELECT 1 FROM research_tasks WHERE id=r.research_task_id AND
 budget_policy_id=NEW.budget_id) THEN
RAISE EXCEPTION 'active budget binding' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_state' ; END
 IF;
PERFORM pr316_refs(r.project_id,NEW.root_hypothesis_version_id,NEW.root_hypothesis_content_hash,
NEW.root_experiment_spec_version_id,NEW.root_experiment_spec_content_hash);
PERFORM pr316_admission(r.research_task_id,NULL,false,false);
ELSE
SELECT * INTO s FROM experiment_search_sessions WHERE id=NEW.search_session_id
AND research_task_id=r.research_task_id AND xmin<>pg_current_xact_id()::xid;
IF s.id IS NULL OR s.id IS DISTINCT FROM r.result_search_session_id OR
 s.project_id<>r.project_id THEN
RAISE EXCEPTION 'session unavailable' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_state' ; END
 IF;
IF TG_TABLE_NAME= 'experiment_search_nodes' THEN
IF r.command_name<> 'append_search_node' OR NEW.id IS DISTINCT FROM r.result_search_node_id
OR (NEW.parent_node_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM experiment_search_nodes
WHERE id=NEW.parent_node_id AND research_task_id=r.research_task_id AND search_session_id=s.id
AND xmin<>pg_current_xact_id()::xid)) THEN
RAISE EXCEPTION 'existing parent/node result' USING ERRCODE= '23514' ,CONSTRAINT=
 'pr316_reference' ; END IF;
IF NEW.depth<>pr316_chain(r.research_task_id,s.id,NEW.parent_node_id)+1 THEN
RAISE EXCEPTION 'child depth' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_validation' ; END IF;
PERFORM pr316_refs(r.project_id,NEW.hypothesis_version_id,NEW.hypothesis_content_hash,
NEW.experiment_spec_version_id,NEW.experiment_spec_content_hash);
PERFORM pr316_node_proof(NEW);
END IF;
END IF;
END IF;
RETURN NEW;
END $$;

CREATE FUNCTION pr316_validate_receipt(p_receipt uuid) RETURNS void
LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE r research_task_command_receipts%ROWTYPE; e experiment_search_events%ROWTYPE;
s experiment_search_sessions%ROWTYPE; n experiment_search_nodes%ROWTYPE;
te research_task_events%ROWTYPE;
args jsonb; material jsonb; wanted_s integer:=0; wanted_n integer:=0;
search_command boolean;
BEGIN
SELECT * INTO r FROM research_task_command_receipts WHERE id=p_receipt;
IF NOT FOUND THEN RAISE EXCEPTION 'receipt absent' USING ERRCODE= '23503' ,CONSTRAINT=
 'pr316_reference' ; END IF;
search_command:=pr316_command_event(r.command_name) IS NOT NULL;
-- Legacy commands must retain their pre-upgrade table privileges. The search
-- INSERT guards reject non-search receipts before any lineage effect can exist.
IF NOT search_command THEN RETURN; END IF;
IF search_command THEN
wanted_s:=(r.command_name= 'create_search_session' )::integer;
wanted_n:=(r.command_name= 'append_search_node' )::integer;
END IF;
IF (SELECT count(*) FROM experiment_search_sessions WHERE receipt_id=r.id)<>wanted_s
OR (SELECT count(*) FROM experiment_search_nodes WHERE receipt_id=r.id)<>wanted_n
OR (SELECT count(*) FROM experiment_search_events WHERE
 receipt_id=r.id)<>search_command::integer THEN
RAISE EXCEPTION 'exact search effects' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_completeness'
 ; END IF;
IF NOT EXISTS(SELECT 1 FROM research_task_command_receipts WHERE id=r.id AND
 xmin=pg_current_xact_id()::xid)
OR r.completed_at<>transaction_timestamp() THEN
RAISE EXCEPTION 'receipt not fresh' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_completeness' ;
 END IF;
PERFORM pr316_live(r);
SELECT * INTO s FROM experiment_search_sessions WHERE id=r.result_search_session_id;
SELECT * INTO n FROM experiment_search_nodes WHERE id=r.result_search_node_id;
SELECT * INTO e FROM experiment_search_events WHERE id=r.result_search_event_id AND
 receipt_id=r.id;
IF e.id IS NULL OR NOT EXISTS(SELECT 1 FROM experiment_search_events WHERE id=e.id AND
 xmin=pg_current_xact_id()::xid)
OR (wanted_s=1 AND NOT EXISTS(SELECT 1 FROM experiment_search_sessions WHERE id=s.id AND
 receipt_id=r.id AND xmin=pg_current_xact_id()::xid))
OR (wanted_n=1 AND NOT EXISTS(SELECT 1 FROM experiment_search_nodes WHERE id=n.id AND
 receipt_id=r.id AND xmin=pg_current_xact_id()::xid)) THEN
RAISE EXCEPTION 'fresh result set' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_completeness' ;
 END IF;
IF (SELECT count(*) FROM experiment_search_events WHERE search_session_id=s.id)<>e.sequence
OR EXISTS(SELECT 1 FROM generate_series(1,e.sequence) seq WHERE NOT EXISTS(
SELECT 1 FROM experiment_search_events WHERE search_session_id=s.id AND sequence=seq)) THEN
RAISE EXCEPTION 'contiguous search history' USING ERRCODE= '23514' ,CONSTRAINT=
 'pr316_completeness' ; END IF;
PERFORM pr316_state(r,e);
SELECT ev.* INTO te FROM research_task_receipt_events re JOIN research_task_events ev ON
 ev.id=re.event_id WHERE re.receipt_id=r.id;
IF te.id IS NULL OR NOT pr316_uuid7(te.id) OR (SELECT count(*) FROM research_task_receipt_events
 WHERE receipt_id=r.id)<>1
OR EXISTS(SELECT 1 FROM research_task_receipt_step_events WHERE receipt_id=r.id)
OR te.event_type IS DISTINCT FROM pr316_command_event(r.command_name)
OR te.prior_status IS DISTINCT FROM te.new_status OR te.reason IS DISTINCT FROM e.reason
OR te.occurred_at IS DISTINCT FROM r.completed_at
OR te.stop_human OR te.stop_policy OR te.stop_budget OR te.stop_repeated_failure OR
 te.stop_no_improvement OR te.stop_success
OR EXISTS(SELECT 1 FROM research_task_steps WHERE research_task_id=r.research_task_id AND
 xmin=pg_current_xact_id()::xid)
OR EXISTS(SELECT 1 FROM research_task_inputs WHERE research_task_id=r.research_task_id AND
 xmin=pg_current_xact_id()::xid)
OR EXISTS(SELECT 1 FROM research_task_step_inputs WHERE research_task_id=r.research_task_id AND
 xmin=pg_current_xact_id()::xid)
OR EXISTS(SELECT 1 FROM research_task_step_dependencies WHERE
 research_task_id=r.research_task_id AND xmin=pg_current_xact_id()::xid)
OR EXISTS(SELECT 1 FROM research_tasks t WHERE t.id=r.research_task_id AND t.plan_sealed_at IS
 NOT NULL
AND NOT EXISTS(SELECT 1 FROM research_task_events x WHERE x.research_task_id=t.id AND
 x.event_type= 'PLAN_SEALED'
AND x.occurred_at=t.plan_sealed_at AND x.task_row_version<r.resulting_row_version)) THEN
RAISE EXCEPTION 'extra task/search effects' USING ERRCODE= '23514' ,CONSTRAINT=
 'pr316_completeness' ; END IF;
CASE r.command_name
WHEN 'create_search_session' THEN
args:=jsonb_build_object( 'session_id' ,s.id::text, 'root_hypothesis_version_id'
 ,s.root_hypothesis_version_id::text,
'root_experiment_spec_version_id' ,s.root_experiment_spec_version_id::text);
WHEN 'append_search_node' THEN
args:=jsonb_build_object( 'session_id' ,s.id::text, 'node_id' ,n.id::text, 'parent_node_id'
 ,n.parent_node_id::text,
'branch_kind' ,n.branch_kind, 'mutation_reason' ,n.mutation_reason, 'hypothesis_version_id'
 ,n.hypothesis_version_id::text,
'experiment_spec_version_id' ,n.experiment_spec_version_id::text, 'reservation_id'
 ,n.reservation_id::text);
END CASE;
material:=jsonb_build_object( 'type' , 'ExperimentSearchCommand' , 'material_version' ,1,
 'command_name' ,r.command_name,
'project_id' ,r.project_id::text, 'actor_id' ,r.actor_id::text, 'command_id'
 ,r.command_id::text,
'task_id' ,r.research_task_id::text, 'expected_row_version' ,r.resulting_row_version-1,
 'arguments' ,args);
IF r.request_hash IS DISTINCT FROM pr302s2_value_digest(material) THEN
RAISE EXCEPTION 'search request digest' USING ERRCODE= '23514' ,CONSTRAINT= 'pr316_provenance' ;
 END IF;
END $$;

CREATE FUNCTION pr316_effect_complete() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
BEGIN
PERFORM pr316_validate_receipt(NEW.receipt_id);
RETURN NULL;
END $$;
"""

RECEIPT_COMPLETE = r"""
CREATE OR REPLACE FUNCTION pr301_receipt_complete() RETURNS trigger LANGUAGE plpgsql SECURITY
 INVOKER
SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE r research_task_command_receipts%ROWTYPE; e research_task_events%ROWTYPE; mapped text;
expected integer; actual integer; gateway boolean; ci capability_invocations%ROWTYPE; ce
 capability_invocation_events%ROWTYPE;
BEGIN
SELECT * INTO r FROM research_task_command_receipts WHERE id=NEW.id;
SELECT te.* INTO e FROM research_task_receipt_events l JOIN research_task_events te ON
 te.id=l.event_id
WHERE l.receipt_id=r.id;
mapped:=CASE r.command_name WHEN 'create_research_task' THEN 'CREATED'
WHEN 'create_task_plan' THEN 'PLAN_CREATED' WHEN 'add_task_step' THEN 'STEP_ADDED'
WHEN 'add_task_step_dependency' THEN 'DEPENDENCY_ADDED' WHEN 'seal_task_plan' THEN 'PLAN_SEALED'
WHEN 'cancel_research_task' THEN 'CANCELLED' WHEN 'bind_task_policies' THEN 'POLICIES_BOUND'
 WHEN 'reserve_task_budget' THEN 'BUDGET_RESERVED' WHEN 'settle_task_budget' THEN
 'BUDGET_SETTLED' WHEN 'evaluate_task_termination' THEN 'TERMINATION_EVALUATED' WHEN
 'request_human_checkpoint' THEN 'CHECKPOINT_REQUESTED' WHEN 'respond_human_checkpoint' THEN
 'CHECKPOINT_RESPONDED'
WHEN 'register_agent_tool_policy' THEN 'TOOL_POLICY_REGISTERED'
WHEN 'request_capability_invocation' THEN 'CAPABILITY_REQUESTED'
WHEN 'start_capability_invocation' THEN 'CAPABILITY_STARTED'
WHEN 'finish_capability_invocation' THEN 'CAPABILITY_FINISHED'
WHEN 'create_search_session' THEN 'SEARCH_SESSION_CREATED'
WHEN 'append_search_node' THEN 'SEARCH_NODE_APPENDED' END;
IF e.id IS NULL OR e.event_type IS DISTINCT FROM mapped OR
ROW(e.research_task_id,e.actor_id,e.command_id,e.task_row_version) IS DISTINCT FROM
ROW(r.research_task_id,r.actor_id,r.command_id,r.resulting_row_version) THEN RAISE EXCEPTION
 'planning guard rejected write' USING ERRCODE= '23514' , CONSTRAINT= 'pr301_validation' ; END
 IF;
IF mapped= 'CREATED' AND e.occurred_at IS DISTINCT FROM
(SELECT created_at FROM research_tasks WHERE id=r.research_task_id) THEN
RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE= '23514' ,
CONSTRAINT= 'pr301_validation' ;
END IF;
IF mapped= 'PLAN_SEALED' AND e.occurred_at IS DISTINCT FROM
(SELECT plan_sealed_at FROM research_tasks WHERE id=r.research_task_id) THEN
RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE= '23514' ,
CONSTRAINT= 'pr301_validation' ;
END IF;
IF mapped= 'DEPENDENCY_ADDED' AND (SELECT count(*) FROM research_task_step_dependencies
WHERE research_task_id=r.research_task_id AND xmin=pg_current_xact_id()::xid)<>1 THEN
RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE= '23514' ,
CONSTRAINT= 'pr301_validation' ;
END IF;
IF e.sequence>1 AND e.prior_status IS DISTINCT FROM (SELECT new_status FROM research_task_events
WHERE research_task_id=r.research_task_id AND sequence=e.sequence-1) THEN RAISE EXCEPTION
 'planning guard rejected write' USING ERRCODE= '23514' , CONSTRAINT= 'pr301_validation' ; END
 IF;
IF EXISTS(SELECT 1 FROM research_task_step_events se LEFT JOIN research_task_receipt_step_events
 l
ON l.step_event_id=se.id WHERE se.research_task_id=r.research_task_id AND
 se.command_id=r.command_id
AND se.actor_id=r.actor_id AND (l.receipt_id IS DISTINCT FROM r.id OR
se.task_row_version<>r.resulting_row_version OR se.occurred_at IS DISTINCT FROM e.occurred_at
OR se.reason IS DISTINCT FROM e.reason OR
se.event_type IS DISTINCT FROM (CASE WHEN mapped= 'CANCELLED' THEN 'CANCELLED' ELSE 'PLANNED'
 END)))
THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE= '23514' , CONSTRAINT=
 'pr301_validation' ; END IF;
SELECT count(*) INTO actual FROM research_task_receipt_step_events WHERE receipt_id=r.id;
expected:=CASE WHEN mapped= 'PLAN_CREATED' THEN (SELECT count(*) FROM research_task_steps WHERE
 research_task_id=r.research_task_id)
WHEN mapped= 'STEP_ADDED' THEN 1 WHEN mapped= 'CANCELLED' THEN (SELECT count(*) FROM
 research_task_steps WHERE research_task_id=r.research_task_id)
ELSE 0 END;
IF actual<>expected THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE= '23514'
 , CONSTRAINT= 'pr301_validation' ; END IF;
IF mapped= 'CANCELLED' AND e.occurred_at IS DISTINCT FROM (SELECT finished_at FROM
 research_tasks WHERE id=r.research_task_id)
THEN RAISE EXCEPTION 'planning guard rejected write' USING ERRCODE= '23514' , CONSTRAINT=
 'pr301_validation' ; END IF;

IF (SELECT count(*) FROM execution_budgets WHERE receipt_id=r.id)<>(CASE r.command_name WHEN
 'bind_task_policies' THEN 1 WHEN 'request_human_checkpoint' THEN (SELECT count(*) FROM
 human_checkpoints WHERE receipt_id=r.id AND checkpoint_type= 'budget_extension' ) ELSE 0 END)
 THEN RAISE EXCEPTION 'wrong safety result count' USING ERRCODE= '23514' ,CONSTRAINT=
 'pr301_validation' ; END IF;

IF (SELECT count(*) FROM termination_policies WHERE receipt_id=r.id)<>(CASE WHEN r.command_name=
 'bind_task_policies' THEN 1 ELSE 0 END) THEN RAISE EXCEPTION 'wrong safety result count' USING
 ERRCODE= '23514' ,CONSTRAINT= 'pr301_validation' ; END IF;

IF (SELECT count(*) FROM checkpoint_policies WHERE receipt_id=r.id)<>(CASE WHEN r.command_name=
 'bind_task_policies' THEN 1 ELSE 0 END) THEN RAISE EXCEPTION 'wrong safety result count' USING
 ERRCODE= '23514' ,CONSTRAINT= 'pr301_validation' ; END IF;

IF r.command_name<> 'bind_task_policies' AND EXISTS(SELECT 1 FROM
 checkpoint_policy_dataset_scopes WHERE receipt_id=r.id) THEN RAISE EXCEPTION
 'extra scope effect' USING ERRCODE= '23514' ,CONSTRAINT= 'pr301_validation' ; END IF;

IF r.command_name<> 'bind_task_policies' AND EXISTS(SELECT 1 FROM
 checkpoint_policy_metric_scopes WHERE receipt_id=r.id) THEN RAISE EXCEPTION
 'extra scope effect' USING ERRCODE= '23514' ,CONSTRAINT= 'pr301_validation' ; END IF;

IF (SELECT count(*) FROM budget_reservations WHERE receipt_id=r.id)<>(CASE WHEN r.command_name
 IN ( 'reserve_task_budget' , 'request_capability_invocation' ) THEN 1 ELSE 0 END) THEN RAISE
 EXCEPTION 'wrong safety result count' USING ERRCODE= '23514' ,CONSTRAINT= 'pr301_validation' ;
 END IF;

IF (SELECT count(*) FROM budget_usage_records WHERE receipt_id=r.id)<>(CASE WHEN r.command_name
 IN ( 'settle_task_budget' , 'finish_capability_invocation' ) THEN 1 ELSE 0 END) THEN RAISE
 EXCEPTION 'wrong safety result count' USING ERRCODE= '23514' ,CONSTRAINT= 'pr301_validation' ;
 END IF;

IF (SELECT count(*) FROM human_checkpoints WHERE receipt_id=r.id)<>(CASE WHEN r.command_name=
 'request_human_checkpoint' THEN 1 ELSE 0 END) THEN RAISE EXCEPTION 'wrong safety result count'
 USING ERRCODE= '23514' ,CONSTRAINT= 'pr301_validation' ; END IF;


IF mapped= 'PLAN_SEALED' AND EXISTS(SELECT 1 FROM research_task_events WHERE
 research_task_id=r.research_task_id AND event_type= 'PLAN_SEALED' AND
 task_row_version<r.resulting_row_version)
THEN RAISE EXCEPTION 'plan already sealed' USING ERRCODE= '23514' ,CONSTRAINT= 'pr301_immutable'
 ; END IF;
IF mapped= 'CREATED' AND EXISTS(SELECT 1 FROM research_tasks WHERE id=r.research_task_id AND
 budget_policy_id IS NOT NULL)
THEN RAISE EXCEPTION 'creation must be unbound' USING ERRCODE= '23514' ,CONSTRAINT=
 'pr301_state' ; END IF;
IF r.command_name IN ( 'bind_task_policies' , 'respond_human_checkpoint' ) OR e.stop_human THEN
IF NOT EXISTS(SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id JOIN
 project_role_assignments p ON p.membership_id=m.id
JOIN actor_subject_bindings b ON b.actor_id=a.id WHERE a.id=r.actor_id AND a.actor_type= 'HUMAN'
 AND a.retired_at IS NULL
AND m.project_id=r.project_id AND m.status= 'ACTIVE' AND p.role= 'OWNER' AND
 p.effective_from<=r.completed_at AND (p.effective_until IS NULL OR
 r.completed_at<p.effective_until)
AND b.status= 'ACTIVE' AND b.bound_at<=r.completed_at AND (b.revoked_at IS NULL OR
 r.completed_at<b.revoked_at))
THEN RAISE EXCEPTION 'Human owner required' USING ERRCODE= '23514' ,CONSTRAINT= 'pr301_scope' ;
 END IF;
END IF;
IF (e.stop_human OR e.stop_policy) AND r.command_name<> 'evaluate_task_termination'
THEN RAISE EXCEPTION 'invalid explicit stop' USING ERRCODE= '23514' ,CONSTRAINT=
 'pr301_validation' ; END IF;
IF EXISTS(SELECT 1 FROM human_checkpoints h WHERE h.receipt_id=r.id AND h.reason IS DISTINCT
 FROM e.reason)
OR EXISTS(SELECT 1 FROM human_checkpoints h WHERE h.response_receipt_id=r.id AND h.status<>
 'EXPIRED' AND h.response_reason IS DISTINCT FROM e.reason)
THEN RAISE EXCEPTION 'checkpoint reason mismatch' USING ERRCODE= '23514' ,CONSTRAINT=
 'pr301_validation' ; END IF;
IF r.command_name= 'bind_task_policies' AND NOT EXISTS(SELECT 1 FROM research_tasks t JOIN
 execution_budgets b ON b.id=t.budget_policy_id AND b.receipt_id=r.id JOIN termination_policies
 p ON p.id=t.termination_policy_id AND p.receipt_id=r.id JOIN checkpoint_policies c ON
 c.id=t.checkpoint_policy_id AND c.receipt_id=r.id WHERE t.id=r.research_task_id)
THEN RAISE EXCEPTION 'wrong policy binding' USING ERRCODE= '23514' ,CONSTRAINT=
 'pr301_validation' ; END IF;
IF r.command_name= 'respond_human_checkpoint' THEN
IF (SELECT count(*) FROM human_checkpoints WHERE response_receipt_id=r.id AND status IN (
 'APPROVED' , 'REJECTED' , 'MODIFIED' ))<>1
THEN RAISE EXCEPTION 'wrong response effect' USING ERRCODE= '23514' ,CONSTRAINT=
 'pr301_validation' ; END IF;
ELSIF r.command_name= 'evaluate_task_termination' THEN
IF EXISTS(SELECT 1 FROM human_checkpoints WHERE research_task_id=r.research_task_id AND
((response_receipt_id=r.id AND status<> 'EXPIRED' ) OR (status= 'PENDING' AND
 expires_at<=r.completed_at)))
THEN RAISE EXCEPTION 'wrong expiry effects' USING ERRCODE= '23514' ,CONSTRAINT=
 'pr301_validation' ; END IF;
ELSIF EXISTS(SELECT 1 FROM human_checkpoints WHERE response_receipt_id=r.id)
THEN RAISE EXCEPTION 'extra response effect' USING ERRCODE= '23514' ,CONSTRAINT=
 'pr301_validation' ; END IF;
IF r.command_name IN ( 'bind_task_policies' , 'reserve_task_budget' , 'settle_task_budget' ,
 'evaluate_task_termination' , 'request_human_checkpoint' , 'respond_human_checkpoint' ,
 'register_agent_tool_policy' , 'request_capability_invocation' , 'start_capability_invocation'
 , 'finish_capability_invocation' ) THEN
IF r.completed_at<transaction_timestamp() OR r.completed_at>clock_timestamp() OR e.occurred_at
 IS DISTINCT FROM r.completed_at
OR EXISTS(SELECT 1 FROM research_task_steps WHERE research_task_id=r.research_task_id AND
 xmin=pg_current_xact_id()::xid)
OR EXISTS(SELECT 1 FROM research_task_inputs WHERE research_task_id=r.research_task_id AND
 xmin=pg_current_xact_id()::xid)
OR EXISTS(SELECT 1 FROM research_task_step_dependencies WHERE
 research_task_id=r.research_task_id AND xmin=pg_current_xact_id()::xid)
OR EXISTS(SELECT 1 FROM research_task_step_inputs WHERE research_task_id=r.research_task_id AND
 xmin=pg_current_xact_id()::xid)
THEN RAISE EXCEPTION 'unrelated safety effect' USING ERRCODE= '23514' ,CONSTRAINT=
 'pr301_validation' ; END IF;
IF e.prior_status= 'CANCELLED' AND r.command_name NOT IN ( 'settle_task_budget' ,
 'evaluate_task_termination' , 'finish_capability_invocation' )
THEN RAISE EXCEPTION 'terminal safety effect' USING ERRCODE= '23514' ,CONSTRAINT= 'pr301_state'
 ; END IF;
END IF;

gateway:=r.command_name IN ( 'register_agent_tool_policy' , 'request_capability_invocation' ,
 'start_capability_invocation' , 'finish_capability_invocation' );
IF ROW(e.result_tool_policy_id,e.result_capability_invocation_id,e.result_capability_event_id)
IS DISTINCT FROM
 ROW(r.result_tool_policy_id,r.result_capability_invocation_id,r.result_capability_event_id)
 THEN
RAISE EXCEPTION 'task event result pointers' USING ERRCODE= '23514' , CONSTRAINT=
 'pr301_validation' ;
END IF;
IF (SELECT count(*) FROM agent_tool_policies WHERE receipt_id=r.id)<>
(CASE WHEN r.command_name= 'register_agent_tool_policy' THEN 1 ELSE 0 END)
OR (SELECT count(*) FROM capability_invocations WHERE request_receipt_id=r.id)<>
(CASE WHEN r.command_name= 'request_capability_invocation' THEN 1 ELSE 0 END)
OR (SELECT count(*) FROM capability_invocation_events WHERE receipt_id=r.id)<>
(CASE WHEN r.command_name IN ( 'request_capability_invocation' , 'start_capability_invocation' ,
 'finish_capability_invocation' ) THEN 1 ELSE 0 END) THEN
RAISE EXCEPTION 'gateway result cardinality' USING ERRCODE= '23514' , CONSTRAINT=
 'pr301_validation' ;
END IF;
IF NOT gateway THEN
IF
 num_nonnulls(r.result_tool_policy_id,r.result_capability_invocation_id,r.result_capability_event_id,r.resulting_invocation_revision)<>0
OR EXISTS(SELECT 1 FROM capability_invocation_refs WHERE receipt_id=r.id) THEN
RAISE EXCEPTION 'extra gateway effect on old command' USING ERRCODE= '23514' , CONSTRAINT=
 'pr301_validation' ;
END IF;
ELSE
IF EXISTS(SELECT 1 FROM research_task_command_receipts WHERE id=r.id AND
 xmin=pg_current_xact_id()::xid)
AND NOT EXISTS(SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id
JOIN project_role_assignments pa ON pa.membership_id=m.id JOIN actor_subject_bindings ab ON
 ab.actor_id=a.id
WHERE a.id=r.actor_id AND a.retired_at IS NULL AND m.project_id=r.project_id AND m.status=
 'ACTIVE'
AND pa.role IN ( 'OWNER' , 'RESEARCHER' , 'REVIEWER' , 'APPROVER' , 'VIEWER' )
AND pa.effective_from<=clock_timestamp() AND (pa.effective_until IS NULL OR
 clock_timestamp()<pa.effective_until)
AND ab.status= 'ACTIVE' AND ab.bound_at<=clock_timestamp() AND (ab.revoked_at IS NULL OR
 clock_timestamp()<ab.revoked_at)) THEN
RAISE EXCEPTION 'current gateway read entitlement' USING ERRCODE= '23514' , CONSTRAINT=
 'pr301_scope' ;
END IF;
IF e.prior_status IS DISTINCT FROM e.new_status OR e.stop_human OR e.stop_policy
OR EXISTS(SELECT 1 FROM research_tasks t WHERE t.id=r.research_task_id AND t.plan_sealed_at IS
 NOT NULL
AND NOT EXISTS(SELECT 1 FROM research_task_events se WHERE se.research_task_id=t.id
AND se.event_type= 'PLAN_SEALED' AND se.occurred_at=t.plan_sealed_at AND
 se.task_row_version<r.resulting_row_version))
OR EXISTS(SELECT 1 FROM research_tasks t JOIN execution_budgets eb ON eb.id=t.budget_policy_id
WHERE t.id=r.research_task_id AND eb.receipt_id=r.id) THEN
RAISE EXCEPTION 'gateway task intent seal or policy effect' USING ERRCODE= '23514' , CONSTRAINT=
 'pr301_validation' ;
END IF;
IF (SELECT count(*) FROM research_task_events WHERE research_task_id=r.research_task_id
AND task_row_version=r.resulting_row_version)<>1
OR (SELECT count(*) FROM research_task_receipt_events WHERE receipt_id=r.id)<>1
OR EXISTS(SELECT 1 FROM research_task_receipt_step_events WHERE receipt_id=r.id) THEN
RAISE EXCEPTION 'one gateway task event and no step events' USING ERRCODE= '23514' , CONSTRAINT=
 'pr301_validation' ;
END IF;
IF r.command_name= 'register_agent_tool_policy' THEN
IF NOT EXISTS(SELECT 1 FROM agent_tool_policies p WHERE p.id=r.result_tool_policy_id
AND p.registration_task_id=r.research_task_id AND p.project_id=r.project_id AND
 p.receipt_id=r.id
AND p.created_by=r.actor_id AND p.created_at=r.completed_at)
OR EXISTS(SELECT 1 FROM capability_invocation_refs WHERE receipt_id=r.id) THEN
RAISE EXCEPTION 'policy registration result' USING ERRCODE= '23514' , CONSTRAINT=
 'pr301_validation' ;
END IF;
ELSE
SELECT * INTO ci FROM capability_invocations WHERE id=r.result_capability_invocation_id;
SELECT * INTO ce FROM capability_invocation_events WHERE id=r.result_capability_event_id;
IF ci.id IS NULL OR ce.id IS NULL OR ROW(ci.policy_id,ci.research_task_id,ci.project_id,
ce.invocation_id,ce.receipt_id,ce.invocation_row_version,ce.actor_id,ce.occurred_at,ce.reason)
IS DISTINCT FROM ROW(r.result_tool_policy_id,r.research_task_id,r.project_id,
ci.id,r.id,r.resulting_invocation_revision,r.actor_id,r.completed_at,e.reason)
OR ce.event_type IS DISTINCT FROM (CASE r.command_name WHEN 'request_capability_invocation' THEN
 'REQUESTED'
WHEN 'start_capability_invocation' THEN 'STARTED' ELSE ce.event_type END)
OR (r.command_name= 'finish_capability_invocation' AND ce.event_type NOT IN ( 'FINISHED' ,
 'RECONCILED' )) THEN
RAISE EXCEPTION 'saved gateway result' USING ERRCODE= '23514' , CONSTRAINT= 'pr301_validation' ;
END IF;
IF r.command_name= 'start_capability_invocation' AND EXISTS(SELECT 1 FROM
 capability_invocation_refs WHERE receipt_id=r.id)
OR EXISTS(SELECT 1 FROM capability_invocation_refs ref WHERE ref.receipt_id=r.id AND
(ref.invocation_id<>ci.id OR ref.direction IS DISTINCT FROM
(CASE WHEN r.command_name= 'request_capability_invocation' THEN 'INPUT' ELSE 'OUTPUT' END)))
 THEN
RAISE EXCEPTION 'extra gateway reference effect' USING ERRCODE= '23514' , CONSTRAINT=
 'pr301_validation' ;
END IF;
IF EXISTS(SELECT 1 FROM budget_reservations br WHERE br.receipt_id=r.id AND
ROW(br.id,br.operation_id,br.step_id) IS DISTINCT FROM ROW(ci.reservation_id,ci.id,ci.step_id))
OR EXISTS(SELECT 1 FROM budget_usage_records bu WHERE bu.receipt_id=r.id AND
ROW(bu.id,bu.reservation_id) IS DISTINCT FROM ROW(ce.usage_record_id,ci.reservation_id)) THEN
RAISE EXCEPTION 'extra gateway accounting effect' USING ERRCODE= '23514' , CONSTRAINT=
 'pr301_validation' ;
END IF;
   -- This check is on the fresh receipt only; replay uses saved event revision,
   -- not a later invocation projection.
IF EXISTS(SELECT 1 FROM research_task_command_receipts WHERE id=r.id AND
 xmin=pg_current_xact_id()::xid) THEN
IF ce.event_type= 'RECONCILED' THEN
IF EXISTS(SELECT 1 FROM capability_invocations WHERE id=ci.id AND
 xmin=pg_current_xact_id()::xid) THEN
RAISE EXCEPTION 'reconciliation cannot rewrite invocation' USING ERRCODE= '23514' , CONSTRAINT=
 'pr301_immutable' ;
END IF;
ELSIF NOT EXISTS(SELECT 1 FROM capability_invocations WHERE id=ci.id AND
 xmin=pg_current_xact_id()::xid)
OR ci.row_version IS DISTINCT FROM ce.invocation_row_version OR ci.status IS DISTINCT FROM
 ce.new_status THEN
RAISE EXCEPTION 'missing invocation write' USING ERRCODE= '23514' , CONSTRAINT=
 'pr301_validation' ;
END IF;
END IF;
END IF;
END IF;
PERFORM pr316_validate_receipt(r.id);
RETURN NULL;
END $$;
"""

TRIGGERS = r"""
CREATE TRIGGER pr316_session_insert BEFORE INSERT ON experiment_search_sessions FOR EACH ROW
 EXECUTE FUNCTION pr316_lineage_insert();
CREATE TRIGGER pr316_session_immutable BEFORE UPDATE OR DELETE ON experiment_search_sessions FOR
 EACH ROW EXECUTE FUNCTION pr316_immutable();
CREATE CONSTRAINT TRIGGER pr316_session_complete AFTER INSERT ON experiment_search_sessions
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pr316_effect_complete();
CREATE TRIGGER pr316_node_insert BEFORE INSERT ON experiment_search_nodes FOR EACH ROW EXECUTE
 FUNCTION pr316_lineage_insert();
CREATE TRIGGER pr316_node_immutable BEFORE UPDATE OR DELETE ON experiment_search_nodes FOR EACH
 ROW EXECUTE FUNCTION pr316_immutable();
CREATE CONSTRAINT TRIGGER pr316_node_complete AFTER INSERT ON experiment_search_nodes DEFERRABLE
 INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pr316_effect_complete();
CREATE TRIGGER pr316_link_insert_disabled BEFORE INSERT ON experiment_search_node_runs FOR EACH
 ROW EXECUTE FUNCTION pr316_link_write_disabled();
CREATE TRIGGER pr316_link_immutable BEFORE UPDATE OR DELETE ON experiment_search_node_runs FOR
 EACH ROW EXECUTE FUNCTION pr316_immutable();
CREATE TRIGGER pr316_link_no_truncate BEFORE TRUNCATE ON experiment_search_node_runs FOR EACH
 STATEMENT EXECUTE FUNCTION pr316_immutable();
CREATE TRIGGER pr316_event_insert BEFORE INSERT ON experiment_search_events FOR EACH ROW EXECUTE
 FUNCTION pr316_lineage_insert();
CREATE TRIGGER pr316_event_immutable BEFORE UPDATE OR DELETE ON experiment_search_events FOR
 EACH ROW EXECUTE FUNCTION pr316_immutable();
CREATE CONSTRAINT TRIGGER pr316_event_complete AFTER INSERT ON experiment_search_events
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pr316_effect_complete();
CREATE TRIGGER pr316_session_no_truncate BEFORE TRUNCATE ON experiment_search_sessions FOR EACH
 STATEMENT EXECUTE FUNCTION pr316_immutable();
CREATE TRIGGER pr316_node_no_truncate BEFORE TRUNCATE ON experiment_search_nodes FOR EACH
 STATEMENT EXECUTE FUNCTION pr316_immutable();
CREATE TRIGGER pr316_event_no_truncate BEFORE TRUNCATE ON experiment_search_events FOR EACH
 STATEMENT EXECUTE FUNCTION pr316_immutable();
CREATE TRIGGER pr316_receipt_insert BEFORE INSERT ON research_task_command_receipts FOR EACH ROW
 EXECUTE FUNCTION pr316_receipt_insert();
"""
# Definitions, enabled/timing flags, column properties and PUBLIC privileges are
# pinned against a pristine 0081 on PG18. Explicit grants to deployment roles are
# retained verbatim; they are not a reason to silently rewrite accepted ACLs.
CATALOG = """
SELECT 'constraint',c.conrelid::regclass::text||'.'||c.conname,
 jsonb_build_array(pg_get_constraintdef(c.oid),c.convalidated)::text
FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace
WHERE n.nspname='public'
UNION ALL
SELECT 'index',i.indexrelid::regclass::text,
 jsonb_build_array(pg_get_indexdef(i.indexrelid),i.indisvalid,i.indisready)::text
FROM pg_index i JOIN pg_class t ON t.oid=i.indrelid
JOIN pg_namespace n ON n.oid=t.relnamespace WHERE n.nspname='public'
UNION ALL
SELECT 'trigger',t.tgrelid::regclass::text||'.'||t.tgname,
 jsonb_build_array(pg_get_triggerdef(t.oid),t.tgenabled)::text
FROM pg_trigger t JOIN pg_class r ON r.oid=t.tgrelid
JOIN pg_namespace n ON n.oid=r.relnamespace
WHERE n.nspname='public' AND NOT t.tgisinternal
UNION ALL
SELECT 'function',p.oid::regprocedure::text,pg_get_functiondef(p.oid)
FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
WHERE n.nspname='public' AND p.prokind='f'
UNION ALL
SELECT 'column',r.relname||'.'||a.attname,
 jsonb_build_array(format_type(a.atttypid,a.atttypmod),a.attnotnull,
 a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid))::text
FROM pg_attribute a JOIN pg_class r ON r.oid=a.attrelid
JOIN pg_namespace n ON n.oid=r.relnamespace
LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum
WHERE n.nspname='public' AND r.relkind IN ('r','p') AND a.attnum>0
AND NOT a.attisdropped
UNION ALL
SELECT 'table',r.relname,jsonb_build_array(r.relkind,r.relrowsecurity,
 r.relforcerowsecurity)::text FROM pg_class r
JOIN pg_namespace n ON n.oid=r.relnamespace
WHERE n.nspname='public' AND r.relkind IN ('r','p')
UNION ALL
SELECT 'relation',r.relname,jsonb_build_array(r.relkind,r.relpersistence)::text
FROM pg_class r JOIN pg_namespace n ON n.oid=r.relnamespace WHERE n.nspname='public'
UNION ALL
SELECT 'type',t.typname,jsonb_build_array(t.typtype,t.typcategory,
 t.typbasetype::regtype::text,(SELECT jsonb_agg(e.enumlabel ORDER BY e.enumsortorder)
 FROM pg_enum e WHERE e.enumtypid=t.oid))::text
FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace WHERE n.nspname='public'
UNION ALL
SELECT 'public_table_privilege',r.relname||'.'||a.privilege_type,a.is_grantable::text
FROM pg_class r JOIN pg_namespace n ON n.oid=r.relnamespace
CROSS JOIN LATERAL aclexplode(coalesce(r.relacl,acldefault('r',r.relowner))) a
WHERE n.nspname='public' AND r.relkind IN ('r','p') AND a.grantee=0
UNION ALL
SELECT 'public_function_privilege',p.oid::regprocedure::text||'.'||a.privilege_type,
 a.is_grantable::text FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
CROSS JOIN LATERAL aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a
WHERE n.nspname='public' AND a.grantee=0
ORDER BY 1,2
"""
BASELINE_DIGEST = "84de6b9572aeeac50aea2765c0fbae6fcd605b8e8db98eecbb34bf5e54d8dd07"

PRIVILEGES = """
SELECT r.relname,r.relacl::text FROM pg_class r
JOIN pg_namespace n ON n.oid=r.relnamespace
WHERE n.nspname='public' AND r.relkind IN ('r','p') ORDER BY r.relname
"""
FUNCTION_PRIVILEGES = """
SELECT p.oid::regprocedure::text,p.proacl::text FROM pg_proc p
JOIN pg_namespace n ON n.oid=p.pronamespace
WHERE n.nspname='public' ORDER BY 1
"""


def upgrade() -> None:
    connection = op.get_bind()
    if int(connection.execute(sa.text("SHOW server_version_num")).scalar_one()) // 10000 != 18:
        raise RuntimeError("0082 requires PostgreSQL 18")
    rows = [tuple(row) for row in connection.execute(sa.text(CATALOG))]
    digest = hashlib.sha256(json.dumps(rows, ensure_ascii=False).encode()).hexdigest()
    if digest != BASELINE_DIGEST:
        raise RuntimeError("0082 accepted 0081 catalog drift; forward migration refused")
    old_privileges = dict(connection.execute(sa.text(PRIVILEGES)).all())
    old_function_privileges = dict(connection.execute(sa.text(FUNCTION_PRIVILEGES)).all())
    for definition in (
        SCALAR_FUNCTIONS,
        SESSIONS,
        NODES,
        NODE_RUNS,
        EVENTS,
        INDEXES,
        RECEIPTS,
        GUARDS,
        RECEIPT_COMPLETE,
        TRIGGERS,
    ):
        op.execute(definition)
    # No existing ACL may change when extending the one inherited function.
    privileges = dict(connection.execute(sa.text(PRIVILEGES)).all())
    function_privileges = dict(connection.execute(sa.text(FUNCTION_PRIVILEGES)).all())
    if any(privileges[name] != acl for name, acl in old_privileges.items()) or any(
        function_privileges[name] != acl for name, acl in old_function_privileges.items()
    ):
        raise RuntimeError("0082 changed accepted privileges; forward migration refused")
    tables = (
        "experiment_search_sessions,experiment_search_nodes,"
        "experiment_search_node_runs,experiment_search_events"
    )
    op.execute(f"REVOKE INSERT,UPDATE,DELETE,TRUNCATE ON {tables} FROM PUBLIC")
    roles = (
        connection.execute(
            sa.text("""
        SELECT DISTINCT grantee FROM information_schema.table_privileges
        WHERE table_schema='public' AND table_name IN (
        'experiment_search_sessions','experiment_search_nodes',
        'experiment_search_node_runs','experiment_search_events')
        AND grantee<>current_user AND grantee<>'PUBLIC'
    """)
        )
        .scalars()
        .all()
    )
    for role in roles:
        quoted = connection.dialect.identifier_preparer.quote(role)
        op.execute(f"REVOKE INSERT,UPDATE,DELETE,TRUNCATE ON {tables} FROM {quoted}")


def downgrade() -> None:
    raise RuntimeError("0082 is forward-only; approved forward repair required")
