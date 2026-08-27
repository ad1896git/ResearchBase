"""Create PR-08 MetricDefinition and MetricDefinitionVersion tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_metric_definition"
down_revision: str | None = "0006_artifact_version"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "metric_definitions",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("project_id", uuid, nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("current_version_id", uuid, nullable=True),
        sa.Column(
            "created_by", uuid, sa.ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
    )
    op.create_table(
        "metric_definition_versions",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "metric_definition_id",
            uuid,
            sa.ForeignKey("metric_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("definition", postgresql.JSONB(), nullable=False),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("aggregation", sa.String(length=64), nullable=True),
        sa.Column("content_hash", sa.CHAR(length=64), nullable=True),
        sa.Column(
            "created_by", uuid, sa.ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("row_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint(
            "version_number > 0", name="ck_metric_definition_versions_version_number"
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'FROZEN', 'SUPERSEDED', 'ABANDONED')",
            name="ck_metric_definition_versions_status",
        ),
        sa.UniqueConstraint(
            "metric_definition_id",
            "version_number",
            name="uq_metric_definition_versions_parent_version",
        ),
    )
    op.create_foreign_key(
        "fk_metric_definitions_current_version_id",
        "metric_definitions",
        "metric_definition_versions",
        ["current_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.execute(
        """
        CREATE FUNCTION reject_frozen_metric_definition_version_material_update() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.status IN ('FROZEN', 'SUPERSEDED') AND (
                NEW.metric_definition_id IS DISTINCT FROM OLD.metric_definition_id OR
                NEW.version_number IS DISTINCT FROM OLD.version_number OR
                NEW.definition IS DISTINCT FROM OLD.definition OR
                NEW.unit IS DISTINCT FROM OLD.unit OR
                NEW.aggregation IS DISTINCT FROM OLD.aggregation OR
                NEW.content_hash IS DISTINCT FROM OLD.content_hash OR
                NEW.created_by IS DISTINCT FROM OLD.created_by OR
                NEW.created_at IS DISTINCT FROM OLD.created_at
            ) THEN
                RAISE EXCEPTION 'frozen metric definition version material is immutable'
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER metric_definition_versions_frozen_immutable
        BEFORE UPDATE ON metric_definition_versions
        FOR EACH ROW EXECUTE FUNCTION reject_frozen_metric_definition_version_material_update()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER metric_definition_versions_frozen_immutable ON metric_definition_versions"
    )
    op.execute("DROP FUNCTION reject_frozen_metric_definition_version_material_update()")
    op.drop_constraint(
        "fk_metric_definitions_current_version_id", "metric_definitions", type_="foreignkey"
    )
    op.drop_table("metric_definition_versions")
    op.drop_table("metric_definitions")
