"""Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes."""

from alembic import op

revision = "0043_pr2_04_schema_contract"
down_revision = "0042_pr2_15_minimal_decision"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Hold these locks through preflight and DDL in Alembic's PostgreSQL transaction.
    # Ordinary UNIQUE semantics intentionally permit multiple NULL reservations.
    op.execute("""
    LOCK TABLE literature_search_executions,literature_search_provider_attempts,
      search_query_records,literature_search_execution_events,
      literature_search_execution_command_receipts IN ACCESS EXCLUSIVE MODE;
    DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM literature_search_provider_attempts
          WHERE query_record_id IS NOT NULL GROUP BY query_record_id HAVING count(*)>1) THEN
        RAISE EXCEPTION '0043 preflight: duplicate %.query_record_id',
          'literature_search_provider_attempts'
          USING ERRCODE='23505';
      END IF;
      IF EXISTS (SELECT 1 FROM search_query_records
          GROUP BY literature_search_execution_id,id HAVING count(*)>1) THEN
        RAISE EXCEPTION '0043 preflight: duplicate search_query_records scoped execution/id key'
          USING ERRCODE='23505';
      END IF;
      IF EXISTS (SELECT 1 FROM literature_search_execution_command_receipts
          WHERE result_dto_version NOT BETWEEN -32768 AND 32767) THEN
        RAISE EXCEPTION '0043 preflight: receipt result_dto_version outside SMALLINT range'
          USING ERRCODE='22003';
      END IF;
    END $$;
    ALTER TABLE literature_search_provider_attempts
      ADD CONSTRAINT uq_pr204_attempt_query_record UNIQUE (query_record_id);
    ALTER TABLE search_query_records
      ADD CONSTRAINT uq_sqr_execution_id UNIQUE (literature_search_execution_id,id);
    ALTER TABLE literature_search_execution_command_receipts
      ALTER COLUMN result_dto_version TYPE SMALLINT USING result_dto_version::SMALLINT;
    CREATE INDEX ix_pr204_execution_requested_by ON literature_search_executions(requested_by);
    CREATE INDEX ix_pr204_execution_executed_by ON literature_search_executions(executed_by);
    CREATE INDEX ix_pr204_execution_project_status_created_id
      ON literature_search_executions(project_id,status,created_at,id);
    CREATE INDEX ix_pr204_query_execution_attempt
      ON search_query_records(literature_search_execution_id,provider_attempt_id);
    CREATE INDEX ix_pr204_event_execution_attempt
      ON literature_search_execution_events(execution_id,attempt_id);
    CREATE INDEX ix_pr204_event_created_by ON literature_search_execution_events(created_by);
    CREATE INDEX ix_pr204_receipt_project_execution
      ON literature_search_execution_command_receipts(project_id,result_execution_id);
    CREATE INDEX ix_pr204_receipt_created_by
      ON literature_search_execution_command_receipts(created_by);
    """)


def downgrade() -> None:
    # Widening SMALLINT to INTEGER is lossless. RESTRICT remains PostgreSQL's default:
    # an unexpected dependent object blocks removal rather than being discarded.
    op.execute("""
    LOCK TABLE literature_search_executions,literature_search_provider_attempts,
      search_query_records,literature_search_execution_events,
      literature_search_execution_command_receipts IN ACCESS EXCLUSIVE MODE;
    DROP INDEX ix_pr204_receipt_created_by;
    DROP INDEX ix_pr204_receipt_project_execution;
    DROP INDEX ix_pr204_event_created_by;
    DROP INDEX ix_pr204_event_execution_attempt;
    DROP INDEX ix_pr204_query_execution_attempt;
    DROP INDEX ix_pr204_execution_project_status_created_id;
    DROP INDEX ix_pr204_execution_executed_by;
    DROP INDEX ix_pr204_execution_requested_by;
    ALTER TABLE literature_search_execution_command_receipts
      ALTER COLUMN result_dto_version TYPE INTEGER USING result_dto_version::INTEGER;
    ALTER TABLE search_query_records DROP CONSTRAINT uq_sqr_execution_id;
    ALTER TABLE literature_search_provider_attempts DROP CONSTRAINT uq_pr204_attempt_query_record;
    """)
