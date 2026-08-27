"""Create PR-09 Run Core tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_run_core"
down_revision: str | None = "0007_metric_definition"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "runs",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "project_id", uuid, sa.ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column(
            "experiment_spec_version_id",
            uuid,
            sa.ForeignKey("experiment_spec_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "run_type", sa.String(length=32), server_default=sa.text("'experiment'"), nullable=False
        ),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("inputs_sealed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_by", uuid, sa.ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint(
            "status IN ('PLANNED','RUNNING','SUCCEEDED','FAILED','CANCELLED')",
            name="ck_runs_status",
        ),
        sa.CheckConstraint(
            "(status = 'PLANNED' AND inputs_sealed_at IS NULL) OR "
            "(status <> 'PLANNED' AND inputs_sealed_at IS NOT NULL)",
            name="ck_runs_inputs_sealed",
        ),
    )
    op.create_table(
        "run_dataset_inputs",
        sa.Column("run_id", uuid, sa.ForeignKey("runs.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column(
            "dataset_snapshot_id",
            uuid,
            sa.ForeignKey("dataset_snapshots.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("role", sa.String(length=32), primary_key=True),
        sa.Column("ordinal", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.CheckConstraint(
            "role IN ('train','validation','test','calibration','auxiliary','other')",
            name="ck_run_dataset_inputs_role",
        ),
    )
    op.create_table(
        "run_artifact_inputs",
        sa.Column("run_id", uuid, sa.ForeignKey("runs.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column(
            "artifact_version_id",
            uuid,
            sa.ForeignKey("artifact_versions.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("role", sa.String(length=32), primary_key=True),
        sa.Column("ordinal", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.CheckConstraint(
            "role IN ('source_code','model','checkpoint','configuration','environment_manifest',"
            "'script','dependency_lock','other')",
            name="ck_run_artifact_inputs_role",
        ),
    )
    op.execute(
        """
        CREATE FUNCTION reject_sealed_run_input_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE sealed_at timestamptz;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                SELECT inputs_sealed_at INTO sealed_at FROM runs WHERE id = OLD.run_id;
            ELSE
                SELECT inputs_sealed_at INTO sealed_at FROM runs WHERE id = NEW.run_id;
            END IF;
            IF sealed_at IS NOT NULL THEN
                RAISE EXCEPTION 'sealed run inputs are immutable' USING ERRCODE = 'check_violation';
            END IF;
            RETURN COALESCE(NEW, OLD);
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER run_dataset_inputs_sealed_immutable
        BEFORE INSERT OR UPDATE OR DELETE ON run_dataset_inputs
        FOR EACH ROW EXECUTE FUNCTION reject_sealed_run_input_mutation()
        """
    )
    op.execute(
        """
        CREATE TRIGGER run_artifact_inputs_sealed_immutable
        BEFORE INSERT OR UPDATE OR DELETE ON run_artifact_inputs
        FOR EACH ROW EXECUTE FUNCTION reject_sealed_run_input_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER run_artifact_inputs_sealed_immutable ON run_artifact_inputs")
    op.execute("DROP TRIGGER run_dataset_inputs_sealed_immutable ON run_dataset_inputs")
    op.execute("DROP FUNCTION reject_sealed_run_input_mutation()")
    op.drop_table("run_artifact_inputs")
    op.drop_table("run_dataset_inputs")
    op.drop_table("runs")
