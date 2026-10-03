"""Serialize proposal basis sealing and verify stale transitions."""

# The SQL is intentionally kept close to the persisted PostgreSQL contract.
# ruff: noqa: E501

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0021a_source_merge_gov_guards"
down_revision: str | None = "0021_source_merge_governance_bridge"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE source_merge_governance_events
            ADD COLUMN sealed_project_basis_count integer,
            ADD COLUMN sealed_identifier_basis_count integer,
            ADD COLUMN sealed_source_basis_count integer,
            ADD COLUMN sealed_evidence_basis_count integer;
        ALTER TABLE source_merge_governance_events
            ADD CONSTRAINT ck_source_merge_submission_sealed_counts CHECK (
                (event_kind='SUBMITTED' AND sealed_project_basis_count IS NOT NULL
                    AND sealed_identifier_basis_count IS NOT NULL
                    AND sealed_source_basis_count IS NOT NULL
                    AND sealed_evidence_basis_count IS NOT NULL)
                OR (event_kind<>'SUBMITTED' AND sealed_project_basis_count IS NULL
                    AND sealed_identifier_basis_count IS NULL
                    AND sealed_source_basis_count IS NULL
                    AND sealed_evidence_basis_count IS NULL)
            );

        CREATE OR REPLACE FUNCTION rb_guard_source_merge_basis_insert() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE locked_proposal uuid;
        BEGIN
            SELECT id INTO locked_proposal FROM source_merge_proposals
             WHERE id=NEW.proposal_id FOR UPDATE;
            IF locked_proposal IS NOT NULL AND EXISTS (
                SELECT 1 FROM source_merge_governance_events
                 WHERE proposal_id=NEW.proposal_id AND event_kind='SUBMITTED'
            ) THEN
                RAISE EXCEPTION 'source merge proposal basis is sealed after submission'
                    USING ERRCODE='23514', CONSTRAINT='ck_source_merge_basis_sealed';
            END IF;
            RETURN NEW;
        END $$;

        CREATE FUNCTION rb_lock_source_merge_event_proposal() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE locked_proposal uuid;
        BEGIN
            SELECT id INTO locked_proposal FROM source_merge_proposals
             WHERE id=NEW.proposal_id FOR UPDATE;
            IF locked_proposal IS NOT NULL AND NEW.event_kind='SUBMITTED' THEN
                SELECT count(*) INTO NEW.sealed_project_basis_count
                    FROM source_merge_proposal_projects WHERE proposal_id=NEW.proposal_id;
                SELECT count(*) INTO NEW.sealed_identifier_basis_count
                    FROM source_merge_proposal_identifier_basis WHERE proposal_id=NEW.proposal_id;
                SELECT count(*) INTO NEW.sealed_source_basis_count
                    FROM source_merge_proposal_source_basis WHERE proposal_id=NEW.proposal_id;
                SELECT count(*) INTO NEW.sealed_evidence_basis_count
                    FROM source_merge_proposal_evidence WHERE proposal_id=NEW.proposal_id;
            ELSIF NEW.event_kind='SUBMITTED' THEN
                NEW.sealed_project_basis_count := 0;
                NEW.sealed_identifier_basis_count := 0;
                NEW.sealed_source_basis_count := 0;
                NEW.sealed_evidence_basis_count := 0;
            END IF;
            RETURN NEW;
        END $$;
        CREATE TRIGGER trg_source_merge_event_proposal_lock
            BEFORE INSERT ON source_merge_governance_events
            FOR EACH ROW EXECUTE FUNCTION rb_lock_source_merge_event_proposal();

        CREATE FUNCTION rb_validate_source_merge_basis_seal() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE sealed source_merge_governance_events%ROWTYPE;
        BEGIN
            SELECT * INTO sealed FROM source_merge_governance_events
             WHERE proposal_id=NEW.proposal_id AND event_kind='SUBMITTED';
            IF FOUND AND (
                (SELECT count(*) FROM source_merge_proposal_projects WHERE proposal_id=NEW.proposal_id)
                    <> sealed.sealed_project_basis_count OR
                (SELECT count(*) FROM source_merge_proposal_identifier_basis WHERE proposal_id=NEW.proposal_id)
                    <> sealed.sealed_identifier_basis_count OR
                (SELECT count(*) FROM source_merge_proposal_source_basis WHERE proposal_id=NEW.proposal_id)
                    <> sealed.sealed_source_basis_count OR
                (SELECT count(*) FROM source_merge_proposal_evidence WHERE proposal_id=NEW.proposal_id)
                    <> sealed.sealed_evidence_basis_count
            ) THEN
                RAISE EXCEPTION 'source merge proposal basis is sealed after submission'
                    USING ERRCODE='23514', CONSTRAINT='ck_source_merge_basis_sealed';
            END IF;
            RETURN NULL;
        END $$;
        CREATE CONSTRAINT TRIGGER trg_source_merge_projects_seal_complete
            AFTER INSERT ON source_merge_proposal_projects DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION rb_validate_source_merge_basis_seal();
        CREATE CONSTRAINT TRIGGER trg_source_merge_identifiers_seal_complete
            AFTER INSERT ON source_merge_proposal_identifier_basis DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION rb_validate_source_merge_basis_seal();
        CREATE CONSTRAINT TRIGGER trg_source_merge_sources_seal_complete
            AFTER INSERT ON source_merge_proposal_source_basis DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION rb_validate_source_merge_basis_seal();
        CREATE CONSTRAINT TRIGGER trg_source_merge_evidence_seal_complete
            AFTER INSERT ON source_merge_proposal_evidence DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION rb_validate_source_merge_basis_seal();

        CREATE FUNCTION rb_validate_source_merge_stale_basis() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE p source_merge_proposals%ROWTYPE; basis_changed boolean;
        BEGIN
            SELECT * INTO p FROM source_merge_proposals WHERE id=NEW.proposal_id;
            SELECT
                EXISTS (
                    SELECT 1 FROM literature_source_project_links l
                    WHERE l.literature_source_id IN (p.source_a_id,p.source_b_id)
                      AND NOT EXISTS (
                          SELECT 1 FROM source_merge_proposal_projects x
                          WHERE x.proposal_id=NEW.proposal_id AND x.project_id=l.project_id
                            AND ((l.literature_source_id=p.source_a_id AND x.source_a_link_id=l.id)
                              OR (l.literature_source_id=p.source_b_id AND x.source_b_link_id=l.id))
                      )
                ) OR EXISTS (
                    SELECT 1 FROM source_merge_proposal_projects x
                    WHERE x.proposal_id=NEW.proposal_id
                      AND ((x.source_a_link_id IS NOT NULL AND NOT EXISTS (
                              SELECT 1 FROM literature_source_project_links l
                              WHERE l.id=x.source_a_link_id AND l.project_id=x.project_id
                                AND l.literature_source_id=p.source_a_id))
                        OR (x.source_b_link_id IS NOT NULL AND NOT EXISTS (
                              SELECT 1 FROM literature_source_project_links l
                              WHERE l.id=x.source_b_link_id AND l.project_id=x.project_id
                                AND l.literature_source_id=p.source_b_id)))
                ) OR EXISTS (
                    SELECT 1 FROM source_merge_proposal_identifier_basis b
                    LEFT JOIN source_identifiers i ON i.id=b.identifier_id
                    WHERE b.proposal_id=NEW.proposal_id AND
                      (i.id IS NULL OR ROW(b.source_id,b.identifier_type,b.normalized_value,
                        b.normalization_version,b.verification_status,b.is_primary,
                        b.binding_basis_artifact_version_id,b.supersedes_rejected_identifier_id,
                        b.verification_basis_artifact_version_id,b.verified_by,b.verified_at,
                        b.captured_row_version) IS DISTINCT FROM
                       ROW(i.literature_source_id,i.identifier_type,i.normalized_value,
                        i.normalization_version,i.verification_status,i.is_primary,
                        i.binding_basis_artifact_version_id,i.supersedes_rejected_identifier_id,
                        i.verification_basis_artifact_version_id,i.verified_by,i.verified_at,
                        i.row_version))
                ) OR EXISTS (
                    SELECT 1 FROM source_identifiers i
                    WHERE i.literature_source_id IN (p.source_a_id,p.source_b_id)
                      AND NOT EXISTS (
                          SELECT 1 FROM source_merge_proposal_identifier_basis b
                          WHERE b.proposal_id=NEW.proposal_id AND b.identifier_id=i.id
                      )
                ) INTO basis_changed;
            IF NOT basis_changed THEN
                RAISE EXCEPTION 'source merge proposal cannot be marked stale while its durable basis is current'
                    USING ERRCODE='23514', CONSTRAINT='ck_source_merge_event_stale_basis';
            END IF;
            RETURN NULL;
        END $$;
        CREATE CONSTRAINT TRIGGER trg_source_merge_stale_basis_valid
            AFTER INSERT ON source_merge_governance_events
            DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW WHEN (NEW.event_kind='PROPOSAL_STALE')
            EXECUTE FUNCTION rb_validate_source_merge_stale_basis();
        """
    )


def downgrade() -> None:
    connection = op.get_bind()
    populated = connection.execute(
        sa.text("SELECT EXISTS(SELECT 1 FROM source_merge_proposals)")
    ).scalar_one()
    if populated:
        raise RuntimeError("SOURCE_MERGE_GOVERNANCE_GUARD_DOWNGRADE_REQUIRES_EMPTY_PROPOSALS")
    op.execute("DROP TRIGGER trg_source_merge_stale_basis_valid ON source_merge_governance_events")
    op.execute("DROP FUNCTION rb_validate_source_merge_stale_basis()")
    for table, trigger in (
        ("source_merge_proposal_projects", "trg_source_merge_projects_seal_complete"),
        ("source_merge_proposal_identifier_basis", "trg_source_merge_identifiers_seal_complete"),
        ("source_merge_proposal_source_basis", "trg_source_merge_sources_seal_complete"),
        ("source_merge_proposal_evidence", "trg_source_merge_evidence_seal_complete"),
    ):
        op.execute(f"DROP TRIGGER {trigger} ON {table}")
    op.execute("DROP FUNCTION rb_validate_source_merge_basis_seal()")
    op.execute(
        "DROP TRIGGER trg_source_merge_event_proposal_lock ON source_merge_governance_events"
    )
    op.execute("DROP FUNCTION rb_lock_source_merge_event_proposal()")
    op.execute(
        "ALTER TABLE source_merge_governance_events "
        "DROP CONSTRAINT ck_source_merge_submission_sealed_counts, "
        "DROP COLUMN sealed_project_basis_count, "
        "DROP COLUMN sealed_identifier_basis_count, "
        "DROP COLUMN sealed_source_basis_count, "
        "DROP COLUMN sealed_evidence_basis_count"
    )
    op.execute(
        "CREATE OR REPLACE FUNCTION rb_guard_source_merge_basis_insert() RETURNS trigger "
        "LANGUAGE plpgsql AS $$ BEGIN IF EXISTS (SELECT 1 FROM source_merge_governance_events "
        "WHERE proposal_id=NEW.proposal_id AND event_kind='SUBMITTED') THEN RAISE EXCEPTION "
        "'source merge proposal basis is sealed after submission' USING ERRCODE='23514', "
        "CONSTRAINT='ck_source_merge_basis_sealed'; END IF; RETURN NEW; END $$"
    )
