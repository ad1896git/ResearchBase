"""Create PR-10 immutable Measurement records."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_measurement"
down_revision: str | None = "0009_run_input_seal_fix"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "measurements",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("run_id", uuid, sa.ForeignKey("runs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column(
            "metric_definition_version_id",
            uuid,
            sa.ForeignKey("metric_definition_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("numeric_value", postgresql.DOUBLE_PRECISION(), nullable=True),
        sa.Column("structured_value", postgresql.JSONB(), nullable=True),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("evaluation_scope", postgresql.JSONB(), nullable=True),
        sa.Column("content_hash", sa.CHAR(length=64), nullable=False),
        sa.Column(
            "created_by", uuid, sa.ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(numeric_value IS NOT NULL AND structured_value IS NULL) OR "
            "(numeric_value IS NULL AND structured_value IS NOT NULL)",
            name="ck_measurements_value_xor",
        ),
    )
    op.execute(
        """
        CREATE FUNCTION reject_measurement_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'measurements are immutable' USING ERRCODE = 'check_violation';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER measurements_immutable
        BEFORE UPDATE OR DELETE ON measurements
        FOR EACH ROW EXECUTE FUNCTION reject_measurement_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER measurements_immutable ON measurements")
    op.execute("DROP FUNCTION reject_measurement_mutation()")
    op.drop_table("measurements")
