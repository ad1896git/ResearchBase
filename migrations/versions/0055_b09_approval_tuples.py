"""B09 finite approval tuples, lock protocol and project/purpose rejection fence."""

# Frozen SQL copies preserve accepted migrations and empty-slice downgrade behavior.
# ruff: noqa: E501
from alembic import op

revision = "0055_b09_approval_tuples"
down_revision = "0054_b11_ready_for_submission"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)


UPGRADE_SQL = r"""
LOCK TABLE approval_requests,approval_decisions,approval_grants,approval_request_reviews,approval_request_events,approval_grant_events IN ACCESS EXCLUSIVE MODE;
DO $$ DECLARE cname text; n integer; BEGIN
 SELECT count(*),min(c.conname) INTO n,cname FROM pg_constraint c
 WHERE c.conrelid='approval_requests'::regclass AND c.contype='c'
 AND c.conkey=ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid='approval_requests'::regclass AND attname='approval_purpose')]::smallint[]
 AND pg_get_constraintdef(c.oid)='CHECK ((approval_purpose = ''INTERNAL_SCIENTIFIC_RELEASE''::text))';
 IF n<>1 THEN RAISE EXCEPTION 'unexpected legacy approval_requests.approval_purpose CHECK'; END IF;
 EXECUTE format('ALTER TABLE approval_requests DROP CONSTRAINT %I',cname);
END $$;
DO $$ DECLARE cname text; n integer; BEGIN
 SELECT count(*),min(c.conname) INTO n,cname FROM pg_constraint c
 WHERE c.conrelid='approval_requests'::regclass AND c.contype='c'
 AND c.conkey=ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid='approval_requests'::regclass AND attname='scientific_conclusion_version_id')]::smallint[]
 AND pg_get_constraintdef(c.oid)='CHECK ((scientific_conclusion_version_id IS NOT NULL))';
 IF n<>1 THEN RAISE EXCEPTION 'unexpected legacy approval_requests.scientific_conclusion_version_id CHECK'; END IF;
 EXECUTE format('ALTER TABLE approval_requests DROP CONSTRAINT %I',cname);
END $$;
DO $$ DECLARE cname text; n integer; BEGIN
 SELECT count(*),min(c.conname) INTO n,cname FROM pg_constraint c
 WHERE c.conrelid='approval_grants'::regclass AND c.contype='c'
 AND c.conkey=ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid='approval_grants'::regclass AND attname='purpose')]::smallint[]
 AND pg_get_constraintdef(c.oid)='CHECK ((purpose = ''INTERNAL_SCIENTIFIC_RELEASE''::text))';
 IF n<>1 THEN RAISE EXCEPTION 'unexpected legacy approval_grants.purpose CHECK'; END IF;
 EXECUTE format('ALTER TABLE approval_grants DROP CONSTRAINT %I',cname);
END $$;
DO $$ DECLARE cname text; n integer; BEGIN
 SELECT count(*),min(c.conname) INTO n,cname FROM pg_constraint c
 WHERE c.conrelid='approval_grants'::regclass AND c.contype='c'
 AND c.conkey=ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid='approval_grants'::regclass AND attname='allowed_command')]::smallint[]
 AND pg_get_constraintdef(c.oid)='CHECK ((allowed_command = ''record_internal_scientific_release''::text))';
 IF n<>1 THEN RAISE EXCEPTION 'unexpected legacy approval_grants.allowed_command CHECK'; END IF;
 EXECUTE format('ALTER TABLE approval_grants DROP CONSTRAINT %I',cname);
END $$;
DO $$ DECLARE cname text; n integer; BEGIN
 SELECT count(*),min(c.conname) INTO n,cname FROM pg_constraint c
 WHERE c.conrelid='approval_decisions'::regclass AND c.contype='c'
 AND c.conkey=ARRAY[(SELECT attnum FROM pg_attribute WHERE attrelid='approval_decisions'::regclass AND attname='requires_current_author_consent')]::smallint[]
 AND pg_get_constraintdef(c.oid)='CHECK ((NOT requires_current_author_consent))';
 IF n<>1 THEN RAISE EXCEPTION 'unexpected legacy approval_decisions.requires_current_author_consent CHECK'; END IF;
 EXECUTE format('ALTER TABLE approval_decisions DROP CONSTRAINT %I',cname);
END $$;

ALTER TABLE approval_requests ADD CONSTRAINT ck_b09_request_tuple CHECK (
 (approval_purpose='INTERNAL_SCIENTIFIC_RELEASE' AND scientific_conclusion_version_id IS NOT NULL AND manuscript_version_id IS NULL)
 OR (approval_purpose IN ('READY_FOR_SUBMISSION','PREPARE_SUBMISSION') AND manuscript_version_id IS NOT NULL AND scientific_conclusion_version_id IS NULL));
DROP INDEX uq_pr216_pending;
CREATE UNIQUE INDEX uq_b09_pending_conclusion ON approval_requests (project_id,approval_purpose,scientific_conclusion_version_id) WHERE status='PENDING' AND scientific_conclusion_version_id IS NOT NULL;
CREATE UNIQUE INDEX uq_b09_pending_manuscript ON approval_requests (project_id,approval_purpose,manuscript_version_id) WHERE status='PENDING' AND manuscript_version_id IS NOT NULL;
ALTER TABLE approval_grants ADD CONSTRAINT ck_b09_grant_tuple CHECK (
 (purpose='INTERNAL_SCIENTIFIC_RELEASE' AND allowed_command='record_internal_scientific_release')
 OR (purpose='READY_FOR_SUBMISSION' AND allowed_command='transition_publication_ready')
 OR (purpose='PREPARE_SUBMISSION' AND allowed_command='freeze_prepared_submission'));
ALTER TABLE approval_decisions ADD CONSTRAINT ck_b09_consent_condition CHECK (NOT requires_current_author_consent OR decision='APPROVE_WITH_CONDITIONS');
CREATE INDEX ix_b09_rejection_scope ON approval_requests(project_id,approval_purpose,id);

CREATE FUNCTION b09_preheld() RETURNS void LANGUAGE plpgsql
 SET search_path=pg_catalog, public, pg_temp AS $$
BEGIN
 IF current_setting('transaction_isolation') <> 'read committed' OR EXISTS (
   SELECT 1 FROM unnest(ARRAY['actor_subject_bindings','actors','artifact_versions','artifacts','audit_findings','claim_versions','claims','correction_records','dataset_snapshots','datasets','evidence_relations','experiment_spec_versions','experiment_specs','impact_assessments','impact_targets','literature_evidence','literature_evidence_relations','literature_evidence_review_events','literature_source_project_links','literature_sources','literature_support_snapshots','manuscript_artifact_placements','manuscript_citation_placements','manuscript_claim_placements','manuscript_versions','measurements','metric_definition_versions','metric_definitions','project_membership_events','project_memberships','project_role_assignments','projects','publications','run_artifact_inputs','run_dataset_inputs','runs','scientific_conclusion_claim_inputs','scientific_conclusion_literature_inputs','scientific_conclusion_versions','scientific_conclusions','source_versions','statistical_result_inputs','statistical_results']) AS n(name)
   WHERE NOT EXISTS(SELECT 1 FROM pg_locks l WHERE l.pid=pg_backend_pid()
     AND l.locktype='relation' AND l.relation=to_regclass('public.'||n.name)
     AND l.mode='ShareLock' AND l.granted)) THEN
   RAISE EXCEPTION 'B09 requires preheld SHARE inventory at READ COMMITTED' USING ERRCODE='P16G1';
 END IF;
END $$;
    CREATE OR REPLACE FUNCTION pr216_gate(r approval_requests, approver UUID) RETURNS void
      LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE v scientific_conclusion_versions; d decision_records; pid UUID;
    BEGIN
      PERFORM b09_preheld();
      IF (r.approval_purpose='INTERNAL_SCIENTIFIC_RELEASE' AND r.scientific_conclusion_version_id IS NOT NULL AND r.manuscript_version_id IS NULL)
        OR (r.approval_purpose IN ('READY_FOR_SUBMISSION','PREPARE_SUBMISSION') AND r.manuscript_version_id IS NOT NULL AND r.scientific_conclusion_version_id IS NULL) THEN
        NULL;
      ELSE RAISE EXCEPTION 'unlisted approval tuple' USING ERRCODE='P16P1'; END IF;
      PERFORM pg_advisory_xact_lock(hashtextextended(
        'pr216:scope:'||r.project_id||':'||r.approval_purpose,0));
      IF r.manuscript_version_id IS NOT NULL THEN
        PERFORM m.id FROM manuscript_versions m WHERE m.id=r.manuscript_version_id FOR UPDATE;
        PERFORM p.id FROM publications p JOIN manuscript_versions m ON m.publication_id=p.id
          WHERE m.id=r.manuscript_version_id FOR SHARE OF p;
        RAISE EXCEPTION 'manuscript Decision dependency unavailable' USING ERRCODE='P16B1';
      END IF;
      SELECT * INTO v FROM scientific_conclusion_versions
        WHERE id=r.scientific_conclusion_version_id FOR UPDATE;
      SELECT project_id INTO pid FROM scientific_conclusions WHERE id=v.scientific_conclusion_id;
      IF pid IS DISTINCT FROM r.project_id OR v.status<>'FROZEN' OR v.frozen_at IS NULL
        OR v.content_hash IS DISTINCT FROM r.target_content_hash
        OR v.hash_scheme IS DISTINCT FROM r.target_hash_scheme THEN
        RAISE EXCEPTION 'frozen exact target required' USING ERRCODE='P16T1';
      END IF;
      IF EXISTS(SELECT 1 FROM approval_decisions x JOIN approval_requests q
        ON q.id=x.approval_request_id WHERE q.project_id=r.project_id
          AND q.approval_purpose=r.approval_purpose AND x.decision='REJECT') THEN
        RAISE EXCEPTION 'reconsideration required' USING ERRCODE='P16R1';
      END IF;
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
          RAISE EXCEPTION 'human approver required' USING ERRCODE='P16A1';
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
    CREATE OR REPLACE FUNCTION pr216_request_guard() RETURNS trigger LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    BEGIN
      IF TG_OP='DELETE' THEN
        RAISE EXCEPTION 'immutable request' USING ERRCODE='P17F1';
      ELSIF TG_OP='UPDATE' THEN
        IF (to_jsonb(NEW)-'status') IS DISTINCT FROM (to_jsonb(OLD)-'status')
          OR OLD.status<>'PENDING' OR NEW.status<>'DECIDED'
          OR NOT EXISTS(SELECT 1 FROM approval_decisions WHERE approval_request_id=OLD.id) THEN
          RAISE EXCEPTION 'immutable request material' USING ERRCODE='P17F1';
        END IF; RETURN NEW;
      END IF;
      IF NEW.status<>'PENDING' THEN
        RAISE EXCEPTION 'initial pending required' USING ERRCODE='P16G1';
      END IF;
      PERFORM b09_preheld();
      PERFORM pg_advisory_xact_lock(hashtextextended('pr216:uuid:'||NEW.id,0));
      PERFORM pr216_gate(NEW,NULL);
      IF (SELECT count(*) FROM decision_basis_reviews WHERE decision_id=NEW.basis_decision_id) NOT BETWEEN 1 AND 100 THEN
        RAISE EXCEPTION 'bounded review basis required' USING ERRCODE='23514';
      END IF;
      PERFORM g.id FROM approval_grants g JOIN approval_decisions d ON d.id=g.approval_decision_id
        JOIN approval_requests r ON r.id=d.approval_request_id
        WHERE r.project_id=NEW.project_id AND r.approval_purpose=NEW.approval_purpose
        AND coalesce(r.scientific_conclusion_version_id,r.manuscript_version_id)<>coalesce(NEW.scientific_conclusion_version_id,NEW.manuscript_version_id)
        AND g.status='ACTIVE' ORDER BY g.id FOR UPDATE OF g;
      PERFORM pr216_gate(NEW,NULL);
      IF NOT EXISTS(SELECT 1 FROM projects p JOIN project_memberships m ON m.project_id=p.id
        JOIN project_role_assignments a ON a.membership_id=m.id AND a.actor_id=m.actor_id
        JOIN actors x ON x.id=m.actor_id WHERE p.id=NEW.project_id AND p.lifecycle_status='ACTIVE'
        AND m.actor_id=NEW.requested_by AND m.status='ACTIVE' AND x.retired_at IS NULL
        AND a.role IN ('OWNER','RESEARCHER') AND a.effective_from<=clock_timestamp()
        AND (a.effective_until IS NULL OR clock_timestamp()<a.effective_until)
        AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=x.id
          AND b.status='ACTIVE' AND b.bound_at<=clock_timestamp()
          AND (b.revoked_at IS NULL OR clock_timestamp()<b.revoked_at))) THEN
        RAISE EXCEPTION 'request authority required' USING ERRCODE='P16A1';
      END IF;
      IF EXISTS(SELECT 1 FROM decision_records WHERE id=NEW.basis_decision_id
        AND xmin::text::bigint=pg_current_xact_id()::text::bigint)
        OR EXISTS(SELECT 1 FROM internal_review_records x JOIN decision_basis_reviews b
          ON b.internal_review_record_id=x.id WHERE b.decision_id=NEW.basis_decision_id
          AND x.xmin::text::bigint=pg_current_xact_id()::text::bigint) THEN
        RAISE EXCEPTION 'committed basis required' USING ERRCODE='P16B1';
      END IF;
      NEW.requested_at:=clock_timestamp();
      RETURN NEW;
    END $$;
    CREATE OR REPLACE FUNCTION pr216_decision_guard() RETURNS trigger LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE r approval_requests; digest TEXT;
    BEGIN
      PERFORM b09_preheld();
      PERFORM pg_advisory_xact_lock(hashtextextended('pr216:uuid:'||NEW.id,0));
      SELECT * INTO r FROM approval_requests WHERE id=NEW.approval_request_id;
      IF r.id IS NULL THEN RETURN NEW; END IF;
      PERFORM pr216_gate(r,NEW.decided_by);
      SELECT * INTO r FROM approval_requests WHERE id=NEW.approval_request_id FOR UPDATE;
      IF r.status<>'PENDING' THEN
        RAISE EXCEPTION 'terminal request' USING ERRCODE='P17F3';
      END IF;
      PERFORM pr216_gate(r,NEW.decided_by);
      IF length(NEW.rationale)>16384 OR (NEW.requires_current_author_consent
        AND (r.approval_purpose<>'PREPARE_SUBMISSION' OR NEW.decision<>'APPROVE_WITH_CONDITIONS')) THEN
        RAISE EXCEPTION 'bounded typed conditions required' USING ERRCODE='23514';
      END IF;
      IF NEW.decision='REJECT' THEN
        PERFORM g.id FROM approval_grants g JOIN approval_decisions d ON d.id=g.approval_decision_id
          JOIN approval_requests q ON q.id=d.approval_request_id
          WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose
          AND g.status='ACTIVE' ORDER BY g.id FOR UPDATE OF g;
      END IF;
      PERFORM pr216_gate(r,NEW.decided_by);
      NEW.decided_at:=clock_timestamp();
      IF NEW.valid_until IS NOT NULL AND (NEW.valid_until<=clock_timestamp()
        OR NEW.valid_until>clock_timestamp()+interval '720 hours') THEN
        RAISE EXCEPTION 'finite expiry required' USING ERRCODE='23514';
      END IF;
      digest:=encode(sha256(convert_to(pr216_cjson(jsonb_build_object(
        'type','ApprovalDecision','material_version',1,'approval_request_id',r.id,
        'target',jsonb_build_object('type',CASE WHEN r.manuscript_version_id IS NULL THEN 'ScientificConclusionVersion' ELSE 'ManuscriptVersion' END,
          'id',coalesce(r.scientific_conclusion_version_id,r.manuscript_version_id),'content_hash',r.target_content_hash),
        'decision',NEW.decision,'valid_until',CASE WHEN NEW.valid_until IS NULL THEN NULL ELSE
          to_char(NEW.valid_until AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"') END,
        'requires_current_author_consent',NEW.requires_current_author_consent,
        'rationale',NEW.rationale,'decided_by',jsonb_build_object('type','ActorIdentity',
          'id',NEW.decided_by))), 'UTF8')),'hex');
      IF NEW.content_hash<>digest THEN
        RAISE EXCEPTION 'approval hash mismatch' USING ERRCODE='P17F2';
      END IF; RETURN NEW;
    END $$;
    CREATE OR REPLACE FUNCTION pr216_grant_guard() RETURNS trigger LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
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
            AND q.xmin::text::bigint=pg_current_xact_id()::text::bigint) AND NOT EXISTS (
          SELECT 1 FROM approval_decisions rejected JOIN approval_requests q ON q.id=rejected.approval_request_id
          WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose AND rejected.decision='REJECT'
          AND rejected.xmin::text::bigint=pg_current_xact_id()::text::bigint) THEN
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
          AND xmin::text::bigint=pg_current_xact_id()::text::bigint) THEN
        RAISE EXCEPTION 'exact new grant required' USING ERRCODE='P16G1';
      END IF; RETURN NEW;
    END $$;
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
    CREATE OR REPLACE FUNCTION pr216_complete() RETURNS trigger LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE r approval_requests; did UUID; outcome TEXT;
    BEGIN
      IF TG_TABLE_NAME='approval_requests' THEN
        SELECT * INTO r FROM approval_requests WHERE id=NEW.id;
      ELSIF TG_TABLE_NAME='approval_request_reviews' THEN
        SELECT * INTO r FROM approval_requests WHERE id=NEW.request_id;
      ELSIF TG_TABLE_NAME='approval_grants' THEN
        SELECT q.* INTO r FROM approval_requests q JOIN approval_decisions d
          ON d.approval_request_id=q.id WHERE d.id=NEW.approval_decision_id;
      ELSE
        SELECT * INTO r FROM approval_requests WHERE id=NEW.approval_request_id;
      END IF;
      IF EXISTS((SELECT internal_review_record_id FROM decision_basis_reviews
        WHERE decision_id=r.basis_decision_id) EXCEPT
        (SELECT internal_review_record_id FROM approval_request_reviews WHERE request_id=r.id))
        OR EXISTS((SELECT internal_review_record_id FROM approval_request_reviews
          WHERE request_id=r.id)
          EXCEPT (SELECT internal_review_record_id FROM decision_basis_reviews
            WHERE decision_id=r.basis_decision_id)) THEN
        RAISE EXCEPTION 'complete saved basis required' USING ERRCODE='P16B1';
      END IF;
      SELECT id,decision INTO did,outcome FROM approval_decisions WHERE approval_request_id=r.id;
      IF EXISTS(SELECT 1 FROM approval_request_events e WHERE e.request_id=r.id
        AND e.prior_status IS NULL AND e.xmin::text::bigint=pg_current_xact_id()::text::bigint) THEN
        IF NOT EXISTS(SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id
          JOIN project_role_assignments role ON role.membership_id=m.id AND role.actor_id=m.actor_id
            AND role.project_id=m.project_id
          WHERE a.id=r.requested_by AND a.retired_at IS NULL AND m.project_id=r.project_id
            AND m.status='ACTIVE' AND role.role IN ('OWNER','RESEARCHER')
            AND role.effective_from<=clock_timestamp()
            AND (role.effective_until IS NULL OR clock_timestamp()<role.effective_until)
            AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=a.id AND b.status='ACTIVE'
              AND b.bound_at<=clock_timestamp() AND (b.revoked_at IS NULL OR clock_timestamp()<b.revoked_at))) THEN
          RAISE EXCEPTION 'final request authority required' USING ERRCODE='P16A1';
        END IF;
      END IF;
      IF EXISTS(SELECT 1 FROM approval_decisions d WHERE d.id=did
        AND d.xmin::text::bigint=pg_current_xact_id()::text::bigint
        AND NOT pr216_approver_active(d.decided_by,r.project_id)) THEN
        RAISE EXCEPTION 'final decision authority required' USING ERRCODE='P16A1';
      END IF;
      IF EXISTS(SELECT 1 FROM approval_decisions d WHERE d.id=did
        AND d.xmin::text::bigint=pg_current_xact_id()::text::bigint
        AND d.valid_until IS NOT NULL AND clock_timestamp()>=d.valid_until) THEN
        RAISE EXCEPTION 'final conditional expiry reached' USING ERRCODE='23514';
      END IF;

      IF (r.status='DECIDED') IS DISTINCT FROM (did IS NOT NULL) THEN
        RAISE EXCEPTION 'complete decision history required' USING ERRCODE='P16G1';
      END IF;
      IF did IS NOT NULL AND ((outcome<>'REJECT') IS DISTINCT FROM
        EXISTS(SELECT 1 FROM approval_grants WHERE approval_decision_id=did)) THEN
        RAISE EXCEPTION 'atomic grant required' USING ERRCODE='P16G1';
      END IF; RETURN NULL;
    END $$;

CREATE OR REPLACE FUNCTION pr216_event_insert() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog, public, pg_temp AS $$
DECLARE r approval_requests; d approval_decisions; g approval_grants; owner_xmin bigint;
BEGIN
 IF pg_trigger_depth()<2 THEN
   RAISE EXCEPTION 'events belong to atomic lifecycle change' USING ERRCODE='P17F1';
 END IF;
 IF TG_TABLE_NAME='approval_request_events' THEN
   SELECT q.* INTO r FROM approval_requests q WHERE q.id=NEW.request_id;
   SELECT xmin::text::bigint INTO owner_xmin FROM approval_requests WHERE id=NEW.request_id;
   IF owner_xmin IS DISTINCT FROM pg_current_xact_id()::text::bigint
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
   SELECT xmin::text::bigint INTO owner_xmin FROM approval_grants WHERE id=NEW.grant_id;
   SELECT * INTO d FROM approval_decisions WHERE id=g.approval_decision_id;
   IF owner_xmin IS DISTINCT FROM pg_current_xact_id()::text::bigint
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
END $$;
CREATE CONSTRAINT TRIGGER pr216_complete_grant AFTER INSERT ON approval_grants
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pr216_complete();

"""

DOWNGRADE_SQL = r"""
LOCK TABLE approval_requests,approval_decisions,approval_grants,approval_request_reviews,approval_request_events,approval_grant_events IN ACCESS EXCLUSIVE MODE;
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM approval_requests) OR EXISTS(SELECT 1 FROM approval_decisions) OR EXISTS(SELECT 1 FROM approval_grants) THEN
 RAISE EXCEPTION 'B09 approval history cannot lose guarantees' USING ERRCODE='P17F2'; END IF;
END $$;
DROP TRIGGER pr216_complete_grant ON approval_grants;
ALTER TABLE approval_requests DROP CONSTRAINT ck_b09_request_tuple;
ALTER TABLE approval_grants DROP CONSTRAINT ck_b09_grant_tuple;
ALTER TABLE approval_decisions DROP CONSTRAINT ck_b09_consent_condition;
DROP INDEX uq_b09_pending_conclusion;
DROP INDEX uq_b09_pending_manuscript;
DROP INDEX ix_b09_rejection_scope;
ALTER TABLE approval_requests ADD CHECK(approval_purpose='INTERNAL_SCIENTIFIC_RELEASE'), ADD CHECK(scientific_conclusion_version_id IS NOT NULL);
ALTER TABLE approval_grants ADD CHECK(purpose='INTERNAL_SCIENTIFIC_RELEASE'), ADD CHECK(allowed_command='record_internal_scientific_release');
ALTER TABLE approval_decisions ADD CHECK(NOT requires_current_author_consent);
CREATE UNIQUE INDEX uq_pr216_pending ON approval_requests (project_id,approval_purpose,scientific_conclusion_version_id) WHERE status='PENDING';
    CREATE OR REPLACE FUNCTION pr216_gate(r approval_requests, approver UUID) RETURNS void
      LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE v scientific_conclusion_versions; d decision_records; pid UUID;
    BEGIN
      PERFORM pg_advisory_xact_lock(hashtextextended(
        'pr216:scope:'||r.project_id||':'||'INTERNAL_SCIENTIFIC_RELEASE',0));
      SELECT * INTO v FROM scientific_conclusion_versions
        WHERE id=r.scientific_conclusion_version_id FOR UPDATE;
      LOCK TABLE actor_subject_bindings,
        actors,
        artifact_versions,
        artifacts,
        audit_findings,
        claims,
        correction_records,
        datasets,
        experiment_spec_versions,
        experiment_specs,
        impact_assessments,
        impact_targets,
        literature_evidence,
        literature_evidence_review_events,
        literature_source_project_links,
        literature_sources,
        metric_definition_versions,
        metric_definitions,
        project_membership_events,
        project_memberships,
        project_role_assignments,
        projects,
        run_artifact_inputs,
        run_dataset_inputs,
        runs,
        statistical_result_inputs,
        scientific_conclusions,
        source_versions IN SHARE MODE;
      SELECT project_id INTO pid FROM scientific_conclusions WHERE id=v.scientific_conclusion_id;
      IF pid IS DISTINCT FROM r.project_id OR v.status<>'FROZEN' OR v.frozen_at IS NULL
        OR v.content_hash IS DISTINCT FROM r.target_content_hash
        OR v.hash_scheme IS DISTINCT FROM r.target_hash_scheme THEN
        RAISE EXCEPTION 'frozen exact target required' USING ERRCODE='P16T1';
      END IF;
      IF EXISTS(SELECT 1 FROM approval_decisions x JOIN approval_requests q
        ON q.id=x.approval_request_id WHERE q.project_id=r.project_id
          AND q.approval_purpose=r.approval_purpose AND x.decision='REJECT') THEN
        RAISE EXCEPTION 'reconsideration required' USING ERRCODE='P16R1';
      END IF;
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
        RAISE EXCEPTION 'active project required' USING ERRCODE='P16A1';
      END IF;
      PERFORM pr216_material_gate(r);
      IF d.decided_by IN (SELECT pr216_authors(v.id)) THEN
        RAISE EXCEPTION 'independent basis decider required' USING ERRCODE='P16C1';
      END IF;
      IF approver IS NOT NULL THEN
        IF EXISTS(SELECT 1 FROM approval_requests q WHERE q.project_id=r.project_id
          AND q.approval_purpose=r.approval_purpose
          AND q.scientific_conclusion_version_id<>r.scientific_conclusion_version_id
          AND q.requested_at>r.requested_at) THEN
          RAISE EXCEPTION 'newer approval target selected' USING ERRCODE='P16T1';
        END IF;
        IF NOT pr216_approver_active(approver,r.project_id) THEN
          RAISE EXCEPTION 'human approver required' USING ERRCODE='P16A1';
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
    CREATE OR REPLACE FUNCTION pr216_request_guard() RETURNS trigger LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    BEGIN
      IF TG_OP='DELETE' THEN
        RAISE EXCEPTION 'immutable request' USING ERRCODE='P17F1';
      ELSIF TG_OP='UPDATE' THEN
        IF (to_jsonb(NEW)-'status') IS DISTINCT FROM (to_jsonb(OLD)-'status')
          OR OLD.status<>'PENDING' OR NEW.status<>'DECIDED'
          OR NOT EXISTS(SELECT 1 FROM approval_decisions WHERE approval_request_id=OLD.id) THEN
          RAISE EXCEPTION 'immutable request material' USING ERRCODE='P17F1';
        END IF; RETURN NEW;
      END IF;
      IF NEW.status<>'PENDING' THEN
        RAISE EXCEPTION 'initial pending required' USING ERRCODE='P16G1';
      END IF;
      PERFORM pr216_gate(NEW,NULL);
      IF NOT EXISTS(SELECT 1 FROM projects p JOIN project_memberships m ON m.project_id=p.id
        JOIN project_role_assignments a ON a.membership_id=m.id AND a.actor_id=m.actor_id
        JOIN actors x ON x.id=m.actor_id WHERE p.id=NEW.project_id AND p.lifecycle_status='ACTIVE'
        AND m.actor_id=NEW.requested_by AND m.status='ACTIVE' AND x.retired_at IS NULL
        AND a.role IN ('OWNER','RESEARCHER') AND a.effective_from<=clock_timestamp()
        AND (a.effective_until IS NULL OR clock_timestamp()<a.effective_until)
        AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=x.id
          AND b.status='ACTIVE' AND b.bound_at<=clock_timestamp()
          AND (b.revoked_at IS NULL OR clock_timestamp()<b.revoked_at))) THEN
        RAISE EXCEPTION 'request authority required' USING ERRCODE='P16A1';
      END IF;
      IF EXISTS(SELECT 1 FROM decision_records WHERE id=NEW.basis_decision_id
        AND xmin::text::bigint=pg_current_xact_id()::text::bigint)
        OR EXISTS(SELECT 1 FROM internal_review_records x JOIN decision_basis_reviews b
          ON b.internal_review_record_id=x.id WHERE b.decision_id=NEW.basis_decision_id
          AND x.xmin::text::bigint=pg_current_xact_id()::text::bigint) THEN
        RAISE EXCEPTION 'committed basis required' USING ERRCODE='P16B1';
      END IF;
      NEW.requested_at:=clock_timestamp();
      RETURN NEW;
    END $$;
    CREATE OR REPLACE FUNCTION pr216_decision_guard() RETURNS trigger LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE r approval_requests; digest TEXT;
    BEGIN
      SELECT * INTO r FROM approval_requests WHERE id=NEW.approval_request_id;
      IF r.id IS NULL THEN RETURN NEW; END IF;
      PERFORM pr216_gate(r,NEW.decided_by);
      SELECT * INTO r FROM approval_requests WHERE id=NEW.approval_request_id FOR UPDATE;
      IF r.status<>'PENDING' THEN
        RAISE EXCEPTION 'terminal request' USING ERRCODE='P17F3';
      END IF;
      PERFORM pr216_gate(r,NEW.decided_by);
      NEW.decided_at:=clock_timestamp();
      IF NEW.valid_until IS NOT NULL AND (NEW.valid_until<=clock_timestamp()
        OR NEW.valid_until>clock_timestamp()+interval '720 hours') THEN
        RAISE EXCEPTION 'finite expiry required' USING ERRCODE='23514';
      END IF;
      digest:=encode(sha256(convert_to(pr216_cjson(jsonb_build_object(
        'type','ApprovalDecision','material_version',1,'approval_request_id',r.id,
        'target',jsonb_build_object('type','ScientificConclusionVersion',
          'id',r.scientific_conclusion_version_id,'content_hash',r.target_content_hash),
        'decision',NEW.decision,'valid_until',CASE WHEN NEW.valid_until IS NULL THEN NULL ELSE
          to_char(NEW.valid_until AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"') END,
        'requires_current_author_consent',NEW.requires_current_author_consent,
        'rationale',NEW.rationale,'decided_by',jsonb_build_object('type','ActorIdentity',
          'id',NEW.decided_by))), 'UTF8')),'hex');
      IF NEW.content_hash<>digest THEN
        RAISE EXCEPTION 'approval hash mismatch' USING ERRCODE='P17F2';
      END IF; RETURN NEW;
    END $$;
    CREATE OR REPLACE FUNCTION pr216_grant_guard() RETURNS trigger LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
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
            AND q.scientific_conclusion_version_id<>r.scientific_conclusion_version_id
            AND q.xmin::text::bigint=pg_current_xact_id()::text::bigint) THEN
          RAISE EXCEPTION 'contracted stale cause required' USING ERRCODE='P17F1';
        END IF;
        IF (to_jsonb(NEW)-'status') IS DISTINCT FROM (to_jsonb(OLD)-'status')
          OR OLD.status<>'ACTIVE' OR NEW.status<>'STALE' THEN
          RAISE EXCEPTION 'monotonic grant only' USING ERRCODE='P17F1';
        END IF; RETURN NEW;
      END IF;
      SELECT * INTO d FROM approval_decisions WHERE id=NEW.approval_decision_id;
      SELECT * INTO r FROM approval_requests WHERE id=d.approval_request_id;
      IF d.decision NOT IN ('APPROVE','APPROVE_WITH_CONDITIONS') OR r.id IS NULL
        OR NEW.project_id<>r.project_id OR NEW.purpose<>r.approval_purpose
        OR NOT pr216_approver_active(d.decided_by,r.project_id)
        OR clock_timestamp()>=NEW.valid_until
        OR NEW.status<>'ACTIVE' OR NEW.valid_until IS DISTINCT FROM
          coalesce(d.valid_until,d.decided_at+interval '720 hours')
        OR NOT EXISTS(SELECT 1 FROM approval_decisions WHERE id=d.id
          AND xmin::text::bigint=pg_current_xact_id()::text::bigint) THEN
        RAISE EXCEPTION 'exact new grant required' USING ERRCODE='P16G1';
      END IF; RETURN NEW;
    END $$;
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
            AND q.scientific_conclusion_version_id<>NEW.scientific_conclusion_version_id
            AND g.status='ACTIVE';
      ELSIF TG_TABLE_NAME='approval_decisions' THEN
        UPDATE approval_requests SET status='DECIDED' WHERE id=NEW.approval_request_id;
        INSERT INTO approval_request_events(request_id,prior_status,new_status,
          actor_id,occurred_at,reason)
          VALUES(NEW.approval_request_id,'PENDING','DECIDED',NEW.decided_by,NEW.decided_at,
            'decision recorded');
      ELSE
        SELECT * INTO d FROM approval_decisions WHERE id=NEW.approval_decision_id;
        INSERT INTO approval_grant_events(grant_id,prior_status,new_status,
          actor_id,occurred_at,reason)
          VALUES(NEW.id,CASE WHEN TG_OP='INSERT' THEN NULL ELSE OLD.status END,NEW.status,
            d.decided_by,clock_timestamp(),
            CASE WHEN TG_OP='INSERT' THEN 'grant created' ELSE 'grant stale' END);
      END IF; RETURN NULL;
    END $$;
    CREATE OR REPLACE FUNCTION pr216_complete() RETURNS trigger LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE r approval_requests; did UUID; outcome TEXT;
    BEGIN
      IF TG_TABLE_NAME='approval_requests' THEN
        SELECT * INTO r FROM approval_requests WHERE id=NEW.id;
      ELSIF TG_TABLE_NAME='approval_request_reviews' THEN
        SELECT * INTO r FROM approval_requests WHERE id=NEW.request_id;
      ELSE
        SELECT * INTO r FROM approval_requests WHERE id=NEW.approval_request_id;
      END IF;
      IF EXISTS((SELECT internal_review_record_id FROM decision_basis_reviews
        WHERE decision_id=r.basis_decision_id) EXCEPT
        (SELECT internal_review_record_id FROM approval_request_reviews WHERE request_id=r.id))
        OR EXISTS((SELECT internal_review_record_id FROM approval_request_reviews
          WHERE request_id=r.id)
          EXCEPT (SELECT internal_review_record_id FROM decision_basis_reviews
            WHERE decision_id=r.basis_decision_id)) THEN
        RAISE EXCEPTION 'complete saved basis required' USING ERRCODE='P16B1';
      END IF;
      SELECT id,decision INTO did,outcome FROM approval_decisions WHERE approval_request_id=r.id;
      IF (r.status='DECIDED') IS DISTINCT FROM (did IS NOT NULL) THEN
        RAISE EXCEPTION 'complete decision history required' USING ERRCODE='P16G1';
      END IF;
      IF did IS NOT NULL AND ((outcome<>'REJECT') IS DISTINCT FROM
        EXISTS(SELECT 1 FROM approval_grants WHERE approval_decision_id=did)) THEN
        RAISE EXCEPTION 'atomic grant required' USING ERRCODE='P16G1';
      END IF; RETURN NULL;
    END $$;
CREATE OR REPLACE FUNCTION pr216_event_insert() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog, public, pg_temp AS $$
BEGIN
 IF pg_trigger_depth()<2 THEN
  RAISE EXCEPTION 'events belong to atomic lifecycle change' USING ERRCODE='P17F1';
 END IF;
 RETURN NEW;
END $$;
DROP FUNCTION b09_preheld();
"""
