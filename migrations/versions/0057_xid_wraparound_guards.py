"""Keep transaction-identity guards correct across PostgreSQL XID epochs.

Only the xid representation changes; predicates, errors and lock order are retained.
Downgrade intentionally retains the safe guards. Owning older revisions remove
these functions when their schemas are dropped; epoch-unsafe checks are never restored.
"""

# Literal SQL preserves the owning functions for review.
# ruff: noqa: E501

from alembic import op

revision = "0057_xid_wraparound_guards"
down_revision = "0056_b10_reconsideration"
branch_labels = None
depends_on = None

FUNCTIONS = (
    # 0011_statistical_result.py
    r"""CREATE OR REPLACE FUNCTION reject_statistical_result_input_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'INSERT' AND
               EXISTS (
                   SELECT 1
                   FROM statistical_results
                   WHERE id = NEW.statistical_result_id
                     AND xmin = pg_current_xact_id()::xid
               ) THEN
                RETURN NEW;
            END IF;
            RAISE EXCEPTION 'statistical_result_inputs are immutable'
                USING ERRCODE = 'check_violation';
        END;
        $$""",
    # 0015_governance_audit.py
    r"""CREATE OR REPLACE FUNCTION allow_impact_target_only_with_new_parent() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
            parent_xmin xid;
        BEGIN
            SELECT xmin INTO parent_xmin
            FROM impact_assessments WHERE id = NEW.impact_assessment_id;
            IF parent_xmin IS NULL OR parent_xmin <> pg_current_xact_id()::xid THEN
                RAISE EXCEPTION 'impact targets may be inserted only with their new assessment'
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$""",
    # 0030_literature_evidence.py
    r"""CREATE OR REPLACE FUNCTION m3_support_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE s literature_support_snapshots; p UUID; st TEXT; prev literature_support_snapshots;
    BEGIN
      IF TG_TABLE_NAME='literature_evidence_relations' THEN
        SELECT * INTO s FROM literature_support_snapshots WHERE id=NEW.literature_support_snapshot_id;
        IF NOT EXISTS (SELECT 1 FROM literature_support_snapshots WHERE id=s.id AND xmin=pg_current_xact_id()::xid) THEN
          RAISE EXCEPTION 'M3 sealed relation set' USING ERRCODE='P17D1'; END IF;
        IF NEW.created_by<>s.created_by OR NOT EXISTS (
          SELECT 1 FROM literature_evidence e JOIN source_versions v ON v.id=e.source_version_id
          WHERE e.id=NEW.literature_evidence_id AND e.project_id=s.project_id AND v.status IN ('FROZEN','SUPERSEDED')
          AND (NEW.relation_type<>'SUPPORTS' OR (e.review_status='VERIFIED' AND v.version_kind<>'RETRACTED'
          AND NOT EXISTS (SELECT 1 FROM literature_sources ls JOIN source_versions cv ON cv.id=ls.current_version_id
            WHERE ls.id=v.literature_source_id AND (cv.version_kind='RETRACTED' OR (cv.version_kind='CORRECTED' AND cv.id<>v.id)))
          AND EXISTS (SELECT 1 FROM literature_evidence_review_events re JOIN actors a ON a.id=re.reviewed_by
          WHERE re.literature_evidence_id=e.id AND re.new_status='VERIFIED' AND a.actor_type='HUMAN'
          AND re.reviewed_by<>e.created_by AND re.reviewed_by<>s.created_by
          AND re.id=(SELECT id FROM literature_evidence_review_events WHERE literature_evidence_id=e.id ORDER BY reviewed_at DESC,id DESC LIMIT 1))))) THEN
          RAISE EXCEPTION 'M3 support closure/separation' USING ERRCODE='P17D3'; END IF;
        RETURN NEW;
      END IF;
      s:=NEW;
      IF s.claim_version_id IS NOT NULL THEN
        SELECT c.project_id,v.status INTO p,st FROM claim_versions v JOIN claims c ON c.id=v.claim_id WHERE v.id=s.claim_version_id;
      ELSIF s.hypothesis_version_id IS NOT NULL THEN
        SELECT h.project_id,v.status INTO p,st FROM hypothesis_versions v JOIN hypotheses h ON h.id=v.hypothesis_id WHERE v.id=s.hypothesis_version_id;
      ELSE
        SELECT q.project_id,v.status INTO p,st FROM research_question_versions v JOIN research_questions q ON q.id=v.research_question_id WHERE v.id=s.research_question_version_id;
      END IF;
      IF p IS DISTINCT FROM s.project_id OR st NOT IN ('FROZEN','SUPERSEDED') THEN
        RAISE EXCEPTION 'M3 frozen target project' USING ERRCODE='P17D3'; END IF;
      IF s.previous_snapshot_id IS NOT NULL THEN
        SELECT * INTO prev FROM literature_support_snapshots WHERE id=s.previous_snapshot_id;
        IF prev.project_id<>s.project_id OR prev.snapshot_number+1<>s.snapshot_number
           OR prev.claim_version_id IS DISTINCT FROM s.claim_version_id
           OR prev.hypothesis_version_id IS DISTINCT FROM s.hypothesis_version_id
           OR prev.research_question_version_id IS DISTINCT FROM s.research_question_version_id THEN
          RAISE EXCEPTION 'M3 predecessor mismatch' USING ERRCODE='P17D3'; END IF;
      END IF;
      RETURN NEW;
    END $$;""",
    # 0032_pr2_10_discussion.py
    r"""CREATE OR REPLACE FUNCTION pr210_reference_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE sid UUID; pid UUID; state TEXT; valid BOOLEAN;
    BEGIN
      IF TG_TABLE_NAME IN ('discussion_session_question_inputs',
                           'discussion_session_claim_inputs',
                           'discussion_session_source_inputs') THEN
        sid := NEW.session_id;
      ELSIF TG_TABLE_NAME='discussion_turns' THEN
        sid := NEW.session_id;
      ELSE
        SELECT session_id INTO sid FROM discussion_turns WHERE id=NEW.turn_id;
      END IF;
      SELECT project_id,status INTO pid,state FROM discussion_sessions
        WHERE id=sid FOR UPDATE;
      IF pid IS NULL OR state<>'OPEN' THEN
        RAISE EXCEPTION 'discussion session must be open' USING ERRCODE='P17D2';
      END IF;
      IF TG_TABLE_NAME IN ('discussion_session_question_inputs',
                           'discussion_session_claim_inputs',
                           'discussion_session_source_inputs')
         AND NOT EXISTS(SELECT 1 FROM discussion_sessions
                        WHERE id=sid AND xmin=
                          pg_current_xact_id()::xid) THEN
        RAISE EXCEPTION 'discussion input set is sealed' USING ERRCODE='P17D1';
      END IF;
      IF TG_TABLE_NAME IN ('discussion_turn_source_citations',
                           'discussion_turn_claim_citations') THEN
        IF NOT EXISTS(SELECT 1 FROM discussion_turns
                      WHERE id=NEW.turn_id AND xmin=
                        pg_current_xact_id()::xid) THEN
          RAISE EXCEPTION 'discussion turn citations are sealed' USING ERRCODE='P17D1';
        END IF;
      END IF;
      IF TG_TABLE_NAME='discussion_session_question_inputs' THEN
        SELECT EXISTS(SELECT 1 FROM research_question_versions v
          JOIN research_questions q ON q.id=v.research_question_id
          WHERE v.id=NEW.version_id AND q.project_id=pid
            AND v.status IN ('FROZEN','SUPERSEDED')) INTO valid;
        valid := valid AND NEW.ordinal=(SELECT COALESCE(max(ordinal),-1)+1
          FROM discussion_session_question_inputs WHERE session_id=sid);
      ELSIF TG_TABLE_NAME='discussion_session_claim_inputs' THEN
        SELECT EXISTS(SELECT 1 FROM claim_versions v
          JOIN claims c ON c.id=v.claim_id
          WHERE v.id=NEW.version_id AND c.project_id=pid
            AND v.status IN ('FROZEN','SUPERSEDED')) INTO valid;
        valid := valid AND NEW.ordinal=(SELECT COALESCE(max(ordinal),-1)+1
          FROM discussion_session_claim_inputs WHERE session_id=sid);
      ELSIF TG_TABLE_NAME='discussion_session_source_inputs' THEN
        SELECT EXISTS(SELECT 1 FROM source_versions v
          JOIN literature_source_project_links l
            ON l.literature_source_id=v.literature_source_id
          WHERE v.id=NEW.version_id AND l.project_id=pid
            AND v.status IN ('FROZEN','SUPERSEDED')) INTO valid;
        valid := valid AND NEW.ordinal=(SELECT COALESCE(max(ordinal),-1)+1
          FROM discussion_session_source_inputs WHERE session_id=sid);
      ELSIF TG_TABLE_NAME='discussion_turn_source_citations' THEN
        SELECT EXISTS(SELECT 1 FROM discussion_session_source_inputs i
          WHERE i.session_id=sid AND i.version_id=NEW.version_id) INTO valid;
        valid := valid AND NEW.ordinal=(SELECT COALESCE(max(ordinal),-1)+1
          FROM discussion_turn_source_citations WHERE turn_id=NEW.turn_id);
      ELSIF TG_TABLE_NAME='discussion_turn_claim_citations' THEN
        SELECT EXISTS(SELECT 1 FROM discussion_session_claim_inputs i
          WHERE i.session_id=sid AND i.version_id=NEW.version_id) INTO valid;
        valid := valid AND NEW.ordinal=(SELECT COALESCE(max(ordinal),-1)+1
          FROM discussion_turn_claim_citations WHERE turn_id=NEW.turn_id);
      ELSE
        valid := NEW.ordinal=(SELECT COALESCE(max(ordinal),0)+1
                              FROM discussion_turns WHERE session_id=sid);
        valid := valid AND NEW.created_at >=
          (SELECT COALESCE(max(created_at),
                   (SELECT created_at FROM discussion_sessions WHERE id=sid))
             FROM discussion_turns WHERE session_id=sid);
      END IF;
      IF NOT COALESCE(valid,FALSE) THEN
        RAISE EXCEPTION 'discussion reference or order invalid' USING ERRCODE='P17D3';
      END IF;
      RETURN NEW;
    END $$;""",
    # 0042_pr2_15_minimal_decision.py
    r"""CREATE OR REPLACE FUNCTION pr215_basis_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE target_id UUID; target_project UUID; parent_xmin xid;
      decision_project UUID; target_status TEXT; target_hash TEXT;
    BEGIN
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
    END $$;""",
    # 0045_pr2_16_basic_approval.py
    r"""CREATE OR REPLACE FUNCTION pr216_request_guard() RETURNS trigger LANGUAGE plpgsql
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
        AND xmin=pg_current_xact_id()::xid)
        OR EXISTS(SELECT 1 FROM internal_review_records x JOIN decision_basis_reviews b
          ON b.internal_review_record_id=x.id WHERE b.decision_id=NEW.basis_decision_id
          AND x.xmin=pg_current_xact_id()::xid) THEN
        RAISE EXCEPTION 'committed basis required' USING ERRCODE='P16B1';
      END IF;
      NEW.requested_at:=clock_timestamp();
      RETURN NEW;
    END $$;""",
    # 0045_pr2_16_basic_approval.py
    r"""CREATE OR REPLACE FUNCTION pr216_relation_guard() RETURNS trigger LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE r approval_requests; owner_xmin xid;
    BEGIN
      SELECT q.* INTO r FROM approval_requests q WHERE q.id=NEW.request_id;
      SELECT xmin INTO owner_xmin FROM approval_requests WHERE id=NEW.request_id;
      IF owner_xmin IS DISTINCT FROM pg_current_xact_id()::xid OR r.status<>'PENDING'
        OR NOT EXISTS(SELECT 1 FROM decision_basis_reviews WHERE decision_id=r.basis_decision_id
          AND internal_review_record_id=NEW.internal_review_record_id) THEN
        RAISE EXCEPTION 'sealed exact review set' USING ERRCODE='P16B1';
      END IF; RETURN NEW;
    END $$;""",
    # 0045_pr2_16_basic_approval.py
    r"""CREATE OR REPLACE FUNCTION pr216_grant_guard() RETURNS trigger LANGUAGE plpgsql
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
            AND q.xmin=pg_current_xact_id()::xid) THEN
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
          AND xmin=pg_current_xact_id()::xid) THEN
        RAISE EXCEPTION 'exact new grant required' USING ERRCODE='P16G1';
      END IF; RETURN NEW;
    END $$;""",
    # 0046_pr2_17_authorship_preparation.py
    r"""CREATE OR REPLACE FUNCTION pr217_snapshot_sealed() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE parent_xmin xid;
    BEGIN
      SELECT xmin INTO parent_xmin FROM authorship_snapshots
        WHERE id=NEW.authorship_snapshot_id FOR UPDATE;
      IF parent_xmin IS DISTINCT FROM pg_current_xact_id()::xid THEN
        RAISE EXCEPTION 'snapshot relation set is sealed' USING ERRCODE='P17A1';
      END IF;
      RETURN NEW;
    END $$;""",
    # 0047_pr2_18_novelty_prior_art.py
    r"""CREATE OR REPLACE FUNCTION pr218_child_guard() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE parent_xid xid; author UUID; source UUID; pid UUID; plan UUID;
    BEGIN
      IF TG_TABLE_NAME='search_coverage_executions' THEN
        IF NOT pr218_capture_prelocked() THEN RAISE EXCEPTION 'capture locks required' USING ERRCODE='P17D3'; END IF;
        SELECT xmin,created_by,search_plan_version_id INTO parent_xid,author,plan
          FROM search_coverage WHERE id=NEW.search_coverage_id;
        IF NOT EXISTS(SELECT 1 FROM literature_search_executions e
          JOIN literature_search_plan_versions v ON v.id=plan JOIN literature_search_plans p ON p.id=v.plan_id
          WHERE e.id=NEW.search_execution_id AND e.search_plan_version_id=plan AND e.project_id=p.project_id
            AND e.status IN ('SUCCEEDED','FAILED','CANCELLED','UNKNOWN') AND e.finished_at IS NOT NULL) THEN
          RAISE EXCEPTION 'terminal same plan execution required' USING ERRCODE='P17D3'; END IF;
      ELSE
        SELECT p.xmin,p.created_by,p.source_version_id,c.project_id
          INTO parent_xid,author,source,pid FROM prior_art_relations p
          JOIN claim_versions v ON v.id=p.claim_version_id JOIN claims c ON c.id=v.claim_id
          WHERE p.id=NEW.prior_art_relation_id;
        IF NOT EXISTS(SELECT 1 FROM literature_evidence e WHERE e.id=NEW.literature_evidence_id
          AND e.project_id=pid AND e.source_version_id=source AND e.review_status='VERIFIED'
          AND e.content_hash ~ '^[0-9a-f]{64}$' AND EXISTS(
            SELECT 1 FROM literature_evidence_review_events r JOIN actors a ON a.id=r.reviewed_by
            WHERE r.id=(SELECT id FROM literature_evidence_review_events WHERE literature_evidence_id=e.id ORDER BY reviewed_at DESC,id DESC LIMIT 1)
              AND r.new_status='VERIFIED' AND a.actor_type='HUMAN' AND r.reviewed_by<>e.created_by)) THEN
          RAISE EXCEPTION 'independently verified exact evidence required' USING ERRCODE='P17D3'; END IF;
      END IF;
      IF parent_xid IS DISTINCT FROM pg_current_xact_id()::xid THEN
        RAISE EXCEPTION 'sealed child set' USING ERRCODE='P17D1'; END IF;
      IF author IS DISTINCT FROM NEW.created_by THEN RAISE EXCEPTION 'child author mismatch' USING ERRCODE='P17D3'; END IF;
      RETURN NEW;
    END $$;""",
    # Current Batch C definition: b07_revision_basis_guard
    r"""CREATE OR REPLACE FUNCTION public.b07_revision_basis_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE purpose TEXT;
BEGIN
  LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, audit_findings, claims, correction_records, datasets, experiment_spec_versions, experiment_specs, impact_assessments, impact_targets, internal_review_records, literature_evidence, literature_evidence_review_events, literature_source_project_links, literature_sources, metric_definition_versions, metric_definitions, project_membership_events, project_memberships, project_role_assignments, projects, runs, scientific_conclusions, source_versions IN SHARE MODE;
  SELECT decision_type INTO purpose FROM decision_records WHERE id=NEW.decision_id;
  IF purpose IS DISTINCT FROM 'REVISION_RESPONSE' THEN RAISE EXCEPTION 'revision purpose required' USING ERRCODE='P17F2'; END IF;
  IF NOT EXISTS(SELECT 1 FROM decision_records WHERE id=NEW.decision_id AND xmin=pg_current_xact_id()::xid) THEN
    RAISE EXCEPTION 'basis sealed to creation transaction' USING ERRCODE='P17F1'; END IF;
  IF TG_TABLE_NAME='decision_revision_concerns' THEN
    PERFORM b07_lock_concern(NEW.review_issue_id);
  ELSE
    PERFORM id FROM internal_review_records WHERE claim_version_id=NEW.claim_version_id ORDER BY id FOR SHARE;
    PERFORM b07_lock_concern(review_issue_id) FROM decision_revision_concerns WHERE decision_id=NEW.decision_id;
  END IF;
  RETURN NEW;
END $function$""",
    # Current Batch C definition: b07_validate_decision
    r"""CREATE OR REPLACE FUNCTION public.b07_validate_decision(did uuid, complete_snapshot boolean)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE d decision_records; i review_issues; r internal_review_records; ref internal_review_records; tid UUID; digest TEXT; kind TEXT; basis JSONB; n INT;
BEGIN
  SELECT * INTO d FROM decision_records WHERE id=did;
  SELECT x.* INTO i FROM decision_revision_concerns b JOIN review_issues x ON x.id=b.review_issue_id WHERE b.decision_id=did;
  SELECT * INTO r FROM internal_review_records WHERE id=i.review_record_id;
  IF d.id IS NULL OR d.decision_type<>'REVISION_RESPONSE' OR i.id IS NULL OR r.id IS NULL OR d.project_id<>r.project_id
    OR d.decided_at>clock_timestamp() OR d.supersedes_decision_id IS NOT NULL OR NOT pr216_decision_authorized(d) THEN
    RAISE EXCEPTION 'exact revision concern and authority required' USING ERRCODE='P17F2';
  END IF;
  IF complete_snapshot THEN PERFORM b07_lock_concern(i.id); END IF;
  tid:=coalesce(r.claim_version_id,r.scientific_conclusion_version_id);
  kind:=CASE WHEN r.claim_version_id IS NOT NULL THEN 'ClaimVersion' ELSE 'ScientificConclusionVersion' END;
  IF r.claim_version_id IS NOT NULL THEN SELECT content_hash INTO digest FROM claim_versions WHERE id=tid;
  ELSE SELECT content_hash INTO digest FROM scientific_conclusion_versions WHERE id=tid; END IF;
  PERFORM b07_target(tid,d.project_id,CASE WHEN kind='ClaimVersion' THEN 'claim_versions' ELSE 'scientific_conclusion_versions' END);
  IF d.decided_by IN (SELECT b07_authors(tid,CASE WHEN kind='ClaimVersion' THEN 'claim_versions' ELSE 'scientific_conclusion_versions' END)) OR length(d.question)>16000 OR length(d.rationale)>16000
    OR d.question<>normalize(d.question,NFC) OR d.rationale<>normalize(d.rationale,NFC)
    OR (SELECT count(*) FROM decision_basis_claims WHERE decision_id=did)+
       (SELECT count(*) FROM decision_basis_conclusions WHERE decision_id=did)<>1
    OR (kind='ClaimVersion' AND NOT EXISTS(SELECT 1 FROM decision_basis_claims WHERE decision_id=did AND claim_version_id=tid))
    OR (kind='ScientificConclusionVersion' AND NOT EXISTS(SELECT 1 FROM decision_basis_conclusions WHERE decision_id=did AND scientific_conclusion_version_id=tid))
    OR NOT EXISTS(SELECT 1 FROM decision_basis_reviews WHERE decision_id=did AND internal_review_record_id=r.id) THEN
    RAISE EXCEPTION 'exact revision target basis required' USING ERRCODE='P17F2';
  END IF;
  IF complete_snapshot AND EXISTS(SELECT 1 FROM internal_review_records x WHERE x.project_id=d.project_id
    AND x.claim_version_id IS NOT DISTINCT FROM r.claim_version_id
    AND x.scientific_conclusion_version_id IS NOT DISTINCT FROM r.scientific_conclusion_version_id
    AND NOT EXISTS(SELECT 1 FROM decision_basis_reviews b WHERE b.decision_id=did AND b.internal_review_record_id=x.id)) THEN
    RAISE EXCEPTION 'complete matching review snapshot required' USING ERRCODE='P17F2';
  END IF;
  FOR ref IN SELECT x.* FROM decision_basis_reviews b JOIN internal_review_records x ON x.id=b.internal_review_record_id WHERE b.decision_id=did ORDER BY x.id LOOP
    IF (complete_snapshot AND EXISTS(SELECT 1 FROM internal_review_records WHERE id=ref.id AND xmin=pg_current_xact_id()::xid))
      OR ref.created_at>d.decided_at OR ref.project_id<>d.project_id OR ref.claim_version_id IS DISTINCT FROM r.claim_version_id
      OR ref.scientific_conclusion_version_id IS DISTINCT FROM r.scientific_conclusion_version_id
      OR ref.target_content_hash IS DISTINCT FROM digest THEN
      RAISE EXCEPTION 'exact review binding required' USING ERRCODE='P17F2';
    END IF;
    PERFORM b07_review(ref);
  END LOOP;
  SELECT jsonb_agg(jsonb_build_object('target',pr216_ref(k,id,h),'ordinal',ordinal) ORDER BY k,id,h),count(*) INTO basis,n FROM (
    SELECT 'ClaimVersion' AS k,b.claim_version_id AS id,v.content_hash AS h,b.ordinal FROM decision_basis_claims b JOIN claim_versions v ON v.id=b.claim_version_id WHERE b.decision_id=did
    UNION ALL SELECT 'ScientificConclusionVersion',b.scientific_conclusion_version_id,v.content_hash,b.ordinal FROM decision_basis_conclusions b JOIN scientific_conclusion_versions v ON v.id=b.scientific_conclusion_version_id WHERE b.decision_id=did
    UNION ALL SELECT 'InternalReviewRecord',b.internal_review_record_id,v.content_hash,b.ordinal FROM decision_basis_reviews b JOIN internal_review_records v ON v.id=b.internal_review_record_id WHERE b.decision_id=did) refs;
  IF EXISTS(SELECT 1 FROM jsonb_array_elements(basis) WITH ORDINALITY x(value,pos) WHERE (value->>'ordinal')::int<>pos-1)
    OR d.basis_set_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','DecisionRecordBasisSet','material_version',1,'basis',basis))
    OR d.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','DecisionRecord','material_version',1,
      'project_id',d.project_id,'decision_type',d.decision_type,'question',d.question,'decision',d.decision,'rationale',d.rationale,
      'decided_by',jsonb_build_object('type','ActorIdentity','id',d.decided_by),'supersedes_decision_id',NULL,'basis_set_hash',d.basis_set_hash)) THEN
    RAISE EXCEPTION 'decision basis ordinals or hashes invalid' USING ERRCODE='P17F2';
  END IF;
END $function$""",
    # Current Batch C definition: b07_validate_re_review
    r"""CREATE OR REPLACE FUNCTION public.b07_validate_re_review(link revision_action_re_reviews, take_locks boolean)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE attestation internal_review_records; a revision_actions; old internal_review_records; r internal_review_records; iid UUID; tid UUID; old_tid UUID; cs UUID[]; old_cv claim_versions; old_sc scientific_conclusion_versions; good BOOLEAN; witness UUID; old_witness UUID; candidate UUID;
BEGIN
  SELECT * INTO a FROM revision_actions WHERE id=link.revision_action_id;
  IF a.id IS NULL THEN RAISE EXCEPTION 'exact action required' USING ERRCODE='P17F2'; END IF;
  SELECT coalesce(a.review_issue_id,c.review_issue_id) INTO iid FROM (SELECT 1) x LEFT JOIN decision_revision_concerns c ON c.decision_id=a.decision_record_id;
  SELECT r0.* INTO old FROM review_issues i JOIN internal_review_records r0 ON r0.id=i.review_record_id WHERE i.id=iid;
  SELECT * INTO r FROM internal_review_records WHERE id=link.internal_review_record_id;
  IF take_locks THEN
    LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, audit_findings, claims, correction_records, datasets, experiment_spec_versions, experiment_specs, impact_assessments, impact_targets, internal_review_records, literature_evidence, literature_evidence_review_events, literature_source_project_links, literature_sources, metric_definition_versions, metric_definitions, project_membership_events, project_memberships, project_role_assignments, projects, runs, scientific_conclusions, source_versions IN SHARE MODE;
    PERFORM id FROM internal_review_records WHERE id IN (old.id,r.id) ORDER BY id FOR SHARE;
    PERFORM id FROM review_issues WHERE id=iid FOR SHARE;
    PERFORM id FROM revision_actions WHERE id=a.id FOR UPDATE;
  END IF;
  IF EXISTS(SELECT 1 FROM revision_actions WHERE supersedes_revision_action_id=a.id) THEN
    RAISE EXCEPTION 'action superseded' USING ERRCODE='P17R1'; END IF;
  IF r.id IS NULL OR r.project_id IS DISTINCT FROM old.project_id OR r.reviewer_actor_id<>link.recorded_by
    OR r.created_at<a.created_at OR link.recorded_at<r.created_at OR r.reviewer_actor_id=a.created_by
    OR EXISTS(SELECT 1 FROM revision_actions WHERE id=a.id AND xmin=pg_current_xact_id()::xid)
    OR EXISTS(SELECT 1 FROM internal_review_records WHERE id=r.id AND xmin=pg_current_xact_id()::xid) THEN
    RAISE EXCEPTION 'prior committed independently reviewed action required' USING ERRCODE='P17F2';
  END IF;
  PERFORM b07_validate_revision(a);
  PERFORM b07_review(r);
  attestation:=r; attestation.created_at:=link.recorded_at;
  PERFORM b07_review(attestation);
  tid:=coalesce(r.claim_version_id,r.scientific_conclusion_version_id);
  old_tid:=coalesce(old.claim_version_id,old.scientific_conclusion_version_id);
  IF link.recorded_by IN (SELECT b07_authors(tid,CASE WHEN r.claim_version_id IS NOT NULL THEN 'claim_versions' ELSE 'scientific_conclusion_versions' END) UNION SELECT b07_authors(old_tid,CASE WHEN old.claim_version_id IS NOT NULL THEN 'claim_versions' ELSE 'scientific_conclusion_versions' END)) THEN
    RAISE EXCEPTION 'independent re-reviewer required' USING ERRCODE='P17F2'; END IF;
  SELECT coalesce(array_agg(id),ARRAY[]::UUID[]) INTO cs FROM b07_closure(tid,CASE WHEN r.claim_version_id IS NOT NULL THEN 'claim_versions' ELSE 'scientific_conclusion_versions' END) WHERE kind='claim_versions';
  IF a.action_type='NO_CHANGE' THEN good:=tid=old_tid AND r.target_content_hash=old.target_content_hash;
  ELSIF a.action_type='CLAIM_CHANGE' THEN good:=r.claim_version_id=a.result_claim_version_id;
  ELSIF a.action_type='CONCLUSION_CHANGE' THEN good:=r.scientific_conclusion_version_id=a.result_scientific_conclusion_version_id;
  ELSE
    IF old.claim_version_id IS NOT NULL THEN
      SELECT * INTO old_cv FROM claim_versions WHERE id=old.claim_version_id;
      good:=EXISTS(SELECT 1 FROM claim_versions WHERE id=ANY(cs) AND claim_id=old_cv.claim_id AND version_number>=old_cv.version_number);
    ELSE
      SELECT * INTO old_sc FROM scientific_conclusion_versions WHERE id=old.scientific_conclusion_version_id;
      good:=EXISTS(SELECT 1 FROM scientific_conclusion_versions WHERE id=r.scientific_conclusion_version_id
        AND scientific_conclusion_id=old_sc.scientific_conclusion_id AND version_number>=old_sc.version_number);
    END IF;
    IF a.action_type='NEW_EXPERIMENT' THEN
      good:=good AND EXISTS(SELECT 1 FROM b07_closure(tid,CASE WHEN r.claim_version_id IS NOT NULL THEN 'claim_versions' ELSE 'scientific_conclusion_versions' END) x JOIN measurements m ON x.kind='measurements' AND m.id=x.id
        JOIN runs run ON run.id=m.run_id WHERE run.id=a.result_run_id AND run.experiment_spec_version_id=a.result_experiment_spec_version_id);
    ELSIF a.action_type='ANALYSIS_CHANGE' THEN
      good:=good AND EXISTS(SELECT 1 FROM evidence_relations WHERE claim_version_id=ANY(cs) AND statistical_result_id=a.result_statistical_result_id);
    ELSIF a.action_type='SOURCE_CHANGE' THEN
      good:=good AND EXISTS(SELECT 1 FROM literature_evidence e WHERE e.source_version_id=a.result_source_version_id AND e.id IN (
        SELECT literature_evidence_id FROM scientific_conclusion_literature_inputs WHERE conclusion_version_id=r.scientific_conclusion_version_id
        UNION SELECT rel.literature_evidence_id FROM literature_evidence_relations rel JOIN literature_support_snapshots s ON s.id=rel.literature_support_snapshot_id
          WHERE (r.claim_version_id IS NOT NULL AND s.claim_version_id=r.claim_version_id) OR s.id IN (
            SELECT literature_support_snapshot_id FROM scientific_conclusion_claim_inputs WHERE conclusion_version_id=r.scientific_conclusion_version_id)));
      IF r.claim_version_id IS NOT NULL THEN
        FOR candidate IN SELECT s.id FROM literature_support_snapshots s JOIN literature_evidence_relations rel ON rel.literature_support_snapshot_id=s.id
          JOIN literature_evidence e ON e.id=rel.literature_evidence_id WHERE s.claim_version_id=r.claim_version_id AND e.source_version_id=a.result_source_version_id
          ORDER BY s.snapshot_number,rel.ordinal LOOP
          BEGIN
            PERFORM b07_facts(candidate,r.project_id,'literature_support_snapshots');
            PERFORM b07_current_snapshot(candidate,r.project_id);
            IF link.recorded_by NOT IN (SELECT b07_authors(candidate,'literature_support_snapshots')) THEN witness:=candidate; EXIT; END IF;
          EXCEPTION WHEN SQLSTATE 'P17F2' THEN NULL;
          END;
        END LOOP;
        IF witness IS NULL THEN
          RAISE EXCEPTION 'independent exact source witness required' USING ERRCODE='P17F2'; END IF;
      END IF;
    ELSE good:=false; END IF;
  END IF;
  IF a.action_type='SOURCE_CHANGE' AND old.claim_version_id IS NOT NULL THEN
    FOR candidate IN SELECT s.id FROM literature_support_snapshots s JOIN literature_evidence_relations rel ON rel.literature_support_snapshot_id=s.id
      JOIN literature_evidence e ON e.id=rel.literature_evidence_id WHERE s.claim_version_id=old.claim_version_id
        AND e.source_version_id IN (WITH RECURSIVE chain AS (
          SELECT id,predecessor_source_version_id FROM source_versions WHERE id=a.result_source_version_id
          UNION SELECT v.id,v.predecessor_source_version_id FROM source_versions v JOIN chain c ON v.id=c.predecessor_source_version_id)
          SELECT id FROM chain WHERE id<>a.result_source_version_id)
      ORDER BY s.snapshot_number,rel.ordinal LOOP
      BEGIN
        PERFORM b07_facts(candidate,r.project_id,'literature_support_snapshots');
        IF link.recorded_by NOT IN (SELECT b07_authors(candidate,'literature_support_snapshots')) THEN old_witness:=candidate; EXIT; END IF;
      EXCEPTION WHEN SQLSTATE 'P17F2' THEN NULL;
      END;
    END LOOP;
    IF old_witness IS NULL THEN
      RAISE EXCEPTION 'old source witness independence required' USING ERRCODE='P17F2'; END IF;
  END IF;
  IF good IS DISTINCT FROM true THEN RAISE EXCEPTION 'exact result witness required' USING ERRCODE='P17F2'; END IF;
  PERFORM b07_current_target(tid,r.project_id,CASE WHEN r.claim_version_id IS NOT NULL THEN 'claim_versions' ELSE 'scientific_conclusion_versions' END);
  IF witness IS NOT NULL THEN PERFORM b07_current_snapshot(witness,r.project_id); END IF;
  IF EXISTS(SELECT 1 FROM b07_closure(tid,CASE WHEN r.claim_version_id IS NOT NULL THEN 'claim_versions' ELSE 'scientific_conclusion_versions' END) x JOIN source_versions s ON x.kind='source_versions' AND s.id=x.id
    JOIN literature_sources p ON p.id=s.literature_source_id LEFT JOIN source_versions current ON current.id=p.current_version_id
    WHERE s.version_kind='RETRACTED' OR current.version_kind='RETRACTED') THEN
    RAISE EXCEPTION 'retracted source cannot support re-review' USING ERRCODE='P17F2'; END IF;
END $function$""",
    # Current Batch C definition: b07_validate_revision
    r"""CREATE OR REPLACE FUNCTION public.b07_validate_revision(a revision_actions)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE concern review_issues; review internal_review_records; pid UUID;
  cs UUID[]; ms UUID[]; stats UUID[]; sources UUID[];
  cv claim_versions; sc scientific_conclusion_versions; spec experiment_spec_versions;
  execution runs; result statistical_results; source source_versions; previous source_versions;
  chosen_decision decision_records; effective UUID; prior revision_actions; cursor_id UUID; visited UUID[] := ARRAY[a.id];
BEGIN
  effective := a.review_issue_id;
  IF a.action_type='MANUSCRIPT_CHANGE' THEN
    RAISE EXCEPTION 'manuscript path deferred' USING ERRCODE='P17R1';
  END IF;
  IF a.decision_record_id IS NOT NULL THEN
    SELECT * INTO chosen_decision FROM decision_records WHERE id=a.decision_record_id;
    IF chosen_decision.id IS NULL OR chosen_decision.decision_type<>'REVISION_RESPONSE'
      OR EXISTS (SELECT 1 FROM decision_records WHERE id=chosen_decision.id AND xmin=pg_current_xact_id()::xid) THEN
      RAISE EXCEPTION 'committed revision Decision required' USING ERRCODE='P17F2';
    END IF;
    SELECT review_issue_id INTO effective FROM decision_revision_concerns WHERE decision_id=chosen_decision.id;
    IF effective IS NULL OR (a.review_issue_id IS NOT NULL AND a.review_issue_id<>effective)
      OR (a.action_type='NO_CHANGE' AND chosen_decision.decision<>'ACCEPT_NO_CHANGE')
      OR (a.action_type<>'NO_CHANGE' AND chosen_decision.decision<>'REQUIRE_CHANGE') THEN
      RAISE EXCEPTION 'exact revision choice required' USING ERRCODE='P17F2';
    END IF;
    PERFORM b07_validate_decision(chosen_decision.id,false);
  ELSIF a.action_type='NO_CHANGE' OR effective IS NULL THEN
    RAISE EXCEPTION 'exact eligible basis required' USING ERRCODE='P17F2';
  END IF;
  SELECT * INTO concern FROM review_issues WHERE id=effective;
  SELECT * INTO review FROM internal_review_records WHERE id=concern.review_record_id;
  IF review.id IS NULL THEN
    RAISE EXCEPTION 'exact issue basis required' USING ERRCODE='P17F2';
  END IF;
  IF review.claim_version_id IS NOT NULL THEN
    SELECT * INTO cv FROM claim_versions WHERE id=review.claim_version_id;
    SELECT project_id INTO pid FROM claims WHERE id=cv.claim_id;
    cs := ARRAY[cv.id];
    IF cv.status NOT IN ('FROZEN','SUPERSEDED') OR cv.frozen_at IS NULL
      OR cv.content_hash IS DISTINCT FROM review.target_content_hash THEN
      RAISE EXCEPTION 'exact frozen target required' USING ERRCODE='P17F2';
    END IF;
  ELSE
    SELECT * INTO sc FROM scientific_conclusion_versions
      WHERE id=review.scientific_conclusion_version_id;
    SELECT project_id INTO pid FROM scientific_conclusions WHERE id=sc.scientific_conclusion_id;
    SELECT coalesce(array_agg(claim_version_id),ARRAY[]::UUID[]) INTO cs
      FROM scientific_conclusion_claim_inputs WHERE conclusion_version_id=sc.id;
    IF sc.status NOT IN ('FROZEN','SUPERSEDED') OR sc.frozen_at IS NULL
      OR sc.content_hash IS DISTINCT FROM review.target_content_hash THEN
      RAISE EXCEPTION 'exact frozen target required' USING ERRCODE='P17F2';
    END IF;
  END IF;
  IF (chosen_decision.id IS NOT NULL AND chosen_decision.project_id IS DISTINCT FROM review.project_id)
    OR pid IS NULL OR pid IS DISTINCT FROM review.project_id OR EXISTS (
    SELECT 1 FROM claim_versions v JOIN claims c ON c.id=v.claim_id
    WHERE v.id=ANY(cs) AND (c.project_id<>pid OR v.status NOT IN ('FROZEN','SUPERSEDED')
      OR v.frozen_at IS NULL OR v.content_hash IS NULL)) THEN
    RAISE EXCEPTION 'same-project frozen basis required' USING ERRCODE='P17F2';
  END IF;
  SELECT coalesce(array_agg(statistical_result_id) FILTER (WHERE statistical_result_id IS NOT NULL),
    ARRAY[]::UUID[]) INTO stats FROM evidence_relations WHERE claim_version_id=ANY(cs);
  SELECT coalesce(array_agg(id),ARRAY[]::UUID[]) INTO ms FROM (
    SELECT measurement_id AS id FROM evidence_relations
      WHERE claim_version_id=ANY(cs) AND measurement_id IS NOT NULL
    UNION SELECT measurement_id FROM statistical_result_inputs WHERE statistical_result_id=ANY(stats)
  ) measurements_in_basis;
  IF a.action_type='NO_CHANGE' THEN
    NULL;
  ELSIF a.action_type='CLAIM_CHANGE' THEN
    SELECT * INTO cv FROM claim_versions WHERE id=a.result_claim_version_id;
    IF cv.status NOT IN ('FROZEN','SUPERSEDED') OR cv.frozen_at IS NULL
      OR cv.content_hash IS NULL OR NOT EXISTS (
      SELECT 1 FROM claim_versions old JOIN claims c ON c.id=old.claim_id
      WHERE old.id=ANY(cs) AND old.claim_id=cv.claim_id AND c.project_id=pid
        AND cv.version_number>old.version_number) THEN
      RAISE EXCEPTION 'frozen same-claim successor required' USING ERRCODE='P17F2';
    END IF;
  ELSIF a.action_type='CONCLUSION_CHANGE' THEN
    SELECT * INTO sc FROM scientific_conclusion_versions
      WHERE id=a.result_scientific_conclusion_version_id;
    IF sc.status NOT IN ('FROZEN','SUPERSEDED') OR sc.frozen_at IS NULL
      OR sc.content_hash IS NULL OR NOT EXISTS (SELECT 1 FROM scientific_conclusions
        WHERE id=sc.scientific_conclusion_id AND project_id=pid) THEN
      RAISE EXCEPTION 'same-project frozen conclusion required' USING ERRCODE='P17F2';
    END IF;
    IF review.scientific_conclusion_version_id IS NOT NULL THEN
      IF NOT EXISTS (SELECT 1 FROM scientific_conclusion_versions old
        WHERE old.id=review.scientific_conclusion_version_id
          AND old.scientific_conclusion_id=sc.scientific_conclusion_id
          AND sc.version_number>old.version_number) THEN
        RAISE EXCEPTION 'same-conclusion successor required' USING ERRCODE='P17F2';
      END IF;
    ELSIF NOT EXISTS (SELECT 1 FROM scientific_conclusion_claim_inputs i
      JOIN claim_versions v ON v.id=i.claim_version_id
      JOIN claim_versions old ON old.id=review.claim_version_id
      WHERE i.conclusion_version_id=sc.id AND v.claim_id=old.claim_id
        AND (v.id=old.id OR v.version_number>old.version_number)
        AND v.status IN ('FROZEN','SUPERSEDED') AND v.frozen_at IS NOT NULL) THEN
      RAISE EXCEPTION 'exact reviewed claim lineage required' USING ERRCODE='P17F2';
    END IF;
  ELSIF a.action_type='NEW_EXPERIMENT' THEN
    SELECT * INTO spec FROM experiment_spec_versions WHERE id=a.result_experiment_spec_version_id;
    SELECT * INTO execution FROM runs WHERE id=a.result_run_id;
    IF execution.status NOT IN ('SUCCEEDED','FAILED','CANCELLED') THEN
      RAISE EXCEPTION 'terminal Run required' USING ERRCODE='P17R1';
    END IF;
    IF spec.status NOT IN ('FROZEN','SUPERSEDED') OR spec.frozen_at IS NULL
      OR spec.content_hash IS NULL OR execution.inputs_sealed_at IS NULL THEN
      RAISE EXCEPTION 'sealed frozen experiment required' USING ERRCODE='P17F2';
    END IF;
    IF execution.project_id IS DISTINCT FROM pid
      OR execution.experiment_spec_version_id IS DISTINCT FROM spec.id
      OR NOT EXISTS (SELECT 1 FROM experiment_specs WHERE id=spec.experiment_spec_id AND project_id=pid)
      OR EXISTS (SELECT 1 FROM measurements WHERE id=ANY(ms) AND run_id=execution.id)
      OR NOT EXISTS (SELECT 1 FROM measurements m JOIN runs r ON r.id=m.run_id
        JOIN experiment_spec_versions old ON old.id=r.experiment_spec_version_id
        WHERE m.id=ANY(ms) AND old.experiment_spec_id=spec.experiment_spec_id
          AND spec.version_number>=old.version_number) THEN
      RAISE EXCEPTION 'exact experiment lineage required' USING ERRCODE='P17F2';
    END IF;
    IF EXISTS (SELECT 1 FROM run_artifact_inputs i JOIN artifact_versions v ON v.id=i.artifact_version_id
      JOIN artifacts p ON p.id=v.artifact_id WHERE i.run_id=execution.id
        AND (v.status NOT IN ('FROZEN','SUPERSEDED') OR v.frozen_at IS NULL
          OR (p.project_id IS NOT NULL AND p.project_id<>pid))) OR EXISTS (
      SELECT 1 FROM run_dataset_inputs i JOIN dataset_snapshots s ON s.id=i.dataset_snapshot_id
        JOIN datasets d ON d.id=s.dataset_id WHERE i.run_id=execution.id AND d.project_id<>pid) THEN
      RAISE EXCEPTION 'same-project frozen Run inputs required' USING ERRCODE='P17F2';
    END IF;
  ELSIF a.action_type='ANALYSIS_CHANGE' THEN
    SELECT * INTO result FROM statistical_results WHERE id=a.result_statistical_result_id;
    IF result.project_id IS DISTINCT FROM pid OR result.id=ANY(stats)
      OR NOT EXISTS (SELECT 1 FROM statistical_result_inputs WHERE statistical_result_id=result.id
          AND measurement_id=ANY(ms)) OR EXISTS (
      SELECT 1 FROM statistical_result_inputs i JOIN measurements m ON m.id=i.measurement_id
        JOIN runs r ON r.id=m.run_id JOIN metric_definition_versions v ON v.id=m.metric_definition_version_id
        JOIN metric_definitions metric ON metric.id=v.metric_definition_id
        JOIN experiment_spec_versions sv ON sv.id=r.experiment_spec_version_id
        JOIN experiment_specs sp ON sp.id=sv.experiment_spec_id
      WHERE i.statistical_result_id=result.id AND (r.project_id<>pid OR r.status<>'SUCCEEDED'
        OR r.inputs_sealed_at IS NULL OR v.status NOT IN ('FROZEN','SUPERSEDED') OR v.frozen_at IS NULL
        OR (metric.project_id IS NOT NULL AND metric.project_id<>pid)
        OR sp.project_id<>pid OR sv.status NOT IN ('FROZEN','SUPERSEDED')
        OR sv.frozen_at IS NULL OR sv.content_hash IS NULL
        OR EXISTS (SELECT 1 FROM run_artifact_inputs ri JOIN artifact_versions av ON av.id=ri.artifact_version_id
          JOIN artifacts art ON art.id=av.artifact_id WHERE ri.run_id=r.id
            AND (av.status NOT IN ('FROZEN','SUPERSEDED') OR av.frozen_at IS NULL
              OR (art.project_id IS NOT NULL AND art.project_id<>pid)))
        OR EXISTS (SELECT 1 FROM run_dataset_inputs ri JOIN dataset_snapshots ds ON ds.id=ri.dataset_snapshot_id
          JOIN datasets d ON d.id=ds.dataset_id WHERE ri.run_id=r.id
            AND d.project_id IS NOT NULL AND d.project_id<>pid))) THEN
      RAISE EXCEPTION 'exact shared Measurement analysis required' USING ERRCODE='P17F2';
    END IF;
  ELSE
    SELECT coalesce(array_agg(source_version_id),ARRAY[]::UUID[]) INTO sources FROM literature_evidence
      WHERE id IN (
        SELECT literature_evidence_id FROM scientific_conclusion_literature_inputs
          WHERE conclusion_version_id=review.scientific_conclusion_version_id
        UNION SELECT rel.literature_evidence_id FROM literature_evidence_relations rel
          JOIN literature_support_snapshots s ON s.id=rel.literature_support_snapshot_id
          WHERE (review.claim_version_id IS NOT NULL AND s.claim_version_id=review.claim_version_id)
            OR s.id IN (SELECT literature_support_snapshot_id FROM scientific_conclusion_claim_inputs
              WHERE conclusion_version_id=review.scientific_conclusion_version_id));
    SELECT * INTO source FROM source_versions WHERE id=a.result_source_version_id;
    IF source.version_kind NOT IN ('CORRECTED','RETRACTED') OR NOT EXISTS (
      SELECT 1 FROM literature_source_project_links WHERE literature_source_id=source.literature_source_id
        AND project_id=pid) THEN
      RAISE EXCEPTION 'accessible source correction required' USING ERRCODE='P17F2';
    END IF;
    visited := ARRAY[]::UUID[];
    LOOP
      IF source.id IS NULL OR source.id=ANY(visited)
        OR source.status NOT IN ('FROZEN','SUPERSEDED') OR source.frozen_at IS NULL
        OR source.content_hash IS NULL THEN
        RAISE EXCEPTION 'frozen acyclic source lineage required' USING ERRCODE='P17F2';
      END IF;
      visited := array_append(visited,source.id);
      IF source.version_kind IN ('CORRECTED','RETRACTED') AND NOT EXISTS (
        SELECT 1 FROM artifact_versions v JOIN artifacts p ON p.id=v.artifact_id
          WHERE v.id=source.correction_basis_artifact_version_id AND (p.project_id IS NULL OR p.project_id=pid)
            AND v.status IN ('FROZEN','SUPERSEDED') AND v.frozen_at IS NOT NULL) THEN
        RAISE EXCEPTION 'exact correction artifact required' USING ERRCODE='P17F2';
      END IF;
      EXIT WHEN source.id=ANY(sources) AND source.id<>a.result_source_version_id;
      SELECT * INTO previous FROM source_versions WHERE id=source.predecessor_source_version_id;
      IF previous.literature_source_id IS DISTINCT FROM source.literature_source_id
        OR previous.version_number>=source.version_number THEN
        RAISE EXCEPTION 'same-source predecessor required' USING ERRCODE='P17F2';
      END IF;
      source := previous;
    END LOOP;
  END IF;
  PERFORM b07_target(coalesce(review.claim_version_id,review.scientific_conclusion_version_id),pid,CASE WHEN review.claim_version_id IS NOT NULL THEN 'claim_versions' ELSE 'scientific_conclusion_versions' END);
  IF a.action_type='CLAIM_CHANGE' THEN PERFORM b07_target(a.result_claim_version_id,pid,'claim_versions');
  ELSIF a.action_type='CONCLUSION_CHANGE' THEN PERFORM b07_target(a.result_scientific_conclusion_version_id,pid,'scientific_conclusion_versions');
  ELSIF a.action_type='NEW_EXPERIMENT' THEN PERFORM b07_facts(a.result_experiment_spec_version_id,pid,'experiment_spec_versions'); PERFORM b07_facts(a.result_run_id,pid,'runs');
  ELSIF a.action_type='ANALYSIS_CHANGE' THEN PERFORM b07_facts(a.result_statistical_result_id,pid,'statistical_results');
  ELSIF a.action_type='SOURCE_CHANGE' THEN PERFORM b07_facts(a.result_source_version_id,pid,'source_versions');
  END IF;
  cursor_id := a.supersedes_revision_action_id;
  visited := ARRAY[a.id];
  WHILE cursor_id IS NOT NULL LOOP
    IF cursor_id=ANY(visited) THEN
      RAISE EXCEPTION 'revision correction cycle' USING ERRCODE='P17F2';
    END IF;
    visited := array_append(visited,cursor_id);
    SELECT * INTO prior FROM revision_actions WHERE id=cursor_id;
    IF prior.id IS NULL OR prior.review_issue_id IS DISTINCT FROM a.review_issue_id
      OR prior.decision_record_id IS DISTINCT FROM a.decision_record_id THEN
      RAISE EXCEPTION 'same-basis correction required' USING ERRCODE='P17F2';
    END IF;
    cursor_id := prior.supersedes_revision_action_id;
  END LOOP;
END $function$""",
    # Current Batch C definition: b08_check_history
    r"""CREATE OR REPLACE FUNCTION public.b08_check_history(iid uuid)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE i review_issues; r internal_review_records; root review_issue_events; terminal review_issue_events; n INT; link revision_action_re_reviews;
BEGIN
  SELECT * INTO i FROM review_issues WHERE id=iid;
  SELECT * INTO r FROM internal_review_records WHERE id=i.review_record_id;
  SELECT * INTO root FROM review_issue_events WHERE issue_id=iid AND prior_status IS NULL;
  SELECT * INTO terminal FROM review_issue_events WHERE issue_id=iid AND prior_status='OPEN';
  SELECT count(*) INTO n FROM review_issue_events WHERE issue_id=iid;
  IF i.id IS NULL OR r.id IS NULL OR i.created_at<r.created_at OR i.created_at>clock_timestamp()
    OR root.id IS NULL OR root.new_status<>'OPEN'
    OR root.actor_id<>r.reviewer_actor_id OR root.occurred_at<>i.created_at
    OR (i.status='OPEN' AND (n<>1 OR terminal.id IS NOT NULL))
    OR (i.status<>'OPEN' AND (n<>2 OR terminal.id IS NULL OR terminal.new_status<>i.status
      OR terminal.occurred_at<root.occurred_at)) THEN
    RAISE EXCEPTION 'Issue projection/history mismatch' USING ERRCODE='P17F2'; END IF;
  IF terminal.id IS NOT NULL THEN
    PERFORM b08_validate_event(terminal);
    IF EXISTS(SELECT 1 FROM review_issue_events WHERE id=terminal.id AND xmin=pg_current_xact_id()::xid) THEN
      IF EXISTS(SELECT 1 FROM review_issues WHERE review_record_id=terminal.re_review_record_id AND status='OPEN' AND severity IN ('MAJOR','BLOCKING'))
        OR EXISTS(SELECT 1 FROM revision_actions WHERE supersedes_revision_action_id=terminal.revision_action_id) THEN
        RAISE EXCEPTION 'new disposition admission changed before commit' USING ERRCODE='P17R1'; END IF;
      IF terminal.new_status='ADDRESSED' THEN
        SELECT * INTO link FROM revision_action_re_reviews WHERE revision_action_id=terminal.revision_action_id AND internal_review_record_id=terminal.re_review_record_id;
        PERFORM b07_validate_re_review(link,false);
      END IF;
    END IF;
  END IF;
END $function$""",
    # Current Batch C definition: b08_complete_history
    r"""CREATE OR REPLACE FUNCTION public.b08_complete_history()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE affected UUID;
BEGIN
  IF TG_TABLE_NAME='review_issues' THEN PERFORM b08_check_history(NEW.id);
    FOR affected IN SELECT issue_id FROM review_issue_events WHERE re_review_record_id=NEW.review_record_id
      AND prior_status='OPEN' AND xmin=pg_current_xact_id()::xid LOOP
      PERFORM b08_check_history(affected);
    END LOOP;
  ELSE PERFORM b08_check_history(NEW.issue_id); END IF;
  RETURN NULL;
END $function$""",
    # Current Batch C definition: b08_event_guard
    r"""CREATE OR REPLACE FUNCTION public.b08_event_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE i review_issues; old internal_review_records; r internal_review_records; iid UUID;
  a revision_actions; link revision_action_re_reviews;
BEGIN
  IF NEW.prior_status IS NULL THEN
    SELECT * INTO i FROM review_issues WHERE id=NEW.issue_id;
    SELECT * INTO old FROM internal_review_records WHERE id=i.review_record_id;
    IF NOT EXISTS(SELECT 1 FROM review_issues WHERE id=NEW.issue_id AND xmin=pg_current_xact_id()::xid)
      OR NEW.new_status<>'OPEN' OR NEW.actor_id IS DISTINCT FROM old.reviewer_actor_id
      OR NEW.occurred_at IS DISTINCT FROM i.created_at THEN
      RAISE EXCEPTION 'exact new Issue root required' USING ERRCODE='P17F2'; END IF;
    RETURN NEW;
  END IF;
  LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, audit_findings, claims, correction_records, datasets, experiment_spec_versions, experiment_specs, impact_assessments, impact_targets, internal_review_records, literature_evidence, literature_evidence_review_events, literature_source_project_links, literature_sources, metric_definition_versions, metric_definitions, project_membership_events, project_memberships, project_role_assignments, projects, runs, scientific_conclusions, source_versions IN SHARE MODE;
  SELECT * INTO i FROM review_issues WHERE id=NEW.issue_id;
  PERFORM id FROM internal_review_records WHERE id IN (i.review_record_id,NEW.re_review_record_id) ORDER BY id FOR SHARE;
  FOR iid IN SELECT id FROM review_issues WHERE id=NEW.issue_id OR review_record_id=NEW.re_review_record_id ORDER BY id LOOP
    IF iid=NEW.issue_id THEN PERFORM id FROM review_issues WHERE id=iid FOR UPDATE;
    ELSE PERFORM id FROM review_issues WHERE id=iid FOR SHARE; END IF;
  END LOOP;
  SELECT * INTO i FROM review_issues WHERE id=NEW.issue_id;
  IF i.status IS DISTINCT FROM 'OPEN' OR EXISTS(SELECT 1 FROM revision_actions WHERE supersedes_revision_action_id=NEW.revision_action_id) THEN
    RAISE EXCEPTION 'Issue terminal or action superseded' USING ERRCODE='P17R1'; END IF;
  IF EXISTS(SELECT 1 FROM review_issues WHERE review_record_id=NEW.re_review_record_id AND status='OPEN' AND severity IN ('MAJOR','BLOCKING')) THEN
    RAISE EXCEPTION 're-review concerns remain open' USING ERRCODE='P17R1'; END IF;
  IF EXISTS(SELECT 1 FROM revision_actions WHERE id=NEW.revision_action_id AND xmin=pg_current_xact_id()::xid)
    OR EXISTS(SELECT 1 FROM revision_action_re_reviews WHERE revision_action_id=NEW.revision_action_id
      AND internal_review_record_id=NEW.re_review_record_id AND xmin=pg_current_xact_id()::xid) THEN
    RAISE EXCEPTION 'prior committed action and mapping required' USING ERRCODE='P17F2'; END IF;
  IF NEW.new_status='ADDRESSED' THEN
    SELECT * INTO link FROM revision_action_re_reviews WHERE revision_action_id=NEW.revision_action_id AND internal_review_record_id=NEW.re_review_record_id;
    PERFORM b07_validate_re_review(link,false);
  END IF;
  NEW.occurred_at:=clock_timestamp();
  PERFORM b08_check_history(NEW.issue_id);
  PERFORM b08_validate_event(NEW);
  RETURN NEW;
END $function$""",
    # Current Batch C definition: b08_validate_mapping
    r"""CREATE OR REPLACE FUNCTION public.b08_validate_mapping(link revision_action_re_reviews, disposer uuid)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE attestation internal_review_records; a revision_actions; old internal_review_records; r internal_review_records; iid UUID; tid UUID; old_tid UUID; cs UUID[]; old_cv claim_versions; old_sc scientific_conclusion_versions; good BOOLEAN; witness UUID; old_witness UUID; candidate UUID;
BEGIN
  SELECT * INTO a FROM revision_actions WHERE id=link.revision_action_id;
  IF a.id IS NULL THEN RAISE EXCEPTION 'exact action required' USING ERRCODE='P17F2'; END IF;
  SELECT coalesce(a.review_issue_id,c.review_issue_id) INTO iid FROM (SELECT 1) x LEFT JOIN decision_revision_concerns c ON c.decision_id=a.decision_record_id;
  SELECT r0.* INTO old FROM review_issues i JOIN internal_review_records r0 ON r0.id=i.review_record_id WHERE i.id=iid;
  SELECT * INTO r FROM internal_review_records WHERE id=link.internal_review_record_id;
  IF r.id IS NULL OR r.project_id IS DISTINCT FROM old.project_id OR r.reviewer_actor_id<>link.recorded_by
    OR r.created_at<a.created_at OR link.recorded_at<r.created_at OR r.reviewer_actor_id=a.created_by
    OR EXISTS(SELECT 1 FROM revision_actions WHERE id=a.id AND xmin=pg_current_xact_id()::xid)
    OR EXISTS(SELECT 1 FROM internal_review_records WHERE id=r.id AND xmin=pg_current_xact_id()::xid) THEN
    RAISE EXCEPTION 'prior committed independently reviewed action required' USING ERRCODE='P17F2';
  END IF;
  PERFORM b07_validate_revision(a);
  PERFORM b07_review(r);
  attestation:=r; attestation.created_at:=link.recorded_at;
  PERFORM b07_review(attestation);
  tid:=coalesce(r.claim_version_id,r.scientific_conclusion_version_id);
  old_tid:=coalesce(old.claim_version_id,old.scientific_conclusion_version_id);
  IF link.recorded_by IN (SELECT b07_authors(tid,CASE WHEN r.claim_version_id IS NOT NULL THEN 'claim_versions' ELSE 'scientific_conclusion_versions' END) UNION SELECT b07_authors(old_tid,CASE WHEN old.claim_version_id IS NOT NULL THEN 'claim_versions' ELSE 'scientific_conclusion_versions' END)) THEN
    RAISE EXCEPTION 'independent re-reviewer required' USING ERRCODE='P17F2'; END IF;
  IF disposer=a.created_by OR disposer IN (SELECT b07_authors(tid,CASE WHEN r.claim_version_id IS NOT NULL THEN 'claim_versions' ELSE 'scientific_conclusion_versions' END) UNION SELECT b07_authors(old_tid,CASE WHEN old.claim_version_id IS NOT NULL THEN 'claim_versions' ELSE 'scientific_conclusion_versions' END)) THEN
    RAISE EXCEPTION 'independent disposer required' USING ERRCODE='P17F2'; END IF;
  SELECT coalesce(array_agg(id),ARRAY[]::UUID[]) INTO cs FROM b07_closure(tid,CASE WHEN r.claim_version_id IS NOT NULL THEN 'claim_versions' ELSE 'scientific_conclusion_versions' END) WHERE kind='claim_versions';
  IF a.action_type='NO_CHANGE' THEN good:=tid=old_tid AND r.target_content_hash=old.target_content_hash;
  ELSIF a.action_type='CLAIM_CHANGE' THEN good:=r.claim_version_id=a.result_claim_version_id;
  ELSIF a.action_type='CONCLUSION_CHANGE' THEN good:=r.scientific_conclusion_version_id=a.result_scientific_conclusion_version_id;
  ELSE
    IF old.claim_version_id IS NOT NULL THEN
      SELECT * INTO old_cv FROM claim_versions WHERE id=old.claim_version_id;
      good:=EXISTS(SELECT 1 FROM claim_versions WHERE id=ANY(cs) AND claim_id=old_cv.claim_id AND version_number>=old_cv.version_number);
    ELSE
      SELECT * INTO old_sc FROM scientific_conclusion_versions WHERE id=old.scientific_conclusion_version_id;
      good:=EXISTS(SELECT 1 FROM scientific_conclusion_versions WHERE id=r.scientific_conclusion_version_id
        AND scientific_conclusion_id=old_sc.scientific_conclusion_id AND version_number>=old_sc.version_number);
    END IF;
    IF a.action_type='NEW_EXPERIMENT' THEN
      good:=good AND EXISTS(SELECT 1 FROM b07_closure(tid,CASE WHEN r.claim_version_id IS NOT NULL THEN 'claim_versions' ELSE 'scientific_conclusion_versions' END) x JOIN measurements m ON x.kind='measurements' AND m.id=x.id
        JOIN runs run ON run.id=m.run_id WHERE run.id=a.result_run_id AND run.experiment_spec_version_id=a.result_experiment_spec_version_id);
    ELSIF a.action_type='ANALYSIS_CHANGE' THEN
      good:=good AND EXISTS(SELECT 1 FROM evidence_relations WHERE claim_version_id=ANY(cs) AND statistical_result_id=a.result_statistical_result_id);
    ELSIF a.action_type='SOURCE_CHANGE' THEN
      good:=good AND EXISTS(SELECT 1 FROM literature_evidence e WHERE e.source_version_id=a.result_source_version_id AND e.id IN (
        SELECT literature_evidence_id FROM scientific_conclusion_literature_inputs WHERE conclusion_version_id=r.scientific_conclusion_version_id
        UNION SELECT rel.literature_evidence_id FROM literature_evidence_relations rel JOIN literature_support_snapshots s ON s.id=rel.literature_support_snapshot_id
          WHERE (r.claim_version_id IS NOT NULL AND s.claim_version_id=r.claim_version_id) OR s.id IN (
            SELECT literature_support_snapshot_id FROM scientific_conclusion_claim_inputs WHERE conclusion_version_id=r.scientific_conclusion_version_id)));
      IF r.claim_version_id IS NOT NULL THEN
        FOR candidate IN SELECT s.id FROM literature_support_snapshots s JOIN literature_evidence_relations rel ON rel.literature_support_snapshot_id=s.id
          JOIN literature_evidence e ON e.id=rel.literature_evidence_id WHERE s.claim_version_id=r.claim_version_id AND e.source_version_id=a.result_source_version_id
          ORDER BY s.snapshot_number,rel.ordinal LOOP
          BEGIN
            PERFORM b07_facts(candidate,r.project_id,'literature_support_snapshots');
            IF link.recorded_by NOT IN (SELECT b07_authors(candidate,'literature_support_snapshots')) AND disposer NOT IN (SELECT b07_authors(candidate,'literature_support_snapshots')) THEN witness:=candidate; EXIT; END IF;
          EXCEPTION WHEN SQLSTATE 'P17F2' THEN NULL;
          END;
        END LOOP;
        IF witness IS NULL THEN
          RAISE EXCEPTION 'independent exact source witness required' USING ERRCODE='P17F2'; END IF;
      END IF;
    ELSE good:=false; END IF;
  END IF;
  IF a.action_type='SOURCE_CHANGE' AND old.claim_version_id IS NOT NULL THEN
    FOR candidate IN SELECT s.id FROM literature_support_snapshots s JOIN literature_evidence_relations rel ON rel.literature_support_snapshot_id=s.id
      JOIN literature_evidence e ON e.id=rel.literature_evidence_id WHERE s.claim_version_id=old.claim_version_id
        AND e.source_version_id IN (WITH RECURSIVE chain AS (
          SELECT id,predecessor_source_version_id FROM source_versions WHERE id=a.result_source_version_id
          UNION SELECT v.id,v.predecessor_source_version_id FROM source_versions v JOIN chain c ON v.id=c.predecessor_source_version_id)
          SELECT id FROM chain WHERE id<>a.result_source_version_id)
      ORDER BY s.snapshot_number,rel.ordinal LOOP
      BEGIN
        PERFORM b07_facts(candidate,r.project_id,'literature_support_snapshots');
        IF link.recorded_by NOT IN (SELECT b07_authors(candidate,'literature_support_snapshots')) AND disposer NOT IN (SELECT b07_authors(candidate,'literature_support_snapshots')) THEN old_witness:=candidate; EXIT; END IF;
      EXCEPTION WHEN SQLSTATE 'P17F2' THEN NULL;
      END;
    END LOOP;
    IF old_witness IS NULL THEN
      RAISE EXCEPTION 'old source witness independence required' USING ERRCODE='P17F2'; END IF;
  END IF;
  IF good IS DISTINCT FROM true THEN RAISE EXCEPTION 'exact result witness required' USING ERRCODE='P17F2'; END IF;
END $function$""",
    # Current Batch C definition: b10_child_check
    r"""CREATE OR REPLACE FUNCTION public.b10_child_check(did uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE d decision_records; stamp xid;
BEGIN
 PERFORM b09_preheld();
 SELECT * INTO d FROM decision_records WHERE id=did;
 SELECT xmin INTO stamp FROM decision_records WHERE id=did;
 IF stamp IS DISTINCT FROM pg_current_xact_id()::xid THEN
   RAISE EXCEPTION 'immutable sealed parent' USING ERRCODE='P17F1';
 END IF;
 IF d.decision_type<>'RECONSIDER_REJECTION' THEN
   RAISE EXCEPTION 'reconsideration parent required' USING ERRCODE='P10B1';
 END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended('pr216:scope:'||d.project_id||':'||'INTERNAL_SCIENTIFIC_RELEASE',0));
END $function$""",
    # Current Batch C definition: b10_revision_verify
    r"""CREATE OR REPLACE FUNCTION public.b10_revision_verify(identity uuid, pid uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE a revision_actions; prior revision_actions; current_id uuid:=identity;
 visited uuid[]:=ARRAY[]::uuid[]; results jsonb; expected text; review internal_review_records;
BEGIN
 WHILE current_id IS NOT NULL LOOP
  IF current_id=ANY(visited) OR cardinality(visited)>=10000 THEN
   RAISE EXCEPTION 'bounded acyclic revision history required' USING ERRCODE='P10B1'; END IF;
  visited:=array_append(visited,current_id);
  SELECT * INTO a FROM revision_actions WHERE id=current_id;
  IF a.id IS NULL OR EXISTS(SELECT 1 FROM revision_actions WHERE id=a.id AND xmin=pg_current_xact_id()::xid) THEN
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
END $function$""",
    # Current Batch C definition: b10_successor_check
    r"""CREATE OR REPLACE FUNCTION public.b10_successor_check(r approval_requests, approver uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE d decision_records; anchor UUID; latest timestamptz; target UUID;
BEGIN
 SELECT q.id,x.decided_at INTO anchor,latest FROM approval_decisions x JOIN approval_requests q ON q.id=x.approval_request_id
 WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose AND x.decision='REJECT'
 AND (NOT EXISTS(SELECT 1 FROM approval_decisions own WHERE own.id=x.id
   AND own.approval_request_id=r.id AND own.xmin=pg_current_xact_id()::xid))
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
 OR EXISTS(SELECT 1 FROM decision_records WHERE id=d.id AND xmin=pg_current_xact_id()::xid)
 OR EXISTS((SELECT x.id FROM approval_decisions x JOIN approval_requests q ON q.id=x.approval_request_id
    WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose AND x.decision='REJECT'
    AND NOT (x.approval_request_id=r.id AND x.xmin=pg_current_xact_id()::xid))
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
END $function$""",
    # Current Batch C definition: b10_validate
    r"""CREATE OR REPLACE FUNCTION public.b10_validate(did uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
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
 OR v.status<>'FROZEN' OR v.frozen_at IS NULL OR EXISTS(SELECT 1 FROM scientific_conclusion_versions WHERE id=v.id AND xmin=pg_current_xact_id()::xid) THEN
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
     AND xmin=pg_current_xact_id()::xid) THEN
   RAISE EXCEPTION 'prior committed reviews required' USING ERRCODE='P10B1'; END IF;
 END LOOP;
 FOR rejected IN SELECT x.*,q.scientific_conclusion_version_id AS old_id,q.target_content_hash AS old_hash,q.id AS request_id,q.requested_by
 FROM approval_decisions x JOIN approval_requests q ON q.id=x.approval_request_id
 JOIN decision_basis_approval_decisions b ON b.approval_decision_id=x.id WHERE b.decision_id=did LOOP
  IF EXISTS(SELECT 1 FROM approval_decisions WHERE id=rejected.id AND xmin=pg_current_xact_id()::xid) THEN
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
   OR EXISTS(SELECT 1 FROM revision_actions WHERE id=a.id AND xmin=pg_current_xact_id()::xid)
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
END $function$""",
    # Current Batch C definition: b11_check_basis
    r"""CREATE OR REPLACE FUNCTION public.b11_check_basis(did uuid, tid uuid)
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
END $function$""",
    # Current Batch C definition: pr215_basis_guard
    r"""CREATE OR REPLACE FUNCTION public.pr215_basis_guard()
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
    END $function$""",
    # Current Batch C definition: pr216_complete
    r"""CREATE OR REPLACE FUNCTION public.pr216_complete()
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
    END $function$""",
    # Current Batch C definition: pr216_event_insert
    r"""CREATE OR REPLACE FUNCTION public.pr216_event_insert()
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
END $function$""",
    # Current Batch C definition: pr216_grant_guard
    r"""CREATE OR REPLACE FUNCTION public.pr216_grant_guard()
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
    END $function$""",
    # Current Batch C definition: pr216_request_guard
    r"""CREATE OR REPLACE FUNCTION public.pr216_request_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
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
        AND xmin=pg_current_xact_id()::xid)
        OR EXISTS(SELECT 1 FROM internal_review_records x JOIN decision_basis_reviews b
          ON b.internal_review_record_id=x.id WHERE b.decision_id=NEW.basis_decision_id
          AND x.xmin=pg_current_xact_id()::xid) THEN
        RAISE EXCEPTION 'committed basis required' USING ERRCODE='P16B1';
      END IF;
      NEW.requested_at:=clock_timestamp();
      RETURN NEW;
    END $function$""",
    # Current Batch C definition: pr214_issue_guard
    r"""CREATE OR REPLACE FUNCTION public.pr214_issue_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
    DECLARE review_project UUID; target_id UUID; checked_target UUID; manuscript_id UUID; checked_manuscript UUID;
    BEGIN
      IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Issue history immutable' USING ERRCODE='P17F1'; END IF;
      IF TG_OP='UPDATE' THEN
        IF OLD.status<>'OPEN' OR NEW.status NOT IN ('ADDRESSED','DISMISSED')
          OR (to_jsonb(NEW)-'status') IS DISTINCT FROM (to_jsonb(OLD)-'status') THEN
          RAISE EXCEPTION 'only disposition projection may change' USING ERRCODE='P17F1'; END IF;
        IF NOT EXISTS(SELECT 1 FROM review_issue_events WHERE issue_id=OLD.id
          AND prior_status=OLD.status AND new_status=NEW.status
          AND xmin=pg_current_xact_id()::xid) THEN
          RAISE EXCEPTION 'new matching disposition event required' USING ERRCODE='P17F2'; END IF;
        RETURN NEW;
      END IF;
      IF NEW.status <> 'OPEN' THEN
        RAISE EXCEPTION 'new Issue must be OPEN' USING ERRCODE='P17F2'; END IF;
      -- Discover only immutable identity without a row lock; target precedes review.
      SELECT scientific_conclusion_version_id,manuscript_version_id INTO target_id,manuscript_id
        FROM internal_review_records WHERE id=NEW.review_record_id;
      IF target_id IS NOT NULL THEN
        PERFORM 1 FROM scientific_conclusion_versions WHERE id=target_id FOR UPDATE;
        IF NOT FOUND THEN
          RAISE EXCEPTION 'issue reference outside review project' USING ERRCODE='P17E2';
        END IF;
      END IF;
      IF manuscript_id IS NOT NULL THEN
        PERFORM 1 FROM manuscript_versions WHERE id=manuscript_id FOR UPDATE;
        IF NOT FOUND THEN
          RAISE EXCEPTION 'issue reference outside review project' USING ERRCODE='P17E2';
        END IF;
      END IF;
      -- A new READ COMMITTED statement after any target wait rereads exact binding.
      SELECT project_id,scientific_conclusion_version_id,manuscript_version_id
        INTO review_project,checked_target,checked_manuscript FROM internal_review_records
        WHERE id=NEW.review_record_id FOR UPDATE;
      IF checked_target IS DISTINCT FROM target_id OR checked_manuscript IS DISTINCT FROM manuscript_id THEN
        RAISE EXCEPTION 'issue reference outside review project' USING ERRCODE='P17E2';
      END IF;
      IF review_project IS NULL
         OR (NEW.related_claim_version_id IS NOT NULL AND NOT EXISTS (
           SELECT 1 FROM claim_versions v JOIN claims c ON c.id=v.claim_id
           WHERE v.id=NEW.related_claim_version_id AND c.project_id=review_project))
         OR (NEW.related_source_version_id IS NOT NULL AND NOT EXISTS (
           SELECT 1 FROM source_versions v JOIN literature_source_project_links l
             ON l.literature_source_id=v.literature_source_id
           WHERE v.id=NEW.related_source_version_id AND l.project_id=review_project))
         OR (NEW.related_run_id IS NOT NULL AND NOT EXISTS (
           SELECT 1 FROM runs r WHERE r.id=NEW.related_run_id
             AND r.project_id=review_project)) THEN
        RAISE EXCEPTION 'issue reference outside review project' USING ERRCODE='P17E2';
      END IF;
      RETURN NEW;
    END $function$""",
)


def upgrade() -> None:
    for statement in FUNCTIONS:
        op.execute(statement)


def downgrade() -> None:
    """Retain the corrective representation while reverting the revision marker."""
