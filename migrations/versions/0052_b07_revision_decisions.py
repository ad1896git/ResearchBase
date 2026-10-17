"""B07 approved revision choices and immutable concern/re-review relations."""

# Literal forward SQL preserves accepted release guards and B06 result checks.
# ruff: noqa: E501

from alembic import op

revision = "0052_b07_revision_decisions"
down_revision = "0051_b06_revision_action"
branch_labels = None
depends_on = None

_INVENTORY = "actor_subject_bindings, actors, artifact_versions, artifacts, audit_findings, claims, correction_records, datasets, experiment_spec_versions, experiment_specs, impact_assessments, impact_targets, internal_review_records, literature_evidence, literature_evidence_review_events, literature_source_project_links, literature_sources, metric_definition_versions, metric_definitions, project_membership_events, project_memberships, project_role_assignments, projects, runs, scientific_conclusions, source_versions"

_LOCKS = r"""
CREATE FUNCTION b07_lock_concern(iid UUID) RETURNS void LANGUAGE plpgsql AS $$
DECLARE old internal_review_records;
BEGIN
  LOCK TABLE INVENTORY IN SHARE MODE;
  SELECT r.* INTO old FROM review_issues i JOIN internal_review_records r ON r.id=i.review_record_id WHERE i.id=iid;
  PERFORM r.id FROM internal_review_records r WHERE r.project_id=old.project_id
    AND r.claim_version_id IS NOT DISTINCT FROM old.claim_version_id
    AND r.scientific_conclusion_version_id IS NOT DISTINCT FROM old.scientific_conclusion_version_id
    ORDER BY r.id FOR SHARE;
  PERFORM id FROM review_issues WHERE id=iid FOR UPDATE;
END $$;
"""

_VALIDATE = r"""
CREATE FUNCTION b07_validate_revision(a revision_actions) RETURNS void LANGUAGE plpgsql AS $$
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
      OR EXISTS (SELECT 1 FROM decision_records WHERE id=chosen_decision.id AND xmin::text::bigint=pg_current_xact_id()::text::bigint) THEN
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
END $$;
"""

AUTHORS_SQL = r"""
CREATE FUNCTION b07_authors(target_id UUID,seed_kind TEXT) RETURNS SETOF UUID LANGUAGE SQL STABLE
      SET search_path = pg_catalog, public, pg_temp AS $$
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
$$;"""

CLOSURE_SQL = r"""
CREATE FUNCTION b07_closure(target_id UUID,seed_kind TEXT) RETURNS TABLE(kind TEXT,id UUID)
 LANGUAGE SQL STABLE
      SET search_path = pg_catalog, public, pg_temp AS $$
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
$$;
"""

_FACTS = r"""    CREATE FUNCTION b07_facts(target UUID,pid UUID,seed_kind TEXT) RETURNS void LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE node RECORD; row JSONB; material JSONB; expected TEXT; numerical DOUBLE PRECISION;
      input_set JSONB; bound JSONB; previous JSONB; artifact JSONB; correction JSONB;
    BEGIN
      -- Closed inventory only. These are typed graph queries, never stored soft references.
      FOR node IN SELECT * FROM b07_closure(target,seed_kind) WHERE kind IN (
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
                AND (p.project_id IS NULL OR p.project_id=pid)) THEN
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
    END $$;
"""

_TARGET = r"""
CREATE FUNCTION b07_target(tid UUID,pid UUID,seed_kind TEXT) RETURNS void LANGUAGE plpgsql AS $$
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
END $$;

CREATE FUNCTION b07_review(r internal_review_records) RETURNS void LANGUAGE plpgsql AS $$
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
END $$;

CREATE FUNCTION b07_validate_decision(did UUID, complete_snapshot BOOLEAN) RETURNS void LANGUAGE plpgsql AS $$
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
    IF (complete_snapshot AND EXISTS(SELECT 1 FROM internal_review_records WHERE id=ref.id AND xmin::text::bigint=pg_current_xact_id()::text::bigint))
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
END $$;
"""
_CURRENT = r"""
CREATE FUNCTION b07_current_snapshot(sid UUID,pid UUID) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM literature_evidence_relations rel JOIN literature_evidence e ON e.id=rel.literature_evidence_id
   JOIN literature_support_snapshots snapshot ON snapshot.id=rel.literature_support_snapshot_id
   JOIN source_versions s ON s.id=e.source_version_id JOIN literature_sources p ON p.id=s.literature_source_id
   LEFT JOIN source_versions current ON current.id=p.current_version_id
   WHERE rel.literature_support_snapshot_id=sid AND (s.version_kind='RETRACTED' OR current.version_kind='RETRACTED'
     OR (current.version_kind='CORRECTED' AND current.id<>s.id) OR e.review_status IN ('DISPUTED','REJECTED')
     OR (rel.relation_type='SUPPORTS' AND (e.review_status<>'VERIFIED' OR NOT EXISTS(
       SELECT 1 FROM literature_evidence_review_events event JOIN actors actor ON actor.id=event.reviewed_by
       WHERE event.id=(SELECT latest.id FROM literature_evidence_review_events latest WHERE latest.literature_evidence_id=e.id ORDER BY latest.reviewed_at DESC,latest.id DESC LIMIT 1)
         AND event.new_status='VERIFIED' AND actor.actor_type='HUMAN' AND event.reviewed_by<>e.created_by AND event.reviewed_by<>snapshot.created_by))))) THEN
   RAISE EXCEPTION 'current support witness invalid' USING ERRCODE='P17F2'; END IF;
END $$;
CREATE FUNCTION b07_current_target(tid UUID,pid UUID,seed_kind TEXT) RETURNS void LANGUAGE plpgsql AS $$
DECLARE node RECORD; sid UUID;
BEGIN
 FOR node IN SELECT kind,id FROM b07_closure(tid,seed_kind) WHERE kind IN ('claim_versions','scientific_conclusion_versions','measurements','statistical_results','runs','experiment_spec_versions','metric_definition_versions','artifact_versions','dataset_snapshots') LOOP
  IF EXISTS(SELECT 1 FROM correction_records WHERE project_id=pid AND lower(target_type)=left(node.kind,length(node.kind)-1) AND target_id=node.id)
    OR EXISTS(SELECT 1 FROM impact_targets t JOIN impact_assessments a ON a.id=t.impact_assessment_id
      LEFT JOIN audit_findings f ON f.id=a.audit_finding_id WHERE a.project_id=pid
      AND lower(t.target_type)=left(node.kind,length(node.kind)-1) AND t.target_id=node.id
      AND lower(f.status) IS DISTINCT FROM 'dismissed' AND lower(a.conclusion)<>'no_impact') THEN
    RAISE EXCEPTION 'current scientific target invalid' USING ERRCODE='P17F2'; END IF;
 END LOOP;
 FOR sid IN SELECT literature_support_snapshot_id FROM scientific_conclusion_claim_inputs WHERE seed_kind='scientific_conclusion_versions' AND conclusion_version_id=tid AND literature_support_snapshot_id IS NOT NULL LOOP
   PERFORM b07_current_snapshot(sid,pid);
 END LOOP;
 IF EXISTS(SELECT 1 FROM scientific_conclusion_literature_inputs rel JOIN literature_evidence e ON e.id=rel.literature_evidence_id
   JOIN source_versions s ON s.id=e.source_version_id JOIN literature_sources p ON p.id=s.literature_source_id LEFT JOIN source_versions current ON current.id=p.current_version_id
   WHERE seed_kind='scientific_conclusion_versions' AND rel.conclusion_version_id=tid AND (s.version_kind='RETRACTED' OR current.version_kind='RETRACTED' OR (current.version_kind='CORRECTED' AND current.id<>s.id)
     OR e.review_status IN ('DISPUTED','REJECTED') OR (rel.relation_type='SUPPORTS' AND e.review_status<>'VERIFIED'))) THEN
   RAISE EXCEPTION 'current literature target invalid' USING ERRCODE='P17F2'; END IF;
END $$;
"""

_RELATION = r"""
CREATE FUNCTION b07_validate_re_review(link revision_action_re_reviews, take_locks BOOLEAN) RETURNS void LANGUAGE plpgsql AS $$
DECLARE attestation internal_review_records; a revision_actions; old internal_review_records; r internal_review_records; iid UUID; tid UUID; old_tid UUID; cs UUID[]; old_cv claim_versions; old_sc scientific_conclusion_versions; good BOOLEAN; witness UUID; old_witness UUID; candidate UUID;
BEGIN
  SELECT * INTO a FROM revision_actions WHERE id=link.revision_action_id;
  IF a.id IS NULL THEN RAISE EXCEPTION 'exact action required' USING ERRCODE='P17F2'; END IF;
  SELECT coalesce(a.review_issue_id,c.review_issue_id) INTO iid FROM (SELECT 1) x LEFT JOIN decision_revision_concerns c ON c.decision_id=a.decision_record_id;
  SELECT r0.* INTO old FROM review_issues i JOIN internal_review_records r0 ON r0.id=i.review_record_id WHERE i.id=iid;
  SELECT * INTO r FROM internal_review_records WHERE id=link.internal_review_record_id;
  IF take_locks THEN
    LOCK TABLE INVENTORY IN SHARE MODE;
    PERFORM id FROM internal_review_records WHERE id IN (old.id,r.id) ORDER BY id FOR SHARE;
    PERFORM id FROM review_issues WHERE id=iid FOR SHARE;
    PERFORM id FROM revision_actions WHERE id=a.id FOR UPDATE;
  END IF;
  IF EXISTS(SELECT 1 FROM revision_actions WHERE supersedes_revision_action_id=a.id) THEN
    RAISE EXCEPTION 'action superseded' USING ERRCODE='P17R1'; END IF;
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
END $$;

CREATE FUNCTION b07_re_review_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  LOCK TABLE INVENTORY IN SHARE MODE;
  PERFORM b07_validate_re_review(NEW,true);
  RETURN NEW;
END $$;
CREATE FUNCTION b07_complete_re_review_fn() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  -- Admission locks and mutable facts are protected through commit by BEFORE.
  -- Revalidate closure/current validity without acquiring admission locks again.
  PERFORM b07_validate_re_review(NEW,false);
  RETURN NULL;
END $$;
CREATE TRIGGER b07_re_review_guard BEFORE INSERT ON revision_action_re_reviews FOR EACH ROW EXECUTE FUNCTION b07_re_review_guard();
CREATE CONSTRAINT TRIGGER b07_complete_re_review AFTER INSERT ON revision_action_re_reviews DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b07_complete_re_review_fn();
"""

_DDL = r"""
ALTER TABLE decision_records DROP CONSTRAINT decision_records_decision_type_check, DROP CONSTRAINT decision_records_decision_check;
ALTER TABLE decision_records ADD CONSTRAINT ck_b07_decision_tuple CHECK (
 (decision_type='INTERNAL_SCIENTIFIC_RELEASE' AND decision='PROCEED') OR
 (decision_type='REVISION_RESPONSE' AND decision IN ('REQUIRE_CHANGE','ACCEPT_NO_CHANGE')));
CREATE TABLE decision_basis_claims (
 decision_id UUID NOT NULL REFERENCES decision_records(id) ON DELETE RESTRICT,
 claim_version_id UUID NOT NULL REFERENCES claim_versions(id) ON DELETE RESTRICT,
 ordinal INT NOT NULL CONSTRAINT ck_b07_claim_ordinal CHECK(ordinal>=0),
 CONSTRAINT pk_b07_basis_claim PRIMARY KEY(decision_id,claim_version_id),
 CONSTRAINT uq_b07_claim_target UNIQUE(decision_id), CONSTRAINT uq_b07_claim_ordinal UNIQUE(decision_id,ordinal));
CREATE INDEX ix_b07_claim_basis_target ON decision_basis_claims(claim_version_id);
CREATE TABLE decision_revision_concerns (
 decision_id UUID CONSTRAINT pk_b07_decision_concern PRIMARY KEY REFERENCES decision_records(id) ON DELETE RESTRICT,
 review_issue_id UUID NOT NULL REFERENCES review_issues(id) ON DELETE RESTRICT,
 CONSTRAINT uq_b07_decision_concern UNIQUE(review_issue_id));
CREATE TABLE revision_action_re_reviews (
 revision_action_id UUID NOT NULL REFERENCES revision_actions(id) ON DELETE RESTRICT,
 internal_review_record_id UUID NOT NULL REFERENCES internal_review_records(id) ON DELETE RESTRICT,
 recorded_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
 recorded_at TIMESTAMPTZ NOT NULL,
 CONSTRAINT pk_b07_action_re_review PRIMARY KEY(revision_action_id,internal_review_record_id));
CREATE INDEX ix_b07_re_review_target ON revision_action_re_reviews(internal_review_record_id);
CREATE TRIGGER b07_claim_basis_immutable BEFORE UPDATE OR DELETE ON decision_basis_claims FOR EACH ROW EXECUTE FUNCTION pr215_immutable();
CREATE TRIGGER b07_decision_concern_immutable BEFORE UPDATE OR DELETE ON decision_revision_concerns FOR EACH ROW EXECUTE FUNCTION pr215_immutable();
CREATE TRIGGER b07_re_review_immutable BEFORE UPDATE OR DELETE ON revision_action_re_reviews FOR EACH ROW EXECUTE FUNCTION pr215_immutable();
"""

_DISPATCH = r"""    CREATE OR REPLACE FUNCTION pr215_basis_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE target_id UUID; target_project UUID; parent_xmin bigint;
      decision_project UUID; target_status TEXT; target_hash TEXT;
    BEGIN
      IF (SELECT decision_type FROM decision_records WHERE id=NEW.decision_id)='REVISION_RESPONSE' THEN
        LOCK TABLE INVENTORY IN SHARE MODE;
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
_ACTION = r"""
CREATE FUNCTION b07_action_hash(a revision_actions) RETURNS TEXT LANGUAGE plpgsql AS $$
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
END $$;
CREATE OR REPLACE FUNCTION pr215_revision_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE concern review_issues; prior revision_actions; effective UUID;
BEGIN
  IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'revision history immutable' USING ERRCODE='P17F1'; END IF;
  LOCK TABLE INVENTORY IN SHARE MODE;
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
END $$;
CREATE OR REPLACE FUNCTION b06_complete_revision() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE saved revision_actions;
BEGIN
  SELECT * INTO saved FROM revision_actions WHERE id=NEW.id;
  PERFORM b07_validate_revision(saved);
  IF saved.content_hash IS DISTINCT FROM b07_action_hash(saved) THEN
    RAISE EXCEPTION 'action hash invalid' USING ERRCODE='P17F2'; END IF;
  RETURN NULL;
END $$;
CREATE FUNCTION b07_revision_basis_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE purpose TEXT;
BEGIN
  LOCK TABLE INVENTORY IN SHARE MODE;
  SELECT decision_type INTO purpose FROM decision_records WHERE id=NEW.decision_id;
  IF purpose IS DISTINCT FROM 'REVISION_RESPONSE' THEN RAISE EXCEPTION 'revision purpose required' USING ERRCODE='P17F2'; END IF;
  IF NOT EXISTS(SELECT 1 FROM decision_records WHERE id=NEW.decision_id AND xmin::text::bigint=pg_current_xact_id()::text::bigint) THEN
    RAISE EXCEPTION 'basis sealed to creation transaction' USING ERRCODE='P17F1'; END IF;
  IF TG_TABLE_NAME='decision_revision_concerns' THEN
    PERFORM b07_lock_concern(NEW.review_issue_id);
  ELSE
    PERFORM id FROM internal_review_records WHERE claim_version_id=NEW.claim_version_id ORDER BY id FOR SHARE;
    PERFORM b07_lock_concern(review_issue_id) FROM decision_revision_concerns WHERE decision_id=NEW.decision_id;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER b07_revision_basis_guard BEFORE INSERT ON decision_basis_claims FOR EACH ROW EXECUTE FUNCTION b07_revision_basis_guard();
CREATE TRIGGER b07_concern_guard BEFORE INSERT ON decision_revision_concerns FOR EACH ROW EXECUTE FUNCTION b07_revision_basis_guard();
CREATE CONSTRAINT TRIGGER b07_complete_decision AFTER INSERT ON decision_records DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pr215_complete_basis();
CREATE CONSTRAINT TRIGGER b07_complete_claim AFTER INSERT ON decision_basis_claims DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pr215_complete_basis();
CREATE CONSTRAINT TRIGGER b07_complete_concern AFTER INSERT ON decision_revision_concerns DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pr215_complete_basis();
"""


def upgrade() -> None:
    op.execute(
        "LOCK TABLE decision_records,decision_basis_conclusions,decision_basis_reviews,revision_actions IN ACCESS EXCLUSIVE MODE"
    )
    op.execute("LOCK TABLE " + _INVENTORY + " IN SHARE MODE")
    op.execute(_DDL)
    op.execute(AUTHORS_SQL)
    op.execute(CLOSURE_SQL)
    op.execute(_FACTS)
    op.execute(_TARGET)
    op.execute(_CURRENT)
    op.execute(_LOCKS.replace("INVENTORY", _INVENTORY))
    op.execute(_VALIDATE)
    op.execute(_DISPATCH.replace("INVENTORY", _INVENTORY))
    op.execute(_ACTION.replace("INVENTORY", _INVENTORY))
    op.execute(_RELATION.replace("INVENTORY", _INVENTORY))
    op.execute("""
    DO $$ DECLARE a revision_actions; d decision_records; r internal_review_records;
      target UUID; digest TEXT; basis JSONB; n INT;
    BEGIN
      -- Historical release validation never reapplies today's blocker/current-validity gate
      -- or compares the saved basis with reviews committed after the Decision.
      FOR d IN SELECT * FROM decision_records LOOP
        SELECT b.scientific_conclusion_version_id,v.content_hash INTO target,digest
          FROM decision_basis_conclusions b JOIN scientific_conclusion_versions v
          ON v.id=b.scientific_conclusion_version_id WHERE b.decision_id=d.id;
        IF target IS NULL OR d.decision_type<>'INTERNAL_SCIENTIFIC_RELEASE' OR d.decision<>'PROCEED'
          OR d.supersedes_decision_id IS NOT NULL OR NOT pr216_decision_authorized(d)
          OR d.decided_by IN (SELECT b07_authors(target,'scientific_conclusion_versions')) THEN
          RAISE EXCEPTION 'retained release basis invalid' USING ERRCODE='P17F2'; END IF;
        PERFORM b07_target(target,d.project_id,'scientific_conclusion_versions');
        FOR r IN SELECT x.* FROM decision_basis_reviews b JOIN internal_review_records x
          ON x.id=b.internal_review_record_id WHERE b.decision_id=d.id LOOP
          IF r.project_id<>d.project_id OR r.scientific_conclusion_version_id IS DISTINCT FROM target
            OR r.claim_version_id IS NOT NULL OR r.target_content_hash IS DISTINCT FROM digest
            OR r.created_at>d.decided_at THEN
            RAISE EXCEPTION 'retained release review invalid' USING ERRCODE='P17F2'; END IF;
          PERFORM b07_review(r);
        END LOOP;
        SELECT jsonb_agg(jsonb_build_object('target',pr216_ref(kind,id,hash),'ordinal',ordinal)
          ORDER BY kind,id,hash),count(*) INTO basis,n FROM (
          SELECT 'ScientificConclusionVersion' AS kind,b.scientific_conclusion_version_id AS id,
            v.content_hash AS hash,b.ordinal FROM decision_basis_conclusions b
            JOIN scientific_conclusion_versions v ON v.id=b.scientific_conclusion_version_id WHERE b.decision_id=d.id
          UNION ALL SELECT 'InternalReviewRecord',b.internal_review_record_id,v.content_hash,b.ordinal
            FROM decision_basis_reviews b JOIN internal_review_records v ON v.id=b.internal_review_record_id
            WHERE b.decision_id=d.id) refs;
        IF n<2 OR EXISTS(SELECT 1 FROM jsonb_array_elements(basis) WITH ORDINALITY x(value,pos)
          WHERE (value->>'ordinal')::int<>pos-1)
          OR d.basis_set_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','DecisionRecordBasisSet','material_version',1,'basis',basis))
          OR d.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','DecisionRecord','material_version',1,
            'project_id',d.project_id,'decision_type',d.decision_type,'question',d.question,'decision',d.decision,
            'rationale',d.rationale,'decided_by',jsonb_build_object('type','ActorIdentity','id',d.decided_by),
            'supersedes_decision_id',NULL,'basis_set_hash',d.basis_set_hash)) THEN
          RAISE EXCEPTION 'retained release hash invalid' USING ERRCODE='P17F2'; END IF;
      END LOOP;
      FOR a IN SELECT * FROM revision_actions LOOP
        PERFORM b07_validate_revision(a);
        IF a.content_hash IS DISTINCT FROM b07_action_hash(a) THEN
          RAISE EXCEPTION 'retained action hash invalid' USING ERRCODE='P17F2'; END IF;
      END LOOP;
    END $$;
    """)


def downgrade() -> None:
    op.execute("""
    LOCK TABLE decision_basis_claims,decision_basis_conclusions,decision_basis_reviews,decision_records,decision_revision_concerns,revision_action_re_reviews,revision_actions IN ACCESS EXCLUSIVE MODE;
    DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM decision_records WHERE decision_type='REVISION_RESPONSE')
        OR EXISTS(SELECT 1 FROM decision_basis_claims) OR EXISTS(SELECT 1 FROM decision_revision_concerns)
        OR EXISTS(SELECT 1 FROM revision_action_re_reviews) THEN
        RAISE EXCEPTION 'B07 history cannot be stranded' USING ERRCODE='P17F2'; END IF;
    END $$;
    DROP TRIGGER b07_complete_decision ON decision_records;
    DROP TRIGGER b07_complete_claim ON decision_basis_claims;
    DROP TRIGGER b07_complete_concern ON decision_revision_concerns;
    DROP FUNCTION b07_validate_re_review(revision_action_re_reviews,boolean);
    DROP TABLE revision_action_re_reviews;
    DROP TABLE decision_revision_concerns;
    DROP TABLE decision_basis_claims;
    DROP FUNCTION b07_complete_re_review_fn();
    DROP FUNCTION b07_re_review_guard();
    """)
    op.execute(_RESTORE_DECISION)
    op.execute(_RESTORE_REVISION)
    op.execute("""
    DROP FUNCTION b07_revision_basis_guard();
    DROP FUNCTION b07_validate_revision(revision_actions);
    DROP FUNCTION b07_action_hash(revision_actions);
    DROP FUNCTION b07_validate_decision(UUID,boolean);
    DROP FUNCTION b07_lock_concern(UUID);
    DROP FUNCTION b07_review(internal_review_records);
    DROP FUNCTION b07_current_target(UUID,UUID,TEXT);
    DROP FUNCTION b07_current_snapshot(UUID,UUID);
    DROP FUNCTION b07_target(UUID,UUID,TEXT);
    DROP FUNCTION b07_facts(UUID,UUID,TEXT);
    DROP FUNCTION b07_closure(UUID,TEXT);
    DROP FUNCTION b07_authors(UUID,TEXT);
    ALTER TABLE decision_records DROP CONSTRAINT ck_b07_decision_tuple;
    ALTER TABLE decision_records ADD CONSTRAINT decision_records_decision_type_check CHECK(decision_type='INTERNAL_SCIENTIFIC_RELEASE'),
      ADD CONSTRAINT decision_records_decision_check CHECK(decision='PROCEED');
    """)


_RESTORE_DECISION = r"""    CREATE OR REPLACE FUNCTION pr215_basis_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE target_id UUID; target_project UUID; parent_xmin bigint;
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

_RESTORE_REVISION = r"""    CREATE OR REPLACE FUNCTION pr215_revision_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE concern review_issues; prior revision_actions;
    BEGIN
      IF TG_OP<>'INSERT' THEN
        RAISE EXCEPTION 'revision history is immutable' USING ERRCODE='P17F1';
      END IF;
      LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, audit_findings, claims, correction_records, datasets, experiment_spec_versions, experiment_specs, impact_assessments, impact_targets, literature_evidence, literature_evidence_review_events, literature_source_project_links, literature_sources, metric_definition_versions, metric_definitions, project_membership_events, project_memberships, project_role_assignments, projects, runs, scientific_conclusions, source_versions IN SHARE MODE;
      SELECT * INTO concern FROM review_issues WHERE id=NEW.review_issue_id;
      PERFORM id FROM internal_review_records WHERE id=concern.review_record_id FOR SHARE;
      PERFORM id FROM review_issues WHERE id=concern.id FOR SHARE;
      IF NEW.supersedes_revision_action_id IS NOT NULL THEN
        SELECT * INTO prior FROM revision_actions WHERE id=NEW.supersedes_revision_action_id FOR UPDATE;
        IF EXISTS (SELECT 1 FROM revision_actions WHERE supersedes_revision_action_id=prior.id) THEN
          RAISE EXCEPTION 'predecessor already superseded' USING ERRCODE='P17R1';
        END IF;
      END IF;
      PERFORM b06_validate_revision(NEW);
      RETURN NEW;
    END $$;
    CREATE OR REPLACE FUNCTION b06_complete_revision() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE saved revision_actions;
    BEGIN
      SELECT * INTO saved FROM revision_actions WHERE id=NEW.id;
      PERFORM b06_validate_revision(saved);
      RETURN NULL;
    END $$;

"""
