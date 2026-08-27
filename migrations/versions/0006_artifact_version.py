"""Create PR-07 Artifact and ArtifactVersion tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_artifact_version"
down_revision: str | None = "0005_dataset_snapshot"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "artifacts",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("project_id", uuid, nullable=True),
        sa.Column("artifact_type", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("current_version_id", uuid, nullable=True),
        sa.Column(
            "created_by", uuid, sa.ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
    )
    op.create_table(
        "artifact_versions",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "artifact_id", uuid, sa.ForeignKey("artifacts.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("locator", sa.Text(), nullable=True),
        sa.Column("media_type", sa.String(length=128), nullable=True),
        sa.Column("byte_size", sa.BigInteger(), nullable=True),
        sa.Column("content_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_by", uuid, sa.ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("row_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint(
            "version_number > 0", name="ck_artifact_versions_version_number"
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'FROZEN', 'SUPERSEDED', 'ABANDONED')",
            name="ck_artifact_versions_status",
        ),
        sa.CheckConstraint(
            "byte_size IS NULL OR byte_size >= 0", name="ck_artifact_versions_byte_size"
        ),
        sa.UniqueConstraint(
            "artifact_id", "version_number", name="uq_artifact_versions_artifact_version"
        ),
        sa.UniqueConstraint(
            "artifact_id", "content_hash", name="uq_artifact_versions_artifact_content_hash"
        ),
    )
    op.create_foreign_key(
        "fk_artifacts_current_version_id",
        "artifacts",
        "artifact_versions",
        ["current_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.execute(
        """
        CREATE FUNCTION reject_frozen_artifact_version_material_update() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.status <> 'DRAFT' AND (
                NEW.artifact_id IS DISTINCT FROM OLD.artifact_id OR
                NEW.version_number IS DISTINCT FROM OLD.version_number OR
                NEW.locator IS DISTINCT FROM OLD.locator OR
                NEW.media_type IS DISTINCT FROM OLD.media_type OR
                NEW.byte_size IS DISTINCT FROM OLD.byte_size OR
                NEW.content_hash IS DISTINCT FROM OLD.content_hash OR
                NEW.metadata IS DISTINCT FROM OLD.metadata OR
                NEW.created_by IS DISTINCT FROM OLD.created_by OR
                NEW.created_at IS DISTINCT FROM OLD.created_at
            ) THEN
                RAISE EXCEPTION 'frozen artifact version material is immutable'
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER artifact_versions_frozen_immutable
        BEFORE UPDATE ON artifact_versions
        FOR EACH ROW EXECUTE FUNCTION reject_frozen_artifact_version_material_update()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER artifact_versions_frozen_immutable ON artifact_versions")
    op.execute("DROP FUNCTION reject_frozen_artifact_version_material_update()")
    op.drop_constraint("fk_artifacts_current_version_id", "artifacts", type_="foreignkey")
    op.drop_table("artifact_versions")
    op.drop_table("artifacts")
