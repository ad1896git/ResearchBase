"""Create PR-04 ResearchQuestion and Hypothesis identity/version tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_research_question_hypothesis"
down_revision: str | None = "0002_actor_project_workspace"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.alter_column(
        "alembic_version",
        "version_num",
        existing_type=sa.String(length=32),
        type_=sa.String(length=64),
    )
    uuid = postgresql.UUID(as_uuid=True)
    jsonb = postgresql.JSONB()

    op.create_table(
        "research_questions",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "project_id",
            uuid,
            sa.ForeignKey("projects.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("current_version_id", uuid, nullable=True),
        sa.Column(
            "created_by", uuid, sa.ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
    )
    op.create_table(
        "research_question_versions",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "research_question_id",
            uuid,
            sa.ForeignKey("research_questions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("scope", jsonb, nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.CHAR(length=64), nullable=True),
        sa.Column(
            "created_by", uuid, sa.ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("row_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint(
            "version_number > 0", name="ck_research_question_versions_version_number"
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'FROZEN', 'SUPERSEDED', 'ABANDONED')",
            name="ck_research_question_versions_status",
        ),
        sa.UniqueConstraint(
            "research_question_id",
            "version_number",
            name="uq_research_question_versions_parent_version",
        ),
    )
    op.create_foreign_key(
        "fk_research_questions_current_version",
        "research_questions",
        "research_question_versions",
        ["current_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_table(
        "hypotheses",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "project_id",
            uuid,
            sa.ForeignKey("projects.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "research_question_id",
            uuid,
            sa.ForeignKey("research_questions.id", ondelete="RESTRICT"),
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
        "hypothesis_versions",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "hypothesis_id",
            uuid,
            sa.ForeignKey("hypotheses.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("expected_direction", sa.String(length=64), nullable=True),
        sa.Column("success_criteria", jsonb, nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.CHAR(length=64), nullable=True),
        sa.Column(
            "created_by", uuid, sa.ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("row_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint("version_number > 0", name="ck_hypothesis_versions_version_number"),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'FROZEN', 'SUPERSEDED', 'ABANDONED')",
            name="ck_hypothesis_versions_status",
        ),
        sa.UniqueConstraint(
            "hypothesis_id", "version_number", name="uq_hypothesis_versions_parent_version"
        ),
    )
    op.create_foreign_key(
        "fk_hypotheses_current_version",
        "hypotheses",
        "hypothesis_versions",
        ["current_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_hypotheses_current_version", "hypotheses", type_="foreignkey")
    op.drop_table("hypothesis_versions")
    op.drop_table("hypotheses")
    op.drop_constraint(
        "fk_research_questions_current_version", "research_questions", type_="foreignkey"
    )
    op.drop_table("research_question_versions")
    op.drop_table("research_questions")
