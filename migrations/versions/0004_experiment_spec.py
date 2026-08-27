"""Create PR-05 ExperimentSpec identity/version tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_experiment_spec"
down_revision: str | None = "0003_research_question_hypothesis"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    jsonb = postgresql.JSONB()
    op.create_table(
        "experiment_specs",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "project_id", uuid, sa.ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column(
            "hypothesis_id",
            uuid,
            sa.ForeignKey("hypotheses.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("current_version_id", uuid, nullable=True),
        sa.Column(
            "created_by", uuid, sa.ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
    )
    op.create_table(
        "experiment_spec_versions",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "experiment_spec_id",
            uuid,
            sa.ForeignKey("experiment_specs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("protocol", jsonb, nullable=False),
        sa.Column("planned_metrics", jsonb, nullable=True),
        sa.Column("seed_policy", jsonb, nullable=True),
        sa.Column("analysis_plan", jsonb, nullable=True),
        sa.Column("content_hash", sa.CHAR(length=64), nullable=True),
        sa.Column(
            "created_by", uuid, sa.ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("row_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint(
            "version_number > 0", name="ck_experiment_spec_versions_version_number"
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'FROZEN', 'SUPERSEDED', 'ABANDONED')",
            name="ck_experiment_spec_versions_status",
        ),
        sa.UniqueConstraint(
            "experiment_spec_id",
            "version_number",
            name="uq_experiment_spec_versions_parent_version",
        ),
    )
    op.create_foreign_key(
        "fk_experiment_specs_current_version",
        "experiment_specs",
        "experiment_spec_versions",
        ["current_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_experiment_specs_current_version", "experiment_specs", type_="foreignkey"
    )
    op.drop_table("experiment_spec_versions")
    op.drop_table("experiment_specs")
