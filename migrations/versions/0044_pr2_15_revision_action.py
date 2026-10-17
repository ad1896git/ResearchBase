"""Approved conservative completed RevisionAction slice; retained history is immutable."""

from alembic import op

revision = "0044_pr2_15_revision_action"
down_revision = "0043_pr2_04_schema_contract"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE revision_actions (
      id UUID PRIMARY KEY,
      created_at TIMESTAMPTZ NOT NULL,
      created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
      review_issue_id UUID REFERENCES review_issues(id) ON DELETE RESTRICT,
      decision_record_id UUID REFERENCES decision_records(id) ON DELETE RESTRICT,
      action_type VARCHAR(32) NOT NULL,
      result_experiment_spec_version_id UUID
        REFERENCES experiment_spec_versions(id) ON DELETE RESTRICT,
      result_run_id UUID REFERENCES runs(id) ON DELETE RESTRICT,
      result_statistical_result_id UUID REFERENCES statistical_results(id) ON DELETE RESTRICT,
      result_claim_version_id UUID REFERENCES claim_versions(id) ON DELETE RESTRICT,
      result_scientific_conclusion_version_id UUID
        REFERENCES scientific_conclusion_versions(id) ON DELETE RESTRICT,
      result_manuscript_version_id UUID REFERENCES manuscript_versions(id) ON DELETE RESTRICT,
      result_source_version_id UUID REFERENCES source_versions(id) ON DELETE RESTRICT,
      supersedes_revision_action_id UUID REFERENCES revision_actions(id) ON DELETE RESTRICT,
      content_hash CHAR(64) NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
      hash_scheme VARCHAR(32) NOT NULL CHECK (hash_scheme='sha256-cjson-v1'),
      CHECK (review_issue_id IS NOT NULL OR decision_record_id IS NOT NULL),
      CHECK (supersedes_revision_action_id IS DISTINCT FROM id),
      CONSTRAINT revision_action_shape CHECK (
        (action_type='NEW_EXPERIMENT' AND result_experiment_spec_version_id IS NOT NULL
          AND result_run_id IS NOT NULL AND num_nonnulls(result_statistical_result_id,
            result_claim_version_id,result_scientific_conclusion_version_id,
            result_manuscript_version_id,result_source_version_id)=0)
        OR (action_type='ANALYSIS_CHANGE' AND result_statistical_result_id IS NOT NULL
          AND num_nonnulls(result_experiment_spec_version_id,result_run_id,
            result_claim_version_id,result_scientific_conclusion_version_id,
            result_manuscript_version_id,result_source_version_id)=0)
        OR (action_type='CLAIM_CHANGE' AND result_claim_version_id IS NOT NULL
          AND num_nonnulls(result_experiment_spec_version_id,result_run_id,
            result_statistical_result_id,
            result_scientific_conclusion_version_id,result_manuscript_version_id,
            result_source_version_id)=0)
        OR (action_type='CONCLUSION_CHANGE' AND result_scientific_conclusion_version_id IS NOT NULL
          AND num_nonnulls(result_experiment_spec_version_id,result_run_id,
            result_statistical_result_id,
            result_claim_version_id,result_manuscript_version_id,result_source_version_id)=0)
        OR (action_type='MANUSCRIPT_CHANGE' AND result_manuscript_version_id IS NOT NULL
          AND num_nonnulls(result_experiment_spec_version_id,result_run_id,
            result_statistical_result_id,
            result_claim_version_id,result_scientific_conclusion_version_id,
            result_source_version_id)=0)
        OR (action_type='SOURCE_CHANGE' AND result_source_version_id IS NOT NULL
          AND num_nonnulls(result_experiment_spec_version_id,result_run_id,
            result_statistical_result_id,
            result_claim_version_id,result_scientific_conclusion_version_id,
            result_manuscript_version_id)=0)
        OR (action_type='NO_CHANGE'
          AND num_nonnulls(result_experiment_spec_version_id,result_run_id,
            result_statistical_result_id,result_claim_version_id,
            result_scientific_conclusion_version_id,result_manuscript_version_id,
            result_source_version_id)=0)
      )
    );
    CREATE UNIQUE INDEX uq_revision_action_predecessor
      ON revision_actions(supersedes_revision_action_id)
      WHERE supersedes_revision_action_id IS NOT NULL;
    CREATE FUNCTION pr215_revision_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
    CREATE TRIGGER revision_action_guard BEFORE INSERT OR UPDATE OR DELETE ON revision_actions
      FOR EACH ROW EXECUTE FUNCTION pr215_revision_guard();
    """)
    for column in (
        "created_by",
        "review_issue_id",
        "decision_record_id",
        "result_experiment_spec_version_id",
        "result_run_id",
        "result_statistical_result_id",
        "result_claim_version_id",
        "result_scientific_conclusion_version_id",
        "result_manuscript_version_id",
        "result_source_version_id",
    ):
        op.execute(f"CREATE INDEX ix_revision_action_{column} ON revision_actions({column})")


def downgrade() -> None:
    op.execute("""
    LOCK TABLE revision_actions IN ACCESS EXCLUSIVE MODE;
    DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM revision_actions) THEN
        RAISE EXCEPTION 'revision history cannot be discarded' USING ERRCODE='P17F2';
      END IF;
    END $$;
    DROP TABLE revision_actions;
    DROP FUNCTION pr215_revision_guard();
    """)
