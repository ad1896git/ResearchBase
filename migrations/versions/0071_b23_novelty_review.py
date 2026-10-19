"""B23 exact novelty reviews and precommitted reassessment correspondence.

The replaced PostgreSQL 18 guard definitions and dependent triggers are pinned
verbatim. Rollback restores them only when no B23 history exists.
"""

# ruff: noqa: E501
import hashlib

from alembic import op
from sqlalchemy import text

revision = "0071_b23_novelty_review"
down_revision = "0070_b20_screening_basis"
branch_labels = None
depends_on = None

LEGACY = {
    "pr214_review_guard": r"""CREATE OR REPLACE FUNCTION public.pr214_review_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
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
    END $function$
""",
    "pr214_issue_guard": r"""CREATE OR REPLACE FUNCTION public.pr214_issue_guard()
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
    END $function$
""",
    "b08_event_guard": r"""CREATE OR REPLACE FUNCTION public.b08_event_guard()
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
END $function$
""",
    "pr215_revision_guard": r"""CREATE OR REPLACE FUNCTION public.pr215_revision_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE concern review_issues; prior revision_actions; effective UUID;
BEGIN
  IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'revision history immutable' USING ERRCODE='P17F1'; END IF;
  LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, audit_findings, claims, correction_records, datasets, experiment_spec_versions, experiment_specs, impact_assessments, impact_targets, internal_review_records, literature_evidence, literature_evidence_review_events, literature_source_project_links, literature_sources, metric_definition_versions, metric_definitions, project_membership_events, project_memberships, project_role_assignments, projects, runs, scientific_conclusions, source_versions IN SHARE MODE;
  effective:=NEW.review_issue_id;
  IF effective IS NULL THEN SELECT review_issue_id INTO effective FROM decision_revision_concerns WHERE decision_id=NEW.decision_record_id; END IF;
  SELECT * INTO concern FROM review_issues WHERE id=effective;
  PERFORM id FROM internal_review_records WHERE id=concern.review_record_id FOR SHARE;
  PERFORM id FROM review_issues WHERE id=concern.id FOR SHARE;
  IF NEW.supersedes_revision_action_id IS NOT NULL THEN
    SELECT * INTO prior FROM revision_actions WHERE id=NEW.supersedes_revision_action_id FOR UPDATE;
    IF EXISTS(SELECT 1 FROM revision_actions WHERE supersedes_revision_action_id=prior.id) THEN
      RAISE EXCEPTION 'predecessor already superseded' USING ERRCODE='P17R1'; END IF;
  END IF;
  PERFORM b07_validate_revision(NEW);
  IF NEW.content_hash IS DISTINCT FROM b07_action_hash(NEW) THEN
    RAISE EXCEPTION 'action hash invalid' USING ERRCODE='P17F2'; END IF;
  RETURN NEW;
END $function$
""",
    "b06_complete_revision": r"""CREATE OR REPLACE FUNCTION public.b06_complete_revision()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE saved revision_actions;
BEGIN
  SELECT * INTO saved FROM revision_actions WHERE id=NEW.id;
  PERFORM b07_validate_revision(saved);
  IF saved.content_hash IS DISTINCT FROM b07_action_hash(saved) THEN
    RAISE EXCEPTION 'action hash invalid' USING ERRCODE='P17F2'; END IF;
  RETURN NULL;
END $function$
""",
    "b07_validate_re_review": r"""CREATE OR REPLACE FUNCTION public.b07_validate_re_review(link revision_action_re_reviews, take_locks boolean)
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
END $function$
""",
    "b07_re_review_guard": r"""CREATE OR REPLACE FUNCTION public.b07_re_review_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, audit_findings, claims, correction_records, datasets, experiment_spec_versions, experiment_specs, impact_assessments, impact_targets, internal_review_records, literature_evidence, literature_evidence_review_events, literature_source_project_links, literature_sources, metric_definition_versions, metric_definitions, project_membership_events, project_memberships, project_role_assignments, projects, runs, scientific_conclusions, source_versions IN SHARE MODE;
  PERFORM b07_validate_re_review(NEW,true);
  RETURN NEW;
END $function$
""",
}

DISPATCH = {
    "pr214_review_guard": r"""CREATE OR REPLACE FUNCTION public.pr214_review_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
    DECLARE target_status TEXT; target_hash TEXT; target_project UUID;
      target_author UUID; target_frozen TIMESTAMPTZ;
    BEGIN
 IF TG_OP='INSERT' AND NEW.material_version=2 THEN RETURN NEW; END IF;

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
    END $function$
""",
    "pr214_issue_guard": r"""CREATE OR REPLACE FUNCTION public.pr214_issue_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
    DECLARE review_project UUID; target_id UUID; checked_target UUID; manuscript_id UUID; checked_manuscript UUID;
    BEGIN
 IF EXISTS(SELECT 1 FROM internal_review_records WHERE id=CASE WHEN TG_OP='DELETE' THEN OLD.review_record_id ELSE NEW.review_record_id END AND material_version=2) THEN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'novelty Issue history immutable' USING ERRCODE='P17D1'; END IF;
 IF NOT b23_prelocked() THEN RAISE EXCEPTION 'B23 prelocks required' USING ERRCODE='P17D3'; END IF;
 IF NOT EXISTS(SELECT 1 FROM internal_review_records WHERE id=NEW.review_record_id AND xmin=pg_current_xact_id()::xid) THEN
  RAISE EXCEPTION 'sealed novelty Issues' USING ERRCODE='P17D1'; END IF;
 IF NEW.status<>'OPEN' OR NEW.description<>normalize(NEW.description,NFC) OR char_length(NEW.description) NOT BETWEEN 1 AND 16000 OR btrim(NEW.description)=''
  OR NEW.created_at IS DISTINCT FROM (SELECT created_at FROM internal_review_records WHERE id=NEW.review_record_id)
  OR NEW.target_locator IS NOT NULL OR NEW.related_claim_version_id IS NOT NULL OR NEW.related_source_version_id IS NOT NULL OR NEW.related_run_id IS NOT NULL THEN
  RAISE EXCEPTION 'invalid initial novelty Issue' USING ERRCODE='P17D3'; END IF;
 RETURN NEW;
END IF;

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
    END $function$
""",
    "b08_event_guard": r"""CREATE OR REPLACE FUNCTION public.b08_event_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE i review_issues; old internal_review_records; r internal_review_records; iid UUID;
  a revision_actions; link revision_action_re_reviews;
BEGIN
 IF EXISTS(SELECT 1 FROM review_issues ix JOIN internal_review_records rx ON rx.id=ix.review_record_id WHERE ix.id=NEW.issue_id AND rx.material_version=2) THEN
 IF NEW.prior_status IS NOT NULL OR NEW.new_status<>'OPEN' THEN RAISE EXCEPTION 'novelty disposition deferred' USING ERRCODE='P17D2'; END IF;
 IF NOT b23_prelocked() THEN RAISE EXCEPTION 'B23 prelocks required' USING ERRCODE='P17D3'; END IF;
 IF NOT EXISTS(SELECT 1 FROM review_issues ix JOIN internal_review_records rx ON rx.id=ix.review_record_id
   WHERE ix.id=NEW.issue_id AND ix.xmin=pg_current_xact_id()::xid AND rx.xmin=pg_current_xact_id()::xid
    AND NEW.actor_id=rx.reviewer_actor_id AND NEW.occurred_at=ix.created_at) THEN
  RAISE EXCEPTION 'sealed exact novelty OPEN event required' USING ERRCODE='P17D1'; END IF;
 RETURN NEW;
END IF;

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
END $function$
""",
    "pr215_revision_guard": r"""CREATE OR REPLACE FUNCTION public.pr215_revision_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE concern review_issues; prior revision_actions; effective UUID;
BEGIN
 IF TG_OP='INSERT' AND NEW.material_version=2 THEN RETURN NEW; END IF;

  IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'revision history immutable' USING ERRCODE='P17F1'; END IF;
  LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, audit_findings, claims, correction_records, datasets, experiment_spec_versions, experiment_specs, impact_assessments, impact_targets, internal_review_records, literature_evidence, literature_evidence_review_events, literature_source_project_links, literature_sources, metric_definition_versions, metric_definitions, project_membership_events, project_memberships, project_role_assignments, projects, runs, scientific_conclusions, source_versions IN SHARE MODE;
  effective:=NEW.review_issue_id;
  IF effective IS NULL THEN SELECT review_issue_id INTO effective FROM decision_revision_concerns WHERE decision_id=NEW.decision_record_id; END IF;
  SELECT * INTO concern FROM review_issues WHERE id=effective;
  PERFORM id FROM internal_review_records WHERE id=concern.review_record_id FOR SHARE;
  PERFORM id FROM review_issues WHERE id=concern.id FOR SHARE;
  IF NEW.supersedes_revision_action_id IS NOT NULL THEN
    SELECT * INTO prior FROM revision_actions WHERE id=NEW.supersedes_revision_action_id FOR UPDATE;
    IF EXISTS(SELECT 1 FROM revision_actions WHERE supersedes_revision_action_id=prior.id) THEN
      RAISE EXCEPTION 'predecessor already superseded' USING ERRCODE='P17R1'; END IF;
  END IF;
  PERFORM b07_validate_revision(NEW);
  IF NEW.content_hash IS DISTINCT FROM b07_action_hash(NEW) THEN
    RAISE EXCEPTION 'action hash invalid' USING ERRCODE='P17F2'; END IF;
  RETURN NEW;
END $function$
""",
    "b06_complete_revision": r"""CREATE OR REPLACE FUNCTION public.b06_complete_revision()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE saved revision_actions;
BEGIN
 IF NEW.material_version=2 THEN RETURN NULL; END IF;

  SELECT * INTO saved FROM revision_actions WHERE id=NEW.id;
  PERFORM b07_validate_revision(saved);
  IF saved.content_hash IS DISTINCT FROM b07_action_hash(saved) THEN
    RAISE EXCEPTION 'action hash invalid' USING ERRCODE='P17F2'; END IF;
  RETURN NULL;
END $function$
""",
    "b07_validate_re_review": r"""CREATE OR REPLACE FUNCTION public.b07_validate_re_review(link revision_action_re_reviews, take_locks boolean)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE attestation internal_review_records; a revision_actions; old internal_review_records; r internal_review_records; iid UUID; tid UUID; old_tid UUID; cs UUID[]; old_cv claim_versions; old_sc scientific_conclusion_versions; good BOOLEAN; witness UUID; old_witness UUID; candidate UUID;
BEGIN
 IF (SELECT material_version FROM revision_actions WHERE id=link.revision_action_id)=2 THEN PERFORM b23_validate_re_review(link,take_locks); RETURN; END IF;

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
END $function$
""",
    "b07_re_review_guard": r"""CREATE OR REPLACE FUNCTION public.b07_re_review_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
 IF (SELECT material_version FROM revision_actions WHERE id=NEW.revision_action_id)=2 THEN PERFORM b23_validate_re_review(NEW,true); RETURN NEW; END IF;

  LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, audit_findings, claims, correction_records, datasets, experiment_spec_versions, experiment_specs, impact_assessments, impact_targets, internal_review_records, literature_evidence, literature_evidence_review_events, literature_source_project_links, literature_sources, metric_definition_versions, metric_definitions, project_membership_events, project_memberships, project_role_assignments, projects, runs, scientific_conclusions, source_versions IN SHARE MODE;
  PERFORM b07_validate_re_review(NEW,true);
  RETURN NEW;
END $function$
""",
}

TRIGGERS = {
    "pr214_review_guard": r"""CREATE TRIGGER pr214_review_guard BEFORE INSERT OR DELETE OR UPDATE ON public.internal_review_records FOR EACH ROW EXECUTE FUNCTION pr214_review_guard()""",
    "pr214_issue_guard": r"""CREATE TRIGGER pr214_issue_guard BEFORE INSERT OR DELETE OR UPDATE ON public.review_issues FOR EACH ROW EXECUTE FUNCTION pr214_issue_guard()""",
    "pr214_open_event": r"""CREATE TRIGGER pr214_open_event AFTER INSERT ON public.review_issues FOR EACH ROW EXECUTE FUNCTION pr214_open_event()""",
    "pr214_issue_events_immutable": r"""CREATE TRIGGER pr214_issue_events_immutable BEFORE DELETE OR UPDATE ON public.review_issue_events FOR EACH ROW EXECUTE FUNCTION m2_immutable()""",
    "revision_action_guard": r"""CREATE TRIGGER revision_action_guard BEFORE INSERT OR DELETE OR UPDATE ON public.revision_actions FOR EACH ROW EXECUTE FUNCTION pr215_revision_guard()""",
    "b05_complete_review": r"""CREATE CONSTRAINT TRIGGER b05_complete_review AFTER INSERT ON public.internal_review_records DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN ((new.manuscript_version_id IS NOT NULL)) EXECUTE FUNCTION b05_check_review_structure()""",
    "b05_complete_issue": r"""CREATE CONSTRAINT TRIGGER b05_complete_issue AFTER INSERT ON public.review_issues DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (b05_is_manuscript_review(new.review_record_id)) EXECUTE FUNCTION b05_check_review_structure()""",
    "b05_complete_issue_event": r"""CREATE CONSTRAINT TRIGGER b05_complete_issue_event AFTER INSERT ON public.review_issue_events DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (b05_is_manuscript_issue(new.issue_id)) EXECUTE FUNCTION b05_check_review_structure()""",
    "b06_revision_complete": r"""CREATE CONSTRAINT TRIGGER b06_revision_complete AFTER INSERT ON public.revision_actions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b06_complete_revision()""",
    "b07_re_review_immutable": r"""CREATE TRIGGER b07_re_review_immutable BEFORE DELETE OR UPDATE ON public.revision_action_re_reviews FOR EACH ROW EXECUTE FUNCTION pr215_immutable()""",
    "b07_re_review_guard": r"""CREATE TRIGGER b07_re_review_guard BEFORE INSERT ON public.revision_action_re_reviews FOR EACH ROW EXECUTE FUNCTION b07_re_review_guard()""",
    "b07_complete_re_review": r"""CREATE CONSTRAINT TRIGGER b07_complete_re_review AFTER INSERT ON public.revision_action_re_reviews DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b07_complete_re_review_fn()""",
    "b08_event_guard": r"""CREATE TRIGGER b08_event_guard BEFORE INSERT ON public.review_issue_events FOR EACH ROW EXECUTE FUNCTION b08_event_guard()""",
    "b08_project_status": r"""CREATE TRIGGER b08_project_status AFTER INSERT ON public.review_issue_events FOR EACH ROW EXECUTE FUNCTION b08_project_status()""",
    "b08_complete_issue": r"""CREATE CONSTRAINT TRIGGER b08_complete_issue AFTER INSERT OR UPDATE ON public.review_issues DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b08_complete_history()""",
    "b08_complete_event": r"""CREATE CONSTRAINT TRIGGER b08_complete_event AFTER INSERT ON public.review_issue_events DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b08_complete_history()""",
    "b10_no_basis_cycle": r"""CREATE CONSTRAINT TRIGGER b10_no_basis_cycle AFTER INSERT ON public.revision_actions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b10_no_basis_cycle()""",
}

DDL = r"""ALTER TABLE internal_review_records
  ADD COLUMN novelty_assessment_id UUID
    CONSTRAINT fk_b23_review_novelty REFERENCES novelty_assessments(id) ON DELETE RESTRICT,
  ADD COLUMN material_version SMALLINT NOT NULL DEFAULT 1;
ALTER TABLE internal_review_records DROP CONSTRAINT ck_pr214_one_target;
ALTER TABLE internal_review_records ADD CONSTRAINT ck_b23_review_target CHECK (
  num_nonnulls(manuscript_version_id,claim_version_id,
    scientific_conclusion_version_id,artifact_version_id,novelty_assessment_id)=1),
  ADD CONSTRAINT ck_b23_review_version CHECK (
    (material_version=1 AND novelty_assessment_id IS NULL) OR
    (material_version=2 AND novelty_assessment_id IS NOT NULL));
CREATE INDEX ix_b23_review_novelty ON internal_review_records(novelty_assessment_id);

ALTER TABLE revision_actions
  ADD COLUMN result_novelty_assessment_id UUID
    CONSTRAINT fk_b23_result_novelty REFERENCES novelty_assessments(id) ON DELETE RESTRICT,
  ADD COLUMN material_version SMALLINT NOT NULL DEFAULT 1;
ALTER TABLE revision_actions DROP CONSTRAINT revision_action_shape;
ALTER TABLE revision_actions ADD CONSTRAINT ck_b23_revision_shape CHECK (
  (material_version=1 AND result_novelty_assessment_id IS NULL
   AND num_nonnulls(result_experiment_spec_version_id,result_run_id,
     result_statistical_result_id,result_claim_version_id,
     result_scientific_conclusion_version_id,result_manuscript_version_id,
     result_source_version_id) = CASE action_type
       WHEN 'NEW_EXPERIMENT' THEN 2 WHEN 'NO_CHANGE' THEN 0 ELSE 1 END
   AND (
     (action_type='NEW_EXPERIMENT' AND result_experiment_spec_version_id IS NOT NULL
       AND result_run_id IS NOT NULL) OR
     (action_type='ANALYSIS_CHANGE' AND result_statistical_result_id IS NOT NULL) OR
     (action_type='CLAIM_CHANGE' AND result_claim_version_id IS NOT NULL) OR
     (action_type='CONCLUSION_CHANGE' AND result_scientific_conclusion_version_id IS NOT NULL) OR
     (action_type='MANUSCRIPT_CHANGE' AND result_manuscript_version_id IS NOT NULL) OR
     (action_type='SOURCE_CHANGE' AND result_source_version_id IS NOT NULL) OR
     action_type='NO_CHANGE')) OR
  (material_version=2 AND action_type='NOVELTY_REASSESSMENT'
   AND result_novelty_assessment_id IS NOT NULL
   AND review_issue_id IS NOT NULL AND decision_record_id IS NULL
   AND num_nonnulls(result_experiment_spec_version_id,result_run_id,
     result_statistical_result_id,result_claim_version_id,
     result_scientific_conclusion_version_id,result_manuscript_version_id,
     result_source_version_id)=0));
CREATE INDEX ix_b23_result_novelty ON revision_actions(result_novelty_assessment_id);
"""

SQL = r"""CREATE FUNCTION b23_dependencies(seeds uuid[]) RETURNS TABLE(kind text,id uuid) LANGUAGE sql STABLE
 SET search_path=pg_catalog,public,pg_temp AS $$
WITH RECURSIVE edges(kind,id,child_kind,child_id) AS (
 SELECT 'novelty_assessments',id,'claim_versions',claim_version_id FROM novelty_assessments
 UNION ALL SELECT 'novelty_assessments',id,'search_coverage',search_coverage_id FROM novelty_assessments
 UNION ALL SELECT 'novelty_assessments',id,'novelty_assessments',supersedes_assessment_id FROM novelty_assessments WHERE supersedes_assessment_id IS NOT NULL
 UNION ALL SELECT 'novelty_assessments',novelty_assessment_id,'prior_art_relations',prior_art_relation_id FROM novelty_assessment_prior_art_inputs
 UNION ALL SELECT 'novelty_assessments',novelty_assessment_id,'search_result_resolutions',search_result_resolution_id FROM novelty_assessment_prior_art_inputs
 UNION ALL SELECT 'novelty_assessments',novelty_assessment_id,'novelty_assessment_probes',id FROM novelty_assessment_probes
 UNION ALL SELECT 'novelty_assessments',novelty_assessment_id,'novelty_assessment_screening_results',id FROM novelty_assessment_screening_results
 UNION ALL SELECT 'novelty_assessments',novelty_assessment_id,'prior_art_relations',prior_art_relation_id FROM novelty_assessment_screening_results WHERE prior_art_relation_id IS NOT NULL
 UNION ALL SELECT 'novelty_assessments',novelty_assessment_id,'search_result_resolutions',search_result_resolution_id FROM novelty_assessment_screening_results WHERE search_result_resolution_id IS NOT NULL
 UNION ALL SELECT 'prior_art_relations',id,'claim_versions',claim_version_id FROM prior_art_relations
 UNION ALL SELECT 'prior_art_relations',id,'source_versions',source_version_id FROM prior_art_relations
 UNION ALL SELECT 'prior_art_relations',id,'prior_art_relations',supersedes_prior_art_relation_id FROM prior_art_relations WHERE supersedes_prior_art_relation_id IS NOT NULL
 UNION ALL SELECT 'prior_art_relations',prior_art_relation_id,'literature_evidence',literature_evidence_id FROM prior_art_evidence_inputs
 UNION ALL SELECT 'literature_evidence',literature_evidence_id,'literature_evidence_review_events',id FROM literature_evidence_review_events
 UNION ALL SELECT 'search_coverage',id,'literature_search_plan_versions',search_plan_version_id FROM search_coverage
 UNION ALL SELECT 'search_coverage',search_coverage_id,'literature_search_executions',search_execution_id FROM search_coverage_executions
 UNION ALL SELECT 'search_coverage',search_coverage_id,'search_result_resolutions',search_result_resolution_id FROM search_coverage_resolutions
 UNION ALL SELECT 'literature_search_executions',id,'literature_search_plan_versions',search_plan_version_id FROM literature_search_executions
 UNION ALL SELECT 'literature_search_executions',literature_search_execution_id,'search_query_records',id FROM search_query_records
 UNION ALL SELECT 'literature_search_executions',execution_id,'literature_search_provider_attempts',id FROM literature_search_provider_attempts
 UNION ALL SELECT 'literature_search_executions',execution_id,'literature_search_execution_events',id FROM literature_search_execution_events
 UNION ALL SELECT 'search_query_records',search_query_record_id,'search_result_records',id FROM search_result_records
 UNION ALL SELECT 'search_result_records',search_result_record_id,'search_result_resolutions',id FROM search_result_resolutions
 UNION ALL SELECT 'search_result_resolutions',id,'source_versions',source_version_id FROM search_result_resolutions WHERE source_version_id IS NOT NULL
 UNION ALL SELECT 'search_result_resolutions',id,'literature_sources',source_id FROM search_result_resolutions
 UNION ALL SELECT 'literature_sources',id,'source_versions',current_version_id FROM literature_sources WHERE current_version_id IS NOT NULL
 UNION ALL SELECT 'literature_search_plan_versions',id,'literature_search_plans',plan_id FROM literature_search_plan_versions
 UNION ALL SELECT 'literature_search_plan_versions',plan_version_id,'research_question_versions',research_question_version_id FROM search_plan_question_inputs
 UNION ALL SELECT 'research_question_versions',id,'research_questions',research_question_id FROM research_question_versions
), walk(kind,id) AS (
 SELECT 'novelty_assessments',unnest(seeds)
 UNION SELECT e.child_kind,e.child_id FROM walk w JOIN edges e ON e.kind=w.kind AND e.id=w.id
), expanded AS (SELECT * FROM walk UNION
 SELECT b.kind,b.id FROM walk w CROSS JOIN LATERAL b07_closure(w.id,w.kind) b
 WHERE w.kind IN ('claim_versions','source_versions','literature_evidence','artifact_versions'))
SELECT DISTINCT kind,id FROM expanded $$;
CREATE FUNCTION b23_authorized(actor_id uuid, pid uuid, at_time timestamptz, roles text[], human boolean) RETURNS boolean LANGUAGE sql
 SET search_path=pg_catalog,public,pg_temp AS $$
SELECT EXISTS(SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id
 JOIN project_role_assignments role ON role.membership_id=m.id AND role.actor_id=m.actor_id AND role.project_id=m.project_id
 WHERE a.id=$1 AND (NOT human OR a.actor_type='HUMAN') AND a.created_at<=at_time
 AND (a.retired_at IS NULL OR at_time<a.retired_at) AND m.project_id=pid AND m.started_at<=at_time
 AND role.role=ANY(roles) AND role.effective_from<=at_time AND (role.effective_until IS NULL OR at_time<role.effective_until)
 AND (SELECT e.new_status FROM project_membership_events e WHERE e.membership_id=m.id AND e.occurred_at<=at_time ORDER BY e.occurred_at DESC,e.id DESC LIMIT 1)='ACTIVE'
 AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=a.id AND b.bound_at<=at_time AND (b.revoked_at IS NULL OR at_time<b.revoked_at))) $$;
CREATE FUNCTION b23_prelocked() RETURNS boolean LANGUAGE sql
 SET search_path=pg_catalog,public,pg_temp AS $$ SELECT pr218_capture_prelocked() $$;
CREATE FUNCTION b23_resolution_hash(r search_result_resolutions) RETURNS text LANGUAGE sql
 SET search_path=pg_catalog,public,pg_temp AS $$
SELECT pr216_hash(jsonb_build_object('id',r.id,'search_result_record_id',r.search_result_record_id,
 'source_id',r.source_id,'source_version_id',r.source_version_id,'resolved_by',r.resolved_by,
 'resolved_at',to_char(r.resolved_at AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS')||
 CASE WHEN extract(microseconds FROM r.resolved_at)::bigint%1000000=0 THEN '' ELSE to_char(r.resolved_at AT TIME ZONE 'UTC','.US') END||'+00:00',
 'basis',r.basis,'hash_scheme',r.hash_scheme)) $$;
CREATE FUNCTION b23_verify_capture(cid uuid) RETURNS void LANGUAGE plpgsql
 SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE c search_coverage; p literature_search_plan_versions; pid uuid; q record; x record; r search_result_resolutions; j jsonb; score text;
BEGIN
 SELECT * INTO c FROM search_coverage WHERE id=cid;
 SELECT * INTO p FROM literature_search_plan_versions WHERE id=c.search_plan_version_id;
 SELECT project_id INTO pid FROM literature_search_plans WHERE id=p.plan_id;
 IF p.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','LiteratureSearchPlanVersion','material_version',1,
  'plan_id',p.plan_id,'research_question_refs',(SELECT coalesce(jsonb_agg(pr216_ref('ResearchQuestionVersion',v.id,v.content_hash) ORDER BY v.id),'[]') FROM search_plan_question_inputs i JOIN research_question_versions v ON v.id=i.research_question_version_id WHERE i.plan_version_id=p.id),
  'objective',p.objective,'source_scope',p.source_scope,'inclusion_criteria',p.inclusion_criteria,'exclusion_criteria',p.exclusion_criteria,
  'time_range',p.time_range,'language_scope',p.language_scope,'search_strategy',p.search_strategy,'planned_providers',p.planned_providers,'stopping_rule',p.stopping_rule))
 OR EXISTS(SELECT 1 FROM search_plan_question_inputs i JOIN research_question_versions v ON v.id=i.research_question_version_id JOIN research_questions owner ON owner.id=v.research_question_id
  WHERE i.plan_version_id=p.id AND (owner.project_id<>pid OR v.frozen_at IS NULL OR v.status NOT IN ('FROZEN','SUPERSEDED')
    OR v.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('question_text',v.question_text,'scope',v.scope,'rationale',v.rationale)))) THEN
 RAISE EXCEPTION 'saved plan hash closure mismatch' USING ERRCODE='P17D3'; END IF;
 IF (SELECT count(*) FROM search_coverage_executions WHERE search_coverage_id=cid) NOT BETWEEN 1 AND 100
 OR EXISTS(SELECT 1 FROM search_coverage_executions b JOIN literature_search_executions e ON e.id=b.search_execution_id
  WHERE b.search_coverage_id=cid AND (e.project_id<>pid OR e.search_plan_version_id<>p.id OR e.status NOT IN ('SUCCEEDED','FAILED','CANCELLED','UNKNOWN')
   OR e.finished_at IS NULL OR NOT EXISTS(SELECT 1 FROM literature_search_execution_events event WHERE event.execution_id=e.id AND event.kind='FINISHED' AND event.new_status=e.status)
   OR EXISTS(SELECT 1 FROM literature_search_provider_attempts attempt WHERE attempt.execution_id=e.id AND attempt.status='RESERVED'))) THEN
 RAISE EXCEPTION 'terminal capture closure required' USING ERRCODE='P17D3'; END IF;
 FOR q IN SELECT query.* FROM search_query_records query JOIN search_coverage_executions e ON e.search_execution_id=query.literature_search_execution_id WHERE e.search_coverage_id=cid LOOP
  IF q.query_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','SearchQueryRecord','material_version',1,
   'literature_search_execution_id',q.literature_search_execution_id,'provider_id',q.provider_id,'provider_version',q.provider_version,
   'query_text',q.query_text,'ordinal',q.ordinal)) OR q.hash_scheme<>'sha256-cjson-v1' THEN
   RAISE EXCEPTION 'saved query hash mismatch' USING ERRCODE='P17D3'; END IF;
  FOR x IN SELECT * FROM search_result_records WHERE search_query_record_id=q.id LOOP
   score:=x.provider_score::text;
   IF position('.' IN score)>0 THEN score:=rtrim(rtrim(score,'0'),'.'); END IF;
   IF x.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','SearchResultRecord','material_version',1,
     'query_hash',q.query_hash,'rank',x.rank,'external_identifier',x.external_identifier,'title',x.title,'url',x.url,
     'snippet',x.snippet,'provider_score',score)) OR x.hash_scheme<>'sha256-cjson-v1' THEN
    RAISE EXCEPTION 'saved result hash mismatch' USING ERRCODE='P17D3'; END IF;
   FOR r IN SELECT * FROM search_result_resolutions WHERE search_result_record_id=x.id LOOP
    IF r.content_hash IS DISTINCT FROM b23_resolution_hash(r) OR r.hash_scheme<>'sha256-cjson-v1'
     OR NOT EXISTS(SELECT 1 FROM literature_source_project_links WHERE literature_source_id=r.source_id AND project_id=pid)
     OR (r.source_version_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM source_versions WHERE id=r.source_version_id AND literature_source_id=r.source_id)) THEN
     RAISE EXCEPTION 'saved resolution closure mismatch' USING ERRCODE='P17D3'; END IF;
    IF r.source_version_id IS NOT NULL THEN PERFORM b07_facts(r.source_version_id,pid,'source_versions'); END IF;
   END LOOP;
  END LOOP;
 END LOOP;
 IF c.query_count<>(SELECT count(*) FROM search_query_records q0 JOIN search_coverage_executions e ON e.search_execution_id=q0.literature_search_execution_id WHERE e.search_coverage_id=cid)
  OR c.result_count<>(SELECT count(*) FROM search_result_records x0 JOIN search_query_records q0 ON q0.id=x0.search_query_record_id JOIN search_coverage_executions e ON e.search_execution_id=q0.literature_search_execution_id WHERE e.search_coverage_id=cid)
  OR c.providers IS DISTINCT FROM (SELECT coalesce(jsonb_agg(provider ORDER BY provider COLLATE "C"),'[]') FROM (SELECT DISTINCT normalize(q0.provider_id,NFC) AS provider FROM search_query_records q0 JOIN search_coverage_executions e ON e.search_execution_id=q0.literature_search_execution_id WHERE e.search_coverage_id=cid) providers)
  OR c.time_scope IS DISTINCT FROM p.time_range THEN RAISE EXCEPTION 'capture accounting mismatch' USING ERRCODE='P17D3'; END IF;
 IF c.material_version=2 AND EXISTS(SELECT 1 FROM search_coverage_resolutions b JOIN search_result_resolutions resolution ON resolution.id=b.search_result_resolution_id WHERE b.search_coverage_id=cid AND b.resolution_content_hash IS DISTINCT FROM resolution.content_hash) THEN
 RAISE EXCEPTION 'saved resolution membership hash mismatch' USING ERRCODE='P17D3'; END IF;
END $$;
CREATE FUNCTION b23_coverage_hash(cid uuid) RETURNS text LANGUAGE plpgsql
 SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE c search_coverage; p literature_search_plan_versions; j jsonb; captured jsonb;
BEGIN
 PERFORM b23_verify_capture(cid);
 SELECT * INTO c FROM search_coverage WHERE id=cid;
 SELECT * INTO p FROM literature_search_plan_versions WHERE id=c.search_plan_version_id;
 IF c.id IS NULL OR c.material_version NOT IN (1,2) OR p.status NOT IN ('FROZEN','SUPERSEDED') OR p.frozen_at IS NULL THEN
  RAISE EXCEPTION 'invalid coverage closure' USING ERRCODE='P17D3'; END IF;
 j:=jsonb_build_object('type','SearchCoverage','material_version',c.material_version,
  'search_plan_version',pr216_ref('LiteratureSearchPlanVersion',p.id,p.content_hash),
  'search_execution',(SELECT coalesce(jsonb_agg(jsonb_build_object('type','LiteratureSearchExecution','id',search_execution_id) ORDER BY search_execution_id),'[]') FROM search_coverage_executions WHERE search_coverage_id=cid),
  'providers',c.providers,'query_count',c.query_count,'result_count',c.result_count,
  'resolved_source_count',c.resolved_source_count,'time_scope',c.time_scope,'coverage_limitations',c.coverage_limitations);
 IF c.material_version=2 THEN
  SELECT coalesce(jsonb_agg(jsonb_build_object('search_result_record',jsonb_build_object('type','SearchResultRecord','id',x.id),
    'resolutions',(SELECT coalesce(jsonb_agg(pr216_ref('SearchResultResolution',r.id,r.content_hash) ORDER BY r.id),'[]')
      FROM search_coverage_resolutions b JOIN search_result_resolutions r ON r.id=b.search_result_resolution_id
      WHERE b.search_coverage_id=cid AND r.search_result_record_id=x.id)) ORDER BY x.id),'[]') INTO captured
    FROM search_result_records x JOIN search_query_records q ON q.id=x.search_query_record_id
    JOIN search_coverage_executions ce ON ce.search_execution_id=q.literature_search_execution_id WHERE ce.search_coverage_id=cid;
  j:=j||jsonb_build_object('captured_unresolved_result_count',c.captured_unresolved_result_count,'captured_results',captured);
 END IF;
 IF c.hash_scheme<>'sha256-cjson-v1' OR c.content_hash IS DISTINCT FROM pr216_hash(j) THEN
  RAISE EXCEPTION 'coverage hash mismatch' USING ERRCODE='P17D3'; END IF;
 RETURN c.content_hash;
END $$;
CREATE FUNCTION b23_prior_hash(identity uuid, pid uuid, seen uuid[] DEFAULT '{}') RETURNS text LANGUAGE plpgsql
 SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE comparison prior_art_relations; cv claim_versions; sv source_versions; j jsonb; prior text;
BEGIN
 IF identity=ANY(seen) THEN RAISE EXCEPTION 'prior-art cycle' USING ERRCODE='P17D3'; END IF;
 SELECT * INTO comparison FROM prior_art_relations WHERE id=identity;
 SELECT * INTO cv FROM claim_versions WHERE id=comparison.claim_version_id;
 SELECT * INTO sv FROM source_versions WHERE id=comparison.source_version_id;
 IF comparison.id IS NULL OR comparison.material_version NOT IN (1,2)
  OR (comparison.material_version=1) IS DISTINCT FROM (comparison.supersedes_prior_art_relation_id IS NULL)
  OR NOT EXISTS(SELECT 1 FROM literature_source_project_links WHERE literature_source_id=sv.literature_source_id AND project_id=pid)
  OR NOT EXISTS(SELECT 1 FROM claims WHERE id=cv.claim_id AND project_id=pid)
  OR EXISTS(SELECT 1 FROM prior_art_evidence_inputs b JOIN literature_evidence e ON e.id=b.literature_evidence_id
    WHERE b.prior_art_relation_id=identity AND (e.project_id<>pid OR e.source_version_id<>sv.id)) THEN
  RAISE EXCEPTION 'prior-art closure mismatch' USING ERRCODE='P17D3'; END IF;
 PERFORM b07_target(cv.id,pid,'claim_versions');
 PERFORM b07_facts(sv.id,pid,'source_versions');
 PERFORM b07_facts(e.literature_evidence_id,pid,'literature_evidence') FROM prior_art_evidence_inputs e WHERE e.prior_art_relation_id=identity;
 j:=jsonb_build_object('type','PriorArtRelation','material_version',comparison.material_version,
  'claim_version',pr216_ref('ClaimVersion',cv.id,cv.content_hash),'source_version',pr216_ref('SourceVersion',sv.id,sv.content_hash),
  'relation',comparison.relation,'rationale',comparison.rationale,
  'literature_evidence',(SELECT coalesce(jsonb_agg(pr216_ref('LiteratureEvidence',e.id,e.content_hash) ORDER BY e.id),'[]') FROM prior_art_evidence_inputs b JOIN literature_evidence e ON e.id=b.literature_evidence_id WHERE b.prior_art_relation_id=identity),
  'assessed_by',jsonb_build_object('type','ActorIdentity','id',comparison.assessed_by));
 IF comparison.material_version=2 THEN
  IF NOT EXISTS(SELECT 1 FROM prior_art_relations p WHERE p.id=comparison.supersedes_prior_art_relation_id AND p.claim_version_id=cv.id AND p.source_version_id=sv.id) THEN
   RAISE EXCEPTION 'same-pair predecessor required' USING ERRCODE='P17D3'; END IF;
  prior:=b23_prior_hash(comparison.supersedes_prior_art_relation_id,pid,array_append(seen,identity));
  j:=j||jsonb_build_object('supersedes_prior_art_relation',pr216_ref('PriorArtRelation',comparison.supersedes_prior_art_relation_id,prior));
 END IF;
 IF comparison.hash_scheme<>'sha256-cjson-v1' OR comparison.content_hash IS DISTINCT FROM pr216_hash(j) THEN
  RAISE EXCEPTION 'prior-art hash mismatch' USING ERRCODE='P17D3'; END IF;
 RETURN comparison.content_hash;
END $$;
CREATE FUNCTION b23_assessment_hash(aid uuid, pid uuid, seen uuid[] DEFAULT '{}') RETURNS text LANGUAGE plpgsql
 SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE a novelty_assessments; cv claim_versions; j jsonb; b record; material jsonb; prior text;
BEGIN
 IF aid=ANY(seen) THEN RAISE EXCEPTION 'assessment cycle' USING ERRCODE='P17D3'; END IF;
 SELECT * INTO a FROM novelty_assessments WHERE id=aid;
 SELECT * INTO cv FROM claim_versions WHERE id=a.claim_version_id;
 IF a.id IS NULL OR a.material_version NOT IN (1,2) OR cv.frozen_at IS NULL
  OR cv.status NOT IN ('FROZEN','SUPERSEDED') OR NOT EXISTS(SELECT 1 FROM claims WHERE id=cv.claim_id AND project_id=pid)
  OR NOT EXISTS(SELECT 1 FROM search_coverage s JOIN literature_search_plan_versions v ON v.id=s.search_plan_version_id
    JOIN literature_search_plans p ON p.id=v.plan_id WHERE s.id=a.search_coverage_id AND p.project_id=pid) THEN
  RAISE EXCEPTION 'assessment closure mismatch' USING ERRCODE='P17D3'; END IF;
 PERFORM b07_target(cv.id,pid,'claim_versions');
 IF a.supersedes_assessment_id IS NOT NULL THEN
  IF NOT EXISTS(SELECT 1 FROM novelty_assessments WHERE id=a.supersedes_assessment_id AND claim_version_id=cv.id) THEN
   RAISE EXCEPTION 'assessment predecessor mismatch' USING ERRCODE='P17D3'; END IF;
  prior:=b23_assessment_hash(a.supersedes_assessment_id,pid,array_append(seen,aid));
 END IF;
 j:=jsonb_build_object('type','NoveltyAssessment','material_version',a.material_version,
  'claim_version',pr216_ref('ClaimVersion',cv.id,cv.content_hash),
  'search_coverage',pr216_ref('SearchCoverage',a.search_coverage_id,b23_coverage_hash(a.search_coverage_id)),
  'assessment',a.assessment,'limitations',a.limitations,
  'supersedes_assessment',pr216_ref('NoveltyAssessment',a.supersedes_assessment_id,prior),
  'assessed_by',jsonb_build_object('type','ActorIdentity','id',a.assessed_by));
 IF a.material_version=2 THEN
  IF EXISTS(SELECT 1 FROM novelty_assessment_prior_art_inputs bi JOIN prior_art_relations pr ON pr.id=bi.prior_art_relation_id JOIN search_result_resolutions resolution ON resolution.id=bi.search_result_resolution_id JOIN search_result_records hit ON hit.id=resolution.search_result_record_id JOIN search_query_records query ON query.id=hit.search_query_record_id WHERE bi.novelty_assessment_id=aid AND (resolution.source_version_id IS DISTINCT FROM pr.source_version_id OR NOT EXISTS(SELECT 1 FROM search_coverage_executions WHERE search_coverage_id=a.search_coverage_id AND search_execution_id=query.literature_search_execution_id))) THEN RAISE EXCEPTION 'selected basis witness mismatch' USING ERRCODE='P17D3'; END IF;
  FOR b IN SELECT r.* FROM novelty_assessment_prior_art_inputs i JOIN prior_art_relations r ON r.id=i.prior_art_relation_id WHERE i.novelty_assessment_id=aid LOOP
   IF b.claim_version_id<>cv.id OR NOT EXISTS(SELECT 1 FROM literature_source_project_links l JOIN source_versions v ON v.literature_source_id=l.literature_source_id WHERE v.id=b.source_version_id AND l.project_id=pid) THEN
    RAISE EXCEPTION 'comparison closure mismatch' USING ERRCODE='P17D3'; END IF;
   PERFORM b23_prior_hash(b.id,pid);
   PERFORM b07_facts(b.source_version_id,pid,'source_versions');
   PERFORM b07_facts(e.literature_evidence_id,pid,'literature_evidence') FROM prior_art_evidence_inputs e WHERE e.prior_art_relation_id=b.id;
   material:=jsonb_build_object('type','PriorArtRelation','material_version',b.material_version,
    'claim_version',pr216_ref('ClaimVersion',cv.id,cv.content_hash),
    'source_version',pr216_ref('SourceVersion',b.source_version_id,(SELECT content_hash FROM source_versions WHERE id=b.source_version_id)),
    'relation',b.relation,'rationale',b.rationale,'literature_evidence',
    (SELECT coalesce(jsonb_agg(pr216_ref('LiteratureEvidence',e.id,e.content_hash) ORDER BY e.id),'[]') FROM prior_art_evidence_inputs i JOIN literature_evidence e ON e.id=i.literature_evidence_id WHERE i.prior_art_relation_id=b.id),
    'assessed_by',jsonb_build_object('type','ActorIdentity','id',b.assessed_by));
   IF b.material_version=2 THEN material:=material||jsonb_build_object('supersedes_prior_art_relation',pr216_ref('PriorArtRelation',b.supersedes_prior_art_relation_id,(SELECT content_hash FROM prior_art_relations WHERE id=b.supersedes_prior_art_relation_id))); END IF;
   IF b.content_hash IS DISTINCT FROM pr216_hash(material) THEN RAISE EXCEPTION 'comparison hash mismatch' USING ERRCODE='P17D3'; END IF;
  END LOOP;
  j:=j||jsonb_build_object('scope_statement',a.scope_statement,'closeness_criteria',jsonb_build_object('statements',a.closeness_criteria),
   'prior_art_basis',(SELECT coalesce(jsonb_agg(jsonb_build_object('prior_art_relation',pr216_ref('PriorArtRelation',r.id,r.content_hash),
     'search_result_resolution',pr216_ref('SearchResultResolution',s.id,s.content_hash)) ORDER BY r.id),'[]')
     FROM novelty_assessment_prior_art_inputs i JOIN prior_art_relations r ON r.id=i.prior_art_relation_id JOIN search_result_resolutions s ON s.id=i.search_result_resolution_id WHERE i.novelty_assessment_id=aid));
 END IF;
 -- B20's screening shape is outcome-specific v2; positive-v2 bytes stay unchanged.
 IF a.screening_captured THEN
  FOR b IN SELECT * FROM novelty_assessment_screening_results WHERE novelty_assessment_id=aid LOOP
   IF b.prior_art_relation_id IS NOT NULL THEN
    PERFORM b23_prior_hash(b.prior_art_relation_id,pid);
    IF NOT EXISTS(SELECT 1 FROM prior_art_relations r JOIN search_result_resolutions w ON w.id=b.search_result_resolution_id
       WHERE r.id=b.prior_art_relation_id AND r.claim_version_id=cv.id AND r.source_version_id=w.source_version_id
         AND w.search_result_record_id=b.search_result_record_id)
      OR NOT EXISTS(SELECT 1 FROM search_coverage_resolutions WHERE search_coverage_id=a.search_coverage_id
         AND search_result_resolution_id=b.search_result_resolution_id) THEN
     RAISE EXCEPTION 'screening basis witness mismatch' USING ERRCODE='P17D3'; END IF;
   END IF;
  END LOOP;
  j:=j||jsonb_build_object('screening_basis',jsonb_build_object(
   'probes',(SELECT coalesce(jsonb_agg(jsonb_build_object(
      'search_execution',jsonb_build_object('type','LiteratureSearchExecution','id',p.search_execution_id),
      'query_index',p.query_index,'disposition',p.disposition,'rationale',p.rationale)
      ORDER BY p.search_execution_id,p.query_index),'[]') FROM novelty_assessment_probes p WHERE p.novelty_assessment_id=aid),
   'results',(SELECT coalesce(jsonb_agg(jsonb_build_object(
      'search_result_record',jsonb_build_object('type','SearchResultRecord','id',s.search_result_record_id),
      'disposition',s.disposition,'criteria_ordinals',s.criteria_ordinals,'rationale',s.rationale,
      'prior_art_relation',pr216_ref('PriorArtRelation',s.prior_art_relation_id,r.content_hash),
      'search_result_resolution',pr216_ref('SearchResultResolution',s.search_result_resolution_id,w.content_hash))
      ORDER BY s.search_result_record_id),'[]') FROM novelty_assessment_screening_results s
      LEFT JOIN prior_art_relations r ON r.id=s.prior_art_relation_id
      LEFT JOIN search_result_resolutions w ON w.id=s.search_result_resolution_id WHERE s.novelty_assessment_id=aid)));
 END IF;
 IF a.hash_scheme<>'sha256-cjson-v1' OR a.content_hash IS DISTINCT FROM pr216_hash(j) THEN
  RAISE EXCEPTION 'assessment hash mismatch' USING ERRCODE='P17D3'; END IF;
 RETURN a.content_hash;
END $$;
CREATE FUNCTION b23_review_hash(r internal_review_records) RETURNS text LANGUAGE sql
 SET search_path=pg_catalog,public,pg_temp AS $$
 SELECT pr216_hash(jsonb_build_object('type','InternalReviewRecord','material_version',2,'project_id',r.project_id,
  'target',pr216_ref('NoveltyAssessment',r.novelty_assessment_id,r.target_content_hash),'reviewer_actor_id',r.reviewer_actor_id,
  'review_type',r.review_type,'recommendation',r.recommendation,'summary',r.summary)) $$;
CREATE FUNCTION b23_check_review(r internal_review_records) RETURNS void LANGUAGE plpgsql
 SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE a novelty_assessments; cv claim_versions;
BEGIN
 SELECT * INTO a FROM novelty_assessments WHERE id=r.novelty_assessment_id;
 SELECT * INTO cv FROM claim_versions WHERE id=a.claim_version_id;
 IF r.material_version<>2 OR r.target_content_hash IS DISTINCT FROM b23_assessment_hash(a.id,r.project_id)
  OR r.content_hash IS DISTINCT FROM b23_review_hash(r) OR r.hash_scheme<>'sha256-cjson-v1'
  OR r.summary<>normalize(r.summary,NFC) OR char_length(r.summary) NOT BETWEEN 1 AND 16000 OR btrim(r.summary)=''
  OR r.created_at<a.created_at OR r.created_at>clock_timestamp() THEN RAISE EXCEPTION 'novelty review material mismatch' USING ERRCODE='P17D3'; END IF;
 IF r.reviewer_actor_id IN (a.created_by,a.assessed_by,cv.created_by) THEN
  RAISE EXCEPTION 'independent novelty reviewer required' USING ERRCODE='P23C1'; END IF;
 IF NOT EXISTS(SELECT 1 FROM actors actor JOIN project_memberships m ON m.actor_id=actor.id
   JOIN project_role_assignments role ON role.membership_id=m.id AND role.actor_id=m.actor_id AND role.project_id=m.project_id
   WHERE actor.id=r.reviewer_actor_id AND actor.actor_type='HUMAN' AND actor.created_at<=r.created_at
    AND (actor.retired_at IS NULL OR r.created_at<actor.retired_at) AND m.project_id=r.project_id AND m.started_at<=r.created_at
    AND role.role IN ('OWNER','REVIEWER') AND role.effective_from<=r.created_at AND (role.effective_until IS NULL OR r.created_at<role.effective_until)
    AND (SELECT e.new_status FROM project_membership_events e WHERE e.membership_id=m.id AND e.occurred_at<=r.created_at ORDER BY e.occurred_at DESC,e.id DESC LIMIT 1)='ACTIVE'
    AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=actor.id AND b.bound_at<=r.created_at AND (b.revoked_at IS NULL OR r.created_at<b.revoked_at))) THEN
  RAISE EXCEPTION 'novelty reviewer authority unavailable' USING ERRCODE='P23A1'; END IF;
END $$;
CREATE FUNCTION b23_review_guard() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,public,pg_temp AS $$
BEGIN
 IF NEW.material_version<>2 THEN RETURN NEW; END IF;
 LOCK TABLE internal_review_records,review_issue_events,review_issues IN ROW EXCLUSIVE MODE;
 IF NOT b23_prelocked() THEN RAISE EXCEPTION 'B23 prelocks required' USING ERRCODE='P17D3'; END IF;
 PERFORM 1 FROM claim_versions WHERE id=(SELECT claim_version_id FROM novelty_assessments WHERE id=NEW.novelty_assessment_id) FOR UPDATE;
 PERFORM 1 FROM novelty_assessments WHERE id=NEW.novelty_assessment_id FOR SHARE;
 IF NOT b23_authorized(NEW.reviewer_actor_id,NEW.project_id,clock_timestamp(),ARRAY['OWNER','REVIEWER'],true) OR NOT EXISTS(SELECT 1 FROM projects WHERE id=NEW.project_id AND lifecycle_status='ACTIVE') THEN RAISE EXCEPTION 'live reviewer authority required' USING ERRCODE='P23A1'; END IF;
 IF (SELECT count(*) FROM (SELECT * FROM b23_dependencies(ARRAY[NEW.novelty_assessment_id]) LIMIT 10001) deps)>10000 THEN RAISE EXCEPTION 'dependency admission cap' USING ERRCODE='P17D4'; END IF;
 PERFORM b23_check_review(NEW); RETURN NEW;
END $$;
CREATE TRIGGER trg_b23_review_guard BEFORE INSERT ON internal_review_records FOR EACH ROW EXECUTE FUNCTION b23_review_guard();
CREATE FUNCTION b23_is_novelty_review(identity uuid) RETURNS boolean LANGUAGE sql STABLE
 SET search_path=pg_catalog,public,pg_temp AS $$
 SELECT EXISTS(SELECT 1 FROM internal_review_records WHERE id=identity AND material_version=2) $$;
CREATE FUNCTION b23_is_novelty_issue(identity uuid) RETURNS boolean LANGUAGE sql STABLE
 SET search_path=pg_catalog,public,pg_temp AS $$
 SELECT EXISTS(SELECT 1 FROM review_issues issue JOIN internal_review_records review ON review.id=issue.review_record_id WHERE issue.id=identity AND review.material_version=2) $$;
CREATE FUNCTION b23_complete_review() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE rid uuid; r internal_review_records; total integer;
BEGIN
 IF TG_TABLE_NAME='internal_review_records' THEN rid:=NEW.id;
 ELSIF TG_TABLE_NAME='review_issues' THEN rid:=NEW.review_record_id;
 ELSE SELECT review_record_id INTO rid FROM review_issues WHERE id=NEW.issue_id; END IF;
 SELECT * INTO r FROM internal_review_records WHERE id=rid;
 IF r.material_version<>2 THEN RETURN NULL; END IF;
 PERFORM b23_check_review(r);
 SELECT count(*) INTO total FROM review_issues WHERE review_record_id=rid;
 IF total>100 OR EXISTS(SELECT 1 FROM review_issues i WHERE i.review_record_id=rid AND
   (i.ordinal<0 OR i.ordinal>=total OR i.status<>'OPEN' OR i.created_at IS DISTINCT FROM r.created_at
    OR (SELECT count(*) FROM review_issue_events e WHERE e.issue_id=i.id)<>1
    OR NOT EXISTS(SELECT 1 FROM review_issue_events e WHERE e.issue_id=i.id AND e.prior_status IS NULL
      AND e.new_status='OPEN' AND e.actor_id=r.reviewer_actor_id AND e.occurred_at=i.created_at))) THEN
  RAISE EXCEPTION 'incomplete sealed novelty review' USING ERRCODE='P17D3'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER b23_complete_review_record AFTER INSERT ON internal_review_records DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (NEW.material_version=2) EXECUTE FUNCTION b23_complete_review();
CREATE CONSTRAINT TRIGGER b23_complete_review_issue AFTER INSERT ON review_issues DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (b23_is_novelty_review(NEW.review_record_id)) EXECUTE FUNCTION b23_complete_review();
CREATE CONSTRAINT TRIGGER b23_complete_review_event AFTER INSERT ON review_issue_events DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (b23_is_novelty_issue(NEW.issue_id)) EXECUTE FUNCTION b23_complete_review();
CREATE FUNCTION b23_action_hash(a revision_actions) RETURNS text LANGUAGE sql
 SET search_path=pg_catalog,public,pg_temp AS $$
 SELECT pr216_hash(jsonb_build_object('type','RevisionAction','material_version',2,
  'review_issue',jsonb_build_object('type','ReviewIssue','id',a.review_issue_id),'decision',NULL,
  'action_type','NOVELTY_REASSESSMENT','results',jsonb_build_object(
   'result_experiment_spec_version',NULL,'result_run',NULL,'result_statistical_result',NULL,
   'result_claim_version',NULL,'result_scientific_conclusion_version',NULL,'result_manuscript_version',NULL,'result_source_version',NULL,
   'result_novelty_assessment',pr216_ref('NoveltyAssessment',a.result_novelty_assessment_id,(SELECT content_hash FROM novelty_assessments WHERE id=a.result_novelty_assessment_id))),
  'supersedes_revision_action',pr216_ref('RevisionAction',a.supersedes_revision_action_id,(SELECT content_hash FROM revision_actions WHERE id=a.supersedes_revision_action_id)),
  'created_by',jsonb_build_object('type','ActorIdentity','id',a.created_by))) $$;
CREATE FUNCTION b23_validate_revision(a revision_actions, admission boolean DEFAULT true, seen uuid[] DEFAULT '{}') RETURNS void LANGUAGE plpgsql
 SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE i review_issues; r internal_review_records; old novelty_assessments; result novelty_assessments; prior revision_actions;
BEGIN
 IF a.id=ANY(seen) THEN RAISE EXCEPTION 'revision cycle' USING ERRCODE='P17D3'; END IF;
 SELECT * INTO i FROM review_issues WHERE id=a.review_issue_id;
 SELECT * INTO r FROM internal_review_records WHERE id=i.review_record_id;
 SELECT * INTO old FROM novelty_assessments WHERE id=r.novelty_assessment_id;
 SELECT * INTO result FROM novelty_assessments WHERE id=a.result_novelty_assessment_id;
 IF admission THEN
  IF NOT b23_prelocked() THEN RAISE EXCEPTION 'B23 prelocks required' USING ERRCODE='P17D3'; END IF;
  PERFORM 1 FROM claim_versions WHERE id=old.claim_version_id FOR UPDATE;
  PERFORM 1 FROM novelty_assessments WHERE id IN (old.id,result.id) ORDER BY id FOR SHARE;
  PERFORM 1 FROM internal_review_records WHERE id=r.id FOR SHARE;
  PERFORM 1 FROM review_issues WHERE id=i.id FOR SHARE;
  IF a.supersedes_revision_action_id IS NOT NULL THEN PERFORM 1 FROM revision_actions WHERE id=a.supersedes_revision_action_id FOR UPDATE; END IF;
  SELECT * INTO i FROM review_issues WHERE id=a.review_issue_id;
  IF (SELECT count(*) FROM (SELECT * FROM b23_dependencies(ARRAY[old.id,result.id]) LIMIT 10001) deps)>10000 THEN RAISE EXCEPTION 'dependency admission cap' USING ERRCODE='P17D4'; END IF;
  PERFORM b07_current_target(result.claim_version_id,r.project_id,'claim_versions');
  IF EXISTS(SELECT 1 FROM search_coverage_executions ce JOIN search_query_records q ON q.literature_search_execution_id=ce.search_execution_id JOIN search_result_records x ON x.search_query_record_id=q.id JOIN search_result_resolutions resolution ON resolution.search_result_record_id=x.id WHERE ce.search_coverage_id=result.search_coverage_id AND resolution.source_version_id IS NOT NULL AND NOT pr218_source_valid(resolution.source_version_id,r.project_id)) THEN
   RAISE EXCEPTION 'coverage input unusable' USING ERRCODE='P17D2'; END IF;
  IF i.status<>'OPEN' OR EXISTS(SELECT 1 FROM novelty_assessments WHERE supersedes_assessment_id=result.id)
   OR EXISTS(SELECT 1 FROM novelty_assessments WHERE id=result.id AND xmin=pg_current_xact_id()::xid)
   OR NOT pr218_claim_valid(result.claim_version_id)
   OR EXISTS(SELECT 1 FROM novelty_assessment_prior_art_inputs b JOIN prior_art_relations p ON p.id=b.prior_art_relation_id
     WHERE b.novelty_assessment_id=result.id AND (NOT pr218_source_valid(p.source_version_id,r.project_id)
      OR EXISTS(SELECT 1 FROM prior_art_relations WHERE supersedes_prior_art_relation_id=p.id)
      OR EXISTS(SELECT 1 FROM prior_art_evidence_inputs e JOIN literature_evidence v ON v.id=e.literature_evidence_id WHERE e.prior_art_relation_id=p.id AND (v.review_status<>'VERIFIED' OR NOT EXISTS(SELECT 1 FROM literature_evidence_review_events review JOIN actors actor ON actor.id=review.reviewed_by WHERE review.id=(SELECT id FROM literature_evidence_review_events WHERE literature_evidence_id=v.id ORDER BY reviewed_at DESC,id DESC LIMIT 1) AND review.new_status='VERIFIED' AND actor.actor_type='HUMAN' AND review.reviewed_by<>v.created_by)))))
   THEN RAISE EXCEPTION 'usable precommitted terminal result required' USING ERRCODE='P17D2'; END IF;
 END IF;
 IF a.material_version<>2 OR a.action_type<>'NOVELTY_REASSESSMENT' OR a.decision_record_id IS NOT NULL
   OR old.id IS NULL OR result.id IS NULL OR result.supersedes_assessment_id IS DISTINCT FROM old.id
   OR result.claim_version_id IS DISTINCT FROM old.claim_version_id THEN
  RAISE EXCEPTION 'direct exact novelty result required' USING ERRCODE='P17D3'; END IF;
 IF a.created_at<r.created_at OR a.created_at<result.created_at OR a.created_at>clock_timestamp()
 OR NOT b23_authorized(a.created_by,r.project_id,a.created_at,ARRAY['OWNER','RESEARCHER'],false)
 OR (admission AND (NOT b23_authorized(a.created_by,r.project_id,clock_timestamp(),ARRAY['OWNER','RESEARCHER'],false) OR NOT EXISTS(SELECT 1 FROM projects WHERE id=r.project_id AND lifecycle_status='ACTIVE'))) THEN
 RAISE EXCEPTION 'revision attribution invalid' USING ERRCODE='P23A1'; END IF;
 PERFORM b23_check_review(r); PERFORM b23_assessment_hash(result.id,r.project_id);
 IF a.supersedes_revision_action_id IS NOT NULL THEN
  SELECT * INTO prior FROM revision_actions WHERE id=a.supersedes_revision_action_id;
  IF prior.review_issue_id IS DISTINCT FROM a.review_issue_id OR prior.decision_record_id IS NOT NULL OR prior.material_version<>2
    OR (admission AND EXISTS(SELECT 1 FROM revision_actions WHERE supersedes_revision_action_id=prior.id AND id<>a.id)) THEN
   RAISE EXCEPTION 'same concern unused predecessor required' USING ERRCODE='P17D3'; END IF;
  PERFORM b23_validate_revision(prior,false,array_append(seen,a.id));
 END IF;
 IF a.content_hash IS DISTINCT FROM b23_action_hash(a) OR a.hash_scheme<>'sha256-cjson-v1' THEN
  RAISE EXCEPTION 'novelty revision hash mismatch' USING ERRCODE='P17D3'; END IF;
END $$;
CREATE FUNCTION b23_revision_guard() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,public,pg_temp AS $$ BEGIN
 IF NEW.material_version=2 THEN PERFORM b23_validate_revision(NEW); END IF; RETURN NEW; END $$;
CREATE TRIGGER trg_b23_revision_guard BEFORE INSERT ON revision_actions FOR EACH ROW EXECUTE FUNCTION b23_revision_guard();
CREATE FUNCTION b23_complete_revision() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,public,pg_temp AS $$ BEGIN
 IF NEW.material_version=2 THEN PERFORM b23_validate_revision(NEW); END IF; RETURN NULL; END $$;
CREATE CONSTRAINT TRIGGER b23_complete_revision_action AFTER INSERT ON revision_actions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b23_complete_revision();
CREATE FUNCTION b23_validate_re_review(link revision_action_re_reviews, take_locks boolean) RETURNS void LANGUAGE plpgsql
 SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE a revision_actions; r internal_review_records; original internal_review_records; i review_issues; result novelty_assessments;
BEGIN
 SELECT * INTO a FROM revision_actions WHERE id=link.revision_action_id;
 SELECT * INTO r FROM internal_review_records WHERE id=link.internal_review_record_id;
 SELECT * INTO i FROM review_issues WHERE id=a.review_issue_id;
 SELECT * INTO original FROM internal_review_records WHERE id=i.review_record_id;
 SELECT * INTO result FROM novelty_assessments WHERE id=a.result_novelty_assessment_id;
 IF NOT b23_prelocked() THEN RAISE EXCEPTION 'B23 prelocks required' USING ERRCODE='P17D3'; END IF;
 IF take_locks THEN
  PERFORM 1 FROM claim_versions WHERE id=result.claim_version_id FOR UPDATE;
  PERFORM 1 FROM novelty_assessments WHERE id IN (original.novelty_assessment_id,result.id) ORDER BY id FOR SHARE;
  PERFORM 1 FROM internal_review_records WHERE id IN (original.id,r.id) ORDER BY id FOR SHARE;
  PERFORM 1 FROM review_issues WHERE id=i.id FOR SHARE;
  PERFORM 1 FROM revision_actions WHERE id=a.id FOR SHARE;
 END IF;
 SELECT * INTO a FROM revision_actions WHERE id=link.revision_action_id;
 SELECT * INTO r FROM internal_review_records WHERE id=link.internal_review_record_id;
 PERFORM b23_validate_revision(a,false); PERFORM b23_check_review(r);
 IF NOT b23_authorized(link.recorded_by,r.project_id,link.recorded_at,ARRAY['OWNER','REVIEWER'],true)
  OR NOT b23_authorized(link.recorded_by,r.project_id,clock_timestamp(),ARRAY['OWNER','REVIEWER'],true)
  OR r.created_at<a.created_at
  OR EXISTS(SELECT 1 FROM revision_actions WHERE id=a.id AND xmin=pg_current_xact_id()::xid)
  OR EXISTS(SELECT 1 FROM internal_review_records WHERE id=r.id AND xmin=pg_current_xact_id()::xid) THEN
  RAISE EXCEPTION 'precommitted independently authorized correspondence required' USING ERRCODE='P17D3'; END IF;
 IF r.id=original.id OR r.novelty_assessment_id IS DISTINCT FROM result.id OR r.project_id<>original.project_id
  OR r.target_content_hash IS DISTINCT FROM result.content_hash OR link.recorded_by IS DISTINCT FROM r.reviewer_actor_id
  OR link.recorded_at<r.created_at OR link.recorded_at<a.created_at OR link.recorded_at>clock_timestamp()
  OR EXISTS(SELECT 1 FROM revision_actions WHERE supersedes_revision_action_id=a.id) THEN
  RAISE EXCEPTION 'exact novelty correspondence required' USING ERRCODE='P17D3'; END IF;
 IF r.reviewer_actor_id=a.created_by THEN RAISE EXCEPTION 'independent action reviewer required' USING ERRCODE='P23C1'; END IF;
END $$;
"""

LEGACY_SHAPE = r"""ALTER TABLE revision_actions ADD CONSTRAINT revision_action_shape CHECK (((((action_type)::text = 'NEW_EXPERIMENT'::text) AND (result_experiment_spec_version_id IS NOT NULL) AND (result_run_id IS NOT NULL) AND (num_nonnulls(result_statistical_result_id, result_claim_version_id, result_scientific_conclusion_version_id, result_manuscript_version_id, result_source_version_id) = 0)) OR (((action_type)::text = 'ANALYSIS_CHANGE'::text) AND (result_statistical_result_id IS NOT NULL) AND (num_nonnulls(result_experiment_spec_version_id, result_run_id, result_claim_version_id, result_scientific_conclusion_version_id, result_manuscript_version_id, result_source_version_id) = 0)) OR (((action_type)::text = 'CLAIM_CHANGE'::text) AND (result_claim_version_id IS NOT NULL) AND (num_nonnulls(result_experiment_spec_version_id, result_run_id, result_statistical_result_id, result_scientific_conclusion_version_id, result_manuscript_version_id, result_source_version_id) = 0)) OR (((action_type)::text = 'CONCLUSION_CHANGE'::text) AND (result_scientific_conclusion_version_id IS NOT NULL) AND (num_nonnulls(result_experiment_spec_version_id, result_run_id, result_statistical_result_id, result_claim_version_id, result_manuscript_version_id, result_source_version_id) = 0)) OR (((action_type)::text = 'MANUSCRIPT_CHANGE'::text) AND (result_manuscript_version_id IS NOT NULL) AND (num_nonnulls(result_experiment_spec_version_id, result_run_id, result_statistical_result_id, result_claim_version_id, result_scientific_conclusion_version_id, result_source_version_id) = 0)) OR (((action_type)::text = 'SOURCE_CHANGE'::text) AND (result_source_version_id IS NOT NULL) AND (num_nonnulls(result_experiment_spec_version_id, result_run_id, result_statistical_result_id, result_claim_version_id, result_scientific_conclusion_version_id, result_manuscript_version_id) = 0)) OR (((action_type)::text = 'NO_CHANGE'::text) AND (num_nonnulls(result_experiment_spec_version_id, result_run_id, result_statistical_result_id, result_claim_version_id, result_scientific_conclusion_version_id, result_manuscript_version_id, result_source_version_id) = 0))))"""

LEGACY_REVIEW_TARGET = r"""ALTER TABLE internal_review_records ADD CONSTRAINT ck_pr214_one_target CHECK ((num_nonnulls(manuscript_version_id, claim_version_id, scientific_conclusion_version_id, artifact_version_id) = 1))"""


def upgrade() -> None:
    connection = op.get_bind()
    for name, definition in LEGACY.items():
        current = connection.execute(
            text(
                "SELECT pg_get_functiondef(oid) FROM pg_proc WHERE pronamespace='public'::regnamespace AND proname=:name"
            ),
            {"name": name},
        ).scalar_one()
        if (
            hashlib.sha256(current.encode()).digest()
            != hashlib.sha256(definition.encode()).digest()
        ):
            raise RuntimeError("B23 unexpected guard baseline: " + name)
    current_triggers = dict(
        connection.execute(
            text(
                "SELECT tgname,pg_get_triggerdef(oid) FROM pg_trigger WHERE NOT tgisinternal AND tgrelid IN ('internal_review_records'::regclass,'review_issues'::regclass,'review_issue_events'::regclass,'revision_actions'::regclass,'revision_action_re_reviews'::regclass)"
            )
        ).all()
    )
    if current_triggers != TRIGGERS:
        raise RuntimeError("B23 unexpected dependent trigger inventory")
    op.execute(DDL)
    op.execute(SQL)
    for definition in DISPATCH.values():
        op.execute(definition)


def downgrade() -> None:
    op.execute(
        "LOCK TABLE internal_review_records,review_issue_events,review_issues,revision_action_re_reviews,revision_actions IN ACCESS EXCLUSIVE MODE"
    )
    op.execute("""DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM internal_review_records WHERE material_version=2)
        OR EXISTS(SELECT 1 FROM revision_actions WHERE material_version=2)
        OR EXISTS(SELECT 1 FROM revision_action_re_reviews l JOIN internal_review_records r ON r.id=l.internal_review_record_id JOIN revision_actions a ON a.id=l.revision_action_id WHERE r.material_version=2 OR a.material_version=2) THEN
        RAISE EXCEPTION 'cannot downgrade populated B23 history'; END IF;
    END $$""")
    for definition in LEGACY.values():
        op.execute(definition)
    op.execute("""
    DROP TRIGGER trg_b23_review_guard ON internal_review_records;
    DROP TRIGGER b23_complete_review_record ON internal_review_records;
    DROP TRIGGER b23_complete_review_issue ON review_issues;
    DROP TRIGGER b23_complete_review_event ON review_issue_events;
    DROP TRIGGER trg_b23_revision_guard ON revision_actions;
    DROP TRIGGER b23_complete_revision_action ON revision_actions;
    DROP FUNCTION b23_dependencies(uuid[]);
    DROP FUNCTION b23_authorized(uuid,uuid,timestamptz,text[],boolean);
    DROP FUNCTION b23_complete_revision();
    DROP FUNCTION b23_revision_guard();
    DROP FUNCTION b23_validate_re_review(revision_action_re_reviews,boolean);
    DROP FUNCTION b23_validate_revision(revision_actions,boolean,uuid[]);
    DROP FUNCTION b23_action_hash(revision_actions);
    DROP FUNCTION b23_complete_review();
    DROP FUNCTION b23_is_novelty_issue(uuid);
    DROP FUNCTION b23_is_novelty_review(uuid);
    DROP FUNCTION b23_review_guard();
    DROP FUNCTION b23_check_review(internal_review_records);
    DROP FUNCTION b23_review_hash(internal_review_records);
    DROP FUNCTION b23_assessment_hash(uuid,uuid,uuid[]);
    DROP FUNCTION b23_prior_hash(uuid,uuid,uuid[]);
    DROP FUNCTION b23_coverage_hash(uuid);
    DROP FUNCTION b23_verify_capture(uuid);
    DROP FUNCTION b23_resolution_hash(search_result_resolutions);
    DROP FUNCTION b23_prelocked();
    ALTER TABLE revision_actions DROP CONSTRAINT ck_b23_revision_shape;
    ALTER TABLE revision_actions DROP COLUMN result_novelty_assessment_id, DROP COLUMN material_version;
    ALTER TABLE internal_review_records DROP CONSTRAINT ck_b23_review_target, DROP CONSTRAINT ck_b23_review_version;
    ALTER TABLE internal_review_records DROP COLUMN novelty_assessment_id, DROP COLUMN material_version;

    """)
    op.execute(LEGACY_REVIEW_TARGET)
    op.execute(LEGACY_SHAPE)
