"""B08 immutable terminal Issue events and guarded status projection."""

# Literal SQL preserves original scientific material and historical event membership.
# ruff: noqa: E501

from alembic import op

revision = "0053_b08_issue_disposition"
down_revision = "0052_b07_revision_decisions"
branch_labels = None
depends_on = None

_INVENTORY = "actor_subject_bindings, actors, artifact_versions, artifacts, audit_findings, claims, correction_records, datasets, experiment_spec_versions, experiment_specs, impact_assessments, impact_targets, internal_review_records, literature_evidence, literature_evidence_review_events, literature_source_project_links, literature_sources, metric_definition_versions, metric_definitions, project_membership_events, project_memberships, project_role_assignments, projects, runs, scientific_conclusions, source_versions"

_DDL = r"""
LOCK TABLE review_issues,review_issue_events IN ACCESS EXCLUSIVE MODE;
DO $$ BEGIN
  IF EXISTS(SELECT 1 FROM review_issues i JOIN internal_review_records r ON r.id=i.review_record_id
    WHERE i.status<>'OPEN' OR i.created_at<r.created_at OR i.created_at>clock_timestamp() OR (SELECT count(*) FROM review_issue_events WHERE issue_id=i.id)<>1
      OR NOT EXISTS(SELECT 1 FROM review_issue_events e WHERE e.issue_id=i.id AND e.prior_status IS NULL
        AND e.new_status='OPEN' AND e.actor_id=r.reviewer_actor_id AND e.occurred_at=i.created_at)) THEN
    RAISE EXCEPTION 'retained Issue history inconsistent' USING ERRCODE='P17F2'; END IF;
END $$;
ALTER TABLE review_issues DROP CONSTRAINT review_issues_status_check;
ALTER TABLE review_issue_events DROP CONSTRAINT review_issue_events_new_status_check,
  DROP CONSTRAINT review_issue_events_prior_status_check, DROP CONSTRAINT review_issue_events_issue_id_key;
ALTER TABLE review_issues ADD CONSTRAINT ck_b08_issue_status CHECK(status IN ('OPEN','ADDRESSED','DISMISSED'));
ALTER TABLE review_issue_events ADD COLUMN revision_action_id UUID,
  ADD COLUMN re_review_record_id UUID, ADD COLUMN decision_id UUID, ADD COLUMN rationale TEXT,
  ADD CONSTRAINT fk_b08_event_action FOREIGN KEY(revision_action_id) REFERENCES revision_actions(id) ON DELETE RESTRICT,
  ADD CONSTRAINT fk_b08_event_re_review FOREIGN KEY(re_review_record_id) REFERENCES internal_review_records(id) ON DELETE RESTRICT,
  ADD CONSTRAINT fk_b08_event_decision FOREIGN KEY(decision_id) REFERENCES decision_records(id) ON DELETE RESTRICT,
  ADD CONSTRAINT fk_b08_event_mapping FOREIGN KEY(revision_action_id,re_review_record_id)
    REFERENCES revision_action_re_reviews(revision_action_id,internal_review_record_id) ON DELETE RESTRICT,
  ADD CONSTRAINT ck_b08_event_shape CHECK (
    (prior_status IS NULL AND new_status='OPEN' AND revision_action_id IS NULL AND re_review_record_id IS NULL
      AND decision_id IS NULL AND rationale IS NULL) OR
    (prior_status IS NOT NULL AND prior_status='OPEN' AND new_status IN ('ADDRESSED','DISMISSED')
      AND revision_action_id IS NOT NULL AND re_review_record_id IS NOT NULL
      AND rationale IS NOT NULL AND length(btrim(rationale)) BETWEEN 1 AND 16000
      AND (new_status<>'DISMISSED' OR decision_id IS NOT NULL)));
CREATE UNIQUE INDEX uq_b08_issue_open ON review_issue_events(issue_id) WHERE prior_status IS NULL;
CREATE UNIQUE INDEX uq_b08_issue_terminal ON review_issue_events(issue_id) WHERE prior_status='OPEN';
CREATE INDEX ix_b08_event_action ON review_issue_events(revision_action_id);
CREATE INDEX ix_b08_event_re_review ON review_issue_events(re_review_record_id);
CREATE INDEX ix_b08_event_decision ON review_issue_events(decision_id);
"""

_ISSUE_GUARD = r"""
CREATE OR REPLACE FUNCTION pr214_issue_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE review_project UUID; target_id UUID; checked_target UUID; manuscript_id UUID; checked_manuscript UUID;
    BEGIN
      IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Issue history immutable' USING ERRCODE='P17F1'; END IF;
      IF TG_OP='UPDATE' THEN
        IF OLD.status<>'OPEN' OR NEW.status NOT IN ('ADDRESSED','DISMISSED')
          OR (to_jsonb(NEW)-'status') IS DISTINCT FROM (to_jsonb(OLD)-'status') THEN
          RAISE EXCEPTION 'only disposition projection may change' USING ERRCODE='P17F1'; END IF;
        IF NOT EXISTS(SELECT 1 FROM review_issue_events WHERE issue_id=OLD.id
          AND prior_status=OLD.status AND new_status=NEW.status
          AND xmin::text::bigint=pg_current_xact_id()::text::bigint) THEN
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
    END $$;
"""

_MAPPING = r"""

CREATE FUNCTION b08_validate_mapping(link revision_action_re_reviews, disposer UUID) RETURNS void LANGUAGE plpgsql AS $$
DECLARE attestation internal_review_records; a revision_actions; old internal_review_records; r internal_review_records; iid UUID; tid UUID; old_tid UUID; cs UUID[]; old_cv claim_versions; old_sc scientific_conclusion_versions; good BOOLEAN; witness UUID; old_witness UUID; candidate UUID;
BEGIN
  SELECT * INTO a FROM revision_actions WHERE id=link.revision_action_id;
  IF a.id IS NULL THEN RAISE EXCEPTION 'exact action required' USING ERRCODE='P17F2'; END IF;
  SELECT coalesce(a.review_issue_id,c.review_issue_id) INTO iid FROM (SELECT 1) x LEFT JOIN decision_revision_concerns c ON c.decision_id=a.decision_record_id;
  SELECT r0.* INTO old FROM review_issues i JOIN internal_review_records r0 ON r0.id=i.review_record_id WHERE i.id=iid;
  SELECT * INTO r FROM internal_review_records WHERE id=link.internal_review_record_id;
  IF r.id IS NULL OR r.project_id IS DISTINCT FROM old.project_id OR r.reviewer_actor_id<>link.recorded_by
    OR r.created_at<a.created_at OR link.recorded_at<r.created_at OR r.reviewer_actor_id=a.created_by
    OR EXISTS(SELECT 1 FROM revision_actions WHERE id=a.id AND xmin::text::bigint=pg_current_xact_id()::text::bigint)
    OR EXISTS(SELECT 1 FROM internal_review_records WHERE id=r.id AND xmin::text::bigint=pg_current_xact_id()::text::bigint) THEN
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
END $$;
"""

_RESTORE_ISSUE = r"""
    CREATE OR REPLACE FUNCTION pr214_issue_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE review_project UUID; target_id UUID; checked_target UUID; manuscript_id UUID; checked_manuscript UUID;
    BEGIN
      IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'initial issue is immutable' USING ERRCODE='P17E1';
      END IF;
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
        WHERE id=NEW.review_record_id FOR SHARE;
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
    END $$;
"""

_EVENTS = r"""
CREATE FUNCTION b08_validate_event(e review_issue_events) RETURNS void LANGUAGE plpgsql AS $$
DECLARE i review_issues; old internal_review_records; r internal_review_records;
  a revision_actions; d decision_records; link revision_action_re_reviews; effective UUID;
BEGIN
  SELECT * INTO i FROM review_issues WHERE id=e.issue_id;
  SELECT * INTO old FROM internal_review_records WHERE id=i.review_record_id;
  SELECT * INTO r FROM internal_review_records WHERE id=e.re_review_record_id;
  SELECT * INTO a FROM revision_actions WHERE id=e.revision_action_id;
  SELECT * INTO d FROM decision_records WHERE id=e.decision_id;
  SELECT * INTO link FROM revision_action_re_reviews WHERE revision_action_id=a.id AND internal_review_record_id=r.id;
  SELECT coalesce(a.review_issue_id,c.review_issue_id) INTO effective FROM (SELECT 1) x
    LEFT JOIN decision_revision_concerns c ON c.decision_id=a.decision_record_id;
  IF i.id IS NULL OR old.id IS NULL OR r.id IS NULL OR a.id IS NULL OR link.revision_action_id IS NULL
    OR effective IS DISTINCT FROM i.id OR old.project_id IS DISTINCT FROM r.project_id
    OR (old.claim_version_id IS NULL AND old.scientific_conclusion_version_id IS NULL)
    OR r.id=old.id OR r.recommendation NOT IN ('ACCEPT','MINOR_REVISION')
    OR a.decision_record_id IS DISTINCT FROM e.decision_id
    OR (e.new_status='ADDRESSED' AND (a.action_type NOT IN ('NEW_EXPERIMENT','ANALYSIS_CHANGE','CLAIM_CHANGE','CONCLUSION_CHANGE','SOURCE_CHANGE')
      OR (i.severity='BLOCKING' AND d.id IS NULL) OR (d.id IS NOT NULL AND d.decision<>'REQUIRE_CHANGE')))
    OR (e.new_status='DISMISSED' AND (a.action_type<>'NO_CHANGE' OR d.id IS NULL OR d.decision<>'ACCEPT_NO_CHANGE'))
    OR e.rationale IS NULL OR e.rationale<>normalize(e.rationale,NFC) OR length(e.rationale)>16000
    OR e.occurred_at<greatest(i.created_at,a.created_at,r.created_at,link.recorded_at,d.decided_at)
    OR e.occurred_at>clock_timestamp() THEN
    RAISE EXCEPTION 'exact complete disposition basis required' USING ERRCODE='P17F2'; END IF;
  PERFORM b07_validate_revision(a);
  IF a.content_hash IS DISTINCT FROM b07_action_hash(a) THEN
    RAISE EXCEPTION 'saved action hash invalid' USING ERRCODE='P17F2'; END IF;
  PERFORM b08_validate_mapping(link,e.actor_id);
  IF NOT EXISTS(SELECT 1 FROM actors actor JOIN project_memberships m ON m.actor_id=actor.id
    JOIN project_role_assignments role ON role.membership_id=m.id AND role.actor_id=m.actor_id AND role.project_id=m.project_id
    WHERE actor.id=e.actor_id AND actor.actor_type='HUMAN' AND actor.created_at<=e.occurred_at
      AND (actor.retired_at IS NULL OR e.occurred_at<actor.retired_at) AND m.project_id=old.project_id AND m.started_at<=e.occurred_at
      AND (role.role='OWNER' OR (e.new_status='ADDRESSED' AND e.actor_id=old.reviewer_actor_id AND role.role='REVIEWER'))
      AND role.effective_from<=e.occurred_at AND (role.effective_until IS NULL OR e.occurred_at<role.effective_until)
      AND (SELECT ev.new_status FROM project_membership_events ev WHERE ev.membership_id=m.id AND ev.occurred_at<=e.occurred_at
        ORDER BY ev.occurred_at DESC,ev.id DESC LIMIT 1)='ACTIVE'
      AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=actor.id AND b.bound_at<=e.occurred_at
        AND (b.revoked_at IS NULL OR e.occurred_at<b.revoked_at))) THEN
    RAISE EXCEPTION 'historical independent HUMAN disposer authority required' USING ERRCODE='P17F2'; END IF;
END $$;

CREATE FUNCTION b08_check_history(iid UUID) RETURNS void LANGUAGE plpgsql AS $$
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
    IF EXISTS(SELECT 1 FROM review_issue_events WHERE id=terminal.id AND xmin::text::bigint=pg_current_xact_id()::text::bigint) THEN
      IF EXISTS(SELECT 1 FROM review_issues WHERE review_record_id=terminal.re_review_record_id AND status='OPEN' AND severity IN ('MAJOR','BLOCKING'))
        OR EXISTS(SELECT 1 FROM revision_actions WHERE supersedes_revision_action_id=terminal.revision_action_id) THEN
        RAISE EXCEPTION 'new disposition admission changed before commit' USING ERRCODE='P17R1'; END IF;
      IF terminal.new_status='ADDRESSED' THEN
        SELECT * INTO link FROM revision_action_re_reviews WHERE revision_action_id=terminal.revision_action_id AND internal_review_record_id=terminal.re_review_record_id;
        PERFORM b07_validate_re_review(link,false);
      END IF;
    END IF;
  END IF;
END $$;

CREATE FUNCTION b08_event_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE i review_issues; old internal_review_records; r internal_review_records; iid UUID;
  a revision_actions; link revision_action_re_reviews;
BEGIN
  IF NEW.prior_status IS NULL THEN
    SELECT * INTO i FROM review_issues WHERE id=NEW.issue_id;
    SELECT * INTO old FROM internal_review_records WHERE id=i.review_record_id;
    IF NOT EXISTS(SELECT 1 FROM review_issues WHERE id=NEW.issue_id AND xmin::text::bigint=pg_current_xact_id()::text::bigint)
      OR NEW.new_status<>'OPEN' OR NEW.actor_id IS DISTINCT FROM old.reviewer_actor_id
      OR NEW.occurred_at IS DISTINCT FROM i.created_at THEN
      RAISE EXCEPTION 'exact new Issue root required' USING ERRCODE='P17F2'; END IF;
    RETURN NEW;
  END IF;
  LOCK TABLE INVENTORY IN SHARE MODE;
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
  IF EXISTS(SELECT 1 FROM revision_actions WHERE id=NEW.revision_action_id AND xmin::text::bigint=pg_current_xact_id()::text::bigint)
    OR EXISTS(SELECT 1 FROM revision_action_re_reviews WHERE revision_action_id=NEW.revision_action_id
      AND internal_review_record_id=NEW.re_review_record_id AND xmin::text::bigint=pg_current_xact_id()::text::bigint) THEN
    RAISE EXCEPTION 'prior committed action and mapping required' USING ERRCODE='P17F2'; END IF;
  IF NEW.new_status='ADDRESSED' THEN
    SELECT * INTO link FROM revision_action_re_reviews WHERE revision_action_id=NEW.revision_action_id AND internal_review_record_id=NEW.re_review_record_id;
    PERFORM b07_validate_re_review(link,false);
  END IF;
  NEW.occurred_at:=clock_timestamp();
  PERFORM b08_check_history(NEW.issue_id);
  PERFORM b08_validate_event(NEW);
  RETURN NEW;
END $$;
CREATE TRIGGER b08_event_guard BEFORE INSERT ON review_issue_events FOR EACH ROW EXECUTE FUNCTION b08_event_guard();
CREATE FUNCTION b08_project_status() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.prior_status='OPEN' THEN UPDATE review_issues SET status=NEW.new_status WHERE id=NEW.issue_id; END IF;
  RETURN NULL;
END $$;
CREATE TRIGGER b08_project_status AFTER INSERT ON review_issue_events FOR EACH ROW EXECUTE FUNCTION b08_project_status();
CREATE FUNCTION b08_complete_history() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE affected UUID;
BEGIN
  IF TG_TABLE_NAME='review_issues' THEN PERFORM b08_check_history(NEW.id);
    FOR affected IN SELECT issue_id FROM review_issue_events WHERE re_review_record_id=NEW.review_record_id
      AND prior_status='OPEN' AND xmin::text::bigint=pg_current_xact_id()::text::bigint LOOP
      PERFORM b08_check_history(affected);
    END LOOP;
  ELSE PERFORM b08_check_history(NEW.issue_id); END IF;
  RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER b08_complete_issue AFTER INSERT OR UPDATE ON review_issues
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b08_complete_history();
CREATE CONSTRAINT TRIGGER b08_complete_event AFTER INSERT ON review_issue_events
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b08_complete_history();
"""


def upgrade() -> None:
    op.execute(_DDL)
    op.execute(_ISSUE_GUARD)
    op.execute(_MAPPING)
    op.execute(_EVENTS.replace("INVENTORY", _INVENTORY))


def downgrade() -> None:
    op.execute("""
    LOCK TABLE review_issues,review_issue_events IN ACCESS EXCLUSIVE MODE;
    DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM review_issues WHERE status<>'OPEN')
        OR EXISTS(SELECT 1 FROM review_issue_events WHERE new_status<>'OPEN' OR prior_status IS NOT NULL
          OR revision_action_id IS NOT NULL OR re_review_record_id IS NOT NULL OR decision_id IS NOT NULL OR rationale IS NOT NULL) THEN
        RAISE EXCEPTION 'terminal Issue history cannot be removed' USING ERRCODE='P17F2'; END IF;
    END $$;
    DROP TRIGGER b08_complete_issue ON review_issues;
    DROP TRIGGER b08_complete_event ON review_issue_events;
    DROP TRIGGER b08_event_guard ON review_issue_events;
    DROP TRIGGER b08_project_status ON review_issue_events;
    DROP FUNCTION b08_complete_history();
    DROP FUNCTION b08_event_guard();
    DROP FUNCTION b08_project_status();
    DROP FUNCTION b08_check_history(UUID);
    DROP FUNCTION b08_validate_event(review_issue_events);
    DROP FUNCTION b08_validate_mapping(revision_action_re_reviews,UUID);
    DROP INDEX uq_b08_issue_open;
    DROP INDEX uq_b08_issue_terminal;
    ALTER TABLE review_issue_events DROP CONSTRAINT ck_b08_event_shape;
    ALTER TABLE review_issue_events DROP COLUMN revision_action_id, DROP COLUMN re_review_record_id,
      DROP COLUMN decision_id, DROP COLUMN rationale;
    ALTER TABLE review_issues DROP CONSTRAINT ck_b08_issue_status;
    ALTER TABLE review_issues ADD CONSTRAINT review_issues_status_check CHECK(status='OPEN');
    ALTER TABLE review_issue_events ADD CONSTRAINT review_issue_events_new_status_check CHECK(new_status='OPEN'),
      ADD CONSTRAINT review_issue_events_prior_status_check CHECK(prior_status IS NULL),
      ADD CONSTRAINT review_issue_events_issue_id_key UNIQUE(issue_id);
    """)
    op.execute(_RESTORE_ISSUE)
