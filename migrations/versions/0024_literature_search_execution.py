"""Add bounded literature-search execution provenance."""

# DDL contains intentionally literal PostgreSQL expressions and constraint definitions.
# ruff: noqa: E501

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0024_literature_search_execution"
down_revision: str | None = "0023a_search_plan_review_guards"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "literature_search_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("search_plan_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_id", sa.String(64), nullable=False),
        sa.Column("strategy_version", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="PLANNED"),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("executed_by", postgresql.UUID(as_uuid=True)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("execution_context", postgresql.JSONB(), nullable=False),
        sa.Column("idempotency_key", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("failure_code", sa.String(64)),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('PLANNED','RUNNING','SUCCEEDED','FAILED','CANCELLED','UNKNOWN')",
            name="ck_lse_status",
        ),
        sa.CheckConstraint("row_version > 0", name="ck_lse_row_version"),
        sa.CheckConstraint(
            "strategy_id = 'explicit_queries' AND strategy_version = '1'",
            name="ck_lse_strategy",
        ),
        sa.CheckConstraint(
            "started_at IS NULL OR finished_at IS NULL OR finished_at >= started_at",
            name="ck_lse_finished_after_start",
        ),
        sa.CheckConstraint(
            "(status = 'PLANNED' AND started_at IS NULL AND finished_at IS NULL) OR "
            "(status = 'RUNNING' AND started_at IS NOT NULL AND finished_at IS NULL) OR "
            "(status IN ('SUCCEEDED','FAILED','UNKNOWN') AND started_at IS NOT NULL AND finished_at IS NOT NULL) OR "
            "(status = 'CANCELLED' AND finished_at IS NOT NULL)",
            name="ck_lse_lifecycle_timestamps",
        ),
        sa.CheckConstraint(
            "(status IN ('PLANNED','RUNNING','SUCCEEDED') AND failure_code IS NULL) OR "
            "(status = 'FAILED' AND failure_code IS NOT NULL) OR "
            "(status = 'CANCELLED' AND failure_code = 'CANCELLED') OR "
            "(status = 'UNKNOWN' AND failure_code IS NOT NULL)",
            name="ck_lse_failure_status",
        ),
        sa.UniqueConstraint("project_id", "idempotency_key", name="uq_lse_project_idempotency"),
        sa.UniqueConstraint("project_id", "id", name="uq_lse_project_id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["search_plan_version_id"], ["literature_search_plan_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["requested_by"], ["actors.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["executed_by"], ["actors.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["actors.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_lse_project", "literature_search_executions", ["project_id"])
    op.create_index(
        "ix_lse_project_created",
        "literature_search_executions",
        ["project_id", "created_at", "id"],
    )
    op.create_index(
        "ix_lse_plan_version", "literature_search_executions", ["search_plan_version_id"]
    )
    op.create_index("ix_lse_created_by", "literature_search_executions", ["created_by"])

    op.create_table(
        "literature_search_provider_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("query_index", sa.Integer(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("provider_request_key", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reserved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recovery_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="RESERVED"),
        sa.Column("query_record_id", postgresql.UUID(as_uuid=True)),
        sa.Column("invoked_at", sa.DateTime(timezone=True)),
        sa.Column("returned_at", sa.DateTime(timezone=True)),
        sa.Column("retrieved_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("delivery_certainty", sa.String(24)),
        sa.Column("provider_request_id", sa.String(256)),
        sa.Column("failure_code", sa.String(64)),
        sa.Column("retry_after_seconds", sa.Integer()),
        sa.Column("warning_codes", postgresql.JSONB()),
        sa.Column("result_count", sa.Integer()),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("query_index >= 0", name="ck_lspa_query_index"),
        sa.CheckConstraint("attempt_number > 0", name="ck_lspa_attempt_number"),
        sa.CheckConstraint("provider_request_key = id", name="ck_lspa_request_key_is_attempt_id"),
        sa.CheckConstraint("row_version > 0", name="ck_lspa_row_version"),
        sa.CheckConstraint(
            "retry_after_seconds IS NULL OR retry_after_seconds >= 0", name="ck_lspa_retry_after"
        ),
        sa.CheckConstraint(
            "result_count IS NULL OR result_count >= 0", name="ck_lspa_result_count"
        ),
        sa.CheckConstraint("deadline_at > reserved_at", name="ck_lspa_deadline_after_reserve"),
        sa.CheckConstraint(
            "recovery_after = deadline_at + interval '30 seconds'",
            name="ck_lspa_recovery_after_deadline",
        ),
        sa.CheckConstraint(
            "completed_at IS NULL OR completed_at >= reserved_at",
            name="ck_lspa_completion_after_reserve",
        ),
        sa.CheckConstraint(
            "invoked_at IS NULL OR returned_at IS NULL OR returned_at >= invoked_at",
            name="ck_lspa_return_after_invocation",
        ),
        sa.CheckConstraint(
            "(status = 'RESERVED' AND completed_at IS NULL AND delivery_certainty IS NULL "
            "AND failure_code IS NULL AND result_count IS NULL AND query_record_id IS NULL "
            "AND invoked_at IS NULL AND returned_at IS NULL AND provider_request_id IS NULL "
            "AND retry_after_seconds IS NULL AND warning_codes IS NULL AND retrieved_at IS NULL) OR "
            "(status = 'SUCCEEDED' AND completed_at IS NOT NULL AND invoked_at IS NOT NULL "
            "AND returned_at IS NOT NULL AND delivery_certainty IS NOT NULL "
            "AND delivery_certainty = 'RESPONSE_RECEIVED' "
            "AND failure_code IS NULL AND result_count IS NOT NULL AND query_record_id IS NOT NULL "
            "AND warning_codes IS NOT NULL AND retrieved_at IS NOT NULL) OR "
            "(status IN ('RETRYABLE_FAILURE','PERMANENT_FAILURE','CANCELLED','UNKNOWN') "
            "AND completed_at IS NOT NULL AND delivery_certainty IS NOT NULL "
            "AND delivery_certainty IN ('NOT_SENT','RESPONSE_RECEIVED','MAY_HAVE_BEEN_SENT') "
            "AND failure_code IS NOT NULL AND result_count = 0 AND warning_codes IS NOT NULL "
            "AND retrieved_at IS NULL "
            "AND ((status = 'RETRYABLE_FAILURE' AND failure_code IN "
            "('PROVIDER_TIMEOUT','PROVIDER_RATE_LIMIT','PROVIDER_TRANSIENT')) OR "
            "(status = 'PERMANENT_FAILURE' AND failure_code IN "
            "('PROVIDER_PERMANENT','PROVIDER_MALFORMED')) OR "
            "(status = 'CANCELLED' AND failure_code = 'CANCELLED') OR "
            "(status = 'UNKNOWN' AND failure_code IN "
            "('PROVIDER_OUTCOME_UNKNOWN','RECOVERY_OUTCOME_UNKNOWN'))) "
            "AND (failure_code <> 'PROVIDER_TIMEOUT' OR delivery_certainty = 'NOT_SENT') "
            "AND (failure_code <> 'PROVIDER_MALFORMED' OR delivery_certainty = 'RESPONSE_RECEIVED') "
            "AND ((invoked_at IS NULL AND query_record_id IS NULL) OR "
            "(invoked_at IS NOT NULL AND query_record_id IS NOT NULL)))",
            name="ck_lspa_outcome_shape",
        ),
        sa.CheckConstraint(
            "status IN ('RESERVED','SUCCEEDED','RETRYABLE_FAILURE','PERMANENT_FAILURE','CANCELLED','UNKNOWN')",
            name="ck_lspa_status",
        ),
        sa.CheckConstraint(
            "(status = 'RETRYABLE_FAILURE' AND delivery_certainty <> 'MAY_HAVE_BEEN_SENT') OR "
            "status <> 'RETRYABLE_FAILURE'",
            name="ck_lspa_retry_is_known_safe",
        ),
        sa.CheckConstraint(
            "(status = 'UNKNOWN' AND delivery_certainty = 'MAY_HAVE_BEEN_SENT') OR "
            "status <> 'UNKNOWN'",
            name="ck_lspa_unknown_certainty",
        ),
        sa.CheckConstraint(
            "(status IN ('PERMANENT_FAILURE','CANCELLED') "
            "AND delivery_certainty <> 'MAY_HAVE_BEEN_SENT') OR "
            "status NOT IN ('PERMANENT_FAILURE','CANCELLED')",
            name="ck_lspa_known_terminal_certainty",
        ),
        sa.CheckConstraint(
            "retry_after_seconds IS NULL OR status = 'RETRYABLE_FAILURE'",
            name="ck_lspa_retry_after_status",
        ),
        sa.CheckConstraint(
            "warning_codes IS NULL OR (jsonb_typeof(warning_codes) = 'array' AND "
            "warning_codes <@ '[\"RESULTS_TRUNCATED\",\"PARTIAL_COVERAGE\",\"RATE_LIMITED\"]'::jsonb)",
            name="ck_lspa_warning_codes",
        ),
        sa.UniqueConstraint(
            "execution_id", "query_index", "attempt_number", name="uq_lspa_attempt_number"
        ),
        sa.UniqueConstraint("execution_id", "id", name="uq_lspa_execution_id"),
        sa.UniqueConstraint(
            "execution_id", "provider_request_key", name="uq_lspa_provider_request_key"
        ),
        sa.ForeignKeyConstraint(
            ["execution_id"], ["literature_search_executions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["actors.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_lspa_execution", "literature_search_provider_attempts", ["execution_id"])
    op.create_index("ix_lspa_created_by", "literature_search_provider_attempts", ["created_by"])
    op.create_index(
        "uq_lspa_one_reserved_per_execution",
        "literature_search_provider_attempts",
        ["execution_id"],
        unique=True,
        postgresql_where=sa.text("status = 'RESERVED'"),
    )

    op.create_table(
        "search_query_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("literature_search_execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_attempt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("perspective", sa.Text()),
        sa.Column("provider_id", sa.String(128), nullable=False),
        sa.Column("provider_version", sa.String(128)),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("query_hash", sa.CHAR(64), nullable=False),
        sa.Column("hash_scheme", sa.String(32), nullable=False, server_default="sha256-cjson-v1"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("ordinal >= 0", name="ck_sqr_ordinal"),
        sa.CheckConstraint("query_hash ~ '^[0-9a-f]{64}$'", name="ck_sqr_hash"),
        sa.UniqueConstraint(
            "literature_search_execution_id", "ordinal", name="uq_sqr_execution_ordinal"
        ),
        sa.UniqueConstraint(
            "literature_search_execution_id", "query_hash", name="uq_sqr_execution_hash"
        ),
        sa.ForeignKeyConstraint(
            ["literature_search_execution_id"],
            ["literature_search_executions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["literature_search_execution_id", "provider_attempt_id"],
            [
                "literature_search_provider_attempts.execution_id",
                "literature_search_provider_attempts.id",
            ],
            name="fk_sqr_attempt_same_execution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["actors.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_sqr_execution", "search_query_records", ["literature_search_execution_id"])
    op.create_index("ix_sqr_attempt", "search_query_records", ["provider_attempt_id"])
    op.create_index("ix_sqr_created_by", "search_query_records", ["created_by"])
    op.create_foreign_key(
        "fk_lspa_query_record",
        "literature_search_provider_attempts",
        "search_query_records",
        ["query_record_id"],
        ["id"],
        ondelete="RESTRICT",
        deferrable=True,
        initially="DEFERRED",
    )

    op.create_table(
        "search_result_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("search_query_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_identifier", sa.String(1024)),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(2048), nullable=False),
        sa.Column("url", sa.String(4096)),
        sa.Column("snippet", sa.String(4096)),
        sa.Column("provider_score", sa.Numeric()),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_hash", sa.CHAR(64), nullable=False),
        sa.Column("hash_scheme", sa.String(32), nullable=False, server_default="sha256-cjson-v1"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("rank >= 0", name="ck_srr_rank"),
        sa.CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="ck_srr_hash"),
        sa.CheckConstraint(
            "provider_score IS NULL OR provider_score NOT IN ('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric)",
            name="ck_srr_finite_score",
        ),
        sa.UniqueConstraint("search_query_record_id", "rank", name="uq_srr_query_rank"),
        sa.ForeignKeyConstraint(
            ["search_query_record_id"], ["search_query_records.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["actors.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_srr_query", "search_result_records", ["search_query_record_id"])
    op.create_index("ix_srr_created_by", "search_result_records", ["created_by"])

    op.create_table(
        "literature_search_execution_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True)),
        sa.Column("prior_status", sa.String(16)),
        sa.Column("new_status", sa.String(16), nullable=False),
        sa.Column("prior_row_version", sa.Integer()),
        sa.Column("new_row_version", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("sequence >= 0", name="ck_lsee_sequence"),
        sa.CheckConstraint(
            "kind IN ('CREATED','ATTEMPT_RESERVED','OUTCOME_RECORDED','CANCEL_REQUESTED','FINISHED')",
            name="ck_lsee_kind",
        ),
        sa.CheckConstraint(
            "(kind IN ('ATTEMPT_RESERVED','OUTCOME_RECORDED') AND attempt_id IS NOT NULL) "
            "OR (kind NOT IN ('ATTEMPT_RESERVED','OUTCOME_RECORDED') AND attempt_id IS NULL)",
            name="ck_lsee_attempt_kind",
        ),
        sa.UniqueConstraint("execution_id", "sequence", name="uq_lsee_execution_sequence"),
        sa.ForeignKeyConstraint(
            ["execution_id", "attempt_id"],
            [
                "literature_search_provider_attempts.execution_id",
                "literature_search_provider_attempts.id",
            ],
            name="fk_lsee_attempt_same_execution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["execution_id"], ["literature_search_executions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"], ["literature_search_provider_attempts.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["actors.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_lsee_execution", "literature_search_execution_events", ["execution_id"])
    op.create_index("ix_lsee_attempt", "literature_search_execution_events", ["attempt_id"])
    op.create_index(
        "uq_lsee_cancel_requested",
        "literature_search_execution_events",
        ["execution_id"],
        unique=True,
        postgresql_where=sa.text("kind = 'CANCEL_REQUESTED'"),
    )
    op.create_index(
        "uq_lsee_finished",
        "literature_search_execution_events",
        ["execution_id"],
        unique=True,
        postgresql_where=sa.text("kind = 'FINISHED'"),
    )

    op.create_table(
        "literature_search_execution_command_receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("deployment_id", sa.String(255), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("command_name", sa.String(48), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_hash", sa.CHAR(64), nullable=False),
        sa.Column("hash_scheme", sa.String(32), nullable=False, server_default="sha256-cjson-v1"),
        sa.Column("result_execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("result_dto_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("result_dto", postgresql.JSONB(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "deployment_id",
            "actor_id",
            "project_id",
            "command_name",
            "request_id",
            name="uq_lse_receipt_scope",
        ),
        sa.CheckConstraint("request_hash ~ '^[0-9a-f]{64}$'", name="ck_lsecr_hash"),
        sa.CheckConstraint(
            "command_name IN ('CREATE_LITERATURE_SEARCH_EXECUTION','EXECUTE_LITERATURE_SEARCH_EXECUTION','CANCEL_LITERATURE_SEARCH_EXECUTION','RECOVER_LITERATURE_SEARCH_EXECUTION')",
            name="ck_lsecr_command",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(result_dto) = 'object' AND "
            "result_dto->>'execution_id' = result_execution_id::text AND "
            "result_dto->>'command_name' = command_name AND "
            "jsonb_typeof(result_dto->'accepted_at') = 'string' AND "
            "jsonb_typeof(result_dto->'accepted_row_version') = 'number' AND "
            "(result_dto->>'accepted_row_version')::integer > 0 AND "
            "result_dto ?& ARRAY['execution_id','command_name','accepted_at','accepted_row_version'] "
            "AND result_dto - ARRAY['execution_id','command_name','accepted_at','accepted_row_version'] = '{}'::jsonb",
            name="ck_lse_receipt_admission_dto",
        ),
        sa.CheckConstraint("length(btrim(deployment_id)) > 0", name="ck_lse_receipt_deployment"),
        sa.CheckConstraint("hash_scheme = 'sha256-cjson-v1'", name="ck_lse_receipt_hash_scheme"),
        sa.CheckConstraint("result_dto_version = 1", name="ck_lse_receipt_dto_version"),
        sa.CheckConstraint("created_by = actor_id", name="ck_lse_receipt_actor_attribution"),
        sa.ForeignKeyConstraint(["actor_id"], ["actors.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["actors.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["project_id", "result_execution_id"],
            ["literature_search_executions.project_id", "literature_search_executions.id"],
            name="fk_lse_receipt_execution_same_project",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_lse_receipt_project", "literature_search_execution_command_receipts", ["project_id"]
    )
    op.create_index(
        "ix_lse_receipt_execution",
        "literature_search_execution_command_receipts",
        ["result_execution_id"],
    )
    op.create_index(
        "ix_lse_receipt_actor", "literature_search_execution_command_receipts", ["actor_id"]
    )

    # Direct-SQL backstops for immutable scientific observations and terminal closure.
    op.execute(
        """
        CREATE FUNCTION pr204_reject_immutable_child() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'PR2-04 immutable provenance row' USING ERRCODE = 'P17D1';
        END; $$;
        CREATE TRIGGER trg_pr204_query_immutable
          BEFORE UPDATE OR DELETE ON search_query_records
          FOR EACH ROW EXECUTE FUNCTION pr204_reject_immutable_child();
        CREATE TRIGGER trg_pr204_result_immutable
          BEFORE UPDATE OR DELETE ON search_result_records
          FOR EACH ROW EXECUTE FUNCTION pr204_reject_immutable_child();
        CREATE TRIGGER trg_pr204_event_immutable
          BEFORE UPDATE OR DELETE ON literature_search_execution_events
          FOR EACH ROW EXECUTE FUNCTION pr204_reject_immutable_child();
        CREATE TRIGGER trg_pr204_receipt_immutable
          BEFORE UPDATE OR DELETE ON literature_search_execution_command_receipts
          FOR EACH ROW EXECUTE FUNCTION pr204_reject_immutable_child();

        CREATE FUNCTION pr204_validate_terminal_receipt() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE execution_status text;
        DECLARE execution_row_version integer;
        BEGIN
          SELECT status, row_version
            INTO execution_status, execution_row_version
            FROM literature_search_executions
           WHERE id = NEW.result_execution_id
           FOR UPDATE;
          IF NOT FOUND THEN
            RAISE EXCEPTION 'PR2-04 receipt execution does not exist' USING ERRCODE = 'P17D2';
          END IF;
          IF execution_status IN ('SUCCEEDED','FAILED','CANCELLED','UNKNOWN') THEN
            IF NEW.command_name <> 'RECOVER_LITERATURE_SEARCH_EXECUTION'
               OR NEW.result_dto->>'accepted_row_version' <> execution_row_version::text THEN
              RAISE EXCEPTION 'PR2-04 terminal execution permits only a version-matched recovery receipt' USING ERRCODE = 'P17D3';
            END IF;
          END IF;
          RETURN NULL;
        END; $$;
        CREATE CONSTRAINT TRIGGER trg_pr204_terminal_receipt_guard
          AFTER INSERT ON literature_search_execution_command_receipts
          DEFERRABLE INITIALLY DEFERRED
          FOR EACH ROW EXECUTE FUNCTION pr204_validate_terminal_receipt();

        CREATE FUNCTION pr204_guard_execution_event_insert() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE execution_status text;
        DECLARE execution_row_version integer;
        DECLARE max_sequence integer;
        BEGIN
          SELECT status, row_version
            INTO execution_status, execution_row_version
            FROM literature_search_executions
           WHERE id = NEW.execution_id
           FOR UPDATE;
          IF NOT FOUND THEN
            RAISE EXCEPTION 'PR2-04 event execution does not exist' USING ERRCODE = 'P17D2';
          END IF;

          SELECT max(sequence) INTO max_sequence
            FROM literature_search_execution_events
           WHERE execution_id = NEW.execution_id;
          IF NEW.sequence <> COALESCE(max_sequence + 1, 0) THEN
            RAISE EXCEPTION 'PR2-04 event sequence must be contiguous' USING ERRCODE = 'P17D5';
          END IF;
          IF NEW.new_status IS DISTINCT FROM execution_status
             OR NEW.new_row_version <> execution_row_version THEN
            RAISE EXCEPTION 'PR2-04 event must match durable execution state' USING ERRCODE = 'P17D5';
          END IF;

          IF NEW.kind = 'CREATED' THEN
            IF NEW.sequence <> 0 OR NEW.prior_status IS NOT NULL
               OR NEW.prior_row_version IS NOT NULL
               OR execution_status <> 'PLANNED' OR execution_row_version <> 1 THEN
              RAISE EXCEPTION 'PR2-04 invalid CREATED event coordinates' USING ERRCODE = 'P17D5';
            END IF;
            RETURN NEW;
          END IF;

          IF NEW.prior_status IS NULL OR NEW.prior_row_version IS NULL
             OR NEW.prior_row_version <> NEW.new_row_version - 1 THEN
            RAISE EXCEPTION 'PR2-04 event prior coordinates are invalid' USING ERRCODE = 'P17D5';
          END IF;
          IF execution_status IN ('SUCCEEDED','FAILED','CANCELLED','UNKNOWN')
             AND NEW.kind <> 'FINISHED' THEN
            RAISE EXCEPTION 'PR2-04 no event may follow terminalization' USING ERRCODE = 'P17D3';
          END IF;
          IF NEW.kind = 'CANCEL_REQUESTED'
             AND (NEW.prior_status NOT IN ('PLANNED','RUNNING')
                  OR NEW.new_status <> NEW.prior_status) THEN
            RAISE EXCEPTION 'PR2-04 invalid cancellation-intent event' USING ERRCODE = 'P17D5';
          END IF;
          IF NEW.kind = 'ATTEMPT_RESERVED'
             AND NOT ((NEW.prior_status = 'PLANNED' AND NEW.new_status = 'RUNNING')
                      OR (NEW.prior_status = 'RUNNING' AND NEW.new_status = 'RUNNING')) THEN
            RAISE EXCEPTION 'PR2-04 invalid attempt-reservation event' USING ERRCODE = 'P17D5';
          END IF;
          IF NEW.kind = 'OUTCOME_RECORDED'
             AND (NEW.prior_status <> 'RUNNING' OR NEW.new_status <> 'RUNNING') THEN
            RAISE EXCEPTION 'PR2-04 invalid outcome event' USING ERRCODE = 'P17D5';
          END IF;
          IF NEW.kind = 'FINISHED'
             AND (NEW.prior_status NOT IN ('PLANNED','RUNNING')
                  OR NEW.new_status NOT IN ('SUCCEEDED','FAILED','CANCELLED','UNKNOWN')) THEN
            RAISE EXCEPTION 'PR2-04 invalid FINISHED event' USING ERRCODE = 'P17D5';
          END IF;
          RETURN NEW;
        END; $$;
        CREATE TRIGGER trg_pr204_execution_event_insert
          BEFORE INSERT ON literature_search_execution_events
          FOR EACH ROW EXECUTE FUNCTION pr204_guard_execution_event_insert();

        CREATE FUNCTION pr204_require_execution_event() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE matching_events integer;
        DECLARE context jsonb;
        DECLARE context_integer_key text;
        DECLARE query_item jsonb;
        DECLARE query_total integer;
        DECLARE reserved_total integer;
        DECLARE unknown_total integer;
        DECLARE successful_query_total integer;
        BEGIN
          IF TG_OP = 'INSERT' THEN
            -- Admission only: later supersession preserves this exact historical binding.
            IF NOT EXISTS (
              SELECT 1 FROM literature_search_plan_versions v
              JOIN literature_search_plans p ON p.id = v.plan_id
              WHERE v.id = NEW.search_plan_version_id
                AND p.project_id = NEW.project_id AND v.status = 'FROZEN'
            ) THEN
              RAISE EXCEPTION 'PR2-04 admission requires a same-project FROZEN plan version'
                USING ERRCODE = 'P17D5';
            END IF;
            context := NEW.execution_context;
            -- Prove JSON integer types before casts: text extraction alone
            -- would coerce numeric strings and let JSON null evade bounds.
            FOREACH context_integer_key IN ARRAY ARRAY[
              'max_results','max_provider_attempts','timeout_seconds','execution_budget_seconds'
            ] LOOP
              IF jsonb_typeof(context->context_integer_key) IS DISTINCT FROM 'number'
                 OR (context->>context_integer_key) !~ '^-?[0-9]+$' THEN
                RAISE EXCEPTION 'PR2-04 execution context requires JSON integers' USING ERRCODE = 'P17D5';
              END IF;
            END LOOP;
            IF jsonb_typeof(context) <> 'object'
               OR NOT (context ?& ARRAY['schema_version','provider_id','provider_version','queries','max_results','max_provider_attempts','timeout_seconds','execution_budget_seconds'])
               OR context - ARRAY['schema_version','provider_id','provider_version','queries','max_results','max_provider_attempts','timeout_seconds','execution_budget_seconds'] <> '{}'::jsonb
               OR context->>'schema_version' <> '1'
               OR jsonb_typeof(context->'provider_id') <> 'string'
               OR normalize(context->>'provider_id', NFC) IS DISTINCT FROM context->>'provider_id'
               OR length(btrim(context->>'provider_id', U&'\\0009\\000A\\000B\\000C\\000D\\001C\\001D\\001E\\001F\\0020\\0085\\00A0\\1680\\2000\\2001\\2002\\2003\\2004\\2005\\2006\\2007\\2008\\2009\\200A\\2028\\2029\\202F\\205F\\3000')) = 0
               OR length(context->>'provider_id') NOT BETWEEN 1 AND 128
               OR jsonb_typeof(context->'provider_version') <> 'string'
               OR normalize(context->>'provider_version', NFC) IS DISTINCT FROM context->>'provider_version'
               OR length(btrim(context->>'provider_version', U&'\\0009\\000A\\000B\\000C\\000D\\001C\\001D\\001E\\001F\\0020\\0085\\00A0\\1680\\2000\\2001\\2002\\2003\\2004\\2005\\2006\\2007\\2008\\2009\\200A\\2028\\2029\\202F\\205F\\3000')) = 0
               OR length(context->>'provider_version') NOT BETWEEN 1 AND 128
               OR jsonb_typeof(context->'queries') <> 'array'
               OR jsonb_array_length(context->'queries') NOT BETWEEN 1 AND 32
               OR (context->>'max_results')::numeric NOT BETWEEN 1 AND 100
               OR (context->>'max_provider_attempts')::numeric NOT BETWEEN 1 AND 3
               OR (context->>'timeout_seconds')::numeric NOT BETWEEN 1 AND 30
               OR (context->>'execution_budget_seconds')::numeric NOT BETWEEN 1 AND 600 THEN
              RAISE EXCEPTION 'PR2-04 execution context has an invalid closed shape' USING ERRCODE = 'P17D5';
            END IF;
            FOR query_item IN SELECT value FROM jsonb_array_elements(context->'queries') LOOP
              IF jsonb_typeof(query_item) <> 'object'
                 OR NOT (query_item ?& ARRAY['query_type','query_text','perspective'])
                 OR query_item - ARRAY['query_type','query_text','perspective'] <> '{}'::jsonb
                 OR query_item->>'query_type' <> 'TEXT'
                 OR jsonb_typeof(query_item->'query_text') <> 'string'
                 OR length(btrim(query_item->>'query_text')) NOT BETWEEN 1 AND 4096
                 OR (jsonb_typeof(query_item->'perspective') NOT IN ('null','string'))
                 OR (jsonb_typeof(query_item->'perspective') = 'string'
                     AND length(query_item->>'perspective') > 256) THEN
                RAISE EXCEPTION 'PR2-04 query input has an invalid closed shape' USING ERRCODE = 'P17D5';
              END IF;
            END LOOP;
            SELECT count(*) INTO matching_events
              FROM literature_search_execution_events
             WHERE execution_id = NEW.id AND kind = 'CREATED'
               AND sequence = 0 AND prior_status IS NULL
               AND new_status = NEW.status AND new_row_version = NEW.row_version
               AND prior_row_version IS NULL;
          ELSE
            SELECT count(*) INTO matching_events
              FROM literature_search_execution_events
             WHERE execution_id = NEW.id
               AND prior_status = OLD.status AND new_status = NEW.status
               AND prior_row_version = OLD.row_version
               AND new_row_version = NEW.row_version;
          END IF;
          IF matching_events <> 1 THEN
            RAISE EXCEPTION 'PR2-04 execution mutation requires exactly one matching event'
              USING ERRCODE = 'P17D5';
          END IF;
          IF TG_OP = 'UPDATE' AND NEW.status IS DISTINCT FROM OLD.status THEN
            SELECT count(*) INTO reserved_total
              FROM literature_search_provider_attempts
             WHERE execution_id = NEW.id AND status = 'RESERVED';
            SELECT count(*) INTO unknown_total
              FROM literature_search_provider_attempts
             WHERE execution_id = NEW.id AND status = 'UNKNOWN';
            IF NEW.status = 'RUNNING' AND reserved_total <> 1 THEN
              RAISE EXCEPTION 'PR2-04 RUNNING transition requires one reserved attempt' USING ERRCODE = 'P17D5';
            ELSIF NEW.status = 'SUCCEEDED' THEN
              SELECT count(DISTINCT query_index) INTO successful_query_total
                FROM literature_search_provider_attempts
               WHERE execution_id = NEW.id AND status = 'SUCCEEDED';
              IF successful_query_total <> jsonb_array_length(NEW.execution_context->'queries') THEN
                RAISE EXCEPTION 'PR2-04 SUCCEEDED requires every input query' USING ERRCODE = 'P17D5';
              END IF;
            ELSIF NEW.status = 'UNKNOWN' AND unknown_total = 0 THEN
              RAISE EXCEPTION 'PR2-04 UNKNOWN requires an uncertain provider attempt' USING ERRCODE = 'P17D5';
            ELSIF NEW.status = 'CANCELLED' THEN
              IF reserved_total <> 0 OR unknown_total <> 0 OR NOT EXISTS (
                SELECT 1 FROM literature_search_execution_events
                 WHERE execution_id = NEW.id AND kind = 'CANCEL_REQUESTED'
              ) THEN
                RAISE EXCEPTION 'PR2-04 CANCELLED requires resolved cancellation intent' USING ERRCODE = 'P17D5';
              END IF;
              IF OLD.status = 'PLANNED' AND EXISTS (
                SELECT 1 FROM literature_search_provider_attempts WHERE execution_id = NEW.id
              ) THEN
                RAISE EXCEPTION 'PR2-04 pre-start cancellation cannot have attempts' USING ERRCODE = 'P17D5';
              END IF;
            ELSIF NEW.status = 'FAILED'
              AND NEW.failure_code NOT IN ('PROVIDER_PERMANENT','PROVIDER_MALFORMED','PROVIDER_RETRY_EXHAUSTED','RECOVERY_INTERRUPTED') THEN
              RAISE EXCEPTION 'PR2-04 FAILED reason is not canonical' USING ERRCODE = 'P17D5';
            END IF;
          END IF;
          RETURN NULL;
        END; $$;
        CREATE CONSTRAINT TRIGGER trg_pr204_execution_created_event_commit
          AFTER INSERT ON literature_search_executions
          DEFERRABLE INITIALLY DEFERRED
          FOR EACH ROW EXECUTE FUNCTION pr204_require_execution_event();
        CREATE CONSTRAINT TRIGGER trg_pr204_execution_event_commit
          AFTER UPDATE ON literature_search_executions
          DEFERRABLE INITIALLY DEFERRED
          FOR EACH ROW EXECUTE FUNCTION pr204_require_execution_event();
        """
    )
    op.execute(
        """
        CREATE FUNCTION pr204_guard_execution_update() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF OLD.status IN ('SUCCEEDED','FAILED','CANCELLED','UNKNOWN') AND NEW IS DISTINCT FROM OLD THEN
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
            RAISE EXCEPTION 'PR2-04 executed_by may be assigned only at start' USING ERRCODE = 'P17D1';
          END IF;
          IF NEW.started_at IS DISTINCT FROM OLD.started_at
             AND NOT (OLD.status = 'PLANNED' AND NEW.status = 'RUNNING'
                      AND OLD.started_at IS NULL AND NEW.started_at IS NOT NULL) THEN
            RAISE EXCEPTION 'PR2-04 started_at may be assigned only at start' USING ERRCODE = 'P17D4';
          END IF;
          IF NEW.finished_at IS DISTINCT FROM OLD.finished_at
             AND NOT (OLD.status IN ('PLANNED','RUNNING')
                      AND NEW.status IN ('SUCCEEDED','FAILED','CANCELLED','UNKNOWN')
                      AND OLD.finished_at IS NULL AND NEW.finished_at IS NOT NULL) THEN
            RAISE EXCEPTION 'PR2-04 finished_at may be assigned only at finalization' USING ERRCODE = 'P17D4';
          END IF;
          IF NEW.failure_code IS DISTINCT FROM OLD.failure_code
             AND NOT (NEW.status IN ('FAILED','CANCELLED','UNKNOWN')
                      AND OLD.status IN ('PLANNED','RUNNING')) THEN
            RAISE EXCEPTION 'PR2-04 failure_code may change only at terminalization' USING ERRCODE = 'P17D4';
          END IF;
          IF NEW.row_version <> OLD.row_version + 1 THEN
            RAISE EXCEPTION 'PR2-04 execution row_version must advance once' USING ERRCODE = 'P17D5';
          END IF;
          RETURN NEW;
        END; $$;
        CREATE TRIGGER trg_pr204_execution_update_guard
          BEFORE UPDATE ON literature_search_executions
          FOR EACH ROW EXECUTE FUNCTION pr204_guard_execution_update();

        CREATE FUNCTION pr204_guard_attempt_update() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE execution_status text;
        BEGIN
          SELECT status INTO execution_status
            FROM literature_search_executions
           WHERE id = NEW.execution_id
           FOR UPDATE;
          IF execution_status IN ('SUCCEEDED','FAILED','CANCELLED','UNKNOWN') THEN
            RAISE EXCEPTION 'PR2-04 terminal execution cannot seal new outcomes' USING ERRCODE = 'P17D3';
          END IF;
          IF OLD.status <> 'RESERVED' THEN
            RAISE EXCEPTION 'PR2-04 provider attempt is sealed' USING ERRCODE = 'P17D1';
          END IF;
          IF NEW.id IS DISTINCT FROM OLD.id
             OR NEW.execution_id IS DISTINCT FROM OLD.execution_id
             OR NEW.query_index IS DISTINCT FROM OLD.query_index
             OR NEW.attempt_number IS DISTINCT FROM OLD.attempt_number
             OR NEW.provider_request_key IS DISTINCT FROM OLD.provider_request_key
             OR NEW.reserved_at IS DISTINCT FROM OLD.reserved_at
             OR NEW.deadline_at IS DISTINCT FROM OLD.deadline_at
             OR NEW.recovery_after IS DISTINCT FROM OLD.recovery_after
             OR NEW.created_by IS DISTINCT FROM OLD.created_by
             OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
            RAISE EXCEPTION 'PR2-04 attempt reservation material is immutable' USING ERRCODE = 'P17D1';
          END IF;
          IF NEW.status = 'RESERVED' OR NEW.row_version <> OLD.row_version + 1 THEN
            RAISE EXCEPTION 'PR2-04 invalid attempt seal' USING ERRCODE = 'P17D5';
          END IF;
          RETURN NEW;
        END; $$;
        CREATE TRIGGER trg_pr204_attempt_seal_guard
          BEFORE UPDATE ON literature_search_provider_attempts
          FOR EACH ROW EXECUTE FUNCTION pr204_guard_attempt_update();
        CREATE FUNCTION pr204_guard_attempt_insert() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF NEW.status <> 'RESERVED' OR NEW.row_version <> 1
             OR NEW.provider_request_key <> NEW.id THEN
            RAISE EXCEPTION 'PR2-04 attempts must begin as a version-one reservation' USING ERRCODE = 'P17D5';
          END IF;
          RETURN NEW;
        END; $$;
        CREATE TRIGGER trg_pr204_attempt_insert_guard
          BEFORE INSERT ON literature_search_provider_attempts
          FOR EACH ROW EXECUTE FUNCTION pr204_guard_attempt_insert();
        CREATE TRIGGER trg_pr204_attempt_no_delete
          BEFORE DELETE ON literature_search_provider_attempts
          FOR EACH ROW EXECUTE FUNCTION pr204_reject_immutable_child();
        """
    )
    op.execute(
        """
        CREATE FUNCTION pr204_reject_terminal_child() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE execution_status text;
        DECLARE target_execution_id uuid;
        BEGIN
          IF TG_TABLE_NAME = 'literature_search_provider_attempts' THEN
            target_execution_id := NEW.execution_id;
          ELSE
            target_execution_id := NEW.literature_search_execution_id;
          END IF;
          SELECT status INTO execution_status
            FROM literature_search_executions
           WHERE id = target_execution_id
           FOR UPDATE;
          IF execution_status IN ('SUCCEEDED','FAILED','CANCELLED','UNKNOWN') THEN
            RAISE EXCEPTION 'PR2-04 terminal execution cannot gain new provenance' USING ERRCODE = 'P17D3';
          END IF;
          RETURN NEW;
        END; $$;
        CREATE TRIGGER trg_pr204_attempt_terminal_guard
          BEFORE INSERT ON literature_search_provider_attempts
          FOR EACH ROW EXECUTE FUNCTION pr204_reject_terminal_child();
        CREATE TRIGGER trg_pr204_query_terminal_guard
          BEFORE INSERT ON search_query_records
          FOR EACH ROW EXECUTE FUNCTION pr204_reject_terminal_child();
        CREATE FUNCTION pr204_reject_terminal_result() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE target_execution_id uuid;
        DECLARE execution_status text;
        BEGIN
          SELECT literature_search_execution_id INTO target_execution_id
            FROM search_query_records WHERE id = NEW.search_query_record_id;
          SELECT status INTO execution_status
            FROM literature_search_executions
           WHERE id = target_execution_id
           FOR UPDATE;
          IF execution_status IN ('SUCCEEDED','FAILED','CANCELLED','UNKNOWN') THEN
            RAISE EXCEPTION 'PR2-04 terminal execution cannot gain new results' USING ERRCODE = 'P17D3';
          END IF;
          RETURN NEW;
        END; $$;
        CREATE TRIGGER trg_pr204_result_terminal_guard
          BEFORE INSERT ON search_result_records
          FOR EACH ROW EXECUTE FUNCTION pr204_reject_terminal_result();
        """
    )
    op.execute(
        """
        CREATE FUNCTION pr204_validate_attempt_provenance() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE target_attempt_id uuid;
        DECLARE target_query_id uuid;
        DECLARE target_execution_id uuid;
        DECLARE attempt_status text;
        DECLARE attempt_query_id uuid;
        DECLARE attempt_result_count integer;
        DECLARE actual_result_count integer;
        DECLARE invocation_time timestamptz;
        DECLARE execution_context jsonb;
        DECLARE execution_status text;
        DECLARE input_query jsonb;
        DECLARE query_ordinal_count integer;
        DECLARE query_ordinal_max integer;
        DECLARE attempt_ordinal_count integer;
        DECLARE attempt_ordinal_max integer;
        DECLARE result_rank_count integer;
        DECLARE result_rank_max integer;
        DECLARE warning_count integer;
        DECLARE distinct_warning_count integer;
        DECLARE attempt_total integer;
        DECLARE previous_success_count integer;
        DECLARE previous_attempt_status text;
        DECLARE previous_completed_at timestamptz;
        DECLARE previous_retry_after integer;
        DECLARE execution_started_at timestamptz;
        BEGIN
          IF TG_TABLE_NAME = 'literature_search_provider_attempts' THEN
            target_attempt_id := NEW.id;
          ELSIF TG_TABLE_NAME = 'search_query_records' THEN
            target_attempt_id := NEW.provider_attempt_id;
          ELSE
            target_query_id := NEW.search_query_record_id;
            SELECT provider_attempt_id INTO target_attempt_id
              FROM search_query_records WHERE id = target_query_id;
          END IF;

          SELECT execution_id, status, query_record_id, result_count, invoked_at
            INTO target_execution_id, attempt_status, attempt_query_id,
                 attempt_result_count, invocation_time
            FROM literature_search_provider_attempts
           WHERE id = target_attempt_id;
          IF NOT FOUND THEN
            RAISE EXCEPTION 'PR2-04 provenance attempt does not exist' USING ERRCODE = 'P17D2';
          END IF;
          SELECT e.execution_context, e.status, e.started_at
            INTO execution_context, execution_status, execution_started_at
            FROM literature_search_executions e WHERE e.id = target_execution_id;
          IF attempt_status = 'RESERVED' THEN
            IF EXISTS (SELECT 1 FROM search_query_records WHERE provider_attempt_id = target_attempt_id) THEN
              RAISE EXCEPTION 'PR2-04 query requires a sealed attempt' USING ERRCODE = 'P17D5';
            END IF;
            SELECT count(*) INTO attempt_total FROM literature_search_provider_attempts
             WHERE execution_id = target_execution_id;
            SELECT count(*), max(attempt_number)
              INTO attempt_ordinal_count, attempt_ordinal_max
              FROM literature_search_provider_attempts
             WHERE execution_id = target_execution_id
               AND query_index = (SELECT query_index FROM literature_search_provider_attempts WHERE id = target_attempt_id);
            SELECT count(DISTINCT query_index) INTO previous_success_count
              FROM literature_search_provider_attempts
             WHERE execution_id = target_execution_id
               AND query_index < (SELECT query_index FROM literature_search_provider_attempts WHERE id = target_attempt_id)
               AND status = 'SUCCEEDED';
            IF execution_status <> 'RUNNING'
               OR (SELECT query_index FROM literature_search_provider_attempts WHERE id = target_attempt_id)
                    >= jsonb_array_length(execution_context->'queries')
               OR attempt_total > 96
               OR attempt_ordinal_count <> attempt_ordinal_max
               OR attempt_ordinal_count > (execution_context->>'max_provider_attempts')::integer
               OR previous_success_count <> (SELECT query_index FROM literature_search_provider_attempts WHERE id = target_attempt_id)
               OR execution_started_at IS NULL THEN
              RAISE EXCEPTION 'PR2-04 reservation violates execution/query attempt bounds' USING ERRCODE = 'P17D5';
            END IF;
            IF (SELECT attempt_number FROM literature_search_provider_attempts WHERE id = target_attempt_id) > 1 THEN
              SELECT status, completed_at, retry_after_seconds
                INTO previous_attempt_status, previous_completed_at, previous_retry_after
                FROM literature_search_provider_attempts
               WHERE execution_id = target_execution_id
                 AND query_index = (SELECT query_index FROM literature_search_provider_attempts WHERE id = target_attempt_id)
                 AND attempt_number = (SELECT attempt_number - 1 FROM literature_search_provider_attempts WHERE id = target_attempt_id);
              IF previous_attempt_status <> 'RETRYABLE_FAILURE'
                 OR (previous_retry_after IS NOT NULL AND clock_timestamp() < previous_completed_at + make_interval(secs => previous_retry_after)) THEN
                RAISE EXCEPTION 'PR2-04 retry reservation lacks known-safe predecessor or Retry-After elapsed' USING ERRCODE = 'P17D5';
              END IF;
            END IF;
            RETURN NULL;
          END IF;

          IF invocation_time IS NOT NULL AND attempt_query_id IS NULL THEN
            RAISE EXCEPTION 'PR2-04 invoked attempt requires query provenance' USING ERRCODE = 'P17D5';
          END IF;
          IF attempt_query_id IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM search_query_records q
             WHERE q.id = attempt_query_id
               AND q.provider_attempt_id = target_attempt_id
               AND q.literature_search_execution_id = target_execution_id
          ) THEN
            RAISE EXCEPTION 'PR2-04 attempt/query provenance mismatch' USING ERRCODE = 'P17D5';
          END IF;
          IF attempt_query_id IS NOT NULL THEN
            input_query := execution_context->'queries'->(
              SELECT query_index FROM literature_search_provider_attempts WHERE id = target_attempt_id
            );
            IF NOT EXISTS (
              SELECT 1 FROM search_query_records q
               WHERE q.id = attempt_query_id
                 AND q.query_text = input_query->>'query_text'
                 AND q.perspective IS NOT DISTINCT FROM NULLIF(input_query->>'perspective','')
                 AND q.provider_id = execution_context->>'provider_id'
                 AND q.provider_version = execution_context->>'provider_version'
                 AND q.executed_at = invocation_time
            ) THEN
              RAISE EXCEPTION 'PR2-04 query differs from admitted input/invocation' USING ERRCODE = 'P17D5';
            END IF;
          END IF;
          SELECT count(*), max(ordinal) INTO query_ordinal_count, query_ordinal_max
            FROM search_query_records WHERE literature_search_execution_id = target_execution_id;
          IF query_ordinal_count > 0 AND query_ordinal_max <> query_ordinal_count - 1 THEN
            RAISE EXCEPTION 'PR2-04 query ordinals must be contiguous' USING ERRCODE = 'P17D5';
          END IF;
          SELECT count(*), max(attempt_number)
            INTO attempt_ordinal_count, attempt_ordinal_max
            FROM literature_search_provider_attempts
           WHERE execution_id = target_execution_id
             AND query_index = (SELECT query_index FROM literature_search_provider_attempts WHERE id = target_attempt_id);
          IF attempt_ordinal_count <> attempt_ordinal_max THEN
            RAISE EXCEPTION 'PR2-04 attempt ordinals must be contiguous' USING ERRCODE = 'P17D5';
          END IF;
          SELECT count(*) INTO actual_result_count
            FROM search_result_records r
            JOIN search_query_records q ON q.id = r.search_query_record_id
           WHERE q.provider_attempt_id = target_attempt_id
             AND q.literature_search_execution_id = target_execution_id;
          IF attempt_status = 'SUCCEEDED' THEN
            IF (SELECT count(DISTINCT retrieved_at) FROM search_result_records
                 WHERE search_query_record_id = attempt_query_id) > 1 THEN
              RAISE EXCEPTION 'PR2-04 response retrieval timestamps must be uniform' USING ERRCODE = 'P17D5';
            END IF;
            IF EXISTS (
              SELECT 1 FROM search_result_records r
               WHERE r.search_query_record_id = attempt_query_id
                 AND r.retrieved_at IS DISTINCT FROM (
                   SELECT a.retrieved_at FROM literature_search_provider_attempts a
                    WHERE a.id = target_attempt_id
                 )
            ) THEN
              RAISE EXCEPTION 'PR2-04 results must copy attempt retrieval observation' USING ERRCODE = 'P17D5';
            END IF;
            IF attempt_query_id IS NULL OR attempt_result_count IS NULL
               OR actual_result_count <> attempt_result_count THEN
              RAISE EXCEPTION 'PR2-04 successful attempt result count mismatch' USING ERRCODE = 'P17D5';
            END IF;
          ELSIF attempt_result_count <> 0 OR actual_result_count <> 0 THEN
            RAISE EXCEPTION 'PR2-04 failed attempt cannot retain result rows' USING ERRCODE = 'P17D5';
          END IF;
          IF attempt_query_id IS NOT NULL THEN
            SELECT count(*), max(rank) INTO result_rank_count, result_rank_max
              FROM search_result_records WHERE search_query_record_id = attempt_query_id;
            IF result_rank_count > 0 AND result_rank_max <> result_rank_count - 1 THEN
              RAISE EXCEPTION 'PR2-04 result ranks must be contiguous' USING ERRCODE = 'P17D5';
            END IF;
          END IF;
          SELECT count(*), count(DISTINCT value)
            INTO warning_count, distinct_warning_count
            FROM jsonb_array_elements_text(
              COALESCE((SELECT warning_codes FROM literature_search_provider_attempts WHERE id = target_attempt_id), '[]'::jsonb)
            ) AS warnings(value);
          IF warning_count <> distinct_warning_count THEN
            RAISE EXCEPTION 'PR2-04 warning codes must be unique' USING ERRCODE = 'P17D5';
          END IF;
          RETURN NULL;
        END; $$;
        CREATE CONSTRAINT TRIGGER trg_pr204_attempt_outcome_commit
          AFTER INSERT OR UPDATE ON literature_search_provider_attempts
          DEFERRABLE INITIALLY DEFERRED
          FOR EACH ROW EXECUTE FUNCTION pr204_validate_attempt_provenance();
        CREATE CONSTRAINT TRIGGER trg_pr204_query_outcome_commit
          AFTER INSERT ON search_query_records
          DEFERRABLE INITIALLY DEFERRED
          FOR EACH ROW EXECUTE FUNCTION pr204_validate_attempt_provenance();
        CREATE CONSTRAINT TRIGGER trg_pr204_result_outcome_commit
          AFTER INSERT ON search_result_records
          DEFERRABLE INITIALLY DEFERRED
          FOR EACH ROW EXECUTE FUNCTION pr204_validate_attempt_provenance();
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    tables = (
        "literature_search_execution_command_receipts",
        "literature_search_execution_events",
        "search_result_records",
        "search_query_records",
        "literature_search_provider_attempts",
        "literature_search_executions",
    )
    if any(
        bind.execute(sa.text(f"SELECT EXISTS (SELECT 1 FROM {table} LIMIT 1)")).scalar()
        for table in tables
    ):
        raise RuntimeError("0024 downgrade requires all PR2-04 tables to be empty")
    op.drop_constraint(
        "fk_lspa_query_record", "literature_search_provider_attempts", type_="foreignkey"
    )
    op.execute("DROP FUNCTION IF EXISTS pr204_reject_terminal_child() CASCADE")
    op.execute("DROP FUNCTION IF EXISTS pr204_reject_terminal_result() CASCADE")
    op.execute("DROP FUNCTION IF EXISTS pr204_guard_attempt_update() CASCADE")
    op.execute("DROP FUNCTION IF EXISTS pr204_guard_attempt_insert() CASCADE")
    op.execute("DROP FUNCTION IF EXISTS pr204_guard_execution_update() CASCADE")
    op.execute("DROP FUNCTION IF EXISTS pr204_require_execution_event() CASCADE")
    op.execute("DROP FUNCTION IF EXISTS pr204_guard_execution_event_insert() CASCADE")
    op.execute("DROP FUNCTION IF EXISTS pr204_validate_attempt_provenance() CASCADE")
    op.execute("DROP FUNCTION IF EXISTS pr204_reject_immutable_child() CASCADE")
    op.execute("DROP FUNCTION IF EXISTS pr204_validate_terminal_receipt() CASCADE")
    for table in tables:
        op.drop_table(table)
