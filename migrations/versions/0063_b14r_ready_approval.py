"""B14r exact READY approval permission; no publication or consumption effects."""

# Frozen predecessor SQL preserves unrelated purposes and exact downgrade definitions.
# ruff: noqa: E501
from alembic import op

revision = "0063_b14r_ready_approval"
down_revision = "0062_b14a_publication_entry"
branch_labels = None
depends_on = None

B14R_SNAPSHOT_TABLES = (
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

PREDECESSOR_GATE_SQL = r"""
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

PREDECESSOR_COMPLETE_SQL = r"""
CREATE OR REPLACE FUNCTION public.pr216_complete()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
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
        AND e.prior_status IS NULL AND e.xmin=pg_current_xact_id()::xid) THEN
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
        AND d.xmin=pg_current_xact_id()::xid
        AND NOT pr216_approver_active(d.decided_by,r.project_id)) THEN
        RAISE EXCEPTION 'final decision authority required' USING ERRCODE='P16A1';
      END IF;
      IF EXISTS(SELECT 1 FROM approval_decisions d WHERE d.id=did
        AND d.xmin=pg_current_xact_id()::xid
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
    END $function$;
"""

UPGRADE_SQL = r"""
LOCK TABLE approval_decisions,approval_grant_events,approval_grants,approval_request_events,approval_request_reviews,approval_requests IN ACCESS EXCLUSIVE MODE;
CREATE FUNCTION b14r_saved_decision(did UUID,tid UUID,pid UUID) RETURNS void
 LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE d decision_records; m manuscript_versions; rr internal_review_records; refs JSONB; bh TEXT;
BEGIN
 SELECT * INTO d FROM decision_records WHERE id=did;
 SELECT * INTO m FROM manuscript_versions WHERE id=tid;
 IF d.id IS NULL OR d.project_id IS DISTINCT FROM pid OR d.decision_type<>'READY_FOR_SUBMISSION'
 OR d.decision<>'PROCEED' OR d.supersedes_decision_id IS NOT NULL OR d.hash_scheme<>'sha256-cjson-v1'
 OR NOT pr216_decision_authorized(d) OR d.decided_by IN (SELECT b11_authors(tid))
 OR NOT EXISTS(SELECT 1 FROM decision_basis_manuscripts WHERE decision_id=did AND manuscript_version_id=tid)
 OR EXISTS(SELECT 1 FROM decision_basis_conclusions WHERE decision_id=did)
 OR EXISTS(SELECT 1 FROM decision_basis_claims WHERE decision_id=did)
 OR EXISTS(SELECT 1 FROM decision_revision_concerns WHERE decision_id=did)
 OR EXISTS(SELECT 1 FROM decision_basis_approval_decisions WHERE decision_id=did)
 OR EXISTS(SELECT 1 FROM decision_basis_revision_actions WHERE decision_id=did)
 OR (SELECT count(*) FROM decision_basis_manuscripts WHERE decision_id=did)<>1
 OR NOT EXISTS(SELECT 1 FROM publications WHERE id=m.publication_id AND project_id=pid)
 OR (SELECT count(*) FROM decision_basis_reviews WHERE decision_id=did) NOT BETWEEN 1 AND 100
 OR (SELECT ordinal FROM decision_basis_manuscripts WHERE decision_id=did)<>
    (SELECT count(*) FROM decision_basis_reviews WHERE decision_id=did)
 OR EXISTS(SELECT 1 FROM (SELECT ordinal,row_number() OVER(ORDER BY internal_review_record_id)-1 expected
    FROM decision_basis_reviews WHERE decision_id=did) positions WHERE ordinal<>expected) THEN
  RAISE EXCEPTION 'exact saved READY basis required' USING ERRCODE='P16B1'; END IF;
 FOR rr IN SELECT r.* FROM internal_review_records r JOIN decision_basis_reviews b
  ON b.internal_review_record_id=r.id WHERE b.decision_id=did ORDER BY r.id LOOP
  IF rr.project_id IS DISTINCT FROM pid OR rr.manuscript_version_id IS DISTINCT FROM tid
  OR rr.target_content_hash IS DISTINCT FROM m.content_hash OR rr.created_at>d.decided_at
  OR rr.claim_version_id IS NOT NULL OR rr.scientific_conclusion_version_id IS NOT NULL
  OR rr.artifact_version_id IS NOT NULL
  OR rr.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','InternalReviewRecord','material_version',1,
   'project_id',rr.project_id,'target',pr216_ref('ManuscriptVersion',m.id,m.content_hash),
   'reviewer_actor_id',rr.reviewer_actor_id,'review_type',rr.review_type,'recommendation',rr.recommendation,'summary',rr.summary))
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
  RAISE EXCEPTION 'saved READY digest invalid' USING ERRCODE='P17F2'; END IF;
END $$;
CREATE FUNCTION b14r_approval_gate(r approval_requests,approver UUID) RETURNS void
 LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE m manuscript_versions; d decision_records; rr internal_review_records; iid UUID;
BEGIN
 SELECT * INTO m FROM manuscript_versions WHERE id=r.manuscript_version_id;
 SELECT * INTO d FROM decision_records WHERE id=r.basis_decision_id;
 IF NOT EXISTS(SELECT 1 FROM projects WHERE id=r.project_id AND lifecycle_status='ACTIVE')
 OR NOT EXISTS(SELECT 1 FROM publications WHERE id=m.publication_id AND project_id=r.project_id
  AND lifecycle_status='INTERNAL_REVIEW') THEN
  RAISE EXCEPTION 'INTERNAL_REVIEW active project required' USING ERRCODE='P16G1'; END IF;
 IF m.id IS NULL OR m.status<>'FROZEN' OR m.frozen_at IS NULL OR m.placement_set_hash IS NULL
 OR m.content_hash IS DISTINCT FROM r.target_content_hash OR m.hash_scheme IS DISTINCT FROM r.target_hash_scheme
 OR NOT EXISTS(SELECT 1 FROM publications WHERE id=m.publication_id AND current_manuscript_version_id=m.id) THEN
  RAISE EXCEPTION 'sealed selected manuscript required' USING ERRCODE='P16T1'; END IF;
 PERFORM b14r_saved_decision(d.id,m.id,r.project_id);
 IF d.decided_at>coalesce(r.requested_at,clock_timestamp()) THEN
  RAISE EXCEPTION 'prior committed Decision required' USING ERRCODE='P16B1'; END IF;
 IF r.prior_rejected_request_id IS NOT NULL OR r.reconsideration_decision_id IS NOT NULL THEN
  RAISE EXCEPTION 'READY successor unavailable' USING ERRCODE='P16B1'; END IF;
 PERFORM b14a_verify_entry(m.publication_id);
 PERFORM b04_verify_structure(m.id);
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
        PERFORM b14r_approval_gate(r,approver); RETURN;
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
CREATE OR REPLACE FUNCTION public.pr216_complete()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
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
        AND e.prior_status IS NULL AND e.xmin=pg_current_xact_id()::xid) THEN
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
        AND d.xmin=pg_current_xact_id()::xid
        AND NOT pr216_approver_active(d.decided_by,r.project_id)) THEN
        RAISE EXCEPTION 'final decision authority required' USING ERRCODE='P16A1';
      END IF;
      IF EXISTS(SELECT 1 FROM approval_decisions d WHERE d.id=did
        AND d.xmin=pg_current_xact_id()::xid
        AND d.valid_until IS NOT NULL AND clock_timestamp()>=d.valid_until) THEN
        RAISE EXCEPTION 'final conditional expiry reached' USING ERRCODE='23514';
      END IF;

      -- Only this transaction's creation/decision invokes current READY admission.
      -- Grant lifecycle updates must retain historical verification semantics.
      IF r.approval_purpose='READY_FOR_SUBMISSION' AND (
        EXISTS(SELECT 1 FROM approval_request_events e WHERE e.request_id=r.id
          AND e.prior_status IS NULL AND e.xmin=pg_current_xact_id()::xid)
        OR EXISTS(SELECT 1 FROM approval_decisions d WHERE d.id=did
          AND d.xmin=pg_current_xact_id()::xid)) THEN
        PERFORM pr216_gate(r,(SELECT decided_by FROM approval_decisions
          WHERE id=did AND xmin=pg_current_xact_id()::xid));
      END IF;
      IF (r.status='DECIDED') IS DISTINCT FROM (did IS NOT NULL) THEN
        RAISE EXCEPTION 'complete decision history required' USING ERRCODE='P16G1';
      END IF;
      IF did IS NOT NULL AND ((outcome<>'REJECT') IS DISTINCT FROM
        EXISTS(SELECT 1 FROM approval_grants WHERE approval_decision_id=did)) THEN
        RAISE EXCEPTION 'atomic grant required' USING ERRCODE='P16G1';
      END IF; RETURN NULL;
    END $function$;
"""

DOWNGRADE_PREFIX_SQL = r"""
LOCK TABLE approval_decisions,approval_grant_events,approval_grants,approval_request_events,approval_request_reviews,approval_requests IN ACCESS EXCLUSIVE MODE;
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM approval_requests WHERE approval_purpose='READY_FOR_SUBMISSION')
 OR EXISTS(SELECT 1 FROM approval_decisions d JOIN approval_requests r ON r.id=d.approval_request_id WHERE r.approval_purpose='READY_FOR_SUBMISSION')
 OR EXISTS(SELECT 1 FROM approval_grants WHERE purpose='READY_FOR_SUBMISSION') THEN
 RAISE EXCEPTION 'READY approval history prevents downgrade' USING ERRCODE='P17F1'; END IF;
END $$;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_PREFIX_SQL)
    op.execute(PREDECESSOR_GATE_SQL)
    op.execute(PREDECESSOR_COMPLETE_SQL)
    op.execute("DROP FUNCTION b14r_approval_gate(approval_requests,UUID)")
    op.execute("DROP FUNCTION b14r_saved_decision(UUID,UUID,UUID)")
