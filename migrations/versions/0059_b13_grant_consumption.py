"""B13 one-use release receipts and explicit terminal grant maintenance.

READY/package bindings remain disabled until B14 supplies their concrete owners.
Frozen predecessor functions below support an empty-slice downgrade.
"""

# ruff: noqa: E501
from alembic import op

revision = "0059_b13_grant_consumption"
down_revision = "0058_b12_prepare_submission"
branch_labels = None
depends_on = None

B13_SNAPSHOT_TABLES = (
    "actor_subject_bindings",
    "actors",
    "artifact_versions",
    "artifacts",
    "audit_findings",
    "claim_versions",
    "claims",
    "correction_records",
    "dataset_snapshots",
    "datasets",
    "evidence_relations",
    "experiment_spec_versions",
    "experiment_specs",
    "impact_assessments",
    "impact_targets",
    "internal_review_records",
    "literature_evidence",
    "literature_evidence_relations",
    "literature_evidence_review_events",
    "literature_source_project_links",
    "literature_sources",
    "literature_support_snapshots",
    "manuscript_artifact_placements",
    "manuscript_citation_placements",
    "manuscript_claim_placements",
    "manuscript_versions",
    "measurements",
    "metric_definition_versions",
    "metric_definitions",
    "project_membership_events",
    "project_memberships",
    "project_role_assignments",
    "projects",
    "review_issue_events",
    "review_issues",
    "run_artifact_inputs",
    "run_dataset_inputs",
    "runs",
    "scientific_conclusion_claim_inputs",
    "scientific_conclusion_literature_inputs",
    "scientific_conclusion_versions",
    "scientific_conclusions",
    "source_versions",
    "statistical_result_inputs",
    "statistical_results",
)

UPGRADE_SQL = r"""
LOCK TABLE approval_grants,approval_grant_events IN ACCESS EXCLUSIVE MODE;
CREATE TABLE approval_grant_consumptions (
 id UUID CONSTRAINT pk_b13_consumptions PRIMARY KEY,
 grant_id UUID NOT NULL CONSTRAINT uq_b13_consumption_grant UNIQUE CONSTRAINT fk_b13_consumption_grant REFERENCES approval_grants(id) ON DELETE RESTRICT,
 command_key UUID NOT NULL CONSTRAINT uq_b13_command_key UNIQUE,
 project_id UUID NOT NULL CONSTRAINT fk_b13_consumption_project REFERENCES projects(id) ON DELETE RESTRICT,
 actor_id UUID NOT NULL CONSTRAINT fk_b13_consumption_actor REFERENCES actors(id) ON DELETE RESTRICT,
 consumed_at TIMESTAMPTZ NOT NULL, command VARCHAR(40) NOT NULL,
 request_hash CHAR(64) NOT NULL, hash_scheme VARCHAR(32) NOT NULL,
 result_dto_version SMALLINT NOT NULL, result_dto JSONB NOT NULL,
 result_publication_id UUID CONSTRAINT fk_b13_result_publication REFERENCES publications(id) ON DELETE RESTRICT,
 result_prepared_submission_version_id UUID,
 result_scientific_conclusion_version_id UUID CONSTRAINT fk_b13_result_conclusion REFERENCES scientific_conclusion_versions(id) ON DELETE RESTRICT,
 CONSTRAINT ck_b13_hash CHECK(request_hash ~ '^[0-9a-f]{64}$' AND hash_scheme='sha256-cjson-v1'),
 CONSTRAINT ck_b13_time CHECK(isfinite(consumed_at)),
 CONSTRAINT ck_b13_dto CHECK(result_dto_version=1 AND jsonb_typeof(result_dto)='object'),
 -- No unbound package locator may be stored. B14 replaces this closed release-only gate with concrete FKs/guards.
 CONSTRAINT ck_b13_result_tuple CHECK(command='RECORD_INTERNAL_SCIENTIFIC_RELEASE' AND result_scientific_conclusion_version_id IS NOT NULL AND result_publication_id IS NULL AND result_prepared_submission_version_id IS NULL)
);
CREATE INDEX ix_b13_consumption_project ON approval_grant_consumptions(project_id,consumed_at,id);
CREATE INDEX ix_b13_consumption_actor ON approval_grant_consumptions(actor_id);
CREATE INDEX ix_b13_result_publication ON approval_grant_consumptions(result_publication_id) WHERE result_publication_id IS NOT NULL;
CREATE INDEX ix_b13_result_conclusion ON approval_grant_consumptions(result_scientific_conclusion_version_id) WHERE result_scientific_conclusion_version_id IS NOT NULL;
DO $$ DECLARE c text; BEGIN
 SELECT conname INTO STRICT c FROM pg_constraint WHERE conrelid='approval_grant_events'::regclass AND contype='c' AND pg_get_constraintdef(oid) LIKE '%new_status%';
 EXECUTE format('ALTER TABLE approval_grant_events DROP CONSTRAINT %I',c);
END $$;
ALTER TABLE approval_grant_events ADD CONSTRAINT ck_b13_grant_event_status CHECK(
 (prior_status IS NULL AND new_status='ACTIVE') OR (prior_status='ACTIVE' AND new_status IN ('CONSUMED','EXPIRED','REVOKED','STALE')));
CREATE UNIQUE INDEX uq_b13_one_terminal_event ON approval_grant_events(grant_id) WHERE prior_status='ACTIVE';

CREATE FUNCTION b13_preheld(consuming boolean) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
BEGIN
 IF current_setting('transaction_isolation') <> (CASE WHEN consuming THEN 'serializable' ELSE 'read committed' END)
 OR EXISTS(SELECT 1 FROM unnest(ARRAY['actor_subject_bindings','actors','artifact_versions','artifacts','audit_findings','claim_versions','claims','correction_records','dataset_snapshots','datasets','evidence_relations','experiment_spec_versions','experiment_specs','impact_assessments','impact_targets','internal_review_records','literature_evidence','literature_evidence_relations','literature_evidence_review_events','literature_source_project_links','literature_sources','literature_support_snapshots','manuscript_artifact_placements','manuscript_citation_placements','manuscript_claim_placements','manuscript_versions','measurements','metric_definition_versions','metric_definitions','project_membership_events','project_memberships','project_role_assignments','projects','review_issue_events','review_issues','run_artifact_inputs','run_dataset_inputs','runs','scientific_conclusion_claim_inputs','scientific_conclusion_literature_inputs','scientific_conclusion_versions','scientific_conclusions','source_versions','statistical_result_inputs','statistical_results','approval_decisions','approval_request_reviews','approval_requests']) n(name)
 WHERE NOT EXISTS(SELECT 1 FROM pg_locks l WHERE l.pid=pg_backend_pid() AND l.locktype='relation' AND l.relation=to_regclass('public.'||n.name) AND l.mode='ShareLock' AND l.granted))
 OR NOT EXISTS(SELECT 1 FROM pg_locks l WHERE l.pid=pg_backend_pid() AND l.locktype='relation' AND l.relation='public.publications'::regclass AND l.mode='ShareRowExclusiveLock' AND l.granted) THEN
 RAISE EXCEPTION 'B13 preheld inventory and isolation required' USING ERRCODE='P16G1'; END IF;
END $$;
CREATE FUNCTION b13_authorized(aid UUID,pid UUID,roles TEXT[]) RETURNS boolean LANGUAGE SQL VOLATILE SET search_path=pg_catalog,public,pg_temp AS $$
 SELECT EXISTS(SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id
 JOIN project_role_assignments r ON r.membership_id=m.id AND r.actor_id=m.actor_id AND r.project_id=m.project_id
 WHERE a.id=aid AND a.retired_at IS NULL AND m.project_id=pid AND m.status='ACTIVE' AND r.role=ANY(roles)
 AND r.effective_from<=clock_timestamp() AND (r.effective_until IS NULL OR clock_timestamp()<r.effective_until)
 AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=a.id AND b.status='ACTIVE'
 AND b.bound_at<=clock_timestamp() AND (b.revoked_at IS NULL OR clock_timestamp()<b.revoked_at)))
$$;
CREATE FUNCTION b13_request_hash(c approval_grant_consumptions) RETURNS text LANGUAGE SQL STABLE SET search_path=pg_catalog,public,pg_temp AS $$
 SELECT pr216_hash(jsonb_build_object('type','ApprovalGrantConsumptionRequest','material_version',1,
 'command',c.command,'project_id',c.project_id,'actor_id',c.actor_id,'grant_id',c.grant_id,
 'target',jsonb_build_object('type','ScientificConclusionVersion','id',r.scientific_conclusion_version_id,'content_hash',r.target_content_hash),
 'result_id',c.result_scientific_conclusion_version_id,'expected_package_manifest_hash',NULL,
 'checked_review_ids',(SELECT jsonb_agg(rr.internal_review_record_id ORDER BY rr.internal_review_record_id::text) FROM approval_request_reviews rr WHERE rr.request_id=r.id)))
 FROM approval_grants g JOIN approval_decisions d ON d.id=g.approval_decision_id JOIN approval_requests r ON r.id=d.approval_request_id WHERE g.id=c.grant_id
$$;
CREATE FUNCTION b13_verify_receipt(c approval_grant_consumptions, complete boolean DEFAULT false) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE g approval_grants; d approval_decisions; r approval_requests;
BEGIN
 SELECT * INTO g FROM approval_grants WHERE id=c.grant_id;
 SELECT * INTO d FROM approval_decisions WHERE id=g.approval_decision_id;
 SELECT * INTO r FROM approval_requests WHERE id=d.approval_request_id;
 IF r.id IS NULL OR g.project_id IS DISTINCT FROM c.project_id OR r.project_id IS DISTINCT FROM c.project_id
 OR r.status<>'DECIDED' OR g.purpose<>'INTERNAL_SCIENTIFIC_RELEASE' OR g.allowed_command<>'record_internal_scientific_release'
 OR r.approval_purpose<>g.purpose OR d.decision NOT IN ('APPROVE','APPROVE_WITH_CONDITIONS')
 OR g.valid_until IS DISTINCT FROM coalesce(d.valid_until,d.decided_at+interval '720 hours')
 OR c.result_scientific_conclusion_version_id IS DISTINCT FROM r.scientific_conclusion_version_id
 OR c.consumed_at<d.decided_at OR c.consumed_at>=g.valid_until
 OR c.request_hash IS DISTINCT FROM b13_request_hash(c)
 OR c.result_dto IS DISTINCT FROM jsonb_build_object('command',c.command,'scientific_conclusion_version_id',r.scientific_conclusion_version_id,'consumption_id',c.id)
 OR NOT EXISTS(SELECT 1 FROM approval_request_reviews WHERE request_id=r.id)
 OR EXISTS((SELECT internal_review_record_id FROM approval_request_reviews WHERE request_id=r.id) EXCEPT (SELECT internal_review_record_id FROM decision_basis_reviews WHERE decision_id=r.basis_decision_id))
 OR EXISTS((SELECT internal_review_record_id FROM decision_basis_reviews WHERE decision_id=r.basis_decision_id) EXCEPT (SELECT internal_review_record_id FROM approval_request_reviews WHERE request_id=r.id)) THEN
 RAISE EXCEPTION 'corrupt receipt history' USING ERRCODE='P17F2'; END IF;
 IF complete AND (g.status<>'CONSUMED' OR NOT EXISTS(SELECT 1 FROM approval_grant_events e
  WHERE e.grant_id=g.id AND e.prior_status IS NULL AND e.new_status='ACTIVE'
    AND e.actor_id=d.decided_by AND e.reason='grant created' AND e.occurred_at>=d.decided_at)
 OR NOT EXISTS(SELECT 1 FROM approval_grant_events e WHERE e.grant_id=g.id AND e.prior_status='ACTIVE'
  AND e.new_status='CONSUMED' AND e.actor_id=c.actor_id AND e.occurred_at=c.consumed_at)) THEN
 RAISE EXCEPTION 'incomplete receipt events' USING ERRCODE='P17F2'; END IF;

END $$;
CREATE FUNCTION b13_release_gate(r approval_requests, approver UUID) RETURNS void
      LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE v scientific_conclusion_versions; d decision_records; pid UUID;
    BEGIN

      IF (r.approval_purpose='INTERNAL_SCIENTIFIC_RELEASE' AND r.scientific_conclusion_version_id IS NOT NULL AND r.manuscript_version_id IS NULL)
        OR (r.approval_purpose IN ('READY_FOR_SUBMISSION','PREPARE_SUBMISSION') AND r.manuscript_version_id IS NOT NULL AND r.scientific_conclusion_version_id IS NULL) THEN
        NULL;
      ELSE RAISE EXCEPTION 'unlisted approval tuple' USING ERRCODE='P16P1'; END IF;
      IF r.manuscript_version_id IS NOT NULL THEN RAISE EXCEPTION 'B14 binding unavailable' USING ERRCODE='P16G1'; END IF;
      SELECT * INTO v FROM scientific_conclusion_versions
        WHERE id=r.scientific_conclusion_version_id;
      SELECT project_id INTO pid FROM scientific_conclusions WHERE id=v.scientific_conclusion_id;
      IF pid IS DISTINCT FROM r.project_id OR v.status NOT IN ('FROZEN','SUPERSEDED') OR v.frozen_at IS NULL
        OR v.content_hash IS DISTINCT FROM r.target_content_hash
        OR v.hash_scheme IS DISTINCT FROM r.target_hash_scheme THEN
        RAISE EXCEPTION 'frozen exact target required' USING ERRCODE='P16T1';
      END IF;
      PERFORM b10_successor_check(r,approver);
      SELECT * INTO d FROM decision_records WHERE id=r.basis_decision_id;
      IF d.project_id IS DISTINCT FROM r.project_id OR d.decision<>'PROCEED'
        OR d.decision_type<>r.approval_purpose
        OR NOT EXISTS(SELECT 1 FROM decision_basis_conclusions WHERE decision_id=d.id
          AND scientific_conclusion_version_id=v.id)
        OR NOT EXISTS(SELECT 1 FROM decision_basis_reviews WHERE decision_id=d.id) THEN
        RAISE EXCEPTION 'affirmative exact basis required' USING ERRCODE='P16B1';
      END IF;
      IF EXISTS(SELECT 1 FROM review_issues i JOIN internal_review_records x
        ON x.id=i.review_record_id WHERE x.project_id=r.project_id
        AND x.scientific_conclusion_version_id=v.id AND i.status='OPEN'
          AND i.severity='BLOCKING') THEN
        RAISE EXCEPTION 'blocking issue' USING ERRCODE='P16G1';
      END IF;
      IF EXISTS(SELECT 1 FROM decision_basis_reviews b JOIN internal_review_records x
        ON x.id=b.internal_review_record_id WHERE b.decision_id=d.id
        AND (x.project_id IS DISTINCT FROM r.project_id
          OR x.scientific_conclusion_version_id IS DISTINCT FROM v.id
          OR x.target_content_hash IS DISTINCT FROM r.target_content_hash
          OR x.reviewer_actor_id=r.requested_by
          OR x.reviewer_actor_id IN (SELECT pr216_authors(v.id)))) THEN
        RAISE EXCEPTION 'reviewer independence' USING ERRCODE='P16C1';
      END IF;
      IF NOT EXISTS(SELECT 1 FROM projects WHERE id=r.project_id AND lifecycle_status='ACTIVE') THEN
        RAISE EXCEPTION 'active project required' USING ERRCODE='P16G1';
      END IF;
      PERFORM b08_check_history(i.id) FROM review_issues i JOIN internal_review_records rr
        ON rr.id=i.review_record_id WHERE rr.project_id=r.project_id AND rr.scientific_conclusion_version_id=v.id;
      PERFORM pr216_material_gate(r);
      IF d.decided_by IN (SELECT pr216_authors(v.id)) THEN
        RAISE EXCEPTION 'independent basis decider required' USING ERRCODE='P16C1';
      END IF;
      IF approver IS NOT NULL THEN
        IF EXISTS(SELECT 1 FROM approval_requests q WHERE q.project_id=r.project_id
          AND q.approval_purpose=r.approval_purpose
          AND coalesce(q.scientific_conclusion_version_id,q.manuscript_version_id)<>coalesce(r.scientific_conclusion_version_id,r.manuscript_version_id)
          AND q.requested_at>r.requested_at) THEN
          RAISE EXCEPTION 'newer approval target selected' USING ERRCODE='P16T1';
        END IF;
        IF NOT pr216_approver_active(approver,r.project_id) THEN
          IF EXISTS(SELECT 1 FROM approval_grants g JOIN approval_decisions ad
            ON ad.id=g.approval_decision_id WHERE ad.approval_request_id=r.id
            AND clock_timestamp()>=g.valid_until) THEN
            RAISE EXCEPTION 'grant expired during issuer check' USING ERRCODE='P13G1'; END IF;
          RAISE EXCEPTION 'issuing authority lost' USING ERRCODE='P13S1';
        END IF;
        IF approver=r.requested_by OR approver=d.decided_by
          OR approver IN (SELECT pr216_authors(v.id))
          OR EXISTS(SELECT 1 FROM decision_basis_reviews b JOIN internal_review_records x
            ON x.id=b.internal_review_record_id WHERE b.decision_id=d.id
            AND x.reviewer_actor_id=approver) THEN
          RAISE EXCEPTION 'independent approver required' USING ERRCODE='P16C1';
        END IF;
      END IF;
    END $$;
CREATE FUNCTION b13_stale(g approval_grants) RETURNS boolean LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE r approval_requests; d approval_decisions;
BEGIN
 SELECT * INTO d FROM approval_decisions WHERE id=g.approval_decision_id;
 SELECT * INTO r FROM approval_requests WHERE id=d.approval_request_id;
 IF NOT pr216_approver_active(d.decided_by,g.project_id) OR EXISTS(
 SELECT 1 FROM approval_requests q WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose
 AND coalesce(q.scientific_conclusion_version_id,q.manuscript_version_id)<>coalesce(r.scientific_conclusion_version_id,r.manuscript_version_id)
 AND q.requested_at>r.requested_at) THEN RETURN true; END IF;
 IF r.manuscript_version_id IS NOT NULL THEN
 RAISE EXCEPTION 'B14 consent/effect dependency unavailable' USING ERRCODE='P16G1'; END IF;
 BEGIN
  PERFORM b13_release_gate(r,d.decided_by);
 EXCEPTION WHEN SQLSTATE 'P16T1' OR SQLSTATE 'P16R1' OR SQLSTATE 'P16G1' OR SQLSTATE 'P16C1' OR SQLSTATE 'P16A1' OR SQLSTATE 'P13S1' THEN RETURN true;
 END;
 RETURN false;
END $$;
CREATE FUNCTION b13_consumption_guard() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE g approval_grants; d approval_decisions; r approval_requests;
BEGIN
 PERFORM b13_preheld(true);
 SELECT * INTO g FROM approval_grants WHERE id=NEW.grant_id;
 SELECT * INTO d FROM approval_decisions WHERE id=g.approval_decision_id;
 SELECT * INTO r FROM approval_requests WHERE id=d.approval_request_id;
 IF g.status IS DISTINCT FROM 'ACTIVE' OR clock_timestamp()>=g.valid_until THEN
 RAISE EXCEPTION 'grant unavailable' USING ERRCODE='P13G1'; END IF;
 IF NOT b13_authorized(NEW.actor_id,NEW.project_id,ARRAY['OWNER','RESEARCHER']) THEN
 RAISE EXCEPTION 'writer required' USING ERRCODE='P16A1'; END IF;
 PERFORM b13_release_gate(r,d.decided_by);
 IF NEW.consumed_at>clock_timestamp() THEN RAISE EXCEPTION 'observed time required' USING ERRCODE='P17F2'; END IF;
 NEW.consumed_at:=clock_timestamp();
 IF NEW.consumed_at>=g.valid_until THEN RAISE EXCEPTION 'grant expired during admission' USING ERRCODE='P13G1'; END IF;
 PERFORM b13_verify_receipt(NEW);
 RETURN NEW;
END $$;
CREATE TRIGGER b13_consumption_guard BEFORE INSERT ON approval_grant_consumptions FOR EACH ROW EXECUTE FUNCTION b13_consumption_guard();
CREATE TRIGGER b13_consumption_immutable BEFORE UPDATE OR DELETE ON approval_grant_consumptions FOR EACH ROW EXECUTE FUNCTION pr215_immutable();

CREATE FUNCTION b13_validate_event(e approval_grant_events) RETURNS approval_grant_events LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
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

CREATE FUNCTION b13_complete() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
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
CREATE CONSTRAINT TRIGGER b13_complete_consumption AFTER INSERT ON approval_grant_consumptions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b13_complete();
CREATE CONSTRAINT TRIGGER b13_complete_grant AFTER INSERT OR UPDATE ON approval_grants DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b13_complete();
CREATE CONSTRAINT TRIGGER b13_complete_terminal_event AFTER INSERT ON approval_grant_events DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b13_complete();

CREATE OR REPLACE FUNCTION public.pr216_grant_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
    DECLARE d approval_decisions; r approval_requests;
    BEGIN
      IF TG_OP='DELETE' THEN RAISE EXCEPTION 'immutable grant' USING ERRCODE='P17F1'; END IF;
      IF TG_OP='UPDATE' THEN
        IF (to_jsonb(NEW)-'status') IS DISTINCT FROM (to_jsonb(OLD)-'status')
          OR OLD.status<>'ACTIVE' OR NEW.status NOT IN ('CONSUMED','EXPIRED','REVOKED','STALE') THEN
          RAISE EXCEPTION 'immutable terminal grant' USING ERRCODE='P17F1'; END IF;
        IF EXISTS(SELECT 1 FROM approval_grant_events e WHERE e.grant_id=OLD.id
          AND e.prior_status='ACTIVE' AND e.new_status=NEW.status AND e.xmin=pg_current_xact_id()::xid) THEN
          RETURN NEW;
        END IF;
        IF pg_trigger_depth()<2 THEN
          RAISE EXCEPTION 'explicit grant lifecycle command unavailable' USING ERRCODE='P17F1';
        END IF;
        SELECT * INTO d FROM approval_decisions WHERE id=OLD.approval_decision_id;
        SELECT * INTO r FROM approval_requests WHERE id=d.approval_request_id;
        IF pr216_approver_active(d.decided_by,r.project_id) AND NOT EXISTS(
          SELECT 1 FROM approval_requests q WHERE q.project_id=r.project_id
            AND q.approval_purpose=r.approval_purpose
            AND coalesce(q.scientific_conclusion_version_id,q.manuscript_version_id)<>coalesce(r.scientific_conclusion_version_id,r.manuscript_version_id)
            AND q.xmin=pg_current_xact_id()::xid) AND NOT EXISTS (
          SELECT 1 FROM approval_decisions rejected JOIN approval_requests q ON q.id=rejected.approval_request_id
          WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose AND rejected.decision='REJECT'
          AND rejected.xmin=pg_current_xact_id()::xid) THEN
          RAISE EXCEPTION 'contracted stale cause required' USING ERRCODE='P17F1';
        END IF;
        IF (to_jsonb(NEW)-'status') IS DISTINCT FROM (to_jsonb(OLD)-'status')
          OR OLD.status<>'ACTIVE' OR NEW.status<>'STALE' THEN
          RAISE EXCEPTION 'monotonic grant only' USING ERRCODE='P17F1';
        END IF; RETURN NEW;
      END IF;
      PERFORM b09_preheld();
      SELECT * INTO d FROM approval_decisions WHERE id=NEW.approval_decision_id;
      SELECT * INTO r FROM approval_requests WHERE id=d.approval_request_id;
      IF d.decision NOT IN ('APPROVE','APPROVE_WITH_CONDITIONS') OR r.id IS NULL
        OR NEW.project_id<>r.project_id OR NEW.purpose<>r.approval_purpose
        OR NEW.allowed_command IS DISTINCT FROM (CASE r.approval_purpose
          WHEN 'INTERNAL_SCIENTIFIC_RELEASE' THEN 'record_internal_scientific_release'
          WHEN 'READY_FOR_SUBMISSION' THEN 'transition_publication_ready'
          WHEN 'PREPARE_SUBMISSION' THEN 'freeze_prepared_submission' END)
        OR NOT pr216_approver_active(d.decided_by,r.project_id)
        OR clock_timestamp()>=NEW.valid_until
        OR NEW.status<>'ACTIVE' OR NEW.valid_until IS DISTINCT FROM
          coalesce(d.valid_until,d.decided_at+interval '720 hours')
        OR NOT EXISTS(SELECT 1 FROM approval_decisions WHERE id=d.id
          AND xmin=pg_current_xact_id()::xid) THEN
        RAISE EXCEPTION 'exact new grant required' USING ERRCODE='P16G1';
      END IF; RETURN NEW;
    END $function$;
CREATE OR REPLACE FUNCTION pr216_events() RETURNS trigger LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE r approval_requests; d approval_decisions;
    BEGIN
      IF TG_RELID NOT IN ('public.approval_requests'::regclass,
        'public.approval_decisions'::regclass,'public.approval_grants'::regclass) THEN
        RAISE EXCEPTION 'canonical lifecycle writer required' USING ERRCODE='P17F1';
      END IF;
      IF TG_TABLE_NAME='approval_requests' THEN
        INSERT INTO approval_request_events(request_id,prior_status,new_status,
          actor_id,occurred_at,reason)
          VALUES(NEW.id,NULL,'PENDING',NEW.requested_by,NEW.requested_at,'request created');
        -- Selecting a new target for this purpose terminally stales older unused grants.
        UPDATE approval_grants g SET status='STALE' FROM approval_decisions x,approval_requests q
          WHERE g.approval_decision_id=x.id AND x.approval_request_id=q.id
            AND q.project_id=NEW.project_id AND q.approval_purpose=NEW.approval_purpose
            AND coalesce(q.scientific_conclusion_version_id,q.manuscript_version_id)<>coalesce(NEW.scientific_conclusion_version_id,NEW.manuscript_version_id)
            AND g.status='ACTIVE';
      ELSIF TG_TABLE_NAME='approval_decisions' THEN
        UPDATE approval_requests SET status='DECIDED' WHERE id=NEW.approval_request_id;
        INSERT INTO approval_request_events(request_id,prior_status,new_status,
          actor_id,occurred_at,reason)
          VALUES(NEW.approval_request_id,'PENDING','DECIDED',NEW.decided_by,NEW.decided_at,
            'decision recorded');
        IF NEW.decision='REJECT' THEN
          SELECT * INTO r FROM approval_requests WHERE id=NEW.approval_request_id;
          UPDATE approval_grants g SET status='STALE' FROM approval_decisions x,approval_requests q
            WHERE g.approval_decision_id=x.id AND x.approval_request_id=q.id
              AND q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose
              AND g.status='ACTIVE';
        END IF;
      ELSE
        IF TG_OP='UPDATE' AND EXISTS(SELECT 1 FROM approval_grant_events e
          WHERE e.grant_id=NEW.id AND e.prior_status=OLD.status AND e.new_status=NEW.status
            AND e.xmin=pg_current_xact_id()::xid) THEN RETURN NULL; END IF;
        SELECT * INTO d FROM approval_decisions WHERE id=NEW.approval_decision_id;
        INSERT INTO approval_grant_events(grant_id,prior_status,new_status,
          actor_id,occurred_at,reason)
          VALUES(NEW.id,CASE WHEN TG_OP='INSERT' THEN NULL ELSE OLD.status END,NEW.status,
            d.decided_by,clock_timestamp(),
            CASE WHEN TG_OP='INSERT' THEN 'grant created' ELSE 'grant stale' END);
      END IF; RETURN NULL;
    END $$;
CREATE OR REPLACE FUNCTION public.pr216_event_insert()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE r approval_requests; d approval_decisions; g approval_grants; owner_xmin xid;
BEGIN
 IF TG_TABLE_NAME='approval_grant_events' THEN RETURN b13_validate_event(NEW); END IF;
 IF pg_trigger_depth()<2 THEN
   RAISE EXCEPTION 'events belong to atomic lifecycle change' USING ERRCODE='P17F1';
 END IF;
 IF TG_TABLE_NAME='approval_request_events' THEN
   SELECT q.* INTO r FROM approval_requests q WHERE q.id=NEW.request_id;
   SELECT xmin INTO owner_xmin FROM approval_requests WHERE id=NEW.request_id;
   IF owner_xmin IS DISTINCT FROM pg_current_xact_id()::xid
     OR EXISTS(SELECT 1 FROM approval_request_events WHERE request_id=NEW.request_id AND new_status=NEW.new_status)
     OR r.status IS DISTINCT FROM NEW.new_status THEN
     RAISE EXCEPTION 'exact atomic request event required' USING ERRCODE='P17F1';
   END IF;
   IF NEW.new_status='PENDING' THEN
     IF NEW.prior_status IS NOT NULL OR NEW.actor_id<>r.requested_by OR NEW.occurred_at<>r.requested_at
       OR NEW.reason<>'request created' THEN
       RAISE EXCEPTION 'exact creation event required' USING ERRCODE='P17F1';
     END IF;
   ELSE
     SELECT * INTO d FROM approval_decisions WHERE approval_request_id=r.id;
     IF NEW.prior_status IS DISTINCT FROM 'PENDING' OR NEW.actor_id IS DISTINCT FROM d.decided_by
       OR NEW.occurred_at IS DISTINCT FROM d.decided_at OR NEW.reason<>'decision recorded' THEN
       RAISE EXCEPTION 'exact decision event required' USING ERRCODE='P17F1';
     END IF;
   END IF;
 ELSIF TG_TABLE_NAME='approval_grant_events' THEN
   SELECT * INTO g FROM approval_grants WHERE id=NEW.grant_id;
   SELECT xmin INTO owner_xmin FROM approval_grants WHERE id=NEW.grant_id;
   SELECT * INTO d FROM approval_decisions WHERE id=g.approval_decision_id;
   IF owner_xmin IS DISTINCT FROM pg_current_xact_id()::xid
     OR EXISTS(SELECT 1 FROM approval_grant_events WHERE grant_id=NEW.grant_id AND new_status=NEW.new_status)
     OR NEW.new_status IS DISTINCT FROM g.status OR NEW.actor_id IS DISTINCT FROM d.decided_by
     OR NEW.occurred_at<d.decided_at OR NEW.occurred_at>clock_timestamp()
     OR (NEW.new_status='ACTIVE' AND (NEW.prior_status IS NOT NULL OR NEW.reason<>'grant created'))
     OR (NEW.new_status='STALE' AND (NEW.prior_status IS DISTINCT FROM 'ACTIVE' OR NEW.reason<>'grant stale')) THEN
     RAISE EXCEPTION 'exact atomic grant event required' USING ERRCODE='P17F1';
   END IF;
 ELSE
   RAISE EXCEPTION 'canonical event relation required' USING ERRCODE='P17F1';
 END IF;
 RETURN NEW;
END $function$;
"""

DOWNGRADE_SQL = r"""
LOCK TABLE approval_grants,approval_grant_events,approval_grant_consumptions IN ACCESS EXCLUSIVE MODE;
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM approval_grant_consumptions) OR EXISTS(SELECT 1 FROM approval_grant_events WHERE new_status IN ('CONSUMED','EXPIRED','REVOKED') OR (prior_status='ACTIVE' AND reason<>'grant stale')) THEN
 RAISE EXCEPTION 'B13 terminal history cannot be discarded' USING ERRCODE='P17F2'; END IF;
END $$;
DROP TRIGGER b13_complete_grant ON approval_grants;
DROP TRIGGER b13_complete_terminal_event ON approval_grant_events;
DROP TRIGGER b13_complete_consumption ON approval_grant_consumptions;
DROP TRIGGER b13_consumption_guard ON approval_grant_consumptions;
DROP FUNCTION b13_complete();
DROP FUNCTION b13_consumption_guard();
DROP FUNCTION b13_verify_receipt(approval_grant_consumptions,boolean);
DROP FUNCTION b13_request_hash(approval_grant_consumptions);
DROP TABLE approval_grant_consumptions;
DROP FUNCTION b13_validate_event(approval_grant_events);
DROP FUNCTION b13_stale(approval_grants);
DROP FUNCTION b13_release_gate(approval_requests,UUID);
DROP FUNCTION b13_authorized(UUID,UUID,TEXT[]);
DROP FUNCTION b13_preheld(boolean);
DROP INDEX uq_b13_one_terminal_event;
ALTER TABLE approval_grant_events DROP CONSTRAINT ck_b13_grant_event_status;
ALTER TABLE approval_grant_events ADD CHECK(new_status IN ('ACTIVE','STALE'));

CREATE OR REPLACE FUNCTION public.pr216_grant_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
    DECLARE d approval_decisions; r approval_requests;
    BEGIN
      IF TG_OP='DELETE' THEN RAISE EXCEPTION 'immutable grant' USING ERRCODE='P17F1'; END IF;
      IF TG_OP='UPDATE' THEN
        IF pg_trigger_depth()<2 THEN
          RAISE EXCEPTION 'explicit grant lifecycle command unavailable' USING ERRCODE='P17F1';
        END IF;
        SELECT * INTO d FROM approval_decisions WHERE id=OLD.approval_decision_id;
        SELECT * INTO r FROM approval_requests WHERE id=d.approval_request_id;
        IF pr216_approver_active(d.decided_by,r.project_id) AND NOT EXISTS(
          SELECT 1 FROM approval_requests q WHERE q.project_id=r.project_id
            AND q.approval_purpose=r.approval_purpose
            AND coalesce(q.scientific_conclusion_version_id,q.manuscript_version_id)<>coalesce(r.scientific_conclusion_version_id,r.manuscript_version_id)
            AND q.xmin=pg_current_xact_id()::xid) AND NOT EXISTS (
          SELECT 1 FROM approval_decisions rejected JOIN approval_requests q ON q.id=rejected.approval_request_id
          WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose AND rejected.decision='REJECT'
          AND rejected.xmin=pg_current_xact_id()::xid) THEN
          RAISE EXCEPTION 'contracted stale cause required' USING ERRCODE='P17F1';
        END IF;
        IF (to_jsonb(NEW)-'status') IS DISTINCT FROM (to_jsonb(OLD)-'status')
          OR OLD.status<>'ACTIVE' OR NEW.status<>'STALE' THEN
          RAISE EXCEPTION 'monotonic grant only' USING ERRCODE='P17F1';
        END IF; RETURN NEW;
      END IF;
      PERFORM b09_preheld();
      SELECT * INTO d FROM approval_decisions WHERE id=NEW.approval_decision_id;
      SELECT * INTO r FROM approval_requests WHERE id=d.approval_request_id;
      IF d.decision NOT IN ('APPROVE','APPROVE_WITH_CONDITIONS') OR r.id IS NULL
        OR NEW.project_id<>r.project_id OR NEW.purpose<>r.approval_purpose
        OR NEW.allowed_command IS DISTINCT FROM (CASE r.approval_purpose
          WHEN 'INTERNAL_SCIENTIFIC_RELEASE' THEN 'record_internal_scientific_release'
          WHEN 'READY_FOR_SUBMISSION' THEN 'transition_publication_ready'
          WHEN 'PREPARE_SUBMISSION' THEN 'freeze_prepared_submission' END)
        OR NOT pr216_approver_active(d.decided_by,r.project_id)
        OR clock_timestamp()>=NEW.valid_until
        OR NEW.status<>'ACTIVE' OR NEW.valid_until IS DISTINCT FROM
          coalesce(d.valid_until,d.decided_at+interval '720 hours')
        OR NOT EXISTS(SELECT 1 FROM approval_decisions WHERE id=d.id
          AND xmin=pg_current_xact_id()::xid) THEN
        RAISE EXCEPTION 'exact new grant required' USING ERRCODE='P16G1';
      END IF; RETURN NEW;
    END $function$;
CREATE OR REPLACE FUNCTION pr216_events() RETURNS trigger LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE r approval_requests; d approval_decisions;
    BEGIN
      IF TG_RELID NOT IN ('public.approval_requests'::regclass,
        'public.approval_decisions'::regclass,'public.approval_grants'::regclass) THEN
        RAISE EXCEPTION 'canonical lifecycle writer required' USING ERRCODE='P17F1';
      END IF;
      IF TG_TABLE_NAME='approval_requests' THEN
        INSERT INTO approval_request_events(request_id,prior_status,new_status,
          actor_id,occurred_at,reason)
          VALUES(NEW.id,NULL,'PENDING',NEW.requested_by,NEW.requested_at,'request created');
        -- Selecting a new target for this purpose terminally stales older unused grants.
        UPDATE approval_grants g SET status='STALE' FROM approval_decisions x,approval_requests q
          WHERE g.approval_decision_id=x.id AND x.approval_request_id=q.id
            AND q.project_id=NEW.project_id AND q.approval_purpose=NEW.approval_purpose
            AND coalesce(q.scientific_conclusion_version_id,q.manuscript_version_id)<>coalesce(NEW.scientific_conclusion_version_id,NEW.manuscript_version_id)
            AND g.status='ACTIVE';
      ELSIF TG_TABLE_NAME='approval_decisions' THEN
        UPDATE approval_requests SET status='DECIDED' WHERE id=NEW.approval_request_id;
        INSERT INTO approval_request_events(request_id,prior_status,new_status,
          actor_id,occurred_at,reason)
          VALUES(NEW.approval_request_id,'PENDING','DECIDED',NEW.decided_by,NEW.decided_at,
            'decision recorded');
        IF NEW.decision='REJECT' THEN
          SELECT * INTO r FROM approval_requests WHERE id=NEW.approval_request_id;
          UPDATE approval_grants g SET status='STALE' FROM approval_decisions x,approval_requests q
            WHERE g.approval_decision_id=x.id AND x.approval_request_id=q.id
              AND q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose
              AND g.status='ACTIVE';
        END IF;
      ELSE
        SELECT * INTO d FROM approval_decisions WHERE id=NEW.approval_decision_id;
        INSERT INTO approval_grant_events(grant_id,prior_status,new_status,
          actor_id,occurred_at,reason)
          VALUES(NEW.id,CASE WHEN TG_OP='INSERT' THEN NULL ELSE OLD.status END,NEW.status,
            d.decided_by,clock_timestamp(),
            CASE WHEN TG_OP='INSERT' THEN 'grant created' ELSE 'grant stale' END);
      END IF; RETURN NULL;
    END $$;
CREATE OR REPLACE FUNCTION public.pr216_event_insert()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE r approval_requests; d approval_decisions; g approval_grants; owner_xmin xid;
BEGIN
 IF pg_trigger_depth()<2 THEN
   RAISE EXCEPTION 'events belong to atomic lifecycle change' USING ERRCODE='P17F1';
 END IF;
 IF TG_TABLE_NAME='approval_request_events' THEN
   SELECT q.* INTO r FROM approval_requests q WHERE q.id=NEW.request_id;
   SELECT xmin INTO owner_xmin FROM approval_requests WHERE id=NEW.request_id;
   IF owner_xmin IS DISTINCT FROM pg_current_xact_id()::xid
     OR EXISTS(SELECT 1 FROM approval_request_events WHERE request_id=NEW.request_id AND new_status=NEW.new_status)
     OR r.status IS DISTINCT FROM NEW.new_status THEN
     RAISE EXCEPTION 'exact atomic request event required' USING ERRCODE='P17F1';
   END IF;
   IF NEW.new_status='PENDING' THEN
     IF NEW.prior_status IS NOT NULL OR NEW.actor_id<>r.requested_by OR NEW.occurred_at<>r.requested_at
       OR NEW.reason<>'request created' THEN
       RAISE EXCEPTION 'exact creation event required' USING ERRCODE='P17F1';
     END IF;
   ELSE
     SELECT * INTO d FROM approval_decisions WHERE approval_request_id=r.id;
     IF NEW.prior_status IS DISTINCT FROM 'PENDING' OR NEW.actor_id IS DISTINCT FROM d.decided_by
       OR NEW.occurred_at IS DISTINCT FROM d.decided_at OR NEW.reason<>'decision recorded' THEN
       RAISE EXCEPTION 'exact decision event required' USING ERRCODE='P17F1';
     END IF;
   END IF;
 ELSIF TG_TABLE_NAME='approval_grant_events' THEN
   SELECT * INTO g FROM approval_grants WHERE id=NEW.grant_id;
   SELECT xmin INTO owner_xmin FROM approval_grants WHERE id=NEW.grant_id;
   SELECT * INTO d FROM approval_decisions WHERE id=g.approval_decision_id;
   IF owner_xmin IS DISTINCT FROM pg_current_xact_id()::xid
     OR EXISTS(SELECT 1 FROM approval_grant_events WHERE grant_id=NEW.grant_id AND new_status=NEW.new_status)
     OR NEW.new_status IS DISTINCT FROM g.status OR NEW.actor_id IS DISTINCT FROM d.decided_by
     OR NEW.occurred_at<d.decided_at OR NEW.occurred_at>clock_timestamp()
     OR (NEW.new_status='ACTIVE' AND (NEW.prior_status IS NOT NULL OR NEW.reason<>'grant created'))
     OR (NEW.new_status='STALE' AND (NEW.prior_status IS DISTINCT FROM 'ACTIVE' OR NEW.reason<>'grant stale')) THEN
     RAISE EXCEPTION 'exact atomic grant event required' USING ERRCODE='P17F1';
   END IF;
 ELSE
   RAISE EXCEPTION 'canonical event relation required' USING ERRCODE='P17F1';
 END IF;
 RETURN NEW;
END $function$;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
