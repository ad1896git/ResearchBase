"""B10 owner-approved first conclusion rejection reconsideration slice."""

# Frozen forward/restoration SQL; historical migrations remain untouched.
# ruff: noqa: E501
from alembic import op

revision = "0056_b10_reconsideration"
down_revision = "0055_b09_approval_tuples"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)


UPGRADE_SQL = r"""

LOCK TABLE decision_records,decision_basis_conclusions,decision_basis_reviews,approval_requests,approval_decisions,revision_actions IN ACCESS EXCLUSIVE MODE;
ALTER TABLE decision_records DROP CONSTRAINT ck_b11_decision_policy;
ALTER TABLE approval_requests DROP CONSTRAINT approval_requests_prior_rejected_request_id_check;
ALTER TABLE approval_requests DROP CONSTRAINT approval_requests_reconsideration_decision_id_check;
CREATE TABLE decision_basis_approval_decisions (
 decision_id UUID NOT NULL,
 approval_decision_id UUID NOT NULL,
 ordinal INTEGER NOT NULL,
 CONSTRAINT pk_b10_rejection_basis PRIMARY KEY(decision_id,approval_decision_id),
 CONSTRAINT fk_b10_rejection_decision FOREIGN KEY(decision_id)
  REFERENCES decision_records(id) ON DELETE RESTRICT,
 CONSTRAINT fk_b10_rejection_approval FOREIGN KEY(approval_decision_id)
  REFERENCES approval_decisions(id) ON DELETE RESTRICT,
 CONSTRAINT ck_b10_rejection_ordinal CHECK(ordinal>=0),
 CONSTRAINT uq_b10_rejection_ordinal UNIQUE(decision_id,ordinal)
);
CREATE TABLE decision_basis_revision_actions (
 decision_id UUID NOT NULL,
 revision_action_id UUID NOT NULL,
 ordinal INTEGER NOT NULL,
 CONSTRAINT pk_b10_revision_basis PRIMARY KEY(decision_id,revision_action_id),
 CONSTRAINT fk_b10_revision_decision FOREIGN KEY(decision_id)
  REFERENCES decision_records(id) ON DELETE RESTRICT,
 CONSTRAINT fk_b10_revision_action FOREIGN KEY(revision_action_id)
  REFERENCES revision_actions(id) ON DELETE RESTRICT,
 CONSTRAINT ck_b10_revision_ordinal CHECK(ordinal>=0),
 CONSTRAINT uq_b10_revision_ordinal UNIQUE(decision_id,ordinal)
);
CREATE INDEX ix_b10_rejection_reverse
 ON decision_basis_approval_decisions(approval_decision_id);
CREATE INDEX ix_b10_revision_reverse
 ON decision_basis_revision_actions(revision_action_id);
ALTER TABLE approval_requests ADD CONSTRAINT ck_b10_request_links CHECK
 ((prior_rejected_request_id IS NULL)=(reconsideration_decision_id IS NULL));
CREATE UNIQUE INDEX uq_b10_successor_reconsideration
 ON approval_requests(reconsideration_decision_id)
 WHERE reconsideration_decision_id IS NOT NULL;
ALTER TABLE decision_records ADD CONSTRAINT ck_b10_decision_pair CHECK (
 (decision_type='INTERNAL_SCIENTIFIC_RELEASE' AND decision='PROCEED') OR
 (decision_type='REVISION_RESPONSE' AND decision IN ('REQUIRE_CHANGE','ACCEPT_NO_CHANGE')) OR
 (decision_type='READY_FOR_SUBMISSION' AND decision='PROCEED') OR
 (decision_type='RECONSIDER_REJECTION'
  AND decision IN ('REVISED_TARGET','CORRECTED_REVIEW')));

ALTER TABLE decision_records ADD CONSTRAINT ck_b10_text_bounds CHECK (
 decision_type<>'RECONSIDER_REJECTION' OR
 (question=normalize(question,NFC) AND question='Reconsider rejection for INTERNAL_SCIENTIFIC_RELEASE'
 AND rationale=normalize(rationale,NFC) AND length(btrim(translate(rationale,U&'\0009\000A\000B\000C\000D\001C\001D\001E\001F\0020\0085\00A0\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200A\2028\2029\202F\205F\3000',repeat(' ',29))))>0 AND length(rationale)<=16384));
ALTER TABLE decision_records ADD CONSTRAINT ck_b10_finite_time CHECK (
 decision_type<>'RECONSIDER_REJECTION' OR isfinite(decided_at));
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
CREATE FUNCTION b10_material_gate(r approval_requests) RETURNS void LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE v scientific_conclusion_versions; d decision_records;
      review_row internal_review_records;
      basis JSONB; claims JSONB; literature JSONB; support TEXT; cv claim_versions;
      basis_before TIMESTAMPTZ;
    BEGIN
      basis_before:=clock_timestamp();
      IF EXISTS(SELECT 1 FROM approval_requests WHERE id=r.id) THEN
        basis_before:=least(basis_before,r.requested_at);
      END IF;
      PERFORM pr216_facts(r.scientific_conclusion_version_id,r.project_id);
      SELECT * INTO v
          FROM scientific_conclusion_versions
          WHERE id=r.scientific_conclusion_version_id;
      SELECT coalesce(jsonb_agg(jsonb_build_object('claim_version',jsonb_build_object(
        'type','ClaimVersion','id',c.id,'content_hash',c.content_hash),
        'literature_support_snapshot',CASE WHEN s.id IS NULL THEN NULL ELSE
          jsonb_build_object('type','LiteratureSupportSnapshot','id',s.id,
            'content_hash',s.content_hash) END,'relation_type',b.relation_type,'ordinal',b.ordinal)
        ORDER BY b.ordinal),'[]'::jsonb) INTO claims
        FROM scientific_conclusion_claim_inputs b JOIN claim_versions c ON c.id=b.claim_version_id
        LEFT JOIN literature_support_snapshots s ON s.id=b.literature_support_snapshot_id
        WHERE b.conclusion_version_id=v.id;
      SELECT coalesce(jsonb_agg(jsonb_build_object('literature_evidence',jsonb_build_object(
        'type','LiteratureEvidence','id',e.id,'content_hash',e.content_hash),
        'relation_type',b.relation_type,'ordinal',b.ordinal) ORDER BY b.ordinal),'[]'::jsonb)
        INTO literature FROM scientific_conclusion_literature_inputs b
        JOIN literature_evidence e ON e.id=b.literature_evidence_id
          WHERE b.conclusion_version_id=v.id;
      support:=pr216_hash(jsonb_build_object('type','ScientificConclusionVersionSupportSet',
        'material_version',1,'claim_inputs',claims,'literature_inputs',literature));
      IF support IS DISTINCT FROM v.support_set_hash OR pr216_hash(jsonb_build_object(
        'type','ScientificConclusionVersion','material_version',1,'scientific_conclusion_id',
        v.scientific_conclusion_id,'statement',v.statement,'scope',v.scope,'confidence',v.confidence,
        'limitation_summary',v.limitation_summary,'support_set_hash',support))<>v.content_hash THEN
        RAISE EXCEPTION 'target material hash mismatch' USING ERRCODE='P17F2';
      END IF;
      FOR cv IN SELECT c.* FROM scientific_conclusion_claim_inputs b
        JOIN claim_versions c ON c.id=b.claim_version_id WHERE b.conclusion_version_id=v.id LOOP
        IF cv.status NOT IN ('FROZEN','SUPERSEDED') OR cv.frozen_at IS NULL
          OR pr216_hash(jsonb_build_object('statement',cv.statement,'scope',cv.scope,
            'qualification',cv.qualification,'support_set_hash',cv.support_set_hash))<>cv.content_hash
          OR cv.support_set_hash IS DISTINCT FROM (SELECT pr216_hash(coalesce(jsonb_agg(
            jsonb_build_object('source_type',CASE WHEN e.measurement_id IS NULL THEN
              'statistical_result' ELSE 'measurement' END,'source_id',
              coalesce(e.measurement_id,e.statistical_result_id),'relation_type',lower(e.relation_type),
              'qualification',e.qualification) ORDER BY
              CASE WHEN e.measurement_id IS NULL THEN 'statistical_result' ELSE 'measurement' END,
              coalesce(e.measurement_id,e.statistical_result_id),lower(e.relation_type),
              e.qualification IS NOT NULL,coalesce(e.qualification,'')),'[]'::jsonb))
            FROM evidence_relations e WHERE e.claim_version_id=cv.id) THEN
          RAISE EXCEPTION 'claim material invalid' USING ERRCODE='P17F2';
        END IF;
        IF EXISTS(SELECT 1 FROM correction_records WHERE project_id=r.project_id
          AND lower(target_type)='claim_version' AND target_id=cv.id) OR EXISTS(
          SELECT 1 FROM impact_targets t JOIN impact_assessments a ON a.id=t.impact_assessment_id
          LEFT JOIN audit_findings f ON f.id=a.audit_finding_id WHERE a.project_id=r.project_id
          AND lower(t.target_type)='claim_version' AND t.target_id=cv.id
          AND lower(f.status) IS DISTINCT
          FROM 'dismissed' AND lower(a.conclusion)<>'no_impact') THEN
          RAISE EXCEPTION 'current claim invalid' USING ERRCODE='P16T1';
        END IF;
      END LOOP;
      IF EXISTS(WITH effective AS (
        SELECT b.literature_evidence_id,b.relation_type,v.created_by AS author
          FROM scientific_conclusion_literature_inputs b
          WHERE b.conclusion_version_id=v.id UNION ALL
        SELECT e.literature_evidence_id,e.relation_type,snapshot.created_by
          FROM scientific_conclusion_claim_inputs b
          JOIN literature_support_snapshots snapshot ON snapshot.id=b.literature_support_snapshot_id
          JOIN literature_evidence_relations e ON e.literature_support_snapshot_id=
            b.literature_support_snapshot_id WHERE b.conclusion_version_id=v.id)
        SELECT 1 FROM effective b JOIN literature_evidence e ON e.id=b.literature_evidence_id
          JOIN source_versions s ON s.id=e.source_version_id
          JOIN literature_sources p ON p.id=s.literature_source_id
          LEFT JOIN source_versions current ON current.id=p.current_version_id
        WHERE s.status NOT IN ('FROZEN','SUPERSEDED') OR s.version_kind='RETRACTED'
          OR current.version_kind='RETRACTED'
          OR (current.version_kind='CORRECTED' AND current.id<>s.id)
          OR e.review_status IN ('DISPUTED','REJECTED')
          OR (b.relation_type='SUPPORTS' AND (e.review_status<>'VERIFIED' OR NOT EXISTS(
            SELECT 1 FROM literature_evidence_review_events event JOIN actors actor
              ON actor.id=event.reviewed_by
            WHERE event.id=(SELECT latest.id FROM literature_evidence_review_events latest
              WHERE latest.literature_evidence_id=e.id
              ORDER BY latest.reviewed_at DESC,latest.id DESC
              LIMIT 1) AND event.new_status='VERIFIED' AND actor.actor_type='HUMAN'
              AND event.reviewed_by<>e.created_by AND event.reviewed_by<>b.author)))) THEN
        RAISE EXCEPTION 'current evidence invalid' USING ERRCODE='P16T1';
      END IF;
      FOR review_row IN SELECT * FROM internal_review_records WHERE project_id=r.project_id
        AND scientific_conclusion_version_id=v.id ORDER BY id LOOP
        IF review_row.created_at>clock_timestamp() OR (
          review_row.created_at>basis_before AND EXISTS(SELECT 1 FROM decision_basis_reviews
            WHERE decision_id=r.basis_decision_id AND internal_review_record_id=review_row.id)) THEN
          RAISE EXCEPTION 'prior committed review required' USING ERRCODE='P16B1';
        END IF;
        IF review_row.target_content_hash<>v.content_hash
          OR review_row.hash_scheme<>'sha256-cjson-v1'
          OR pr216_hash(jsonb_build_object('type','InternalReviewRecord','material_version',1,
            'project_id',review_row.project_id,'target',jsonb_build_object('type','ScientificConclusionVersion',
              'id',v.id,'content_hash',v.content_hash),'reviewer_actor_id',review_row.reviewer_actor_id,
              'review_type',review_row.review_type,'recommendation',review_row.recommendation,'summary',review_row.summary))
            <>review_row.content_hash OR NOT EXISTS(
            SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id
            JOIN project_role_assignments role ON role.membership_id=m.id
              AND role.actor_id=m.actor_id AND role.project_id=m.project_id
            WHERE a.id=review_row.reviewer_actor_id
          AND a.actor_type='HUMAN'
          AND a.created_at<=review_row.created_at

          AND (a.retired_at IS NULL
          OR review_row.created_at<a.retired_at)
          AND m.project_id=r.project_id
              AND m.started_at<=review_row.created_at AND role.role IN ('OWNER','REVIEWER')
              AND role.effective_from<=review_row.created_at
              AND (role.effective_until IS NULL OR review_row.created_at<role.effective_until)
              AND (SELECT e.new_status FROM project_membership_events e
                WHERE e.membership_id=m.id AND e.occurred_at<=review_row.created_at
                ORDER BY e.occurred_at DESC,e.id DESC LIMIT 1)='ACTIVE'
              AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=a.id
                AND b.bound_at<=review_row.created_at
          AND ( b.revoked_at IS NULL OR review_row.created_at<b.revoked_at)))
          OR review_row.reviewer_actor_id IN (SELECT pr216_authors(v.id)) THEN
          RAISE EXCEPTION 'matching review material invalid' USING ERRCODE='P17F2';
        END IF;
      END LOOP;
    END $$;
CREATE FUNCTION b10_refs(did UUID) RETURNS TABLE(kind text,id UUID,digest text,ordinal integer)
LANGUAGE SQL STABLE SET search_path=pg_catalog, public, pg_temp AS $$
 SELECT 'ApprovalDecision',b.approval_decision_id,d.content_hash::text,b.ordinal
 FROM decision_basis_approval_decisions b JOIN approval_decisions d ON d.id=b.approval_decision_id WHERE b.decision_id=did
 UNION ALL SELECT 'InternalReviewRecord',b.internal_review_record_id,r.content_hash::text,b.ordinal
 FROM decision_basis_reviews b JOIN internal_review_records r ON r.id=b.internal_review_record_id WHERE b.decision_id=did
 UNION ALL SELECT 'RevisionAction',b.revision_action_id,a.content_hash::text,b.ordinal
 FROM decision_basis_revision_actions b JOIN revision_actions a ON a.id=b.revision_action_id WHERE b.decision_id=did
 UNION ALL SELECT 'ScientificConclusionVersion',b.scientific_conclusion_version_id,v.content_hash::text,b.ordinal
 FROM decision_basis_conclusions b JOIN scientific_conclusion_versions v ON v.id=b.scientific_conclusion_version_id WHERE b.decision_id=did
$$;
CREATE FUNCTION b10_child_check(did UUID) RETURNS void LANGUAGE plpgsql
SET search_path=pg_catalog, public, pg_temp AS $$
DECLARE d decision_records; stamp bigint;
BEGIN
 PERFORM b09_preheld();
 SELECT * INTO d FROM decision_records WHERE id=did;
 SELECT xmin::text::bigint INTO stamp FROM decision_records WHERE id=did;
 IF stamp IS DISTINCT FROM pg_current_xact_id()::text::bigint THEN
   RAISE EXCEPTION 'immutable sealed parent' USING ERRCODE='P17F1';
 END IF;
 IF d.decision_type<>'RECONSIDER_REJECTION' THEN
   RAISE EXCEPTION 'reconsideration parent required' USING ERRCODE='P10B1';
 END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended('pr216:scope:'||d.project_id||':'||'INTERNAL_SCIENTIFIC_RELEASE',0));
END $$;
CREATE FUNCTION b10_basis_guard() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog, public, pg_temp AS $$
BEGIN
 PERFORM b10_child_check(NEW.decision_id);
 RETURN NEW;
END $$;
CREATE FUNCTION b10_decision_guard() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog, public, pg_temp AS $$
BEGIN
 IF NEW.decision_type IN ('INTERNAL_SCIENTIFIC_RELEASE','RECONSIDER_REJECTION') THEN
  PERFORM b09_preheld();
  PERFORM pg_advisory_xact_lock(hashtextextended('pr215:decision:'||NEW.id,0));
  PERFORM pg_advisory_xact_lock(hashtextextended('pr216:scope:'||NEW.project_id||':'||'INTERNAL_SCIENTIFIC_RELEASE',0));
  IF NEW.decision_type='RECONSIDER_REJECTION' AND NOT pr216_approver_active(NEW.decided_by,NEW.project_id) THEN
    RAISE EXCEPTION 'HUMAN APPROVER required' USING ERRCODE='P16A1';
  END IF;
  IF NEW.decision_type='RECONSIDER_REJECTION' THEN NEW.decided_at:=clock_timestamp(); END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER b10_decision_guard BEFORE INSERT ON decision_records FOR EACH ROW EXECUTE FUNCTION b10_decision_guard();
CREATE TRIGGER b10_basis_guard BEFORE INSERT ON decision_basis_approval_decisions FOR EACH ROW EXECUTE FUNCTION b10_basis_guard();
CREATE TRIGGER b10_basis_guard BEFORE INSERT ON decision_basis_revision_actions FOR EACH ROW EXECUTE FUNCTION b10_basis_guard();
CREATE TRIGGER b10_basis_immutable BEFORE UPDATE OR DELETE ON decision_basis_approval_decisions FOR EACH ROW EXECUTE FUNCTION pr215_immutable();
CREATE TRIGGER b10_basis_immutable BEFORE UPDATE OR DELETE ON decision_basis_revision_actions FOR EACH ROW EXECUTE FUNCTION pr215_immutable();

CREATE FUNCTION b10_normalize(value jsonb) RETURNS jsonb LANGUAGE plpgsql IMMUTABLE
SET search_path=pg_catalog, public, pg_temp AS $$
DECLARE result jsonb; field record;
BEGIN
 IF jsonb_typeof(value)='string' THEN
  RETURN to_jsonb(regexp_replace(btrim(translate(normalize(value #>> '{}',NFC),U&'\0009\000A\000B\000C\000D\001C\001D\001E\001F\0020\0085\00A0\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200A\2028\2029\202F\205F\3000',repeat(' ',29))), ' +', ' ', 'g'));
 ELSIF jsonb_typeof(value)='object' THEN
  result:='{}';
  FOR field IN SELECT * FROM jsonb_each(value) LOOP
   result:=result||jsonb_build_object(field.key,b10_normalize(field.value));
  END LOOP;
  RETURN result;
 END IF;
 RETURN value;
END $$;
CREATE FUNCTION b10_explanation(value text) RETURNS boolean LANGUAGE SQL IMMUTABLE
SET search_path=pg_catalog, public, pg_temp AS $$
 SELECT cleaned<>'' AND cleaned NOT IN ('accept','approve','reject','uncertain','minor revision','major revision',
  'recommend accept','recommend approve','recommend reject') FROM (
  SELECT btrim(regexp_replace(regexp_replace(lower(value),
   '[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}','','g'),
   '[[:space:][:punct:][:digit:]]+', ' ', 'g')) AS cleaned) prose
$$;
CREATE FUNCTION b10_review_verify(r internal_review_records,pid UUID) RETURNS void LANGUAGE plpgsql
SET search_path=pg_catalog, public, pg_temp AS $$
DECLARE v scientific_conclusion_versions;
BEGIN
 SELECT * INTO v FROM scientific_conclusion_versions WHERE id=r.scientific_conclusion_version_id;
 IF r.project_id IS DISTINCT FROM pid OR v.id IS NULL OR v.content_hash IS DISTINCT FROM r.target_content_hash
 OR r.hash_scheme<>'sha256-cjson-v1' OR r.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object(
  'type','InternalReviewRecord','material_version',1,'project_id',r.project_id,
  'target',pr216_ref('ScientificConclusionVersion',v.id,v.content_hash),
  'reviewer_actor_id',r.reviewer_actor_id,'review_type',r.review_type,
  'recommendation',r.recommendation,'summary',r.summary)) THEN
  RAISE EXCEPTION 'review binding/hash corrupt' USING ERRCODE='P17F2';
 END IF;
 IF NOT EXISTS(SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id
 JOIN project_role_assignments role ON role.membership_id=m.id AND role.project_id=m.project_id AND role.actor_id=m.actor_id
 WHERE a.id=r.reviewer_actor_id AND a.actor_type='HUMAN' AND a.created_at<=r.created_at
 AND (a.retired_at IS NULL OR r.created_at<a.retired_at) AND m.project_id=pid AND m.started_at<=r.created_at
 AND role.role IN ('OWNER','REVIEWER') AND role.effective_from<=r.created_at
 AND (role.effective_until IS NULL OR r.created_at<role.effective_until)
 AND (SELECT e.new_status FROM project_membership_events e WHERE e.membership_id=m.id
  AND e.occurred_at<=r.created_at ORDER BY e.occurred_at DESC,e.id DESC LIMIT 1)='ACTIVE'
 AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=a.id AND b.bound_at<=r.created_at
  AND (b.revoked_at IS NULL OR r.created_at<b.revoked_at))) THEN
  RAISE EXCEPTION 'historical review authority invalid' USING ERRCODE='P17F2';
 END IF;
 PERFORM b10_facts('ScientificConclusionVersion',v.id,pid);
END $$;
CREATE FUNCTION b10_validate(did UUID) RETURNS void LANGUAGE plpgsql
SET search_path=pg_catalog, public, pg_temp AS $$
DECLARE d decision_records; v scientific_conclusion_versions; old scientific_conclusion_versions;
 r approval_requests; rejected record; checked_review internal_review_records; a revision_actions;
 refs jsonb; last_rejection timestamptz; authors UUID[]; rejectors UUID[]; corrected_reviewers UUID[];
 old_review_ids UUID[]; fresh_ids UUID[]; selected_fresh UUID[]; n integer; action_count integer;
BEGIN
 SELECT * INTO d FROM decision_records WHERE id=did;
 IF d.decision_type<>'RECONSIDER_REJECTION' THEN RETURN; END IF;
 PERFORM b09_preheld();
 IF NOT pr216_approver_active(d.decided_by,d.project_id) THEN
  RAISE EXCEPTION 'current reconsiderer authority required' USING ERRCODE='P16A1'; END IF;
 IF NOT EXISTS(SELECT 1 FROM projects WHERE id=d.project_id AND lifecycle_status='ACTIVE') THEN
  RAISE EXCEPTION 'active project required' USING ERRCODE='P16G1'; END IF;
 SELECT count(*) INTO n FROM decision_basis_conclusions WHERE decision_id=did;
 IF n<>1 THEN RAISE EXCEPTION 'one exact target required' USING ERRCODE='P10B1'; END IF;
 SELECT s.* INTO v FROM scientific_conclusion_versions s JOIN decision_basis_conclusions b
  ON b.scientific_conclusion_version_id=s.id WHERE b.decision_id=did FOR UPDATE OF s;
 PERFORM c.id FROM scientific_conclusions c WHERE c.id=v.scientific_conclusion_id FOR SHARE;
 IF NOT EXISTS(SELECT 1 FROM scientific_conclusions c WHERE c.id=v.scientific_conclusion_id AND c.project_id=d.project_id)
 OR v.status<>'FROZEN' OR v.frozen_at IS NULL OR EXISTS(SELECT 1 FROM scientific_conclusion_versions WHERE id=v.id AND xmin::text::bigint=pg_current_xact_id()::text::bigint) THEN
  RAISE EXCEPTION 'new exact frozen target required' USING ERRCODE='P16T1'; END IF;
 SELECT count(*) INTO n FROM decision_basis_approval_decisions WHERE decision_id=did;
 IF n NOT BETWEEN 1 AND 100 OR EXISTS(
  (SELECT x.id FROM approval_decisions x JOIN approval_requests q ON q.id=x.approval_request_id
   WHERE q.project_id=d.project_id AND q.approval_purpose='INTERNAL_SCIENTIFIC_RELEASE' AND x.decision='REJECT')
  EXCEPT (SELECT approval_decision_id FROM decision_basis_approval_decisions WHERE decision_id=did)) OR EXISTS(
  (SELECT approval_decision_id FROM decision_basis_approval_decisions WHERE decision_id=did) EXCEPT
  (SELECT x.id FROM approval_decisions x JOIN approval_requests q ON q.id=x.approval_request_id
   WHERE q.project_id=d.project_id AND q.approval_purpose='INTERNAL_SCIENTIFIC_RELEASE' AND x.decision='REJECT')) THEN
  RAISE EXCEPTION 'complete rejection scope required' USING ERRCODE='P10B1'; END IF;
 SELECT max(x.decided_at),array_agg(DISTINCT x.decided_by) INTO last_rejection,rejectors
 FROM approval_decisions x JOIN decision_basis_approval_decisions b ON b.approval_decision_id=x.id WHERE b.decision_id=did;
 IF d.decided_at<=last_rejection THEN RAISE EXCEPTION 'fresh decision required' USING ERRCODE='P10B1'; END IF;
 SELECT coalesce(array_agg(id),ARRAY[]::uuid[]) INTO old_review_ids FROM (
  SELECT DISTINCT ar.internal_review_record_id AS id FROM approval_request_reviews ar
  JOIN approval_decisions x ON x.approval_request_id=ar.request_id
  JOIN decision_basis_approval_decisions b ON b.approval_decision_id=x.id
  JOIN decision_basis_reviews selected ON selected.internal_review_record_id=ar.internal_review_record_id AND selected.decision_id=did
  WHERE b.decision_id=did) ids;
 SELECT coalesce(array_agg(DISTINCT reviewer_actor_id),ARRAY[]::uuid[]) INTO corrected_reviewers
 FROM internal_review_records WHERE id=ANY(old_review_ids);
 SELECT coalesce(array_agg(actor),ARRAY[]::uuid[]) INTO authors FROM pr216_authors(v.id) actor;
 IF d.decided_by=ANY(authors||rejectors) OR EXISTS(SELECT 1 FROM decision_basis_reviews b
  JOIN internal_review_records review ON review.id=b.internal_review_record_id
  WHERE b.decision_id=did AND review.reviewer_actor_id=d.decided_by) THEN
  RAISE EXCEPTION 'independent reconsiderer required' USING ERRCODE='P16C1'; END IF;
 fresh_ids:=ARRAY[]::uuid[];
 FOR checked_review IN SELECT * FROM internal_review_records WHERE scientific_conclusion_version_id=v.id AND project_id=d.project_id ORDER BY id LOOP
  PERFORM b10_review_verify(checked_review,d.project_id);
  IF checked_review.created_at>last_rejection AND checked_review.created_at<d.decided_at
    AND NOT checked_review.reviewer_actor_id=ANY(authors||rejectors||corrected_reviewers||ARRAY[d.decided_by]) THEN
    fresh_ids:=array_append(fresh_ids,checked_review.id);
  END IF;
 END LOOP;
 IF cardinality(fresh_ids) NOT BETWEEN 1 AND 100 OR EXISTS(
  SELECT 1 FROM unnest(fresh_ids) f(id) WHERE NOT EXISTS(SELECT 1 FROM decision_basis_reviews b
   WHERE b.decision_id=did AND b.internal_review_record_id=f.id)) OR EXISTS(
  SELECT 1 FROM decision_basis_reviews b WHERE b.decision_id=did AND NOT b.internal_review_record_id=ANY(fresh_ids||old_review_ids)) THEN
  RAISE EXCEPTION 'complete fresh independent review basis required' USING ERRCODE='P10B1'; END IF;
 IF cardinality(old_review_ids)>100 THEN RAISE EXCEPTION 'bounded corrections required' USING ERRCODE='P10B1'; END IF;
 IF EXISTS(SELECT 1 FROM unnest(old_review_ids) corrected(id)
   WHERE position(corrected.id::text IN lower(d.rationale))=0) THEN
  RAISE EXCEPTION 'every corrected review must be named' USING ERRCODE='P10B1'; END IF;
 SELECT count(*) INTO action_count FROM decision_basis_revision_actions WHERE decision_id=did;
 IF (d.decision='REVISED_TARGET' AND (action_count NOT BETWEEN 1 AND 100 OR cardinality(old_review_ids)<>0))
 OR (d.decision='CORRECTED_REVIEW' AND (action_count<>0 OR cardinality(old_review_ids)=0)) THEN
  RAISE EXCEPTION 'finite ground witnesses required' USING ERRCODE='P10B1'; END IF;
 FOR checked_review IN SELECT review.* FROM internal_review_records review JOIN decision_basis_reviews b
  ON b.internal_review_record_id=review.id WHERE b.decision_id=did LOOP
  PERFORM b10_review_verify(checked_review,d.project_id);
  IF EXISTS(SELECT 1 FROM internal_review_records current_row WHERE id=checked_review.id
     AND xmin::text::bigint=pg_current_xact_id()::text::bigint) THEN
   RAISE EXCEPTION 'prior committed reviews required' USING ERRCODE='P10B1'; END IF;
 END LOOP;
 FOR rejected IN SELECT x.*,q.scientific_conclusion_version_id AS old_id,q.target_content_hash AS old_hash,q.id AS request_id,q.requested_by
 FROM approval_decisions x JOIN approval_requests q ON q.id=x.approval_request_id
 JOIN decision_basis_approval_decisions b ON b.approval_decision_id=x.id WHERE b.decision_id=did LOOP
  IF EXISTS(SELECT 1 FROM approval_decisions WHERE id=rejected.id AND xmin::text::bigint=pg_current_xact_id()::text::bigint) THEN
   RAISE EXCEPTION 'prior committed rejections required' USING ERRCODE='P10B1'; END IF;
  SELECT * INTO old FROM scientific_conclusion_versions WHERE id=rejected.old_id;
  IF old.content_hash IS DISTINCT FROM rejected.old_hash OR rejected.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object(
    'type','ApprovalDecision','material_version',1,'approval_request_id',rejected.request_id,
    'target',pr216_ref('ScientificConclusionVersion',old.id,old.content_hash),
    'decision',rejected.decision,'valid_until',NULL,'requires_current_author_consent',false,
    'rationale',rejected.rationale,'decided_by',jsonb_build_object('type','ActorIdentity','id',rejected.decided_by))) THEN
    RAISE EXCEPTION 'rejection history corrupt' USING ERRCODE='P17F2'; END IF;
  IF position(rejected.id::text IN lower(d.rationale))=0 THEN
    RAISE EXCEPTION 'rationale must explain each rejection' USING ERRCODE='P10B1'; END IF;
  IF d.decision='REVISED_TARGET' THEN
   IF v.scientific_conclusion_id<>old.scientific_conclusion_id OR v.version_number<=old.version_number
    OR b10_normalize(jsonb_build_object('statement',v.statement,'scope',v.scope,'confidence',v.confidence,'limitation_summary',v.limitation_summary))
     =b10_normalize(jsonb_build_object('statement',old.statement,'scope',old.scope,'confidence',old.confidence,'limitation_summary',old.limitation_summary))
    OR NOT EXISTS(SELECT 1 FROM revision_actions action JOIN review_issues issue ON issue.id=action.review_issue_id
      JOIN internal_review_records review ON review.id=issue.review_record_id
      JOIN decision_basis_revision_actions b ON b.revision_action_id=action.id
      WHERE b.decision_id=did AND action.action_type='CONCLUSION_CHANGE'
      AND action.result_scientific_conclusion_version_id=v.id AND review.scientific_conclusion_version_id=old.id
      AND action.decision_record_id IS NULL) THEN
     RAISE EXCEPTION 'material revision witness for each rejection required' USING ERRCODE='P10B1'; END IF;
  ELSE
   IF NOT b10_explanation(d.rationale) OR NOT EXISTS(SELECT 1 FROM approval_request_reviews ar JOIN internal_review_records prior ON prior.id=ar.internal_review_record_id
     WHERE ar.request_id=rejected.request_id AND prior.id=ANY(old_review_ids)
     AND position(prior.id::text IN lower(d.rationale))>0
     AND EXISTS(SELECT 1 FROM internal_review_records fresh WHERE fresh.id=ANY(fresh_ids)
       AND b10_explanation(fresh.summary) AND b10_normalize(to_jsonb(fresh.summary))<>b10_normalize(to_jsonb(prior.summary)))) THEN
    RAISE EXCEPTION 'reasoned explicit review correction for each rejection required' USING ERRCODE='P10B1'; END IF;
  END IF;
 END LOOP;
 FOR a IN SELECT action.* FROM revision_actions action JOIN decision_basis_revision_actions b
  ON b.revision_action_id=action.id WHERE b.decision_id=did LOOP
  IF a.action_type<>'CONCLUSION_CHANGE' OR a.result_scientific_conclusion_version_id IS DISTINCT FROM v.id
   OR EXISTS(SELECT 1 FROM revision_actions WHERE id=a.id AND xmin::text::bigint=pg_current_xact_id()::text::bigint)
   OR NOT EXISTS(SELECT 1 FROM review_issues i JOIN internal_review_records review ON review.id=i.review_record_id
     JOIN approval_requests q ON q.scientific_conclusion_version_id=review.scientific_conclusion_version_id
     JOIN approval_decisions x ON x.approval_request_id=q.id JOIN decision_basis_approval_decisions b ON b.approval_decision_id=x.id
     WHERE i.id=a.review_issue_id AND b.decision_id=did) THEN
   RAISE EXCEPTION 'committed relevant revision required' USING ERRCODE='P10B1'; END IF;
  PERFORM b10_revision_verify(a.id,d.project_id);
  IF a.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','RevisionAction','material_version',1,
   'review_issue',jsonb_build_object('type','ReviewIssue','id',a.review_issue_id),'decision',NULL,
   'action_type',a.action_type,'results',jsonb_build_object('result_experiment_spec_version',NULL,'result_run',NULL,'result_statistical_result',NULL,
   'result_claim_version',NULL,'result_scientific_conclusion_version',pr216_ref('ScientificConclusionVersion',v.id,v.content_hash),
   'result_manuscript_version',NULL,'result_source_version',NULL),
   'supersedes_revision_action',CASE WHEN a.supersedes_revision_action_id IS NULL THEN NULL ELSE
     (SELECT pr216_ref('RevisionAction',prior.id,prior.content_hash) FROM revision_actions prior WHERE prior.id=a.supersedes_revision_action_id) END,
   'created_by',jsonb_build_object('type','ActorIdentity','id',a.created_by))) THEN
   RAISE EXCEPTION 'revision hash corrupt' USING ERRCODE='P17F2'; END IF;
 END LOOP;
 r.project_id:=d.project_id; r.scientific_conclusion_version_id:=v.id;
 r.target_content_hash:=v.content_hash; r.target_hash_scheme:=v.hash_scheme;
 PERFORM b10_material_gate(r);
 IF EXISTS(SELECT 1 FROM review_issues issue JOIN internal_review_records review ON review.id=issue.review_record_id
  WHERE review.scientific_conclusion_version_id=v.id AND review.project_id=d.project_id AND issue.status='OPEN' AND issue.severity='BLOCKING') THEN
  RAISE EXCEPTION 'blocking issue remains open' USING ERRCODE='P16G1'; END IF;
 SELECT count(*) INTO n FROM b10_refs(did);
 IF n>401 OR EXISTS(SELECT 1 FROM (SELECT ordinal,row_number() OVER(ORDER BY kind,id,digest)-1 AS expected FROM b10_refs(did)) pos WHERE ordinal<>expected) THEN
  RAISE EXCEPTION 'bounded canonical global ordinals required' USING ERRCODE='P10B1'; END IF;
 SELECT jsonb_agg(jsonb_build_object('target',pr216_ref(kind,id,digest),'ordinal',ordinal) ORDER BY kind,id,digest) INTO refs FROM b10_refs(did);
 IF d.basis_set_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','DecisionRecordBasisSet','material_version',1,'basis',refs))
 OR d.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','DecisionRecord','material_version',1,'project_id',d.project_id,
 'decision_type',d.decision_type,'question',d.question,'decision',d.decision,'rationale',d.rationale,
 'decided_by',jsonb_build_object('type','ActorIdentity','id',d.decided_by),'supersedes_decision_id',NULL,'basis_set_hash',d.basis_set_hash)) THEN
  RAISE EXCEPTION 'literal reconsideration hashes required' USING ERRCODE='P17F2'; END IF;
 IF NOT pr216_approver_active(d.decided_by,d.project_id) THEN
  RAISE EXCEPTION 'final reconsiderer authority required' USING ERRCODE='P16A1'; END IF;
END $$;
CREATE FUNCTION b10_successor_check(r approval_requests, approver UUID) RETURNS void LANGUAGE plpgsql
SET search_path=pg_catalog, public, pg_temp AS $$
DECLARE d decision_records; anchor UUID; latest timestamptz; target UUID;
BEGIN
 SELECT q.id,x.decided_at INTO anchor,latest FROM approval_decisions x JOIN approval_requests q ON q.id=x.approval_request_id
 WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose AND x.decision='REJECT'
 AND (NOT EXISTS(SELECT 1 FROM approval_decisions own WHERE own.id=x.id
   AND own.approval_request_id=r.id AND own.xmin::text::bigint=pg_current_xact_id()::text::bigint))
 ORDER BY x.decided_at DESC,x.id DESC LIMIT 1;
 IF anchor IS NULL THEN
  IF r.prior_rejected_request_id IS NOT NULL OR r.reconsideration_decision_id IS NOT NULL THEN
   RAISE EXCEPTION 'unneeded reconsideration links' USING ERRCODE='P16R1'; END IF;
  RETURN;
 END IF;
 SELECT * INTO d FROM decision_records WHERE id=r.reconsideration_decision_id;
 SELECT scientific_conclusion_version_id INTO target FROM decision_basis_conclusions WHERE decision_id=d.id;
 IF d.id IS NULL OR r.prior_rejected_request_id IS DISTINCT FROM anchor OR d.project_id<>r.project_id
 OR d.decision_type<>'RECONSIDER_REJECTION' OR r.approval_purpose<>'INTERNAL_SCIENTIFIC_RELEASE'
 OR target IS DISTINCT FROM r.scientific_conclusion_version_id
 OR d.decided_at<=latest OR d.decided_at>=coalesce(r.requested_at,clock_timestamp())
 OR EXISTS(SELECT 1 FROM decision_records WHERE id=d.id AND xmin::text::bigint=pg_current_xact_id()::text::bigint)
 OR EXISTS((SELECT x.id FROM approval_decisions x JOIN approval_requests q ON q.id=x.approval_request_id
    WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose AND x.decision='REJECT'
    AND NOT (x.approval_request_id=r.id AND x.xmin::text::bigint=pg_current_xact_id()::text::bigint))
    EXCEPT (SELECT approval_decision_id FROM decision_basis_approval_decisions WHERE decision_id=d.id))
 OR EXISTS((SELECT approval_decision_id FROM decision_basis_approval_decisions WHERE decision_id=d.id)
    EXCEPT (SELECT x.id FROM approval_decisions x JOIN approval_requests q ON q.id=x.approval_request_id
      WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose AND x.decision='REJECT')) THEN
  RAISE EXCEPTION 'complete current rejection reconsideration required' USING ERRCODE='P16R1'; END IF;
 IF d.decided_by=r.requested_by OR approver=d.decided_by
 OR EXISTS(SELECT 1 FROM decision_basis_reviews b JOIN internal_review_records review ON review.id=b.internal_review_record_id
  WHERE b.decision_id=d.id AND review.created_at>latest AND review.reviewer_actor_id IN (r.requested_by,approver)) THEN
  RAISE EXCEPTION 'independent successor actors required' USING ERRCODE='P16C1'; END IF;
 IF EXISTS(SELECT 1 FROM approval_requests q WHERE q.reconsideration_decision_id=d.id AND q.id<>r.id) THEN
  RAISE EXCEPTION 'reconsideration already used' USING ERRCODE='P17F3'; END IF;
END $$;
CREATE FUNCTION b10_complete() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog, public, pg_temp AS $$
BEGIN
 IF TG_TABLE_NAME='decision_records' THEN PERFORM b10_validate(NEW.id);
 ELSE PERFORM b10_validate(NEW.decision_id); END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER b10_complete_decision AFTER INSERT ON decision_records
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b10_complete();
CREATE CONSTRAINT TRIGGER b10_complete_rejections AFTER INSERT ON decision_basis_approval_decisions
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b10_complete();
CREATE CONSTRAINT TRIGGER b10_complete_revisions AFTER INSERT ON decision_basis_revision_actions
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b10_complete();

CREATE VIEW b10_edges AS
 SELECT 'DecisionRecord'::text AS kind,decision_id AS id,'ApprovalDecision'::text AS child_kind,approval_decision_id AS child_id FROM decision_basis_approval_decisions
 UNION ALL SELECT 'DecisionRecord',decision_id,'RevisionAction',revision_action_id FROM decision_basis_revision_actions
 UNION ALL SELECT 'DecisionRecord',decision_id,'InternalReviewRecord',internal_review_record_id FROM decision_basis_reviews
 UNION ALL SELECT 'DecisionRecord',id,'DecisionRecord',supersedes_decision_id FROM decision_records WHERE supersedes_decision_id IS NOT NULL
 UNION ALL SELECT 'ApprovalDecision',id,'ApprovalRequest',approval_request_id FROM approval_decisions
 UNION ALL SELECT 'ApprovalRequest',id,'DecisionRecord',basis_decision_id FROM approval_requests
 UNION ALL SELECT 'ApprovalRequest',id,'DecisionRecord',reconsideration_decision_id FROM approval_requests WHERE reconsideration_decision_id IS NOT NULL
 UNION ALL SELECT 'ApprovalRequest',id,'ApprovalRequest',prior_rejected_request_id FROM approval_requests WHERE prior_rejected_request_id IS NOT NULL
 UNION ALL SELECT 'RevisionAction',id,'DecisionRecord',decision_record_id FROM revision_actions WHERE decision_record_id IS NOT NULL
 UNION ALL SELECT 'RevisionAction',id,'ReviewIssue',review_issue_id FROM revision_actions WHERE review_issue_id IS NOT NULL
 UNION ALL SELECT 'RevisionAction',id,'RevisionAction',supersedes_revision_action_id FROM revision_actions WHERE supersedes_revision_action_id IS NOT NULL

 UNION ALL SELECT 'ReviewIssue',id,'InternalReviewRecord',review_record_id FROM review_issues
 UNION ALL SELECT 'DecisionRecord',decision_id,'ScientificConclusionVersion',scientific_conclusion_version_id FROM decision_basis_conclusions
 UNION ALL SELECT 'ApprovalRequest',request_id,'InternalReviewRecord',internal_review_record_id FROM approval_request_reviews
 UNION ALL SELECT 'InternalReviewRecord',id,'ScientificConclusionVersion',scientific_conclusion_version_id FROM internal_review_records WHERE scientific_conclusion_version_id IS NOT NULL
 UNION ALL SELECT 'InternalReviewRecord',id,'ClaimVersion',claim_version_id FROM internal_review_records WHERE claim_version_id IS NOT NULL
 UNION ALL SELECT 'RevisionAction',id,'ScientificConclusionVersion',result_scientific_conclusion_version_id FROM revision_actions WHERE result_scientific_conclusion_version_id IS NOT NULL
 UNION ALL SELECT 'ScientificConclusionVersion',conclusion_version_id,'ClaimVersion',claim_version_id FROM scientific_conclusion_claim_inputs
 UNION ALL SELECT 'ScientificConclusionVersion',conclusion_version_id,'LiteratureSupportSnapshot',literature_support_snapshot_id FROM scientific_conclusion_claim_inputs WHERE literature_support_snapshot_id IS NOT NULL
 UNION ALL SELECT 'ScientificConclusionVersion',conclusion_version_id,'LiteratureEvidence',literature_evidence_id FROM scientific_conclusion_literature_inputs
 UNION ALL SELECT 'ClaimVersion',claim_version_id,'Measurement',measurement_id FROM evidence_relations WHERE measurement_id IS NOT NULL
 UNION ALL SELECT 'ClaimVersion',claim_version_id,'StatisticalResult',statistical_result_id FROM evidence_relations WHERE statistical_result_id IS NOT NULL
 UNION ALL SELECT 'StatisticalResult',statistical_result_id,'Measurement',measurement_id FROM statistical_result_inputs
 UNION ALL SELECT 'LiteratureSupportSnapshot',literature_support_snapshot_id,'LiteratureEvidence',literature_evidence_id FROM literature_evidence_relations
 UNION ALL SELECT 'LiteratureSupportSnapshot',id,'LiteratureSupportSnapshot',previous_snapshot_id FROM literature_support_snapshots WHERE previous_snapshot_id IS NOT NULL
 UNION ALL SELECT 'LiteratureEvidence',id,'SourceVersion',source_version_id FROM literature_evidence
 UNION ALL SELECT 'SourceVersion',id,'SourceVersion',predecessor_source_version_id FROM source_versions WHERE predecessor_source_version_id IS NOT NULL
 UNION ALL SELECT 'SourceVersion',id,'ArtifactVersion',fulltext_artifact_version_id FROM source_versions WHERE fulltext_artifact_version_id IS NOT NULL
 UNION ALL SELECT 'Measurement',id,'Run',run_id FROM measurements
 UNION ALL SELECT 'Measurement',id,'MetricDefinitionVersion',metric_definition_version_id FROM measurements
 UNION ALL SELECT 'Run',id,'ExperimentSpecVersion',experiment_spec_version_id FROM runs
 UNION ALL SELECT 'Run',run_id,'DatasetSnapshot',dataset_snapshot_id FROM run_dataset_inputs
 UNION ALL SELECT 'Run',run_id,'ArtifactVersion',artifact_version_id FROM run_artifact_inputs
 UNION ALL SELECT 'RevisionAction',id,'ExperimentSpecVersion',result_experiment_spec_version_id FROM revision_actions WHERE result_experiment_spec_version_id IS NOT NULL
 UNION ALL SELECT 'RevisionAction',id,'Run',result_run_id FROM revision_actions WHERE result_run_id IS NOT NULL
 UNION ALL SELECT 'RevisionAction',id,'StatisticalResult',result_statistical_result_id FROM revision_actions WHERE result_statistical_result_id IS NOT NULL
 UNION ALL SELECT 'RevisionAction',id,'ClaimVersion',result_claim_version_id FROM revision_actions WHERE result_claim_version_id IS NOT NULL
 UNION ALL SELECT 'RevisionAction',id,'SourceVersion',result_source_version_id FROM revision_actions WHERE result_source_version_id IS NOT NULL
 UNION ALL SELECT 'RevisionAction',id,'ManuscriptVersion',result_manuscript_version_id FROM revision_actions WHERE result_manuscript_version_id IS NOT NULL
 UNION ALL SELECT 'SourceVersion',id,'ArtifactVersion',correction_basis_artifact_version_id FROM source_versions WHERE correction_basis_artifact_version_id IS NOT NULL
 UNION ALL SELECT 'LiteratureSupportSnapshot',id,'ClaimVersion',claim_version_id FROM literature_support_snapshots;



CREATE FUNCTION b10_closure(seed_kind text,seed_id uuid) RETURNS TABLE(kind text,id uuid)
LANGUAGE SQL STABLE SET search_path=pg_catalog, public, pg_temp AS $$
 WITH RECURSIVE closure(kind,id) AS (
  SELECT seed_kind,seed_id UNION SELECT e.child_kind,e.child_id FROM closure c
  JOIN b10_edges e ON e.kind=c.kind AND e.id=c.id)
 SELECT CASE kind
 WHEN 'ScientificConclusionVersion' THEN 'scientific_conclusion_versions'
 WHEN 'ClaimVersion' THEN 'claim_versions'
 WHEN 'Measurement' THEN 'measurements'
 WHEN 'StatisticalResult' THEN 'statistical_results'
 WHEN 'Run' THEN 'runs'
 WHEN 'MetricDefinitionVersion' THEN 'metric_definition_versions'
 WHEN 'ExperimentSpecVersion' THEN 'experiment_spec_versions'
 WHEN 'DatasetSnapshot' THEN 'dataset_snapshots'
 WHEN 'ArtifactVersion' THEN 'artifact_versions'
 WHEN 'SourceVersion' THEN 'source_versions'
 WHEN 'LiteratureEvidence' THEN 'literature_evidence'
 WHEN 'LiteratureSupportSnapshot' THEN 'literature_support_snapshots'
 ELSE kind END,id FROM closure
$$;
CREATE FUNCTION b10_facts(seed_kind text,target UUID,pid UUID) RETURNS void LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE node RECORD; row JSONB; material JSONB; expected TEXT; numerical DOUBLE PRECISION;
      input_set JSONB; bound JSONB; previous JSONB; artifact JSONB; correction JSONB;
      cv claim_versions; version scientific_conclusion_versions; claims jsonb; literature jsonb; support text;
    BEGIN
      -- Closed inventory only. These are typed graph queries, never stored soft references.
      FOR node IN SELECT * FROM b10_closure(seed_kind,target) WHERE kind IN (
        'measurements','statistical_results','runs','metric_definition_versions',
        'experiment_spec_versions','dataset_snapshots','artifact_versions','source_versions',
        'literature_evidence','literature_support_snapshots') ORDER BY kind,id LOOP
        EXECUTE format('SELECT to_jsonb(x) FROM %I x WHERE id=$1',node.kind) INTO row USING node.id;
        IF row IS NULL THEN RAISE EXCEPTION 'missing frozen closure' USING ERRCODE='P17F2'; END IF;
        material:=NULL; expected:=NULL;
        IF node.kind IN ('metric_definition_versions','experiment_spec_versions',
                         'artifact_versions','source_versions') AND (
          row->>'status' NOT IN ('FROZEN','SUPERSEDED') OR row->>'frozen_at' IS NULL) THEN
          RAISE EXCEPTION 'frozen closure required' USING ERRCODE='P17F2';
        END IF;
        CASE node.kind
        WHEN 'measurements' THEN
          SELECT numeric_value INTO numerical FROM measurements WHERE id=node.id;
          IF NOT EXISTS(SELECT 1 FROM runs WHERE id=(row->>'run_id')::uuid AND project_id=pid)
            OR NOT EXISTS(SELECT 1 FROM metric_definition_versions v JOIN metric_definitions p
              ON p.id=v.metric_definition_id WHERE v.id=(row->>'metric_definition_version_id')::uuid
                AND p.project_id=pid) THEN
            RAISE EXCEPTION 'same-project measurement closure required' USING ERRCODE='P17F2';
          END IF;
          expected:=encode(sha256(convert_to(
            '{"evaluation_scope":'||pr216_cjson(row->'evaluation_scope')||
            ',"metric_definition_version_id":'||(row->'metric_definition_version_id')::text||
            ',"numeric_value":'||pr216_float(numerical)||',"run_id":'||(row->'run_id')::text||
            ',"structured_value":'||pr216_cjson(row->'structured_value')||
            ',"unit":'||(row->'unit')::text||'}','UTF8')),'hex');
        WHEN 'statistical_results' THEN
          IF (row->>'project_id')::uuid<>pid OR NOT EXISTS(SELECT 1 FROM statistical_result_inputs
            WHERE statistical_result_id=node.id) THEN
            RAISE EXCEPTION 'same-project completed analysis required' USING ERRCODE='P17F2';
          END IF;
          material:=jsonb_build_object('analysis_type',row->'analysis_type',
            'result_payload',row->'result_payload','analysis_definition',row->'analysis_definition');
        WHEN 'metric_definition_versions' THEN
          material:=jsonb_build_object('definition',row->'definition','unit',row->'unit',
            'aggregation',row->'aggregation');
        WHEN 'experiment_spec_versions' THEN
          IF NOT EXISTS(SELECT 1 FROM experiment_specs WHERE id=(row->>'experiment_spec_id')::uuid
            AND project_id=pid) THEN
            RAISE EXCEPTION 'same-project specification required' USING ERRCODE='P17F2';
          END IF;
          material:=jsonb_build_object('title',row->'title','objective',row->'objective',
            'protocol',row->'protocol','planned_metrics',row->'planned_metrics',
            'seed_policy',row->'seed_policy','analysis_plan',row->'analysis_plan');
        WHEN 'dataset_snapshots' THEN
          material:=jsonb_build_object('manifest_hash',row->'manifest_hash',
            'selection_definition',row->'selection_definition');
        WHEN 'artifact_versions' THEN
          -- Raw CAS content is verified by the Application/store, not rehashed as JSON.
          IF row->>'content_hash' !~ '^[0-9a-f]{64}$' THEN
            RAISE EXCEPTION 'exact artifact byte binding required' USING ERRCODE='P17F2';
          END IF;
        WHEN 'runs' THEN
          IF (row->>'project_id')::uuid<>pid OR (row->>'status'<>'PLANNED'
            AND row->>'inputs_sealed_at' IS NULL) OR EXISTS(
            SELECT 1
          FROM run_artifact_inputs b JOIN artifact_versions v ON v.id=b.artifact_version_id
              JOIN artifacts p ON p.id=v.artifact_id WHERE b.run_id=node.id AND p.project_id<>pid)
            OR EXISTS(SELECT 1 FROM run_dataset_inputs b
              JOIN dataset_snapshots v ON v.id=b.dataset_snapshot_id
              JOIN datasets p ON p.id=v.dataset_id
          WHERE b.run_id=node.id AND p.project_id<>pid) THEN
            RAISE EXCEPTION 'sealed same-project run inputs required' USING ERRCODE='P17F2';
          END IF;
        WHEN 'source_versions' THEN
          SELECT pr216_ref('SourceVersion',v.id,v.content_hash) INTO previous
            FROM source_versions v WHERE v.id=(row->>'predecessor_source_version_id')::uuid;
          SELECT pr216_ref('ArtifactVersion',v.id,v.content_hash) INTO artifact
            FROM artifact_versions v WHERE v.id=(row->>'fulltext_artifact_version_id')::uuid;
          SELECT pr216_ref('ArtifactVersion',v.id,v.content_hash) INTO correction

          FROM artifact_versions v
          WHERE v.id=(row->>'correction_basis_artifact_version_id')::uuid;
          material:=jsonb_build_object('type','SourceVersion','material_version',1,
            'literature_source_id',row->'literature_source_id','version_kind',row->'version_kind',
            'predecessor_source_version',previous,'correction_basis_artifact',correction,
            'title',row->'title','abstract',row->'abstract','authors',row->'authors',
            'publication_date',row->'publication_date','venue',row->'venue',
            'external_version_label',row->'external_version_label','fulltext_artifact',artifact,
            'metadata',row->'metadata');
        WHEN 'literature_evidence' THEN
          SELECT pr216_ref('SourceVersion',v.id,v.content_hash) INTO bound FROM source_versions v
            WHERE v.id=(row->>'source_version_id')::uuid;
          IF (row->>'project_id')::uuid<>pid THEN
            RAISE EXCEPTION 'same-project literature required' USING ERRCODE='P17F2';
          END IF;
          material:=jsonb_build_object('type','LiteratureEvidence','material_version',1,
            'project_id',row->'project_id','source_version',bound,'evidence_type',row->'evidence_type',
            'locator',row->'locator','extracted_statement',row->'extracted_statement',
            'normalized_assertion',row->'normalized_assertion',
            'extraction_method',row->'extraction_method','confidence',row->'confidence');
        WHEN 'literature_support_snapshots' THEN
          SELECT pr216_ref('ClaimVersion',v.id,v.content_hash) INTO bound FROM claim_versions v
            WHERE v.id=(row->>'claim_version_id')::uuid;
          IF bound IS NULL OR (row->>'project_id')::uuid<>pid THEN
            RAISE EXCEPTION 'exact claim snapshot required' USING ERRCODE='P17F2';
          END IF;
          SELECT pr216_ref('LiteratureSupportSnapshot',v.id,v.content_hash) INTO previous
            FROM literature_support_snapshots v WHERE v.id=(row->>'previous_snapshot_id')::uuid;
          SELECT coalesce(jsonb_agg(jsonb_build_object('literature_evidence',
            pr216_ref('LiteratureEvidence',e.id,e.content_hash),'relation_type',b.relation_type,
            'ordinal',b.ordinal,'qualification',b.qualification)
              ORDER BY b.ordinal,e.id),'[]'::jsonb)
            INTO input_set FROM literature_evidence_relations b JOIN literature_evidence e
              ON e.id=b.literature_evidence_id WHERE b.literature_support_snapshot_id=node.id;
          IF pr216_hash(jsonb_build_object('type','LiteratureSupportSnapshotSupportSet',
            'material_version',1,'literature_inputs',input_set))
            <>row->>'literature_support_set_hash' THEN
            RAISE EXCEPTION 'snapshot input hash mismatch' USING ERRCODE='P17F2';
          END IF;
          material:=jsonb_build_object('type','LiteratureSupportSnapshot','material_version',1,
            'project_id',row->'project_id','target',bound,'snapshot_number',row->'snapshot_number',
            'previous_snapshot',previous,
            'literature_support_set_hash',row->'literature_support_set_hash');
        END CASE;
        IF material IS NOT NULL THEN expected:=pr216_hash(material); END IF;
        IF expected IS NOT NULL AND expected<>row->>'content_hash' THEN
          RAISE EXCEPTION 'scientific closure hash mismatch' USING ERRCODE='P17F2';
        END IF;
      END LOOP;

      FOR cv IN SELECT row.* FROM claim_versions row JOIN b10_closure(seed_kind,target) c
        ON c.id=row.id AND c.kind='claim_versions' LOOP
        IF cv.status NOT IN ('FROZEN','SUPERSEDED') OR cv.frozen_at IS NULL
          OR NOT EXISTS(SELECT 1 FROM claims parent WHERE parent.id=cv.claim_id AND parent.project_id=pid)
          OR pr216_hash(jsonb_build_object('statement',cv.statement,'scope',cv.scope,
            'qualification',cv.qualification,'support_set_hash',cv.support_set_hash)) IS DISTINCT FROM cv.content_hash
          OR cv.support_set_hash IS DISTINCT FROM (SELECT pr216_hash(coalesce(jsonb_agg(
            jsonb_build_object('source_type',CASE WHEN e.measurement_id IS NULL THEN
              'statistical_result' ELSE 'measurement' END,'source_id',
              coalesce(e.measurement_id,e.statistical_result_id),'relation_type',lower(e.relation_type),
              'qualification',e.qualification) ORDER BY
              CASE WHEN e.measurement_id IS NULL THEN 'statistical_result' ELSE 'measurement' END,
              coalesce(e.measurement_id,e.statistical_result_id),lower(e.relation_type),
              e.qualification IS NOT NULL,coalesce(e.qualification,'')),'[]'::jsonb))
            FROM evidence_relations e WHERE e.claim_version_id=cv.id) THEN
          RAISE EXCEPTION 'historical claim material corrupt' USING ERRCODE='P17F2'; END IF;
      END LOOP;
      FOR version IN SELECT row.* FROM scientific_conclusion_versions row JOIN b10_closure(seed_kind,target) c
        ON c.id=row.id AND c.kind='scientific_conclusion_versions' LOOP
        IF version.status NOT IN ('FROZEN','SUPERSEDED') OR version.frozen_at IS NULL
          OR NOT EXISTS(SELECT 1 FROM scientific_conclusions parent WHERE parent.id=version.scientific_conclusion_id AND parent.project_id=pid) THEN
          RAISE EXCEPTION 'historical frozen conclusion required' USING ERRCODE='P17F2'; END IF;
        SELECT coalesce(jsonb_agg(jsonb_build_object('claim_version',pr216_ref('ClaimVersion',c.id,c.content_hash),
          'literature_support_snapshot',pr216_ref('LiteratureSupportSnapshot',snapshot.id,snapshot.content_hash),
          'relation_type',input.relation_type,'ordinal',input.ordinal) ORDER BY input.ordinal),'[]'::jsonb)
          INTO claims FROM scientific_conclusion_claim_inputs input JOIN claim_versions c ON c.id=input.claim_version_id
          LEFT JOIN literature_support_snapshots snapshot ON snapshot.id=input.literature_support_snapshot_id
          WHERE input.conclusion_version_id=version.id;
        SELECT coalesce(jsonb_agg(jsonb_build_object('literature_evidence',pr216_ref('LiteratureEvidence',e.id,e.content_hash),
          'relation_type',input.relation_type,'ordinal',input.ordinal) ORDER BY input.ordinal),'[]'::jsonb)
          INTO literature FROM scientific_conclusion_literature_inputs input JOIN literature_evidence e ON e.id=input.literature_evidence_id
          WHERE input.conclusion_version_id=version.id;
        support:=pr216_hash(jsonb_build_object('type','ScientificConclusionVersionSupportSet','material_version',1,
          'claim_inputs',claims,'literature_inputs',literature));
        IF version.hash_scheme<>'sha256-cjson-v1' OR support IS DISTINCT FROM version.support_set_hash
          OR version.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','ScientificConclusionVersion',
          'material_version',1,'scientific_conclusion_id',version.scientific_conclusion_id,
          'statement',version.statement,'scope',version.scope,'confidence',version.confidence,
          'limitation_summary',version.limitation_summary,'support_set_hash',support)) THEN
          RAISE EXCEPTION 'historical conclusion material corrupt' USING ERRCODE='P17F2'; END IF;
      END LOOP;
    END $$;
CREATE FUNCTION b10_revision_verify(identity uuid,pid uuid) RETURNS void LANGUAGE plpgsql
SET search_path=pg_catalog, public, pg_temp AS $$
DECLARE a revision_actions; prior revision_actions; current_id uuid:=identity;
 visited uuid[]:=ARRAY[]::uuid[]; results jsonb; expected text; review internal_review_records;
BEGIN
 WHILE current_id IS NOT NULL LOOP
  IF current_id=ANY(visited) OR cardinality(visited)>=10000 THEN
   RAISE EXCEPTION 'bounded acyclic revision history required' USING ERRCODE='P10B1'; END IF;
  visited:=array_append(visited,current_id);
  SELECT * INTO a FROM revision_actions WHERE id=current_id;
  IF a.id IS NULL OR EXISTS(SELECT 1 FROM revision_actions WHERE id=a.id AND xmin::text::bigint=pg_current_xact_id()::text::bigint) THEN
   RAISE EXCEPTION 'prior committed revision history required' USING ERRCODE='P10B1'; END IF;
  PERFORM b06_validate_revision(a);
  SELECT review_row.* INTO review FROM internal_review_records review_row JOIN review_issues issue
    ON issue.review_record_id=review_row.id WHERE issue.id=a.review_issue_id;
  PERFORM b10_review_verify(review,pid);
  PERFORM b10_facts('RevisionAction',a.id,pid);
  SELECT * INTO prior FROM revision_actions WHERE id=a.supersedes_revision_action_id;
  results:=jsonb_build_object(
    'result_experiment_spec_version',(SELECT pr216_ref('ExperimentSpecVersion',v.id,v.content_hash) FROM experiment_spec_versions v WHERE v.id=a.result_experiment_spec_version_id),
    'result_run',CASE WHEN a.result_run_id IS NULL THEN NULL ELSE jsonb_build_object('type','Run','id',a.result_run_id) END,
    'result_statistical_result',(SELECT pr216_ref('StatisticalResult',v.id,v.content_hash) FROM statistical_results v WHERE v.id=a.result_statistical_result_id),
    'result_claim_version',(SELECT pr216_ref('ClaimVersion',v.id,v.content_hash) FROM claim_versions v WHERE v.id=a.result_claim_version_id),
    'result_scientific_conclusion_version',(SELECT pr216_ref('ScientificConclusionVersion',v.id,v.content_hash) FROM scientific_conclusion_versions v WHERE v.id=a.result_scientific_conclusion_version_id),
    'result_manuscript_version',(SELECT pr216_ref('ManuscriptVersion',v.id,v.content_hash) FROM manuscript_versions v WHERE v.id=a.result_manuscript_version_id),
    'result_source_version',(SELECT pr216_ref('SourceVersion',v.id,v.content_hash) FROM source_versions v WHERE v.id=a.result_source_version_id));
  expected:=pr216_hash(jsonb_build_object('type','RevisionAction','material_version',1,
    'review_issue',jsonb_build_object('type','ReviewIssue','id',a.review_issue_id),
    'decision',NULL,'action_type',a.action_type,'results',results,
    'supersedes_revision_action',pr216_ref('RevisionAction',prior.id,prior.content_hash),
    'created_by',jsonb_build_object('type','ActorIdentity','id',a.created_by)));
  IF a.hash_scheme<>'sha256-cjson-v1' OR a.content_hash IS DISTINCT FROM expected THEN
   RAISE EXCEPTION 'revision predecessor hash corrupt' USING ERRCODE='P17F2'; END IF;
  current_id:=a.supersedes_revision_action_id;
 END LOOP;
END $$;
CREATE FUNCTION b10_no_basis_cycle() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog, public, pg_temp AS $$
DECLARE root_kind text; root_id UUID; item text; node_kind text; node_id UUID;
 stack text[]; visited text[]:=ARRAY[]::text[]; active text[]:=ARRAY[]::text[];
 edge record; saved decision_records;
BEGIN
 root_kind:=CASE TG_TABLE_NAME WHEN 'revision_actions' THEN 'RevisionAction' WHEN 'approval_requests' THEN 'ApprovalRequest' ELSE 'DecisionRecord' END;
 IF TG_TABLE_NAME IN ('revision_actions','approval_requests','decision_records') THEN root_id:=NEW.id; ELSE root_id:=NEW.decision_id; END IF;
 stack:=ARRAY[root_kind||':'||root_id];
 WHILE cardinality(stack)>0 LOOP
  item:=stack[cardinality(stack)]; stack:=stack[1:cardinality(stack)-1];
  IF left(item,1)='!' THEN
   active:=array_remove(active,substring(item FROM 2));
   CONTINUE;
  END IF;
  IF item=ANY(active) THEN RAISE EXCEPTION 'typed basis cycle' USING ERRCODE='P10B1'; END IF;
  IF item=ANY(visited) THEN CONTINUE; END IF;
  visited:=array_append(visited,item);
  IF cardinality(visited)>10000 THEN RAISE EXCEPTION 'typed graph bound exceeded' USING ERRCODE='P10B1'; END IF;
  active:=array_append(active,item);
  stack:=array_append(stack,'!'||item);
  node_kind:=split_part(item,':',1); node_id:=split_part(item,':',2)::uuid;
  FOR edge IN SELECT child_kind,child_id FROM b10_edges WHERE kind=node_kind AND id=node_id LOOP
   stack:=array_append(stack,edge.child_kind||':'||edge.child_id);
  END LOOP;
 END LOOP;
 IF root_kind='DecisionRecord' THEN
  SELECT * INTO saved FROM decision_records WHERE id=root_id;
  IF saved.decision_type='RECONSIDER_REJECTION' AND NOT pr216_approver_active(saved.decided_by,saved.project_id) THEN
   RAISE EXCEPTION 'final graph authority required' USING ERRCODE='P16A1'; END IF;
 END IF;
 RETURN NULL;
END $$;

CREATE CONSTRAINT TRIGGER b10_no_basis_cycle AFTER INSERT ON decision_records DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b10_no_basis_cycle();

CREATE CONSTRAINT TRIGGER b10_no_basis_cycle AFTER INSERT ON decision_basis_conclusions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b10_no_basis_cycle();

CREATE CONSTRAINT TRIGGER b10_no_basis_cycle AFTER INSERT ON decision_basis_reviews DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b10_no_basis_cycle();

CREATE CONSTRAINT TRIGGER b10_no_basis_cycle AFTER INSERT ON decision_basis_approval_decisions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b10_no_basis_cycle();

CREATE CONSTRAINT TRIGGER b10_no_basis_cycle AFTER INSERT ON decision_basis_revision_actions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b10_no_basis_cycle();

CREATE CONSTRAINT TRIGGER b10_no_basis_cycle AFTER INSERT ON revision_actions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b10_no_basis_cycle();

CREATE CONSTRAINT TRIGGER b10_no_basis_cycle AFTER INSERT ON approval_requests DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b10_no_basis_cycle();
CREATE OR REPLACE FUNCTION pr215_basis_guard() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE target_id UUID; target_project UUID; parent_xmin bigint;
      decision_project UUID; target_status TEXT; target_hash TEXT;
    BEGIN
      IF (SELECT decision_type FROM decision_records WHERE id=NEW.decision_id)='RECONSIDER_REJECTION' THEN
        PERFORM b10_child_check(NEW.decision_id);
        RETURN NEW;
      END IF;
      IF (SELECT decision_type FROM decision_records WHERE id=NEW.decision_id)='READY_FOR_SUBMISSION' THEN
        IF TG_TABLE_NAME<>'decision_basis_reviews' THEN
          RAISE EXCEPTION 'readiness excludes conclusion basis' USING ERRCODE='P17F2'; END IF;
        PERFORM b11_check_basis(NEW.decision_id,
          (SELECT manuscript_version_id FROM decision_basis_manuscripts WHERE decision_id=NEW.decision_id));
        IF NOT EXISTS(SELECT 1 FROM internal_review_records r JOIN decision_basis_manuscripts b
          ON b.manuscript_version_id=r.manuscript_version_id JOIN manuscript_versions m ON m.id=b.manuscript_version_id
          JOIN decision_records d ON d.id=b.decision_id
          WHERE b.decision_id=NEW.decision_id AND r.id=NEW.internal_review_record_id
            AND r.project_id=d.project_id AND r.target_content_hash=m.content_hash
            AND r.claim_version_id IS NULL AND r.scientific_conclusion_version_id IS NULL AND r.artifact_version_id IS NULL) THEN
          RAISE EXCEPTION 'exact manuscript review required' USING ERRCODE='P17F2'; END IF;
        RETURN NEW;
      END IF;
      IF (SELECT decision_type FROM decision_records WHERE id=NEW.decision_id)='REVISION_RESPONSE' THEN
        LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, audit_findings, claims, correction_records, datasets, experiment_spec_versions, experiment_specs, impact_assessments, impact_targets, internal_review_records, literature_evidence, literature_evidence_review_events, literature_source_project_links, literature_sources, metric_definition_versions, metric_definitions, project_membership_events, project_memberships, project_role_assignments, projects, runs, scientific_conclusions, source_versions IN SHARE MODE;
        IF NOT EXISTS(SELECT 1 FROM decision_records WHERE id=NEW.decision_id AND xmin::text::bigint=pg_current_xact_id()::text::bigint) THEN
          RAISE EXCEPTION 'basis sealed to creation transaction' USING ERRCODE='P17F1'; END IF;
        IF TG_TABLE_NAME='decision_basis_conclusions' THEN
          PERFORM id FROM internal_review_records WHERE scientific_conclusion_version_id=NEW.scientific_conclusion_version_id ORDER BY id FOR SHARE;
        ELSE
          PERFORM x.id FROM internal_review_records x JOIN internal_review_records r ON r.id=NEW.internal_review_record_id
            WHERE x.project_id=r.project_id AND x.claim_version_id IS NOT DISTINCT FROM r.claim_version_id
              AND x.scientific_conclusion_version_id IS NOT DISTINCT FROM r.scientific_conclusion_version_id
            ORDER BY x.id FOR SHARE OF x;
        END IF;
        PERFORM b07_lock_concern(review_issue_id) FROM decision_revision_concerns WHERE decision_id=NEW.decision_id;
        RETURN NEW;
      END IF;
      IF TG_TABLE_NAME='decision_basis_conclusions' THEN
        target_id := NEW.scientific_conclusion_version_id;
      ELSE
        SELECT scientific_conclusion_version_id INTO target_id FROM internal_review_records
          WHERE id=NEW.internal_review_record_id;
      END IF;
      -- Same exact target exclusion as 0041; no parent/review lock precedes it.
      SELECT v.status,v.content_hash INTO target_status,target_hash
        FROM scientific_conclusion_versions v WHERE v.id=target_id FOR UPDATE;
      IF NOT FOUND OR target_status<>'FROZEN' OR target_hash IS NULL THEN
        RAISE EXCEPTION 'exact frozen conclusion basis required' USING ERRCODE='P17F2';
      END IF;
      SELECT c.project_id INTO target_project FROM scientific_conclusions c
        JOIN scientific_conclusion_versions v ON v.scientific_conclusion_id=c.id
        WHERE v.id=target_id FOR SHARE OF c;
      SELECT d.project_id,d.xmin::text::bigint INTO decision_project,parent_xmin
        FROM decision_records d WHERE d.id=NEW.decision_id;
      IF parent_xmin IS DISTINCT FROM pg_current_xact_id()::text::bigint
         OR decision_project IS DISTINCT FROM target_project THEN
        RAISE EXCEPTION 'new same-project typed decision basis required' USING ERRCODE='P17F2';
      END IF;
      IF EXISTS (SELECT 1 FROM decision_basis_conclusions b JOIN decision_records d
          ON d.id=b.decision_id WHERE b.scientific_conclusion_version_id=target_id
          AND d.project_id=decision_project AND d.decision_type='INTERNAL_SCIENTIFIC_RELEASE'
          AND d.id<>NEW.decision_id) THEN
        RAISE EXCEPTION 'initial decision scope already recorded' USING ERRCODE='P17F3';
      END IF;
      IF TG_TABLE_NAME='decision_basis_reviews' THEN
        IF NOT EXISTS (
            SELECT 1 FROM internal_review_records r WHERE r.id=NEW.internal_review_record_id
              AND r.project_id=decision_project AND r.target_content_hash=target_hash
              AND r.scientific_conclusion_version_id=target_id) THEN
          RAISE EXCEPTION 'exact review binding required' USING ERRCODE='P17F2';
        END IF;
      END IF;
      RETURN NEW;
    END $$;
CREATE OR REPLACE FUNCTION pr215_complete_basis() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE did UUID; tid UUID; pid UUID; target_hash TEXT; n INT;
    BEGIN
      IF TG_TABLE_NAME='decision_records' THEN did := NEW.id;
      ELSE did := NEW.decision_id; END IF;
      IF (SELECT decision_type FROM decision_records WHERE id=did)='RECONSIDER_REJECTION' THEN
        PERFORM b10_validate(did);
        RETURN NULL;
      END IF;
      IF (SELECT decision_type FROM decision_records WHERE id=did)='READY_FOR_SUBMISSION' THEN
        PERFORM b11_complete(did); RETURN NULL;
      END IF;
      IF EXISTS(SELECT 1 FROM decision_basis_manuscripts WHERE decision_id=did) THEN
        RAISE EXCEPTION 'manuscript basis requires readiness purpose' USING ERRCODE='P17F2'; END IF;
      IF (SELECT decision_type FROM decision_records WHERE id=did)='REVISION_RESPONSE' THEN
        PERFORM b07_validate_decision(did,true);
        RETURN NULL;
      END IF;
      IF EXISTS(SELECT 1 FROM decision_revision_concerns WHERE decision_id=did) OR EXISTS(SELECT 1 FROM decision_basis_claims WHERE decision_id=did) THEN
        RAISE EXCEPTION 'release cannot gain revision basis' USING ERRCODE='P17F2'; END IF;
      SELECT d.project_id,b.scientific_conclusion_version_id,v.content_hash
        INTO pid,tid,target_hash FROM decision_records d
        JOIN decision_basis_conclusions b ON b.decision_id=d.id
        JOIN scientific_conclusion_versions v ON v.id=b.scientific_conclusion_version_id
        WHERE d.id=did;
      IF tid IS NULL THEN
        RAISE EXCEPTION 'one exact conclusion basis required' USING ERRCODE='P17F2';
      END IF;
      IF NOT EXISTS (SELECT 1 FROM decision_basis_reviews WHERE decision_id=did)
         OR EXISTS (SELECT 1 FROM decision_basis_reviews b JOIN internal_review_records r
            ON r.id=b.internal_review_record_id WHERE b.decision_id=did
            AND (r.project_id<>pid OR r.scientific_conclusion_version_id IS DISTINCT FROM tid
                 OR r.target_content_hash<>target_hash))
         OR EXISTS (SELECT 1 FROM internal_review_records r
            WHERE r.project_id=pid AND r.scientific_conclusion_version_id=tid
              AND NOT EXISTS (SELECT 1 FROM decision_basis_reviews b
                WHERE b.decision_id=did AND b.internal_review_record_id=r.id)) THEN
        RAISE EXCEPTION 'complete exact review basis required' USING ERRCODE='P17F2';
      END IF;
      IF EXISTS (SELECT 1 FROM review_issues i JOIN internal_review_records r
           ON r.id=i.review_record_id WHERE r.project_id=pid
             AND r.scientific_conclusion_version_id=tid
             AND i.status='OPEN' AND i.severity='BLOCKING') THEN
        RAISE EXCEPTION 'applicable blocking issue remains open' USING ERRCODE='P17F2';
      END IF;
      SELECT count(*) INTO n FROM decision_basis_reviews WHERE decision_id=did;
      -- R2 lexical kind order is InternalReviewRecord before ScientificConclusionVersion.
      IF (SELECT ordinal FROM decision_basis_conclusions WHERE decision_id=did)<>n
         OR EXISTS (SELECT 1 FROM (
           SELECT b.ordinal,row_number() OVER (ORDER BY b.internal_review_record_id)-1 AS expected
           FROM decision_basis_reviews b WHERE b.decision_id=did) positions
           WHERE ordinal<>expected) THEN
        RAISE EXCEPTION 'canonical contiguous basis ordinals required' USING ERRCODE='P17F2';
      END IF;
      RETURN NULL;
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

CREATE OR REPLACE FUNCTION pr216_material_gate(r approval_requests) RETURNS void LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE v scientific_conclusion_versions; d decision_records;
      review_row internal_review_records;
      basis JSONB; claims JSONB; literature JSONB; support TEXT; cv claim_versions;
      basis_before TIMESTAMPTZ;
    BEGIN
      basis_before:=clock_timestamp();
      IF EXISTS(SELECT 1 FROM approval_requests WHERE id=r.id) THEN
        basis_before:=least(basis_before,r.requested_at);
      END IF;
      PERFORM pr216_facts(r.scientific_conclusion_version_id,r.project_id);
      SELECT * INTO v
          FROM scientific_conclusion_versions
          WHERE id=r.scientific_conclusion_version_id;
      SELECT coalesce(jsonb_agg(jsonb_build_object('claim_version',jsonb_build_object(
        'type','ClaimVersion','id',c.id,'content_hash',c.content_hash),
        'literature_support_snapshot',CASE WHEN s.id IS NULL THEN NULL ELSE
          jsonb_build_object('type','LiteratureSupportSnapshot','id',s.id,
            'content_hash',s.content_hash) END,'relation_type',b.relation_type,'ordinal',b.ordinal)
        ORDER BY b.ordinal),'[]'::jsonb) INTO claims
        FROM scientific_conclusion_claim_inputs b JOIN claim_versions c ON c.id=b.claim_version_id
        LEFT JOIN literature_support_snapshots s ON s.id=b.literature_support_snapshot_id
        WHERE b.conclusion_version_id=v.id;
      SELECT coalesce(jsonb_agg(jsonb_build_object('literature_evidence',jsonb_build_object(
        'type','LiteratureEvidence','id',e.id,'content_hash',e.content_hash),
        'relation_type',b.relation_type,'ordinal',b.ordinal) ORDER BY b.ordinal),'[]'::jsonb)
        INTO literature FROM scientific_conclusion_literature_inputs b
        JOIN literature_evidence e ON e.id=b.literature_evidence_id
          WHERE b.conclusion_version_id=v.id;
      support:=pr216_hash(jsonb_build_object('type','ScientificConclusionVersionSupportSet',
        'material_version',1,'claim_inputs',claims,'literature_inputs',literature));
      IF support IS DISTINCT FROM v.support_set_hash OR pr216_hash(jsonb_build_object(
        'type','ScientificConclusionVersion','material_version',1,'scientific_conclusion_id',
        v.scientific_conclusion_id,'statement',v.statement,'scope',v.scope,'confidence',v.confidence,
        'limitation_summary',v.limitation_summary,'support_set_hash',support))<>v.content_hash THEN
        RAISE EXCEPTION 'target material hash mismatch' USING ERRCODE='P17F2';
      END IF;
      FOR cv IN SELECT c.* FROM scientific_conclusion_claim_inputs b
        JOIN claim_versions c ON c.id=b.claim_version_id WHERE b.conclusion_version_id=v.id LOOP
        IF cv.status NOT IN ('FROZEN','SUPERSEDED') OR cv.frozen_at IS NULL
          OR pr216_hash(jsonb_build_object('statement',cv.statement,'scope',cv.scope,
            'qualification',cv.qualification,'support_set_hash',cv.support_set_hash))<>cv.content_hash
          OR cv.support_set_hash IS DISTINCT FROM (SELECT pr216_hash(coalesce(jsonb_agg(
            jsonb_build_object('source_type',CASE WHEN e.measurement_id IS NULL THEN
              'statistical_result' ELSE 'measurement' END,'source_id',
              coalesce(e.measurement_id,e.statistical_result_id),'relation_type',lower(e.relation_type),
              'qualification',e.qualification) ORDER BY
              CASE WHEN e.measurement_id IS NULL THEN 'statistical_result' ELSE 'measurement' END,
              coalesce(e.measurement_id,e.statistical_result_id),lower(e.relation_type),
              e.qualification IS NOT NULL,coalesce(e.qualification,'')),'[]'::jsonb))
            FROM evidence_relations e WHERE e.claim_version_id=cv.id) THEN
          RAISE EXCEPTION 'claim material invalid' USING ERRCODE='P17F2';
        END IF;
        IF EXISTS(SELECT 1 FROM correction_records WHERE project_id=r.project_id
          AND lower(target_type)='claim_version' AND target_id=cv.id) OR EXISTS(
          SELECT 1 FROM impact_targets t JOIN impact_assessments a ON a.id=t.impact_assessment_id
          LEFT JOIN audit_findings f ON f.id=a.audit_finding_id WHERE a.project_id=r.project_id
          AND lower(t.target_type)='claim_version' AND t.target_id=cv.id
          AND lower(f.status) IS DISTINCT
          FROM 'dismissed' AND lower(a.conclusion)<>'no_impact') THEN
          RAISE EXCEPTION 'current claim invalid' USING ERRCODE='P16T1';
        END IF;
      END LOOP;
      IF EXISTS(WITH effective AS (
        SELECT b.literature_evidence_id,b.relation_type,v.created_by AS author
          FROM scientific_conclusion_literature_inputs b
          WHERE b.conclusion_version_id=v.id UNION ALL
        SELECT e.literature_evidence_id,e.relation_type,snapshot.created_by
          FROM scientific_conclusion_claim_inputs b
          JOIN literature_support_snapshots snapshot ON snapshot.id=b.literature_support_snapshot_id
          JOIN literature_evidence_relations e ON e.literature_support_snapshot_id=
            b.literature_support_snapshot_id WHERE b.conclusion_version_id=v.id)
        SELECT 1 FROM effective b JOIN literature_evidence e ON e.id=b.literature_evidence_id
          JOIN source_versions s ON s.id=e.source_version_id
          JOIN literature_sources p ON p.id=s.literature_source_id
          LEFT JOIN source_versions current ON current.id=p.current_version_id
        WHERE s.status NOT IN ('FROZEN','SUPERSEDED') OR s.version_kind='RETRACTED'
          OR current.version_kind='RETRACTED'
          OR (current.version_kind='CORRECTED' AND current.id<>s.id)
          OR e.review_status IN ('DISPUTED','REJECTED')
          OR (b.relation_type='SUPPORTS' AND (e.review_status<>'VERIFIED' OR NOT EXISTS(
            SELECT 1 FROM literature_evidence_review_events event JOIN actors actor
              ON actor.id=event.reviewed_by
            WHERE event.id=(SELECT latest.id FROM literature_evidence_review_events latest
              WHERE latest.literature_evidence_id=e.id
              ORDER BY latest.reviewed_at DESC,latest.id DESC
              LIMIT 1) AND event.new_status='VERIFIED' AND actor.actor_type='HUMAN'
              AND event.reviewed_by<>e.created_by AND event.reviewed_by<>b.author)))) THEN
        RAISE EXCEPTION 'current evidence invalid' USING ERRCODE='P16T1';
      END IF;
      FOR review_row IN SELECT * FROM internal_review_records WHERE project_id=r.project_id
        AND scientific_conclusion_version_id=v.id ORDER BY id LOOP
        IF review_row.created_at>clock_timestamp() OR (
          review_row.created_at>basis_before AND EXISTS(SELECT 1 FROM decision_basis_reviews
            WHERE decision_id=r.basis_decision_id AND internal_review_record_id=review_row.id)) THEN
          RAISE EXCEPTION 'prior committed review required' USING ERRCODE='P16B1';
        END IF;
        IF review_row.target_content_hash<>v.content_hash
          OR review_row.hash_scheme<>'sha256-cjson-v1'
          OR pr216_hash(jsonb_build_object('type','InternalReviewRecord','material_version',1,
            'project_id',review_row.project_id,'target',jsonb_build_object('type','ScientificConclusionVersion',
              'id',v.id,'content_hash',v.content_hash),'reviewer_actor_id',review_row.reviewer_actor_id,
              'review_type',review_row.review_type,'recommendation',review_row.recommendation,'summary',review_row.summary))
            <>review_row.content_hash OR NOT EXISTS(
            SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id
            JOIN project_role_assignments role ON role.membership_id=m.id
              AND role.actor_id=m.actor_id AND role.project_id=m.project_id
            WHERE a.id=review_row.reviewer_actor_id
          AND a.actor_type='HUMAN'
          AND a.created_at<=review_row.created_at

          AND (a.retired_at IS NULL
          OR review_row.created_at<a.retired_at)
          AND m.project_id=r.project_id
              AND m.started_at<=review_row.created_at AND role.role IN ('OWNER','REVIEWER')
              AND role.effective_from<=review_row.created_at
              AND (role.effective_until IS NULL OR review_row.created_at<role.effective_until)
              AND (SELECT e.new_status FROM project_membership_events e
                WHERE e.membership_id=m.id AND e.occurred_at<=review_row.created_at
                ORDER BY e.occurred_at DESC,e.id DESC LIMIT 1)='ACTIVE'
              AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=a.id
                AND b.bound_at<=review_row.created_at
          AND ( b.revoked_at IS NULL OR review_row.created_at<b.revoked_at)))
          OR review_row.reviewer_actor_id IN (SELECT pr216_authors(v.id)) THEN
          RAISE EXCEPTION 'matching review material invalid' USING ERRCODE='P17F2';
        END IF;
      END LOOP;
      SELECT * INTO d FROM decision_records WHERE id=r.basis_decision_id;
      SELECT jsonb_agg(jsonb_build_object('target',jsonb_build_object('type',kind,'id',id,
        'content_hash',digest),'ordinal',ordinal) ORDER BY kind,id,digest) INTO basis FROM (
        SELECT 'ScientificConclusionVersion' AS kind,b.scientific_conclusion_version_id AS id,
          c.content_hash AS digest,b.ordinal FROM decision_basis_conclusions b
          JOIN scientific_conclusion_versions c ON c.id=b.scientific_conclusion_version_id
          WHERE b.decision_id=d.id UNION ALL SELECT 'InternalReviewRecord',
          b.internal_review_record_id,x.content_hash,b.ordinal FROM decision_basis_reviews b
          JOIN internal_review_records x ON x.id=b.internal_review_record_id
          WHERE b.decision_id=d.id) refs;
      IF d.decided_at>basis_before OR NOT pr216_decision_authorized(d) THEN
        RAISE EXCEPTION 'prior committed decision required' USING ERRCODE='P16B1';
      END IF;
      IF d.hash_scheme<>'sha256-cjson-v1' OR d.basis_set_hash IS DISTINCT FROM pr216_hash(
        jsonb_build_object('type','DecisionRecordBasisSet','material_version',1,'basis',basis))
        OR d.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','DecisionRecord',
          'material_version',1,'project_id',d.project_id,'decision_type',d.decision_type,
          'question',d.question,'decision',d.decision,'rationale',d.rationale,'decided_by',
          jsonb_build_object('type','ActorIdentity','id',d.decided_by),'supersedes_decision_id',NULL,
          'basis_set_hash',d.basis_set_hash)) THEN
        RAISE EXCEPTION 'saved decision material invalid' USING ERRCODE='P16B1';
      END IF;
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
      PERFORM b10_successor_check(r,NULL);
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
-- New review freshness is server time after coordination, never supplied future time.
CREATE OR REPLACE FUNCTION pr214_review_guard() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog, public, pg_temp AS $$
    DECLARE target_status TEXT; target_hash TEXT; target_project UUID;
      target_author UUID; target_frozen TIMESTAMPTZ;
    BEGIN
      IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'internal review is immutable' USING ERRCODE='P17E1';
      END IF;
      IF NEW.claim_version_id IS NOT NULL THEN
        SELECT v.status,v.content_hash,c.project_id,v.created_by,v.frozen_at
          INTO target_status,target_hash,target_project,target_author,target_frozen
          FROM claim_versions v JOIN claims c ON c.id=v.claim_id
          WHERE v.id=NEW.claim_version_id FOR SHARE OF v,c;
      ELSIF NEW.scientific_conclusion_version_id IS NOT NULL THEN
        -- Exact target first; never acquire SHARE and upgrade during Issue INSERT.
        PERFORM 1 FROM scientific_conclusion_versions
          WHERE id=NEW.scientific_conclusion_version_id FOR UPDATE;
        IF NOT FOUND THEN
          RAISE EXCEPTION 'exact independent frozen review target required'
            USING ERRCODE='P17E2';
        END IF;
        SELECT v.status,v.content_hash,c.project_id,v.created_by,v.frozen_at
          INTO target_status,target_hash,target_project,target_author,target_frozen
          FROM scientific_conclusion_versions v
          JOIN scientific_conclusions c ON c.id=v.scientific_conclusion_id
          WHERE v.id=NEW.scientific_conclusion_version_id FOR SHARE OF c;
      ELSIF NEW.artifact_version_id IS NOT NULL THEN
        SELECT v.status,v.content_hash,a.project_id,v.created_by,v.frozen_at
          INTO target_status,target_hash,target_project,target_author,target_frozen
          FROM artifact_versions v JOIN artifacts a ON a.id=v.artifact_id
          WHERE v.id=NEW.artifact_version_id FOR SHARE OF v,a;
      ELSE
        PERFORM 1 FROM manuscript_versions WHERE id=NEW.manuscript_version_id FOR UPDATE;
        IF NOT FOUND THEN
          RAISE EXCEPTION 'exact frozen manuscript required' USING ERRCODE='P17E2';
        END IF;
        PERFORM 1 FROM manuscript_versions WHERE id=NEW.manuscript_version_id
          AND placement_set_hash IS NOT NULL;
        IF NOT FOUND THEN
          RAISE EXCEPTION 'complete manuscript seal required' USING ERRCODE='P17E2';
        END IF;
        SELECT v.status,v.content_hash,p.project_id,v.created_by,v.frozen_at
          INTO target_status,target_hash,target_project,target_author,target_frozen
          FROM manuscript_versions v JOIN publications p ON p.id=v.publication_id
          WHERE v.id=NEW.manuscript_version_id FOR SHARE OF p;
      END IF;
      IF target_status NOT IN ('FROZEN','SUPERSEDED') OR target_frozen IS NULL
         OR target_hash IS DISTINCT FROM NEW.target_content_hash
         OR target_project IS DISTINCT FROM NEW.project_id
         OR target_author IS NULL OR target_author=NEW.reviewer_actor_id
         OR NOT EXISTS (SELECT 1 FROM actors a WHERE a.id=NEW.reviewer_actor_id
                       AND a.actor_type='HUMAN' AND a.retired_at IS NULL) THEN
        RAISE EXCEPTION 'exact independent frozen review target required'
          USING ERRCODE='P17E2';
      END IF;
      NEW.created_at:=clock_timestamp();
      RETURN NEW;
    END $$;
"""

DOWNGRADE_SQL = r"""
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM decision_records WHERE decision_type='RECONSIDER_REJECTION')
 OR EXISTS(SELECT 1 FROM approval_requests WHERE reconsideration_decision_id IS NOT NULL)
 THEN RAISE EXCEPTION 'cannot discard reconsideration history'; END IF;
END $$;
DROP TRIGGER b10_no_basis_cycle ON decision_records;
DROP TRIGGER b10_no_basis_cycle ON decision_basis_conclusions;
DROP TRIGGER b10_no_basis_cycle ON decision_basis_reviews;
DROP TRIGGER b10_no_basis_cycle ON decision_basis_approval_decisions;
DROP TRIGGER b10_no_basis_cycle ON decision_basis_revision_actions;
DROP TRIGGER b10_no_basis_cycle ON revision_actions;
DROP TRIGGER b10_no_basis_cycle ON approval_requests;
DROP FUNCTION b10_no_basis_cycle(); DROP FUNCTION b10_revision_verify(uuid,uuid);
DROP FUNCTION b10_facts(text,uuid,uuid); DROP FUNCTION b10_closure(text,uuid); DROP VIEW b10_edges;
CREATE OR REPLACE FUNCTION pr215_basis_guard() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE target_id UUID; target_project UUID; parent_xmin bigint;
      decision_project UUID; target_status TEXT; target_hash TEXT;
    BEGIN
      IF (SELECT decision_type FROM decision_records WHERE id=NEW.decision_id)='READY_FOR_SUBMISSION' THEN
        IF TG_TABLE_NAME<>'decision_basis_reviews' THEN
          RAISE EXCEPTION 'readiness excludes conclusion basis' USING ERRCODE='P17F2'; END IF;
        PERFORM b11_check_basis(NEW.decision_id,
          (SELECT manuscript_version_id FROM decision_basis_manuscripts WHERE decision_id=NEW.decision_id));
        IF NOT EXISTS(SELECT 1 FROM internal_review_records r JOIN decision_basis_manuscripts b
          ON b.manuscript_version_id=r.manuscript_version_id JOIN manuscript_versions m ON m.id=b.manuscript_version_id
          JOIN decision_records d ON d.id=b.decision_id
          WHERE b.decision_id=NEW.decision_id AND r.id=NEW.internal_review_record_id
            AND r.project_id=d.project_id AND r.target_content_hash=m.content_hash
            AND r.claim_version_id IS NULL AND r.scientific_conclusion_version_id IS NULL AND r.artifact_version_id IS NULL) THEN
          RAISE EXCEPTION 'exact manuscript review required' USING ERRCODE='P17F2'; END IF;
        RETURN NEW;
      END IF;
      IF (SELECT decision_type FROM decision_records WHERE id=NEW.decision_id)='REVISION_RESPONSE' THEN
        LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, audit_findings, claims, correction_records, datasets, experiment_spec_versions, experiment_specs, impact_assessments, impact_targets, internal_review_records, literature_evidence, literature_evidence_review_events, literature_source_project_links, literature_sources, metric_definition_versions, metric_definitions, project_membership_events, project_memberships, project_role_assignments, projects, runs, scientific_conclusions, source_versions IN SHARE MODE;
        IF NOT EXISTS(SELECT 1 FROM decision_records WHERE id=NEW.decision_id AND xmin::text::bigint=pg_current_xact_id()::text::bigint) THEN
          RAISE EXCEPTION 'basis sealed to creation transaction' USING ERRCODE='P17F1'; END IF;
        IF TG_TABLE_NAME='decision_basis_conclusions' THEN
          PERFORM id FROM internal_review_records WHERE scientific_conclusion_version_id=NEW.scientific_conclusion_version_id ORDER BY id FOR SHARE;
        ELSE
          PERFORM x.id FROM internal_review_records x JOIN internal_review_records r ON r.id=NEW.internal_review_record_id
            WHERE x.project_id=r.project_id AND x.claim_version_id IS NOT DISTINCT FROM r.claim_version_id
              AND x.scientific_conclusion_version_id IS NOT DISTINCT FROM r.scientific_conclusion_version_id
            ORDER BY x.id FOR SHARE OF x;
        END IF;
        PERFORM b07_lock_concern(review_issue_id) FROM decision_revision_concerns WHERE decision_id=NEW.decision_id;
        RETURN NEW;
      END IF;
      IF TG_TABLE_NAME='decision_basis_conclusions' THEN
        target_id := NEW.scientific_conclusion_version_id;
      ELSE
        SELECT scientific_conclusion_version_id INTO target_id FROM internal_review_records
          WHERE id=NEW.internal_review_record_id;
      END IF;
      -- Same exact target exclusion as 0041; no parent/review lock precedes it.
      SELECT v.status,v.content_hash INTO target_status,target_hash
        FROM scientific_conclusion_versions v WHERE v.id=target_id FOR UPDATE;
      IF NOT FOUND OR target_status<>'FROZEN' OR target_hash IS NULL THEN
        RAISE EXCEPTION 'exact frozen conclusion basis required' USING ERRCODE='P17F2';
      END IF;
      SELECT c.project_id INTO target_project FROM scientific_conclusions c
        JOIN scientific_conclusion_versions v ON v.scientific_conclusion_id=c.id
        WHERE v.id=target_id FOR SHARE OF c;
      SELECT d.project_id,d.xmin::text::bigint INTO decision_project,parent_xmin
        FROM decision_records d WHERE d.id=NEW.decision_id;
      IF parent_xmin IS DISTINCT FROM pg_current_xact_id()::text::bigint
         OR decision_project IS DISTINCT FROM target_project THEN
        RAISE EXCEPTION 'new same-project typed decision basis required' USING ERRCODE='P17F2';
      END IF;
      IF EXISTS (SELECT 1 FROM decision_basis_conclusions b JOIN decision_records d
          ON d.id=b.decision_id WHERE b.scientific_conclusion_version_id=target_id
          AND d.project_id=decision_project AND d.decision_type='INTERNAL_SCIENTIFIC_RELEASE'
          AND d.id<>NEW.decision_id) THEN
        RAISE EXCEPTION 'initial decision scope already recorded' USING ERRCODE='P17F3';
      END IF;
      IF TG_TABLE_NAME='decision_basis_reviews' THEN
        IF NOT EXISTS (
            SELECT 1 FROM internal_review_records r WHERE r.id=NEW.internal_review_record_id
              AND r.project_id=decision_project AND r.target_content_hash=target_hash
              AND r.scientific_conclusion_version_id=target_id) THEN
          RAISE EXCEPTION 'exact review binding required' USING ERRCODE='P17F2';
        END IF;
      END IF;
      RETURN NEW;
    END $$;
CREATE OR REPLACE FUNCTION pr215_complete_basis() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE did UUID; tid UUID; pid UUID; target_hash TEXT; n INT;
    BEGIN
      IF TG_TABLE_NAME='decision_records' THEN did := NEW.id;
      ELSE did := NEW.decision_id; END IF;
      IF (SELECT decision_type FROM decision_records WHERE id=did)='READY_FOR_SUBMISSION' THEN
        PERFORM b11_complete(did); RETURN NULL;
      END IF;
      IF EXISTS(SELECT 1 FROM decision_basis_manuscripts WHERE decision_id=did) THEN
        RAISE EXCEPTION 'manuscript basis requires readiness purpose' USING ERRCODE='P17F2'; END IF;
      IF (SELECT decision_type FROM decision_records WHERE id=did)='REVISION_RESPONSE' THEN
        PERFORM b07_validate_decision(did,true);
        RETURN NULL;
      END IF;
      IF EXISTS(SELECT 1 FROM decision_revision_concerns WHERE decision_id=did) OR EXISTS(SELECT 1 FROM decision_basis_claims WHERE decision_id=did) THEN
        RAISE EXCEPTION 'release cannot gain revision basis' USING ERRCODE='P17F2'; END IF;
      SELECT d.project_id,b.scientific_conclusion_version_id,v.content_hash
        INTO pid,tid,target_hash FROM decision_records d
        JOIN decision_basis_conclusions b ON b.decision_id=d.id
        JOIN scientific_conclusion_versions v ON v.id=b.scientific_conclusion_version_id
        WHERE d.id=did;
      IF tid IS NULL THEN
        RAISE EXCEPTION 'one exact conclusion basis required' USING ERRCODE='P17F2';
      END IF;
      IF NOT EXISTS (SELECT 1 FROM decision_basis_reviews WHERE decision_id=did)
         OR EXISTS (SELECT 1 FROM decision_basis_reviews b JOIN internal_review_records r
            ON r.id=b.internal_review_record_id WHERE b.decision_id=did
            AND (r.project_id<>pid OR r.scientific_conclusion_version_id IS DISTINCT FROM tid
                 OR r.target_content_hash<>target_hash))
         OR EXISTS (SELECT 1 FROM internal_review_records r
            WHERE r.project_id=pid AND r.scientific_conclusion_version_id=tid
              AND NOT EXISTS (SELECT 1 FROM decision_basis_reviews b
                WHERE b.decision_id=did AND b.internal_review_record_id=r.id)) THEN
        RAISE EXCEPTION 'complete exact review basis required' USING ERRCODE='P17F2';
      END IF;
      IF EXISTS (SELECT 1 FROM review_issues i JOIN internal_review_records r
           ON r.id=i.review_record_id WHERE r.project_id=pid
             AND r.scientific_conclusion_version_id=tid
             AND i.status='OPEN' AND i.severity='BLOCKING') THEN
        RAISE EXCEPTION 'applicable blocking issue remains open' USING ERRCODE='P17F2';
      END IF;
      SELECT count(*) INTO n FROM decision_basis_reviews WHERE decision_id=did;
      -- R2 lexical kind order is InternalReviewRecord before ScientificConclusionVersion.
      IF (SELECT ordinal FROM decision_basis_conclusions WHERE decision_id=did)<>n
         OR EXISTS (SELECT 1 FROM (
           SELECT b.ordinal,row_number() OVER (ORDER BY b.internal_review_record_id)-1 AS expected
           FROM decision_basis_reviews b WHERE b.decision_id=did) positions
           WHERE ordinal<>expected) THEN
        RAISE EXCEPTION 'canonical contiguous basis ordinals required' USING ERRCODE='P17F2';
      END IF;
      RETURN NULL;
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
CREATE OR REPLACE FUNCTION b09_preheld() RETURNS void LANGUAGE plpgsql
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
CREATE OR REPLACE FUNCTION pr216_material_gate(r approval_requests) RETURNS void LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE v scientific_conclusion_versions; d decision_records;
      review_row internal_review_records;
      basis JSONB; claims JSONB; literature JSONB; support TEXT; cv claim_versions;
      basis_before TIMESTAMPTZ;
    BEGIN
      basis_before:=clock_timestamp();
      IF EXISTS(SELECT 1 FROM approval_requests WHERE id=r.id) THEN
        basis_before:=least(basis_before,r.requested_at);
      END IF;
      PERFORM pr216_facts(r.scientific_conclusion_version_id,r.project_id);
      SELECT * INTO v
          FROM scientific_conclusion_versions
          WHERE id=r.scientific_conclusion_version_id;
      SELECT coalesce(jsonb_agg(jsonb_build_object('claim_version',jsonb_build_object(
        'type','ClaimVersion','id',c.id,'content_hash',c.content_hash),
        'literature_support_snapshot',CASE WHEN s.id IS NULL THEN NULL ELSE
          jsonb_build_object('type','LiteratureSupportSnapshot','id',s.id,
            'content_hash',s.content_hash) END,'relation_type',b.relation_type,'ordinal',b.ordinal)
        ORDER BY b.ordinal),'[]'::jsonb) INTO claims
        FROM scientific_conclusion_claim_inputs b JOIN claim_versions c ON c.id=b.claim_version_id
        LEFT JOIN literature_support_snapshots s ON s.id=b.literature_support_snapshot_id
        WHERE b.conclusion_version_id=v.id;
      SELECT coalesce(jsonb_agg(jsonb_build_object('literature_evidence',jsonb_build_object(
        'type','LiteratureEvidence','id',e.id,'content_hash',e.content_hash),
        'relation_type',b.relation_type,'ordinal',b.ordinal) ORDER BY b.ordinal),'[]'::jsonb)
        INTO literature FROM scientific_conclusion_literature_inputs b
        JOIN literature_evidence e ON e.id=b.literature_evidence_id
          WHERE b.conclusion_version_id=v.id;
      support:=pr216_hash(jsonb_build_object('type','ScientificConclusionVersionSupportSet',
        'material_version',1,'claim_inputs',claims,'literature_inputs',literature));
      IF support IS DISTINCT FROM v.support_set_hash OR pr216_hash(jsonb_build_object(
        'type','ScientificConclusionVersion','material_version',1,'scientific_conclusion_id',
        v.scientific_conclusion_id,'statement',v.statement,'scope',v.scope,'confidence',v.confidence,
        'limitation_summary',v.limitation_summary,'support_set_hash',support))<>v.content_hash THEN
        RAISE EXCEPTION 'target material hash mismatch' USING ERRCODE='P17F2';
      END IF;
      FOR cv IN SELECT c.* FROM scientific_conclusion_claim_inputs b
        JOIN claim_versions c ON c.id=b.claim_version_id WHERE b.conclusion_version_id=v.id LOOP
        IF cv.status NOT IN ('FROZEN','SUPERSEDED') OR cv.frozen_at IS NULL
          OR pr216_hash(jsonb_build_object('statement',cv.statement,'scope',cv.scope,
            'qualification',cv.qualification,'support_set_hash',cv.support_set_hash))<>cv.content_hash
          OR cv.support_set_hash IS DISTINCT FROM (SELECT pr216_hash(coalesce(jsonb_agg(
            jsonb_build_object('source_type',CASE WHEN e.measurement_id IS NULL THEN
              'statistical_result' ELSE 'measurement' END,'source_id',
              coalesce(e.measurement_id,e.statistical_result_id),'relation_type',lower(e.relation_type),
              'qualification',e.qualification) ORDER BY
              CASE WHEN e.measurement_id IS NULL THEN 'statistical_result' ELSE 'measurement' END,
              coalesce(e.measurement_id,e.statistical_result_id),lower(e.relation_type),
              e.qualification IS NOT NULL,coalesce(e.qualification,'')),'[]'::jsonb))
            FROM evidence_relations e WHERE e.claim_version_id=cv.id) THEN
          RAISE EXCEPTION 'claim material invalid' USING ERRCODE='P17F2';
        END IF;
        IF EXISTS(SELECT 1 FROM correction_records WHERE project_id=r.project_id
          AND lower(target_type)='claim_version' AND target_id=cv.id) OR EXISTS(
          SELECT 1 FROM impact_targets t JOIN impact_assessments a ON a.id=t.impact_assessment_id
          LEFT JOIN audit_findings f ON f.id=a.audit_finding_id WHERE a.project_id=r.project_id
          AND lower(t.target_type)='claim_version' AND t.target_id=cv.id
          AND lower(f.status) IS DISTINCT
          FROM 'dismissed' AND lower(a.conclusion)<>'no_impact') THEN
          RAISE EXCEPTION 'current claim invalid' USING ERRCODE='P16T1';
        END IF;
      END LOOP;
      IF EXISTS(WITH effective AS (
        SELECT b.literature_evidence_id,b.relation_type,v.created_by AS author
          FROM scientific_conclusion_literature_inputs b
          WHERE b.conclusion_version_id=v.id UNION ALL
        SELECT e.literature_evidence_id,e.relation_type,snapshot.created_by
          FROM scientific_conclusion_claim_inputs b
          JOIN literature_support_snapshots snapshot ON snapshot.id=b.literature_support_snapshot_id
          JOIN literature_evidence_relations e ON e.literature_support_snapshot_id=
            b.literature_support_snapshot_id WHERE b.conclusion_version_id=v.id)
        SELECT 1 FROM effective b JOIN literature_evidence e ON e.id=b.literature_evidence_id
          JOIN source_versions s ON s.id=e.source_version_id
          JOIN literature_sources p ON p.id=s.literature_source_id
          LEFT JOIN source_versions current ON current.id=p.current_version_id
        WHERE s.status NOT IN ('FROZEN','SUPERSEDED') OR s.version_kind='RETRACTED'
          OR current.version_kind='RETRACTED'
          OR (current.version_kind='CORRECTED' AND current.id<>s.id)
          OR e.review_status IN ('DISPUTED','REJECTED')
          OR (b.relation_type='SUPPORTS' AND (e.review_status<>'VERIFIED' OR NOT EXISTS(
            SELECT 1 FROM literature_evidence_review_events event JOIN actors actor
              ON actor.id=event.reviewed_by
            WHERE event.id=(SELECT latest.id FROM literature_evidence_review_events latest
              WHERE latest.literature_evidence_id=e.id
              ORDER BY latest.reviewed_at DESC,latest.id DESC
              LIMIT 1) AND event.new_status='VERIFIED' AND actor.actor_type='HUMAN'
              AND event.reviewed_by<>e.created_by AND event.reviewed_by<>b.author)))) THEN
        RAISE EXCEPTION 'current evidence invalid' USING ERRCODE='P16T1';
      END IF;
      FOR review_row IN SELECT * FROM internal_review_records WHERE project_id=r.project_id
        AND scientific_conclusion_version_id=v.id ORDER BY id FOR SHARE LOOP
        IF review_row.created_at>clock_timestamp() OR (
          review_row.created_at>basis_before AND EXISTS(SELECT 1 FROM decision_basis_reviews
            WHERE decision_id=r.basis_decision_id AND internal_review_record_id=review_row.id)) THEN
          RAISE EXCEPTION 'prior committed review required' USING ERRCODE='P16B1';
        END IF;
        IF review_row.target_content_hash<>v.content_hash
          OR review_row.hash_scheme<>'sha256-cjson-v1'
          OR pr216_hash(jsonb_build_object('type','InternalReviewRecord','material_version',1,
            'project_id',review_row.project_id,'target',jsonb_build_object('type','ScientificConclusionVersion',
              'id',v.id,'content_hash',v.content_hash),'reviewer_actor_id',review_row.reviewer_actor_id,
              'review_type',review_row.review_type,'recommendation',review_row.recommendation,'summary',review_row.summary))
            <>review_row.content_hash OR NOT EXISTS(
            SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id
            JOIN project_role_assignments role ON role.membership_id=m.id
              AND role.actor_id=m.actor_id AND role.project_id=m.project_id
            WHERE a.id=review_row.reviewer_actor_id
          AND a.actor_type='HUMAN'
          AND a.created_at<=review_row.created_at

          AND (a.retired_at IS NULL
          OR review_row.created_at<a.retired_at)
          AND m.project_id=r.project_id
              AND m.started_at<=review_row.created_at AND role.role IN ('OWNER','REVIEWER')
              AND role.effective_from<=review_row.created_at
              AND (role.effective_until IS NULL OR review_row.created_at<role.effective_until)
              AND (SELECT e.new_status FROM project_membership_events e
                WHERE e.membership_id=m.id AND e.occurred_at<=review_row.created_at
                ORDER BY e.occurred_at DESC,e.id DESC LIMIT 1)='ACTIVE'
              AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=a.id
                AND b.bound_at<=review_row.created_at
          AND ( b.revoked_at IS NULL OR review_row.created_at<b.revoked_at)))
          OR review_row.reviewer_actor_id IN (SELECT pr216_authors(v.id)) THEN
          RAISE EXCEPTION 'matching review material invalid' USING ERRCODE='P17F2';
        END IF;
      END LOOP;
      SELECT * INTO d FROM decision_records WHERE id=r.basis_decision_id;
      SELECT jsonb_agg(jsonb_build_object('target',jsonb_build_object('type',kind,'id',id,
        'content_hash',digest),'ordinal',ordinal) ORDER BY kind,id,digest) INTO basis FROM (
        SELECT 'ScientificConclusionVersion' AS kind,b.scientific_conclusion_version_id AS id,
          c.content_hash AS digest,b.ordinal FROM decision_basis_conclusions b
          JOIN scientific_conclusion_versions c ON c.id=b.scientific_conclusion_version_id
          WHERE b.decision_id=d.id UNION ALL SELECT 'InternalReviewRecord',
          b.internal_review_record_id,x.content_hash,b.ordinal FROM decision_basis_reviews b
          JOIN internal_review_records x ON x.id=b.internal_review_record_id
          WHERE b.decision_id=d.id) refs;
      IF d.decided_at>basis_before OR NOT pr216_decision_authorized(d) THEN
        RAISE EXCEPTION 'prior committed decision required' USING ERRCODE='P16B1';
      END IF;
      IF d.hash_scheme<>'sha256-cjson-v1' OR d.basis_set_hash IS DISTINCT FROM pr216_hash(
        jsonb_build_object('type','DecisionRecordBasisSet','material_version',1,'basis',basis))
        OR d.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','DecisionRecord',
          'material_version',1,'project_id',d.project_id,'decision_type',d.decision_type,
          'question',d.question,'decision',d.decision,'rationale',d.rationale,'decided_by',
          jsonb_build_object('type','ActorIdentity','id',d.decided_by),'supersedes_decision_id',NULL,
          'basis_set_hash',d.basis_set_hash)) THEN
        RAISE EXCEPTION 'saved decision material invalid' USING ERRCODE='P16B1';
      END IF;
    END $$;
DROP TRIGGER b10_decision_guard ON decision_records;
DROP TRIGGER b10_complete_decision ON decision_records;
DROP TABLE decision_basis_approval_decisions;
DROP TABLE decision_basis_revision_actions;
DROP FUNCTION b10_complete(); DROP FUNCTION b10_basis_guard(); DROP FUNCTION b10_child_check(UUID);
DROP FUNCTION b10_decision_guard(); DROP FUNCTION b10_validate(UUID); DROP FUNCTION b10_successor_check(approval_requests,UUID);
DROP FUNCTION b10_refs(UUID); DROP FUNCTION b10_material_gate(approval_requests);
DROP FUNCTION b10_explanation(text); DROP FUNCTION b10_review_verify(internal_review_records,UUID); DROP FUNCTION b10_normalize(jsonb);
DROP INDEX uq_b10_successor_reconsideration;
ALTER TABLE approval_requests DROP CONSTRAINT ck_b10_request_links;
ALTER TABLE decision_records DROP CONSTRAINT ck_b10_decision_pair;
ALTER TABLE decision_records DROP CONSTRAINT ck_b10_text_bounds;
ALTER TABLE decision_records DROP CONSTRAINT ck_b10_finite_time;
ALTER TABLE decision_records ADD CONSTRAINT ck_b11_decision_policy CHECK (
 (decision_type='INTERNAL_SCIENTIFIC_RELEASE' AND decision='PROCEED') OR
 (decision_type='REVISION_RESPONSE' AND decision IN ('REQUIRE_CHANGE','ACCEPT_NO_CHANGE')) OR
 (decision_type='READY_FOR_SUBMISSION' AND decision='PROCEED'));
ALTER TABLE approval_requests ADD CONSTRAINT approval_requests_prior_rejected_request_id_check CHECK(prior_rejected_request_id IS NULL);
ALTER TABLE approval_requests ADD CONSTRAINT approval_requests_reconsideration_decision_id_check CHECK(reconsideration_decision_id IS NULL);


CREATE OR REPLACE FUNCTION pr214_review_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE target_status TEXT; target_hash TEXT; target_project UUID;
      target_author UUID; target_frozen TIMESTAMPTZ;
    BEGIN
      IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'internal review is immutable' USING ERRCODE='P17E1';
      END IF;
      IF NEW.claim_version_id IS NOT NULL THEN
        SELECT v.status,v.content_hash,c.project_id,v.created_by,v.frozen_at
          INTO target_status,target_hash,target_project,target_author,target_frozen
          FROM claim_versions v JOIN claims c ON c.id=v.claim_id
          WHERE v.id=NEW.claim_version_id FOR SHARE OF v,c;
      ELSIF NEW.scientific_conclusion_version_id IS NOT NULL THEN
        -- Exact target first; never acquire SHARE and upgrade during Issue INSERT.
        PERFORM 1 FROM scientific_conclusion_versions
          WHERE id=NEW.scientific_conclusion_version_id FOR UPDATE;
        IF NOT FOUND THEN
          RAISE EXCEPTION 'exact independent frozen review target required'
            USING ERRCODE='P17E2';
        END IF;
        SELECT v.status,v.content_hash,c.project_id,v.created_by,v.frozen_at
          INTO target_status,target_hash,target_project,target_author,target_frozen
          FROM scientific_conclusion_versions v
          JOIN scientific_conclusions c ON c.id=v.scientific_conclusion_id
          WHERE v.id=NEW.scientific_conclusion_version_id FOR SHARE OF c;
      ELSIF NEW.artifact_version_id IS NOT NULL THEN
        SELECT v.status,v.content_hash,a.project_id,v.created_by,v.frozen_at
          INTO target_status,target_hash,target_project,target_author,target_frozen
          FROM artifact_versions v JOIN artifacts a ON a.id=v.artifact_id
          WHERE v.id=NEW.artifact_version_id FOR SHARE OF v,a;
      ELSE
        PERFORM 1 FROM manuscript_versions WHERE id=NEW.manuscript_version_id FOR UPDATE;
        IF NOT FOUND THEN
          RAISE EXCEPTION 'exact frozen manuscript required' USING ERRCODE='P17E2';
        END IF;
        PERFORM 1 FROM manuscript_versions WHERE id=NEW.manuscript_version_id
          AND placement_set_hash IS NOT NULL;
        IF NOT FOUND THEN
          RAISE EXCEPTION 'complete manuscript seal required' USING ERRCODE='P17E2';
        END IF;
        SELECT v.status,v.content_hash,p.project_id,v.created_by,v.frozen_at
          INTO target_status,target_hash,target_project,target_author,target_frozen
          FROM manuscript_versions v JOIN publications p ON p.id=v.publication_id
          WHERE v.id=NEW.manuscript_version_id FOR SHARE OF p;
      END IF;
      IF target_status NOT IN ('FROZEN','SUPERSEDED') OR target_frozen IS NULL
         OR target_hash IS DISTINCT FROM NEW.target_content_hash
         OR target_project IS DISTINCT FROM NEW.project_id
         OR target_author IS NULL OR target_author=NEW.reviewer_actor_id
         OR NOT EXISTS (SELECT 1 FROM actors a WHERE a.id=NEW.reviewer_actor_id
                       AND a.actor_type='HUMAN' AND a.retired_at IS NULL) THEN
        RAISE EXCEPTION 'exact independent frozen review target required'
          USING ERRCODE='P17E2';
      END IF;
      RETURN NEW;
    END $$;
"""
