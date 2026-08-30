"""Create PR-14 governance audit, impact, and correction tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015_governance_audit"
down_revision: str | None = "0014_claim_evidence"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "audit_findings",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "project_id",
            uuid,
            sa.ForeignKey("projects.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("finding_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", uuid, nullable=False),
        sa.Column("target_content_hash", sa.CHAR(length=64), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'open'"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            uuid,
            sa.ForeignKey("actors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint(
            "severity IN ('info','minor','major','critical')",
            name="ck_audit_findings_severity",
        ),
        sa.CheckConstraint(
            "status IN ('open','confirmed','dismissed','resolved')",
            name="ck_audit_findings_status",
        ),
    )
    op.create_index("ix_audit_findings_project", "audit_findings", ["project_id"])
    op.create_index(
        "ix_audit_findings_target",
        "audit_findings",
        ["project_id", "target_type", "target_id"],
    )
    op.create_table(
        "impact_assessments",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "project_id",
            uuid,
            sa.ForeignKey("projects.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "audit_finding_id",
            uuid,
            sa.ForeignKey("audit_findings.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("assessment_payload", postgresql.JSONB(), nullable=False),
        sa.Column("conclusion", sa.String(length=32), nullable=False),
        sa.Column(
            "created_by",
            uuid,
            sa.ForeignKey("actors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_hash", sa.CHAR(length=64), nullable=False),
        sa.CheckConstraint(
            "conclusion IN ('no_impact','stale','invalid','requires_review','unknown')",
            name="ck_impact_assessments_conclusion",
        ),
    )
    op.create_index("ix_impact_assessments_project", "impact_assessments", ["project_id"])
    op.create_index("ix_impact_assessments_finding", "impact_assessments", ["audit_finding_id"])
    op.create_table(
        "impact_targets",
        sa.Column(
            "impact_assessment_id",
            uuid,
            sa.ForeignKey("impact_assessments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", uuid, nullable=False),
        sa.Column("target_content_hash", sa.CHAR(length=64), nullable=True),
        sa.Column("impact_kind", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint(
            "impact_assessment_id", "target_type", "target_id", name="impact_targets_pkey"
        ),
        sa.CheckConstraint(
            "impact_kind IN ('direct','downstream','stale','invalid','requires_review')",
            name="ck_impact_targets_kind",
        ),
    )
    op.create_index("ix_impact_targets_target", "impact_targets", ["target_type", "target_id"])
    op.create_table(
        "correction_records",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "project_id",
            uuid,
            sa.ForeignKey("projects.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", uuid, nullable=False),
        sa.Column("target_content_hash", sa.CHAR(length=64), nullable=True),
        sa.Column("correction_type", sa.String(length=32), nullable=False),
        sa.Column("corrected_assertion", postgresql.JSONB(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_by",
            uuid,
            sa.ForeignKey("actors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_hash", sa.CHAR(length=64), nullable=False),
        sa.CheckConstraint(
            "correction_type IN ('factual','metadata','computational','attribution','other')",
            name="ck_correction_records_type",
        ),
    )
    op.create_index(
        "ix_correction_records_target",
        "correction_records",
        ["project_id", "target_type", "target_id", "created_at", "id"],
    )

    op.execute(
        """
        CREATE FUNCTION reject_audit_finding_material_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.id IS DISTINCT FROM OLD.id OR
               NEW.project_id IS DISTINCT FROM OLD.project_id OR
               NEW.finding_type IS DISTINCT FROM OLD.finding_type OR
               NEW.severity IS DISTINCT FROM OLD.severity OR
               NEW.title IS DISTINCT FROM OLD.title OR
               NEW.description IS DISTINCT FROM OLD.description OR
               NEW.target_type IS DISTINCT FROM OLD.target_type OR
               NEW.target_id IS DISTINCT FROM OLD.target_id OR
               NEW.target_content_hash IS DISTINCT FROM OLD.target_content_hash OR
               NEW.created_by IS DISTINCT FROM OLD.created_by OR
               NEW.created_at IS DISTINCT FROM OLD.created_at THEN
                RAISE EXCEPTION 'audit finding material is immutable'
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_findings_material_immutable
        BEFORE UPDATE ON audit_findings
        FOR EACH ROW EXECUTE FUNCTION reject_audit_finding_material_mutation()
        """
    )
    op.execute(
        """
        CREATE FUNCTION reject_immutable_governance_update() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION '% rows are immutable', TG_TABLE_NAME
                USING ERRCODE = 'check_violation';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER impact_assessments_immutable
        BEFORE UPDATE ON impact_assessments
        FOR EACH ROW EXECUTE FUNCTION reject_immutable_governance_update()
        """
    )
    op.execute(
        """
        CREATE FUNCTION allow_impact_target_only_with_new_parent() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
            parent_xmin bigint;
        BEGIN
            SELECT xmin::text::bigint INTO parent_xmin
            FROM impact_assessments WHERE id = NEW.impact_assessment_id;
            IF parent_xmin IS NULL OR parent_xmin <> pg_current_xact_id()::text::bigint THEN
                RAISE EXCEPTION 'impact targets may be inserted only with their new assessment'
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER impact_targets_insert_guard
        BEFORE INSERT ON impact_targets
        FOR EACH ROW EXECUTE FUNCTION allow_impact_target_only_with_new_parent()
        """
    )
    op.execute(
        """
        CREATE TRIGGER impact_targets_immutable
        BEFORE UPDATE OR DELETE ON impact_targets
        FOR EACH ROW EXECUTE FUNCTION reject_immutable_governance_update()
        """
    )
    op.execute(
        """
        CREATE TRIGGER correction_records_immutable
        BEFORE UPDATE ON correction_records
        FOR EACH ROW EXECUTE FUNCTION reject_immutable_governance_update()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER correction_records_immutable ON correction_records")
    op.execute("DROP TRIGGER impact_targets_immutable ON impact_targets")
    op.execute("DROP TRIGGER impact_targets_insert_guard ON impact_targets")
    op.execute("DROP TRIGGER impact_assessments_immutable ON impact_assessments")
    op.execute("DROP TRIGGER audit_findings_material_immutable ON audit_findings")
    op.execute("DROP FUNCTION allow_impact_target_only_with_new_parent()")
    op.execute("DROP FUNCTION reject_immutable_governance_update()")
    op.execute("DROP FUNCTION reject_audit_finding_material_mutation()")
    op.drop_table("correction_records")
    op.drop_table("impact_targets")
    op.drop_table("impact_assessments")
    op.drop_table("audit_findings")
