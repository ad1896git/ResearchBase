"""M1-S1 manuscript successors, exact revision evidence and carried blockers.

No new tables/columns. The predecessor bodies are retained verbatim for a safe,
history-refusing downgrade; unrelated release and novelty branches are preserved.
"""

# ruff: noqa: E501
from alembic import op

revision = "0074_m1_manuscript_revision"
down_revision = "0073_b02_strategy_admission"
branch_labels = None
depends_on = None

_UPGRADE = r"""
DO $$ DECLARE bad TEXT; BEGIN
 SELECT string_agg(publication_id::text,', ' ORDER BY publication_id) INTO bad FROM
 (SELECT publication_id FROM manuscript_versions WHERE status='DRAFT' GROUP BY publication_id HAVING count(*)>1) duplicates;
 IF bad IS NOT NULL THEN RAISE EXCEPTION 'M1 preflight: duplicate drafts for publications %. Resolve via architecture review; no rows removed.',bad USING ERRCODE='P17F2'; END IF;
END $$;
ALTER TABLE manuscript_versions ADD CONSTRAINT ck_m1_manuscript_change_class CHECK (
 (version_number=1 AND semantic_change_class='INITIAL') OR
 (version_number>1 AND semantic_change_class IN ('EDITORIAL','SCIENTIFIC_MINOR','SCIENTIFIC_MATERIAL')));
CREATE UNIQUE INDEX uq_m1_one_draft_manuscript ON manuscript_versions(publication_id) WHERE status='DRAFT';
ALTER TABLE revision_actions RENAME CONSTRAINT ck_b23_revision_shape TO ck_m1_revision_action_shape;
CREATE INDEX ix_m1_revision_manuscript ON revision_actions(result_manuscript_version_id) WHERE result_manuscript_version_id IS NOT NULL;
CREATE OR REPLACE FUNCTION public.b04_verify_structure(identity uuid)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
    DECLARE m manuscript_versions; project UUID; pointer UUID; n BIGINT;
    BEGIN
      SELECT * INTO m FROM manuscript_versions WHERE id=identity;
      IF NOT FOUND THEN RETURN; END IF;
      IF m.status='DRAFT' THEN
        IF m.content_hash IS NOT NULL OR m.placement_set_hash IS NOT NULL OR m.frozen_at IS NOT NULL THEN
          RAISE EXCEPTION 'malformed draft seal' USING ERRCODE='P04M3'; END IF;
        RETURN;
      END IF;
      SELECT project_id,current_manuscript_version_id INTO project,pointer FROM publications WHERE id=m.publication_id;
      IF EXISTS(SELECT 1 FROM manuscript_versions WHERE id=m.id AND xmin=pg_current_xact_id()::xid)
        AND pointer IS DISTINCT FROM m.id THEN
        RAISE EXCEPTION 'new seal must advance current pointer atomically' USING ERRCODE='P04M3'; END IF;
      IF m.content_hash IS NULL OR m.placement_set_hash IS NULL OR m.frozen_at IS NULL THEN
        RAISE EXCEPTION 'incomplete manuscript seal' USING ERRCODE='P04M3'; END IF;
      IF NOT EXISTS (SELECT 1 FROM artifact_versions v JOIN artifacts a ON a.id=v.artifact_id
        WHERE v.id=m.document_artifact_version_id AND a.project_id=project AND a.artifact_type='manuscript'
          AND v.status IN ('FROZEN','SUPERSEDED') AND v.frozen_at IS NOT NULL AND v.byte_size IS NOT NULL
          AND v.content_hash ~ '^[0-9a-f]{64}$') THEN
        RAISE EXCEPTION 'manuscript document closure' USING ERRCODE='P04M3'; END IF;
      SELECT count(*) INTO n FROM (
        SELECT section_id,ordinal FROM manuscript_claim_placements WHERE manuscript_version_id=identity
        UNION ALL SELECT section_id,ordinal FROM manuscript_citation_placements WHERE manuscript_version_id=identity
        UNION ALL SELECT section_id,ordinal FROM manuscript_artifact_placements WHERE manuscript_version_id=identity) p;
      IF n>10000 THEN RAISE EXCEPTION 'placement cap exceeded' USING ERRCODE='P04M3'; END IF;
      IF EXISTS (SELECT 1 FROM (
        SELECT 'claim' AS kind,section_id,ordinal FROM manuscript_claim_placements WHERE manuscript_version_id=identity
        UNION ALL SELECT 'citation',section_id,ordinal FROM manuscript_citation_placements WHERE manuscript_version_id=identity
        UNION ALL SELECT 'artifact',section_id,ordinal FROM manuscript_artifact_placements WHERE manuscript_version_id=identity) p
        GROUP BY kind,section_id HAVING min(ordinal)<>0 OR max(ordinal)<>count(*)-1 OR count(DISTINCT ordinal)<>count(*)) THEN
        RAISE EXCEPTION 'placement ordinal gaps' USING ERRCODE='P04M3'; END IF;
      IF EXISTS (SELECT 1 FROM manuscript_claim_placements p
        LEFT JOIN claim_versions v ON v.id=p.claim_version_id LEFT JOIN claims c ON c.id=v.claim_id
        LEFT JOIN scientific_conclusion_versions s ON s.id=p.scientific_conclusion_version_id
        LEFT JOIN scientific_conclusions sc ON sc.id=s.scientific_conclusion_id
        WHERE p.manuscript_version_id=identity AND
          ((p.claim_version_id IS NULL)=(p.scientific_conclusion_version_id IS NULL)
          OR (p.claim_version_id IS NOT NULL AND (c.project_id IS DISTINCT FROM project OR v.status NOT IN ('FROZEN','SUPERSEDED') OR v.frozen_at IS NULL OR v.content_hash IS NULL))
          OR (p.scientific_conclusion_version_id IS NOT NULL AND (sc.project_id IS DISTINCT FROM project OR s.status NOT IN ('FROZEN','SUPERSEDED') OR s.frozen_at IS NULL OR s.content_hash IS NULL OR s.support_set_hash IS NULL)))) THEN
        RAISE EXCEPTION 'scientific placement closure' USING ERRCODE='P04M3'; END IF;
      IF EXISTS (SELECT 1 FROM manuscript_citation_placements p LEFT JOIN source_versions v ON v.id=p.source_version_id
        WHERE p.manuscript_version_id=identity AND (v.status NOT IN ('FROZEN','SUPERSEDED') OR v.frozen_at IS NULL OR v.content_hash IS NULL
          OR NOT EXISTS (SELECT 1 FROM literature_source_project_links l WHERE l.literature_source_id=v.literature_source_id AND l.project_id=project))) THEN
        RAISE EXCEPTION 'citation placement closure' USING ERRCODE='P04M3'; END IF;
      IF EXISTS (SELECT 1 FROM manuscript_artifact_placements p LEFT JOIN artifact_versions v ON v.id=p.artifact_version_id
        LEFT JOIN artifacts a ON a.id=v.artifact_id WHERE p.manuscript_version_id=identity
          AND (a.project_id IS DISTINCT FROM project OR v.status NOT IN ('FROZEN','SUPERSEDED') OR v.frozen_at IS NULL OR v.content_hash IS NULL)) THEN
        RAISE EXCEPTION 'artifact placement closure' USING ERRCODE='P04M3'; END IF;
    END $function$;
CREATE OR REPLACE FUNCTION public.pr212_draft_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
    BEGIN
      IF TG_OP='DELETE' THEN RAISE EXCEPTION 'manuscript history retained' USING ERRCODE='P04M1'; END IF;
      PERFORM id FROM publications WHERE id=NEW.publication_id FOR UPDATE;
      IF NOT EXISTS(SELECT 1 FROM publications WHERE id=NEW.publication_id AND lifecycle_status IN ('DRAFTING','INTERNAL_REVIEW')) THEN
        RAISE EXCEPTION 'manuscript stage ineligible' USING ERRCODE='P04M2'; END IF;
      IF TG_OP='INSERT' AND (NEW.version_number IS DISTINCT FROM
        (SELECT coalesce(max(version_number)::bigint,0)+1 FROM manuscript_versions WHERE publication_id=NEW.publication_id)
        OR (NEW.version_number>1 AND NOT EXISTS(SELECT 1 FROM manuscript_versions m JOIN publications p ON p.id=m.publication_id
          WHERE p.id=NEW.publication_id AND m.id=p.current_manuscript_version_id AND m.status='FROZEN' AND m.version_number=NEW.version_number-1))) THEN
        RAISE EXCEPTION 'contiguous current frozen predecessor required' USING ERRCODE='P04M2'; END IF;
      IF TG_OP='DELETE' THEN
        RAISE EXCEPTION 'manuscript history retained' USING ERRCODE='P04M1';
      END IF;
      IF TG_OP='UPDATE' THEN
        IF OLD.status='FROZEN' THEN RAISE EXCEPTION 'sealed manuscript immutable' USING ERRCODE='P04M1'; END IF;
        IF OLD.status<>'DRAFT' OR NEW.status<>'FROZEN' OR NEW.row_version<>OLD.row_version+1
          OR NEW.content_hash IS NULL OR NEW.placement_set_hash IS NULL OR NEW.frozen_at IS NULL
          OR (to_jsonb(NEW)-ARRAY['status','row_version','content_hash','placement_set_hash','frozen_at'])
            IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['status','row_version','content_hash','placement_set_hash','frozen_at']) THEN
          RAISE EXCEPTION 'invalid manuscript seal transition' USING ERRCODE='P04M2'; END IF;
      ELSIF NEW.status<>'DRAFT' OR NEW.row_version<>1 OR NEW.placement_set_hash IS NOT NULL
        OR NEW.content_hash IS NOT NULL OR NEW.frozen_at IS NOT NULL THEN
        RAISE EXCEPTION 'insert draft only' USING ERRCODE='P04M2';
      END IF;
      PERFORM 1 FROM publications p
        JOIN artifact_versions v ON v.id=NEW.document_artifact_version_id
        JOIN artifacts a ON a.id=v.artifact_id
        WHERE p.id=NEW.publication_id AND a.project_id=p.project_id
          AND a.artifact_type='manuscript' AND v.status='FROZEN'
          AND v.frozen_at IS NOT NULL AND v.content_hash ~ '^[0-9a-f]{64}$'
        FOR SHARE OF p,v,a;
      IF NOT FOUND THEN
        RAISE EXCEPTION 'exact frozen manuscript document required' USING ERRCODE='P17D3';
      END IF;
      RETURN NEW;
    END $function$;
CREATE OR REPLACE FUNCTION public.pr212_publication_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
    DECLARE candidate RECORD; admitted boolean;
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
      IF OLD.lifecycle_status IN ('DRAFTING','INTERNAL_REVIEW') AND NEW.lifecycle_status=OLD.lifecycle_status
        AND NEW.current_manuscript_version_id IS DISTINCT FROM OLD.current_manuscript_version_id
        AND NEW.current_manuscript_version_id IS NOT NULL
        AND NEW.row_version=OLD.row_version+1
        AND (to_jsonb(NEW)-ARRAY['current_manuscript_version_id','row_version'])
          IS NOT DISTINCT FROM (to_jsonb(OLD)-ARRAY['current_manuscript_version_id','row_version'])
        AND EXISTS (SELECT 1 FROM manuscript_versions m WHERE m.id=NEW.current_manuscript_version_id
          AND m.publication_id=NEW.id AND m.status='FROZEN' AND m.content_hash IS NOT NULL
          AND m.placement_set_hash IS NOT NULL AND m.frozen_at IS NOT NULL
          AND m.version_number=coalesce((SELECT version_number FROM manuscript_versions WHERE id=OLD.current_manuscript_version_id),0)+1) THEN RETURN NEW; END IF;
      IF OLD.lifecycle_status='DRAFTING' AND NEW.lifecycle_status='INTERNAL_REVIEW'
        AND OLD.current_manuscript_version_id IS NOT NULL
        AND NEW.row_version::bigint=OLD.row_version::bigint+1
        AND (to_jsonb(NEW)-ARRAY['lifecycle_status','row_version']) IS NOT DISTINCT FROM
            (to_jsonb(OLD)-ARRAY['lifecycle_status','row_version']) THEN
        PERFORM b14a_preheld();
        PERFORM b14a_admission(NEW.current_manuscript_version_id,NEW.project_id);
        RETURN NEW;
      END IF;
      IF OLD.lifecycle_status='INTERNAL_REVIEW' AND NEW.lifecycle_status='READY'
       AND NEW.row_version::bigint=OLD.row_version::bigint+1
       AND (to_jsonb(NEW)-ARRAY['lifecycle_status','row_version']) IS NOT DISTINCT FROM
           (to_jsonb(OLD)-ARRAY['lifecycle_status','row_version']) THEN
        PERFORM b13_preheld(true);
        admitted:=false;
        FOR candidate IN SELECT r AS request,d.decided_by,g.valid_until FROM approval_grants g JOIN approval_decisions d ON d.id=g.approval_decision_id
          JOIN approval_requests r ON r.id=d.approval_request_id WHERE g.status='ACTIVE'
          AND g.purpose='READY_FOR_SUBMISSION' AND g.allowed_command='transition_publication_ready'
          AND g.project_id=NEW.project_id AND r.manuscript_version_id=NEW.current_manuscript_version_id
          AND clock_timestamp()<g.valid_until ORDER BY g.id LOOP
          BEGIN
            PERFORM b14_consumption_gate(candidate.request,candidate.decided_by);
            IF clock_timestamp()<candidate.valid_until AND pr216_approver_active(candidate.decided_by,NEW.project_id) THEN
              admitted:=true; EXIT;
            END IF;
          EXCEPTION WHEN SQLSTATE 'P16T1' OR SQLSTATE 'P16G1' OR SQLSTATE 'P16B1' OR SQLSTATE 'P16A1' OR SQLSTATE 'P16C1' OR SQLSTATE 'P16R1' THEN
            CONTINUE;
          END;
        END LOOP;
        IF NOT admitted THEN RAISE EXCEPTION 'valid ACTIVE readiness permission required' USING ERRCODE='P16G1'; END IF;
        RETURN NEW;
      END IF;
      RAISE EXCEPTION 'invalid manuscript pointer transition' USING ERRCODE='P04M2';
    END $function$;
CREATE OR REPLACE FUNCTION public.b14a_verify_entry(pid uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
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
 IF p.lifecycle_status NOT IN ('INTERNAL_REVIEW','READY') OR e.id IS NULL OR e.prior_status IS DISTINCT FROM 'DRAFTING'
 OR m.id IS NULL OR m.publication_id IS DISTINCT FROM pid OR m.status<>'FROZEN' OR m.frozen_at IS NULL
 OR NOT EXISTS(SELECT 1 FROM manuscript_versions current WHERE current.id=p.current_manuscript_version_id AND current.publication_id=pid AND current.status='FROZEN' AND current.version_number>=m.version_number)
 OR e.occurred_at<m.frozen_at OR e.occurred_at<p.created_at OR e.occurred_at>clock_timestamp()
 OR e.basis_decision_id IS NOT NULL OR e.basis_grant_consumption_id IS NOT NULL THEN
 RAISE EXCEPTION 'complete exact entry graph required' USING ERRCODE='P14P1'; END IF;
 PERFORM b04_verify_structure(m.id);
 IF p.lifecycle_status='INTERNAL_REVIEW' AND EXISTS(SELECT 1 FROM publication_lifecycle_events WHERE id=e.id AND xmin=pg_current_xact_id()::xid) THEN
  IF NOT EXISTS(SELECT 1 FROM publications WHERE id=pid AND xmin=pg_current_xact_id()::xid) THEN
   RAISE EXCEPTION 'same transaction transition required' USING ERRCODE='P14I1'; END IF;
  PERFORM b14a_preheld(); PERFORM b14a_admission(m.id,p.project_id);
  IF NOT b13_authorized(e.actor_id,p.project_id,ARRAY['OWNER','RESEARCHER']) OR NOT EXISTS(SELECT 1 FROM projects WHERE id=p.project_id AND lifecycle_status='ACTIVE') THEN
   RAISE EXCEPTION 'final entry authority unavailable' USING ERRCODE='P14A1'; END IF;

 END IF;
END $function$;
CREATE OR REPLACE FUNCTION public.b05_verify_review_structure(identity uuid)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE target UUID; r internal_review_records; n BIGINT;
BEGIN
  SELECT manuscript_version_id INTO target FROM internal_review_records WHERE id=identity;
  IF target IS NULL THEN RETURN; END IF;
  SELECT * INTO r FROM internal_review_records WHERE id=identity;
  IF r.manuscript_version_id IS DISTINCT FROM target OR NOT EXISTS (
    SELECT 1 FROM manuscript_versions m JOIN publications p ON p.id=m.publication_id
    WHERE m.id=target AND p.project_id=r.project_id AND m.status IN ('FROZEN','SUPERSEDED')
      AND m.frozen_at IS NOT NULL AND m.placement_set_hash IS NOT NULL
      AND m.content_hash=r.target_content_hash) THEN
    RAISE EXCEPTION 'B05 malformed target for review %',identity USING ERRCODE='P05R1';
  END IF;
  SELECT count(*) INTO n FROM review_issues WHERE review_record_id=identity;
  IF n>0 AND EXISTS (SELECT 1 FROM review_issues WHERE review_record_id=identity
      GROUP BY review_record_id HAVING min(ordinal)<>0 OR max(ordinal)<>n-1
        OR count(DISTINCT ordinal)<>n) THEN
    RAISE EXCEPTION 'B05 issue ordinal gap for review %',identity USING ERRCODE='P05R1';
  END IF;
  IF EXISTS (SELECT 1 FROM review_issues i WHERE i.review_record_id=identity AND
    ((SELECT count(*) FROM review_issue_events e WHERE e.issue_id=i.id)<>CASE WHEN i.status='OPEN' THEN 1 ELSE 2 END
      OR (i.status<>'OPEN' AND NOT EXISTS(SELECT 1 FROM review_issue_events e WHERE e.issue_id=i.id AND e.prior_status='OPEN' AND e.new_status=i.status))
      OR NOT EXISTS (SELECT 1 FROM review_issue_events e WHERE e.issue_id=i.id
        AND e.prior_status IS NULL AND e.new_status='OPEN'
        AND e.actor_id=r.reviewer_actor_id AND e.occurred_at=i.created_at))) THEN
    RAISE EXCEPTION 'B05 malformed OPEN history for review %',identity USING ERRCODE='P05R1';
  END IF;
END $function$;
CREATE FUNCTION m1_manuscript(tid UUID,pid UUID) RETURNS void LANGUAGE plpgsql SET search_path TO pg_catalog, public, pg_temp AS $$
DECLARE m manuscript_versions; cp JSONB; ap JSONB; sp JSONB; ph TEXT; root RECORD;
BEGIN
 SELECT v.* INTO m FROM manuscript_versions v JOIN publications p ON p.id=v.publication_id WHERE v.id=tid AND p.project_id=pid;
 IF m.id IS NULL OR m.status<>'FROZEN' THEN RAISE EXCEPTION 'frozen manuscript required' USING ERRCODE='P17F2'; END IF;
 PERFORM b04_verify_structure(tid);
 SELECT coalesce(jsonb_agg(jsonb_build_object('target',pr216_ref(CASE WHEN p.claim_version_id IS NOT NULL THEN 'ClaimVersion' ELSE 'ScientificConclusionVersion' END,coalesce(p.claim_version_id,p.scientific_conclusion_version_id),coalesce(c.content_hash,s.content_hash)),
 'section_id',p.section_id,'locator',p.locator,'rhetorical_strength',p.rhetorical_strength,'ordinal',p.ordinal) ORDER BY p.section_id COLLATE "C",p.ordinal),'[]'::jsonb) INTO cp
 FROM manuscript_claim_placements p LEFT JOIN claim_versions c ON c.id=p.claim_version_id LEFT JOIN scientific_conclusion_versions s ON s.id=p.scientific_conclusion_version_id WHERE p.manuscript_version_id=tid;
 SELECT coalesce(jsonb_agg(jsonb_build_object('source_version',pr216_ref('SourceVersion',s.id,s.content_hash),'section_id',p.section_id,'locator',p.locator,'citation_purpose',p.citation_purpose,'ordinal',p.ordinal) ORDER BY p.section_id COLLATE "C",p.ordinal),'[]'::jsonb) INTO sp
 FROM manuscript_citation_placements p JOIN source_versions s ON s.id=p.source_version_id WHERE p.manuscript_version_id=tid;
 SELECT coalesce(jsonb_agg(jsonb_build_object('artifact_version',pr216_ref('ArtifactVersion',v.id,v.content_hash),'section_id',p.section_id,'locator',p.locator,'artifact_role',p.artifact_role,'ordinal',p.ordinal) ORDER BY p.section_id COLLATE "C",p.ordinal),'[]'::jsonb) INTO ap
 FROM manuscript_artifact_placements p JOIN artifact_versions v ON v.id=p.artifact_version_id WHERE p.manuscript_version_id=tid;
 ph:=pr216_hash(jsonb_build_object('type','ManuscriptVersionPlacementSet','material_version',1,'claim_placements',cp,'citation_placements',sp,'artifact_placements',ap));
 IF m.placement_set_hash IS DISTINCT FROM ph OR m.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','ManuscriptVersion','material_version',1,'publication_id',m.publication_id,
 'document_artifact',pr216_ref('ArtifactVersion',m.document_artifact_version_id,(SELECT content_hash FROM artifact_versions WHERE id=m.document_artifact_version_id)),
 'title',m.title,'abstract',m.abstract,'semantic_change_class',m.semantic_change_class,'placement_set_hash',ph)) THEN
 RAISE EXCEPTION 'manuscript seal mismatch' USING ERRCODE='P17F2'; END IF;
 FOR root IN SELECT * FROM b11_roots(tid) LOOP
 IF root.kind IN ('claim_versions','scientific_conclusion_versions') THEN PERFORM b07_target(root.id,pid,root.kind);
 ELSE PERFORM b07_facts(root.id,pid,root.kind); END IF;
 END LOOP;
END $$;
CREATE OR REPLACE FUNCTION public.b07_closure(target_id uuid, seed_kind text)
 RETURNS TABLE(kind text, id uuid)
 LANGUAGE sql
 STABLE
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
WITH RECURSIVE edges AS (SELECT 'manuscript_versions'::text AS kind,m.id,r.kind AS child_kind,r.id AS child_id
 FROM manuscript_versions m CROSS JOIN LATERAL b11_roots(m.id) r
 UNION ALL SELECT
    'scientific_conclusion_versions'::text AS kind,
    id,'scientific_conclusions'::text AS child_kind,
    scientific_conclusion_id AS child_id
    FROM scientific_conclusion_versions
 UNION ALL SELECT 'claim_versions'::text
      AS kind, id,'claims'::text
      AS child_kind, claim_id AS child_id
      FROM claim_versions
 UNION ALL SELECT 'source_versions'::text
      AS kind, id,'literature_sources'::text
      AS child_kind, literature_source_id AS child_id
      FROM source_versions
 UNION ALL SELECT 'artifact_versions'::text
      AS kind, id,'artifacts'::text
      AS child_kind, artifact_id AS child_id
      FROM artifact_versions
 UNION ALL SELECT 'dataset_snapshots'::text
      AS kind, id,'datasets'::text
      AS child_kind, dataset_id AS child_id
      FROM dataset_snapshots
 UNION ALL SELECT 'metric_definition_versions'::text
      AS kind, id,'metric_definitions'::text
      AS child_kind, metric_definition_id AS child_id
      FROM metric_definition_versions
 UNION ALL SELECT 'experiment_spec_versions'::text
      AS kind, id,'experiment_specs'::text
      AS child_kind, experiment_spec_id AS child_id
      FROM experiment_spec_versions
 UNION ALL SELECT
    'scientific_conclusion_versions',
    conclusion_version_id,'claim_versions',
    claim_version_id
      FROM scientific_conclusion_claim_inputs
      WHERE claim_version_id IS NOT NULL
 UNION ALL SELECT
    'scientific_conclusion_versions',
    conclusion_version_id,'literature_support_snapshots',
    literature_support_snapshot_id
      FROM scientific_conclusion_claim_inputs
      WHERE literature_support_snapshot_id IS NOT NULL
 UNION ALL SELECT
    'scientific_conclusion_versions',
    conclusion_version_id,'literature_evidence',literature_evidence_id
      FROM scientific_conclusion_literature_inputs
      WHERE literature_evidence_id IS NOT NULL
 UNION ALL SELECT 'claim_versions',claim_version_id,'measurements',measurement_id
      FROM evidence_relations
      WHERE measurement_id IS NOT NULL
 UNION ALL SELECT 'claim_versions',claim_version_id,'statistical_results',statistical_result_id
      FROM evidence_relations
      WHERE statistical_result_id IS NOT NULL
 UNION ALL SELECT 'statistical_results',statistical_result_id,'measurements',measurement_id
      FROM statistical_result_inputs
      WHERE measurement_id IS NOT NULL
 UNION ALL SELECT 'runs',run_id,'artifact_versions',artifact_version_id
      FROM run_artifact_inputs
      WHERE artifact_version_id IS NOT NULL
 UNION ALL SELECT 'runs',run_id,'dataset_snapshots',dataset_snapshot_id
      FROM run_dataset_inputs
      WHERE dataset_snapshot_id IS NOT NULL
 UNION ALL SELECT
    'literature_support_snapshots',
    literature_support_snapshot_id,'literature_evidence',literature_evidence_id
      FROM literature_evidence_relations
      WHERE literature_evidence_id IS NOT NULL
 UNION ALL SELECT 'measurements',id,'runs',run_id FROM measurements WHERE run_id IS NOT NULL
 UNION ALL SELECT 'measurements',id,'metric_definition_versions',metric_definition_version_id
      FROM measurements
      WHERE metric_definition_version_id IS NOT NULL
 UNION ALL SELECT 'runs',id,'experiment_spec_versions',experiment_spec_version_id
      FROM runs
      WHERE experiment_spec_version_id IS NOT NULL
 UNION ALL SELECT 'literature_evidence',id,'source_versions',source_version_id
      FROM literature_evidence
      WHERE source_version_id IS NOT NULL
 UNION ALL SELECT 'literature_support_snapshots',id,'claim_versions',claim_version_id
      FROM literature_support_snapshots
      WHERE claim_version_id IS NOT NULL
 UNION ALL SELECT
    'literature_support_snapshots',
    id,'literature_support_snapshots',
    previous_snapshot_id
      FROM literature_support_snapshots
      WHERE previous_snapshot_id IS NOT NULL
 UNION ALL SELECT 'source_versions',id,'artifact_versions',fulltext_artifact_version_id
      FROM source_versions
      WHERE fulltext_artifact_version_id IS NOT NULL
 UNION ALL SELECT 'source_versions',id,'source_versions',predecessor_source_version_id
      FROM source_versions
      WHERE predecessor_source_version_id IS NOT NULL
 UNION ALL SELECT 'source_versions',id,'artifact_versions',correction_basis_artifact_version_id
      FROM source_versions
      WHERE correction_basis_artifact_version_id IS NOT NULL),
          closure(kind,id) AS (SELECT seed_kind,target_id
            UNION SELECT e.child_kind,e.child_id FROM closure c JOIN edges e
              ON e.kind=c.kind AND e.id=c.id) SELECT kind,id FROM closure
$function$;
CREATE OR REPLACE FUNCTION public.b07_authors(target_id uuid, seed_kind text)
 RETURNS SETOF uuid
 LANGUAGE sql
 STABLE
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
WITH RECURSIVE edges AS (SELECT 'manuscript_versions'::text AS kind,m.id,r.kind AS child_kind,r.id AS child_id
 FROM manuscript_versions m CROSS JOIN LATERAL b11_roots(m.id) r
 UNION ALL SELECT
    'scientific_conclusion_versions'::text AS kind,
    id,'scientific_conclusions'::text AS child_kind,
    scientific_conclusion_id AS child_id
    FROM scientific_conclusion_versions
 UNION ALL SELECT 'claim_versions'::text
      AS kind, id,'claims'::text
      AS child_kind, claim_id AS child_id
      FROM claim_versions
 UNION ALL SELECT 'source_versions'::text
      AS kind, id,'literature_sources'::text
      AS child_kind, literature_source_id AS child_id
      FROM source_versions
 UNION ALL SELECT 'artifact_versions'::text
      AS kind, id,'artifacts'::text
      AS child_kind, artifact_id AS child_id
      FROM artifact_versions
 UNION ALL SELECT 'dataset_snapshots'::text
      AS kind, id,'datasets'::text
      AS child_kind, dataset_id AS child_id
      FROM dataset_snapshots
 UNION ALL SELECT 'metric_definition_versions'::text
      AS kind, id,'metric_definitions'::text
      AS child_kind, metric_definition_id AS child_id
      FROM metric_definition_versions
 UNION ALL SELECT 'experiment_spec_versions'::text
      AS kind, id,'experiment_specs'::text
      AS child_kind, experiment_spec_id AS child_id
      FROM experiment_spec_versions
 UNION ALL SELECT
    'scientific_conclusion_versions',
    conclusion_version_id,'claim_versions',
    claim_version_id
      FROM scientific_conclusion_claim_inputs
      WHERE claim_version_id IS NOT NULL
 UNION ALL SELECT
    'scientific_conclusion_versions',
    conclusion_version_id,'literature_support_snapshots',
    literature_support_snapshot_id
      FROM scientific_conclusion_claim_inputs
      WHERE literature_support_snapshot_id IS NOT NULL
 UNION ALL SELECT
    'scientific_conclusion_versions',
    conclusion_version_id,'literature_evidence',literature_evidence_id
      FROM scientific_conclusion_literature_inputs
      WHERE literature_evidence_id IS NOT NULL
 UNION ALL SELECT 'claim_versions',claim_version_id,'measurements',measurement_id
      FROM evidence_relations
      WHERE measurement_id IS NOT NULL
 UNION ALL SELECT 'claim_versions',claim_version_id,'statistical_results',statistical_result_id
      FROM evidence_relations
      WHERE statistical_result_id IS NOT NULL
 UNION ALL SELECT 'statistical_results',statistical_result_id,'measurements',measurement_id
      FROM statistical_result_inputs
      WHERE measurement_id IS NOT NULL
 UNION ALL SELECT 'runs',run_id,'artifact_versions',artifact_version_id
      FROM run_artifact_inputs
      WHERE artifact_version_id IS NOT NULL
 UNION ALL SELECT 'runs',run_id,'dataset_snapshots',dataset_snapshot_id
      FROM run_dataset_inputs
      WHERE dataset_snapshot_id IS NOT NULL
 UNION ALL SELECT
    'literature_support_snapshots',
    literature_support_snapshot_id,'literature_evidence',literature_evidence_id
      FROM literature_evidence_relations
      WHERE literature_evidence_id IS NOT NULL
 UNION ALL SELECT 'measurements',id,'runs',run_id FROM measurements WHERE run_id IS NOT NULL
 UNION ALL SELECT 'measurements',id,'metric_definition_versions',metric_definition_version_id
      FROM measurements
      WHERE metric_definition_version_id IS NOT NULL
 UNION ALL SELECT 'runs',id,'experiment_spec_versions',experiment_spec_version_id
      FROM runs
      WHERE experiment_spec_version_id IS NOT NULL
 UNION ALL SELECT 'literature_evidence',id,'source_versions',source_version_id
      FROM literature_evidence
      WHERE source_version_id IS NOT NULL
 UNION ALL SELECT 'literature_support_snapshots',id,'claim_versions',claim_version_id
      FROM literature_support_snapshots
      WHERE claim_version_id IS NOT NULL
 UNION ALL SELECT
    'literature_support_snapshots',
    id,'literature_support_snapshots',
    previous_snapshot_id
      FROM literature_support_snapshots
      WHERE previous_snapshot_id IS NOT NULL
 UNION ALL SELECT 'source_versions',id,'artifact_versions',fulltext_artifact_version_id
      FROM source_versions
      WHERE fulltext_artifact_version_id IS NOT NULL
 UNION ALL SELECT 'source_versions',id,'source_versions',predecessor_source_version_id
      FROM source_versions
      WHERE predecessor_source_version_id IS NOT NULL
 UNION ALL SELECT 'source_versions',id,'artifact_versions',correction_basis_artifact_version_id
      FROM source_versions
      WHERE correction_basis_artifact_version_id IS NOT NULL),
          closure(kind,id) AS (SELECT seed_kind,target_id
            UNION SELECT e.child_kind,e.child_id FROM closure c JOIN edges e
              ON e.kind=c.kind AND e.id=c.id), authors AS (SELECT 'manuscript_versions'::text AS kind,id,created_by FROM manuscript_versions
 UNION SELECT 'manuscript_versions',m.id,p.created_by FROM manuscript_versions m JOIN publications p ON p.id=m.publication_id
 UNION SELECT 'manuscript_versions',manuscript_version_id,created_by FROM manuscript_claim_placements
 UNION SELECT 'manuscript_versions',manuscript_version_id,created_by FROM manuscript_citation_placements
 UNION SELECT 'manuscript_versions',manuscript_version_id,created_by FROM manuscript_artifact_placements
 UNION SELECT
    'artifact_versions'::text AS kind,
    id,created_by
    FROM artifact_versions
 UNION ALL SELECT 'artifacts'::text AS kind,id,created_by FROM artifacts
 UNION ALL SELECT 'claim_versions'::text AS kind,id,created_by FROM claim_versions
 UNION ALL SELECT 'claims'::text AS kind,id,created_by FROM claims
 UNION ALL SELECT 'dataset_snapshots'::text AS kind,id,created_by FROM dataset_snapshots
 UNION ALL SELECT 'datasets'::text AS kind,id,created_by FROM datasets
 UNION ALL SELECT 'experiment_spec_versions'::text
      AS kind, id,created_by
      FROM experiment_spec_versions
 UNION ALL SELECT 'experiment_specs'::text AS kind,id,created_by FROM experiment_specs
 UNION ALL SELECT 'literature_evidence'::text AS kind,id,created_by FROM literature_evidence
 UNION ALL SELECT 'literature_sources'::text AS kind,id,created_by FROM literature_sources
 UNION ALL SELECT 'literature_support_snapshots'::text
      AS kind, id,created_by
      FROM literature_support_snapshots
 UNION ALL SELECT 'measurements'::text AS kind,id,created_by FROM measurements
 UNION ALL SELECT 'metric_definition_versions'::text
      AS kind, id,created_by
      FROM metric_definition_versions
 UNION ALL SELECT 'metric_definitions'::text AS kind,id,created_by FROM metric_definitions
 UNION ALL SELECT 'runs'::text AS kind,id,created_by FROM runs
 UNION ALL SELECT 'scientific_conclusion_versions'::text
      AS kind, id,created_by
      FROM scientific_conclusion_versions
 UNION ALL SELECT 'scientific_conclusions'::text AS kind,id,created_by FROM scientific_conclusions
 UNION ALL SELECT 'source_versions'::text AS kind,id,created_by FROM source_versions
 UNION ALL SELECT 'statistical_results'::text AS kind,id,created_by FROM statistical_results
 UNION ALL SELECT 'claim_versions',claim_version_id,created_by FROM evidence_relations
 UNION ALL SELECT 'literature_support_snapshots',literature_support_snapshot_id,created_by
      FROM literature_evidence_relations )
          SELECT DISTINCT a.created_by FROM authors a JOIN closure c
            ON c.kind=a.kind AND c.id=a.id
$function$;
CREATE OR REPLACE FUNCTION public.b07_target(tid uuid, pid uuid, seed_kind text)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE cv claim_versions; v scientific_conclusion_versions; support TEXT; cs JSONB; ls JSONB;
BEGIN
  IF seed_kind='manuscript_versions' THEN PERFORM m1_manuscript(tid,pid); RETURN; END IF;
  IF seed_kind NOT IN ('claim_versions','scientific_conclusion_versions') THEN
    RAISE EXCEPTION 'typed scientific target required' USING ERRCODE='P17F2'; END IF;
  PERFORM b07_facts(tid,pid,seed_kind);
  SELECT * INTO v FROM scientific_conclusion_versions WHERE id=tid AND seed_kind='scientific_conclusion_versions';
  IF v.id IS NOT NULL THEN
    IF v.status NOT IN ('FROZEN','SUPERSEDED') OR v.frozen_at IS NULL
      OR NOT EXISTS(SELECT 1 FROM scientific_conclusions WHERE id=v.scientific_conclusion_id AND project_id=pid) THEN
      RAISE EXCEPTION 'frozen same-project target required' USING ERRCODE='P17F2';
    END IF;
    SELECT coalesce(jsonb_agg(jsonb_build_object('claim_version',pr216_ref('ClaimVersion',c.id,c.content_hash),
      'literature_support_snapshot',pr216_ref('LiteratureSupportSnapshot',s.id,s.content_hash),
      'relation_type',b.relation_type,'ordinal',b.ordinal) ORDER BY b.ordinal),'[]'::jsonb) INTO cs
      FROM scientific_conclusion_claim_inputs b JOIN claim_versions c ON c.id=b.claim_version_id
      LEFT JOIN literature_support_snapshots s ON s.id=b.literature_support_snapshot_id WHERE b.conclusion_version_id=v.id;
    SELECT coalesce(jsonb_agg(jsonb_build_object('literature_evidence',pr216_ref('LiteratureEvidence',e.id,e.content_hash),
      'relation_type',b.relation_type,'ordinal',b.ordinal) ORDER BY b.ordinal),'[]'::jsonb) INTO ls
      FROM scientific_conclusion_literature_inputs b JOIN literature_evidence e ON e.id=b.literature_evidence_id
      WHERE b.conclusion_version_id=v.id;
    support:=pr216_hash(jsonb_build_object('type','ScientificConclusionVersionSupportSet','material_version',1,'claim_inputs',cs,'literature_inputs',ls));
    IF support IS DISTINCT FROM v.support_set_hash OR v.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object(
      'type','ScientificConclusionVersion','material_version',1,'scientific_conclusion_id',v.scientific_conclusion_id,
      'statement',v.statement,'scope',v.scope,'confidence',v.confidence,'limitation_summary',v.limitation_summary,'support_set_hash',support)) THEN
      RAISE EXCEPTION 'target hash invalid' USING ERRCODE='P17F2';
    END IF;
  END IF;
  FOR cv IN SELECT c.* FROM b07_closure(tid,seed_kind) x JOIN claim_versions c ON c.id=x.id WHERE x.kind='claim_versions' LOOP
    IF cv.status NOT IN ('FROZEN','SUPERSEDED') OR cv.frozen_at IS NULL
      OR NOT EXISTS(SELECT 1 FROM claims WHERE id=cv.claim_id AND project_id=pid)
      OR cv.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('statement',cv.statement,'scope',cv.scope,
        'qualification',cv.qualification,'support_set_hash',cv.support_set_hash))
      OR cv.support_set_hash IS DISTINCT FROM (SELECT pr216_hash(coalesce(jsonb_agg(jsonb_build_object(
        'source_type',CASE WHEN e.measurement_id IS NULL THEN 'statistical_result' ELSE 'measurement' END,
        'source_id',coalesce(e.measurement_id,e.statistical_result_id),'relation_type',lower(e.relation_type),
        'qualification',e.qualification) ORDER BY CASE WHEN e.measurement_id IS NULL THEN 'statistical_result' ELSE 'measurement' END,
        coalesce(e.measurement_id,e.statistical_result_id),lower(e.relation_type),e.qualification IS NOT NULL,coalesce(e.qualification,'')),'[]'::jsonb))
        FROM evidence_relations e WHERE e.claim_version_id=cv.id) THEN
      RAISE EXCEPTION 'claim material invalid' USING ERRCODE='P17F2';
    END IF;
  END LOOP;
  IF v.id IS NULL AND (seed_kind<>'claim_versions' OR NOT EXISTS(SELECT 1 FROM claim_versions WHERE id=tid)) THEN
    RAISE EXCEPTION 'exact scientific target required' USING ERRCODE='P17F2';
  END IF;
END $function$;
CREATE OR REPLACE FUNCTION public.b07_review(r internal_review_records)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE tid UUID; kind TEXT; digest TEXT;
BEGIN
  tid:=coalesce(r.claim_version_id,r.scientific_conclusion_version_id,r.manuscript_version_id);
  kind:=CASE WHEN r.claim_version_id IS NOT NULL THEN 'ClaimVersion' WHEN r.manuscript_version_id IS NOT NULL THEN 'ManuscriptVersion' ELSE 'ScientificConclusionVersion' END;
  PERFORM b07_target(tid,r.project_id,CASE WHEN r.claim_version_id IS NOT NULL THEN 'claim_versions' WHEN r.manuscript_version_id IS NOT NULL THEN 'manuscript_versions' ELSE 'scientific_conclusion_versions' END);
  IF r.claim_version_id IS NOT NULL THEN SELECT content_hash INTO digest FROM claim_versions WHERE id=tid;
  ELSIF r.manuscript_version_id IS NOT NULL THEN SELECT content_hash INTO digest FROM manuscript_versions WHERE id=tid;
  ELSE SELECT content_hash INTO digest FROM scientific_conclusion_versions WHERE id=tid; END IF;
  IF r.created_at>clock_timestamp() OR r.target_content_hash IS DISTINCT FROM digest OR r.hash_scheme<>'sha256-cjson-v1'
    OR r.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','InternalReviewRecord','material_version',1,
      'project_id',r.project_id,'target',pr216_ref(kind,tid,digest),'reviewer_actor_id',r.reviewer_actor_id,
      'review_type',r.review_type,'recommendation',r.recommendation,'summary',r.summary))
    OR r.reviewer_actor_id IN (SELECT b07_authors(tid,CASE WHEN kind='ClaimVersion' THEN 'claim_versions' WHEN kind='ManuscriptVersion' THEN 'manuscript_versions' ELSE 'scientific_conclusion_versions' END)) OR NOT EXISTS(
      SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id
      JOIN project_role_assignments role ON role.membership_id=m.id AND role.actor_id=m.actor_id AND role.project_id=m.project_id
      WHERE a.id=r.reviewer_actor_id AND a.actor_type='HUMAN' AND a.created_at<=r.created_at
        AND (a.retired_at IS NULL OR r.created_at<a.retired_at) AND m.project_id=r.project_id AND m.started_at<=r.created_at
        AND role.role IN ('OWNER','REVIEWER') AND role.effective_from<=r.created_at AND (role.effective_until IS NULL OR r.created_at<role.effective_until)
        AND (SELECT e.new_status FROM project_membership_events e WHERE e.membership_id=m.id AND e.occurred_at<=r.created_at
          ORDER BY e.occurred_at DESC,e.id DESC LIMIT 1)='ACTIVE'
        AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=a.id AND b.bound_at<=r.created_at AND (b.revoked_at IS NULL OR r.created_at<b.revoked_at))) THEN
    RAISE EXCEPTION 'review material or authority invalid' USING ERRCODE='P17F2';
  END IF;
END $function$;
CREATE OR REPLACE FUNCTION public.b07_validate_decision(did uuid, complete_snapshot boolean)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE d decision_records; i review_issues; r internal_review_records; ref internal_review_records; tid UUID; digest TEXT; kind TEXT; basis JSONB; n INT; ordinals_valid BOOLEAN;
BEGIN
  SELECT * INTO d FROM decision_records WHERE id=did;
  SELECT x.* INTO i FROM decision_revision_concerns b JOIN review_issues x ON x.id=b.review_issue_id WHERE b.decision_id=did;
  SELECT * INTO r FROM internal_review_records WHERE id=i.review_record_id;
  IF d.id IS NULL OR d.decision_type<>'REVISION_RESPONSE' OR i.id IS NULL OR r.id IS NULL OR d.project_id<>r.project_id
    OR d.decided_at>clock_timestamp() OR d.supersedes_decision_id IS NOT NULL OR NOT pr216_decision_authorized(d) THEN
    RAISE EXCEPTION 'exact revision concern and authority required' USING ERRCODE='P17F2';
  END IF;
  IF complete_snapshot THEN PERFORM b07_lock_concern(i.id); END IF;
  tid:=coalesce(r.claim_version_id,r.scientific_conclusion_version_id,r.manuscript_version_id);
  kind:=CASE WHEN r.claim_version_id IS NOT NULL THEN 'ClaimVersion' WHEN r.manuscript_version_id IS NOT NULL THEN 'ManuscriptVersion' ELSE 'ScientificConclusionVersion' END;
  IF r.claim_version_id IS NOT NULL THEN SELECT content_hash INTO digest FROM claim_versions WHERE id=tid;
  ELSIF r.manuscript_version_id IS NOT NULL THEN SELECT content_hash INTO digest FROM manuscript_versions WHERE id=tid;
  ELSE SELECT content_hash INTO digest FROM scientific_conclusion_versions WHERE id=tid; END IF;
  PERFORM b07_target(tid,d.project_id,CASE WHEN kind='ClaimVersion' THEN 'claim_versions' WHEN kind='ManuscriptVersion' THEN 'manuscript_versions' ELSE 'scientific_conclusion_versions' END);
  IF d.decided_by IN (SELECT b07_authors(tid,CASE WHEN kind='ClaimVersion' THEN 'claim_versions' WHEN kind='ManuscriptVersion' THEN 'manuscript_versions' ELSE 'scientific_conclusion_versions' END)) OR length(d.question)>16000 OR length(d.rationale)>16000
    OR d.question<>normalize(d.question,NFC) OR d.rationale<>normalize(d.rationale,NFC)
    OR (SELECT count(*) FROM decision_basis_claims WHERE decision_id=did)+
       (SELECT count(*) FROM decision_basis_conclusions WHERE decision_id=did)+(SELECT count(*) FROM decision_basis_manuscripts WHERE decision_id=did)<>1
    OR (kind='ClaimVersion' AND NOT EXISTS(SELECT 1 FROM decision_basis_claims WHERE decision_id=did AND claim_version_id=tid))
    OR (kind='ScientificConclusionVersion' AND NOT EXISTS(SELECT 1 FROM decision_basis_conclusions WHERE decision_id=did AND scientific_conclusion_version_id=tid))
    OR (kind='ManuscriptVersion' AND NOT EXISTS(SELECT 1 FROM decision_basis_manuscripts WHERE decision_id=did AND manuscript_version_id=tid))
    OR NOT EXISTS(SELECT 1 FROM decision_basis_reviews WHERE decision_id=did AND internal_review_record_id=r.id) THEN
    RAISE EXCEPTION 'exact revision target basis required' USING ERRCODE='P17F2';
  END IF;
  IF complete_snapshot AND EXISTS(SELECT 1 FROM internal_review_records x WHERE x.project_id=d.project_id
    AND x.claim_version_id IS NOT DISTINCT FROM r.claim_version_id
    AND x.scientific_conclusion_version_id IS NOT DISTINCT FROM r.scientific_conclusion_version_id
    AND x.manuscript_version_id IS NOT DISTINCT FROM r.manuscript_version_id
    AND NOT EXISTS(SELECT 1 FROM decision_basis_reviews b WHERE b.decision_id=did AND b.internal_review_record_id=x.id)) THEN
    RAISE EXCEPTION 'complete matching review snapshot required' USING ERRCODE='P17F2';
  END IF;
  FOR ref IN SELECT x.* FROM decision_basis_reviews b JOIN internal_review_records x ON x.id=b.internal_review_record_id WHERE b.decision_id=did ORDER BY x.id LOOP
    IF (complete_snapshot AND EXISTS(SELECT 1 FROM internal_review_records WHERE id=ref.id AND xmin=pg_current_xact_id()::xid))
      OR ref.created_at>d.decided_at OR ref.project_id<>d.project_id OR ref.claim_version_id IS DISTINCT FROM r.claim_version_id
      OR ref.scientific_conclusion_version_id IS DISTINCT FROM r.scientific_conclusion_version_id
      OR ref.manuscript_version_id IS DISTINCT FROM r.manuscript_version_id
      OR ref.target_content_hash IS DISTINCT FROM digest THEN
      RAISE EXCEPTION 'exact review binding required' USING ERRCODE='P17F2';
    END IF;
    PERFORM b07_review(ref);
  END LOOP;
  SELECT jsonb_agg(jsonb_build_object('target',pr216_ref(k,id,h),'ordinal',expected) ORDER BY k,id,h),count(*),bool_and(ordinal=expected) INTO basis,n,ordinals_valid FROM (SELECT refs.*,row_number() OVER(ORDER BY k,id,h)-1 AS expected FROM (
    SELECT 'ClaimVersion' AS k,b.claim_version_id AS id,v.content_hash AS h,b.ordinal FROM decision_basis_claims b JOIN claim_versions v ON v.id=b.claim_version_id WHERE b.decision_id=did
    UNION ALL SELECT 'ScientificConclusionVersion',b.scientific_conclusion_version_id,v.content_hash,b.ordinal FROM decision_basis_conclusions b JOIN scientific_conclusion_versions v ON v.id=b.scientific_conclusion_version_id WHERE b.decision_id=did
    UNION ALL SELECT 'ManuscriptVersion',b.manuscript_version_id,v.content_hash,b.ordinal FROM decision_basis_manuscripts b JOIN manuscript_versions v ON v.id=b.manuscript_version_id WHERE b.decision_id=did
    UNION ALL SELECT 'InternalReviewRecord',b.internal_review_record_id,v.content_hash,b.ordinal FROM decision_basis_reviews b JOIN internal_review_records v ON v.id=b.internal_review_record_id WHERE b.decision_id=did) refs) canonical_refs;
  IF (complete_snapshot AND ordinals_valid IS DISTINCT FROM true)
    OR d.basis_set_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','DecisionRecordBasisSet','material_version',1,'basis',basis))
    OR d.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','DecisionRecord','material_version',1,
      'project_id',d.project_id,'decision_type',d.decision_type,'question',d.question,'decision',d.decision,'rationale',d.rationale,
      'decided_by',jsonb_build_object('type','ActorIdentity','id',d.decided_by),'supersedes_decision_id',NULL,'basis_set_hash',d.basis_set_hash)) THEN
    RAISE EXCEPTION 'decision basis ordinals or hashes invalid' USING ERRCODE='P17F2';
  END IF;
END $function$;
CREATE OR REPLACE FUNCTION public.b07_validate_re_review(link revision_action_re_reviews, take_locks boolean)
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
    LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, audit_findings, claim_versions, claims, correction_records, dataset_snapshots, datasets, evidence_relations, experiment_spec_versions, experiment_specs, impact_assessments, impact_targets, internal_review_records, literature_evidence, literature_evidence_relations, literature_evidence_review_events, literature_source_project_links, literature_sources, literature_support_snapshots, manuscript_artifact_placements, manuscript_citation_placements, manuscript_claim_placements, manuscript_versions, measurements, metric_definition_versions, metric_definitions, project_membership_events, project_memberships, project_role_assignments, projects, publications, review_issue_events, review_issues, run_artifact_inputs, run_dataset_inputs, runs, scientific_conclusion_claim_inputs, scientific_conclusion_literature_inputs, scientific_conclusion_versions, scientific_conclusions, source_versions, statistical_result_inputs, statistical_results IN SHARE MODE;
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
  tid:=coalesce(r.claim_version_id,r.scientific_conclusion_version_id,r.manuscript_version_id);
  old_tid:=coalesce(old.claim_version_id,old.scientific_conclusion_version_id,old.manuscript_version_id);
  IF link.recorded_by IN (SELECT b07_authors(tid,CASE WHEN r.claim_version_id IS NOT NULL THEN 'claim_versions' WHEN r.manuscript_version_id IS NOT NULL THEN 'manuscript_versions' ELSE 'scientific_conclusion_versions' END) UNION SELECT b07_authors(old_tid,CASE WHEN old.claim_version_id IS NOT NULL THEN 'claim_versions' WHEN old.manuscript_version_id IS NOT NULL THEN 'manuscript_versions' ELSE 'scientific_conclusion_versions' END)) THEN
    RAISE EXCEPTION 'independent re-reviewer required' USING ERRCODE='P17F2'; END IF;
  SELECT coalesce(array_agg(id),ARRAY[]::UUID[]) INTO cs FROM b07_closure(tid,CASE WHEN r.claim_version_id IS NOT NULL THEN 'claim_versions' WHEN r.manuscript_version_id IS NOT NULL THEN 'manuscript_versions' ELSE 'scientific_conclusion_versions' END) WHERE kind='claim_versions';
  IF a.action_type='NO_CHANGE' THEN good:=tid=old_tid AND r.target_content_hash=old.target_content_hash;
  ELSIF a.action_type='MANUSCRIPT_CHANGE' THEN good:=r.manuscript_version_id=a.result_manuscript_version_id;
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
      good:=good AND EXISTS(SELECT 1 FROM b07_closure(tid,CASE WHEN r.claim_version_id IS NOT NULL THEN 'claim_versions' WHEN r.manuscript_version_id IS NOT NULL THEN 'manuscript_versions' ELSE 'scientific_conclusion_versions' END) x JOIN measurements m ON x.kind='measurements' AND m.id=x.id
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
  PERFORM b07_current_target(tid,r.project_id,CASE WHEN r.claim_version_id IS NOT NULL THEN 'claim_versions' WHEN r.manuscript_version_id IS NOT NULL THEN 'manuscript_versions' ELSE 'scientific_conclusion_versions' END);
  IF witness IS NOT NULL THEN PERFORM b07_current_snapshot(witness,r.project_id); END IF;
  IF EXISTS(SELECT 1 FROM b07_closure(tid,CASE WHEN r.claim_version_id IS NOT NULL THEN 'claim_versions' WHEN r.manuscript_version_id IS NOT NULL THEN 'manuscript_versions' ELSE 'scientific_conclusion_versions' END) x JOIN source_versions s ON x.kind='source_versions' AND s.id=x.id
    JOIN literature_sources p ON p.id=s.literature_source_id LEFT JOIN source_versions current ON current.id=p.current_version_id
    WHERE s.version_kind='RETRACTED' OR current.version_kind='RETRACTED') THEN
    RAISE EXCEPTION 'retracted source cannot support re-review' USING ERRCODE='P17F2'; END IF;
END $function$;
CREATE OR REPLACE FUNCTION public.b08_validate_mapping(link revision_action_re_reviews, disposer uuid)
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
  tid:=coalesce(r.claim_version_id,r.scientific_conclusion_version_id,r.manuscript_version_id);
  old_tid:=coalesce(old.claim_version_id,old.scientific_conclusion_version_id,old.manuscript_version_id);
  IF link.recorded_by IN (SELECT b07_authors(tid,CASE WHEN r.claim_version_id IS NOT NULL THEN 'claim_versions' WHEN r.manuscript_version_id IS NOT NULL THEN 'manuscript_versions' ELSE 'scientific_conclusion_versions' END) UNION SELECT b07_authors(old_tid,CASE WHEN old.claim_version_id IS NOT NULL THEN 'claim_versions' WHEN old.manuscript_version_id IS NOT NULL THEN 'manuscript_versions' ELSE 'scientific_conclusion_versions' END)) THEN
    RAISE EXCEPTION 'independent re-reviewer required' USING ERRCODE='P17F2'; END IF;
  IF disposer=a.created_by OR disposer IN (SELECT b07_authors(tid,CASE WHEN r.claim_version_id IS NOT NULL THEN 'claim_versions' WHEN r.manuscript_version_id IS NOT NULL THEN 'manuscript_versions' ELSE 'scientific_conclusion_versions' END) UNION SELECT b07_authors(old_tid,CASE WHEN old.claim_version_id IS NOT NULL THEN 'claim_versions' WHEN old.manuscript_version_id IS NOT NULL THEN 'manuscript_versions' ELSE 'scientific_conclusion_versions' END)) THEN
    RAISE EXCEPTION 'independent disposer required' USING ERRCODE='P17F2'; END IF;
  SELECT coalesce(array_agg(id),ARRAY[]::UUID[]) INTO cs FROM b07_closure(tid,CASE WHEN r.claim_version_id IS NOT NULL THEN 'claim_versions' WHEN r.manuscript_version_id IS NOT NULL THEN 'manuscript_versions' ELSE 'scientific_conclusion_versions' END) WHERE kind='claim_versions';
  IF a.action_type='NO_CHANGE' THEN good:=tid=old_tid AND r.target_content_hash=old.target_content_hash;
  ELSIF a.action_type='MANUSCRIPT_CHANGE' THEN good:=r.manuscript_version_id=a.result_manuscript_version_id;
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
      good:=good AND EXISTS(SELECT 1 FROM b07_closure(tid,CASE WHEN r.claim_version_id IS NOT NULL THEN 'claim_versions' WHEN r.manuscript_version_id IS NOT NULL THEN 'manuscript_versions' ELSE 'scientific_conclusion_versions' END) x JOIN measurements m ON x.kind='measurements' AND m.id=x.id
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
END $function$;
CREATE OR REPLACE FUNCTION public.b07_lock_concern(iid uuid)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE old internal_review_records;
BEGIN
  LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, audit_findings, claim_versions, claims, correction_records, dataset_snapshots, datasets, evidence_relations, experiment_spec_versions, experiment_specs, impact_assessments, impact_targets, internal_review_records, literature_evidence, literature_evidence_relations, literature_evidence_review_events, literature_source_project_links, literature_sources, literature_support_snapshots, manuscript_artifact_placements, manuscript_citation_placements, manuscript_claim_placements, manuscript_versions, measurements, metric_definition_versions, metric_definitions, project_membership_events, project_memberships, project_role_assignments, projects, publications, review_issue_events, review_issues, run_artifact_inputs, run_dataset_inputs, runs, scientific_conclusion_claim_inputs, scientific_conclusion_literature_inputs, scientific_conclusion_versions, scientific_conclusions, source_versions, statistical_result_inputs, statistical_results IN SHARE MODE;
  SELECT r.* INTO old FROM review_issues i JOIN internal_review_records r ON r.id=i.review_record_id WHERE i.id=iid;
  PERFORM r.id FROM internal_review_records r WHERE r.project_id=old.project_id
    AND r.claim_version_id IS NOT DISTINCT FROM old.claim_version_id
    AND r.scientific_conclusion_version_id IS NOT DISTINCT FROM old.scientific_conclusion_version_id
    AND r.manuscript_version_id IS NOT DISTINCT FROM old.manuscript_version_id
    ORDER BY r.id FOR SHARE;
  PERFORM id FROM review_issues WHERE id=iid FOR UPDATE;
END $function$;
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
        LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, audit_findings, claim_versions, claims, correction_records, dataset_snapshots, datasets, evidence_relations, experiment_spec_versions, experiment_specs, impact_assessments, impact_targets, internal_review_records, literature_evidence, literature_evidence_relations, literature_evidence_review_events, literature_source_project_links, literature_sources, literature_support_snapshots, manuscript_artifact_placements, manuscript_citation_placements, manuscript_claim_placements, manuscript_versions, measurements, metric_definition_versions, metric_definitions, project_membership_events, project_memberships, project_role_assignments, projects, publications, review_issue_events, review_issues, run_artifact_inputs, run_dataset_inputs, runs, scientific_conclusion_claim_inputs, scientific_conclusion_literature_inputs, scientific_conclusion_versions, scientific_conclusions, source_versions, statistical_result_inputs, statistical_results IN SHARE MODE;
        IF NOT EXISTS(SELECT 1 FROM decision_records WHERE id=NEW.decision_id AND xmin=pg_current_xact_id()::xid) THEN
          RAISE EXCEPTION 'basis sealed to creation transaction' USING ERRCODE='P17F1'; END IF;
        IF TG_TABLE_NAME='decision_basis_conclusions' THEN
          PERFORM id FROM internal_review_records WHERE scientific_conclusion_version_id=NEW.scientific_conclusion_version_id ORDER BY id FOR SHARE;
        ELSE
          PERFORM x.id FROM internal_review_records x JOIN internal_review_records r ON r.id=NEW.internal_review_record_id
            WHERE x.project_id=r.project_id AND x.claim_version_id IS NOT DISTINCT FROM r.claim_version_id
              AND x.scientific_conclusion_version_id IS NOT DISTINCT FROM r.scientific_conclusion_version_id
    AND x.manuscript_version_id IS NOT DISTINCT FROM r.manuscript_version_id
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
CREATE OR REPLACE FUNCTION public.b07_validate_revision(a revision_actions)
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
  -- M1 target dispatch: this IF closes before shared correction-chain validation.
  IF review.manuscript_version_id IS NOT NULL THEN
    PERFORM m1_manuscript(review.manuscript_version_id,review.project_id);
    IF (SELECT content_hash FROM manuscript_versions WHERE id=review.manuscript_version_id) IS DISTINCT FROM review.target_content_hash
      OR (chosen_decision.id IS NOT NULL AND chosen_decision.project_id<>review.project_id)
      OR a.action_type NOT IN ('MANUSCRIPT_CHANGE','NO_CHANGE') THEN
      RAISE EXCEPTION 'exact manuscript concern required' USING ERRCODE='P17F2'; END IF;
    IF a.action_type='MANUSCRIPT_CHANGE' THEN
      PERFORM m1_manuscript(a.result_manuscript_version_id,review.project_id);
      IF NOT EXISTS(SELECT 1 FROM manuscript_versions old JOIN manuscript_versions successor ON successor.publication_id=old.publication_id
         WHERE old.id=review.manuscript_version_id AND successor.id=a.result_manuscript_version_id AND successor.version_number>old.version_number) THEN
        RAISE EXCEPTION 'later same-Publication result required' USING ERRCODE='P17F2'; END IF;
    END IF;
  ELSE
    IF a.action_type='MANUSCRIPT_CHANGE' THEN RAISE EXCEPTION 'manuscript concern required' USING ERRCODE='P17F2'; END IF;
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
  END IF; -- M1 target dispatch: manuscript / scientific concern.
  -- Shared by both branches; no manuscript result can bypass correction checks.
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
END $function$;
CREATE OR REPLACE FUNCTION public.b06_validate_revision(a revision_actions)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE concern review_issues; review internal_review_records; pid UUID;
  cs UUID[]; ms UUID[]; stats UUID[]; sources UUID[];
  cv claim_versions; sc scientific_conclusion_versions; spec experiment_spec_versions;
  execution runs; result statistical_results; source source_versions; previous source_versions;
  prior revision_actions; cursor_id UUID; visited UUID[] := ARRAY[a.id];
BEGIN
  IF a.action_type='MANUSCRIPT_CHANGE' THEN PERFORM b07_validate_revision(a); RETURN; END IF;
  IF a.decision_record_id IS NOT NULL OR a.review_issue_id IS NULL
    OR a.action_type NOT IN ('NEW_EXPERIMENT','ANALYSIS_CHANGE','CLAIM_CHANGE',
                            'CONCLUSION_CHANGE','SOURCE_CHANGE') THEN
    RAISE EXCEPTION 'revision path not contracted' USING ERRCODE='P17R1';
  END IF;
  SELECT * INTO concern FROM review_issues WHERE id=a.review_issue_id;
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
  IF pid IS NULL OR pid IS DISTINCT FROM review.project_id OR EXISTS (
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
  IF a.action_type='CLAIM_CHANGE' THEN
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
END $function$;
CREATE OR REPLACE FUNCTION public.b07_action_hash(a revision_actions)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
DECLARE results JSONB; d decision_records; prior revision_actions;
BEGIN
  SELECT * INTO d FROM decision_records WHERE id=a.decision_record_id;
  SELECT * INTO prior FROM revision_actions WHERE id=a.supersedes_revision_action_id;
  results:=jsonb_build_object(
    'result_experiment_spec_version',pr216_ref('ExperimentSpecVersion',a.result_experiment_spec_version_id,(SELECT content_hash FROM experiment_spec_versions WHERE id=a.result_experiment_spec_version_id)),
    'result_run',CASE WHEN a.result_run_id IS NULL THEN NULL ELSE jsonb_build_object('type','Run','id',a.result_run_id) END,
    'result_statistical_result',pr216_ref('StatisticalResult',a.result_statistical_result_id,(SELECT content_hash FROM statistical_results WHERE id=a.result_statistical_result_id)),
    'result_claim_version',pr216_ref('ClaimVersion',a.result_claim_version_id,(SELECT content_hash FROM claim_versions WHERE id=a.result_claim_version_id)),
    'result_scientific_conclusion_version',pr216_ref('ScientificConclusionVersion',a.result_scientific_conclusion_version_id,(SELECT content_hash FROM scientific_conclusion_versions WHERE id=a.result_scientific_conclusion_version_id)),
    'result_manuscript_version',pr216_ref('ManuscriptVersion',a.result_manuscript_version_id,(SELECT content_hash FROM manuscript_versions WHERE id=a.result_manuscript_version_id)),
    'result_source_version',pr216_ref('SourceVersion',a.result_source_version_id,(SELECT content_hash FROM source_versions WHERE id=a.result_source_version_id)));
  RETURN pr216_hash(jsonb_build_object('type','RevisionAction','material_version',1,
    'review_issue',CASE WHEN a.review_issue_id IS NULL THEN NULL ELSE jsonb_build_object('type','ReviewIssue','id',a.review_issue_id) END,
    'decision',pr216_ref('DecisionRecord',d.id,d.content_hash),'action_type',a.action_type,'results',results,
    'supersedes_revision_action',pr216_ref('RevisionAction',prior.id,prior.content_hash),
    'created_by',jsonb_build_object('type','ActorIdentity','id',a.created_by)));
END $function$;
CREATE OR REPLACE FUNCTION public.b08_validate_event(e review_issue_events)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
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
    OR (old.claim_version_id IS NULL AND old.scientific_conclusion_version_id IS NULL AND old.manuscript_version_id IS NULL)
    OR r.id=old.id OR r.recommendation NOT IN ('ACCEPT','MINOR_REVISION')
    OR a.decision_record_id IS DISTINCT FROM e.decision_id
    OR (e.new_status='ADDRESSED' AND (a.action_type NOT IN ('NEW_EXPERIMENT','ANALYSIS_CHANGE','CLAIM_CHANGE','CONCLUSION_CHANGE','SOURCE_CHANGE','MANUSCRIPT_CHANGE')
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
END $function$;
CREATE OR REPLACE FUNCTION public.pr215_complete_basis()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
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
      IF (SELECT decision_type FROM decision_records WHERE id=did)='REVISION_RESPONSE' THEN
        PERFORM b07_validate_decision(did,true);
        RETURN NULL;
      END IF;
      IF EXISTS(SELECT 1 FROM decision_basis_manuscripts WHERE decision_id=did) THEN
        RAISE EXCEPTION 'manuscript basis requires readiness purpose' USING ERRCODE='P17F2'; END IF;
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
    END $function$;
CREATE OR REPLACE FUNCTION public.b11_manuscript_basis_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
BEGIN
 IF (SELECT decision_type FROM decision_records WHERE id=NEW.decision_id)='REVISION_RESPONSE' THEN
   IF NOT EXISTS(SELECT 1 FROM decision_records WHERE id=NEW.decision_id AND xmin=pg_current_xact_id()::xid) THEN
     RAISE EXCEPTION 'basis sealed to creation' USING ERRCODE='P17F1'; END IF;
   PERFORM b07_lock_concern(review_issue_id) FROM decision_revision_concerns WHERE decision_id=NEW.decision_id;
   RETURN NEW;
 END IF;
 PERFORM b11_check_basis(NEW.decision_id,NEW.manuscript_version_id);
 RETURN NEW;
END $function$;
CREATE FUNCTION m1_admission_reviews(tid UUID,pid UUID) RETURNS SETOF internal_review_records LANGUAGE sql STABLE SET search_path TO pg_catalog, public, pg_temp AS $$
 SELECT * FROM b11_applicable_reviews(tid,pid)
 UNION SELECT r.* FROM internal_review_records r JOIN manuscript_versions old ON old.id=r.manuscript_version_id
 JOIN manuscript_versions selected ON selected.publication_id=old.publication_id
 WHERE selected.id=tid AND old.version_number<selected.version_number AND r.project_id=pid
 AND EXISTS(SELECT 1 FROM review_issues i WHERE i.review_record_id=r.id AND i.status='OPEN' AND i.severity='BLOCKING')
$$;
CREATE OR REPLACE FUNCTION public.b11_complete(did uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
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
 FOR iid IN SELECT i.id FROM review_issues i JOIN m1_admission_reviews(m.id,d.project_id) r ON r.id=i.review_record_id ORDER BY i.id LOOP
   PERFORM b08_check_history(iid);
 END LOOP;
 IF EXISTS(SELECT 1 FROM review_issues i JOIN m1_admission_reviews(m.id,d.project_id) r ON r.id=i.review_record_id WHERE i.status='OPEN' AND i.severity='BLOCKING') THEN
   RAISE EXCEPTION 'applicable OPEN blocker' USING ERRCODE='P17F2'; END IF;
IF d.decision_type='PREPARE_SUBMISSION' THEN PERFORM b12_saved_decision(did,m.id,d.project_id); END IF;
END $function$;
CREATE OR REPLACE FUNCTION public.b12_approval_gate(r approval_requests, approver uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
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
 FOR iid IN SELECT i.id FROM review_issues i JOIN m1_admission_reviews(m.id,r.project_id) review ON review.id=i.review_record_id ORDER BY i.id LOOP
  PERFORM b08_check_history(iid);
 END LOOP;
 IF EXISTS(SELECT 1 FROM review_issues i JOIN m1_admission_reviews(m.id,r.project_id) review ON review.id=i.review_record_id
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
END $function$;
CREATE OR REPLACE FUNCTION public.b14r_approval_gate(r approval_requests, approver uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
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
 FOR iid IN SELECT i.id FROM review_issues i JOIN m1_admission_reviews(m.id,r.project_id) review ON review.id=i.review_record_id ORDER BY i.id LOOP
  PERFORM b08_check_history(iid);
 END LOOP;
 IF EXISTS(SELECT 1 FROM review_issues i JOIN m1_admission_reviews(m.id,r.project_id) review ON review.id=i.review_record_id
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
END $function$;
CREATE OR REPLACE FUNCTION public.b14_consumption_gate(r approval_requests, approver uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE m manuscript_versions; d decision_records; rr internal_review_records; iid UUID;
BEGIN
 IF r.approval_purpose IS DISTINCT FROM 'READY_FOR_SUBMISSION'
 OR r.manuscript_version_id IS NULL OR r.scientific_conclusion_version_id IS NOT NULL THEN
  RAISE EXCEPTION 'exact READY manuscript tuple required' USING ERRCODE='P16P1'; END IF;
 SELECT * INTO m FROM manuscript_versions WHERE id=r.manuscript_version_id;
 SELECT * INTO d FROM decision_records WHERE id=r.basis_decision_id;
 IF NOT EXISTS(SELECT 1 FROM projects WHERE id=r.project_id AND lifecycle_status='ACTIVE')
 OR NOT EXISTS(SELECT 1 FROM publications WHERE id=m.publication_id AND project_id=r.project_id
  AND (lifecycle_status='INTERNAL_REVIEW' OR (lifecycle_status='READY' AND xmin=pg_current_xact_id()::xid))) THEN
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
 PERFORM b14a_admission(m.id,r.project_id);
 PERFORM b14_material(m.id,r.project_id);
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
 FOR iid IN SELECT i.id FROM review_issues i JOIN m1_admission_reviews(m.id,r.project_id) review ON review.id=i.review_record_id ORDER BY i.id LOOP
  PERFORM b08_check_history(iid);
 END LOOP;
 IF EXISTS(SELECT 1 FROM review_issues i JOIN m1_admission_reviews(m.id,r.project_id) review ON review.id=i.review_record_id
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
END $function$;
CREATE OR REPLACE FUNCTION public.b14a_admission(mid uuid, pid uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
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
 FOR iid IN SELECT i.id FROM review_issues i JOIN m1_admission_reviews(mid,pid) applicable ON applicable.id=i.review_record_id LOOP PERFORM b08_check_history(iid); END LOOP;
 IF EXISTS(SELECT 1 FROM review_issues i JOIN m1_admission_reviews(mid,pid) applicable ON applicable.id=i.review_record_id WHERE i.status='OPEN' AND i.severity='BLOCKING') THEN
 RAISE EXCEPTION 'applicable open blocker' USING ERRCODE='P14B1'; END IF;
END $function$;
CREATE OR REPLACE FUNCTION public.pr215_revision_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE concern review_issues; prior revision_actions; effective UUID;
BEGIN
 IF TG_OP='INSERT' AND NEW.material_version=2 THEN RETURN NEW; END IF;

  IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'revision history immutable' USING ERRCODE='P17F1'; END IF;
  LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, audit_findings, claim_versions, claims, correction_records, dataset_snapshots, datasets, evidence_relations, experiment_spec_versions, experiment_specs, impact_assessments, impact_targets, internal_review_records, literature_evidence, literature_evidence_relations, literature_evidence_review_events, literature_source_project_links, literature_sources, literature_support_snapshots, manuscript_artifact_placements, manuscript_citation_placements, manuscript_claim_placements, manuscript_versions, measurements, metric_definition_versions, metric_definitions, project_membership_events, project_memberships, project_role_assignments, projects, publications, review_issue_events, review_issues, run_artifact_inputs, run_dataset_inputs, runs, scientific_conclusion_claim_inputs, scientific_conclusion_literature_inputs, scientific_conclusion_versions, scientific_conclusions, source_versions, statistical_result_inputs, statistical_results IN SHARE MODE;
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
  IF EXISTS(SELECT 1 FROM internal_review_records WHERE id=concern.review_record_id AND manuscript_version_id IS NOT NULL) THEN
    IF concern.status<>'OPEN' THEN RAISE EXCEPTION 'manuscript concern already disposed' USING ERRCODE='P04M2'; END IF;
    IF NEW.action_type='MANUSCRIPT_CHANGE' AND concern.severity='BLOCKING' AND
      (NEW.decision_record_id IS NULL OR NOT EXISTS(SELECT 1 FROM decision_records WHERE id=NEW.decision_record_id AND decision_type='REVISION_RESPONSE' AND decision='REQUIRE_CHANGE')) THEN
      RAISE EXCEPTION 'blocking manuscript change requires REQUIRE_CHANGE' USING ERRCODE='P16B1'; END IF;
  END IF;
  PERFORM b07_validate_revision(NEW);
  IF NEW.content_hash IS DISTINCT FROM b07_action_hash(NEW) THEN
    RAISE EXCEPTION 'action hash invalid' USING ERRCODE='P17F2'; END IF;
  RETURN NEW;
END $function$;
CREATE OR REPLACE FUNCTION public.b07_revision_basis_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE purpose TEXT;
BEGIN
  LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, audit_findings, claim_versions, claims, correction_records, dataset_snapshots, datasets, evidence_relations, experiment_spec_versions, experiment_specs, impact_assessments, impact_targets, internal_review_records, literature_evidence, literature_evidence_relations, literature_evidence_review_events, literature_source_project_links, literature_sources, literature_support_snapshots, manuscript_artifact_placements, manuscript_citation_placements, manuscript_claim_placements, manuscript_versions, measurements, metric_definition_versions, metric_definitions, project_membership_events, project_memberships, project_role_assignments, projects, publications, review_issue_events, review_issues, run_artifact_inputs, run_dataset_inputs, runs, scientific_conclusion_claim_inputs, scientific_conclusion_literature_inputs, scientific_conclusion_versions, scientific_conclusions, source_versions, statistical_result_inputs, statistical_results IN SHARE MODE;
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
END $function$;
CREATE OR REPLACE FUNCTION public.b08_event_guard()
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
  LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, audit_findings, claim_versions, claims, correction_records, dataset_snapshots, datasets, evidence_relations, experiment_spec_versions, experiment_specs, impact_assessments, impact_targets, internal_review_records, literature_evidence, literature_evidence_relations, literature_evidence_review_events, literature_source_project_links, literature_sources, literature_support_snapshots, manuscript_artifact_placements, manuscript_citation_placements, manuscript_claim_placements, manuscript_versions, measurements, metric_definition_versions, metric_definitions, project_membership_events, project_memberships, project_role_assignments, projects, publications, run_artifact_inputs, run_dataset_inputs, runs, scientific_conclusion_claim_inputs, scientific_conclusion_literature_inputs, scientific_conclusion_versions, scientific_conclusions, source_versions, statistical_result_inputs, statistical_results IN SHARE MODE;
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
END $function$;
CREATE OR REPLACE FUNCTION public.b14_verify_ready(pid uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE p publications; e publication_lifecycle_events; c approval_grant_consumptions; g approval_grants; d approval_decisions; r approval_requests; m manuscript_versions; ge approval_grant_events;
BEGIN
 SELECT * INTO p FROM publications WHERE id=pid;
 SELECT * INTO e FROM publication_lifecycle_events WHERE publication_id=pid AND new_status='READY';
 IF p.lifecycle_status<>'READY' THEN
  IF e.id IS NOT NULL THEN RAISE EXCEPTION 'orphan READY event' USING ERRCODE='P17F2'; END IF;
  RETURN;
 END IF;
 SELECT * INTO c FROM approval_grant_consumptions WHERE id=e.basis_grant_consumption_id;
 SELECT * INTO g FROM approval_grants WHERE id=c.grant_id;
 SELECT * INTO d FROM approval_decisions WHERE id=g.approval_decision_id;
 SELECT * INTO r FROM approval_requests WHERE id=d.approval_request_id;
 SELECT * INTO m FROM manuscript_versions WHERE id=r.manuscript_version_id;
 SELECT * INTO ge FROM approval_grant_events WHERE grant_id=g.id AND prior_status='ACTIVE';
 IF e.id IS NULL OR c.id IS NULL OR g.id IS NULL OR r.id IS NULL OR m.id IS NULL OR ge.id IS NULL
  OR e.prior_status IS DISTINCT FROM 'INTERNAL_REVIEW' OR e.manuscript_version_id IS NOT NULL
  OR c.command<>'TRANSITION_PUBLICATION_READY' OR g.purpose<>'READY_FOR_SUBMISSION'
  OR g.allowed_command<>'transition_publication_ready' OR g.status<>'CONSUMED'
  OR c.project_id IS DISTINCT FROM p.project_id OR g.project_id IS DISTINCT FROM p.project_id OR r.project_id IS DISTINCT FROM p.project_id
  OR c.result_publication_id IS DISTINCT FROM pid OR m.publication_id IS DISTINCT FROM pid
  OR p.current_manuscript_version_id IS DISTINCT FROM m.id OR m.content_hash IS DISTINCT FROM r.target_content_hash
  OR m.hash_scheme IS DISTINCT FROM r.target_hash_scheme
  OR e.basis_decision_id IS DISTINCT FROM r.basis_decision_id
  OR e.actor_id IS DISTINCT FROM c.actor_id OR e.occurred_at IS DISTINCT FROM c.consumed_at
  OR ge.actor_id IS DISTINCT FROM c.actor_id OR ge.occurred_at IS DISTINCT FROM c.consumed_at OR ge.new_status<>'CONSUMED'
  OR NOT EXISTS(SELECT 1 FROM publication_lifecycle_events WHERE publication_id=pid AND new_status='INTERNAL_REVIEW' AND occurred_at<=e.occurred_at AND manuscript_version_id IN (SELECT id FROM manuscript_versions WHERE publication_id=pid AND status='FROZEN' AND version_number<=m.version_number))
  OR (SELECT count(*) FROM publication_lifecycle_events WHERE publication_id=pid)<>3 THEN
  RAISE EXCEPTION 'complete READY graph required' USING ERRCODE='P17F2'; END IF;
 PERFORM b14r_saved_decision(r.basis_decision_id,m.id,p.project_id);
 IF EXISTS(SELECT 1 FROM approval_grant_consumptions WHERE id=c.id AND xmin=pg_current_xact_id()::xid)
 OR EXISTS(SELECT 1 FROM publication_lifecycle_events WHERE id=e.id AND xmin=pg_current_xact_id()::xid)
 OR EXISTS(SELECT 1 FROM publications WHERE id=pid AND xmin=pg_current_xact_id()::xid) THEN
  IF NOT EXISTS(SELECT 1 FROM publications WHERE id=pid AND xmin=pg_current_xact_id()::xid)
  OR NOT EXISTS(SELECT 1 FROM approval_grant_consumptions WHERE id=c.id AND xmin=pg_current_xact_id()::xid)
  OR NOT EXISTS(SELECT 1 FROM publication_lifecycle_events WHERE id=e.id AND xmin=pg_current_xact_id()::xid)
  OR NOT EXISTS(SELECT 1 FROM approval_grant_events WHERE id=ge.id AND xmin=pg_current_xact_id()::xid)
  OR NOT EXISTS(SELECT 1 FROM approval_grants WHERE id=g.id AND xmin=pg_current_xact_id()::xid) THEN
   RAISE EXCEPTION 'same transaction READY graph required' USING ERRCODE='P14I1'; END IF;
  PERFORM b13_preheld(true);
 END IF;
END $function$;
CREATE OR REPLACE FUNCTION public.b04_check_manuscript_closure()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
    BEGIN PERFORM b04_verify_structure(NEW.id);
      IF (SELECT status FROM manuscript_versions WHERE id=NEW.id)='FROZEN' THEN
        PERFORM m1_manuscript(NEW.id,(SELECT p.project_id FROM publications p JOIN manuscript_versions m ON m.publication_id=p.id WHERE m.id=NEW.id));
      END IF; RETURN NULL; END $function$;
"""

_DOWNGRADE = r"""
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM manuscript_versions WHERE version_number>1)
 OR EXISTS(SELECT 1 FROM revision_actions WHERE result_manuscript_version_id IS NOT NULL)
 OR EXISTS(SELECT 1 FROM decision_basis_manuscripts b JOIN decision_records d ON d.id=b.decision_id WHERE d.decision_type='REVISION_RESPONSE') THEN
 RAISE EXCEPTION 'M1 manuscript history prevents downgrade' USING ERRCODE='P17F1'; END IF;
END $$;
DROP INDEX ix_m1_revision_manuscript;
ALTER TABLE revision_actions RENAME CONSTRAINT ck_m1_revision_action_shape TO ck_b23_revision_shape;
DROP INDEX uq_m1_one_draft_manuscript;
ALTER TABLE manuscript_versions DROP CONSTRAINT ck_m1_manuscript_change_class;
CREATE OR REPLACE FUNCTION public.b04_verify_structure(identity uuid)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
    DECLARE m manuscript_versions; project UUID; pointer UUID; n BIGINT;
    BEGIN
      SELECT * INTO m FROM manuscript_versions WHERE id=identity;
      IF NOT FOUND THEN RETURN; END IF;
      IF m.status='DRAFT' THEN
        IF m.content_hash IS NOT NULL OR m.placement_set_hash IS NOT NULL OR m.frozen_at IS NOT NULL THEN
          RAISE EXCEPTION 'malformed draft seal' USING ERRCODE='P04M3'; END IF;
        RETURN;
      END IF;
      SELECT project_id,current_manuscript_version_id INTO project,pointer FROM publications WHERE id=m.publication_id;
      IF pointer IS DISTINCT FROM m.id OR m.content_hash IS NULL OR m.placement_set_hash IS NULL OR m.frozen_at IS NULL THEN
        RAISE EXCEPTION 'incomplete manuscript seal' USING ERRCODE='P04M3'; END IF;
      IF NOT EXISTS (SELECT 1 FROM artifact_versions v JOIN artifacts a ON a.id=v.artifact_id
        WHERE v.id=m.document_artifact_version_id AND a.project_id=project AND a.artifact_type='manuscript'
          AND v.status IN ('FROZEN','SUPERSEDED') AND v.frozen_at IS NOT NULL AND v.byte_size IS NOT NULL
          AND v.content_hash ~ '^[0-9a-f]{64}$') THEN
        RAISE EXCEPTION 'manuscript document closure' USING ERRCODE='P04M3'; END IF;
      SELECT count(*) INTO n FROM (
        SELECT section_id,ordinal FROM manuscript_claim_placements WHERE manuscript_version_id=identity
        UNION ALL SELECT section_id,ordinal FROM manuscript_citation_placements WHERE manuscript_version_id=identity
        UNION ALL SELECT section_id,ordinal FROM manuscript_artifact_placements WHERE manuscript_version_id=identity) p;
      IF n>10000 THEN RAISE EXCEPTION 'placement cap exceeded' USING ERRCODE='P04M3'; END IF;
      IF EXISTS (SELECT 1 FROM (
        SELECT 'claim' AS kind,section_id,ordinal FROM manuscript_claim_placements WHERE manuscript_version_id=identity
        UNION ALL SELECT 'citation',section_id,ordinal FROM manuscript_citation_placements WHERE manuscript_version_id=identity
        UNION ALL SELECT 'artifact',section_id,ordinal FROM manuscript_artifact_placements WHERE manuscript_version_id=identity) p
        GROUP BY kind,section_id HAVING min(ordinal)<>0 OR max(ordinal)<>count(*)-1 OR count(DISTINCT ordinal)<>count(*)) THEN
        RAISE EXCEPTION 'placement ordinal gaps' USING ERRCODE='P04M3'; END IF;
      IF EXISTS (SELECT 1 FROM manuscript_claim_placements p
        LEFT JOIN claim_versions v ON v.id=p.claim_version_id LEFT JOIN claims c ON c.id=v.claim_id
        LEFT JOIN scientific_conclusion_versions s ON s.id=p.scientific_conclusion_version_id
        LEFT JOIN scientific_conclusions sc ON sc.id=s.scientific_conclusion_id
        WHERE p.manuscript_version_id=identity AND
          ((p.claim_version_id IS NULL)=(p.scientific_conclusion_version_id IS NULL)
          OR (p.claim_version_id IS NOT NULL AND (c.project_id IS DISTINCT FROM project OR v.status NOT IN ('FROZEN','SUPERSEDED') OR v.frozen_at IS NULL OR v.content_hash IS NULL))
          OR (p.scientific_conclusion_version_id IS NOT NULL AND (sc.project_id IS DISTINCT FROM project OR s.status NOT IN ('FROZEN','SUPERSEDED') OR s.frozen_at IS NULL OR s.content_hash IS NULL OR s.support_set_hash IS NULL)))) THEN
        RAISE EXCEPTION 'scientific placement closure' USING ERRCODE='P04M3'; END IF;
      IF EXISTS (SELECT 1 FROM manuscript_citation_placements p LEFT JOIN source_versions v ON v.id=p.source_version_id
        WHERE p.manuscript_version_id=identity AND (v.status NOT IN ('FROZEN','SUPERSEDED') OR v.frozen_at IS NULL OR v.content_hash IS NULL
          OR NOT EXISTS (SELECT 1 FROM literature_source_project_links l WHERE l.literature_source_id=v.literature_source_id AND l.project_id=project))) THEN
        RAISE EXCEPTION 'citation placement closure' USING ERRCODE='P04M3'; END IF;
      IF EXISTS (SELECT 1 FROM manuscript_artifact_placements p LEFT JOIN artifact_versions v ON v.id=p.artifact_version_id
        LEFT JOIN artifacts a ON a.id=v.artifact_id WHERE p.manuscript_version_id=identity
          AND (a.project_id IS DISTINCT FROM project OR v.status NOT IN ('FROZEN','SUPERSEDED') OR v.frozen_at IS NULL OR v.content_hash IS NULL)) THEN
        RAISE EXCEPTION 'artifact placement closure' USING ERRCODE='P04M3'; END IF;
    END $function$;
CREATE OR REPLACE FUNCTION public.pr212_draft_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
    BEGIN
      IF TG_OP='DELETE' THEN
        RAISE EXCEPTION 'manuscript history retained' USING ERRCODE='P04M1';
      END IF;
      IF TG_OP='UPDATE' THEN
        IF OLD.status='FROZEN' THEN RAISE EXCEPTION 'sealed manuscript immutable' USING ERRCODE='P04M1'; END IF;
        IF OLD.status<>'DRAFT' OR NEW.status<>'FROZEN' OR NEW.row_version<>OLD.row_version+1
          OR NEW.content_hash IS NULL OR NEW.placement_set_hash IS NULL OR NEW.frozen_at IS NULL
          OR (to_jsonb(NEW)-ARRAY['status','row_version','content_hash','placement_set_hash','frozen_at'])
            IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['status','row_version','content_hash','placement_set_hash','frozen_at']) THEN
          RAISE EXCEPTION 'invalid manuscript seal transition' USING ERRCODE='P04M2'; END IF;
      ELSIF NEW.status<>'DRAFT' OR NEW.row_version<>1 OR NEW.placement_set_hash IS NOT NULL
        OR NEW.content_hash IS NOT NULL OR NEW.frozen_at IS NOT NULL THEN
        RAISE EXCEPTION 'insert draft only' USING ERRCODE='P04M2';
      END IF;
      PERFORM 1 FROM publications p
        JOIN artifact_versions v ON v.id=NEW.document_artifact_version_id
        JOIN artifacts a ON a.id=v.artifact_id
        WHERE p.id=NEW.publication_id AND a.project_id=p.project_id
          AND a.artifact_type='manuscript' AND v.status='FROZEN'
          AND v.frozen_at IS NOT NULL AND v.content_hash ~ '^[0-9a-f]{64}$'
        FOR SHARE OF p,v,a;
      IF NOT FOUND THEN
        RAISE EXCEPTION 'exact frozen manuscript document required' USING ERRCODE='P17D3';
      END IF;
      RETURN NEW;
    END $function$;
CREATE OR REPLACE FUNCTION public.pr212_publication_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
    DECLARE candidate RECORD; admitted boolean;
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
      IF OLD.lifecycle_status='INTERNAL_REVIEW' AND NEW.lifecycle_status='READY'
       AND NEW.row_version::bigint=OLD.row_version::bigint+1
       AND (to_jsonb(NEW)-ARRAY['lifecycle_status','row_version']) IS NOT DISTINCT FROM
           (to_jsonb(OLD)-ARRAY['lifecycle_status','row_version']) THEN
        PERFORM b13_preheld(true);
        admitted:=false;
        FOR candidate IN SELECT r AS request,d.decided_by,g.valid_until FROM approval_grants g JOIN approval_decisions d ON d.id=g.approval_decision_id
          JOIN approval_requests r ON r.id=d.approval_request_id WHERE g.status='ACTIVE'
          AND g.purpose='READY_FOR_SUBMISSION' AND g.allowed_command='transition_publication_ready'
          AND g.project_id=NEW.project_id AND r.manuscript_version_id=NEW.current_manuscript_version_id
          AND clock_timestamp()<g.valid_until ORDER BY g.id LOOP
          BEGIN
            PERFORM b14_consumption_gate(candidate.request,candidate.decided_by);
            IF clock_timestamp()<candidate.valid_until AND pr216_approver_active(candidate.decided_by,NEW.project_id) THEN
              admitted:=true; EXIT;
            END IF;
          EXCEPTION WHEN SQLSTATE 'P16T1' OR SQLSTATE 'P16G1' OR SQLSTATE 'P16B1' OR SQLSTATE 'P16A1' OR SQLSTATE 'P16C1' OR SQLSTATE 'P16R1' THEN
            CONTINUE;
          END;
        END LOOP;
        IF NOT admitted THEN RAISE EXCEPTION 'valid ACTIVE readiness permission required' USING ERRCODE='P16G1'; END IF;
        RETURN NEW;
      END IF;
      RAISE EXCEPTION 'invalid manuscript pointer transition' USING ERRCODE='P04M2';
    END $function$;
CREATE OR REPLACE FUNCTION public.b14a_verify_entry(pid uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
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
 IF p.lifecycle_status NOT IN ('INTERNAL_REVIEW','READY') OR e.id IS NULL OR e.prior_status IS DISTINCT FROM 'DRAFTING'
 OR m.id IS NULL OR m.publication_id IS DISTINCT FROM pid OR m.status<>'FROZEN' OR m.frozen_at IS NULL
 OR e.manuscript_version_id IS DISTINCT FROM p.current_manuscript_version_id
 OR e.occurred_at<m.frozen_at OR e.occurred_at<p.created_at OR e.occurred_at>clock_timestamp()
 OR e.basis_decision_id IS NOT NULL OR e.basis_grant_consumption_id IS NOT NULL THEN
 RAISE EXCEPTION 'complete exact entry graph required' USING ERRCODE='P14P1'; END IF;
 PERFORM b04_verify_structure(m.id);
 IF p.lifecycle_status='INTERNAL_REVIEW' AND EXISTS(SELECT 1 FROM publication_lifecycle_events WHERE id=e.id AND xmin=pg_current_xact_id()::xid) THEN
  IF NOT EXISTS(SELECT 1 FROM publications WHERE id=pid AND xmin=pg_current_xact_id()::xid) THEN
   RAISE EXCEPTION 'same transaction transition required' USING ERRCODE='P14I1'; END IF;
  PERFORM b14a_preheld(); PERFORM b14a_admission(m.id,p.project_id);
  IF NOT b13_authorized(e.actor_id,p.project_id,ARRAY['OWNER','RESEARCHER']) OR NOT EXISTS(SELECT 1 FROM projects WHERE id=p.project_id AND lifecycle_status='ACTIVE') THEN
   RAISE EXCEPTION 'final entry authority unavailable' USING ERRCODE='P14A1'; END IF;
 ELSIF p.lifecycle_status='INTERNAL_REVIEW' AND EXISTS(SELECT 1 FROM publications WHERE id=pid AND xmin=pg_current_xact_id()::xid) THEN
  RAISE EXCEPTION 'old event cannot complete new transition' USING ERRCODE='P14I1';
 END IF;
END $function$;
CREATE OR REPLACE FUNCTION public.b05_verify_review_structure(identity uuid)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE target UUID; r internal_review_records; n BIGINT;
BEGIN
  SELECT manuscript_version_id INTO target FROM internal_review_records WHERE id=identity;
  IF target IS NULL THEN RETURN; END IF;
  PERFORM 1 FROM manuscript_versions WHERE id=target FOR UPDATE;
  SELECT * INTO r FROM internal_review_records WHERE id=identity FOR SHARE;
  IF r.manuscript_version_id IS DISTINCT FROM target OR NOT EXISTS (
    SELECT 1 FROM manuscript_versions m JOIN publications p ON p.id=m.publication_id
    WHERE m.id=target AND p.project_id=r.project_id AND m.status IN ('FROZEN','SUPERSEDED')
      AND m.frozen_at IS NOT NULL AND m.placement_set_hash IS NOT NULL
      AND m.content_hash=r.target_content_hash) THEN
    RAISE EXCEPTION 'B05 malformed target for review %',identity USING ERRCODE='P05R1';
  END IF;
  SELECT count(*) INTO n FROM review_issues WHERE review_record_id=identity;
  IF n>0 AND EXISTS (SELECT 1 FROM review_issues WHERE review_record_id=identity
      GROUP BY review_record_id HAVING min(ordinal)<>0 OR max(ordinal)<>n-1
        OR count(DISTINCT ordinal)<>n) THEN
    RAISE EXCEPTION 'B05 issue ordinal gap for review %',identity USING ERRCODE='P05R1';
  END IF;
  IF EXISTS (SELECT 1 FROM review_issues i WHERE i.review_record_id=identity AND
    (i.status<>'OPEN' OR (SELECT count(*) FROM review_issue_events e WHERE e.issue_id=i.id)<>1
      OR NOT EXISTS (SELECT 1 FROM review_issue_events e WHERE e.issue_id=i.id
        AND e.prior_status IS NULL AND e.new_status='OPEN'
        AND e.actor_id=r.reviewer_actor_id AND e.occurred_at=i.created_at))) THEN
    RAISE EXCEPTION 'B05 malformed OPEN history for review %',identity USING ERRCODE='P05R1';
  END IF;
END $function$;
CREATE OR REPLACE FUNCTION public.b07_closure(target_id uuid, seed_kind text)
 RETURNS TABLE(kind text, id uuid)
 LANGUAGE sql
 STABLE
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
WITH RECURSIVE edges AS (SELECT
    'scientific_conclusion_versions'::text AS kind,
    id,'scientific_conclusions'::text AS child_kind,
    scientific_conclusion_id AS child_id
    FROM scientific_conclusion_versions
 UNION ALL SELECT 'claim_versions'::text
      AS kind, id,'claims'::text
      AS child_kind, claim_id AS child_id
      FROM claim_versions
 UNION ALL SELECT 'source_versions'::text
      AS kind, id,'literature_sources'::text
      AS child_kind, literature_source_id AS child_id
      FROM source_versions
 UNION ALL SELECT 'artifact_versions'::text
      AS kind, id,'artifacts'::text
      AS child_kind, artifact_id AS child_id
      FROM artifact_versions
 UNION ALL SELECT 'dataset_snapshots'::text
      AS kind, id,'datasets'::text
      AS child_kind, dataset_id AS child_id
      FROM dataset_snapshots
 UNION ALL SELECT 'metric_definition_versions'::text
      AS kind, id,'metric_definitions'::text
      AS child_kind, metric_definition_id AS child_id
      FROM metric_definition_versions
 UNION ALL SELECT 'experiment_spec_versions'::text
      AS kind, id,'experiment_specs'::text
      AS child_kind, experiment_spec_id AS child_id
      FROM experiment_spec_versions
 UNION ALL SELECT
    'scientific_conclusion_versions',
    conclusion_version_id,'claim_versions',
    claim_version_id
      FROM scientific_conclusion_claim_inputs
      WHERE claim_version_id IS NOT NULL
 UNION ALL SELECT
    'scientific_conclusion_versions',
    conclusion_version_id,'literature_support_snapshots',
    literature_support_snapshot_id
      FROM scientific_conclusion_claim_inputs
      WHERE literature_support_snapshot_id IS NOT NULL
 UNION ALL SELECT
    'scientific_conclusion_versions',
    conclusion_version_id,'literature_evidence',literature_evidence_id
      FROM scientific_conclusion_literature_inputs
      WHERE literature_evidence_id IS NOT NULL
 UNION ALL SELECT 'claim_versions',claim_version_id,'measurements',measurement_id
      FROM evidence_relations
      WHERE measurement_id IS NOT NULL
 UNION ALL SELECT 'claim_versions',claim_version_id,'statistical_results',statistical_result_id
      FROM evidence_relations
      WHERE statistical_result_id IS NOT NULL
 UNION ALL SELECT 'statistical_results',statistical_result_id,'measurements',measurement_id
      FROM statistical_result_inputs
      WHERE measurement_id IS NOT NULL
 UNION ALL SELECT 'runs',run_id,'artifact_versions',artifact_version_id
      FROM run_artifact_inputs
      WHERE artifact_version_id IS NOT NULL
 UNION ALL SELECT 'runs',run_id,'dataset_snapshots',dataset_snapshot_id
      FROM run_dataset_inputs
      WHERE dataset_snapshot_id IS NOT NULL
 UNION ALL SELECT
    'literature_support_snapshots',
    literature_support_snapshot_id,'literature_evidence',literature_evidence_id
      FROM literature_evidence_relations
      WHERE literature_evidence_id IS NOT NULL
 UNION ALL SELECT 'measurements',id,'runs',run_id FROM measurements WHERE run_id IS NOT NULL
 UNION ALL SELECT 'measurements',id,'metric_definition_versions',metric_definition_version_id
      FROM measurements
      WHERE metric_definition_version_id IS NOT NULL
 UNION ALL SELECT 'runs',id,'experiment_spec_versions',experiment_spec_version_id
      FROM runs
      WHERE experiment_spec_version_id IS NOT NULL
 UNION ALL SELECT 'literature_evidence',id,'source_versions',source_version_id
      FROM literature_evidence
      WHERE source_version_id IS NOT NULL
 UNION ALL SELECT 'literature_support_snapshots',id,'claim_versions',claim_version_id
      FROM literature_support_snapshots
      WHERE claim_version_id IS NOT NULL
 UNION ALL SELECT
    'literature_support_snapshots',
    id,'literature_support_snapshots',
    previous_snapshot_id
      FROM literature_support_snapshots
      WHERE previous_snapshot_id IS NOT NULL
 UNION ALL SELECT 'source_versions',id,'artifact_versions',fulltext_artifact_version_id
      FROM source_versions
      WHERE fulltext_artifact_version_id IS NOT NULL
 UNION ALL SELECT 'source_versions',id,'source_versions',predecessor_source_version_id
      FROM source_versions
      WHERE predecessor_source_version_id IS NOT NULL
 UNION ALL SELECT 'source_versions',id,'artifact_versions',correction_basis_artifact_version_id
      FROM source_versions
      WHERE correction_basis_artifact_version_id IS NOT NULL),
          closure(kind,id) AS (SELECT seed_kind,target_id
            UNION SELECT e.child_kind,e.child_id FROM closure c JOIN edges e
              ON e.kind=c.kind AND e.id=c.id) SELECT kind,id FROM closure
$function$;
CREATE OR REPLACE FUNCTION public.b07_authors(target_id uuid, seed_kind text)
 RETURNS SETOF uuid
 LANGUAGE sql
 STABLE
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
WITH RECURSIVE edges AS (SELECT
    'scientific_conclusion_versions'::text AS kind,
    id,'scientific_conclusions'::text AS child_kind,
    scientific_conclusion_id AS child_id
    FROM scientific_conclusion_versions
 UNION ALL SELECT 'claim_versions'::text
      AS kind, id,'claims'::text
      AS child_kind, claim_id AS child_id
      FROM claim_versions
 UNION ALL SELECT 'source_versions'::text
      AS kind, id,'literature_sources'::text
      AS child_kind, literature_source_id AS child_id
      FROM source_versions
 UNION ALL SELECT 'artifact_versions'::text
      AS kind, id,'artifacts'::text
      AS child_kind, artifact_id AS child_id
      FROM artifact_versions
 UNION ALL SELECT 'dataset_snapshots'::text
      AS kind, id,'datasets'::text
      AS child_kind, dataset_id AS child_id
      FROM dataset_snapshots
 UNION ALL SELECT 'metric_definition_versions'::text
      AS kind, id,'metric_definitions'::text
      AS child_kind, metric_definition_id AS child_id
      FROM metric_definition_versions
 UNION ALL SELECT 'experiment_spec_versions'::text
      AS kind, id,'experiment_specs'::text
      AS child_kind, experiment_spec_id AS child_id
      FROM experiment_spec_versions
 UNION ALL SELECT
    'scientific_conclusion_versions',
    conclusion_version_id,'claim_versions',
    claim_version_id
      FROM scientific_conclusion_claim_inputs
      WHERE claim_version_id IS NOT NULL
 UNION ALL SELECT
    'scientific_conclusion_versions',
    conclusion_version_id,'literature_support_snapshots',
    literature_support_snapshot_id
      FROM scientific_conclusion_claim_inputs
      WHERE literature_support_snapshot_id IS NOT NULL
 UNION ALL SELECT
    'scientific_conclusion_versions',
    conclusion_version_id,'literature_evidence',literature_evidence_id
      FROM scientific_conclusion_literature_inputs
      WHERE literature_evidence_id IS NOT NULL
 UNION ALL SELECT 'claim_versions',claim_version_id,'measurements',measurement_id
      FROM evidence_relations
      WHERE measurement_id IS NOT NULL
 UNION ALL SELECT 'claim_versions',claim_version_id,'statistical_results',statistical_result_id
      FROM evidence_relations
      WHERE statistical_result_id IS NOT NULL
 UNION ALL SELECT 'statistical_results',statistical_result_id,'measurements',measurement_id
      FROM statistical_result_inputs
      WHERE measurement_id IS NOT NULL
 UNION ALL SELECT 'runs',run_id,'artifact_versions',artifact_version_id
      FROM run_artifact_inputs
      WHERE artifact_version_id IS NOT NULL
 UNION ALL SELECT 'runs',run_id,'dataset_snapshots',dataset_snapshot_id
      FROM run_dataset_inputs
      WHERE dataset_snapshot_id IS NOT NULL
 UNION ALL SELECT
    'literature_support_snapshots',
    literature_support_snapshot_id,'literature_evidence',literature_evidence_id
      FROM literature_evidence_relations
      WHERE literature_evidence_id IS NOT NULL
 UNION ALL SELECT 'measurements',id,'runs',run_id FROM measurements WHERE run_id IS NOT NULL
 UNION ALL SELECT 'measurements',id,'metric_definition_versions',metric_definition_version_id
      FROM measurements
      WHERE metric_definition_version_id IS NOT NULL
 UNION ALL SELECT 'runs',id,'experiment_spec_versions',experiment_spec_version_id
      FROM runs
      WHERE experiment_spec_version_id IS NOT NULL
 UNION ALL SELECT 'literature_evidence',id,'source_versions',source_version_id
      FROM literature_evidence
      WHERE source_version_id IS NOT NULL
 UNION ALL SELECT 'literature_support_snapshots',id,'claim_versions',claim_version_id
      FROM literature_support_snapshots
      WHERE claim_version_id IS NOT NULL
 UNION ALL SELECT
    'literature_support_snapshots',
    id,'literature_support_snapshots',
    previous_snapshot_id
      FROM literature_support_snapshots
      WHERE previous_snapshot_id IS NOT NULL
 UNION ALL SELECT 'source_versions',id,'artifact_versions',fulltext_artifact_version_id
      FROM source_versions
      WHERE fulltext_artifact_version_id IS NOT NULL
 UNION ALL SELECT 'source_versions',id,'source_versions',predecessor_source_version_id
      FROM source_versions
      WHERE predecessor_source_version_id IS NOT NULL
 UNION ALL SELECT 'source_versions',id,'artifact_versions',correction_basis_artifact_version_id
      FROM source_versions
      WHERE correction_basis_artifact_version_id IS NOT NULL),
          closure(kind,id) AS (SELECT seed_kind,target_id
            UNION SELECT e.child_kind,e.child_id FROM closure c JOIN edges e
              ON e.kind=c.kind AND e.id=c.id), authors AS (SELECT
    'artifact_versions'::text AS kind,
    id,created_by
    FROM artifact_versions
 UNION ALL SELECT 'artifacts'::text AS kind,id,created_by FROM artifacts
 UNION ALL SELECT 'claim_versions'::text AS kind,id,created_by FROM claim_versions
 UNION ALL SELECT 'claims'::text AS kind,id,created_by FROM claims
 UNION ALL SELECT 'dataset_snapshots'::text AS kind,id,created_by FROM dataset_snapshots
 UNION ALL SELECT 'datasets'::text AS kind,id,created_by FROM datasets
 UNION ALL SELECT 'experiment_spec_versions'::text
      AS kind, id,created_by
      FROM experiment_spec_versions
 UNION ALL SELECT 'experiment_specs'::text AS kind,id,created_by FROM experiment_specs
 UNION ALL SELECT 'literature_evidence'::text AS kind,id,created_by FROM literature_evidence
 UNION ALL SELECT 'literature_sources'::text AS kind,id,created_by FROM literature_sources
 UNION ALL SELECT 'literature_support_snapshots'::text
      AS kind, id,created_by
      FROM literature_support_snapshots
 UNION ALL SELECT 'measurements'::text AS kind,id,created_by FROM measurements
 UNION ALL SELECT 'metric_definition_versions'::text
      AS kind, id,created_by
      FROM metric_definition_versions
 UNION ALL SELECT 'metric_definitions'::text AS kind,id,created_by FROM metric_definitions
 UNION ALL SELECT 'runs'::text AS kind,id,created_by FROM runs
 UNION ALL SELECT 'scientific_conclusion_versions'::text
      AS kind, id,created_by
      FROM scientific_conclusion_versions
 UNION ALL SELECT 'scientific_conclusions'::text AS kind,id,created_by FROM scientific_conclusions
 UNION ALL SELECT 'source_versions'::text AS kind,id,created_by FROM source_versions
 UNION ALL SELECT 'statistical_results'::text AS kind,id,created_by FROM statistical_results
 UNION ALL SELECT 'claim_versions',claim_version_id,created_by FROM evidence_relations
 UNION ALL SELECT 'literature_support_snapshots',literature_support_snapshot_id,created_by
      FROM literature_evidence_relations )
          SELECT DISTINCT a.created_by FROM authors a JOIN closure c
            ON c.kind=a.kind AND c.id=a.id
$function$;
CREATE OR REPLACE FUNCTION public.b07_target(tid uuid, pid uuid, seed_kind text)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE cv claim_versions; v scientific_conclusion_versions; support TEXT; cs JSONB; ls JSONB;
BEGIN
  IF seed_kind NOT IN ('claim_versions','scientific_conclusion_versions') THEN
    RAISE EXCEPTION 'typed scientific target required' USING ERRCODE='P17F2'; END IF;
  PERFORM b07_facts(tid,pid,seed_kind);
  SELECT * INTO v FROM scientific_conclusion_versions WHERE id=tid AND seed_kind='scientific_conclusion_versions';
  IF v.id IS NOT NULL THEN
    IF v.status NOT IN ('FROZEN','SUPERSEDED') OR v.frozen_at IS NULL
      OR NOT EXISTS(SELECT 1 FROM scientific_conclusions WHERE id=v.scientific_conclusion_id AND project_id=pid) THEN
      RAISE EXCEPTION 'frozen same-project target required' USING ERRCODE='P17F2';
    END IF;
    SELECT coalesce(jsonb_agg(jsonb_build_object('claim_version',pr216_ref('ClaimVersion',c.id,c.content_hash),
      'literature_support_snapshot',pr216_ref('LiteratureSupportSnapshot',s.id,s.content_hash),
      'relation_type',b.relation_type,'ordinal',b.ordinal) ORDER BY b.ordinal),'[]'::jsonb) INTO cs
      FROM scientific_conclusion_claim_inputs b JOIN claim_versions c ON c.id=b.claim_version_id
      LEFT JOIN literature_support_snapshots s ON s.id=b.literature_support_snapshot_id WHERE b.conclusion_version_id=v.id;
    SELECT coalesce(jsonb_agg(jsonb_build_object('literature_evidence',pr216_ref('LiteratureEvidence',e.id,e.content_hash),
      'relation_type',b.relation_type,'ordinal',b.ordinal) ORDER BY b.ordinal),'[]'::jsonb) INTO ls
      FROM scientific_conclusion_literature_inputs b JOIN literature_evidence e ON e.id=b.literature_evidence_id
      WHERE b.conclusion_version_id=v.id;
    support:=pr216_hash(jsonb_build_object('type','ScientificConclusionVersionSupportSet','material_version',1,'claim_inputs',cs,'literature_inputs',ls));
    IF support IS DISTINCT FROM v.support_set_hash OR v.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object(
      'type','ScientificConclusionVersion','material_version',1,'scientific_conclusion_id',v.scientific_conclusion_id,
      'statement',v.statement,'scope',v.scope,'confidence',v.confidence,'limitation_summary',v.limitation_summary,'support_set_hash',support)) THEN
      RAISE EXCEPTION 'target hash invalid' USING ERRCODE='P17F2';
    END IF;
  END IF;
  FOR cv IN SELECT c.* FROM b07_closure(tid,seed_kind) x JOIN claim_versions c ON c.id=x.id WHERE x.kind='claim_versions' LOOP
    IF cv.status NOT IN ('FROZEN','SUPERSEDED') OR cv.frozen_at IS NULL
      OR NOT EXISTS(SELECT 1 FROM claims WHERE id=cv.claim_id AND project_id=pid)
      OR cv.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('statement',cv.statement,'scope',cv.scope,
        'qualification',cv.qualification,'support_set_hash',cv.support_set_hash))
      OR cv.support_set_hash IS DISTINCT FROM (SELECT pr216_hash(coalesce(jsonb_agg(jsonb_build_object(
        'source_type',CASE WHEN e.measurement_id IS NULL THEN 'statistical_result' ELSE 'measurement' END,
        'source_id',coalesce(e.measurement_id,e.statistical_result_id),'relation_type',lower(e.relation_type),
        'qualification',e.qualification) ORDER BY CASE WHEN e.measurement_id IS NULL THEN 'statistical_result' ELSE 'measurement' END,
        coalesce(e.measurement_id,e.statistical_result_id),lower(e.relation_type),e.qualification IS NOT NULL,coalesce(e.qualification,'')),'[]'::jsonb))
        FROM evidence_relations e WHERE e.claim_version_id=cv.id) THEN
      RAISE EXCEPTION 'claim material invalid' USING ERRCODE='P17F2';
    END IF;
  END LOOP;
  IF v.id IS NULL AND (seed_kind<>'claim_versions' OR NOT EXISTS(SELECT 1 FROM claim_versions WHERE id=tid)) THEN
    RAISE EXCEPTION 'exact scientific target required' USING ERRCODE='P17F2';
  END IF;
END $function$;
CREATE OR REPLACE FUNCTION public.b07_review(r internal_review_records)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE tid UUID; kind TEXT; digest TEXT;
BEGIN
  tid:=coalesce(r.claim_version_id,r.scientific_conclusion_version_id);
  kind:=CASE WHEN r.claim_version_id IS NOT NULL THEN 'ClaimVersion' ELSE 'ScientificConclusionVersion' END;
  PERFORM b07_target(tid,r.project_id,CASE WHEN r.claim_version_id IS NOT NULL THEN 'claim_versions' ELSE 'scientific_conclusion_versions' END);
  IF r.claim_version_id IS NOT NULL THEN SELECT content_hash INTO digest FROM claim_versions WHERE id=tid;
  ELSE SELECT content_hash INTO digest FROM scientific_conclusion_versions WHERE id=tid; END IF;
  IF r.created_at>clock_timestamp() OR r.target_content_hash IS DISTINCT FROM digest OR r.hash_scheme<>'sha256-cjson-v1'
    OR r.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','InternalReviewRecord','material_version',1,
      'project_id',r.project_id,'target',pr216_ref(kind,tid,digest),'reviewer_actor_id',r.reviewer_actor_id,
      'review_type',r.review_type,'recommendation',r.recommendation,'summary',r.summary))
    OR r.reviewer_actor_id IN (SELECT b07_authors(tid,CASE WHEN kind='ClaimVersion' THEN 'claim_versions' ELSE 'scientific_conclusion_versions' END)) OR NOT EXISTS(
      SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id
      JOIN project_role_assignments role ON role.membership_id=m.id AND role.actor_id=m.actor_id AND role.project_id=m.project_id
      WHERE a.id=r.reviewer_actor_id AND a.actor_type='HUMAN' AND a.created_at<=r.created_at
        AND (a.retired_at IS NULL OR r.created_at<a.retired_at) AND m.project_id=r.project_id AND m.started_at<=r.created_at
        AND role.role IN ('OWNER','REVIEWER') AND role.effective_from<=r.created_at AND (role.effective_until IS NULL OR r.created_at<role.effective_until)
        AND (SELECT e.new_status FROM project_membership_events e WHERE e.membership_id=m.id AND e.occurred_at<=r.created_at
          ORDER BY e.occurred_at DESC,e.id DESC LIMIT 1)='ACTIVE'
        AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=a.id AND b.bound_at<=r.created_at AND (b.revoked_at IS NULL OR r.created_at<b.revoked_at))) THEN
    RAISE EXCEPTION 'review material or authority invalid' USING ERRCODE='P17F2';
  END IF;
END $function$;
CREATE OR REPLACE FUNCTION public.b07_validate_decision(did uuid, complete_snapshot boolean)
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
END $function$;
CREATE OR REPLACE FUNCTION public.b07_validate_re_review(link revision_action_re_reviews, take_locks boolean)
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
END $function$;
CREATE OR REPLACE FUNCTION public.b08_validate_mapping(link revision_action_re_reviews, disposer uuid)
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
END $function$;
CREATE OR REPLACE FUNCTION public.b07_lock_concern(iid uuid)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE old internal_review_records;
BEGIN
  LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, audit_findings, claims, correction_records, datasets, experiment_spec_versions, experiment_specs, impact_assessments, impact_targets, internal_review_records, literature_evidence, literature_evidence_review_events, literature_source_project_links, literature_sources, metric_definition_versions, metric_definitions, project_membership_events, project_memberships, project_role_assignments, projects, runs, scientific_conclusions, source_versions IN SHARE MODE;
  SELECT r.* INTO old FROM review_issues i JOIN internal_review_records r ON r.id=i.review_record_id WHERE i.id=iid;
  PERFORM r.id FROM internal_review_records r WHERE r.project_id=old.project_id
    AND r.claim_version_id IS NOT DISTINCT FROM old.claim_version_id
    AND r.scientific_conclusion_version_id IS NOT DISTINCT FROM old.scientific_conclusion_version_id
    ORDER BY r.id FOR SHARE;
  PERFORM id FROM review_issues WHERE id=iid FOR UPDATE;
END $function$;
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
CREATE OR REPLACE FUNCTION public.b07_validate_revision(a revision_actions)
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
END $function$;
CREATE OR REPLACE FUNCTION public.b06_validate_revision(a revision_actions)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE concern review_issues; review internal_review_records; pid UUID;
  cs UUID[]; ms UUID[]; stats UUID[]; sources UUID[];
  cv claim_versions; sc scientific_conclusion_versions; spec experiment_spec_versions;
  execution runs; result statistical_results; source source_versions; previous source_versions;
  prior revision_actions; cursor_id UUID; visited UUID[] := ARRAY[a.id];
BEGIN
  IF a.decision_record_id IS NOT NULL OR a.review_issue_id IS NULL
    OR a.action_type NOT IN ('NEW_EXPERIMENT','ANALYSIS_CHANGE','CLAIM_CHANGE',
                            'CONCLUSION_CHANGE','SOURCE_CHANGE') THEN
    RAISE EXCEPTION 'revision path not contracted' USING ERRCODE='P17R1';
  END IF;
  SELECT * INTO concern FROM review_issues WHERE id=a.review_issue_id;
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
  IF pid IS NULL OR pid IS DISTINCT FROM review.project_id OR EXISTS (
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
  IF a.action_type='CLAIM_CHANGE' THEN
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
END $function$;
CREATE OR REPLACE FUNCTION public.b07_action_hash(a revision_actions)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
DECLARE results JSONB; d decision_records; prior revision_actions;
BEGIN
  SELECT * INTO d FROM decision_records WHERE id=a.decision_record_id;
  SELECT * INTO prior FROM revision_actions WHERE id=a.supersedes_revision_action_id;
  results:=jsonb_build_object(
    'result_experiment_spec_version',pr216_ref('ExperimentSpecVersion',a.result_experiment_spec_version_id,(SELECT content_hash FROM experiment_spec_versions WHERE id=a.result_experiment_spec_version_id)),
    'result_run',CASE WHEN a.result_run_id IS NULL THEN NULL ELSE jsonb_build_object('type','Run','id',a.result_run_id) END,
    'result_statistical_result',pr216_ref('StatisticalResult',a.result_statistical_result_id,(SELECT content_hash FROM statistical_results WHERE id=a.result_statistical_result_id)),
    'result_claim_version',pr216_ref('ClaimVersion',a.result_claim_version_id,(SELECT content_hash FROM claim_versions WHERE id=a.result_claim_version_id)),
    'result_scientific_conclusion_version',pr216_ref('ScientificConclusionVersion',a.result_scientific_conclusion_version_id,(SELECT content_hash FROM scientific_conclusion_versions WHERE id=a.result_scientific_conclusion_version_id)),
    'result_manuscript_version',NULL,
    'result_source_version',pr216_ref('SourceVersion',a.result_source_version_id,(SELECT content_hash FROM source_versions WHERE id=a.result_source_version_id)));
  RETURN pr216_hash(jsonb_build_object('type','RevisionAction','material_version',1,
    'review_issue',CASE WHEN a.review_issue_id IS NULL THEN NULL ELSE jsonb_build_object('type','ReviewIssue','id',a.review_issue_id) END,
    'decision',pr216_ref('DecisionRecord',d.id,d.content_hash),'action_type',a.action_type,'results',results,
    'supersedes_revision_action',pr216_ref('RevisionAction',prior.id,prior.content_hash),
    'created_by',jsonb_build_object('type','ActorIdentity','id',a.created_by)));
END $function$;
CREATE OR REPLACE FUNCTION public.b08_validate_event(e review_issue_events)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
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
END $function$;
CREATE OR REPLACE FUNCTION public.pr215_complete_basis()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
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
    END $function$;
CREATE OR REPLACE FUNCTION public.b11_manuscript_basis_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
BEGIN
 PERFORM b11_check_basis(NEW.decision_id,NEW.manuscript_version_id);
 RETURN NEW;
END $function$;
CREATE OR REPLACE FUNCTION public.b11_complete(did uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
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
END $function$;
CREATE OR REPLACE FUNCTION public.b12_approval_gate(r approval_requests, approver uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
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
END $function$;
CREATE OR REPLACE FUNCTION public.b14r_approval_gate(r approval_requests, approver uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
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
END $function$;
CREATE OR REPLACE FUNCTION public.b14_consumption_gate(r approval_requests, approver uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE m manuscript_versions; d decision_records; rr internal_review_records; iid UUID;
BEGIN
 IF r.approval_purpose IS DISTINCT FROM 'READY_FOR_SUBMISSION'
 OR r.manuscript_version_id IS NULL OR r.scientific_conclusion_version_id IS NOT NULL THEN
  RAISE EXCEPTION 'exact READY manuscript tuple required' USING ERRCODE='P16P1'; END IF;
 SELECT * INTO m FROM manuscript_versions WHERE id=r.manuscript_version_id;
 SELECT * INTO d FROM decision_records WHERE id=r.basis_decision_id;
 IF NOT EXISTS(SELECT 1 FROM projects WHERE id=r.project_id AND lifecycle_status='ACTIVE')
 OR NOT EXISTS(SELECT 1 FROM publications WHERE id=m.publication_id AND project_id=r.project_id
  AND (lifecycle_status='INTERNAL_REVIEW' OR (lifecycle_status='READY' AND xmin=pg_current_xact_id()::xid))) THEN
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
 PERFORM b14a_admission(m.id,r.project_id);
 PERFORM b14_material(m.id,r.project_id);
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
END $function$;
CREATE OR REPLACE FUNCTION public.b14a_admission(mid uuid, pid uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
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
END $function$;
CREATE OR REPLACE FUNCTION public.pr215_revision_guard()
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
END $function$;
CREATE OR REPLACE FUNCTION public.b07_revision_basis_guard()
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
END $function$;
CREATE OR REPLACE FUNCTION public.b08_event_guard()
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
END $function$;
DROP FUNCTION m1_admission_reviews(UUID,UUID);
DROP FUNCTION m1_manuscript(UUID,UUID);
CREATE OR REPLACE FUNCTION public.b14_verify_ready(pid uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE p publications; e publication_lifecycle_events; c approval_grant_consumptions; g approval_grants; d approval_decisions; r approval_requests; m manuscript_versions; ge approval_grant_events;
BEGIN
 SELECT * INTO p FROM publications WHERE id=pid;
 SELECT * INTO e FROM publication_lifecycle_events WHERE publication_id=pid AND new_status='READY';
 IF p.lifecycle_status<>'READY' THEN
  IF e.id IS NOT NULL THEN RAISE EXCEPTION 'orphan READY event' USING ERRCODE='P17F2'; END IF;
  RETURN;
 END IF;
 SELECT * INTO c FROM approval_grant_consumptions WHERE id=e.basis_grant_consumption_id;
 SELECT * INTO g FROM approval_grants WHERE id=c.grant_id;
 SELECT * INTO d FROM approval_decisions WHERE id=g.approval_decision_id;
 SELECT * INTO r FROM approval_requests WHERE id=d.approval_request_id;
 SELECT * INTO m FROM manuscript_versions WHERE id=r.manuscript_version_id;
 SELECT * INTO ge FROM approval_grant_events WHERE grant_id=g.id AND prior_status='ACTIVE';
 IF e.id IS NULL OR c.id IS NULL OR g.id IS NULL OR r.id IS NULL OR m.id IS NULL OR ge.id IS NULL
  OR e.prior_status IS DISTINCT FROM 'INTERNAL_REVIEW' OR e.manuscript_version_id IS NOT NULL
  OR c.command<>'TRANSITION_PUBLICATION_READY' OR g.purpose<>'READY_FOR_SUBMISSION'
  OR g.allowed_command<>'transition_publication_ready' OR g.status<>'CONSUMED'
  OR c.project_id IS DISTINCT FROM p.project_id OR g.project_id IS DISTINCT FROM p.project_id OR r.project_id IS DISTINCT FROM p.project_id
  OR c.result_publication_id IS DISTINCT FROM pid OR m.publication_id IS DISTINCT FROM pid
  OR p.current_manuscript_version_id IS DISTINCT FROM m.id OR m.content_hash IS DISTINCT FROM r.target_content_hash
  OR m.hash_scheme IS DISTINCT FROM r.target_hash_scheme
  OR e.basis_decision_id IS DISTINCT FROM r.basis_decision_id
  OR e.actor_id IS DISTINCT FROM c.actor_id OR e.occurred_at IS DISTINCT FROM c.consumed_at
  OR ge.actor_id IS DISTINCT FROM c.actor_id OR ge.occurred_at IS DISTINCT FROM c.consumed_at OR ge.new_status<>'CONSUMED'
  OR NOT EXISTS(SELECT 1 FROM publication_lifecycle_events WHERE publication_id=pid AND new_status='INTERNAL_REVIEW' AND manuscript_version_id=m.id AND occurred_at<=e.occurred_at)
  OR (SELECT count(*) FROM publication_lifecycle_events WHERE publication_id=pid)<>3 THEN
  RAISE EXCEPTION 'complete READY graph required' USING ERRCODE='P17F2'; END IF;
 PERFORM b14r_saved_decision(r.basis_decision_id,m.id,p.project_id);
 IF EXISTS(SELECT 1 FROM approval_grant_consumptions WHERE id=c.id AND xmin=pg_current_xact_id()::xid)
 OR EXISTS(SELECT 1 FROM publication_lifecycle_events WHERE id=e.id AND xmin=pg_current_xact_id()::xid)
 OR EXISTS(SELECT 1 FROM publications WHERE id=pid AND xmin=pg_current_xact_id()::xid) THEN
  IF NOT EXISTS(SELECT 1 FROM publications WHERE id=pid AND xmin=pg_current_xact_id()::xid)
  OR NOT EXISTS(SELECT 1 FROM approval_grant_consumptions WHERE id=c.id AND xmin=pg_current_xact_id()::xid)
  OR NOT EXISTS(SELECT 1 FROM publication_lifecycle_events WHERE id=e.id AND xmin=pg_current_xact_id()::xid)
  OR NOT EXISTS(SELECT 1 FROM approval_grant_events WHERE id=ge.id AND xmin=pg_current_xact_id()::xid)
  OR NOT EXISTS(SELECT 1 FROM approval_grants WHERE id=g.id AND xmin=pg_current_xact_id()::xid) THEN
   RAISE EXCEPTION 'same transaction READY graph required' USING ERRCODE='P14I1'; END IF;
  PERFORM b13_preheld(true);
 END IF;
END $function$;
CREATE OR REPLACE FUNCTION public.b04_check_manuscript_closure()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
    BEGIN PERFORM b04_verify_structure(NEW.id); RETURN NULL; END $function$;
"""


def upgrade() -> None:
    op.execute(_UPGRADE)


def downgrade() -> None:
    op.execute(_DOWNGRADE)
