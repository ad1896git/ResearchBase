"""B03 immutable explicit discussion to DRAFT hypothesis admission."""

from alembic import op

revision = "0072_b03_discussion_hypothesis"
down_revision = "0071_b23_novelty_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    LOCK TABLE discussion_command_receipts IN ACCESS EXCLUSIVE MODE;
    DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM discussion_command_receipts WHERE command_name NOT IN
          ('CREATE_SESSION','APPEND_TURN','CLOSE_SESSION','BIND_TRANSCRIPT')
          OR ((command_name='APPEND_TURN') IS DISTINCT FROM (result_turn_id IS NOT NULL))) THEN
        RAISE EXCEPTION 'invalid historical discussion receipt' USING ERRCODE='P17D3';
      END IF;
    END $$;
    ALTER TABLE discussion_command_receipts
      DROP CONSTRAINT ck_pr210_receipt_command_with_binding;
    ALTER TABLE discussion_command_receipts ADD CONSTRAINT ck_b03_receipt_command
      CHECK(command_name IN ('CREATE_SESSION','APPEND_TURN','CLOSE_SESSION',
                            'BIND_TRANSCRIPT','PROMOTE_HYPOTHESIS'));
    ALTER TABLE discussion_command_receipts ADD CONSTRAINT uq_b03_receipt_context
      UNIQUE(id,project_id,result_session_id);
    CREATE TABLE discussion_hypothesis_admissions (
      receipt_id UUID CONSTRAINT pk_b03_admission PRIMARY KEY,
      project_id UUID NOT NULL,
      session_id UUID NOT NULL,
      turn_id UUID NOT NULL,
      transcript_artifact_version_id UUID NOT NULL,
      research_question_version_id UUID NOT NULL,
      hypothesis_version_id UUID NOT NULL,
      candidate_hash CHAR(64) NOT NULL,
      statement TEXT NOT NULL,
      expected_direction VARCHAR(64),
      rationale TEXT,
      CONSTRAINT fk_b03_receipt FOREIGN KEY(receipt_id,project_id,session_id)
        REFERENCES discussion_command_receipts(id,project_id,result_session_id) ON DELETE RESTRICT,
      CONSTRAINT fk_b03_session FOREIGN KEY(project_id,session_id)
        REFERENCES discussion_sessions(project_id,id) ON DELETE RESTRICT,
      CONSTRAINT fk_b03_turn FOREIGN KEY(session_id,turn_id)
        REFERENCES discussion_turns(session_id,id) ON DELETE RESTRICT,
      CONSTRAINT fk_b03_question FOREIGN KEY(session_id,research_question_version_id)
        REFERENCES discussion_session_question_inputs(session_id,version_id) ON DELETE RESTRICT,
      CONSTRAINT fk_b03_transcript FOREIGN KEY(transcript_artifact_version_id)
        REFERENCES artifact_versions(id) ON DELETE RESTRICT,
      CONSTRAINT fk_b03_hv FOREIGN KEY(hypothesis_version_id)
        REFERENCES hypothesis_versions(id) ON DELETE RESTRICT,
      CONSTRAINT uq_b03_output UNIQUE(hypothesis_version_id),
      CONSTRAINT uq_b03_candidate UNIQUE(session_id,turn_id,candidate_hash),
      CONSTRAINT ck_b03_hash CHECK(candidate_hash ~ '^[0-9a-f]{64}$'),
      CONSTRAINT ck_b03_statement CHECK(length(statement) BETWEEN 1 AND 16000
        AND length(btrim(statement))>0),
      CONSTRAINT ck_b03_direction CHECK(expected_direction IS NULL OR
        (length(expected_direction) BETWEEN 1 AND 64 AND length(btrim(expected_direction))>0)),
      CONSTRAINT ck_b03_rationale CHECK(rationale IS NULL OR
        (length(rationale) BETWEEN 1 AND 16000 AND length(btrim(rationale))>0))
    );
    CREATE INDEX ix_b03_admission_project_receipt
      ON discussion_hypothesis_admissions(project_id,receipt_id);
    CREATE TRIGGER b03_admission_immutable BEFORE UPDATE OR DELETE
      ON discussion_hypothesis_admissions FOR EACH ROW EXECUTE FUNCTION m2_immutable();
    CREATE FUNCTION b03_complete_admission_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE rid UUID; r discussion_command_receipts%ROWTYPE;
      a discussion_hypothesis_admissions%ROWTYPE;
    BEGIN
      IF TG_TABLE_NAME='discussion_command_receipts' THEN rid:=NEW.id;
      ELSE rid:=NEW.receipt_id; END IF;
      SELECT * INTO r FROM discussion_command_receipts WHERE id=rid;
      SELECT * INTO a FROM discussion_hypothesis_admissions WHERE receipt_id=rid;
      IF r.command_name<>'PROMOTE_HYPOTHESIS' AND a.receipt_id IS NULL THEN RETURN NULL; END IF;
      IF r.id IS NULL OR r.command_name<>'PROMOTE_HYPOTHESIS' OR a.receipt_id IS NULL THEN
        RAISE EXCEPTION 'exact promotion receipt and admission required' USING ERRCODE='P17D3';
      END IF;
      IF NOT EXISTS (
        SELECT 1 FROM discussion_sessions s
        JOIN research_question_versions qv ON qv.id=a.research_question_version_id
        JOIN research_questions q ON q.id=qv.research_question_id
        JOIN hypothesis_versions v ON v.id=a.hypothesis_version_id
        JOIN hypotheses h ON h.id=v.hypothesis_id
        WHERE s.id=a.session_id AND s.project_id=a.project_id AND s.status='CLOSED'
          AND s.transcript_artifact_version_id=a.transcript_artifact_version_id
          AND q.project_id=a.project_id AND qv.status IN ('FROZEN','SUPERSEDED')
          AND qv.content_hash IS NOT NULL AND qv.frozen_at IS NOT NULL
          AND h.project_id=a.project_id AND h.research_question_id=q.id
          AND h.current_version_id=v.id AND h.row_version=1
          AND h.created_by=r.actor_id AND v.created_by=r.actor_id
          AND h.created_at=r.completed_at AND v.created_at=r.completed_at
          AND h.xmin = pg_current_xact_id()::xid
          AND v.xmin = pg_current_xact_id()::xid
          AND v.version_number=1 AND v.row_version=1 AND v.status='DRAFT'
          -- Phase 1 derives hash_scheme from content_hash in its repository.
          AND v.content_hash IS NULL AND v.frozen_at IS NULL
          AND v.statement=a.statement
          AND v.expected_direction IS NOT DISTINCT FROM a.expected_direction
          AND v.rationale IS NOT DISTINCT FROM a.rationale
          AND (v.success_criteria IS NULL OR v.success_criteria='null'::jsonb)
      ) THEN
        RAISE EXCEPTION 'complete fresh DRAFT admission required' USING ERRCODE='P17D3';
      END IF;
      RETURN NULL;
    END $$;
    CREATE CONSTRAINT TRIGGER b03_complete_receipt AFTER INSERT ON discussion_command_receipts
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b03_complete_admission_guard();
    CREATE CONSTRAINT TRIGGER b03_complete_admission
      AFTER INSERT ON discussion_hypothesis_admissions
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b03_complete_admission_guard();
    """)


def downgrade() -> None:
    op.execute("""
    LOCK TABLE discussion_command_receipts,discussion_hypothesis_admissions
      IN ACCESS EXCLUSIVE MODE;
    DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM discussion_hypothesis_admissions)
         OR EXISTS(SELECT 1 FROM discussion_command_receipts
                   WHERE command_name='PROMOTE_HYPOTHESIS')
      THEN RAISE EXCEPTION 'B03 promotion history cannot be discarded' USING ERRCODE='P17D3';
      END IF;
    END $$;
    DROP TRIGGER b03_complete_receipt ON discussion_command_receipts;
    DROP TABLE discussion_hypothesis_admissions;
    DROP FUNCTION b03_complete_admission_guard();
    ALTER TABLE discussion_command_receipts DROP CONSTRAINT uq_b03_receipt_context;
    ALTER TABLE discussion_command_receipts DROP CONSTRAINT ck_b03_receipt_command;
    ALTER TABLE discussion_command_receipts ADD CONSTRAINT ck_pr210_receipt_command_with_binding
      CHECK(command_name IN ('CREATE_SESSION','APPEND_TURN','CLOSE_SESSION','BIND_TRANSCRIPT'));
    """)
