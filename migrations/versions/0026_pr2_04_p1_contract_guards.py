"""Restore attribution and one-to-one execution provenance contracts.

Historical NULL attribution is inferred only from agreeing immutable creation
receipt/event evidence, or a unique first-start event and reservation. Ambiguous
rows abort the transaction before any update. Existing non-NULL values are kept.
"""

from alembic import op

revision = "0026_pr2_04_p1_contract_guards"
down_revision = "0025_pr2_04_reservation_guards"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        LOCK TABLE literature_search_executions, literature_search_execution_events,
          literature_search_provider_attempts, literature_search_execution_command_receipts,
          search_query_records IN ACCESS EXCLUSIVE MODE;
        CREATE TEMP TABLE pr204_attribution_backfill (
          execution_id uuid PRIMARY KEY, actor_id uuid NOT NULL
        ) ON COMMIT DROP;
        DO $$
        DECLARE e record;
        DECLARE actor uuid;
        DECLARE evidence_count integer;
        BEGIN
          FOR e IN SELECT * FROM literature_search_executions WHERE executed_by IS NULL LOOP
            SELECT count(*) INTO evidence_count
            FROM literature_search_execution_events v
            JOIN literature_search_execution_command_receipts r
              ON r.result_execution_id = v.execution_id
             AND r.command_name = 'CREATE_LITERATURE_SEARCH_EXECUTION'
             AND r.actor_id = v.created_by AND r.created_by = v.created_by
             AND r.project_id = e.project_id
            WHERE v.execution_id = e.id AND v.kind = 'CREATED' AND v.sequence = 0
              AND v.new_status = 'PLANNED' AND v.new_row_version = 1
              AND v.prior_status IS NULL AND v.prior_row_version IS NULL
              AND v.created_by = e.requested_by AND e.created_by = e.requested_by;
            IF evidence_count <> 1 THEN
              RAISE EXCEPTION 'PR2-04 ambiguous historical creation attribution for %', e.id
                USING ERRCODE = 'P17D5';
            END IF;
            actor := NULL;
            IF e.started_at IS NULL AND e.status IN ('PLANNED','CANCELLED')
               AND NOT EXISTS (SELECT 1 FROM literature_search_provider_attempts
                               WHERE execution_id=e.id)
               AND NOT EXISTS (SELECT 1 FROM literature_search_execution_events
                               WHERE execution_id=e.id AND new_status='RUNNING') THEN
              actor := e.requested_by;
            ELSIF e.started_at IS NOT NULL AND e.status <> 'PLANNED' THEN
              SELECT count(*) INTO evidence_count
              FROM literature_search_execution_events v
              JOIN literature_search_provider_attempts a ON a.id=v.attempt_id
              WHERE v.execution_id=e.id AND v.kind='ATTEMPT_RESERVED'
                AND v.prior_status='PLANNED' AND v.new_status='RUNNING'
                AND v.new_row_version=v.prior_row_version+1
                AND a.execution_id=e.id AND a.query_index=0 AND a.attempt_number=1
                AND a.reserved_at=e.started_at AND a.created_by=v.created_by;
              IF evidence_count = 1 AND (SELECT count(*) FROM literature_search_execution_events
                  WHERE execution_id=e.id AND kind='ATTEMPT_RESERVED'
                    AND prior_status='PLANNED' AND new_status='RUNNING') = 1 THEN
                SELECT v.created_by INTO actor FROM literature_search_execution_events v
                WHERE v.execution_id=e.id AND v.kind='ATTEMPT_RESERVED'
                  AND v.prior_status='PLANNED' AND v.new_status='RUNNING';
              END IF;
            END IF;
            IF actor IS NULL THEN
              RAISE EXCEPTION 'PR2-04 ambiguous historical start attribution for %', e.id
                USING ERRCODE = 'P17D5';
            END IF;
            INSERT INTO pr204_attribution_backfill VALUES (e.id,actor);
          END LOOP;
        END; $$;
        -- Only the proven attribution column changes. Audit rows and versions stay immutable.
        ALTER TABLE literature_search_executions DISABLE TRIGGER trg_pr204_execution_update_guard;
        ALTER TABLE literature_search_executions DISABLE TRIGGER trg_pr204_execution_event_commit;
        UPDATE literature_search_executions e SET executed_by=b.actor_id
          FROM pr204_attribution_backfill b WHERE e.id=b.execution_id;
        ALTER TABLE literature_search_executions ENABLE TRIGGER trg_pr204_execution_update_guard;
        ALTER TABLE literature_search_executions ENABLE TRIGGER trg_pr204_execution_event_commit;
        ALTER TABLE literature_search_executions ALTER COLUMN executed_by SET NOT NULL;
        ALTER TABLE literature_search_execution_events ADD CONSTRAINT uq_lsee_mutation_coordinate
          UNIQUE (execution_id,new_row_version);
        ALTER TABLE search_query_records ADD CONSTRAINT uq_sqrec_provider_attempt
          UNIQUE (provider_attempt_id);
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION pr204_guard_execution_update() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF OLD.status IN ('SUCCEEDED','FAILED','CANCELLED','UNKNOWN')
             AND NEW IS DISTINCT FROM OLD THEN
            RAISE EXCEPTION 'PR2-04 terminal execution is immutable' USING ERRCODE = 'P17D1';
          END IF;
          IF NEW.id IS DISTINCT FROM OLD.id
             OR NEW.project_id IS DISTINCT FROM OLD.project_id
             OR NEW.search_plan_version_id IS DISTINCT FROM OLD.search_plan_version_id
             OR NEW.strategy_id IS DISTINCT FROM OLD.strategy_id
             OR NEW.strategy_version IS DISTINCT FROM OLD.strategy_version
             OR NEW.requested_by IS DISTINCT FROM OLD.requested_by
             OR NEW.execution_context IS DISTINCT FROM OLD.execution_context
             OR NEW.idempotency_key IS DISTINCT FROM OLD.idempotency_key
             OR NEW.created_by IS DISTINCT FROM OLD.created_by
             OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
            RAISE EXCEPTION 'PR2-04 execution input material is immutable' USING ERRCODE = 'P17D1';
          END IF;
          IF NEW.status IS DISTINCT FROM OLD.status
             AND NOT ((OLD.status = 'PLANNED' AND NEW.status IN ('RUNNING','CANCELLED'))
                      OR (OLD.status = 'RUNNING'
                          AND NEW.status IN ('SUCCEEDED','FAILED','CANCELLED','UNKNOWN'))) THEN
            RAISE EXCEPTION 'PR2-04 invalid execution lifecycle transition' USING ERRCODE = 'P17D4';
          END IF;
          IF NEW.executed_by IS DISTINCT FROM OLD.executed_by
             AND NOT (OLD.status = 'PLANNED' AND NEW.status = 'RUNNING'
                      AND OLD.started_at IS NULL AND NEW.started_at IS NOT NULL
                      AND OLD.executed_by = OLD.requested_by AND NEW.executed_by IS NOT NULL) THEN
            RAISE EXCEPTION 'PR2-04 executed_by may be assigned only at start'
              USING ERRCODE = 'P17D1';
          END IF;
          IF NEW.started_at IS DISTINCT FROM OLD.started_at
             AND NOT (OLD.status = 'PLANNED' AND NEW.status = 'RUNNING'
                      AND OLD.started_at IS NULL AND NEW.started_at IS NOT NULL) THEN
            RAISE EXCEPTION 'PR2-04 started_at may be assigned only at start'
              USING ERRCODE = 'P17D4';
          END IF;
          IF NEW.finished_at IS DISTINCT FROM OLD.finished_at
             AND NOT (OLD.status IN ('PLANNED','RUNNING')
                      AND NEW.status IN ('SUCCEEDED','FAILED','CANCELLED','UNKNOWN')
                      AND OLD.finished_at IS NULL AND NEW.finished_at IS NOT NULL) THEN
            RAISE EXCEPTION 'PR2-04 finished_at may be assigned only at finalization'
              USING ERRCODE = 'P17D4';
          END IF;
          IF NEW.failure_code IS DISTINCT FROM OLD.failure_code
             AND NOT (NEW.status IN ('FAILED','CANCELLED','UNKNOWN')
                      AND OLD.status IN ('PLANNED','RUNNING')) THEN
            RAISE EXCEPTION 'PR2-04 failure_code may change only at terminalization'
              USING ERRCODE = 'P17D4';
          END IF;
          IF NEW.row_version <> OLD.row_version + 1 THEN
            RAISE EXCEPTION 'PR2-04 execution row_version must advance once'
              USING ERRCODE = 'P17D5';
          END IF;
          RETURN NEW;
        END; $$;
    """)
    op.execute("""
        CREATE FUNCTION pr204_guard_initial_attribution() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF NEW.executed_by IS DISTINCT FROM NEW.requested_by
             OR NEW.created_by IS DISTINCT FROM NEW.requested_by THEN
            RAISE EXCEPTION 'PR2-04 initial attribution must equal requester' USING ERRCODE='P17D5';
          END IF;
          RETURN NEW;
        END; $$;
        CREATE TRIGGER trg_pr204_initial_attribution BEFORE INSERT ON literature_search_executions
          FOR EACH ROW EXECUTE FUNCTION pr204_guard_initial_attribution();

        CREATE FUNCTION pr204_validate_start_attribution() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF OLD.status='PLANNED' AND NEW.status='RUNNING' AND NOT EXISTS (
            SELECT 1 FROM literature_search_execution_events v
            JOIN literature_search_provider_attempts a ON a.id=v.attempt_id
            WHERE v.execution_id=NEW.id AND v.kind='ATTEMPT_RESERVED'
              AND v.prior_status='PLANNED' AND v.new_status='RUNNING'
              AND v.prior_row_version=OLD.row_version AND v.new_row_version=NEW.row_version
              AND v.created_by=NEW.executed_by AND a.created_by=NEW.executed_by
              AND a.execution_id=NEW.id AND a.query_index=0 AND a.attempt_number=1
              AND a.reserved_at=NEW.started_at
          ) THEN
            RAISE EXCEPTION 'PR2-04 first executor requires matching start evidence'
              USING ERRCODE='P17D5';
          END IF;
          RETURN NULL;
        END; $$;
        CREATE CONSTRAINT TRIGGER trg_pr204_start_attribution_commit
          AFTER UPDATE ON literature_search_executions DEFERRABLE INITIALLY DEFERRED
          FOR EACH ROW EXECUTE FUNCTION pr204_validate_start_attribution();

        CREATE FUNCTION pr204_validate_query_reciprocal() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM literature_search_provider_attempts a
            WHERE a.id=NEW.provider_attempt_id AND a.query_record_id=NEW.id
              AND a.execution_id=NEW.literature_search_execution_id
              AND a.status<>'RESERVED' AND a.invoked_at=NEW.executed_at
          ) THEN
            RAISE EXCEPTION 'PR2-04 query must be the sealed attempt outcome' USING ERRCODE='P17D5';
          END IF;
          RETURN NULL;
        END; $$;
        CREATE CONSTRAINT TRIGGER trg_pr204_query_reciprocal_commit
          AFTER INSERT ON search_query_records DEFERRABLE INITIALLY DEFERRED
          FOR EACH ROW EXECUTE FUNCTION pr204_validate_query_reciprocal();
    """)


def downgrade() -> None:
    # Empty-only: never erase backfilled attribution or permit history to lose its guards.
    op.execute("""
        LOCK TABLE literature_search_executions IN ACCESS EXCLUSIVE MODE;
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM literature_search_executions) THEN
            RAISE EXCEPTION 'PR2-04 0026 downgrade requires empty execution history'
              USING ERRCODE='P17D5';
          END IF;
        END; $$;
        DROP TRIGGER trg_pr204_query_reciprocal_commit ON search_query_records;
        DROP FUNCTION pr204_validate_query_reciprocal();
        DROP TRIGGER trg_pr204_start_attribution_commit ON literature_search_executions;
        DROP FUNCTION pr204_validate_start_attribution();
        DROP TRIGGER trg_pr204_initial_attribution ON literature_search_executions;
        DROP FUNCTION pr204_guard_initial_attribution();
        ALTER TABLE search_query_records DROP CONSTRAINT uq_sqrec_provider_attempt;
        ALTER TABLE literature_search_execution_events DROP CONSTRAINT uq_lsee_mutation_coordinate;
        ALTER TABLE literature_search_executions ALTER COLUMN executed_by DROP NOT NULL;
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION pr204_guard_execution_update() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF OLD.status IN ('SUCCEEDED','FAILED','CANCELLED','UNKNOWN')
             AND NEW IS DISTINCT FROM OLD THEN
            RAISE EXCEPTION 'PR2-04 terminal execution is immutable' USING ERRCODE = 'P17D1';
          END IF;
          IF NEW.id IS DISTINCT FROM OLD.id
             OR NEW.project_id IS DISTINCT FROM OLD.project_id
             OR NEW.search_plan_version_id IS DISTINCT FROM OLD.search_plan_version_id
             OR NEW.strategy_id IS DISTINCT FROM OLD.strategy_id
             OR NEW.strategy_version IS DISTINCT FROM OLD.strategy_version
             OR NEW.requested_by IS DISTINCT FROM OLD.requested_by
             OR NEW.execution_context IS DISTINCT FROM OLD.execution_context
             OR NEW.idempotency_key IS DISTINCT FROM OLD.idempotency_key
             OR NEW.created_by IS DISTINCT FROM OLD.created_by
             OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
            RAISE EXCEPTION 'PR2-04 execution input material is immutable' USING ERRCODE = 'P17D1';
          END IF;
          IF NEW.status IS DISTINCT FROM OLD.status
             AND NOT ((OLD.status = 'PLANNED' AND NEW.status IN ('RUNNING','CANCELLED'))
                      OR (OLD.status = 'RUNNING'
                          AND NEW.status IN ('SUCCEEDED','FAILED','CANCELLED','UNKNOWN'))) THEN
            RAISE EXCEPTION 'PR2-04 invalid execution lifecycle transition' USING ERRCODE = 'P17D4';
          END IF;
          IF NEW.executed_by IS DISTINCT FROM OLD.executed_by
             AND NOT (OLD.status = 'PLANNED' AND NEW.status = 'RUNNING'
                      AND OLD.executed_by IS NULL AND NEW.executed_by IS NOT NULL) THEN
            RAISE EXCEPTION 'PR2-04 executed_by may be assigned only at start'
              USING ERRCODE = 'P17D1';
          END IF;
          IF NEW.started_at IS DISTINCT FROM OLD.started_at
             AND NOT (OLD.status = 'PLANNED' AND NEW.status = 'RUNNING'
                      AND OLD.started_at IS NULL AND NEW.started_at IS NOT NULL) THEN
            RAISE EXCEPTION 'PR2-04 started_at may be assigned only at start'
              USING ERRCODE = 'P17D4';
          END IF;
          IF NEW.finished_at IS DISTINCT FROM OLD.finished_at
             AND NOT (OLD.status IN ('PLANNED','RUNNING')
                      AND NEW.status IN ('SUCCEEDED','FAILED','CANCELLED','UNKNOWN')
                      AND OLD.finished_at IS NULL AND NEW.finished_at IS NOT NULL) THEN
            RAISE EXCEPTION 'PR2-04 finished_at may be assigned only at finalization'
              USING ERRCODE = 'P17D4';
          END IF;
          IF NEW.failure_code IS DISTINCT FROM OLD.failure_code
             AND NOT (NEW.status IN ('FAILED','CANCELLED','UNKNOWN')
                      AND OLD.status IN ('PLANNED','RUNNING')) THEN
            RAISE EXCEPTION 'PR2-04 failure_code may change only at terminalization'
              USING ERRCODE = 'P17D4';
          END IF;
          IF NEW.row_version <> OLD.row_version + 1 THEN
            RAISE EXCEPTION 'PR2-04 execution row_version must advance once'
              USING ERRCODE = 'P17D5';
          END IF;
          RETURN NEW;
        END; $$;
    """)
