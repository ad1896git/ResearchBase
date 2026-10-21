"""B14a exact frozen manuscript entry, with retained atomic lifecycle history."""

# ruff: noqa: E501
from alembic import op

revision = "0062_b14a_publication_entry"
down_revision = "0061_b16_consent_withdrawal"
branch_labels = None
depends_on = None

UPGRADE_SQL = r"""
LOCK TABLE publications,publication_lifecycle_events,manuscript_versions IN ACCESS EXCLUSIVE MODE;
DO $$ DECLARE p publications; m manuscript_versions; c text;
BEGIN
 FOR p IN SELECT * FROM publications LOOP
  IF p.lifecycle_status<>'DRAFTING' OR (SELECT count(*) FROM publication_lifecycle_events WHERE publication_id=p.id)<>1
   OR NOT EXISTS(SELECT 1 FROM publication_lifecycle_events e WHERE e.publication_id=p.id AND e.prior_status IS NULL AND e.new_status='DRAFTING' AND e.actor_id=p.created_by AND e.occurred_at=p.created_at AND isfinite(e.occurred_at) AND e.basis_decision_id IS NULL AND e.basis_grant_consumption_id IS NULL) THEN
   RAISE EXCEPTION 'corrupt legacy publication history' USING ERRCODE='P14P1'; END IF;
 END LOOP;
 IF EXISTS(SELECT 1 FROM publications pub WHERE pub.current_manuscript_version_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM manuscript_versions mv WHERE mv.id=pub.current_manuscript_version_id AND mv.publication_id=pub.id AND mv.status='FROZEN' AND mv.content_hash IS NOT NULL AND mv.placement_set_hash IS NOT NULL AND mv.frozen_at IS NOT NULL)) THEN
  RAISE EXCEPTION 'corrupt legacy current pointer' USING ERRCODE='P14P1'; END IF;
 FOR m IN SELECT * FROM manuscript_versions LOOP PERFORM b04_verify_structure(m.id); END LOOP;
 FOREACH c IN ARRAY ARRAY['publications_lifecycle_status_check','publication_lifecycle_events_new_status_check','publication_lifecycle_events_check','publication_lifecycle_events_publication_id_key'] LOOP
  IF NOT EXISTS(SELECT 1 FROM pg_constraint WHERE conname=c AND conrelid=CASE WHEN c='publications_lifecycle_status_check' THEN 'publications'::regclass ELSE 'publication_lifecycle_events'::regclass END AND contype=CASE WHEN c='publication_lifecycle_events_publication_id_key' THEN 'u'::"char" ELSE 'c'::"char" END) THEN
   RAISE EXCEPTION 'unexpected predecessor constraint inventory'; END IF;
 END LOOP;
END $$;
ALTER TABLE publications DROP CONSTRAINT publications_lifecycle_status_check;
ALTER TABLE publication_lifecycle_events DROP CONSTRAINT publication_lifecycle_events_new_status_check,
 DROP CONSTRAINT publication_lifecycle_events_check,DROP CONSTRAINT publication_lifecycle_events_publication_id_key;
ALTER TABLE publications ADD CONSTRAINT ck_b14a_publication_status CHECK(lifecycle_status IN ('DRAFTING','INTERNAL_REVIEW'));
ALTER TABLE publication_lifecycle_events ADD COLUMN manuscript_version_id UUID,
 ADD CONSTRAINT fk_b14a_entry_same_parent FOREIGN KEY(publication_id,manuscript_version_id) REFERENCES manuscript_versions(publication_id,id) ON DELETE RESTRICT,
 ADD CONSTRAINT ck_b14a_event_tuple CHECK(
 (prior_status IS NULL AND new_status='DRAFTING' AND manuscript_version_id IS NULL AND basis_decision_id IS NULL AND basis_grant_consumption_id IS NULL) OR
 (prior_status IS NOT DISTINCT FROM 'DRAFTING' AND new_status='INTERNAL_REVIEW' AND manuscript_version_id IS NOT NULL AND basis_decision_id IS NULL AND basis_grant_consumption_id IS NULL)),
 ADD CONSTRAINT ck_b14a_event_time CHECK(isfinite(occurred_at));
CREATE UNIQUE INDEX uq_b14a_initial_event ON publication_lifecycle_events(publication_id) WHERE prior_status IS NULL;
CREATE UNIQUE INDEX uq_b14a_review_entry ON publication_lifecycle_events(publication_id) WHERE new_status='INTERNAL_REVIEW';
CREATE INDEX ix_b14a_entry_manuscript ON publication_lifecycle_events(manuscript_version_id) WHERE manuscript_version_id IS NOT NULL;
CREATE FUNCTION b14a_preheld() RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
BEGIN
 IF current_setting('transaction_isolation')<>'read committed'
 OR EXISTS(SELECT 1 FROM unnest(ARRAY['actor_subject_bindings','actors','artifact_versions','artifacts','audit_findings','claim_versions','claims','correction_records','dataset_snapshots','datasets','evidence_relations','experiment_spec_versions','experiment_specs','impact_assessments','impact_targets','internal_review_records','literature_evidence','literature_evidence_relations','literature_evidence_review_events','literature_source_project_links','literature_sources','literature_support_snapshots','manuscript_artifact_placements','manuscript_citation_placements','manuscript_claim_placements','manuscript_versions','measurements','metric_definition_versions','metric_definitions','project_membership_events','project_memberships','project_role_assignments','projects','review_issue_events','review_issues','run_artifact_inputs','run_dataset_inputs','runs','scientific_conclusion_claim_inputs','scientific_conclusion_literature_inputs','scientific_conclusion_versions','scientific_conclusions','source_versions','statistical_result_inputs','statistical_results','approval_decisions','approval_request_reviews','approval_requests']) n(name) WHERE NOT EXISTS(
 SELECT 1 FROM pg_locks l WHERE l.pid=pg_backend_pid() AND l.locktype='relation'
 AND l.relation=to_regclass('public.'||n.name) AND l.mode='ShareLock' AND l.granted))
 OR NOT EXISTS(SELECT 1 FROM pg_locks l WHERE l.pid=pg_backend_pid() AND l.locktype='relation'
 AND l.relation='public.publications'::regclass AND l.mode='ShareRowExclusiveLock' AND l.granted) THEN
 RAISE EXCEPTION 'entry requires preheld snapshot inventory' USING ERRCODE='P14C1'; END IF;
END $$;

CREATE FUNCTION b14a_admission(mid UUID,pid UUID) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE iid UUID; r internal_review_records; target_hash text; kind text; tid UUID;
BEGIN
 IF NOT EXISTS(SELECT 1 FROM manuscript_versions m JOIN publications p ON p.id=m.publication_id WHERE m.id=mid AND p.project_id=pid AND m.status='FROZEN' AND m.frozen_at IS NOT NULL AND m.placement_set_hash IS NOT NULL AND m.content_hash IS NOT NULL AND m.hash_scheme='sha256-cjson-v1') THEN
 RAISE EXCEPTION 'sealed exact manuscript required' USING ERRCODE='P14P1'; END IF;
 PERFORM b04_verify_structure(mid);
 FOR r IN SELECT * FROM b11_applicable_reviews(mid,pid) LOOP
  IF r.manuscript_version_id IS NOT NULL THEN
   SELECT content_hash INTO target_hash FROM manuscript_versions WHERE id=r.manuscript_version_id; kind:='ManuscriptVersion'; tid:=r.manuscript_version_id;
  ELSIF r.claim_version_id IS NOT NULL THEN
   SELECT content_hash INTO target_hash FROM claim_versions WHERE id=r.claim_version_id; kind:='ClaimVersion'; tid:=r.claim_version_id;
  ELSIF r.scientific_conclusion_version_id IS NOT NULL THEN
   SELECT content_hash INTO target_hash FROM scientific_conclusion_versions WHERE id=r.scientific_conclusion_version_id; kind:='ScientificConclusionVersion'; tid:=r.scientific_conclusion_version_id;
  ELSE
   SELECT content_hash INTO target_hash FROM artifact_versions WHERE id=r.artifact_version_id; kind:='ArtifactVersion'; tid:=r.artifact_version_id;
  END IF;
  IF r.hash_scheme<>'sha256-cjson-v1' OR r.target_content_hash IS DISTINCT FROM target_hash
   OR r.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','InternalReviewRecord','material_version',1,'project_id',r.project_id,'target',jsonb_build_object('type',kind,'id',tid,'content_hash',target_hash),'reviewer_actor_id',r.reviewer_actor_id,'review_type',r.review_type,'recommendation',r.recommendation,'summary',r.summary))
   OR EXISTS(SELECT 1 FROM claim_versions WHERE id=r.claim_version_id AND created_by=r.reviewer_actor_id)
   OR EXISTS(SELECT 1 FROM scientific_conclusion_versions WHERE id=r.scientific_conclusion_version_id AND created_by=r.reviewer_actor_id)
   OR EXISTS(SELECT 1 FROM artifact_versions WHERE id=r.artifact_version_id AND created_by=r.reviewer_actor_id)
   OR (r.manuscript_version_id IS NOT NULL AND r.reviewer_actor_id IN (SELECT b11_authors(mid)))
   OR NOT EXISTS(SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id JOIN project_role_assignments role ON role.membership_id=m.id AND role.actor_id=m.actor_id AND role.project_id=m.project_id
    WHERE a.id=r.reviewer_actor_id AND a.actor_type='HUMAN' AND a.created_at<=r.created_at AND (a.retired_at IS NULL OR r.created_at<a.retired_at) AND m.project_id=pid AND m.started_at<=r.created_at
    AND (SELECT e.new_status FROM project_membership_events e WHERE e.membership_id=m.id AND e.occurred_at<=r.created_at ORDER BY e.occurred_at DESC,e.id DESC LIMIT 1)='ACTIVE'
    AND role.role IN ('OWNER','REVIEWER') AND role.effective_from<=r.created_at AND (role.effective_until IS NULL OR r.created_at<role.effective_until)
    AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=a.id AND b.bound_at<=r.created_at AND (b.revoked_at IS NULL OR r.created_at<b.revoked_at))) THEN
   RAISE EXCEPTION 'corrupt applicable review' USING ERRCODE='P14P1'; END IF;
 END LOOP;
 FOR iid IN SELECT i.id FROM review_issues i JOIN b11_applicable_reviews(mid,pid) applicable ON applicable.id=i.review_record_id LOOP PERFORM b08_check_history(iid); END LOOP;
 IF EXISTS(SELECT 1 FROM review_issues i JOIN b11_applicable_reviews(mid,pid) applicable ON applicable.id=i.review_record_id WHERE i.status='OPEN' AND i.severity='BLOCKING') THEN
 RAISE EXCEPTION 'applicable open blocker' USING ERRCODE='P14B1'; END IF;
END $$;
CREATE OR REPLACE FUNCTION pr212_publication_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP='DELETE' THEN
        RAISE EXCEPTION 'publication history retained' USING ERRCODE='P17D1';
      END IF;
      IF TG_OP='INSERT' THEN
        IF NEW.lifecycle_status<>'DRAFTING' OR NEW.row_version<>1
           OR NEW.current_manuscript_version_id IS NOT NULL THEN
          RAISE EXCEPTION 'publication starts drafting' USING ERRCODE='P17D2';
        END IF;
        RETURN NEW;
      END IF;
      IF OLD.lifecycle_status='DRAFTING' AND NEW.lifecycle_status='DRAFTING'
        AND OLD.current_manuscript_version_id IS NULL AND NEW.current_manuscript_version_id IS NOT NULL
        AND NEW.row_version=OLD.row_version+1
        AND (to_jsonb(NEW)-ARRAY['current_manuscript_version_id','row_version'])
          IS NOT DISTINCT FROM (to_jsonb(OLD)-ARRAY['current_manuscript_version_id','row_version'])
        AND EXISTS (SELECT 1 FROM manuscript_versions m WHERE m.id=NEW.current_manuscript_version_id
          AND m.publication_id=NEW.id AND m.status='FROZEN' AND m.content_hash IS NOT NULL
          AND m.placement_set_hash IS NOT NULL AND m.frozen_at IS NOT NULL) THEN RETURN NEW; END IF;
      IF OLD.lifecycle_status='DRAFTING' AND NEW.lifecycle_status='INTERNAL_REVIEW'
        AND OLD.current_manuscript_version_id IS NOT NULL
        AND NEW.row_version::bigint=OLD.row_version::bigint+1
        AND (to_jsonb(NEW)-ARRAY['lifecycle_status','row_version']) IS NOT DISTINCT FROM
            (to_jsonb(OLD)-ARRAY['lifecycle_status','row_version']) THEN
        PERFORM b14a_preheld();
        PERFORM b14a_admission(NEW.current_manuscript_version_id,NEW.project_id);
        RETURN NEW;
      END IF;
      RAISE EXCEPTION 'invalid manuscript pointer transition' USING ERRCODE='P04M2';
    END $$;
CREATE FUNCTION b14a_entry_event_guard() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE p publications; m manuscript_versions;
BEGIN
 SELECT * INTO p FROM publications WHERE id=NEW.publication_id;
 IF NEW.prior_status IS NULL THEN
  IF NOT EXISTS(SELECT 1 FROM publications WHERE id=p.id AND xmin=pg_current_xact_id()::xid)
   OR p.lifecycle_status<>'DRAFTING' OR NEW.new_status<>'DRAFTING' OR NEW.actor_id IS DISTINCT FROM p.created_by OR NEW.occurred_at IS DISTINCT FROM p.created_at THEN
   RAISE EXCEPTION 'creation event belongs to new parent' USING ERRCODE='P14I1'; END IF;
  RETURN NEW;
 END IF;
 PERFORM b14a_preheld();
 SELECT * INTO m FROM manuscript_versions WHERE id=NEW.manuscript_version_id;
 IF p.lifecycle_status IS DISTINCT FROM 'INTERNAL_REVIEW'
  OR NOT EXISTS(SELECT 1 FROM publications WHERE id=p.id AND xmin=pg_current_xact_id()::xid)
  OR EXISTS(SELECT 1 FROM publication_lifecycle_events WHERE publication_id=p.id AND new_status='INTERNAL_REVIEW') THEN
  RAISE EXCEPTION 'entry event belongs to new transition' USING ERRCODE='P14I1'; END IF;
 IF m.id IS NULL OR m.publication_id IS DISTINCT FROM p.id OR p.current_manuscript_version_id IS DISTINCT FROM m.id OR m.status<>'FROZEN'
  OR NEW.occurred_at<m.frozen_at OR NEW.occurred_at>clock_timestamp()
  OR NOT EXISTS(SELECT 1 FROM publication_lifecycle_events WHERE publication_id=p.id AND prior_status IS NULL AND occurred_at<=NEW.occurred_at) THEN
  RAISE EXCEPTION 'entry target or chronology mismatch' USING ERRCODE='P14P1'; END IF;
 IF NOT b13_authorized(NEW.actor_id,p.project_id,ARRAY['OWNER','RESEARCHER']) OR NOT EXISTS(SELECT 1 FROM projects WHERE id=p.project_id AND lifecycle_status='ACTIVE') THEN
  RAISE EXCEPTION 'entry authority unavailable' USING ERRCODE='P14A1'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER b14a_entry_event_guard BEFORE INSERT ON publication_lifecycle_events FOR EACH ROW EXECUTE FUNCTION b14a_entry_event_guard();
CREATE FUNCTION b14a_verify_entry(pid UUID) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE p publications; e publication_lifecycle_events; m manuscript_versions;
BEGIN
 SELECT * INTO p FROM publications WHERE id=pid;
 IF p.id IS NULL OR (SELECT count(*) FROM publication_lifecycle_events WHERE publication_id=pid AND prior_status IS NULL)<>1
 OR NOT EXISTS(SELECT 1 FROM publication_lifecycle_events WHERE publication_id=pid AND prior_status IS NULL AND new_status='DRAFTING' AND actor_id=p.created_by AND occurred_at=p.created_at AND manuscript_version_id IS NULL AND basis_decision_id IS NULL AND basis_grant_consumption_id IS NULL) THEN
 RAISE EXCEPTION 'complete initial history required' USING ERRCODE='P14P1'; END IF;
 SELECT * INTO e FROM publication_lifecycle_events WHERE publication_id=pid AND new_status='INTERNAL_REVIEW';
 IF p.lifecycle_status='DRAFTING' THEN
  IF e.id IS NOT NULL THEN RAISE EXCEPTION 'event without transition' USING ERRCODE='P14P1'; END IF;
  RETURN;
 END IF;
 SELECT * INTO m FROM manuscript_versions WHERE id=e.manuscript_version_id;
 IF p.lifecycle_status<>'INTERNAL_REVIEW' OR e.id IS NULL OR e.prior_status IS DISTINCT FROM 'DRAFTING'
 OR m.id IS NULL OR m.publication_id IS DISTINCT FROM pid OR m.status<>'FROZEN' OR m.frozen_at IS NULL
 OR e.manuscript_version_id IS DISTINCT FROM p.current_manuscript_version_id
 OR e.occurred_at<m.frozen_at OR e.occurred_at<p.created_at OR e.occurred_at>clock_timestamp()
 OR e.basis_decision_id IS NOT NULL OR e.basis_grant_consumption_id IS NOT NULL THEN
 RAISE EXCEPTION 'complete exact entry graph required' USING ERRCODE='P14P1'; END IF;
 PERFORM b04_verify_structure(m.id);
 IF EXISTS(SELECT 1 FROM publication_lifecycle_events WHERE id=e.id AND xmin=pg_current_xact_id()::xid) THEN
  IF NOT EXISTS(SELECT 1 FROM publications WHERE id=pid AND xmin=pg_current_xact_id()::xid) THEN
   RAISE EXCEPTION 'same transaction transition required' USING ERRCODE='P14I1'; END IF;
  PERFORM b14a_preheld(); PERFORM b14a_admission(m.id,p.project_id);
  IF NOT b13_authorized(e.actor_id,p.project_id,ARRAY['OWNER','RESEARCHER']) OR NOT EXISTS(SELECT 1 FROM projects WHERE id=p.project_id AND lifecycle_status='ACTIVE') THEN
   RAISE EXCEPTION 'final entry authority unavailable' USING ERRCODE='P14A1'; END IF;
 ELSIF EXISTS(SELECT 1 FROM publications WHERE id=pid AND xmin=pg_current_xact_id()::xid) THEN
  RAISE EXCEPTION 'old event cannot complete new transition' USING ERRCODE='P14I1';
 END IF;
END $$;
CREATE FUNCTION b14a_complete_graph() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
BEGIN
 IF TG_TABLE_NAME='publications' THEN
  PERFORM b14a_verify_entry(NEW.id);
 ELSE
  PERFORM b14a_verify_entry(NEW.publication_id);
 END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER b14a_complete_publication AFTER INSERT OR UPDATE ON publications DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b14a_complete_graph();
CREATE CONSTRAINT TRIGGER b14a_complete_entry_event AFTER INSERT ON publication_lifecycle_events DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b14a_complete_graph();
"""

DOWNGRADE_SQL = r"""
LOCK TABLE publications,publication_lifecycle_events,manuscript_versions IN ACCESS EXCLUSIVE MODE;
DO $$ BEGIN IF EXISTS(SELECT 1 FROM publication_lifecycle_events WHERE new_status<>'DRAFTING' OR manuscript_version_id IS NOT NULL) OR EXISTS(SELECT 1 FROM publications WHERE lifecycle_status<>'DRAFTING') THEN
 RAISE EXCEPTION 'entry history retained' USING ERRCODE='P14I1'; END IF; END $$;
DROP TRIGGER b14a_complete_publication ON publications;
DROP TRIGGER b14a_complete_entry_event ON publication_lifecycle_events;
DROP TRIGGER b14a_entry_event_guard ON publication_lifecycle_events;
DROP FUNCTION b14a_complete_graph(); DROP FUNCTION b14a_verify_entry(UUID); DROP FUNCTION b14a_entry_event_guard();
DROP INDEX ix_b14a_entry_manuscript; DROP INDEX uq_b14a_initial_event; DROP INDEX uq_b14a_review_entry;
ALTER TABLE publication_lifecycle_events DROP CONSTRAINT fk_b14a_entry_same_parent,DROP CONSTRAINT ck_b14a_event_tuple,DROP CONSTRAINT ck_b14a_event_time,DROP COLUMN manuscript_version_id;
ALTER TABLE publications DROP CONSTRAINT ck_b14a_publication_status;
ALTER TABLE publications ADD CONSTRAINT publications_lifecycle_status_check CHECK(lifecycle_status='DRAFTING');
ALTER TABLE publication_lifecycle_events ADD CONSTRAINT publication_lifecycle_events_new_status_check CHECK(new_status='DRAFTING'), ADD CONSTRAINT publication_lifecycle_events_check CHECK(prior_status IS NULL AND basis_decision_id IS NULL AND basis_grant_consumption_id IS NULL), ADD CONSTRAINT publication_lifecycle_events_publication_id_key UNIQUE(publication_id);
CREATE OR REPLACE FUNCTION pr212_publication_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP='DELETE' THEN
        RAISE EXCEPTION 'publication history retained' USING ERRCODE='P17D1';
      END IF;
      IF TG_OP='INSERT' THEN
        IF NEW.lifecycle_status<>'DRAFTING' OR NEW.row_version<>1
           OR NEW.current_manuscript_version_id IS NOT NULL THEN
          RAISE EXCEPTION 'publication starts drafting' USING ERRCODE='P17D2';
        END IF;
        RETURN NEW;
      END IF;
      IF OLD.lifecycle_status='DRAFTING' AND NEW.lifecycle_status='DRAFTING'
        AND OLD.current_manuscript_version_id IS NULL AND NEW.current_manuscript_version_id IS NOT NULL
        AND NEW.row_version=OLD.row_version+1
        AND (to_jsonb(NEW)-ARRAY['current_manuscript_version_id','row_version'])
          IS NOT DISTINCT FROM (to_jsonb(OLD)-ARRAY['current_manuscript_version_id','row_version'])
        AND EXISTS (SELECT 1 FROM manuscript_versions m WHERE m.id=NEW.current_manuscript_version_id
          AND m.publication_id=NEW.id AND m.status='FROZEN' AND m.content_hash IS NOT NULL
          AND m.placement_set_hash IS NOT NULL AND m.frozen_at IS NOT NULL) THEN RETURN NEW; END IF;
      RAISE EXCEPTION 'invalid manuscript pointer transition' USING ERRCODE='P04M2';
    END $$;
DROP FUNCTION b14a_admission(UUID,UUID); DROP FUNCTION b14a_preheld();
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
