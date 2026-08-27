"""Create PR-06 Dataset and immutable DatasetSnapshot tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_dataset_snapshot"
down_revision: str | None = "0004_experiment_spec"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    jsonb = postgresql.JSONB()
    op.create_table(
        "datasets",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "project_id", uuid, sa.ForeignKey("projects.id", ondelete="RESTRICT"), nullable=True
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_locator", sa.Text(), nullable=True),
        sa.Column(
            "lifecycle_status", sa.String(length=20), nullable=False, server_default="active"
        ),
        sa.Column(
            "created_by", uuid, sa.ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint(
            "lifecycle_status IN ('active', 'archived', 'retired')",
            name="ck_datasets_lifecycle_status",
        ),
    )
    op.create_table(
        "dataset_snapshots",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "dataset_id", uuid, sa.ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("manifest_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("selection_definition", jsonb, nullable=False),
        sa.Column("manifest_locator", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.CHAR(length=64), nullable=False),
        sa.Column(
            "created_by", uuid, sa.ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "dataset_id", "content_hash", name="uq_dataset_snapshots_dataset_content_hash"
        ),
    )
    op.execute(
        """
        CREATE FUNCTION reject_dataset_snapshot_update() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'dataset_snapshots are immutable'
                USING ERRCODE = 'check_violation';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER dataset_snapshots_immutable
        BEFORE UPDATE ON dataset_snapshots
        FOR EACH ROW EXECUTE FUNCTION reject_dataset_snapshot_update()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER dataset_snapshots_immutable ON dataset_snapshots")
    op.execute("DROP FUNCTION reject_dataset_snapshot_update()")
    op.drop_table("dataset_snapshots")
    op.drop_table("datasets")
