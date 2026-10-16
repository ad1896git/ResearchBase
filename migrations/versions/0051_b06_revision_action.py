"""Owner-approved B06 issue-only completed results; no result or Issue mutation."""

# The frozen SQL inventory and restoration body intentionally retain literal SQL.
# ruff: noqa: E501

from alembic import op

revision = "0051_b06_revision_action"
down_revision = "0050_b01_resolution_admission"
branch_labels = None
depends_on = None

# Literal reviewed B inventory; revision_actions and frozen Claim/conclusion rows excluded.
_INVENTORY = "actor_subject_bindings, actors, artifact_versions, artifacts, audit_findings, claims, correction_records, datasets, experiment_spec_versions, experiment_specs, impact_assessments, impact_targets, literature_evidence, literature_evidence_review_events, literature_source_project_links, literature_sources, metric_definition_versions, metric_definitions, project_membership_events, project_memberships, project_role_assignments, projects, runs, scientific_conclusions, source_versions"

_VALIDATE = r"""
CREATE FUNCTION b06_validate_revision(a revision_actions) RETURNS void LANGUAGE plpgsql AS $$
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
END $$;
"""


def upgrade() -> None:
    op.execute("LOCK TABLE revision_actions IN ACCESS EXCLUSIVE MODE")
    op.execute("LOCK TABLE " + _INVENTORY + " IN SHARE MODE")
    op.execute(_VALIDATE)
    # No rewritten history: fail preflight on inconsistent retained structural closure.
    op.execute("""
    DO $$ DECLARE a revision_actions; BEGIN
      FOR a IN SELECT * FROM revision_actions LOOP PERFORM b06_validate_revision(a); END LOOP;
    END $$;
    """)
    op.execute(
        """
    CREATE OR REPLACE FUNCTION pr215_revision_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE concern review_issues; prior revision_actions;
    BEGIN
      IF TG_OP<>'INSERT' THEN
        RAISE EXCEPTION 'revision history is immutable' USING ERRCODE='P17F1';
      END IF;
      LOCK TABLE """
        + _INVENTORY
        + """ IN SHARE MODE;
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
    CREATE FUNCTION b06_complete_revision() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE saved revision_actions;
    BEGIN
      SELECT * INTO saved FROM revision_actions WHERE id=NEW.id;
      PERFORM b06_validate_revision(saved);
      RETURN NULL;
    END $$;
    CREATE CONSTRAINT TRIGGER b06_revision_complete AFTER INSERT ON revision_actions
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b06_complete_revision();
    """
    )


def downgrade() -> None:
    op.execute("""
    LOCK TABLE revision_actions IN ACCESS EXCLUSIVE MODE;
    DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM revision_actions a JOIN review_issues i ON i.id=a.review_issue_id
        JOIN internal_review_records r ON r.id=i.review_record_id
        WHERE a.decision_record_id IS NOT NULL OR a.action_type NOT IN ('CLAIM_CHANGE','CONCLUSION_CHANGE')
          OR (a.action_type='CLAIM_CHANGE' AND r.claim_version_id IS NULL)
          OR (a.action_type='CONCLUSION_CHANGE' AND r.scientific_conclusion_version_id IS NULL)) THEN
        RAISE EXCEPTION 'new revision history cannot be stranded' USING ERRCODE='P17F2';
      END IF;
    END $$;
    DROP TRIGGER b06_revision_complete ON revision_actions;
    DROP FUNCTION b06_complete_revision();
    """)
    op.execute(_RESTORE)
    op.execute("DROP FUNCTION b06_validate_revision(revision_actions)")


_RESTORE = r"""
    CREATE OR REPLACE FUNCTION pr215_revision_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE concern review_issues; review internal_review_records;
      old_claim claim_versions; new_claim claim_versions;
      old_conclusion scientific_conclusion_versions; new_conclusion scientific_conclusion_versions;
      predecessor revision_actions; pid UUID; result_project UUID;
    BEGIN
      IF TG_OP<>'INSERT' THEN
        RAISE EXCEPTION 'revision history is immutable' USING ERRCODE='P17F1';
      END IF;
      IF NEW.decision_record_id IS NOT NULL OR NEW.review_issue_id IS NULL
        OR NEW.action_type NOT IN ('CLAIM_CHANGE','CONCLUSION_CHANGE') THEN
        RAISE EXCEPTION 'revision path not contracted' USING ERRCODE='P17R1';
      END IF;
      SELECT * INTO concern FROM review_issues WHERE id=NEW.review_issue_id;
      SELECT * INTO review FROM internal_review_records WHERE id=concern.review_record_id;
      IF review.id IS NULL THEN
        RAISE EXCEPTION 'exact issue basis required' USING ERRCODE='P17F2';
      END IF;
      -- Same target-before-parent protocol as Decision and conclusion Review writers.
      IF review.claim_version_id IS NOT NULL THEN
        SELECT * INTO old_claim FROM claim_versions WHERE id=review.claim_version_id FOR UPDATE;
        SELECT project_id INTO pid FROM claims WHERE id=old_claim.claim_id;
      ELSE
        SELECT * INTO old_conclusion FROM scientific_conclusion_versions
          WHERE id=review.scientific_conclusion_version_id FOR UPDATE;
        SELECT project_id INTO pid FROM scientific_conclusions
          WHERE id=old_conclusion.scientific_conclusion_id;
      END IF;
      IF pid IS DISTINCT FROM review.project_id THEN
        RAISE EXCEPTION 'same-project basis required' USING ERRCODE='P17F2';
      END IF;
      PERFORM id FROM internal_review_records WHERE id=review.id FOR SHARE;
      PERFORM id FROM review_issues WHERE id=concern.id FOR SHARE;
      IF NEW.action_type='CLAIM_CHANGE' THEN
        SELECT * INTO new_claim FROM claim_versions WHERE id=NEW.result_claim_version_id;
        SELECT project_id INTO result_project FROM claims WHERE id=new_claim.claim_id;
        IF old_claim.id IS NULL OR new_claim.id IS NULL
          OR new_claim.claim_id IS DISTINCT FROM old_claim.claim_id
          OR new_claim.version_number<=old_claim.version_number
          OR new_claim.status NOT IN ('FROZEN','SUPERSEDED') OR new_claim.frozen_at IS NULL
          OR old_claim.content_hash IS DISTINCT FROM review.target_content_hash THEN
          RAISE EXCEPTION 'frozen same-claim successor required' USING ERRCODE='P17F2';
        END IF;
      ELSE
        SELECT * INTO new_conclusion FROM scientific_conclusion_versions
          WHERE id=NEW.result_scientific_conclusion_version_id;
        SELECT project_id INTO result_project FROM scientific_conclusions
          WHERE id=new_conclusion.scientific_conclusion_id;
        IF old_conclusion.id IS NULL OR new_conclusion.id IS NULL
          OR new_conclusion.scientific_conclusion_id
             IS DISTINCT FROM old_conclusion.scientific_conclusion_id
          OR new_conclusion.version_number<=old_conclusion.version_number
          OR new_conclusion.status NOT IN ('FROZEN','SUPERSEDED')
          OR new_conclusion.frozen_at IS NULL
          OR old_conclusion.content_hash IS DISTINCT FROM review.target_content_hash THEN
          RAISE EXCEPTION 'frozen same-conclusion successor required' USING ERRCODE='P17F2';
        END IF;
      END IF;
      IF result_project IS DISTINCT FROM pid THEN
        RAISE EXCEPTION 'same-project result required' USING ERRCODE='P17F2';
      END IF;
      IF NEW.supersedes_revision_action_id IS NOT NULL THEN
        SELECT * INTO predecessor FROM revision_actions
          WHERE id=NEW.supersedes_revision_action_id FOR UPDATE;
        IF predecessor.id IS NULL OR predecessor.id=NEW.id
          OR predecessor.review_issue_id IS DISTINCT FROM NEW.review_issue_id
          OR predecessor.decision_record_id IS DISTINCT FROM NEW.decision_record_id THEN
          RAISE EXCEPTION 'same-basis correction required' USING ERRCODE='P17F2';
        END IF;
        IF EXISTS (SELECT 1 FROM revision_actions
          WHERE supersedes_revision_action_id=predecessor.id) THEN
          RAISE EXCEPTION 'predecessor already superseded' USING ERRCODE='P17R1';
        END IF;
      END IF;
      RETURN NEW;
    END $$;
"""
