"""Create PR-11 immutable StatisticalResult records and Measurement inputs."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_statistical_result"
down_revision: str | None = "0010_measurement"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "statistical_results",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "project_id",
            uuid,
            sa.ForeignKey("projects.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("analysis_type", sa.String(length=64), nullable=False),
        sa.Column("result_payload", postgresql.JSONB(), nullable=False),
        sa.Column("analysis_definition", postgresql.JSONB(), nullable=False),
        sa.Column("content_hash", sa.CHAR(length=64), nullable=False),
        sa.Column(
            "created_by",
            uuid,
            sa.ForeignKey("actors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "statistical_result_inputs",
        sa.Column(
            "statistical_result_id",
            uuid,
            sa.ForeignKey("statistical_results.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "measurement_id",
            uuid,
            sa.ForeignKey("measurements.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "input_role",
            sa.String(length=32),
            primary_key=True,
            server_default=sa.text("'input'"),
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.execute(
        """
        CREATE FUNCTION reject_statistical_result_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'statistical_results are immutable' USING ERRCODE = 'check_violation';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER statistical_results_immutable
        BEFORE UPDATE OR DELETE ON statistical_results
        FOR EACH ROW EXECUTE FUNCTION reject_statistical_result_mutation()
        """
    )
    op.execute(
        """
        CREATE FUNCTION reject_statistical_result_input_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'INSERT' AND
               EXISTS (
                   SELECT 1
                   FROM statistical_results
                   WHERE id = NEW.statistical_result_id
                     AND xmin::text::bigint = txid_current()
               ) THEN
                RETURN NEW;
            END IF;
            RAISE EXCEPTION 'statistical_result_inputs are immutable'
                USING ERRCODE = 'check_violation';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER statistical_result_inputs_immutable
        BEFORE INSERT OR UPDATE OR DELETE ON statistical_result_inputs
        FOR EACH ROW EXECUTE FUNCTION reject_statistical_result_input_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER statistical_result_inputs_immutable ON statistical_result_inputs")
    op.execute("DROP FUNCTION reject_statistical_result_input_mutation()")
    op.execute("DROP TRIGGER statistical_results_immutable ON statistical_results")
    op.execute("DROP FUNCTION reject_statistical_result_mutation()")
    op.drop_table("statistical_result_inputs")
    op.drop_table("statistical_results")
