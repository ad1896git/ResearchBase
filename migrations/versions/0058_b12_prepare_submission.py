"""B12 PREPARE judgment and exact approval tuple, without lifecycle effects."""

# Frozen predecessor definitions retain unrelated purposes and safe xid comparisons.
# ruff: noqa: E501
from alembic import op

revision = "0058_b12_prepare_submission"
down_revision = "0057_xid_wraparound_guards"
branch_labels = None
depends_on = None

B12_SNAPSHOT_TABLES = (
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
    "publications",
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
LOCK TABLE decision_basis_approval_decisions,decision_basis_claims,decision_basis_conclusions,decision_basis_manuscripts,decision_basis_reviews,decision_basis_revision_actions,decision_records,decision_revision_concerns IN ACCESS EXCLUSIVE MODE;
ALTER TABLE decision_records DROP CONSTRAINT ck_b10_decision_pair;
ALTER TABLE decision_records ADD CONSTRAINT ck_b12_decision_policy CHECK ((decision_type='INTERNAL_SCIENTIFIC_RELEASE' AND decision='PROCEED') OR
 (decision_type='REVISION_RESPONSE' AND decision IN ('REQUIRE_CHANGE','ACCEPT_NO_CHANGE')) OR
 (decision_type='READY_FOR_SUBMISSION' AND decision='PROCEED') OR
 (decision_type='RECONSIDER_REJECTION' AND decision IN ('REVISED_TARGET','CORRECTED_REVIEW')) OR (decision_type='PREPARE_SUBMISSION' AND decision='PROCEED'));
ALTER TABLE decision_records ADD CONSTRAINT ck_b12_text_bounds CHECK (decision_type<>'PREPARE_SUBMISSION' OR (length(question) BETWEEN 1 AND 16000 AND length(rationale) BETWEEN 1 AND 16000 AND question=normalize(question,NFC) AND rationale=normalize(rationale,NFC)));

CREATE FUNCTION b12_saved_decision(did UUID,tid UUID,pid UUID) RETURNS void
 LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE d decision_records; m manuscript_versions; rr internal_review_records; refs JSONB; bh TEXT;
BEGIN
 SELECT * INTO d FROM decision_records WHERE id=did;
 SELECT * INTO m FROM manuscript_versions WHERE id=tid;
 IF d.id IS NULL OR d.project_id IS DISTINCT FROM pid OR d.decision_type<>'PREPARE_SUBMISSION'
 OR d.decision<>'PROCEED' OR d.supersedes_decision_id IS NOT NULL OR d.hash_scheme<>'sha256-cjson-v1'
 OR NOT pr216_decision_authorized(d) OR d.decided_by IN (SELECT b11_authors(tid))
 OR NOT EXISTS(SELECT 1 FROM decision_basis_manuscripts WHERE decision_id=did AND manuscript_version_id=tid)
 OR EXISTS(SELECT 1 FROM decision_basis_conclusions WHERE decision_id=did)
 OR EXISTS(SELECT 1 FROM decision_basis_claims WHERE decision_id=did)
 OR EXISTS(SELECT 1 FROM decision_revision_concerns WHERE decision_id=did)
 OR EXISTS(SELECT 1 FROM decision_basis_approval_decisions WHERE decision_id=did)
 OR EXISTS(SELECT 1 FROM decision_basis_revision_actions WHERE decision_id=did)
 OR NOT EXISTS(SELECT 1 FROM decision_basis_reviews WHERE decision_id=did) THEN
  RAISE EXCEPTION 'exact saved PREPARE basis required' USING ERRCODE='P16B1'; END IF;
 FOR rr IN SELECT r.* FROM internal_review_records r JOIN decision_basis_reviews b
  ON b.internal_review_record_id=r.id WHERE b.decision_id=did ORDER BY r.id LOOP
  IF rr.project_id IS DISTINCT FROM pid OR rr.manuscript_version_id IS DISTINCT FROM tid
  OR rr.target_content_hash IS DISTINCT FROM m.content_hash OR rr.created_at>d.decided_at
  OR rr.hash_scheme<>'sha256-cjson-v1' OR rr.reviewer_actor_id IN (SELECT b11_authors(tid))
  OR NOT EXISTS(SELECT 1 FROM actors a JOIN project_memberships mem ON mem.actor_id=a.id
 JOIN project_role_assignments role ON role.membership_id=mem.id AND role.actor_id=mem.actor_id AND role.project_id=mem.project_id
 WHERE a.id=rr.reviewer_actor_id AND a.actor_type='HUMAN' AND a.created_at<=rr.created_at
 AND (a.retired_at IS NULL OR rr.created_at<a.retired_at) AND mem.project_id=rr.project_id AND mem.started_at<=rr.created_at
 AND (SELECT e.new_status FROM project_membership_events e WHERE e.membership_id=mem.id AND e.occurred_at<=rr.created_at ORDER BY e.occurred_at DESC,e.id DESC LIMIT 1)='ACTIVE'
 AND role.role IN ('OWNER','REVIEWER') AND role.effective_from<=rr.created_at AND (role.effective_until IS NULL OR rr.created_at<role.effective_until)
 AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=a.id AND b.bound_at<=rr.created_at AND (b.revoked_at IS NULL OR rr.created_at<b.revoked_at))) THEN
   RAISE EXCEPTION 'independent saved manuscript review required' USING ERRCODE='P17F2'; END IF;
 END LOOP;
 SELECT jsonb_agg(jsonb_build_object('target',pr216_ref(kind,id,digest),'ordinal',pos) ORDER BY kind,id,digest)
 INTO refs FROM (SELECT *,row_number() OVER(ORDER BY kind,id,digest)-1 AS pos FROM (
  SELECT 'ManuscriptVersion' AS kind,m.id,m.content_hash AS digest
  UNION ALL SELECT 'InternalReviewRecord',r.id,r.content_hash FROM internal_review_records r
  JOIN decision_basis_reviews b ON b.internal_review_record_id=r.id WHERE b.decision_id=did) material) ordered;
 bh:=pr216_hash(jsonb_build_object('type','DecisionRecordBasisSet','material_version',1,'basis',refs));
 IF d.basis_set_hash IS DISTINCT FROM bh OR d.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object(
 'type','DecisionRecord','material_version',1,'project_id',d.project_id,'decision_type',d.decision_type,
 'question',d.question,'decision',d.decision,'rationale',d.rationale,'decided_by',jsonb_build_object('type','ActorIdentity','id',d.decided_by),
 'supersedes_decision_id',NULL,'basis_set_hash',bh)) THEN
  RAISE EXCEPTION 'saved PREPARE digest invalid' USING ERRCODE='P17F2'; END IF;
END $$;
CREATE FUNCTION b12_approval_gate(r approval_requests,approver UUID) RETURNS void
 LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE m manuscript_versions; d decision_records; rr internal_review_records; iid UUID;
BEGIN
 SELECT * INTO m FROM manuscript_versions WHERE id=r.manuscript_version_id;
 SELECT * INTO d FROM decision_records WHERE id=r.basis_decision_id;
 IF NOT EXISTS(SELECT 1 FROM projects WHERE id=r.project_id AND lifecycle_status='ACTIVE')
 OR NOT EXISTS(SELECT 1 FROM publications WHERE id=m.publication_id AND project_id=r.project_id
  AND lifecycle_status='READY') THEN
  RAISE EXCEPTION 'READY active project required' USING ERRCODE='P16G1'; END IF;
 IF m.id IS NULL OR m.status<>'FROZEN' OR m.frozen_at IS NULL OR m.placement_set_hash IS NULL
 OR m.content_hash IS DISTINCT FROM r.target_content_hash OR m.hash_scheme IS DISTINCT FROM r.target_hash_scheme
 OR NOT EXISTS(SELECT 1 FROM publications WHERE id=m.publication_id AND current_manuscript_version_id=m.id) THEN
  RAISE EXCEPTION 'sealed selected manuscript required' USING ERRCODE='P16T1'; END IF;
 PERFORM b12_saved_decision(d.id,m.id,r.project_id);
 IF d.decided_at>coalesce(r.requested_at,clock_timestamp()) THEN
  RAISE EXCEPTION 'prior committed Decision required' USING ERRCODE='P16B1'; END IF;
 PERFORM b10_successor_check(r,approver);
 FOR rr IN SELECT * FROM internal_review_records WHERE project_id=r.project_id AND manuscript_version_id=m.id ORDER BY id LOOP
  IF rr.target_content_hash IS DISTINCT FROM m.content_hash OR rr.hash_scheme<>'sha256-cjson-v1'
  OR rr.created_at>clock_timestamp() OR NOT EXISTS(SELECT 1 FROM actors a JOIN project_memberships mem ON mem.actor_id=a.id
 JOIN project_role_assignments role ON role.membership_id=mem.id AND role.actor_id=mem.actor_id AND role.project_id=mem.project_id
 WHERE a.id=rr.reviewer_actor_id AND a.actor_type='HUMAN' AND a.created_at<=rr.created_at
 AND (a.retired_at IS NULL OR rr.created_at<a.retired_at) AND mem.project_id=rr.project_id AND mem.started_at<=rr.created_at
 AND (SELECT e.new_status FROM project_membership_events e WHERE e.membership_id=mem.id AND e.occurred_at<=rr.created_at ORDER BY e.occurred_at DESC,e.id DESC LIMIT 1)='ACTIVE'
 AND role.role IN ('OWNER','REVIEWER') AND role.effective_from<=rr.created_at AND (role.effective_until IS NULL OR rr.created_at<role.effective_until)
 AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=a.id AND b.bound_at<=rr.created_at AND (b.revoked_at IS NULL OR rr.created_at<b.revoked_at)))
  OR rr.reviewer_actor_id IN (SELECT b11_authors(m.id))
  OR rr.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','InternalReviewRecord','material_version',1,
   'project_id',rr.project_id,'target',pr216_ref('ManuscriptVersion',m.id,m.content_hash),
   'reviewer_actor_id',rr.reviewer_actor_id,'review_type',rr.review_type,'recommendation',rr.recommendation,'summary',rr.summary)) THEN
    RAISE EXCEPTION 'matching manuscript review corrupt' USING ERRCODE='P17F2'; END IF;
 END LOOP;
 FOR iid IN SELECT i.id FROM review_issues i JOIN b11_applicable_reviews(m.id,r.project_id) review ON review.id=i.review_record_id ORDER BY i.id LOOP
  PERFORM b08_check_history(iid);
 END LOOP;
 IF EXISTS(SELECT 1 FROM review_issues i JOIN b11_applicable_reviews(m.id,r.project_id) review ON review.id=i.review_record_id
  WHERE i.status='OPEN' AND i.severity='BLOCKING') THEN
   RAISE EXCEPTION 'applicable OPEN blocker' USING ERRCODE='P16G1'; END IF;
 IF EXISTS(SELECT 1 FROM decision_basis_reviews b JOIN internal_review_records review ON review.id=b.internal_review_record_id
  WHERE b.decision_id=d.id AND review.reviewer_actor_id=r.requested_by) THEN
   RAISE EXCEPTION 'independent requester required' USING ERRCODE='P16C1'; END IF;
 IF approver IS NOT NULL THEN
  IF NOT pr216_approver_active(approver,r.project_id) THEN
   RAISE EXCEPTION 'HUMAN approver required' USING ERRCODE='P16A1'; END IF;
  IF approver IN (r.requested_by,d.decided_by) OR approver IN (SELECT b11_authors(m.id))
  OR EXISTS(SELECT 1 FROM decision_basis_reviews b JOIN internal_review_records review ON review.id=b.internal_review_record_id
    WHERE b.decision_id=d.id AND review.reviewer_actor_id=approver) THEN
   RAISE EXCEPTION 'independent approver required' USING ERRCODE='P16C1'; END IF;
  IF EXISTS(SELECT 1 FROM approval_requests q WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose
   AND q.manuscript_version_id<>m.id AND q.requested_at>r.requested_at) THEN
   RAISE EXCEPTION 'newer target selected' USING ERRCODE='P16T1'; END IF;
 END IF;
END $$;

CREATE OR REPLACE FUNCTION b11_decision_guard() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
BEGIN
 IF NEW.decision_type IN ('READY_FOR_SUBMISSION','PREPARE_SUBMISSION') THEN PERFORM b11_require_snapshot(); END IF;
 IF NEW.decision_type='PREPARE_SUBMISSION' THEN PERFORM pg_advisory_xact_lock(hashtextextended('b12:decision:'||NEW.id,0)); END IF;
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION public.b11_check_basis(did uuid, tid uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE m manuscript_versions; d decision_records; pid UUID;
BEGIN
 PERFORM b11_require_snapshot();
 SELECT * INTO m FROM manuscript_versions WHERE id=tid FOR UPDATE;
 SELECT * INTO d FROM decision_records WHERE id=did;
 IF NOT EXISTS(SELECT 1 FROM decision_records WHERE id=did AND xmin=pg_current_xact_id()::xid) THEN
   RAISE EXCEPTION 'basis sealed to creation transaction' USING ERRCODE='P17F1'; END IF;
 PERFORM id FROM projects WHERE id=d.project_id FOR SHARE;
 SELECT project_id INTO pid FROM publications WHERE id=m.publication_id FOR SHARE;
 IF d.decision_type NOT IN ('READY_FOR_SUBMISSION','PREPARE_SUBMISSION') OR pid IS DISTINCT FROM d.project_id
   OR m.id IS NULL OR m.status<>'FROZEN' OR m.frozen_at IS NULL OR m.placement_set_hash IS NULL
   OR m.content_hash IS NULL OR m.hash_scheme<>'sha256-cjson-v1'
   OR EXISTS(SELECT 1 FROM decision_basis_conclusions WHERE decision_id=did)
   OR EXISTS(SELECT 1 FROM decision_basis_claims WHERE decision_id=did)
   OR EXISTS(SELECT 1 FROM decision_revision_concerns WHERE decision_id=did) THEN
   RAISE EXCEPTION 'exact frozen same-project manuscript required' USING ERRCODE='P17F2'; END IF;
 IF EXISTS(SELECT 1 FROM decision_basis_manuscripts b JOIN decision_records x ON x.id=b.decision_id
   WHERE b.manuscript_version_id=tid AND x.project_id=d.project_id AND x.decision_type=d.decision_type AND x.id<>did) THEN
   RAISE EXCEPTION 'readiness scope already recorded' USING ERRCODE='P17F3'; END IF;
END $function$;
CREATE OR REPLACE FUNCTION b11_complete(did UUID) RETURNS void LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE d decision_records; m manuscript_versions; saved_review internal_review_records; n INT; iid UUID;
BEGIN
 SELECT * INTO d FROM decision_records WHERE id=did;
 SELECT v.* INTO m FROM decision_basis_manuscripts b JOIN manuscript_versions v ON v.id=b.manuscript_version_id WHERE b.decision_id=did;
 PERFORM b11_check_basis(did,m.id);
 SELECT count(*) INTO n FROM decision_basis_reviews WHERE decision_id=did;
 IF n NOT BETWEEN 1 AND 10000 OR d.decision<>'PROCEED' OR d.supersedes_decision_id IS NOT NULL
   OR NOT pr216_decision_authorized(d) OR d.decided_at>clock_timestamp()
   OR d.decided_by IN (SELECT b11_authors(m.id))
   OR NOT EXISTS(SELECT 1 FROM projects WHERE id=d.project_id AND lifecycle_status='ACTIVE')
   OR NOT EXISTS(SELECT 1 FROM publications WHERE id=m.publication_id AND project_id=d.project_id
     AND ((d.decision_type='READY_FOR_SUBMISSION' AND lifecycle_status IN ('DRAFTING','INTERNAL_REVIEW')) OR (d.decision_type='PREPARE_SUBMISSION' AND lifecycle_status='READY')) AND current_manuscript_version_id=m.id)
   OR EXISTS(SELECT 1 FROM internal_review_records r WHERE r.project_id=d.project_id AND r.manuscript_version_id=m.id
     AND NOT EXISTS(SELECT 1 FROM decision_basis_reviews b WHERE b.decision_id=did AND b.internal_review_record_id=r.id))
   OR EXISTS(SELECT 1 FROM decision_basis_reviews b JOIN internal_review_records r ON r.id=b.internal_review_record_id
     WHERE b.decision_id=did AND (r.project_id<>d.project_id OR r.manuscript_version_id IS DISTINCT FROM m.id
       OR r.target_content_hash IS DISTINCT FROM m.content_hash OR r.claim_version_id IS NOT NULL
       OR r.scientific_conclusion_version_id IS NOT NULL OR r.artifact_version_id IS NOT NULL))
   OR (SELECT ordinal FROM decision_basis_manuscripts WHERE decision_id=did)<>n
   OR EXISTS(SELECT 1 FROM (SELECT ordinal,row_number() OVER(ORDER BY internal_review_record_id)-1 AS expected
     FROM decision_basis_reviews WHERE decision_id=did) x WHERE ordinal<>expected) THEN
   RAISE EXCEPTION 'complete independent canonical readiness basis required' USING ERRCODE='P17F2'; END IF;
 FOR saved_review IN SELECT x.* FROM decision_basis_reviews b JOIN internal_review_records x ON x.id=b.internal_review_record_id WHERE b.decision_id=did LOOP
   IF saved_review.hash_scheme<>'sha256-cjson-v1' OR saved_review.created_at>d.decided_at
     OR saved_review.reviewer_actor_id IN (SELECT b11_authors(m.id)) OR NOT EXISTS(
       SELECT 1 FROM actors a JOIN project_memberships mem ON mem.actor_id=a.id
       JOIN project_role_assignments role ON role.membership_id=mem.id AND role.actor_id=mem.actor_id AND role.project_id=mem.project_id
       WHERE a.id=saved_review.reviewer_actor_id AND a.actor_type='HUMAN' AND a.created_at<=saved_review.created_at
         AND (a.retired_at IS NULL OR saved_review.created_at<a.retired_at) AND mem.project_id=d.project_id AND mem.started_at<=saved_review.created_at
         AND (SELECT e.new_status FROM project_membership_events e WHERE e.membership_id=mem.id AND e.occurred_at<=saved_review.created_at ORDER BY e.occurred_at DESC,e.id DESC LIMIT 1)='ACTIVE'
         AND role.role IN ('OWNER','REVIEWER') AND role.effective_from<=saved_review.created_at AND (role.effective_until IS NULL OR saved_review.created_at<role.effective_until)
         AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=a.id AND b.bound_at<=saved_review.created_at AND (b.revoked_at IS NULL OR saved_review.created_at<b.revoked_at))) THEN
     RAISE EXCEPTION 'historical independent HUMAN review required' USING ERRCODE='P17F2'; END IF;
 END LOOP;
 FOR iid IN SELECT i.id FROM review_issues i JOIN b11_applicable_reviews(m.id,d.project_id) r ON r.id=i.review_record_id ORDER BY i.id LOOP
   PERFORM b08_check_history(iid);
 END LOOP;
 IF EXISTS(SELECT 1 FROM review_issues i JOIN b11_applicable_reviews(m.id,d.project_id) r ON r.id=i.review_record_id WHERE i.status='OPEN' AND i.severity='BLOCKING') THEN
   RAISE EXCEPTION 'applicable OPEN blocker' USING ERRCODE='P17F2'; END IF;
IF d.decision_type='PREPARE_SUBMISSION' THEN PERFORM b12_saved_decision(did,m.id,d.project_id); END IF;
END $$;
CREATE OR REPLACE FUNCTION public.pr215_basis_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
    DECLARE target_id UUID; target_project UUID; parent_xmin xid;
      decision_project UUID; target_status TEXT; target_hash TEXT;
    BEGIN
      IF (SELECT decision_type FROM decision_records WHERE id=NEW.decision_id)='RECONSIDER_REJECTION' THEN
        PERFORM b10_child_check(NEW.decision_id);
        RETURN NEW;
      END IF;
      IF (SELECT decision_type FROM decision_records WHERE id=NEW.decision_id) IN ('READY_FOR_SUBMISSION','PREPARE_SUBMISSION') THEN
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
        IF NOT EXISTS(SELECT 1 FROM decision_records WHERE id=NEW.decision_id AND xmin=pg_current_xact_id()::xid) THEN
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
      SELECT d.project_id,d.xmin INTO decision_project,parent_xmin
        FROM decision_records d WHERE d.id=NEW.decision_id;
      IF parent_xmin IS DISTINCT FROM pg_current_xact_id()::xid
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
    END $function$;
CREATE OR REPLACE FUNCTION pr215_complete_basis() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE did UUID; tid UUID; pid UUID; target_hash TEXT; n INT;
    BEGIN
      IF TG_TABLE_NAME='decision_records' THEN did := NEW.id;
      ELSE did := NEW.decision_id; END IF;
      IF (SELECT decision_type FROM decision_records WHERE id=did)='RECONSIDER_REJECTION' THEN
        PERFORM b10_validate(did);
        RETURN NULL;
      END IF;
      IF (SELECT decision_type FROM decision_records WHERE id=did) IN ('READY_FOR_SUBMISSION','PREPARE_SUBMISSION') THEN
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
        IF r.approval_purpose='PREPARE_SUBMISSION' THEN
          PERFORM b12_approval_gate(r,approver); RETURN;
        END IF;
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
"""

DOWNGRADE_SQL = r"""
LOCK TABLE decision_basis_approval_decisions,decision_basis_claims,decision_basis_conclusions,decision_basis_manuscripts,decision_basis_reviews,decision_basis_revision_actions,decision_records,decision_revision_concerns IN ACCESS EXCLUSIVE MODE;
DO $$ BEGIN IF EXISTS(SELECT 1 FROM decision_records WHERE decision_type='PREPARE_SUBMISSION') OR EXISTS(SELECT 1 FROM approval_requests WHERE approval_purpose='PREPARE_SUBMISSION') THEN RAISE EXCEPTION 'PREPARE history cannot be discarded' USING ERRCODE='P17F2'; END IF; END $$;
CREATE OR REPLACE FUNCTION b11_decision_guard() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
BEGIN
 IF NEW.decision_type='READY_FOR_SUBMISSION' THEN PERFORM b11_require_snapshot(); END IF;
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION public.b11_check_basis(did uuid, tid uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE m manuscript_versions; d decision_records; pid UUID;
BEGIN
 PERFORM b11_require_snapshot();
 SELECT * INTO m FROM manuscript_versions WHERE id=tid FOR UPDATE;
 SELECT * INTO d FROM decision_records WHERE id=did;
 IF NOT EXISTS(SELECT 1 FROM decision_records WHERE id=did AND xmin=pg_current_xact_id()::xid) THEN
   RAISE EXCEPTION 'basis sealed to creation transaction' USING ERRCODE='P17F1'; END IF;
 PERFORM id FROM projects WHERE id=d.project_id FOR SHARE;
 SELECT project_id INTO pid FROM publications WHERE id=m.publication_id FOR SHARE;
 IF d.decision_type IS DISTINCT FROM 'READY_FOR_SUBMISSION' OR pid IS DISTINCT FROM d.project_id
   OR m.id IS NULL OR m.status<>'FROZEN' OR m.frozen_at IS NULL OR m.placement_set_hash IS NULL
   OR m.content_hash IS NULL OR m.hash_scheme<>'sha256-cjson-v1'
   OR EXISTS(SELECT 1 FROM decision_basis_conclusions WHERE decision_id=did)
   OR EXISTS(SELECT 1 FROM decision_basis_claims WHERE decision_id=did)
   OR EXISTS(SELECT 1 FROM decision_revision_concerns WHERE decision_id=did) THEN
   RAISE EXCEPTION 'exact frozen same-project manuscript required' USING ERRCODE='P17F2'; END IF;
 IF EXISTS(SELECT 1 FROM decision_basis_manuscripts b JOIN decision_records x ON x.id=b.decision_id
   WHERE b.manuscript_version_id=tid AND x.project_id=d.project_id AND x.decision_type='READY_FOR_SUBMISSION' AND x.id<>did) THEN
   RAISE EXCEPTION 'readiness scope already recorded' USING ERRCODE='P17F3'; END IF;
END $function$;
CREATE OR REPLACE FUNCTION b11_complete(did UUID) RETURNS void LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE d decision_records; m manuscript_versions; saved_review internal_review_records; n INT; iid UUID;
BEGIN
 SELECT * INTO d FROM decision_records WHERE id=did;
 SELECT v.* INTO m FROM decision_basis_manuscripts b JOIN manuscript_versions v ON v.id=b.manuscript_version_id WHERE b.decision_id=did;
 PERFORM b11_check_basis(did,m.id);
 SELECT count(*) INTO n FROM decision_basis_reviews WHERE decision_id=did;
 IF n NOT BETWEEN 1 AND 10000 OR d.decision<>'PROCEED' OR d.supersedes_decision_id IS NOT NULL
   OR NOT pr216_decision_authorized(d) OR d.decided_at>clock_timestamp()
   OR d.decided_by IN (SELECT b11_authors(m.id))
   OR NOT EXISTS(SELECT 1 FROM projects WHERE id=d.project_id AND lifecycle_status='ACTIVE')
   OR NOT EXISTS(SELECT 1 FROM publications WHERE id=m.publication_id AND project_id=d.project_id
     AND lifecycle_status IN ('DRAFTING','INTERNAL_REVIEW') AND current_manuscript_version_id=m.id)
   OR EXISTS(SELECT 1 FROM internal_review_records r WHERE r.project_id=d.project_id AND r.manuscript_version_id=m.id
     AND NOT EXISTS(SELECT 1 FROM decision_basis_reviews b WHERE b.decision_id=did AND b.internal_review_record_id=r.id))
   OR EXISTS(SELECT 1 FROM decision_basis_reviews b JOIN internal_review_records r ON r.id=b.internal_review_record_id
     WHERE b.decision_id=did AND (r.project_id<>d.project_id OR r.manuscript_version_id IS DISTINCT FROM m.id
       OR r.target_content_hash IS DISTINCT FROM m.content_hash OR r.claim_version_id IS NOT NULL
       OR r.scientific_conclusion_version_id IS NOT NULL OR r.artifact_version_id IS NOT NULL))
   OR (SELECT ordinal FROM decision_basis_manuscripts WHERE decision_id=did)<>n
   OR EXISTS(SELECT 1 FROM (SELECT ordinal,row_number() OVER(ORDER BY internal_review_record_id)-1 AS expected
     FROM decision_basis_reviews WHERE decision_id=did) x WHERE ordinal<>expected) THEN
   RAISE EXCEPTION 'complete independent canonical readiness basis required' USING ERRCODE='P17F2'; END IF;
 FOR saved_review IN SELECT x.* FROM decision_basis_reviews b JOIN internal_review_records x ON x.id=b.internal_review_record_id WHERE b.decision_id=did LOOP
   IF saved_review.hash_scheme<>'sha256-cjson-v1' OR saved_review.created_at>d.decided_at
     OR saved_review.reviewer_actor_id IN (SELECT b11_authors(m.id)) OR NOT EXISTS(
       SELECT 1 FROM actors a JOIN project_memberships mem ON mem.actor_id=a.id
       JOIN project_role_assignments role ON role.membership_id=mem.id AND role.actor_id=mem.actor_id AND role.project_id=mem.project_id
       WHERE a.id=saved_review.reviewer_actor_id AND a.actor_type='HUMAN' AND a.created_at<=saved_review.created_at
         AND (a.retired_at IS NULL OR saved_review.created_at<a.retired_at) AND mem.project_id=d.project_id AND mem.started_at<=saved_review.created_at
         AND (SELECT e.new_status FROM project_membership_events e WHERE e.membership_id=mem.id AND e.occurred_at<=saved_review.created_at ORDER BY e.occurred_at DESC,e.id DESC LIMIT 1)='ACTIVE'
         AND role.role IN ('OWNER','REVIEWER') AND role.effective_from<=saved_review.created_at AND (role.effective_until IS NULL OR saved_review.created_at<role.effective_until)
         AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=a.id AND b.bound_at<=saved_review.created_at AND (b.revoked_at IS NULL OR saved_review.created_at<b.revoked_at))) THEN
     RAISE EXCEPTION 'historical independent HUMAN review required' USING ERRCODE='P17F2'; END IF;
 END LOOP;
 FOR iid IN SELECT i.id FROM review_issues i JOIN b11_applicable_reviews(m.id,d.project_id) r ON r.id=i.review_record_id ORDER BY i.id LOOP
   PERFORM b08_check_history(iid);
 END LOOP;
 IF EXISTS(SELECT 1 FROM review_issues i JOIN b11_applicable_reviews(m.id,d.project_id) r ON r.id=i.review_record_id WHERE i.status='OPEN' AND i.severity='BLOCKING') THEN
   RAISE EXCEPTION 'applicable OPEN blocker' USING ERRCODE='P17F2'; END IF;
END $$;
CREATE OR REPLACE FUNCTION public.pr215_basis_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
    DECLARE target_id UUID; target_project UUID; parent_xmin xid;
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
        IF NOT EXISTS(SELECT 1 FROM decision_records WHERE id=NEW.decision_id AND xmin=pg_current_xact_id()::xid) THEN
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
      SELECT d.project_id,d.xmin INTO decision_project,parent_xmin
        FROM decision_records d WHERE d.id=NEW.decision_id;
      IF parent_xmin IS DISTINCT FROM pg_current_xact_id()::xid
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
    END $function$;
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
DROP FUNCTION b12_approval_gate(approval_requests,UUID);
DROP FUNCTION b12_saved_decision(UUID,UUID,UUID);
ALTER TABLE decision_records DROP CONSTRAINT ck_b12_decision_policy,DROP CONSTRAINT ck_b12_text_bounds;
ALTER TABLE decision_records ADD CONSTRAINT ck_b10_decision_pair CHECK ((decision_type='INTERNAL_SCIENTIFIC_RELEASE' AND decision='PROCEED') OR
 (decision_type='REVISION_RESPONSE' AND decision IN ('REQUIRE_CHANGE','ACCEPT_NO_CHANGE')) OR
 (decision_type='READY_FOR_SUBMISSION' AND decision='PROCEED') OR
 (decision_type='RECONSIDER_REJECTION' AND decision IN ('REVISED_TARGET','CORRECTED_REVIEW')));
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
