"""Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014_claim_evidence"
down_revision: str | None = "0013_statistical_result_legacy_input_precheck"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "claims",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "project_id",
            uuid,
            sa.ForeignKey("projects.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("current_version_id", uuid, nullable=True),
        sa.Column(
            "created_by",
            uuid,
            sa.ForeignKey("actors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
    )
    op.create_table(
        "claim_versions",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "claim_id",
            uuid,
            sa.ForeignKey("claims.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("scope", postgresql.JSONB(), nullable=True),
        sa.Column("qualification", sa.Text(), nullable=True),
        sa.Column("support_set_hash", sa.CHAR(length=64), nullable=True),
        sa.Column("content_hash", sa.CHAR(length=64), nullable=True),
        sa.Column(
            "created_by",
            uuid,
            sa.ForeignKey("actors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("row_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint("version_number > 0", name="ck_claim_versions_version_number"),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'FROZEN', 'SUPERSEDED', 'ABANDONED')",
            name="ck_claim_versions_status",
        ),
        sa.UniqueConstraint("claim_id", "version_number", name="uq_claim_versions_parent_version"),
    )
    op.create_foreign_key(
        "fk_claim_current_version",
        "claims",
        "claim_versions",
        ["current_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_table(
        "evidence_relations",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "claim_version_id",
            uuid,
            sa.ForeignKey("claim_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "measurement_id",
            uuid,
            sa.ForeignKey("measurements.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "statistical_result_id",
            uuid,
            sa.ForeignKey("statistical_results.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("relation_type", sa.String(length=32), nullable=False),
        sa.Column("qualification", sa.Text(), nullable=True),
        sa.Column(
            "created_by",
            uuid,
            sa.ForeignKey("actors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "relation_type IN ('supports', 'contradicts', 'qualifies', 'context')",
            name="ck_evidence_relations_relation_type",
        ),
        sa.CheckConstraint(
            "(measurement_id IS NOT NULL AND statistical_result_id IS NULL) OR "
            "(measurement_id IS NULL AND statistical_result_id IS NOT NULL)",
            name="ck_evidence_relations_source_xor",
        ),
    )
    op.create_index(
        "uq_evidence_measurement",
        "evidence_relations",
        ["claim_version_id", "measurement_id", "relation_type"],
        unique=True,
        postgresql_where=sa.text("measurement_id IS NOT NULL"),
    )
    op.create_index(
        "uq_evidence_stat",
        "evidence_relations",
        ["claim_version_id", "statistical_result_id", "relation_type"],
        unique=True,
        postgresql_where=sa.text("statistical_result_id IS NOT NULL"),
    )
    op.execute(
        """
        CREATE FUNCTION reject_claim_version_material_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.status IN ('FROZEN', 'SUPERSEDED', 'ABANDONED') AND (
                NEW.claim_id IS DISTINCT FROM OLD.claim_id OR
                NEW.version_number IS DISTINCT FROM OLD.version_number OR
                NEW.statement IS DISTINCT FROM OLD.statement OR
                NEW.scope IS DISTINCT FROM OLD.scope OR
                NEW.qualification IS DISTINCT FROM OLD.qualification OR
                NEW.support_set_hash IS DISTINCT FROM OLD.support_set_hash OR
                NEW.content_hash IS DISTINCT FROM OLD.content_hash OR
                NEW.created_by IS DISTINCT FROM OLD.created_by OR
                NEW.created_at IS DISTINCT FROM OLD.created_at OR
                NEW.frozen_at IS DISTINCT FROM OLD.frozen_at OR
                (OLD.status = 'FROZEN' AND NEW.status NOT IN ('FROZEN', 'SUPERSEDED')) OR
                (OLD.status IN ('SUPERSEDED', 'ABANDONED') AND NEW.status <> OLD.status)
            ) THEN
                RAISE EXCEPTION 'finalized claim version material is immutable'
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER claim_versions_finalized_immutable
        BEFORE UPDATE ON claim_versions
        FOR EACH ROW EXECUTE FUNCTION reject_claim_version_material_mutation()
        """
    )
    op.execute(
        """
        CREATE FUNCTION reject_non_draft_evidence_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
            old_status text;
            new_status text;
        BEGIN
            IF TG_OP IN ('UPDATE', 'DELETE') THEN
                SELECT status INTO old_status
                FROM claim_versions WHERE id = OLD.claim_version_id;
                IF old_status IS NULL OR old_status <> 'DRAFT' THEN
                    RAISE EXCEPTION 'evidence relations are mutable only for draft claim versions'
                        USING ERRCODE = 'check_violation';
                END IF;
            END IF;
            IF TG_OP IN ('INSERT', 'UPDATE') THEN
                SELECT status INTO new_status
                FROM claim_versions WHERE id = NEW.claim_version_id;
                IF new_status IS NULL OR new_status <> 'DRAFT' THEN
                    RAISE EXCEPTION 'evidence relations are mutable only for draft claim versions'
                        USING ERRCODE = 'check_violation';
                END IF;
            END IF;
            RETURN COALESCE(NEW, OLD);
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER evidence_relations_draft_only
        BEFORE INSERT OR UPDATE OR DELETE ON evidence_relations
        FOR EACH ROW EXECUTE FUNCTION reject_non_draft_evidence_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER evidence_relations_draft_only ON evidence_relations")
    op.execute("DROP FUNCTION reject_non_draft_evidence_mutation()")
    op.execute("DROP TRIGGER claim_versions_finalized_immutable ON claim_versions")
    op.execute("DROP FUNCTION reject_claim_version_material_mutation()")
    op.drop_index("uq_evidence_stat", table_name="evidence_relations")
    op.drop_index("uq_evidence_measurement", table_name="evidence_relations")
    op.drop_table("evidence_relations")
    op.drop_constraint("fk_claim_current_version", "claims", type_="foreignkey")
    op.drop_table("claim_versions")
    op.drop_table("claims")
