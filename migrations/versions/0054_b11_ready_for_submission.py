"""B11 exact immutable manuscript readiness judgment; no publication effect."""

# Literal SQL retains predecessor branches unchanged.
# ruff: noqa: E501
from alembic import op

revision = "0054_b11_ready_for_submission"
down_revision = "0053_b08_issue_disposition"
branch_labels = None
depends_on = None

_TABLES = (
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

_RESTORE_DISPATCH = r"""    CREATE OR REPLACE FUNCTION pr215_basis_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE target_id UUID; target_project UUID; parent_xmin bigint;
      decision_project UUID; target_status TEXT; target_hash TEXT;
    BEGIN
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
    CREATE OR REPLACE FUNCTION pr215_complete_basis() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE did UUID; tid UUID; pid UUID; target_hash TEXT; n INT;
    BEGIN
      IF TG_TABLE_NAME='decision_records' THEN did := NEW.id;
      ELSE did := NEW.decision_id; END IF;
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
"""

_DISPATCH = r"""    CREATE OR REPLACE FUNCTION pr215_basis_guard() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
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
"""

_DDL = r"""
CREATE TABLE decision_basis_manuscripts (
  decision_id UUID NOT NULL,
  manuscript_version_id UUID NOT NULL,
  ordinal INT NOT NULL,
  CONSTRAINT pk_b11_basis_manuscripts PRIMARY KEY(decision_id,manuscript_version_id),
  CONSTRAINT fk_b11_basis_decision FOREIGN KEY(decision_id) REFERENCES decision_records(id) ON DELETE RESTRICT,
  CONSTRAINT fk_b11_basis_manuscript FOREIGN KEY(manuscript_version_id) REFERENCES manuscript_versions(id) ON DELETE RESTRICT,
  CONSTRAINT uq_b11_one_manuscript UNIQUE(decision_id),
  CONSTRAINT uq_b11_manuscript_ordinal UNIQUE(decision_id,ordinal),
  CONSTRAINT ck_b11_manuscript_ordinal CHECK(ordinal>=0));
CREATE INDEX ix_b11_manuscript_target ON decision_basis_manuscripts(manuscript_version_id);
ALTER TABLE decision_records DROP CONSTRAINT ck_b07_decision_tuple;
ALTER TABLE decision_records ADD CONSTRAINT ck_b11_decision_policy CHECK (
 (decision_type='INTERNAL_SCIENTIFIC_RELEASE' AND decision='PROCEED') OR
 (decision_type='REVISION_RESPONSE' AND decision IN ('REQUIRE_CHANGE','ACCEPT_NO_CHANGE')) OR
 (decision_type='READY_FOR_SUBMISSION' AND decision='PROCEED'));
ALTER TABLE decision_records ADD CONSTRAINT ck_b11_text_bounds CHECK (
 decision_type<>'READY_FOR_SUBMISSION' OR
 (length(question) BETWEEN 1 AND 16000 AND length(rationale) BETWEEN 1 AND 16000));
CREATE FUNCTION b11_roots(tid UUID) RETURNS TABLE(kind TEXT,id UUID) LANGUAGE SQL STABLE SET search_path = pg_catalog, public, pg_temp AS $$
 SELECT 'artifact_versions',document_artifact_version_id FROM manuscript_versions WHERE id=tid
 UNION SELECT 'claim_versions',claim_version_id FROM manuscript_claim_placements WHERE manuscript_version_id=tid AND claim_version_id IS NOT NULL
 UNION SELECT 'scientific_conclusion_versions',scientific_conclusion_version_id FROM manuscript_claim_placements WHERE manuscript_version_id=tid AND scientific_conclusion_version_id IS NOT NULL
 UNION SELECT 'source_versions',source_version_id FROM manuscript_citation_placements WHERE manuscript_version_id=tid
 UNION SELECT 'artifact_versions',artifact_version_id FROM manuscript_artifact_placements WHERE manuscript_version_id=tid
$$;
CREATE FUNCTION b11_closure(tid UUID) RETURNS TABLE(kind TEXT,id UUID) LANGUAGE SQL STABLE SET search_path = pg_catalog, public, pg_temp AS $$
 SELECT 'manuscript_versions',tid
 UNION SELECT c.kind,c.id FROM b11_roots(tid) r CROSS JOIN LATERAL b07_closure(r.id,r.kind) c
$$;
CREATE FUNCTION b11_authors(tid UUID) RETURNS SETOF UUID LANGUAGE SQL STABLE SET search_path = pg_catalog, public, pg_temp AS $$
 SELECT created_by FROM manuscript_versions WHERE id=tid
 UNION SELECT p.created_by FROM publications p JOIN manuscript_versions m ON m.publication_id=p.id WHERE m.id=tid
 UNION SELECT created_by FROM manuscript_claim_placements WHERE manuscript_version_id=tid
 UNION SELECT created_by FROM manuscript_citation_placements WHERE manuscript_version_id=tid
 UNION SELECT created_by FROM manuscript_artifact_placements WHERE manuscript_version_id=tid
 UNION SELECT a FROM b11_roots(tid) r CROSS JOIN LATERAL b07_authors(r.id,r.kind) a
$$;
CREATE FUNCTION b11_applicable_reviews(tid UUID,pid UUID) RETURNS SETOF internal_review_records LANGUAGE SQL STABLE SET search_path = pg_catalog, public, pg_temp AS $$
 SELECT r.* FROM internal_review_records r WHERE r.project_id=pid AND EXISTS(
 SELECT 1 FROM b11_closure(tid) c WHERE
 (c.kind='manuscript_versions' AND r.manuscript_version_id=c.id) OR
 (c.kind='claim_versions' AND r.claim_version_id=c.id) OR
 (c.kind='scientific_conclusion_versions' AND r.scientific_conclusion_version_id=c.id) OR
 (c.kind='artifact_versions' AND r.artifact_version_id=c.id)) ORDER BY r.id
$$;
CREATE FUNCTION b11_require_snapshot() RETURNS void LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE name TEXT;
BEGIN
 IF current_setting('transaction_isolation')<>'read committed' THEN
   RAISE EXCEPTION 'read committed protected snapshot required' USING ERRCODE='P17F2'; END IF;
 FOREACH name IN ARRAY ARRAY[INVENTORY] LOOP
   IF NOT EXISTS(SELECT 1 FROM pg_locks WHERE pid=pg_backend_pid() AND locktype='relation'
     AND relation=to_regclass(name) AND granted AND mode IN ('ShareLock','ShareRowExclusiveLock','ExclusiveLock','AccessExclusiveLock')) THEN
     RAISE EXCEPTION 'preheld inventory required' USING ERRCODE='P17F2'; END IF;
 END LOOP;
END $$;
CREATE FUNCTION b11_decision_guard() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
BEGIN
 IF NEW.decision_type='READY_FOR_SUBMISSION' THEN PERFORM b11_require_snapshot(); END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER b11_decision_guard BEFORE INSERT ON decision_records FOR EACH ROW EXECUTE FUNCTION b11_decision_guard();
CREATE FUNCTION b11_check_basis(did UUID,tid UUID) RETURNS void LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
DECLARE m manuscript_versions; d decision_records; pid UUID;
BEGIN
 PERFORM b11_require_snapshot();
 SELECT * INTO m FROM manuscript_versions WHERE id=tid FOR UPDATE;
 SELECT * INTO d FROM decision_records WHERE id=did;
 IF NOT EXISTS(SELECT 1 FROM decision_records WHERE id=did AND xmin::text::bigint=pg_current_xact_id()::text::bigint) THEN
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
END $$;
CREATE FUNCTION b11_manuscript_basis_guard() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
BEGIN
 PERFORM b11_check_basis(NEW.decision_id,NEW.manuscript_version_id);
 RETURN NEW;
END $$;
CREATE TRIGGER b11_manuscript_basis_guard BEFORE INSERT ON decision_basis_manuscripts FOR EACH ROW EXECUTE FUNCTION b11_manuscript_basis_guard();
CREATE TRIGGER b11_manuscript_basis_immutable BEFORE UPDATE OR DELETE ON decision_basis_manuscripts FOR EACH ROW EXECUTE FUNCTION pr215_immutable();
CREATE FUNCTION b11_complete(did UUID) RETURNS void LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
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
CREATE CONSTRAINT TRIGGER b11_complete_manuscript AFTER INSERT ON decision_basis_manuscripts DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pr215_complete_basis();
"""


def upgrade() -> None:
    op.execute(
        "LOCK TABLE decision_basis_claims,decision_basis_conclusions,decision_basis_reviews,decision_records,decision_revision_concerns IN ACCESS EXCLUSIVE MODE"
    )
    op.execute(_DDL.replace("INVENTORY", ",".join("'" + t + "'" for t in _TABLES)))
    op.execute(_DISPATCH)


def downgrade() -> None:
    op.execute("""
    LOCK TABLE decision_basis_claims,decision_basis_conclusions,decision_basis_manuscripts,decision_basis_reviews,decision_records,decision_revision_concerns IN ACCESS EXCLUSIVE MODE;
    DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM decision_records WHERE decision_type='READY_FOR_SUBMISSION') OR EXISTS(SELECT 1 FROM decision_basis_manuscripts) THEN
        RAISE EXCEPTION 'readiness history cannot be discarded' USING ERRCODE='P17F2'; END IF;
    END $$;
    """)
    op.execute(_RESTORE_DISPATCH)
    op.execute("""
    DROP TABLE decision_basis_manuscripts;
    DROP TRIGGER b11_decision_guard ON decision_records;
    DROP FUNCTION b11_decision_guard();
    DROP FUNCTION b11_manuscript_basis_guard();
    DROP FUNCTION b11_complete(UUID);
    DROP FUNCTION b11_check_basis(UUID,UUID);
    DROP FUNCTION b11_require_snapshot();
    DROP FUNCTION b11_applicable_reviews(UUID,UUID);
    DROP FUNCTION b11_authors(UUID);
    DROP FUNCTION b11_closure(UUID);
    DROP FUNCTION b11_roots(UUID);
    ALTER TABLE decision_records DROP CONSTRAINT ck_b11_decision_policy,DROP CONSTRAINT ck_b11_text_bounds;
    ALTER TABLE decision_records ADD CONSTRAINT ck_b07_decision_tuple CHECK (
      (decision_type='INTERNAL_SCIENTIFIC_RELEASE' AND decision='PROCEED') OR
      (decision_type='REVISION_RESPONSE' AND decision IN ('REQUIRE_CHANGE','ACCEPT_NO_CHANGE')));
    """)
