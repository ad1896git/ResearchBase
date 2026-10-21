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
END $function$
