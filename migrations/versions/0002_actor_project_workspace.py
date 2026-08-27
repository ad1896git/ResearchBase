"""Create PR-02 actor, project, and workspace tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_actor_project_workspace"
down_revision: str | None = "0001_empty"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    actor_uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "actors",
        sa.Column("id", actor_uuid, primary_key=True),
        sa.Column("actor_type", sa.String(length=16), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("external_key", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("row_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint(
            "actor_type IN ('human', 'agent', 'service')", name="ck_actors_actor_type"
        ),
    )
    op.create_index(
        "uq_actors_external_key",
        "actors",
        ["external_key"],
        unique=True,
        postgresql_where=sa.text("external_key IS NOT NULL"),
    )
    op.create_table(
        "projects",
        sa.Column("id", actor_uuid, primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "lifecycle_status",
            sa.String(length=20),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            actor_uuid,
            sa.ForeignKey("actors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint(
            "lifecycle_status IN ('active', 'archived', 'retired')",
            name="ck_projects_lifecycle_status",
        ),
    )
    op.create_table(
        "workspaces",
        sa.Column("id", actor_uuid, primary_key=True),
        sa.Column(
            "project_id",
            actor_uuid,
            sa.ForeignKey("projects.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("locator", sa.Text(), nullable=True),
        sa.Column(
            "lifecycle_status",
            sa.String(length=20),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            actor_uuid,
            sa.ForeignKey("actors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint(
            "lifecycle_status IN ('active', 'archived', 'retired')",
            name="ck_workspaces_lifecycle_status",
        ),
        sa.UniqueConstraint("project_id", "name", name="uq_workspaces_project_name"),
    )


def downgrade() -> None:
    op.drop_table("workspaces")
    op.drop_table("projects")
    op.drop_index("uq_actors_external_key", table_name="actors")
    op.drop_table("actors")
