"""Disabled bearing v2 binding and guards; ADR-0027 O09 only.

Existing routine definitions are edited in place, with uniquely matched anchors.
PostgreSQL CREATE OR REPLACE preserves their OIDs, owners, ACLs and attributes.
No producer, deployment profile or positive admission is supplied by this revision.
"""

import sqlalchemy as sa
from alembic import op

revision = "0083_bearing_evaluation_guards"
down_revision = "0082_experiment_search_core"
branch_labels = None
depends_on = None

ADMIT = "admit_bearing_evaluation_v2"
SETTLE = "settle_bearing_evaluation_v2"
COMMANDS = f"'{ADMIT}','{SETTLE}'"
EVENTS = "'BEARING_EVALUATION_ADMITTED','BEARING_EVALUATION_SETTLED'"
BINDINGS = (
    ("labels_artifact_version_id", "artifact_versions", "pr316d1_labels_av_fk"),
    (
        "baseline_predictions_artifact_version_id",
        "artifact_versions",
        "pr316d1_baseline_predictions_av_fk",
    ),
    (
        "candidate_predictions_artifact_version_id",
        "artifact_versions",
        "pr316d1_candidate_predictions_av_fk",
    ),
    ("protocol_artifact_version_id", "artifact_versions", "pr316d1_protocol_av_fk"),
    ("evaluator_artifact_version_id", "artifact_versions", "pr316d1_evaluator_av_fk"),
    ("dataset_snapshot_id", "dataset_snapshots", "pr316d1_dataset_snapshot_fk"),
    ("metric_definition_version_id", "metric_definition_versions", "pr316d1_metric_version_fk"),
)
COLUMNS = tuple(c for c, _, _ in BINDINGS) + ("consumer_generation",)

AUTHORITY = r"""
CREATE FUNCTION pr316d1_authority(r research_task_command_receipts) RETURNS void
LANGUAGE plpgsql VOLATILE SECURITY INVOKER
SET search_path=pg_catalog,public,pg_temp AS $body$
DECLARE at_time timestamptz;
BEGIN
PERFORM pr316_preheld(r);
-- All metadata is reread after the caller's existing project/command/task locks.
PERFORM id FROM research_tasks WHERE id=r.research_task_id FOR UPDATE;
at_time:=clock_timestamp();
IF r.command_name NOT IN ('admit_bearing_evaluation_v2','settle_bearing_evaluation_v2')
OR NOT EXISTS(SELECT 1 FROM projects p JOIN project_memberships m ON m.project_id=p.id
JOIN project_role_assignments ro ON ro.membership_id=m.id JOIN actors a ON a.id=m.actor_id
JOIN actor_subject_bindings b ON b.actor_id=a.id
WHERE p.id=r.project_id AND p.lifecycle_status='ACTIVE' AND a.id=r.actor_id
AND a.retired_at IS NULL AND m.status='ACTIVE' AND m.started_at<=at_time
AND ro.effective_from<=at_time AND (ro.effective_until IS NULL OR ro.effective_until>at_time)
AND b.status='ACTIVE' AND b.bound_at<=at_time AND (b.revoked_at IS NULL OR b.revoked_at>at_time)
AND ((a.actor_type='HUMAN' AND ro.role IN ('OWNER','RESEARCHER')) OR
(a.actor_type='AGENT' AND ro.role='RESEARCHER' AND b.subject_kind='MTLS_URI'
AND b.proof_kind='MTLS_CHALLENGE' AND EXISTS(SELECT 1 FROM agent_command_receipts enrolled
WHERE enrolled.operation='provision_project_agent' AND enrolled.result_actor_id=a.id
AND enrolled.project_id=p.id AND enrolled.result_binding_id=b.id)))) THEN
RAISE EXCEPTION 'bearing current authority' USING ERRCODE='23514',CONSTRAINT='pr316_scope';
END IF;
IF NOT EXISTS(SELECT 1 FROM research_tasks WHERE id=r.research_task_id
AND project_id=r.project_id AND row_version=r.resulting_row_version
AND xmin=pg_current_xact_id()::xid
AND (status IN ('CREATED','PLANNING') OR
(r.command_name='settle_bearing_evaluation_v2' AND status='CANCELLED'))) THEN
RAISE EXCEPTION 'bearing fresh task/state' USING ERRCODE='23514',CONSTRAINT='pr316_state';
END IF;
END $body$;
"""

ADMISSION = r"""
CREATE FUNCTION pr316d1_admission(n experiment_search_nodes) RETURNS void
LANGUAGE plpgsql VOLATILE SECURITY INVOKER
SET search_path=pg_catalog,public,pg_temp AS $body$
DECLARE r budget_reservations%ROWTYPE; cr research_task_command_receipts%ROWTYPE;
s experiment_search_sessions%ROWTYPE; t research_tasks%ROWTYPE;
b execution_budgets%ROWTYPE; c checkpoint_policies%ROWTYPE; term termination_policies%ROWTYPE;
st research_task_steps%ROWTYPE; cur uuid; seen uuid[]:=ARRAY[]::uuid[]; d integer:=0;
origin timestamptz; at_time timestamptz; k text; total numeric; cap numeric;
gate text; gate_status text; meta record; expected integer; actual integer;
BEGIN
SELECT * INTO cr FROM research_task_command_receipts WHERE id=n.receipt_id
AND research_task_id=n.research_task_id AND xmin=pg_current_xact_id()::xid;
PERFORM pr316d1_authority(cr);
SELECT * INTO t FROM research_tasks WHERE id=n.research_task_id;
SELECT * INTO s FROM experiment_search_sessions WHERE id=n.search_session_id
AND research_task_id=t.id AND project_id=t.project_id AND xmin<>pg_current_xact_id()::xid;
SELECT * INTO r FROM budget_reservations WHERE id=n.reservation_id
AND receipt_id=cr.id AND research_task_id=t.id AND xmin=pg_current_xact_id()::xid;
SELECT * INTO b FROM execution_budgets WHERE id=t.budget_policy_id AND research_task_id=t.id;
SELECT * INTO c FROM checkpoint_policies WHERE id=t.checkpoint_policy_id AND research_task_id=t.id;
SELECT * INTO term FROM termination_policies WHERE id=t.termination_policy_id
AND research_task_id=t.id;
at_time:=clock_timestamp();
IF cr.id IS NULL OR cr.command_name<>'admit_bearing_evaluation_v2' OR s.id IS NULL
OR r.id IS NULL OR b.id IS NULL OR c.id IS NULL OR term.id IS NULL
OR t.autonomy_level NOT IN ('A0','A1') OR t.autonomy_level>c.maximum_autonomy
OR r.budget_id IS DISTINCT FROM b.id OR s.budget_id IS DISTINCT FROM b.id
OR ROW(n.id,n.search_session_id) IS DISTINCT FROM ROW(cr.result_search_node_id,
cr.result_search_session_id) OR r.operation_id IS DISTINCT FROM n.id
OR r.created_at IS DISTINCT FROM transaction_timestamp()
OR cr.completed_at IS DISTINCT FROM r.created_at OR n.created_at IS DISTINCT FROM r.created_at
OR n.created_by IS DISTINCT FROM cr.actor_id
OR num_nonnulls(r.labels_artifact_version_id,r.baseline_predictions_artifact_version_id,
r.candidate_predictions_artifact_version_id,r.protocol_artifact_version_id,
r.evaluator_artifact_version_id,r.dataset_snapshot_id,r.metric_definition_version_id,
r.consumer_generation)<>8
OR ROW(r.agent_steps,r.llm_calls,r.search_calls,r.code_iterations,r.experiment_runs,
r.tree_nodes,r.gpu_hours,r.token_cost) IS DISTINCT FROM ROW(1::bigint,0::bigint,0::bigint,
0::bigint,0::bigint,1::bigint,0::numeric,0::numeric)
OR r.observed_depth<>n.depth OR n.depth>3 OR n.depth>b.max_tree_depth
OR r.observed_parallel_branches<>1 OR r.wall_time_seconds<=0
OR r.deadline IS DISTINCT FROM r.created_at+r.wall_time_seconds*interval '1 second'
OR r.deadline<=at_time OR EXISTS(SELECT 1 FROM budget_usage_records WHERE reservation_id=r.id)
OR EXISTS(SELECT 1 FROM experiment_search_nodes WHERE reservation_id=r.id AND id<>n.id) THEN
RAISE EXCEPTION 'bearing admission shape/deadline' USING ERRCODE='23514',
CONSTRAINT='pr316d1_admission'; END IF;
SELECT min(created_at) INTO origin FROM budget_reservations WHERE research_task_id=t.id;
IF r.deadline>origin+b.max_wall_time_seconds*interval '1 second'
OR at_time>=origin+b.max_wall_time_seconds*interval '1 second' THEN
RAISE EXCEPTION 'bearing task origin deadline' USING ERRCODE='23514',
CONSTRAINT='pr316d1_deadline'; END IF;
cur:=r.step_id;
WHILE cur IS NOT NULL LOOP
IF cur=ANY(seen) THEN RAISE EXCEPTION 'bearing step cycle' USING ERRCODE='23514',
CONSTRAINT='pr316_reference'; END IF;
seen:=array_append(seen,cur);
SELECT * INTO st FROM research_task_steps WHERE id=cur AND research_task_id=t.id;
IF NOT FOUND THEN RAISE EXCEPTION 'bearing step scope' USING ERRCODE='23503',
CONSTRAINT='pr316_reference'; END IF;
IF d=0 AND n.parent_node_id IS NOT NULL AND NOT EXISTS(
SELECT 1 FROM experiment_search_nodes pn JOIN budget_reservations br ON br.id=pn.reservation_id
WHERE pn.id=n.parent_node_id AND pn.research_task_id=t.id AND pn.search_session_id=s.id
AND br.step_id IS NOT DISTINCT FROM st.parent_step_id) THEN
RAISE EXCEPTION 'bearing immediate mapped parent' USING ERRCODE='23514',
CONSTRAINT='pr316_reference'; END IF;
cur:=st.parent_step_id;
IF cur IS NOT NULL THEN d:=d+1; END IF;
END LOOP;
IF d<>n.depth OR (r.step_id IS NULL AND n.depth<>0)
OR n.depth<>pr316_chain(t.id,s.id,n.parent_node_id)+1 THEN
RAISE EXCEPTION 'bearing mapped depth' USING ERRCODE='23514',CONSTRAINT='pr316_reference';
END IF;
-- Metadata only: snapshots are immutable records, with no FROZEN status column.
SELECT count(*) INTO actual FROM unnest(ARRAY[r.labels_artifact_version_id,
r.baseline_predictions_artifact_version_id,r.candidate_predictions_artifact_version_id,
r.protocol_artifact_version_id,r.evaluator_artifact_version_id]) role_id
JOIN artifact_versions av ON av.id=role_id JOIN artifacts a ON a.id=av.artifact_id
WHERE a.project_id=t.project_id AND av.status='FROZEN' AND av.frozen_at IS NOT NULL
AND av.content_hash IS NOT NULL;
IF actual<>5 OR NOT EXISTS(SELECT 1 FROM dataset_snapshots ds
JOIN datasets ds_owner ON ds_owner.id=ds.dataset_id WHERE ds.id=r.dataset_snapshot_id
AND ds_owner.project_id=t.project_id AND ds.manifest_hash IS NOT NULL
AND ds.content_hash IS NOT NULL) OR NOT EXISTS(SELECT 1 FROM metric_definition_versions mv
JOIN metric_definitions md ON md.id=mv.metric_definition_id
WHERE mv.id=r.metric_definition_version_id AND md.project_id=t.project_id
AND mv.status='FROZEN' AND mv.frozen_at IS NOT NULL AND mv.content_hash IS NOT NULL
AND term.score_metric_version_id=mv.id AND term.score_direction='MAXIMIZE'
AND mv.definition->>'kind'='paired_accuracy_delta'
AND term.evaluator_version IS NOT NULL) THEN
RAISE EXCEPTION 'bearing canonical binding metadata' USING ERRCODE='23514',
CONSTRAINT='pr316d1_binding'; END IF;
-- Compare immutable owners, never a role/GUC or the attribution-only generation.
IF EXISTS(SELECT 1 FROM budget_usage_records u JOIN budget_reservations br
ON br.id=u.reservation_id WHERE br.research_task_id=t.id
AND br.step_id IS NOT DISTINCT FROM r.step_id AND br.consumer_generation IS NULL
AND u.score IS NOT NULL) OR EXISTS(SELECT 1 FROM budget_reservations br
WHERE br.research_task_id=t.id AND br.step_id IS NOT DISTINCT FROM r.step_id
AND br.consumer_generation IS NOT NULL AND br.id<>r.id
AND ROW(br.labels_artifact_version_id,br.baseline_predictions_artifact_version_id,
br.protocol_artifact_version_id,br.evaluator_artifact_version_id,br.dataset_snapshot_id,
br.metric_definition_version_id) IS DISTINCT FROM
ROW(r.labels_artifact_version_id,r.baseline_predictions_artifact_version_id,
r.protocol_artifact_version_id,r.evaluator_artifact_version_id,r.dataset_snapshot_id,
r.metric_definition_version_id)) THEN
RAISE EXCEPTION 'bearing mixed comparison history' USING ERRCODE='23514',
CONSTRAINT='pr316d1_comparison'; END IF;
-- Prefix excludes only this command's own effects, retaining every prior sticky stop.
IF EXISTS(SELECT 1 FROM research_task_events e WHERE e.research_task_id=t.id
AND e.task_row_version<cr.resulting_row_version AND (e.stop_human OR e.stop_policy
OR e.stop_budget OR e.stop_repeated_failure OR e.stop_no_improvement OR e.stop_success))
OR EXISTS(SELECT 1 FROM budget_usage_records u WHERE u.research_task_id=t.id AND u.is_final
AND (u.failure_streak>=term.repeated_failure_threshold OR
u.no_improvement_streak>=term.max_no_improvement_iterations)) THEN
RAISE EXCEPTION 'bearing prior stop' USING ERRCODE='23514',CONSTRAINT='pr316_state'; END IF;
FOREACH k IN ARRAY ARRAY['agent_steps','llm_calls','search_calls','code_iterations',
'experiment_runs','tree_nodes','gpu_hours','token_cost'] LOOP
SELECT coalesce(sum(CASE WHEN u.id IS NULL THEN (to_jsonb(br)->>k)::numeric
ELSE (to_jsonb(u)->>k)::numeric END),0) INTO total
FROM budget_reservations br LEFT JOIN budget_usage_records u
ON u.reservation_id=br.id AND u.is_final WHERE br.research_task_id=t.id AND br.id<>r.id;
cap:=(to_jsonb(b)->>('max_'||k))::numeric;
IF total>cap OR (cap>0 AND total>=cap) OR total+(to_jsonb(r)->>k)::numeric>cap THEN
RAISE EXCEPTION 'bearing prefix cap' USING ERRCODE='23514',CONSTRAINT='pr316_state'; END IF;
END LOOP;
SELECT count(*) INTO expected FROM budget_reservations br WHERE br.research_task_id=t.id
AND NOT EXISTS(SELECT 1 FROM budget_usage_records u WHERE u.reservation_id=br.id AND u.is_final);
IF expected<>r.observed_parallel_branches OR expected>b.max_parallel_branches THEN
RAISE EXCEPTION 'bearing occupancy' USING ERRCODE='23514',CONSTRAINT='pr316_state'; END IF;
FOREACH gate IN ARRAY c.required_types||ARRAY['plan_review'] LOOP
SELECT status INTO gate_status FROM human_checkpoints WHERE research_task_id=t.id
AND step_id IS NOT DISTINCT FROM r.step_id AND checkpoint_type=gate
ORDER BY created_at DESC,id DESC LIMIT 1;
IF gate_status IS DISTINCT FROM 'APPROVED' THEN
RAISE EXCEPTION 'bearing checkpoint' USING ERRCODE='23514',CONSTRAINT='pr316_state'; END IF;
END LOOP;
PERFORM pr316_refs(t.project_id,n.hypothesis_version_id,n.hypothesis_content_hash,
n.experiment_spec_version_id,n.experiment_spec_content_hash);
-- The literal disabled helper is checked at receipt completion, after all proofs.
-- Registered implementation and measured remaining-phase allowance require Stage 3.
END $body$;
"""

VALIDATE = r"""
CREATE FUNCTION pr316d1_validate_receipt(p_receipt uuid) RETURNS void
LANGUAGE plpgsql VOLATILE SECURITY INVOKER
SET search_path=pg_catalog,public,pg_temp AS $body$
DECLARE r research_task_command_receipts%ROWTYPE; br budget_reservations%ROWTYPE;
u budget_usage_records%ROWTYPE; n experiment_search_nodes%ROWTYPE;
e experiment_search_events%ROWTYPE; te research_task_events%ROWTYPE;
args jsonb; binding jsonb; vector jsonb; material jsonb; ids uuid[];
meta record; i integer; field text; admission boolean; fresh boolean;
BEGIN
SELECT * INTO r FROM research_task_command_receipts WHERE id=p_receipt;
IF r.id IS NULL OR r.command_name NOT IN
('admit_bearing_evaluation_v2','settle_bearing_evaluation_v2') THEN
RAISE EXCEPTION 'bearing receipt required' USING ERRCODE='23514',CONSTRAINT='pr316d1_receipt';
END IF;
SELECT EXISTS(SELECT 1 FROM research_task_command_receipts WHERE id=r.id
AND xmin=pg_current_xact_id()::xid) INTO fresh;
IF NOT fresh OR r.completed_at IS DISTINCT FROM transaction_timestamp()
OR r.material_version<>2 OR r.hash_scheme<>'sha256-cjson-v1' THEN
RAISE EXCEPTION 'bearing fresh receipt' USING ERRCODE='23514',CONSTRAINT='pr316_completeness';
END IF;
PERFORM pr316d1_authority(r);
admission:=r.command_name='admit_bearing_evaluation_v2';
SELECT ev.* INTO te FROM research_task_receipt_events re JOIN research_task_events ev
ON ev.id=re.event_id WHERE re.receipt_id=r.id;
IF te.id IS NULL OR NOT pr316_uuid7(te.id) OR NOT EXISTS(SELECT 1 FROM research_task_events
WHERE id=te.id AND xmin=pg_current_xact_id()::xid)
OR (SELECT count(*) FROM research_task_receipt_events WHERE receipt_id=r.id)<>1
OR (SELECT count(*) FROM research_task_events WHERE research_task_id=r.research_task_id
AND task_row_version=r.resulting_row_version)<>1
OR ROW(te.research_task_id,te.actor_id,te.command_id,te.task_row_version,te.sequence,
te.occurred_at) IS DISTINCT FROM ROW(r.research_task_id,r.actor_id,r.command_id,
r.resulting_row_version,r.resulting_row_version,r.completed_at)
OR te.event_type IS DISTINCT FROM (CASE WHEN admission THEN 'BEARING_EVALUATION_ADMITTED'
ELSE 'BEARING_EVALUATION_SETTLED' END)
OR te.prior_status IS DISTINCT FROM te.new_status
OR pr316_reason(te.reason) IS DISTINCT FROM true
OR te.stop_human OR te.stop_policy OR te.stop_success
OR (admission AND (te.stop_repeated_failure OR te.stop_no_improvement))
OR EXISTS(SELECT 1 FROM research_task_receipt_step_events WHERE receipt_id=r.id)
OR EXISTS(SELECT 1 FROM experiment_search_sessions WHERE receipt_id=r.id)
OR EXISTS(SELECT 1 FROM experiment_search_node_runs WHERE receipt_id=r.id)
OR (SELECT count(*) FROM experiment_search_nodes WHERE receipt_id=r.id)<>admission::integer
OR (SELECT count(*) FROM experiment_search_events WHERE receipt_id=r.id)<>admission::integer
OR (SELECT count(*) FROM budget_reservations WHERE receipt_id=r.id)<>admission::integer
OR (SELECT count(*) FROM budget_usage_records WHERE receipt_id=r.id)<>(NOT admission)::integer
OR EXISTS(SELECT 1 FROM research_task_steps WHERE research_task_id=r.research_task_id
AND xmin=pg_current_xact_id()::xid)
OR EXISTS(SELECT 1 FROM research_task_inputs WHERE research_task_id=r.research_task_id
AND xmin=pg_current_xact_id()::xid)
OR EXISTS(SELECT 1 FROM research_task_step_inputs WHERE research_task_id=r.research_task_id
AND xmin=pg_current_xact_id()::xid)
OR EXISTS(SELECT 1 FROM research_task_step_dependencies WHERE research_task_id=r.research_task_id
AND xmin=pg_current_xact_id()::xid)
OR EXISTS(SELECT 1 FROM research_tasks t WHERE t.id=r.research_task_id
AND t.plan_sealed_at IS NOT NULL AND NOT EXISTS(SELECT 1 FROM research_task_events se
WHERE se.research_task_id=t.id AND se.event_type='PLAN_SEALED'
AND se.occurred_at=t.plan_sealed_at AND se.task_row_version<r.resulting_row_version)) THEN
RAISE EXCEPTION 'bearing exact effects' USING ERRCODE='23514',CONSTRAINT='pr316_completeness';
END IF;
IF admission THEN
SELECT * INTO br FROM budget_reservations WHERE receipt_id=r.id;
SELECT * INTO n FROM experiment_search_nodes WHERE id=r.result_search_node_id AND receipt_id=r.id
AND xmin=pg_current_xact_id()::xid;
SELECT * INTO e FROM experiment_search_events WHERE id=r.result_search_event_id AND receipt_id=r.id
AND xmin=pg_current_xact_id()::xid;
IF n.id IS NULL OR e.id IS NULL THEN
RAISE EXCEPTION 'bearing fresh search effects' USING ERRCODE='23514',
CONSTRAINT='pr316_completeness'; END IF;
PERFORM pr316_state(r,e);
IF (SELECT count(*) FROM experiment_search_events WHERE search_session_id=e.search_session_id)
<>e.sequence OR e.sequence>11 OR (SELECT count(*) FROM experiment_search_nodes
WHERE search_session_id=e.search_session_id)>10 THEN
RAISE EXCEPTION 'bearing complete read bounds' USING ERRCODE='23514',
CONSTRAINT='pr316_completeness'; END IF;
vector:=to_jsonb(br);
args:=jsonb_build_object('session_id',n.search_session_id::text,'node_id',n.id::text,
'branch_kind',n.branch_kind,'mutation_reason',n.mutation_reason,'reservation_id',br.id::text,
'parent_node_id',n.parent_node_id::text,'hypothesis_version_id',n.hypothesis_version_id::text,
'experiment_spec_version_id',n.experiment_spec_version_id::text,'step_id',br.step_id::text,
'operation_id',br.operation_id::text,'observed_depth',br.observed_depth,
'observed_parallel_branches',br.observed_parallel_branches,
'deadline_seconds',br.wall_time_seconds,'reason',te.reason);
ELSE
SELECT * INTO u FROM budget_usage_records WHERE receipt_id=r.id
AND xmin=pg_current_xact_id()::xid;
SELECT * INTO br FROM budget_reservations WHERE id=u.reservation_id
AND research_task_id=r.research_task_id AND xmin<>pg_current_xact_id()::xid;
IF u.id IS NULL OR br.id IS NULL OR br.consumer_generation IS NULL
OR u.created_at IS DISTINCT FROM r.completed_at
OR num_nonnulls(r.result_search_session_id,r.result_search_node_id,r.result_search_event_id)<>0
OR (u.evaluator_version IS NOT NULL AND
lower(btrim(u.evaluator_version)) IN ('latest','main','master','current','live'))
OR (u.outcome='SUCCEEDED' AND (u.score IS NULL OR u.evaluator_version IS NULL
OR u.score NOT BETWEEN -1 AND 1))
OR (u.outcome<>'SUCCEEDED' AND (u.score IS NOT NULL OR u.evaluator_version IS NOT NULL)) THEN
RAISE EXCEPTION 'bearing settlement owner/outcome' USING ERRCODE='23514',
CONSTRAINT='pr316d1_binding'; END IF;
vector:=to_jsonb(u);
args:=jsonb_build_object('reservation_id',br.id::text,'outcome',u.outcome,
'score',CASE WHEN u.score IS NULL THEN NULL ELSE to_char(u.score,
'FM999999999999990.000000') END,'evaluator_version',u.evaluator_version,'reason',te.reason);
END IF;
ids:=ARRAY[br.labels_artifact_version_id,br.baseline_predictions_artifact_version_id,
br.candidate_predictions_artifact_version_id,br.protocol_artifact_version_id,
br.evaluator_artifact_version_id];
binding:=jsonb_build_object('labels_artifact_version_id',ids[1]::text,
'baseline_predictions_artifact_version_id',ids[2]::text,
'candidate_predictions_artifact_version_id',ids[3]::text,'protocol_artifact_version_id',ids[4]::text,
'evaluator_artifact_version_id',ids[5]::text,'dataset_snapshot_id',br.dataset_snapshot_id::text,
'metric_definition_version_id',br.metric_definition_version_id::text,
'consumer_generation',br.consumer_generation::text);
FOR i IN 1..5 LOOP
SELECT av.content_hash,a.project_id,av.status,av.frozen_at INTO meta
FROM artifact_versions av JOIN artifacts a ON a.id=av.artifact_id WHERE av.id=ids[i];
IF NOT FOUND OR meta.project_id IS DISTINCT FROM r.project_id OR meta.status<>'FROZEN'
OR meta.frozen_at IS NULL OR meta.content_hash IS NULL THEN
RAISE EXCEPTION 'bearing artifact owner' USING ERRCODE='23514',CONSTRAINT='pr316d1_binding';
END IF;
field:=(ARRAY['labels_content_hash','baseline_predictions_content_hash',
'candidate_predictions_content_hash','protocol_content_hash','evaluator_content_hash'])[i];
binding:=binding||jsonb_build_object(field,meta.content_hash::text);
END LOOP;
SELECT ds.manifest_hash,ds.content_hash,d.project_id INTO meta
FROM dataset_snapshots ds JOIN datasets d ON d.id=ds.dataset_id WHERE ds.id=br.dataset_snapshot_id;
IF NOT FOUND OR meta.project_id IS DISTINCT FROM r.project_id THEN
RAISE EXCEPTION 'bearing dataset owner' USING ERRCODE='23514',CONSTRAINT='pr316d1_binding';
END IF;
binding:=binding||jsonb_build_object('dataset_manifest_hash',meta.manifest_hash::text,
'dataset_content_hash',meta.content_hash::text);
SELECT mv.content_hash,md.project_id,mv.status,mv.frozen_at INTO meta
FROM metric_definition_versions mv JOIN metric_definitions md ON md.id=mv.metric_definition_id
JOIN research_tasks t ON t.id=r.research_task_id
JOIN termination_policies term ON term.id=t.termination_policy_id
WHERE mv.id=br.metric_definition_version_id AND term.score_metric_version_id=mv.id
AND term.score_direction='MAXIMIZE'
AND mv.definition->>'kind'='paired_accuracy_delta'
AND (admission OR u.evaluator_version IS NULL OR u.evaluator_version=term.evaluator_version);
IF NOT FOUND OR meta.project_id IS DISTINCT FROM r.project_id OR meta.status<>'FROZEN'
OR meta.frozen_at IS NULL OR meta.content_hash IS NULL THEN
RAISE EXCEPTION 'bearing metric owner' USING ERRCODE='23514',CONSTRAINT='pr316d1_binding';
END IF;
binding:=binding||jsonb_build_object('metric_content_hash',meta.content_hash::text);
-- Preserve JSON integer types and the two exact six-place decimal strings.
vector:=jsonb_build_object('wall_time_seconds',vector->'wall_time_seconds',
'agent_steps',vector->'agent_steps','llm_calls',vector->'llm_calls',
'search_calls',vector->'search_calls','code_iterations',vector->'code_iterations',
'experiment_runs',vector->'experiment_runs','tree_nodes',vector->'tree_nodes',
'gpu_hours',to_char((vector->>'gpu_hours')::numeric,'FM999999999999990.000000'),
'token_cost',to_char((vector->>'token_cost')::numeric,'FM999999999999990.000000'));
args:=args||binding||jsonb_build_object(CASE WHEN admission THEN 'resources' ELSE 'measured' END,
vector);
material:=jsonb_build_object('type','BearingEvaluationCommand','material_version',2,
'command_name',r.command_name,'project_id',r.project_id::text,'actor_id',r.actor_id::text,
'command_id',r.command_id::text,'task_id',r.research_task_id::text,
'expected_row_version',r.resulting_row_version-1,'arguments',args);
IF r.request_hash IS DISTINCT FROM pr302s2_value_digest(material) THEN
RAISE EXCEPTION 'bearing request digest' USING ERRCODE='23514',CONSTRAINT='pr316_provenance';
END IF;
PERFORM pr304_validate_safety(r.research_task_id);
IF admission AND br.deadline<=clock_timestamp() THEN
RAISE EXCEPTION 'bearing expired at deferred completion' USING ERRCODE='23514',
CONSTRAINT='pr316d1_deadline'; END IF;
-- This is deliberately last: complete candidates exercise every preceding proof.
IF NOT pr316d1_enabled() THEN
RAISE EXCEPTION 'bearing Stage2 disabled' USING ERRCODE='23514',CONSTRAINT='pr316d1_disabled';
END IF;
END $body$;
"""

# Ownership is checked immediately and again under the task lock at deferred completion.
CHILD_OWNERSHIP = r"""
 IF TG_TABLE_NAME='budget_reservations' THEN
  IF (NEW.consumer_generation IS NOT NULL) IS DISTINCT FROM
     (r.command_name='admit_bearing_evaluation_v2') THEN
   RAISE EXCEPTION 'bearing reservation command owner' USING ERRCODE='23514',
   CONSTRAINT='pr316d1_binding'; END IF;
 ELSIF TG_TABLE_NAME='budget_usage_records' THEN
  IF NOT EXISTS(SELECT 1 FROM budget_reservations br WHERE br.id=NEW.reservation_id
    AND br.research_task_id=t.id AND (br.consumer_generation IS NOT NULL) =
    (r.command_name='settle_bearing_evaluation_v2')) THEN
   RAISE EXCEPTION 'bearing usage command owner' USING ERRCODE='23514',
   CONSTRAINT='pr316d1_binding'; END IF;
  IF r.command_name IN ('settle_task_budget','finish_capability_invocation')
   AND NEW.score IS NOT NULL AND EXISTS(SELECT 1 FROM budget_reservations br
    JOIN budget_reservations own ON own.id=NEW.reservation_id
    WHERE br.research_task_id=t.id AND br.step_id IS NOT DISTINCT FROM own.step_id
    AND br.consumer_generation IS NOT NULL) THEN
   RAISE EXCEPTION 'legacy score in bearing scope' USING ERRCODE='23514',
   CONSTRAINT='pr316d1_comparison'; END IF;
 END IF;
"""

SAFETY_OWNERSHIP = r"""
 -- Only new effects are rechecked: historical v1 material/replay is unchanged.
 IF EXISTS(SELECT 1 FROM budget_reservations br JOIN research_task_command_receipts cr
 ON cr.id=br.receipt_id WHERE br.research_task_id=p_task AND br.xmin=pg_current_xact_id()::xid
 AND (br.consumer_generation IS NOT NULL) IS DISTINCT FROM
 (cr.command_name='admit_bearing_evaluation_v2')) OR EXISTS(
 SELECT 1 FROM budget_usage_records bu JOIN budget_reservations br ON br.id=bu.reservation_id
 JOIN research_task_command_receipts cr ON cr.id=bu.receipt_id
 WHERE bu.research_task_id=p_task AND bu.xmin=pg_current_xact_id()::xid AND
 ((br.consumer_generation IS NOT NULL) IS DISTINCT FROM
 (cr.command_name='settle_bearing_evaluation_v2') OR
 (cr.command_name IN ('settle_task_budget','finish_capability_invocation') AND bu.score IS NOT NULL
 AND EXISTS(SELECT 1 FROM budget_reservations other WHERE other.research_task_id=p_task
 AND other.step_id IS NOT DISTINCT FROM br.step_id AND other.consumer_generation IS NOT NULL))))
 THEN RAISE EXCEPTION 'bearing deferred ownership/comparison' USING ERRCODE='23514',
 CONSTRAINT='pr316d1_comparison'; END IF;
 IF EXISTS(SELECT 1 FROM budget_reservations br JOIN budget_usage_records scored_usage
 ON scored_usage.research_task_id=br.research_task_id JOIN budget_reservations legacy
 ON legacy.id=scored_usage.reservation_id WHERE br.research_task_id=p_task
 AND br.xmin=pg_current_xact_id()::xid AND br.consumer_generation IS NOT NULL
 AND legacy.consumer_generation IS NULL AND legacy.step_id IS NOT DISTINCT FROM br.step_id
 AND scored_usage.score IS NOT NULL) THEN
 RAISE EXCEPTION 'bearing against legacy scores' USING ERRCODE='23514',
 CONSTRAINT='pr316d1_comparison'; END IF;
"""


def _edit(definition: str, old: str, new: str) -> str:
    if definition.count(old) != 1:
        raise RuntimeError("0083 accepted routine anchor drift; forward migration refused")
    return definition.replace(old, new, 1)


def _extend_check(table: str, name: str, expression) -> None:
    connection = op.get_bind()
    old = connection.execute(
        sa.text(
            "SELECT pg_get_expr(conbin,conrelid) FROM pg_constraint "
            "WHERE conrelid=CAST(:table AS regclass) AND conname=:name"
        ),
        {"table": table, "name": name},
    ).scalar_one()
    op.execute(f'ALTER TABLE {table} DROP CONSTRAINT "{name}"')
    op.execute(f'ALTER TABLE {table} ADD CONSTRAINT "{name}" CHECK ({expression(old)})')


def amend_function(signature: str, original: str) -> str:
    sql = original
    if signature == "pr316_command_event(text)":
        sql = _edit(
            sql,
            "WHEN 'append_search_node'",
            f"WHEN '{ADMIT}' THEN 'BEARING_EVALUATION_ADMITTED'\nWHEN 'append_search_node'",
        )
    elif signature == "pr316_receipt_insert()":
        sql = _edit(
            sql,
            "BEGIN\n",
            f"""BEGIN
IF NEW.command_name IN ({COMMANDS}) THEN
PERFORM pr316d1_authority(NEW);
IF NOT pr316_uuid7(NEW.id) THEN
RAISE EXCEPTION 'bearing receipt UUIDv7' USING ERRCODE='23514',CONSTRAINT='pr316_validation';
END IF;
NEW.completed_at:=transaction_timestamp();
RETURN NEW;
END IF;
""",
        )
    elif signature.startswith("pr316_node_proof("):
        sql = _edit(
            sql,
            "BEGIN\n",
            f"""BEGIN
IF EXISTS(SELECT 1 FROM research_task_command_receipts cr WHERE cr.id=n.receipt_id
AND cr.command_name='{ADMIT}') THEN
PERFORM pr316d1_admission(n); RETURN;
END IF;
""",
        )
    elif signature.startswith("pr316_state("):
        sql = _edit(
            sql,
            "CASE r.command_name\n",
            f"""CASE r.command_name
WHEN '{ADMIT}' THEN
expected_kind:='NODE_APPENDED';
IF n.receipt_id IS DISTINCT FROM r.id OR e.reason IS DISTINCT FROM n.mutation_reason
OR n.depth<>pr316_chain(r.research_task_id,s.id,n.parent_node_id)+1 THEN
RAISE EXCEPTION 'bearing append shape' USING ERRCODE='23514',CONSTRAINT='pr316_validation';
END IF;
PERFORM pr316d1_admission(n);
""",
        )
    elif signature == "pr316_lineage_insert()":
        sql = _edit(
            sql,
            "r.command_name<> 'append_search_node'",
            f"r.command_name NOT IN ('append_search_node','{ADMIT}')",
        )
    elif signature == "pr316_validate_receipt(uuid)":
        sql = _edit(
            sql,
            "search_command:=",
            f"""IF r.command_name IN ({COMMANDS}) THEN
PERFORM pr316d1_validate_receipt(r.id); RETURN;
END IF;
search_command:=""",
        )
    elif signature == "pr304_child_guard()":
        sql = _edit(
            sql,
            "ARRAY['reserve_task_budget','request_capability_invocation']",
            f"ARRAY['reserve_task_budget','request_capability_invocation','{ADMIT}']",
        )
        sql = _edit(
            sql,
            "ARRAY['settle_task_budget','finish_capability_invocation']",
            f"ARRAY['settle_task_budget','finish_capability_invocation','{SETTLE}']",
        )
        sql = _edit(
            sql,
            "r.command_name NOT IN ('settle_task_budget','finish_capability_invocation')",
            f"r.command_name NOT IN "
            f"('settle_task_budget','finish_capability_invocation','{SETTLE}')",
        )
        sql = _edit(sql, " RETURN NEW;", CHILD_OWNERSHIP + " RETURN NEW;")
    elif signature == "pr304_validate_safety(uuid)":
        sql = _edit(sql, "BEGIN\n", "BEGIN\n" + SAFETY_OWNERSHIP)
        sql = _edit(
            sql,
            "'request_capability_invocation','finish_capability_invocation') THEN",
            f"'request_capability_invocation','finish_capability_invocation',{COMMANDS}) THEN",
        )
    elif signature == "pr301_receipt_complete()":
        sql = _edit(
            sql,
            "WHEN 'append_search_node' THEN 'SEARCH_NODE_APPENDED' END;",
            f"WHEN 'append_search_node' THEN 'SEARCH_NODE_APPENDED'\nWHEN '{ADMIT}' "
            f"THEN 'BEARING_EVALUATION_ADMITTED'\nWHEN '{SETTLE}' THEN "
            f"'BEARING_EVALUATION_SETTLED' END;",
        )
        sql = _edit(
            sql,
            "IN ( 'reserve_task_budget' , 'request_capability_invocation' )",
            f"IN ( 'reserve_task_budget' , 'request_capability_invocation' , '{ADMIT}' )",
        )
        sql = _edit(
            sql,
            "IN ( 'settle_task_budget' , 'finish_capability_invocation' )",
            f"IN ( 'settle_task_budget' , 'finish_capability_invocation' , '{SETTLE}' )",
        )
        sql = _edit(
            sql,
            " , 'finish_capability_invocation' ) THEN\nIF r.completed_at",
            f" , 'finish_capability_invocation', {COMMANDS} ) THEN\nIF r.completed_at",
        )
        sql = _edit(
            sql,
            "'evaluate_task_termination' , 'finish_capability_invocation' )",
            f"'evaluate_task_termination' , 'finish_capability_invocation', '{SETTLE}' )",
        )
    return sql


def upgrade() -> None:
    connection = op.get_bind()
    if int(connection.execute(sa.text("SHOW server_version_num")).scalar_one()) // 10000 != 18:
        raise RuntimeError("0083 requires PostgreSQL 18")
    if (
        connection.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one()
        != down_revision
    ):
        raise RuntimeError("0083 requires sole accepted 0082 parent")
    signatures = (
        "pr316_command_event(text)",
        "pr316_receipt_insert()",
        "pr316_node_proof(experiment_search_nodes)",
        "pr316_state(research_task_command_receipts,experiment_search_events)",
        "pr316_lineage_insert()",
        "pr316_validate_receipt(uuid)",
        "pr304_child_guard()",
        "pr304_validate_safety(uuid)",
        "pr301_receipt_complete()",
    )
    definitions = {
        signature: connection.execute(
            sa.text("SELECT pg_get_functiondef(CAST(:signature AS regprocedure))"),
            {"signature": signature},
        ).scalar_one()
        for signature in signatures
    }
    for column in COLUMNS:
        op.execute(f"ALTER TABLE budget_reservations ADD COLUMN {column} uuid NULL")
    for column, target, name in BINDINGS:
        op.execute(
            f"ALTER TABLE budget_reservations ADD CONSTRAINT {name} "
            f"FOREIGN KEY ({column}) REFERENCES {target}(id) ON DELETE RESTRICT"
        )
    op.execute(
        "ALTER TABLE budget_reservations ADD CONSTRAINT "
        "pr316d1_reservation_binding_shape_ck CHECK (num_nonnulls("
        + ",".join(COLUMNS)
        + ") IN (0,8))"
    )
    op.execute(
        "CREATE FUNCTION pr316d1_enabled() RETURNS boolean LANGUAGE sql STABLE "
        "SECURITY INVOKER SET search_path=pg_catalog,public,pg_temp AS 'SELECT false'"
    )
    for sql in (AUTHORITY, ADMISSION, VALIDATE):
        op.execute(sql)
    # Refuse deployment default privileges that would give new helpers extra grantees.
    if connection.execute(
        sa.text("""SELECT EXISTS(SELECT 1 FROM pg_proc p
        WHERE p.pronamespace='public'::regnamespace AND p.proname IN
        ('pr316d1_enabled','pr316d1_authority','pr316d1_admission','pr316d1_validate_receipt')
        AND (EXISTS(SELECT 1 FROM
        aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a
        WHERE a.grantee NOT IN (0,p.proowner) OR a.privilege_type<>'EXECUTE'
        OR (a.grantee=0 AND a.is_grantable))
        OR NOT EXISTS(SELECT 1 FROM
        aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a
        WHERE a.grantee=0 AND a.privilege_type='EXECUTE' AND NOT a.is_grantable)
        OR NOT EXISTS(SELECT 1 FROM
        aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a
        WHERE a.grantee=p.proowner AND a.privilege_type='EXECUTE')))""")
    ).scalar_one():
        raise RuntimeError("0083 unexpected helper default grants")

    for signature, original in definitions.items():
        op.execute(amend_function(signature, original))

    _extend_check(
        "research_task_command_receipts",
        "pr316_command_names",
        lambda old: f"({old}) OR command_name IN ({COMMANDS})",
    )
    _extend_check(
        "research_task_command_receipts",
        "research_task_command_receipts_material_version_check",
        lambda _: f"material_version=CASE WHEN command_name IN ({COMMANDS}) THEN 2 ELSE 1 END",
    )
    _extend_check(
        "research_task_command_receipts",
        "pr316_receipt_shape_ck",
        lambda old: f"({old}) OR (command_name='{ADMIT}' AND "
        "num_nonnulls(result_search_session_id,result_search_node_id,"
        "result_search_event_id)=3 AND resulting_row_version>=2)",
    )
    _extend_check(
        "research_task_events",
        "pr316_task_event_names",
        lambda old: f"({old}) OR event_type IN ({EVENTS})",
    )
    _extend_check(
        "research_task_events",
        "pr316_task_event_states",
        lambda old: f"({old}) OR (event_type='BEARING_EVALUATION_ADMITTED' AND prior_status "
        f"IN ('CREATED','PLANNING') AND new_status=prior_status) OR "
        f"(event_type='BEARING_EVALUATION_SETTLED' AND prior_status IN "
        f"('CREATED','PLANNING','CANCELLED') AND new_status=prior_status)",
    )
    _extend_check(
        "research_task_events",
        "pr316_task_event_reason",
        lambda old: f"(event_type NOT IN ({EVENTS}) AND ({old})) OR (event_type IN "
        f"({EVENTS}) AND reason IS NOT NULL AND pr316_reason(reason))",
    )
    _extend_check(
        "research_task_events",
        "pr303_event_stop_kind",
        lambda old: f"({old}) OR event_type IN ({EVENTS})",
    )


def downgrade() -> None:
    raise RuntimeError("0083 is forward-only; approved forward repair required")
