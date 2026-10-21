"""Add public literature source identity, identifiers, and project access links."""

# DDL contains intentionally literal PostgreSQL expressions and constraint definitions.
# ruff: noqa: E501

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020_literature_source_identity"
down_revision: str | None = "0019_phase2_bootstrap_membership"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

SOURCE_TABLES = (
    "literature_sources",
    "source_identifiers",
    "source_identifier_verification_events",
    "literature_source_project_links",
    "literature_command_receipts",
)


def upgrade() -> None:
    op.create_table(
        "literature_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_kind", sa.String(32), nullable=False),
        sa.Column("canonical_title", sa.Text(), nullable=False),
        sa.Column("lifecycle_status", sa.String(16), nullable=False),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("actors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "source_kind IN ('PAPER','PREPRINT','THESIS','BOOK','WEB','STANDARD','DATASET_DOC','OTHER')",
            name="ck_literature_sources_kind",
        ),
        sa.CheckConstraint(
            "length(btrim(canonical_title)) > 0", name="ck_literature_sources_title"
        ),
        sa.CheckConstraint(
            "lifecycle_status IN ('ACTIVE','RETIRED')", name="ck_literature_sources_status"
        ),
        sa.CheckConstraint("row_version > 0", name="ck_literature_sources_row_version"),
    )
    op.create_index("ix_literature_sources_status", "literature_sources", ["lifecycle_status"])

    op.create_table(
        "source_identifiers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "literature_source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("literature_sources.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("identifier_type", sa.String(32), nullable=False),
        sa.Column("identifier_value", sa.Text(), nullable=False),
        sa.Column("normalized_value", sa.Text(), nullable=False),
        sa.Column("normalization_version", sa.String(48), nullable=False),
        sa.Column(
            "binding_basis_artifact_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("artifact_versions.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "supersedes_rejected_identifier_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_identifiers.id", ondelete="RESTRICT"),
        ),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("verification_status", sa.String(16), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column(
            "verified_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("actors.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "verification_basis_artifact_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("artifact_versions.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("actors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "identifier_type IN ('DOI','ARXIV','PMID','SEMANTIC_SCHOLAR','OPENALEX','URL','ISBN','OTHER')",
            name="ck_source_identifiers_type",
        ),
        sa.CheckConstraint(
            "length(btrim(identifier_value)) > 0 AND length(btrim(normalized_value)) > 0",
            name="ck_source_identifiers_values",
        ),
        sa.CheckConstraint(
            "normalization_version = 'source-identifier-normalization-v1'",
            name="ck_source_identifiers_normalization",
        ),
        sa.CheckConstraint(
            "verification_status IN ('UNVERIFIED','VERIFIED','REJECTED')",
            name="ck_source_identifiers_status",
        ),
        sa.CheckConstraint("row_version > 0", name="ck_source_identifiers_row_version"),
        sa.CheckConstraint(
            "supersedes_rejected_identifier_id IS NULL OR binding_basis_artifact_version_id IS NOT NULL",
            name="ck_source_identifier_correction_pair",
        ),
        sa.CheckConstraint(
            "(verification_status = 'VERIFIED' AND verified_at IS NOT NULL AND verified_by IS NOT NULL AND verification_basis_artifact_version_id IS NOT NULL) OR (verification_status IN ('UNVERIFIED','REJECTED') AND verified_at IS NULL AND verified_by IS NULL AND verification_basis_artifact_version_id IS NULL)",
            name="ck_source_identifier_verification_fields",
        ),
    )
    op.create_index(
        "uq_source_identifier_live_value",
        "source_identifiers",
        ["identifier_type", "normalized_value"],
        unique=True,
        postgresql_where=sa.text("verification_status IN ('UNVERIFIED','VERIFIED')"),
    )
    op.create_index(
        "uq_source_identifier_primary",
        "source_identifiers",
        ["literature_source_id"],
        unique=True,
        postgresql_where=sa.text("is_primary AND verification_status <> 'REJECTED'"),
    )
    op.create_index(
        "uq_source_identifier_corrected_predecessor",
        "source_identifiers",
        ["supersedes_rejected_identifier_id"],
        unique=True,
        postgresql_where=sa.text("supersedes_rejected_identifier_id IS NOT NULL"),
    )
    op.create_index(
        "ix_source_identifiers_source_status",
        "source_identifiers",
        ["literature_source_id", "verification_status", "id"],
    )
    op.create_index(
        "ix_source_identifiers_rejected",
        "source_identifiers",
        ["identifier_type", "normalized_value", "created_at", "id"],
        postgresql_where=sa.text("verification_status = 'REJECTED'"),
    )

    op.create_table(
        "source_identifier_verification_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_identifier_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_identifiers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("prior_status", sa.String(16), nullable=False),
        sa.Column("new_status", sa.String(16), nullable=False),
        sa.Column(
            "basis_artifact_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("artifact_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "verified_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("actors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.CheckConstraint(
            "prior_status IN ('UNVERIFIED','VERIFIED')", name="ck_source_identifier_events_prior"
        ),
        sa.CheckConstraint(
            "new_status IN ('VERIFIED','REJECTED')", name="ck_source_identifier_events_new"
        ),
        sa.CheckConstraint(
            "(prior_status = 'UNVERIFIED' AND new_status IN ('VERIFIED','REJECTED')) OR (prior_status = 'VERIFIED' AND new_status = 'REJECTED')",
            name="ck_source_identifier_events_transition",
        ),
        sa.CheckConstraint("length(btrim(reason)) > 0", name="ck_source_identifier_events_reason"),
        sa.UniqueConstraint(
            "source_identifier_id", "request_id", name="uq_source_identifier_event_request"
        ),
    )
    op.create_index(
        "ix_source_identifier_events_time",
        "source_identifier_verification_events",
        ["source_identifier_id", "occurred_at", "id"],
    )

    op.create_table(
        "literature_source_project_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "literature_source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("literature_sources.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "linked_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("actors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "literature_source_id", "project_id", name="uq_literature_source_project_link"
        ),
    )
    op.create_index(
        "ix_literature_source_links_project",
        "literature_source_project_links",
        ["project_id", "literature_source_id"],
    )

    op.create_table(
        "literature_command_receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("deployment_id", sa.Text(), nullable=False),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "actor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("actors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("command_name", sa.String(40), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("hash_scheme", sa.String(32), nullable=False),
        sa.Column(
            "result_source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("literature_sources.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "result_identifier_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_identifiers.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "result_verification_event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_identifier_verification_events.id", ondelete="RESTRICT"),
        ),
        sa.Column("result_dto_version", sa.SmallInteger(), nullable=False),
        sa.Column("result_dto", postgresql.JSONB(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "command_name IN ('REGISTER_LITERATURE_SOURCE','ADD_SOURCE_IDENTIFIER','VERIFY_SOURCE_IDENTIFIER','REJECT_SOURCE_IDENTIFIER')",
            name="ck_literature_receipts_command",
        ),
        sa.CheckConstraint("input_hash ~ '^[0-9a-f]{64}$'", name="ck_literature_receipts_hash"),
        sa.CheckConstraint(
            "hash_scheme = 'sha256-cjson-v1'", name="ck_literature_receipts_hash_scheme"
        ),
        sa.CheckConstraint(
            "length(btrim(deployment_id)) > 0", name="ck_literature_receipts_deployment"
        ),
        sa.CheckConstraint("result_dto_version > 0", name="ck_literature_receipts_dto_version"),
        sa.CheckConstraint(
            "(command_name = 'REGISTER_LITERATURE_SOURCE' AND result_verification_event_id IS NULL) OR (command_name = 'ADD_SOURCE_IDENTIFIER' AND result_identifier_id IS NOT NULL AND result_verification_event_id IS NULL) OR (command_name IN ('VERIFY_SOURCE_IDENTIFIER','REJECT_SOURCE_IDENTIFIER') AND result_identifier_id IS NOT NULL AND result_verification_event_id IS NOT NULL)",
            name="ck_literature_receipts_result_shape",
        ),
        sa.UniqueConstraint(
            "deployment_id",
            "project_id",
            "actor_id",
            "command_name",
            "request_id",
            name="uq_literature_command_receipt_scope",
        ),
    )
    op.create_index(
        "ix_literature_receipts_source",
        "literature_command_receipts",
        ["result_source_id", "completed_at"],
    )
    op.create_index(
        "ix_literature_receipts_scope",
        "literature_command_receipts",
        ["project_id", "actor_id", "completed_at"],
    )

    op.execute(
        """
        CREATE FUNCTION rb_guard_literature_source() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'literature source identity is immutable' USING ERRCODE='P17D1';
        END $$;

        CREATE FUNCTION rb_guard_source_identifier() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'source identifier history is immutable' USING ERRCODE='P17D1';
            END IF;
            IF NEW.id IS DISTINCT FROM OLD.id OR NEW.literature_source_id IS DISTINCT FROM OLD.literature_source_id OR
               NEW.identifier_type IS DISTINCT FROM OLD.identifier_type OR NEW.identifier_value IS DISTINCT FROM OLD.identifier_value OR
               NEW.normalized_value IS DISTINCT FROM OLD.normalized_value OR NEW.normalization_version IS DISTINCT FROM OLD.normalization_version OR
               NEW.binding_basis_artifact_version_id IS DISTINCT FROM OLD.binding_basis_artifact_version_id OR
               NEW.supersedes_rejected_identifier_id IS DISTINCT FROM OLD.supersedes_rejected_identifier_id OR
               NEW.is_primary IS DISTINCT FROM OLD.is_primary OR NEW.created_by IS DISTINCT FROM OLD.created_by OR
               NEW.created_at IS DISTINCT FROM OLD.created_at OR NEW.row_version <> OLD.row_version + 1 OR
               NOT ((OLD.verification_status = 'UNVERIFIED' AND NEW.verification_status = 'VERIFIED' AND
                     NEW.verified_at IS NOT NULL AND NEW.verified_by IS NOT NULL AND NEW.verification_basis_artifact_version_id IS NOT NULL) OR
                    (OLD.verification_status IN ('UNVERIFIED','VERIFIED') AND NEW.verification_status = 'REJECTED' AND
                     NEW.verified_at IS NULL AND NEW.verified_by IS NULL AND NEW.verification_basis_artifact_version_id IS NULL)) THEN
                RAISE EXCEPTION 'source identifier update is not a legal transition' USING ERRCODE='P17D2';
            END IF;
            IF NEW.verification_status = 'VERIFIED' AND NOT EXISTS (
                SELECT 1 FROM artifact_versions WHERE id = NEW.verification_basis_artifact_version_id AND status = 'FROZEN'
            ) THEN
                RAISE EXCEPTION 'identifier basis must be frozen' USING ERRCODE='P17D4';
            END IF;
            RETURN NEW;
        END $$;

        CREATE FUNCTION rb_guard_source_identity_history() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'literature source history is append-only' USING ERRCODE='P17D1';
        END $$;

        CREATE FUNCTION rb_validate_source_identifier_event() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE v_identifier source_identifiers%ROWTYPE;
        BEGIN
            SELECT * INTO v_identifier FROM source_identifiers WHERE id = NEW.source_identifier_id;
            IF NOT FOUND OR v_identifier.verification_status <> NEW.new_status OR
               NOT EXISTS (SELECT 1 FROM artifact_versions WHERE id = NEW.basis_artifact_version_id AND status = 'FROZEN') OR
               (NEW.new_status = 'VERIFIED' AND (v_identifier.verified_by <> NEW.verified_by OR
                    v_identifier.verification_basis_artifact_version_id <> NEW.basis_artifact_version_id OR
                    v_identifier.verified_at <> NEW.occurred_at)) OR
               (NEW.new_status = 'REJECTED' AND (v_identifier.verified_at IS NOT NULL OR
                    v_identifier.verified_by IS NOT NULL OR v_identifier.verification_basis_artifact_version_id IS NOT NULL)) THEN
                RAISE EXCEPTION 'identifier event does not match a legal frozen-basis transition' USING ERRCODE='P17D2';
            END IF;
            RETURN NULL;
        END $$;

        CREATE FUNCTION rb_validate_source_identifier_transition() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM source_identifier_verification_events e
                WHERE e.source_identifier_id = NEW.id AND e.prior_status = OLD.verification_status
                  AND e.new_status = NEW.verification_status
                  AND e.verified_by = coalesce(NEW.verified_by, e.verified_by)
                  AND e.occurred_at = coalesce(NEW.verified_at, e.occurred_at)) THEN
                RAISE EXCEPTION 'source identifier transition requires its event' USING ERRCODE='P17D2';
            END IF;
            RETURN NULL;
        END $$;

        CREATE FUNCTION rb_validate_literature_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.result_identifier_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM source_identifiers si WHERE si.id=NEW.result_identifier_id
                  AND si.literature_source_id=NEW.result_source_id
            ) THEN
                RAISE EXCEPTION 'receipt source and identifier disagree' USING ERRCODE='23514', CONSTRAINT='ck_literature_receipt_source_identifier';
            END IF;
            IF NEW.result_verification_event_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM source_identifier_verification_events e WHERE e.id=NEW.result_verification_event_id
                  AND e.source_identifier_id=NEW.result_identifier_id
            ) THEN
                RAISE EXCEPTION 'receipt event and identifier disagree' USING ERRCODE='23514', CONSTRAINT='ck_literature_receipt_event_identifier';
            END IF;
            RETURN NULL;
        END $$;

        CREATE FUNCTION rb_validate_source_identifier_correction() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            v_predecessor source_identifiers%ROWTYPE;
            v_basis_frozen_at timestamptz;
            v_rejected_at timestamptz;
        BEGIN
            IF NEW.supersedes_rejected_identifier_id IS NULL THEN
                IF NEW.binding_basis_artifact_version_id IS NOT NULL AND NOT EXISTS (
                    SELECT 1 FROM artifact_versions WHERE id=NEW.binding_basis_artifact_version_id
                      AND status='FROZEN' AND frozen_at <= NEW.created_at
                ) THEN
                    RAISE EXCEPTION 'identifier binding basis must be frozen before addition' USING ERRCODE='P17D4';
                END IF;
                RETURN NULL;
            END IF;
            SELECT * INTO v_predecessor FROM source_identifiers
             WHERE id=NEW.supersedes_rejected_identifier_id;
            SELECT frozen_at INTO v_basis_frozen_at FROM artifact_versions
             WHERE id=NEW.binding_basis_artifact_version_id AND status='FROZEN';
            SELECT max(occurred_at) INTO v_rejected_at FROM source_identifier_verification_events
             WHERE source_identifier_id=NEW.supersedes_rejected_identifier_id AND new_status='REJECTED';
            IF v_predecessor.id IS NULL OR v_predecessor.id=NEW.id OR v_predecessor.verification_status<>'REJECTED' OR
               v_predecessor.identifier_type<>NEW.identifier_type OR v_predecessor.normalized_value<>NEW.normalized_value OR
               v_basis_frozen_at IS NULL OR v_basis_frozen_at>NEW.created_at OR
               v_rejected_at IS NULL OR v_rejected_at>NEW.created_at THEN
                RAISE EXCEPTION 'corrected identifier binding has invalid predecessor or frozen basis' USING ERRCODE='P17D4';
            END IF;
            RETURN NULL;
        END $$;

        CREATE TRIGGER trg_literature_sources_immutable BEFORE UPDATE OR DELETE ON literature_sources
            FOR EACH ROW EXECUTE FUNCTION rb_guard_literature_source();
        CREATE TRIGGER trg_source_identifiers_transition BEFORE UPDATE OR DELETE ON source_identifiers
            FOR EACH ROW EXECUTE FUNCTION rb_guard_source_identifier();
        CREATE TRIGGER trg_source_identifier_events_immutable BEFORE UPDATE OR DELETE ON source_identifier_verification_events
            FOR EACH ROW EXECUTE FUNCTION rb_guard_source_identity_history();
        CREATE TRIGGER trg_source_project_links_immutable BEFORE UPDATE OR DELETE ON literature_source_project_links
            FOR EACH ROW EXECUTE FUNCTION rb_guard_source_identity_history();
        CREATE TRIGGER trg_literature_receipts_immutable BEFORE UPDATE OR DELETE ON literature_command_receipts
            FOR EACH ROW EXECUTE FUNCTION rb_guard_source_identity_history();
        CREATE CONSTRAINT TRIGGER trg_source_identifier_event_valid AFTER INSERT ON source_identifier_verification_events
            DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION rb_validate_source_identifier_event();
        CREATE CONSTRAINT TRIGGER trg_source_identifier_requires_event AFTER UPDATE ON source_identifiers
            DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION rb_validate_source_identifier_transition();
        CREATE CONSTRAINT TRIGGER trg_literature_receipt_result_consistent AFTER INSERT ON literature_command_receipts
            DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION rb_validate_literature_receipt();
        CREATE CONSTRAINT TRIGGER trg_source_identifier_correction_valid AFTER INSERT ON source_identifiers
            DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION rb_validate_source_identifier_correction();
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    populated = bind.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM literature_sources) OR "
            "EXISTS (SELECT 1 FROM source_identifiers) OR "
            "EXISTS (SELECT 1 FROM source_identifier_verification_events) OR "
            "EXISTS (SELECT 1 FROM literature_source_project_links) OR "
            "EXISTS (SELECT 1 FROM literature_command_receipts)"
        )
    ).scalar_one()
    if populated:
        raise RuntimeError("LITERATURE_SOURCE_DATA_PRESERVATION_REQUIRED")
    for table in reversed(SOURCE_TABLES):
        op.drop_table(table)
    op.execute(
        """
        DROP FUNCTION rb_validate_literature_receipt();
        DROP FUNCTION rb_validate_source_identifier_correction();
        DROP FUNCTION rb_validate_source_identifier_transition();
        DROP FUNCTION rb_validate_source_identifier_event();
        DROP FUNCTION rb_guard_source_identity_history();
        DROP FUNCTION rb_guard_source_identifier();
        DROP FUNCTION rb_guard_literature_source();
        """
    )
