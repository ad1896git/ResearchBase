"""Persist typed, basis-bound source merge governance proposals and decisions."""

# The DDL is PostgreSQL-specific by contract.
# ruff: noqa: E501

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0021_source_merge_governance_bridge"
down_revision: str | None = "0020_literature_source_identity"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

TABLES = (
    "source_merge_proposals",
    "source_merge_proposal_projects",
    "source_merge_proposal_identifier_basis",
    "source_merge_proposal_source_basis",
    "source_merge_proposal_evidence",
    "source_merge_approvals",
    "source_merge_governance_events",
)


def upgrade() -> None:
    op.create_table(
        "source_merge_proposals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("deployment_id", sa.Text(), nullable=False),
        sa.Column(
            "source_a_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("literature_sources.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "source_b_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("literature_sources.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "canonical_survivor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("literature_sources.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "proposed_by_actor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("actors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "proposed_in_project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("basis_contract_version", sa.String(40), nullable=False),
        sa.Column("identifier_basis_hash", sa.String(64), nullable=False),
        sa.Column("source_version_basis_hash", sa.String(64), nullable=False),
        sa.Column("proposal_basis_hash", sa.String(64), nullable=False),
        sa.Column("hash_scheme", sa.String(32), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("result_dto_version", sa.SmallInteger(), nullable=False),
        sa.Column("result_dto", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "supersedes_proposal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_merge_proposals.id", ondelete="RESTRICT"),
        ),
        sa.Column("command_name", sa.String(48), nullable=False),
        sa.CheckConstraint("source_a_id < source_b_id", name="ck_source_merge_pair_order"),
        sa.CheckConstraint(
            "canonical_survivor_id IN (source_a_id, source_b_id)", name="ck_source_merge_survivor"
        ),
        sa.CheckConstraint(
            "length(btrim(deployment_id)) > 0 AND length(btrim(rationale)) > 0",
            name="ck_source_merge_proposal_text",
        ),
        sa.CheckConstraint(
            "basis_contract_version = 'source-merge-basis-v1'", name="ck_source_merge_basis_version"
        ),
        sa.CheckConstraint("hash_scheme = 'sha256-cjson-v1'", name="ck_source_merge_hash_scheme"),
        sa.CheckConstraint(
            "identifier_basis_hash ~ '^[0-9a-f]{64}$' AND source_version_basis_hash ~ '^[0-9a-f]{64}$' AND proposal_basis_hash ~ '^[0-9a-f]{64}$' AND request_hash ~ '^[0-9a-f]{64}$'",
            name="ck_source_merge_hashes",
        ),
        sa.CheckConstraint("result_dto_version > 0", name="ck_source_merge_result_version"),
        sa.UniqueConstraint(
            "deployment_id",
            "proposed_in_project_id",
            "proposed_by_actor_id",
            "command_name",
            "request_id",
            name="uq_source_merge_proposal_request",
        ),
    )
    op.create_index(
        "ix_source_merge_proposals_pair",
        "source_merge_proposals",
        ["source_a_id", "source_b_id", "created_at"],
    )

    op.create_table(
        "source_merge_proposal_projects",
        sa.Column(
            "proposal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_merge_proposals.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "source_a_link_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("literature_source_project_links.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "source_b_link_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("literature_source_project_links.id", ondelete="RESTRICT"),
        ),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("link_basis_hash", sa.String(64), nullable=False),
        sa.CheckConstraint(
            "source_a_link_id IS NOT NULL OR source_b_link_id IS NOT NULL",
            name="ck_source_merge_project_link_present",
        ),
        sa.CheckConstraint("link_basis_hash ~ '^[0-9a-f]{64}$'", name="ck_source_merge_link_hash"),
    )

    op.create_table(
        "source_merge_proposal_identifier_basis",
        sa.Column(
            "proposal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_merge_proposals.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "identifier_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_identifiers.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("literature_sources.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("identifier_type", sa.String(32), nullable=False),
        sa.Column("normalized_value", sa.Text(), nullable=False),
        sa.Column("normalization_version", sa.String(48), nullable=False),
        sa.Column("verification_status", sa.String(16), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
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
        sa.Column(
            "verification_basis_artifact_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("artifact_versions.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "verified_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("actors.id", ondelete="RESTRICT"),
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("captured_row_version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "verification_status IN ('UNVERIFIED','VERIFIED','REJECTED')",
            name="ck_source_merge_identifier_status",
        ),
        sa.CheckConstraint("captured_row_version > 0", name="ck_source_merge_identifier_version"),
    )

    op.create_table(
        "source_merge_proposal_source_basis",
        sa.Column(
            "proposal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_merge_proposals.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("literature_sources.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("current_version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("current_version_hash", sa.String(64)),
        sa.Column("version_state_hash", sa.String(64), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "current_version_id IS NULL AND current_version_hash IS NULL",
            name="ck_source_merge_no_versions_at_0021",
        ),
        sa.CheckConstraint(
            "version_state_hash ~ '^[0-9a-f]{64}$'", name="ck_source_merge_version_hash"
        ),
    )

    op.create_table(
        "source_merge_proposal_evidence",
        sa.Column(
            "proposal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_merge_proposals.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "artifact_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("artifact_versions.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="ck_source_merge_evidence_hash"),
    )

    op.create_table(
        "source_merge_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "proposal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_merge_proposals.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("decision", sa.String(8), nullable=False),
        sa.Column("decision_reason", sa.Text()),
        sa.Column("decision_payload_hash", sa.String(64), nullable=False),
        sa.Column(
            "approver_actor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("actors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "membership_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project_memberships.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "owner_role_assignment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project_role_assignments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("deployment_id", sa.Text(), nullable=False),
        sa.Column("credential_id", sa.Text(), nullable=False),
        sa.Column("trusted_subject_kind", sa.String(16), nullable=False),
        sa.Column("trusted_subject_value", sa.Text(), nullable=False),
        sa.Column("principal_verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decision_basis_hash", sa.String(64), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("command_name", sa.String(48), nullable=False),
        sa.Column("result_dto_version", sa.SmallInteger(), nullable=False),
        sa.Column("result_dto", postgresql.JSONB(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("decision IN ('APPROVE','REJECT')", name="ck_source_merge_decision"),
        sa.CheckConstraint(
            "(decision='APPROVE' AND decision_reason IS NULL) OR (decision='REJECT' AND length(btrim(decision_reason)) > 0)",
            name="ck_source_merge_decision_reason",
        ),
        sa.CheckConstraint(
            "decision_payload_hash ~ '^[0-9a-f]{64}$' AND decision_basis_hash ~ '^[0-9a-f]{64}$' AND request_hash ~ '^[0-9a-f]{64}$'",
            name="ck_source_merge_decision_hashes",
        ),
        sa.CheckConstraint("result_dto_version > 0", name="ck_source_merge_decision_dto_version"),
        sa.UniqueConstraint("proposal_id", "project_id", name="uq_source_merge_project_decision"),
        sa.UniqueConstraint(
            "deployment_id",
            "project_id",
            "approver_actor_id",
            "command_name",
            "request_id",
            name="uq_source_merge_decision_request",
        ),
    )
    op.create_table(
        "source_merge_governance_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "proposal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_merge_proposals.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "approval_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_merge_approvals.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "actor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("actors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("event_kind", sa.String(32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("deployment_id", sa.Text(), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("basis_hash", sa.String(64), nullable=False),
        sa.Column("command_name", sa.String(48), nullable=False),
        sa.CheckConstraint(
            "event_kind IN ('SUBMITTED','APPROVAL_REVOKED','PROPOSAL_SUPERSEDED','PROPOSAL_STALE','PROPOSAL_CONSUMED')",
            name="ck_source_merge_event_kind",
        ),
        sa.CheckConstraint(
            "request_hash ~ '^[0-9a-f]{64}$' AND basis_hash ~ '^[0-9a-f]{64}$'",
            name="ck_source_merge_event_hashes",
        ),
        sa.UniqueConstraint(
            "deployment_id",
            "actor_id",
            "project_id",
            "command_name",
            "request_id",
            name="uq_source_merge_event_request",
        ),
    )
    for table in TABLES:
        op.execute(
            sa.text(
                f"CREATE TRIGGER trg_{table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION reject_immutable_governance_update()"
            )
        )
    op.execute(
        """
        CREATE FUNCTION rb_validate_source_merge_project_basis() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE p source_merge_proposals%ROWTYPE;
        BEGIN
            SELECT * INTO p FROM source_merge_proposals WHERE id=NEW.proposal_id;
            IF NOT FOUND OR
               (NEW.source_a_link_id IS NOT NULL AND NOT EXISTS (
                 SELECT 1 FROM literature_source_project_links l
                 WHERE l.id=NEW.source_a_link_id AND l.literature_source_id=p.source_a_id
                   AND l.project_id=NEW.project_id)) OR
               (NEW.source_b_link_id IS NOT NULL AND NOT EXISTS (
                 SELECT 1 FROM literature_source_project_links l
                 WHERE l.id=NEW.source_b_link_id AND l.literature_source_id=p.source_b_id
                   AND l.project_id=NEW.project_id)) THEN
                RAISE EXCEPTION 'source merge project basis does not match proposal links'
                    USING ERRCODE='23514', CONSTRAINT='ck_source_merge_project_basis';
            END IF;
            RETURN NULL;
        END $$;
        CREATE CONSTRAINT TRIGGER trg_source_merge_project_basis_valid
            AFTER INSERT ON source_merge_proposal_projects DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION rb_validate_source_merge_project_basis();

        CREATE FUNCTION rb_validate_source_merge_approval() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE p source_merge_proposals%ROWTYPE;
        BEGIN
            SELECT * INTO p FROM source_merge_proposals WHERE id=NEW.proposal_id;
            IF NOT FOUND OR NEW.decision_basis_hash <> p.proposal_basis_hash OR
               NOT EXISTS (SELECT 1 FROM source_merge_proposal_projects x
                           WHERE x.proposal_id=NEW.proposal_id AND x.project_id=NEW.project_id) OR
               NOT EXISTS (
                 SELECT 1 FROM actors a
                 JOIN project_memberships m ON m.actor_id=a.id
                 JOIN project_role_assignments r ON r.membership_id=m.id AND r.project_id=m.project_id
                    AND r.actor_id=m.actor_id
                 JOIN actor_subject_bindings b ON b.actor_id=a.id
                 WHERE a.id=NEW.approver_actor_id AND a.actor_type='HUMAN' AND a.retired_at IS NULL
                   AND m.id=NEW.membership_id AND m.project_id=NEW.project_id AND m.status='ACTIVE'
                   AND r.id=NEW.owner_role_assignment_id AND r.role='OWNER'
                   AND r.effective_from <= NEW.decided_at
                   AND (r.effective_until IS NULL OR NEW.decided_at < r.effective_until)
                   AND b.deployment_id=NEW.deployment_id AND b.subject_kind=NEW.trusted_subject_kind
                   AND b.subject_value=NEW.trusted_subject_value
                   AND b.subject_credential_id=NEW.credential_id AND b.status='ACTIVE'
                   AND b.bound_at <= NEW.decided_at
                   AND (b.revoked_at IS NULL OR NEW.decided_at < b.revoked_at)
                   AND NEW.principal_verified_at <= NEW.decided_at) THEN
                RAISE EXCEPTION 'source merge decision lacks current project Human Owner authority'
                    USING ERRCODE='23514', CONSTRAINT='ck_source_merge_human_owner';
            END IF;
            RETURN NULL;
        END $$;
        CREATE CONSTRAINT TRIGGER trg_source_merge_approval_valid
            AFTER INSERT ON source_merge_approvals DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION rb_validate_source_merge_approval();

        CREATE FUNCTION rb_validate_source_merge_evidence() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM artifact_versions
                           WHERE id=NEW.artifact_version_id AND status='FROZEN'
                             AND content_hash=NEW.content_hash) THEN
                RAISE EXCEPTION 'source merge evidence must reference its frozen content hash'
                    USING ERRCODE='23514', CONSTRAINT='ck_source_merge_evidence_frozen';
            END IF;
            RETURN NULL;
        END $$;
        CREATE CONSTRAINT TRIGGER trg_source_merge_evidence_valid
            AFTER INSERT ON source_merge_proposal_evidence DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION rb_validate_source_merge_evidence();
        """
    )


def downgrade() -> None:
    populated = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT EXISTS (SELECT 1 FROM "
                + " UNION ALL SELECT 1 FROM ".join(TABLES)
                + " LIMIT 1)"
            )
        )
        .scalar_one()
    )
    if populated:
        raise RuntimeError("SOURCE_MERGE_GOVERNANCE_DATA_PRESERVATION_REQUIRED")
    for table in reversed(TABLES):
        op.execute(sa.text(f"DROP TRIGGER IF EXISTS trg_{table}_immutable ON {table}"))
    for table in reversed(TABLES):
        op.drop_table(table)
    op.execute(
        "DROP FUNCTION rb_validate_source_merge_evidence();"
        "DROP FUNCTION rb_validate_source_merge_approval();"
        "DROP FUNCTION rb_validate_source_merge_project_basis();"
    )
