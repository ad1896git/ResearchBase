"""Enforce frozen PR2-04 reservation time and cancellation invariants."""

from alembic import op

revision: str = "0025_pr2_04_reservation_guards"
down_revision: str | None = "0024_literature_search_execution"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION pr204_guard_reservation_time_and_cancel() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE execution_context jsonb;
        DECLARE execution_started_at timestamptz;
        DECLARE budget_deadline timestamptz;
        BEGIN
          SELECT e.execution_context, e.started_at
            INTO execution_context, execution_started_at
            FROM literature_search_executions e
           WHERE e.id = NEW.execution_id
           FOR UPDATE;
          IF NOT FOUND THEN
            -- Preserve the existing foreign-key rejection of a missing parent.
            RETURN NEW;
          END IF;
          IF NEW.reserved_at IS NULL OR NEW.deadline_at IS NULL
             OR NEW.deadline_at <= NEW.reserved_at THEN
            -- Existing NOT NULL/deadline-order constraints retain their SQLSTATE.
            RETURN NEW;
          END IF;
          budget_deadline := execution_started_at
            + make_interval(secs => (execution_context->>'execution_budget_seconds')::integer);
          IF execution_started_at IS NULL
             OR NEW.reserved_at + interval '1 second' > budget_deadline
             OR NEW.deadline_at IS DISTINCT FROM LEAST(
                  NEW.reserved_at
                    + make_interval(secs => (execution_context->>'timeout_seconds')::integer),
                  budget_deadline) THEN
            RAISE EXCEPTION 'PR2-04 reservation violates frozen time bounds'
              USING ERRCODE = 'P17D5';
          END IF;
          -- Separate statement after the lock: observe C1 committed during a wait.
          IF EXISTS (SELECT 1 FROM literature_search_execution_events
                      WHERE execution_id = NEW.execution_id AND kind = 'CANCEL_REQUESTED') THEN
            RAISE EXCEPTION 'PR2-04 cancellation intent forbids a new reservation'
              USING ERRCODE = 'P17D5';
          END IF;
          RETURN NEW;
        END; $$;
        CREATE TRIGGER trg_pr204_attempt_time_cancel_guard
          BEFORE INSERT ON literature_search_provider_attempts
          FOR EACH ROW EXECUTE FUNCTION pr204_guard_reservation_time_and_cancel();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER trg_pr204_attempt_time_cancel_guard ON literature_search_provider_attempts"
    )
    op.execute("DROP FUNCTION pr204_guard_reservation_time_and_cancel()")
