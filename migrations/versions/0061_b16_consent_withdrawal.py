"""B16 immutable alternating consent and atomic exact-manuscript grant staling."""

# ruff: noqa: E501
from alembic import op

revision = "0061_b16_consent_withdrawal"
down_revision = "0060_b15_package_preparation"
branch_labels = None
depends_on = None

UPGRADE_SQL = r"""
CREATE FUNCTION b16_preheld() RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$ BEGIN
 IF current_setting('transaction_isolation')<>'read committed' OR EXISTS(SELECT 1 FROM unnest(ARRAY['actor_subject_bindings','actors','artifact_versions','artifacts','audit_findings','authorship_snapshot_authors','authorship_snapshot_contributions','authorship_snapshot_corresponding_authors','authorship_snapshot_equal_groups','authorship_snapshots','claim_versions','claims','contribution_records','correction_records','dataset_snapshots','datasets','evidence_relations','experiment_spec_versions','experiment_specs','impact_assessments','impact_targets','internal_review_records','literature_evidence','literature_evidence_relations','literature_evidence_review_events','literature_source_project_links','literature_sources','literature_support_snapshots','manuscript_artifact_placements','manuscript_citation_placements','manuscript_claim_placements','manuscript_versions','measurements','metric_definition_versions','metric_definitions','project_membership_events','project_memberships','project_role_assignments','projects','review_issue_events','review_issues','run_artifact_inputs','run_dataset_inputs','runs','scientific_conclusion_claim_inputs','scientific_conclusion_literature_inputs','scientific_conclusion_versions','scientific_conclusions','source_versions','statistical_result_inputs','statistical_results']) n(name) WHERE NOT EXISTS(SELECT 1 FROM pg_locks l WHERE l.pid=pg_backend_pid() AND l.locktype='relation' AND l.relation=to_regclass('public.'||n.name) AND l.mode='ShareLock' AND l.granted)) THEN RAISE EXCEPTION 'B15 preheld inventory required' USING ERRCODE='P16G1'; END IF;
 IF NOT EXISTS(SELECT 1 FROM pg_locks WHERE pid=pg_backend_pid() AND locktype='relation'
 AND relation='public.publications'::regclass AND mode='ShareRowExclusiveLock' AND granted)
 OR EXISTS(SELECT 1 FROM unnest(ARRAY['approval_decisions','approval_request_reviews','approval_requests']) n(name)
 WHERE NOT EXISTS(SELECT 1 FROM pg_locks WHERE pid=pg_backend_pid() AND locktype='relation'
 AND relation=to_regclass('public.'||n.name) AND mode='ShareLock' AND granted)) THEN
 RAISE EXCEPTION 'B16 coordination required' USING ERRCODE='P16G1'; END IF;
 END $$;
CREATE OR REPLACE FUNCTION b09_preheld() RETURNS void LANGUAGE plpgsql
 SET search_path=pg_catalog, public, pg_temp AS $$
BEGIN
 IF current_setting('transaction_isolation') <> 'read committed' OR EXISTS (
   SELECT 1 FROM unnest(ARRAY['actor_subject_bindings','actors','artifact_versions','artifacts','audit_findings','claim_versions','claims','correction_records','dataset_snapshots','datasets','evidence_relations','experiment_spec_versions','experiment_specs','impact_assessments','impact_targets','internal_review_records','literature_evidence','literature_evidence_relations','literature_evidence_review_events','literature_source_project_links','literature_sources','literature_support_snapshots','manuscript_artifact_placements','manuscript_citation_placements','manuscript_claim_placements','manuscript_versions','measurements','metric_definition_versions','metric_definitions','project_membership_events','project_memberships','project_role_assignments','projects','publications','review_issue_events','review_issues','run_artifact_inputs','run_dataset_inputs','runs','scientific_conclusion_claim_inputs','scientific_conclusion_literature_inputs','scientific_conclusion_versions','scientific_conclusions','source_versions','statistical_result_inputs','statistical_results']) AS n(name)
   WHERE NOT EXISTS(SELECT 1 FROM pg_locks l WHERE l.pid=pg_backend_pid()
     AND l.locktype='relation' AND l.relation=to_regclass('public.'||n.name)
     AND (l.mode='ShareLock' OR (n.name='publications' AND l.mode='ShareRowExclusiveLock')) AND l.granted)) THEN
   RAISE EXCEPTION 'B09 requires preheld SHARE inventory at READ COMMITTED' USING ERRCODE='P16G1';
 END IF;
END $$;

ALTER TABLE author_consents DROP CONSTRAINT ck_b15_consent_root;
ALTER TABLE author_consents ADD CONSTRAINT ck_b16_consent_state CHECK(consent_state IN ('GRANTED','WITHDRAWN'));
ALTER TABLE author_consents ADD CONSTRAINT ck_b16_consent_scope CHECK(consent_scope='PREPARED_PACKAGE');
ALTER TABLE author_consents ADD CONSTRAINT ck_b16_consent_root CHECK(prior_consent_id IS NOT NULL OR consent_state='GRANTED');
ALTER TABLE author_consents ADD CONSTRAINT ck_b16_consent_not_self CHECK(prior_consent_id IS NULL OR prior_consent_id<>id);
CREATE FUNCTION b16_live_author(aid UUID) RETURNS boolean LANGUAGE SQL VOLATILE
 SET search_path=pg_catalog,public,pg_temp AS $$
 SELECT EXISTS(SELECT 1 FROM actors a JOIN actor_subject_bindings b ON b.actor_id=a.id
 WHERE a.id=aid AND a.actor_type='HUMAN' AND a.retired_at IS NULL AND b.status='ACTIVE'
 AND b.bound_at<=clock_timestamp() AND (b.revoked_at IS NULL OR clock_timestamp()<b.revoked_at))
$$;
CREATE FUNCTION b16_verify_chain(pid UUID, aid UUID) RETURNS void LANGUAGE plpgsql
 SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE c author_consents; prior author_consents; evidence artifact_versions;
 expected text; root_count bigint; row_count bigint; walked bigint:=0; cursor_id UUID;
BEGIN
 SELECT count(*),count(*) FILTER(WHERE prior_consent_id IS NULL) INTO row_count,root_count
 FROM author_consents WHERE prepared_submission_version_id=pid AND actor_id=aid;
 IF row_count=0 THEN RETURN; END IF;
 IF root_count<>1 THEN RAISE EXCEPTION 'one consent root required' USING ERRCODE='P17F2'; END IF;
 SELECT id INTO cursor_id FROM author_consents WHERE prepared_submission_version_id=pid AND actor_id=aid AND prior_consent_id IS NULL;
 WHILE cursor_id IS NOT NULL LOOP
  walked:=walked+1;
  IF walked>row_count THEN RAISE EXCEPTION 'consent cycle' USING ERRCODE='P17F2'; END IF;
  SELECT * INTO c FROM author_consents WHERE id=cursor_id;
  SELECT * INTO prior FROM author_consents WHERE id=c.prior_consent_id;
  SELECT * INTO evidence FROM artifact_versions WHERE id=c.evidence_artifact_version_id;
  IF c.consent_scope<>'PREPARED_PACKAGE' OR c.actor_id<>c.created_by OR c.created_at<>c.captured_at
   OR (c.prior_consent_id IS NULL AND c.consent_state<>'GRANTED')
   OR (c.prior_consent_id IS NOT NULL AND (prior.id IS NULL OR prior.prepared_submission_version_id<>pid
     OR prior.actor_id<>aid OR prior.consent_scope<>c.consent_scope OR prior.consent_state=c.consent_state))
   OR evidence.id IS NULL OR evidence.status NOT IN ('FROZEN','SUPERSEDED') OR evidence.frozen_at IS NULL
   OR NOT EXISTS(SELECT 1 FROM artifacts a JOIN prepared_submission_versions p ON p.id=pid
     JOIN publications pub ON pub.id=p.publication_id WHERE a.id=evidence.artifact_id AND a.project_id=pub.project_id)
  THEN RAISE EXCEPTION 'consent chain structure' USING ERRCODE='P17F2'; END IF;
  expected:=pr216_hash(jsonb_build_object('type','AuthorConsent','material_version',1,
   'prepared_submission',jsonb_build_object('type','PreparedSubmissionVersion','id',pid),
   'actor',jsonb_build_object('type','ActorIdentity','id',aid),'consent_state',c.consent_state,
   'consent_scope',c.consent_scope,'evidence_artifact',jsonb_build_object('type','ArtifactVersion','id',evidence.id,'content_hash',evidence.content_hash),
   'prior_consent',CASE WHEN prior.id IS NULL THEN 'null'::jsonb ELSE jsonb_build_object('type','AuthorConsent','id',prior.id,'content_hash',prior.content_hash) END));
  IF c.content_hash<>expected OR c.hash_scheme<>'sha256-cjson-v1' THEN
   RAISE EXCEPTION 'consent hash closure' USING ERRCODE='P17F2'; END IF;
  SELECT id INTO cursor_id FROM author_consents WHERE prior_consent_id=c.id;
 END LOOP;
 IF walked<>row_count THEN RAISE EXCEPTION 'disconnected consent chain' USING ERRCODE='P17F2'; END IF;
END $$;
CREATE OR REPLACE FUNCTION b15_consent_guard() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE p prepared_submission_versions; prior author_consents; pid UUID;
BEGIN
 PERFORM b16_preheld();
 SELECT * INTO p FROM prepared_submission_versions WHERE id=NEW.prepared_submission_version_id;
 PERFORM 1 FROM manuscript_versions WHERE id=p.manuscript_version_id FOR UPDATE;
 PERFORM 1 FROM publications WHERE id=p.publication_id FOR UPDATE;
 SELECT * INTO p FROM prepared_submission_versions WHERE id=NEW.prepared_submission_version_id FOR UPDATE;
 SELECT project_id INTO pid FROM publications WHERE id=p.publication_id;
 IF NEW.actor_id IS DISTINCT FROM NEW.created_by OR NOT b16_live_author(NEW.actor_id) THEN
 RAISE EXCEPTION 'direct live author required' USING ERRCODE='P16A1'; END IF;
 IF NOT EXISTS(SELECT 1 FROM authorship_snapshot_authors s WHERE s.authorship_snapshot_id=p.authorship_snapshot_id AND s.actor_id=NEW.actor_id)
 OR NOT EXISTS(SELECT 1 FROM artifact_versions v JOIN artifacts a ON a.id=v.artifact_id WHERE v.id=NEW.evidence_artifact_version_id
 AND a.project_id=pid AND v.status IN ('FROZEN','SUPERSEDED') AND v.frozen_at IS NOT NULL AND v.content_hash ~ '^[0-9a-f]{64}$') THEN
 RAISE EXCEPTION 'consent context closure' USING ERRCODE='P17F2'; END IF;
 IF NEW.prior_consent_id IS NOT NULL THEN
  SELECT * INTO prior FROM author_consents WHERE id=NEW.prior_consent_id;
  IF prior.id IS NULL OR prior.prepared_submission_version_id<>p.id OR prior.actor_id<>NEW.actor_id OR prior.consent_scope<>NEW.consent_scope THEN
   RAISE EXCEPTION 'same consent chain required' USING ERRCODE='P17F2'; END IF;
  IF EXISTS(SELECT 1 FROM author_consents WHERE prior_consent_id=prior.id) THEN
   RAISE EXCEPTION 'old consent head' USING ERRCODE='23505',CONSTRAINT='uq_author_consents_successor'; END IF;
  IF prior.consent_state=NEW.consent_state THEN RAISE EXCEPTION 'alternating state required' USING ERRCODE='P15S2'; END IF;
 END IF;
 IF (NEW.consent_state='GRANTED' AND p.status<>'PREPARED') OR (NEW.consent_state='WITHDRAWN' AND NEW.prior_consent_id IS NULL) THEN
 RAISE EXCEPTION 'consent state disallowed' USING ERRCODE='P15S2'; END IF;
 IF NEW.consent_state='GRANTED' AND NOT b13_authorized(NEW.actor_id,pid,ARRAY['OWNER','RESEARCHER','VIEWER','REVIEWER','APPROVER']) THEN
 RAISE EXCEPTION 'current project reader required' USING ERRCODE='P16A1'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION b16_consent_chain() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,public,pg_temp AS $$ BEGIN
 PERFORM b16_verify_chain(NEW.prepared_submission_version_id,NEW.actor_id);
 IF NOT b16_live_author(NEW.actor_id) THEN RAISE EXCEPTION 'final live author required' USING ERRCODE='P16A1'; END IF;
 RETURN NULL; END $$;
CREATE CONSTRAINT TRIGGER b16_consent_chain AFTER INSERT ON author_consents
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b16_consent_chain();
CREATE FUNCTION b16_consent_cause(e approval_grant_events) RETURNS boolean LANGUAGE plpgsql
 SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE c author_consents; gid UUID;
BEGIN
 IF e.reason !~ '^author consent withdrawn:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
 OR e.prior_status IS DISTINCT FROM 'ACTIVE' OR e.new_status IS DISTINCT FROM 'STALE' THEN RETURN false; END IF;
 SELECT * INTO c FROM author_consents WHERE id=substring(e.reason FROM 26)::uuid AND consent_state='WITHDRAWN' AND xmin=pg_current_xact_id()::xid;
 IF c.id IS NULL OR c.actor_id<>e.actor_id OR c.captured_at<>e.occurred_at
 OR EXISTS(SELECT 1 FROM approval_grant_consumptions WHERE grant_id=e.grant_id) THEN RETURN false; END IF;
 SELECT g.id INTO gid FROM prepared_submission_versions p JOIN publications pub ON pub.id=p.publication_id
 JOIN approval_requests r ON r.manuscript_version_id=p.manuscript_version_id AND r.project_id=pub.project_id AND r.approval_purpose='PREPARE_SUBMISSION'
 JOIN approval_decisions d ON d.approval_request_id=r.id JOIN approval_grants g ON g.approval_decision_id=d.id
 WHERE p.id=c.prepared_submission_version_id AND g.id=e.grant_id AND g.project_id=pub.project_id AND g.purpose='PREPARE_SUBMISSION';
 IF gid IS NULL THEN RETURN false; END IF;
 PERFORM b16_preheld(); PERFORM b16_verify_chain(c.prepared_submission_version_id,c.actor_id);
 IF NOT b16_live_author(c.actor_id) THEN RAISE EXCEPTION 'live withdrawal author required' USING ERRCODE='P16A1'; END IF;
 RETURN true;
END $$;
CREATE FUNCTION b16_withdrawal_staling() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE c author_consents; g approval_grants; e approval_grant_events;
BEGIN
 FOR c IN SELECT * FROM author_consents WHERE consent_state='WITHDRAWN' AND xmin=pg_current_xact_id()::xid LOOP
  PERFORM b16_verify_chain(c.prepared_submission_version_id,c.actor_id);
  FOR g IN SELECT ag.* FROM prepared_submission_versions p JOIN publications pub ON pub.id=p.publication_id
   JOIN approval_requests r ON r.manuscript_version_id=p.manuscript_version_id AND r.project_id=pub.project_id AND r.approval_purpose='PREPARE_SUBMISSION'
   JOIN approval_decisions d ON d.approval_request_id=r.id JOIN approval_grants ag ON ag.approval_decision_id=d.id
   WHERE p.id=c.prepared_submission_version_id AND ag.project_id=pub.project_id AND ag.purpose='PREPARE_SUBMISSION' LOOP
   IF g.status='ACTIVE' THEN RAISE EXCEPTION 'withdrawal ACTIVE remainder' USING ERRCODE='P17F2'; END IF;
   IF g.status='STALE' AND EXISTS(SELECT 1 FROM approval_grants WHERE id=g.id AND xmin=pg_current_xact_id()::xid) THEN
    SELECT * INTO e FROM approval_grant_events WHERE grant_id=g.id AND prior_status='ACTIVE';
    IF e.id IS NULL OR NOT b16_consent_cause(e) OR e.reason<>'author consent withdrawn:'||c.id::text
     OR NOT EXISTS(SELECT 1 FROM approval_grant_events WHERE id=e.id AND xmin=pg_current_xact_id()::xid) THEN
     RAISE EXCEPTION 'withdrawal terminal event mismatch' USING ERRCODE='P17F2'; END IF;
   END IF;
  END LOOP;
 END LOOP;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER b16_withdrawal_staling_consent AFTER INSERT ON author_consents DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b16_withdrawal_staling();
CREATE CONSTRAINT TRIGGER b16_withdrawal_staling_grant AFTER INSERT OR UPDATE ON approval_grants DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b16_withdrawal_staling();
CREATE CONSTRAINT TRIGGER b16_withdrawal_staling_event AFTER INSERT ON approval_grant_events DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b16_withdrawal_staling();
CREATE FUNCTION b16_prepare_grant_guard() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE scope_key bigint;
BEGIN
 IF NEW.purpose='PREPARE_SUBMISSION' THEN
  IF NOT EXISTS(SELECT 1 FROM pg_locks WHERE pid=pg_backend_pid() AND locktype='relation' AND relation='public.publications'::regclass AND mode='ShareRowExclusiveLock' AND granted) THEN
   RAISE EXCEPTION 'preheld prepare issuance coordination required' USING ERRCODE='P16G1'; END IF;
  PERFORM b09_preheld();
  scope_key:=hashtextextended('pr216:scope:'||NEW.project_id::text||':'||'PREPARE_SUBMISSION',0);
  IF NOT EXISTS(SELECT 1 FROM pg_locks WHERE pid=pg_backend_pid() AND locktype='advisory'
    AND classid=((scope_key>>32)&4294967295)::oid AND objid=(scope_key&4294967295)::oid
    AND objsubid=1 AND mode='ExclusiveLock' AND granted) THEN
    RAISE EXCEPTION 'preheld prepare scope required' USING ERRCODE='P16G1'; END IF;
  IF NOT EXISTS(SELECT 1 FROM approval_decisions d JOIN approval_requests r ON r.id=d.approval_request_id
   JOIN manuscript_versions m ON m.id=r.manuscript_version_id JOIN publications p ON p.id=m.publication_id
   WHERE d.id=NEW.approval_decision_id AND r.project_id=NEW.project_id AND p.project_id=r.project_id
    AND r.approval_purpose='PREPARE_SUBMISSION' AND m.status='FROZEN' AND m.content_hash=r.target_content_hash
    AND d.decision IN ('APPROVE','APPROVE_WITH_CONDITIONS')) THEN
   RAISE EXCEPTION 'exact prepare issuance closure required' USING ERRCODE='P16G1'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER b16_prepare_grant_guard BEFORE INSERT ON approval_grants FOR EACH ROW EXECUTE FUNCTION b16_prepare_grant_guard();

CREATE OR REPLACE FUNCTION b13_validate_event(e approval_grant_events) RETURNS approval_grant_events LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE g approval_grants; d approval_decisions; r approval_requests; c approval_grant_consumptions; automatic boolean;
BEGIN
 SELECT * INTO g FROM approval_grants WHERE id=e.grant_id;
 SELECT * INTO d FROM approval_decisions WHERE id=g.approval_decision_id;
 SELECT * INTO r FROM approval_requests WHERE id=d.approval_request_id;
 IF e.occurred_at IS NULL OR NOT isfinite(e.occurred_at) OR e.occurred_at<d.decided_at OR e.occurred_at>clock_timestamp()
 OR EXISTS(SELECT 1 FROM approval_grant_events WHERE grant_id=e.grant_id AND new_status=e.new_status) THEN
 RAISE EXCEPTION 'invalid event history' USING ERRCODE='P17F1'; END IF;
 IF e.prior_status IS NULL THEN
  IF pg_trigger_depth()<2 OR g.status<>'ACTIVE' OR e.new_status<>'ACTIVE' OR e.actor_id<>d.decided_by
  OR e.reason<>'grant created' OR NOT EXISTS(SELECT 1 FROM approval_grants WHERE id=g.id AND xmin=pg_current_xact_id()::xid) THEN
  RAISE EXCEPTION 'invalid creation event' USING ERRCODE='P17F1'; END IF;
  RETURN e;
 END IF;
 automatic := g.status='STALE' AND e.new_status='STALE' AND pg_trigger_depth()>=2
 AND e.actor_id=d.decided_by AND e.reason='grant stale'
 AND EXISTS(SELECT 1 FROM approval_grants WHERE id=g.id AND xmin=pg_current_xact_id()::xid)
 AND (NOT pr216_approver_active(d.decided_by,g.project_id) OR EXISTS(
 SELECT 1 FROM approval_requests q WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose
 AND coalesce(q.scientific_conclusion_version_id,q.manuscript_version_id)<>coalesce(r.scientific_conclusion_version_id,r.manuscript_version_id)
 AND q.xmin=pg_current_xact_id()::xid) OR EXISTS(SELECT 1 FROM approval_decisions x JOIN approval_requests q ON q.id=x.approval_request_id
 WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose AND x.decision='REJECT' AND x.xmin=pg_current_xact_id()::xid));
 IF automatic AND e.prior_status='ACTIVE' THEN RETURN e; END IF;
 IF b16_consent_cause(e) THEN RETURN e; END IF;
 IF g.status<>'ACTIVE' OR e.prior_status<>'ACTIVE' OR e.new_status NOT IN ('CONSUMED','EXPIRED','STALE','REVOKED')
 OR length(e.reason) NOT BETWEEN 1 AND 16384 OR e.reason<>normalize(e.reason,NFC) THEN
 RAISE EXCEPTION 'one-way terminal event required' USING ERRCODE='P17F1'; END IF;
 PERFORM b13_preheld(e.new_status='CONSUMED');
 IF e.new_status='CONSUMED' THEN
  SELECT * INTO c FROM approval_grant_consumptions WHERE grant_id=g.id AND xmin=pg_current_xact_id()::xid;
  e.occurred_at:=c.consumed_at;
  IF NOT b13_authorized(e.actor_id,g.project_id,ARRAY['OWNER','RESEARCHER']) THEN
   RAISE EXCEPTION 'live consumption writer required' USING ERRCODE='P16A1'; END IF;
  IF c.id IS NULL OR c.actor_id<>e.actor_id OR clock_timestamp()>=g.valid_until THEN
  RAISE EXCEPTION 'atomic consumption required' USING ERRCODE='P13G1'; END IF;
  PERFORM b13_verify_receipt(c);
  PERFORM b13_release_gate(r,d.decided_by);
 ELSE
  e.occurred_at:=clock_timestamp();
  IF NOT b13_authorized(e.actor_id,g.project_id,ARRAY['OWNER']) THEN
  RAISE EXCEPTION 'live owner required' USING ERRCODE='P16A1'; END IF;
  IF (e.new_status='EXPIRED' AND clock_timestamp()<g.valid_until)
  OR (e.new_status IN ('STALE','REVOKED') AND clock_timestamp()>=g.valid_until) THEN
  RAISE EXCEPTION 'expiry precedence' USING ERRCODE='P13G1'; END IF;
  IF e.new_status='STALE' AND NOT b13_stale(g) OR e.new_status='REVOKED' AND b13_stale(g) THEN
  RAISE EXCEPTION 'verified terminal cause required' USING ERRCODE='P16G1'; END IF;
 END IF;
 RETURN e;
END $$;
CREATE OR REPLACE FUNCTION b13_complete() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE gid UUID; g approval_grants; c approval_grant_consumptions; e approval_grant_events;
BEGIN
 IF TG_TABLE_NAME='approval_grants' THEN gid:=NEW.id; ELSE gid:=NEW.grant_id; END IF;
 SELECT * INTO g FROM approval_grants WHERE id=gid;
 SELECT * INTO c FROM approval_grant_consumptions WHERE grant_id=gid;
 SELECT * INTO e FROM approval_grant_events WHERE grant_id=gid AND prior_status='ACTIVE';
 IF (g.status='CONSUMED') IS DISTINCT FROM (c.id IS NOT NULL)
 OR (g.status<>'ACTIVE') IS DISTINCT FROM (e.id IS NOT NULL)
 OR (e.id IS NOT NULL AND e.new_status<>g.status) THEN
 RAISE EXCEPTION 'complete terminal graph required' USING ERRCODE='P17F2'; END IF;
 IF c.id IS NOT NULL THEN
  PERFORM b13_verify_receipt(c,true);
  IF e.actor_id<>c.actor_id OR e.occurred_at<>c.consumed_at THEN
  RAISE EXCEPTION 'receipt event mismatch' USING ERRCODE='P17F2'; END IF;
 END IF;
 -- Only newly consumed history rechecks live admission. Historical terminals are immutable.
 IF c.id IS NOT NULL AND EXISTS(SELECT 1 FROM approval_grant_consumptions WHERE id=c.id AND xmin=pg_current_xact_id()::xid) THEN
  IF clock_timestamp()>=g.valid_until THEN RAISE EXCEPTION 'final expiry' USING ERRCODE='P13G1'; END IF;
  IF NOT b13_authorized(c.actor_id,g.project_id,ARRAY['OWNER','RESEARCHER']) THEN
   RAISE EXCEPTION 'final writer authority required' USING ERRCODE='P16A1'; END IF;
  PERFORM b13_release_gate(r,d.decided_by) FROM approval_decisions d JOIN approval_requests r ON r.id=d.approval_request_id WHERE d.id=g.approval_decision_id;
  IF clock_timestamp()>=g.valid_until THEN RAISE EXCEPTION 'grant expired during final admission' USING ERRCODE='P13G1'; END IF;
  IF NOT b13_authorized(c.actor_id,g.project_id,ARRAY['OWNER','RESEARCHER']) THEN
   RAISE EXCEPTION 'writer expired during final admission' USING ERRCODE='P16A1'; END IF;
 END IF;

 IF e.id IS NOT NULL AND c.id IS NULL AND EXISTS(SELECT 1 FROM approval_grant_events
   WHERE id=e.id AND xmin=pg_current_xact_id()::xid)
 AND EXISTS(SELECT 1 FROM pg_locks WHERE pid=pg_backend_pid() AND locktype='relation'
   AND relation='public.publications'::regclass AND mode='ShareRowExclusiveLock' AND granted) THEN
   IF b16_consent_cause(e) THEN RETURN NULL; END IF;
   -- B09 decisions now prehold Publication SRE too. Preserve their proved,
   -- trigger-created rejection/target-change events; these are not OWNER commands.
   IF e.new_status='STALE' AND e.reason='grant stale'
    AND EXISTS(SELECT 1 FROM approval_grants WHERE id=g.id AND xmin=pg_current_xact_id()::xid)
    AND EXISTS(SELECT 1 FROM approval_decisions d JOIN approval_requests r ON r.id=d.approval_request_id
      WHERE d.id=g.approval_decision_id AND e.actor_id=d.decided_by AND (
       EXISTS(SELECT 1 FROM approval_requests q WHERE q.project_id=r.project_id
        AND q.approval_purpose=r.approval_purpose
        AND coalesce(q.scientific_conclusion_version_id,q.manuscript_version_id)<>coalesce(r.scientific_conclusion_version_id,r.manuscript_version_id)
        AND q.xmin=pg_current_xact_id()::xid)
       OR EXISTS(SELECT 1 FROM approval_decisions x JOIN approval_requests q ON q.id=x.approval_request_id
        WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose
        AND x.decision='REJECT' AND x.xmin=pg_current_xact_id()::xid))) THEN RETURN NULL; END IF;
   PERFORM b13_preheld(false);
   IF NOT b13_authorized(e.actor_id,g.project_id,ARRAY['OWNER']) THEN
    RAISE EXCEPTION 'final owner authority required' USING ERRCODE='P16A1'; END IF;
   IF (e.new_status='EXPIRED' AND (clock_timestamp()<g.valid_until OR e.occurred_at<g.valid_until))
   OR (e.new_status IN ('STALE','REVOKED') AND clock_timestamp()>=g.valid_until) THEN
    RAISE EXCEPTION 'final expiry precedence' USING ERRCODE='P13G1'; END IF;
   IF (e.new_status='STALE' AND NOT b13_stale(g)) OR (e.new_status='REVOKED' AND b13_stale(g)) THEN
    RAISE EXCEPTION 'final stale precedence' USING ERRCODE='P16G1'; END IF;
 END IF;
 RETURN NULL;
END $$;
"""

RESTORE_SQL = r"""
CREATE OR REPLACE FUNCTION b15_consent_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p prepared_submission_versions; pid UUID;
BEGIN
 PERFORM b15_preheld();
 SELECT * INTO p FROM prepared_submission_versions WHERE id=NEW.prepared_submission_version_id FOR UPDATE;
 IF p.status IS DISTINCT FROM 'PREPARED' OR NEW.consent_state<>'GRANTED' OR NEW.consent_scope<>'PREPARED_PACKAGE' OR NEW.prior_consent_id IS NOT NULL THEN
 RAISE EXCEPTION 'closed root consent state' USING ERRCODE='P15S2'; END IF;
 SELECT project_id INTO pid FROM publications WHERE id=p.publication_id;
 IF NEW.actor_id IS DISTINCT FROM NEW.created_by OR NOT EXISTS(SELECT 1 FROM authorship_snapshot_authors s JOIN actors a ON a.id=s.actor_id WHERE s.authorship_snapshot_id=p.authorship_snapshot_id AND a.id=NEW.actor_id AND a.actor_type='HUMAN' AND a.retired_at IS NULL)
 OR NOT EXISTS(SELECT 1 FROM artifact_versions v JOIN artifacts a ON a.id=v.artifact_id WHERE v.id=NEW.evidence_artifact_version_id AND a.project_id=pid AND v.status IN ('FROZEN','SUPERSEDED') AND v.frozen_at IS NOT NULL AND v.content_hash ~ '^[0-9a-f]{64}$') THEN
 RAISE EXCEPTION 'root consent provenance' USING ERRCODE='P15S3'; END IF;
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION b09_preheld() RETURNS void LANGUAGE plpgsql
 SET search_path=pg_catalog, public, pg_temp AS $$
BEGIN
 IF current_setting('transaction_isolation') <> 'read committed' OR EXISTS (
   SELECT 1 FROM unnest(ARRAY['actor_subject_bindings','actors','artifact_versions','artifacts','audit_findings','claim_versions','claims','correction_records','dataset_snapshots','datasets','evidence_relations','experiment_spec_versions','experiment_specs','impact_assessments','impact_targets','internal_review_records','literature_evidence','literature_evidence_relations','literature_evidence_review_events','literature_source_project_links','literature_sources','literature_support_snapshots','manuscript_artifact_placements','manuscript_citation_placements','manuscript_claim_placements','manuscript_versions','measurements','metric_definition_versions','metric_definitions','project_membership_events','project_memberships','project_role_assignments','projects','publications','review_issue_events','review_issues','run_artifact_inputs','run_dataset_inputs','runs','scientific_conclusion_claim_inputs','scientific_conclusion_literature_inputs','scientific_conclusion_versions','scientific_conclusions','source_versions','statistical_result_inputs','statistical_results']) AS n(name)
   WHERE NOT EXISTS(SELECT 1 FROM pg_locks l WHERE l.pid=pg_backend_pid()
     AND l.locktype='relation' AND l.relation=to_regclass('public.'||n.name)
     AND l.mode='ShareLock' AND l.granted)) THEN
   RAISE EXCEPTION 'B09 requires preheld SHARE inventory at READ COMMITTED' USING ERRCODE='P16G1';
 END IF;
END $$;
CREATE OR REPLACE FUNCTION b13_validate_event(e approval_grant_events) RETURNS approval_grant_events LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE g approval_grants; d approval_decisions; r approval_requests; c approval_grant_consumptions; automatic boolean;
BEGIN
 SELECT * INTO g FROM approval_grants WHERE id=e.grant_id;
 SELECT * INTO d FROM approval_decisions WHERE id=g.approval_decision_id;
 SELECT * INTO r FROM approval_requests WHERE id=d.approval_request_id;
 IF e.occurred_at IS NULL OR NOT isfinite(e.occurred_at) OR e.occurred_at<d.decided_at OR e.occurred_at>clock_timestamp()
 OR EXISTS(SELECT 1 FROM approval_grant_events WHERE grant_id=e.grant_id AND new_status=e.new_status) THEN
 RAISE EXCEPTION 'invalid event history' USING ERRCODE='P17F1'; END IF;
 IF e.prior_status IS NULL THEN
  IF pg_trigger_depth()<2 OR g.status<>'ACTIVE' OR e.new_status<>'ACTIVE' OR e.actor_id<>d.decided_by
  OR e.reason<>'grant created' OR NOT EXISTS(SELECT 1 FROM approval_grants WHERE id=g.id AND xmin=pg_current_xact_id()::xid) THEN
  RAISE EXCEPTION 'invalid creation event' USING ERRCODE='P17F1'; END IF;
  RETURN e;
 END IF;
 automatic := g.status='STALE' AND e.new_status='STALE' AND pg_trigger_depth()>=2
 AND e.actor_id=d.decided_by AND e.reason='grant stale'
 AND EXISTS(SELECT 1 FROM approval_grants WHERE id=g.id AND xmin=pg_current_xact_id()::xid)
 AND (NOT pr216_approver_active(d.decided_by,g.project_id) OR EXISTS(
 SELECT 1 FROM approval_requests q WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose
 AND coalesce(q.scientific_conclusion_version_id,q.manuscript_version_id)<>coalesce(r.scientific_conclusion_version_id,r.manuscript_version_id)
 AND q.xmin=pg_current_xact_id()::xid) OR EXISTS(SELECT 1 FROM approval_decisions x JOIN approval_requests q ON q.id=x.approval_request_id
 WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose AND x.decision='REJECT' AND x.xmin=pg_current_xact_id()::xid));
 IF automatic AND e.prior_status='ACTIVE' THEN RETURN e; END IF;
 IF g.status<>'ACTIVE' OR e.prior_status<>'ACTIVE' OR e.new_status NOT IN ('CONSUMED','EXPIRED','STALE','REVOKED')
 OR length(e.reason) NOT BETWEEN 1 AND 16384 OR e.reason<>normalize(e.reason,NFC) THEN
 RAISE EXCEPTION 'one-way terminal event required' USING ERRCODE='P17F1'; END IF;
 PERFORM b13_preheld(e.new_status='CONSUMED');
 IF e.new_status='CONSUMED' THEN
  SELECT * INTO c FROM approval_grant_consumptions WHERE grant_id=g.id AND xmin=pg_current_xact_id()::xid;
  e.occurred_at:=c.consumed_at;
  IF NOT b13_authorized(e.actor_id,g.project_id,ARRAY['OWNER','RESEARCHER']) THEN
   RAISE EXCEPTION 'live consumption writer required' USING ERRCODE='P16A1'; END IF;
  IF c.id IS NULL OR c.actor_id<>e.actor_id OR clock_timestamp()>=g.valid_until THEN
  RAISE EXCEPTION 'atomic consumption required' USING ERRCODE='P13G1'; END IF;
  PERFORM b13_verify_receipt(c);
  PERFORM b13_release_gate(r,d.decided_by);
 ELSE
  e.occurred_at:=clock_timestamp();
  IF NOT b13_authorized(e.actor_id,g.project_id,ARRAY['OWNER']) THEN
  RAISE EXCEPTION 'live owner required' USING ERRCODE='P16A1'; END IF;
  IF (e.new_status='EXPIRED' AND clock_timestamp()<g.valid_until)
  OR (e.new_status IN ('STALE','REVOKED') AND clock_timestamp()>=g.valid_until) THEN
  RAISE EXCEPTION 'expiry precedence' USING ERRCODE='P13G1'; END IF;
  IF e.new_status='STALE' AND NOT b13_stale(g) OR e.new_status='REVOKED' AND b13_stale(g) THEN
  RAISE EXCEPTION 'verified terminal cause required' USING ERRCODE='P16G1'; END IF;
 END IF;
 RETURN e;
END $$;
CREATE OR REPLACE FUNCTION b13_complete() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE gid UUID; g approval_grants; c approval_grant_consumptions; e approval_grant_events;
BEGIN
 IF TG_TABLE_NAME='approval_grants' THEN gid:=NEW.id; ELSE gid:=NEW.grant_id; END IF;
 SELECT * INTO g FROM approval_grants WHERE id=gid;
 SELECT * INTO c FROM approval_grant_consumptions WHERE grant_id=gid;
 SELECT * INTO e FROM approval_grant_events WHERE grant_id=gid AND prior_status='ACTIVE';
 IF (g.status='CONSUMED') IS DISTINCT FROM (c.id IS NOT NULL)
 OR (g.status<>'ACTIVE') IS DISTINCT FROM (e.id IS NOT NULL)
 OR (e.id IS NOT NULL AND e.new_status<>g.status) THEN
 RAISE EXCEPTION 'complete terminal graph required' USING ERRCODE='P17F2'; END IF;
 IF c.id IS NOT NULL THEN
  PERFORM b13_verify_receipt(c,true);
  IF e.actor_id<>c.actor_id OR e.occurred_at<>c.consumed_at THEN
  RAISE EXCEPTION 'receipt event mismatch' USING ERRCODE='P17F2'; END IF;
 END IF;
 -- Only newly consumed history rechecks live admission. Historical terminals are immutable.
 IF c.id IS NOT NULL AND EXISTS(SELECT 1 FROM approval_grant_consumptions WHERE id=c.id AND xmin=pg_current_xact_id()::xid) THEN
  IF clock_timestamp()>=g.valid_until THEN RAISE EXCEPTION 'final expiry' USING ERRCODE='P13G1'; END IF;
  IF NOT b13_authorized(c.actor_id,g.project_id,ARRAY['OWNER','RESEARCHER']) THEN
   RAISE EXCEPTION 'final writer authority required' USING ERRCODE='P16A1'; END IF;
  PERFORM b13_release_gate(r,d.decided_by) FROM approval_decisions d JOIN approval_requests r ON r.id=d.approval_request_id WHERE d.id=g.approval_decision_id;
  IF clock_timestamp()>=g.valid_until THEN RAISE EXCEPTION 'grant expired during final admission' USING ERRCODE='P13G1'; END IF;
  IF NOT b13_authorized(c.actor_id,g.project_id,ARRAY['OWNER','RESEARCHER']) THEN
   RAISE EXCEPTION 'writer expired during final admission' USING ERRCODE='P16A1'; END IF;
 END IF;

 IF e.id IS NOT NULL AND c.id IS NULL AND EXISTS(SELECT 1 FROM approval_grant_events
   WHERE id=e.id AND xmin=pg_current_xact_id()::xid)
 AND EXISTS(SELECT 1 FROM pg_locks WHERE pid=pg_backend_pid() AND locktype='relation'
   AND relation='public.publications'::regclass AND mode='ShareRowExclusiveLock' AND granted) THEN
   PERFORM b13_preheld(false);
   IF NOT b13_authorized(e.actor_id,g.project_id,ARRAY['OWNER']) THEN
    RAISE EXCEPTION 'final owner authority required' USING ERRCODE='P16A1'; END IF;
   IF (e.new_status='EXPIRED' AND (clock_timestamp()<g.valid_until OR e.occurred_at<g.valid_until))
   OR (e.new_status IN ('STALE','REVOKED') AND clock_timestamp()>=g.valid_until) THEN
    RAISE EXCEPTION 'final expiry precedence' USING ERRCODE='P13G1'; END IF;
   IF (e.new_status='STALE' AND NOT b13_stale(g)) OR (e.new_status='REVOKED' AND b13_stale(g)) THEN
    RAISE EXCEPTION 'final stale precedence' USING ERRCODE='P16G1'; END IF;
 END IF;
 RETURN NULL;
END $$;
"""


def upgrade():
    op.execute(UPGRADE_SQL)


def downgrade():
    op.execute(
        "LOCK TABLE author_consents,approval_grants,approval_grant_events IN ACCESS EXCLUSIVE MODE"
    )
    op.execute("""DO $$ BEGIN IF EXISTS(SELECT 1 FROM author_consents WHERE prior_consent_id IS NOT NULL)
        OR EXISTS(SELECT 1 FROM approval_grant_events WHERE reason LIKE 'author consent withdrawn:%') THEN
        RAISE EXCEPTION 'retained B16 history prevents downgrade'; END IF; END $$""")
    for table, trigger in (
        ("author_consents", "b16_consent_chain"),
        ("author_consents", "b16_withdrawal_staling_consent"),
        ("approval_grants", "b16_withdrawal_staling_grant"),
        ("approval_grant_events", "b16_withdrawal_staling_event"),
        ("approval_grants", "b16_prepare_grant_guard"),
    ):
        op.execute(f"DROP TRIGGER {trigger} ON {table}")
    op.execute(RESTORE_SQL)
    for signature in (
        "b16_prepare_grant_guard()",
        "b16_withdrawal_staling()",
        "b16_consent_cause(approval_grant_events)",
        "b16_consent_chain()",
        "b16_verify_chain(UUID,UUID)",
        "b16_live_author(UUID)",
        "b16_preheld()",
    ):
        op.execute(f"DROP FUNCTION {signature}")
    for name in ("state", "scope", "root", "not_self"):
        op.execute(f"ALTER TABLE author_consents DROP CONSTRAINT ck_b16_consent_{name}")
    op.execute(
        "ALTER TABLE author_consents ADD CONSTRAINT ck_b15_consent_root CHECK(consent_state='GRANTED' AND consent_scope='PREPARED_PACKAGE' AND prior_consent_id IS NULL)"
    )
