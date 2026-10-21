"""Add immutable source versions and non-destructive merge lineage."""

# DDL contains intentionally literal PostgreSQL expressions and constraint definitions.
# ruff: noqa: E501

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0022_source_version_and_merge_lineage"
down_revision: str | None = "0021a_source_merge_gov_guards"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "source_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "literature_source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("literature_sources.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("version_kind", sa.String(32), nullable=False),
        sa.Column("predecessor_source_version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("correction_basis_artifact_version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("abstract", sa.Text()),
        sa.Column("authors", postgresql.JSONB(), nullable=False),
        sa.Column("publication_date", sa.Date()),
        sa.Column("venue", sa.Text()),
        sa.Column("external_version_label", sa.Text()),
        sa.Column("fulltext_artifact_version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("metadata", postgresql.JSONB()),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("content_hash", sa.String(64)),
        sa.Column("hash_scheme", sa.String(32), nullable=False),
        sa.Column("frozen_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("actors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("version_number > 0", name="ck_source_versions_number"),
        sa.CheckConstraint(
            "version_kind IN ('SUBMITTED','PREPRINT','REVISED_PREPRINT','ACCEPTED','PUBLISHED','CORRECTED','RETRACTED','WEB_SNAPSHOT','OTHER')",
            name="ck_source_versions_kind",
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT','FROZEN','SUPERSEDED','ABANDONED')",
            name="ck_source_versions_status",
        ),
        sa.CheckConstraint("hash_scheme='sha256-cjson-v1'", name="ck_source_versions_hash_scheme"),
        sa.CheckConstraint(
            "(content_hash IS NULL OR content_hash ~ '^[0-9a-f]{64}$')",
            name="ck_source_versions_hash",
        ),
        sa.CheckConstraint(
            "(status IN ('DRAFT','ABANDONED') AND content_hash IS NULL AND frozen_at IS NULL) OR "
            "(status IN ('FROZEN','SUPERSEDED') AND content_hash IS NOT NULL AND frozen_at IS NOT NULL)",
            name="ck_source_versions_freeze_fields",
        ),
        sa.CheckConstraint(
            "version_kind NOT IN ('CORRECTED','RETRACTED') OR "
            "(predecessor_source_version_id IS NOT NULL AND correction_basis_artifact_version_id IS NOT NULL)",
            name="ck_source_versions_correction_refs",
        ),
        sa.CheckConstraint(
            "predecessor_source_version_id IS NULL OR predecessor_source_version_id<>id",
            name="ck_source_versions_not_self_predecessor",
        ),
        sa.UniqueConstraint(
            "literature_source_id", "version_number", name="uq_source_versions_number"
        ),
        sa.UniqueConstraint("literature_source_id", "id", name="uq_source_versions_source_id"),
        sa.ForeignKeyConstraint(
            ["literature_source_id", "predecessor_source_version_id"],
            ["source_versions.literature_source_id", "source_versions.id"],
            ondelete="RESTRICT",
            name="fk_source_versions_predecessor_same_source",
        ),
        sa.ForeignKeyConstraint(
            ["correction_basis_artifact_version_id"],
            ["artifact_versions.id"],
            ondelete="RESTRICT",
            name="fk_source_versions_correction_artifact",
        ),
        sa.ForeignKeyConstraint(
            ["fulltext_artifact_version_id"],
            ["artifact_versions.id"],
            ondelete="RESTRICT",
            name="fk_source_versions_fulltext_artifact",
        ),
    )
    op.create_index(
        "ix_source_versions_source_status", "source_versions", ["literature_source_id", "status"]
    )
    op.create_index(
        "ix_source_versions_predecessor", "source_versions", ["predecessor_source_version_id"]
    )
    op.create_index(
        "ix_source_versions_correction_artifact",
        "source_versions",
        ["correction_basis_artifact_version_id"],
    )
    op.create_index(
        "ix_source_versions_fulltext_artifact", "source_versions", ["fulltext_artifact_version_id"]
    )

    op.add_column(
        "literature_sources",
        sa.Column("current_version_id", postgresql.UUID(as_uuid=True)),
    )
    op.add_column(
        "literature_sources",
        sa.Column("merged_into_source_id", postgresql.UUID(as_uuid=True)),
    )
    op.drop_constraint("ck_literature_sources_status", "literature_sources", type_="check")
    op.create_check_constraint(
        "ck_literature_sources_status",
        "literature_sources",
        "lifecycle_status IN ('ACTIVE','MERGED','RETIRED')",
    )
    op.create_check_constraint(
        "ck_literature_sources_merge_pointer",
        "literature_sources",
        "(lifecycle_status='MERGED' AND merged_into_source_id IS NOT NULL AND merged_into_source_id<>id) OR "
        "(lifecycle_status<>'MERGED' AND merged_into_source_id IS NULL)",
    )
    op.create_unique_constraint(
        "uq_literature_sources_id_current_version",
        "literature_sources",
        ["id", "current_version_id"],
    )
    op.create_foreign_key(
        "fk_literature_sources_current_version_same_source",
        "literature_sources",
        "source_versions",
        ["id", "current_version_id"],
        ["literature_source_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_literature_sources_merged_into",
        "literature_sources",
        "literature_sources",
        ["merged_into_source_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_literature_sources_current_version", "literature_sources", ["current_version_id"]
    )
    op.create_index(
        "ix_literature_sources_merged_into", "literature_sources", ["merged_into_source_id"]
    )

    op.create_table(
        "source_merge_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "losing_source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("literature_sources.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "winning_source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("literature_sources.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "identity_basis_artifact_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("artifact_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "merged_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("actors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("merged_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("hash_scheme", sa.String(32), nullable=False),
        sa.CheckConstraint(
            "losing_source_id<>winning_source_id", name="ck_source_merge_record_distinct"
        ),
        sa.CheckConstraint("length(btrim(reason))>0", name="ck_source_merge_record_reason"),
        sa.CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="ck_source_merge_record_hash"),
        sa.CheckConstraint(
            "hash_scheme='sha256-cjson-v1'", name="ck_source_merge_record_hash_scheme"
        ),
    )
    op.create_index(
        "uq_source_merge_record_unordered_pair",
        "source_merge_records",
        [
            sa.text("LEAST(losing_source_id,winning_source_id)"),
            sa.text("GREATEST(losing_source_id,winning_source_id)"),
        ],
        unique=True,
    )
    op.create_index("ix_source_merge_records_winner", "source_merge_records", ["winning_source_id"])
    op.create_index(
        "ix_source_merge_records_identity_basis",
        "source_merge_records",
        ["identity_basis_artifact_version_id"],
    )

    op.create_table(
        "source_version_command_receipts",
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
        sa.Column("command_name", sa.String(48), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("hash_scheme", sa.String(32), nullable=False),
        sa.Column("result_source_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("result_dto_version", sa.SmallInteger(), nullable=False),
        sa.Column("result_dto", postgresql.JSONB(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(btrim(deployment_id))>0", name="ck_source_version_receipt_deployment"
        ),
        sa.CheckConstraint(
            "command_name IN ('CREATE_SOURCE_VERSION','UPDATE_SOURCE_VERSION_DRAFT','FREEZE_SOURCE_VERSION','ABANDON_SOURCE_VERSION')",
            name="ck_source_version_receipt_command",
        ),
        sa.CheckConstraint(
            "request_hash ~ '^[0-9a-f]{64}$'", name="ck_source_version_receipt_hash"
        ),
        sa.CheckConstraint(
            "hash_scheme='sha256-cjson-v1'", name="ck_source_version_receipt_hash_scheme"
        ),
        sa.CheckConstraint("result_dto_version>0", name="ck_source_version_receipt_dto_version"),
        sa.ForeignKeyConstraint(
            ["result_source_version_id"],
            ["source_versions.id"],
            ondelete="RESTRICT",
            name="fk_source_version_receipt_result",
        ),
        sa.UniqueConstraint(
            "deployment_id",
            "actor_id",
            "project_id",
            "command_name",
            "request_id",
            name="uq_source_version_command_request",
        ),
    )
    op.create_index(
        "ix_source_version_receipt_project",
        "source_version_command_receipts",
        ["project_id", "completed_at"],
    )

    op.drop_constraint(
        "ck_source_merge_no_versions_at_0021", "source_merge_proposal_source_basis", type_="check"
    )
    op.add_column(
        "source_merge_proposal_source_basis", sa.Column("current_version_kind", sa.String(32))
    )
    op.add_column(
        "source_merge_proposal_source_basis", sa.Column("current_version_status", sa.String(16))
    )
    op.create_check_constraint(
        "ck_source_merge_version_basis_pair",
        "source_merge_proposal_source_basis",
        "(current_version_id IS NULL AND current_version_hash IS NULL AND current_version_kind IS NULL AND current_version_status IS NULL) OR "
        "(current_version_id IS NOT NULL AND current_version_hash ~ '^[0-9a-f]{64}$' AND current_version_kind IN "
        "('SUBMITTED','PREPRINT','REVISED_PREPRINT','ACCEPTED','PUBLISHED','CORRECTED','RETRACTED','WEB_SNAPSHOT','OTHER') "
        "AND current_version_status='FROZEN')",
    )
    op.create_foreign_key(
        "fk_source_merge_basis_current_version",
        "source_merge_proposal_source_basis",
        "source_versions",
        ["source_id", "current_version_id"],
        ["literature_source_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_source_merge_basis_current_version",
        "source_merge_proposal_source_basis",
        ["current_version_id"],
    )

    _install_guards()


def _install_guards() -> None:
    op.execute(
        """
        CREATE FUNCTION rb_guard_source_version() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE current_id uuid;
        BEGIN
            IF TG_OP='DELETE' THEN
                RAISE EXCEPTION 'source version history is immutable' USING ERRCODE='P17D1';
            END IF;
            IF TG_OP='INSERT' THEN
                IF NEW.status<>'DRAFT' THEN
                    RAISE EXCEPTION 'source version must begin as DRAFT' USING ERRCODE='23514', CONSTRAINT='ck_source_version_initial_draft';
                END IF;
                RETURN NEW;
            END IF;
            IF NEW.id IS DISTINCT FROM OLD.id OR NEW.literature_source_id IS DISTINCT FROM OLD.literature_source_id OR
               NEW.version_number IS DISTINCT FROM OLD.version_number OR NEW.created_by IS DISTINCT FROM OLD.created_by OR
               NEW.created_at IS DISTINCT FROM OLD.created_at OR NEW.hash_scheme IS DISTINCT FROM OLD.hash_scheme OR
               OLD.status IN ('SUPERSEDED','ABANDONED') OR
               (OLD.status='DRAFT' AND NEW.status NOT IN ('DRAFT','FROZEN','ABANDONED')) OR
               (OLD.status='FROZEN' AND NEW.status NOT IN ('FROZEN','SUPERSEDED')) THEN
                RAISE EXCEPTION 'source version transition is invalid' USING ERRCODE='23514', CONSTRAINT='ck_source_version_transition';
            END IF;
            IF OLD.status IN ('FROZEN','SUPERSEDED','ABANDONED') AND
               ROW(NEW.version_kind,NEW.predecessor_source_version_id,NEW.correction_basis_artifact_version_id,
                   NEW.title,NEW.abstract,NEW.authors,NEW.publication_date,NEW.venue,NEW.external_version_label,
                   NEW.fulltext_artifact_version_id,NEW.metadata,NEW.content_hash,NEW.frozen_at)
               IS DISTINCT FROM
               ROW(OLD.version_kind,OLD.predecessor_source_version_id,OLD.correction_basis_artifact_version_id,
                   OLD.title,OLD.abstract,OLD.authors,OLD.publication_date,OLD.venue,OLD.external_version_label,
                   OLD.fulltext_artifact_version_id,OLD.metadata,OLD.content_hash,OLD.frozen_at) THEN
                RAISE EXCEPTION 'frozen source version material is immutable' USING ERRCODE='P17D1';
            END IF;
            IF OLD.status='FROZEN' AND NEW.status='SUPERSEDED' THEN
                SELECT current_version_id INTO current_id FROM literature_sources WHERE id=OLD.literature_source_id;
                IF current_id=OLD.id THEN
                    RAISE EXCEPTION 'current source version cannot be superseded before pointer change' USING ERRCODE='23514', CONSTRAINT='ck_source_version_supersede_current';
                END IF;
            END IF;
            IF OLD.status='DRAFT' AND NEW.status='FROZEN' THEN
                IF NEW.content_hash IS NULL OR NEW.frozen_at IS NULL THEN
                    RAISE EXCEPTION 'freezing source version requires hash and time' USING ERRCODE='23514', CONSTRAINT='ck_source_versions_freeze_fields';
                END IF;
                IF NEW.version_kind IN ('CORRECTED','RETRACTED') THEN
                    SELECT current_version_id INTO current_id FROM literature_sources WHERE id=OLD.literature_source_id FOR UPDATE;
                    IF current_id IS DISTINCT FROM NEW.predecessor_source_version_id THEN
                        RAISE EXCEPTION 'correction predecessor must be the current source version' USING ERRCODE='23514', CONSTRAINT='ck_source_version_current_predecessor';
                    END IF;
                END IF;
            END IF;
            RETURN NEW;
        END $$;
        CREATE TRIGGER trg_source_version_guard BEFORE INSERT OR UPDATE OR DELETE ON source_versions
            FOR EACH ROW EXECUTE FUNCTION rb_guard_source_version();

        CREATE FUNCTION rb_validate_source_version_refs() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE predecessor source_versions%ROWTYPE;
        BEGIN
            IF NEW.status IN ('FROZEN','SUPERSEDED') THEN
                IF NEW.authors IS NULL OR jsonb_typeof(NEW.authors)<>'array' OR
                   EXISTS (SELECT 1 FROM jsonb_array_elements(NEW.authors) x
                           WHERE jsonb_typeof(x)<>'object' OR
                                 (SELECT array_agg(k.key ORDER BY k.key) FROM jsonb_object_keys(x) AS k(key))<>
                                   ARRAY['name','orcid']::text[] OR
                                 jsonb_typeof(x->'name')<>'string' OR length(btrim(x->>'name'))=0 OR
                                 (x->'orcid' IS NOT NULL AND jsonb_typeof(x->'orcid') NOT IN ('string','null'))) THEN
                    RAISE EXCEPTION 'source version authors must use the closed schema' USING ERRCODE='23514', CONSTRAINT='ck_source_version_authors';
                END IF;
                IF NEW.metadata IS NOT NULL AND (
                    jsonb_typeof(NEW.metadata)<>'object' OR
                    (SELECT array_agg(k.key ORDER BY k.key) FROM jsonb_object_keys(NEW.metadata) AS k(key))<>
                      ARRAY['issue','journal_identifier','license_label','pages','public_repository_label','volume']::text[] OR
                    EXISTS (SELECT 1 FROM jsonb_each(NEW.metadata) x WHERE jsonb_typeof(x.value) NOT IN ('string','null'))
                ) THEN
                    RAISE EXCEPTION 'source version metadata must use the six registered fields' USING ERRCODE='23514', CONSTRAINT='ck_source_version_metadata';
                END IF;
                IF NEW.correction_basis_artifact_version_id IS NOT NULL AND NOT EXISTS (
                    SELECT 1 FROM artifact_versions WHERE id=NEW.correction_basis_artifact_version_id AND status='FROZEN'
                ) THEN
                    RAISE EXCEPTION 'source version correction basis must be frozen' USING ERRCODE='23514', CONSTRAINT='ck_source_version_correction_artifact_frozen';
                END IF;
                IF NEW.fulltext_artifact_version_id IS NOT NULL AND NOT EXISTS (
                    SELECT 1 FROM artifact_versions WHERE id=NEW.fulltext_artifact_version_id AND status='FROZEN'
                ) THEN
                    RAISE EXCEPTION 'source version full text must reference a frozen artifact' USING ERRCODE='23514', CONSTRAINT='ck_source_version_fulltext_artifact_frozen';
                END IF;
                IF NEW.predecessor_source_version_id IS NOT NULL THEN
                    SELECT * INTO predecessor FROM source_versions
                     WHERE literature_source_id=NEW.literature_source_id AND id=NEW.predecessor_source_version_id;
                    IF predecessor.id IS NULL OR predecessor.status NOT IN ('FROZEN','SUPERSEDED') OR
                       predecessor.frozen_at>=NEW.frozen_at THEN
                        RAISE EXCEPTION 'source version predecessor must be a prior frozen version' USING ERRCODE='23514', CONSTRAINT='ck_source_version_predecessor_frozen';
                    END IF;
                END IF;
            END IF;
            RETURN NULL;
        END $$;
        CREATE CONSTRAINT TRIGGER trg_source_version_refs_valid
            AFTER INSERT OR UPDATE ON source_versions DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION rb_validate_source_version_refs();

        DROP TRIGGER trg_literature_sources_immutable ON literature_sources;
        CREATE OR REPLACE FUNCTION rb_guard_literature_source() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP='DELETE' THEN
                RAISE EXCEPTION 'literature source identity is immutable' USING ERRCODE='P17D1';
            END IF;
            IF ROW(NEW.id,NEW.source_kind,NEW.canonical_title,NEW.created_by,NEW.created_at,NEW.row_version)
               IS DISTINCT FROM ROW(OLD.id,OLD.source_kind,OLD.canonical_title,OLD.created_by,OLD.created_at,OLD.row_version) THEN
                RAISE EXCEPTION 'literature source identity is immutable' USING ERRCODE='P17D1';
            END IF;
            IF OLD.lifecycle_status='MERGED' OR OLD.lifecycle_status='RETIRED' THEN
                RAISE EXCEPTION 'terminal literature source cannot be changed' USING ERRCODE='23514', CONSTRAINT='ck_literature_source_terminal';
            END IF;
            IF NEW.lifecycle_status<>OLD.lifecycle_status AND NOT
               (OLD.lifecycle_status='ACTIVE' AND NEW.lifecycle_status='MERGED' AND
                NEW.current_version_id IS NOT DISTINCT FROM OLD.current_version_id AND
                NEW.merged_into_source_id IS NOT NULL AND EXISTS (
                    SELECT 1 FROM source_merge_records r WHERE r.losing_source_id=OLD.id AND r.winning_source_id=NEW.merged_into_source_id
                )) THEN
                RAISE EXCEPTION 'literature source lifecycle transition is invalid' USING ERRCODE='23514', CONSTRAINT='ck_literature_source_transition';
            END IF;
            IF NEW.merged_into_source_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM literature_sources target WHERE target.id=NEW.merged_into_source_id
                  AND target.lifecycle_status='ACTIVE' AND target.merged_into_source_id IS NULL
            ) THEN
                RAISE EXCEPTION 'merge target must be an active canonical root' USING ERRCODE='23514', CONSTRAINT='ck_literature_source_merge_root';
            END IF;
            IF NEW.current_version_id IS DISTINCT FROM OLD.current_version_id AND NEW.current_version_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM source_versions v WHERE v.id=NEW.current_version_id
                  AND v.literature_source_id=NEW.id AND v.status='FROZEN'
            ) THEN
                RAISE EXCEPTION 'source current version must be frozen and same-source' USING ERRCODE='23514', CONSTRAINT='ck_literature_source_current_version';
            END IF;
            IF OLD.lifecycle_status='ACTIVE' AND NEW.lifecycle_status='ACTIVE' AND NEW.merged_into_source_id IS NOT NULL THEN
                RAISE EXCEPTION 'active source cannot have merge target' USING ERRCODE='23514', CONSTRAINT='ck_literature_source_merge_pointer';
            END IF;
            RETURN NEW;
        END $$;
        CREATE TRIGGER trg_literature_sources_immutable BEFORE UPDATE OR DELETE ON literature_sources
            FOR EACH ROW EXECUTE FUNCTION rb_guard_literature_source();

        CREATE FUNCTION rb_guard_source_merge_record() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'source merge records are immutable' USING ERRCODE='P17D1';
        END $$;
        CREATE TRIGGER trg_source_merge_records_immutable BEFORE UPDATE OR DELETE ON source_merge_records
            FOR EACH ROW EXECUTE FUNCTION rb_guard_source_merge_record();

        CREATE FUNCTION rb_guard_source_version_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'source version command receipts are immutable' USING ERRCODE='P17D1';
        END $$;
        CREATE TRIGGER trg_source_version_receipts_immutable BEFORE UPDATE OR DELETE ON source_version_command_receipts
            FOR EACH ROW EXECUTE FUNCTION rb_guard_source_version_receipt();

        CREATE FUNCTION rb_validate_source_version_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE result_row source_versions%ROWTYPE;
        BEGIN
            SELECT * INTO result_row FROM source_versions WHERE id=NEW.result_source_version_id;
            IF result_row.id IS NULL OR NOT EXISTS (
                SELECT 1 FROM literature_source_project_links l
                WHERE l.project_id=NEW.project_id AND l.literature_source_id=result_row.literature_source_id
            ) THEN
                RAISE EXCEPTION 'source version receipt result is outside project' USING ERRCODE='23514', CONSTRAINT='ck_source_version_receipt_result';
            END IF;
            RETURN NULL;
        END $$;
        CREATE CONSTRAINT TRIGGER trg_source_version_receipt_valid AFTER INSERT ON source_version_command_receipts
            DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION rb_validate_source_version_receipt();
        """
    )
    op.execute(
        """
        CREATE FUNCTION rb_validate_source_merge_pair() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            p source_merge_proposals%ROWTYPE;
            consumed source_merge_governance_events%ROWTYPE;
            loser uuid;
            winner uuid;
        BEGIN
            IF TG_TABLE_NAME='source_merge_records' THEN
                SELECT * INTO consumed FROM source_merge_governance_events e
                 JOIN source_merge_proposals q ON q.id=e.proposal_id
                 WHERE e.event_kind='PROPOSAL_CONSUMED'
                   AND LEAST(q.source_a_id,q.source_b_id)=LEAST(NEW.losing_source_id,NEW.winning_source_id)
                   AND GREATEST(q.source_a_id,q.source_b_id)=GREATEST(NEW.losing_source_id,NEW.winning_source_id);
                IF consumed.id IS NULL THEN
                    RAISE EXCEPTION 'source merge record requires matching consumed proposal' USING ERRCODE='23514', CONSTRAINT='ck_source_merge_record_consumed_proposal';
                END IF;
                SELECT * INTO p FROM source_merge_proposals WHERE id=consumed.proposal_id;
                loser := CASE WHEN p.canonical_survivor_id=p.source_a_id THEN p.source_b_id ELSE p.source_a_id END;
                winner := p.canonical_survivor_id;
                IF NEW.losing_source_id<>loser OR NEW.winning_source_id<>winner OR NEW.reason<>p.rationale OR
                   NEW.merged_by<>consumed.actor_id OR NEW.merged_at<>consumed.occurred_at OR
                   consumed.basis_hash<>p.proposal_basis_hash OR consumed.request_hash !~ '^[0-9a-f]{64}$' OR
                   NOT EXISTS (SELECT 1 FROM source_merge_proposal_evidence e
                               WHERE e.proposal_id=p.id AND e.artifact_version_id=NEW.identity_basis_artifact_version_id
                                 AND e.content_hash=(SELECT content_hash FROM artifact_versions WHERE id=NEW.identity_basis_artifact_version_id)) OR
                   NOT EXISTS (SELECT 1 FROM literature_sources s WHERE s.id=loser AND s.lifecycle_status='MERGED' AND s.merged_into_source_id=winner) OR
                   EXISTS (SELECT 1 FROM source_merge_governance_events e WHERE e.proposal_id=p.id
                           AND e.event_kind IN ('PROPOSAL_STALE','PROPOSAL_SUPERSEDED')) OR
                   EXISTS (SELECT 1 FROM source_merge_approvals a WHERE a.proposal_id=p.id AND a.decision='REJECT') OR
                   (SELECT count(*) FROM source_merge_approvals a WHERE a.proposal_id=p.id AND a.decision='APPROVE' AND a.decision_basis_hash=p.proposal_basis_hash)<>
                   (SELECT count(*) FROM source_merge_proposal_projects x WHERE x.proposal_id=p.id) THEN
                    RAISE EXCEPTION 'source merge record does not match the approved proposal' USING ERRCODE='23514', CONSTRAINT='ck_source_merge_record_proposal_match';
                END IF;
            ELSE
                SELECT * INTO p FROM source_merge_proposals WHERE id=NEW.proposal_id;
                IF NEW.event_kind='PROPOSAL_CONSUMED' THEN
                    loser := CASE WHEN p.canonical_survivor_id=p.source_a_id THEN p.source_b_id ELSE p.source_a_id END;
                    winner := p.canonical_survivor_id;
                    IF NOT EXISTS (SELECT 1 FROM source_merge_records r WHERE r.losing_source_id=loser AND r.winning_source_id=winner
                                   AND r.merged_by=NEW.actor_id AND r.reason=p.rationale
                                   AND r.identity_basis_artifact_version_id IN (
                                       SELECT e.artifact_version_id FROM source_merge_proposal_evidence e WHERE e.proposal_id=p.id)) THEN
                        RAISE EXCEPTION 'consumed proposal requires its source merge record' USING ERRCODE='23514', CONSTRAINT='ck_source_merge_consumption_record';
                    END IF;
                END IF;
            END IF;
            RETURN NULL;
        END $$;
        CREATE CONSTRAINT TRIGGER trg_source_merge_record_proposal_match AFTER INSERT ON source_merge_records
            DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION rb_validate_source_merge_pair();
        CREATE CONSTRAINT TRIGGER trg_source_merge_consumption_record AFTER INSERT ON source_merge_governance_events
            DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (NEW.event_kind='PROPOSAL_CONSUMED')
            EXECUTE FUNCTION rb_validate_source_merge_pair();

        CREATE FUNCTION rb_validate_source_version_basis() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE p source_merge_proposals%ROWTYPE;
        BEGIN
            SELECT * INTO p FROM source_merge_proposals WHERE id=NEW.proposal_id;
            IF p.id IS NULL OR NOT EXISTS (
                SELECT 1 FROM literature_sources s
                LEFT JOIN source_versions v ON v.id=s.current_version_id AND v.literature_source_id=s.id
                WHERE s.id=NEW.source_id AND s.current_version_id IS NOT DISTINCT FROM NEW.current_version_id
                  AND v.content_hash IS NOT DISTINCT FROM NEW.current_version_hash
                  AND v.version_kind IS NOT DISTINCT FROM NEW.current_version_kind
                  AND v.status IS NOT DISTINCT FROM NEW.current_version_status
            ) THEN
                RAISE EXCEPTION 'source version basis does not match current source state' USING ERRCODE='23514', CONSTRAINT='ck_source_merge_version_basis_current';
            END IF;
            RETURN NULL;
        END $$;
        CREATE CONSTRAINT TRIGGER trg_source_merge_version_basis_current AFTER INSERT ON source_merge_proposal_source_basis
            DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION rb_validate_source_version_basis();

        CREATE OR REPLACE FUNCTION rb_validate_source_merge_stale_basis() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE p source_merge_proposals%ROWTYPE; basis_changed boolean;
        BEGIN
            SELECT * INTO p FROM source_merge_proposals WHERE id=NEW.proposal_id;
            SELECT
                EXISTS (
                    SELECT 1 FROM literature_source_project_links l
                    WHERE l.literature_source_id IN (p.source_a_id,p.source_b_id)
                      AND NOT EXISTS (SELECT 1 FROM source_merge_proposal_projects x WHERE x.proposal_id=NEW.proposal_id
                          AND x.project_id=l.project_id AND ((l.literature_source_id=p.source_a_id AND x.source_a_link_id=l.id)
                          OR (l.literature_source_id=p.source_b_id AND x.source_b_link_id=l.id)))
                ) OR EXISTS (
                    SELECT 1 FROM source_merge_proposal_projects x WHERE x.proposal_id=NEW.proposal_id
                      AND ((x.source_a_link_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM literature_source_project_links l
                          WHERE l.id=x.source_a_link_id AND l.project_id=x.project_id AND l.literature_source_id=p.source_a_id))
                        OR (x.source_b_link_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM literature_source_project_links l
                          WHERE l.id=x.source_b_link_id AND l.project_id=x.project_id AND l.literature_source_id=p.source_b_id)))
                ) OR EXISTS (
                    SELECT 1 FROM source_merge_proposal_identifier_basis b LEFT JOIN source_identifiers i ON i.id=b.identifier_id
                    WHERE b.proposal_id=NEW.proposal_id AND (i.id IS NULL OR ROW(b.source_id,b.identifier_type,b.normalized_value,
                        b.normalization_version,b.verification_status,b.is_primary,b.binding_basis_artifact_version_id,
                        b.supersedes_rejected_identifier_id,b.verification_basis_artifact_version_id,b.verified_by,b.verified_at,
                        b.captured_row_version) IS DISTINCT FROM ROW(i.literature_source_id,i.identifier_type,i.normalized_value,
                        i.normalization_version,i.verification_status,i.is_primary,i.binding_basis_artifact_version_id,
                        i.supersedes_rejected_identifier_id,i.verification_basis_artifact_version_id,i.verified_by,i.verified_at,i.row_version))
                ) OR EXISTS (SELECT 1 FROM source_identifiers i WHERE i.literature_source_id IN (p.source_a_id,p.source_b_id)
                    AND NOT EXISTS (SELECT 1 FROM source_merge_proposal_identifier_basis b WHERE b.proposal_id=NEW.proposal_id AND b.identifier_id=i.id))
                OR EXISTS (
                    SELECT 1 FROM source_merge_proposal_source_basis b JOIN literature_sources s ON s.id=b.source_id
                    LEFT JOIN source_versions v ON v.id=s.current_version_id AND v.literature_source_id=s.id
                    WHERE b.proposal_id=NEW.proposal_id AND
                        (b.current_version_id IS DISTINCT FROM s.current_version_id OR
                         b.current_version_hash IS DISTINCT FROM v.content_hash OR
                         b.current_version_kind IS DISTINCT FROM v.version_kind OR
                         b.current_version_status IS DISTINCT FROM v.status)
                ) INTO basis_changed;
            IF NOT basis_changed THEN
                RAISE EXCEPTION 'source merge proposal cannot be marked stale while its durable basis is current'
                    USING ERRCODE='23514', CONSTRAINT='ck_source_merge_event_stale_basis';
            END IF;
            RETURN NULL;
        END $$;
        """
    )


def downgrade() -> None:
    connection = op.get_bind()
    populated = connection.execute(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM source_versions) OR EXISTS(SELECT 1 FROM source_merge_records) "
            "OR EXISTS(SELECT 1 FROM source_version_command_receipts) "
            "OR EXISTS(SELECT 1 FROM literature_sources WHERE current_version_id IS NOT NULL OR merged_into_source_id IS NOT NULL) "
            "OR EXISTS(SELECT 1 FROM source_merge_proposal_source_basis WHERE current_version_id IS NOT NULL OR current_version_hash IS NOT NULL OR current_version_kind IS NOT NULL OR current_version_status IS NOT NULL)"
        )
    ).scalar_one()
    if populated:
        raise RuntimeError("SOURCE_VERSION_LINEAGE_DATA_PRESERVATION_REQUIRED")

    op.drop_constraint(
        "fk_source_merge_basis_current_version",
        "source_merge_proposal_source_basis",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_source_merge_basis_current_version", table_name="source_merge_proposal_source_basis"
    )
    op.drop_constraint(
        "ck_source_merge_version_basis_pair", "source_merge_proposal_source_basis", type_="check"
    )
    op.drop_column("source_merge_proposal_source_basis", "current_version_status")
    op.drop_column("source_merge_proposal_source_basis", "current_version_kind")
    op.create_check_constraint(
        "ck_source_merge_no_versions_at_0021",
        "source_merge_proposal_source_basis",
        "current_version_id IS NULL AND current_version_hash IS NULL",
    )
    op.drop_constraint(
        "fk_literature_sources_current_version_same_source",
        "literature_sources",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_literature_sources_id_current_version", "literature_sources", type_="unique"
    )
    op.drop_constraint(
        "fk_literature_sources_merged_into", "literature_sources", type_="foreignkey"
    )
    op.drop_index("ix_literature_sources_current_version", table_name="literature_sources")
    op.drop_index("ix_literature_sources_merged_into", table_name="literature_sources")
    op.drop_constraint("ck_literature_sources_merge_pointer", "literature_sources", type_="check")
    op.drop_constraint("ck_literature_sources_status", "literature_sources", type_="check")
    op.create_check_constraint(
        "ck_literature_sources_status",
        "literature_sources",
        "lifecycle_status IN ('ACTIVE','RETIRED')",
    )
    op.drop_column("literature_sources", "merged_into_source_id")
    op.drop_column("literature_sources", "current_version_id")

    # Both triggers share rb_validate_source_merge_pair; remove all dependents
    # before dropping that function.
    op.execute("DROP TRIGGER trg_source_merge_consumption_record ON source_merge_governance_events")
    op.execute("DROP TRIGGER trg_source_merge_record_proposal_match ON source_merge_records")
    op.execute("DROP FUNCTION rb_validate_source_merge_pair()")
    for table, trigger, function in (
        (
            "source_merge_proposal_source_basis",
            "trg_source_merge_version_basis_current",
            "rb_validate_source_version_basis",
        ),
        (
            "source_version_command_receipts",
            "trg_source_version_receipt_valid",
            "rb_validate_source_version_receipt",
        ),
    ):
        op.execute(sa.text(f"DROP TRIGGER {trigger} ON {table}"))
        op.execute(sa.text(f"DROP FUNCTION {function}()"))
    op.execute(
        "DROP TRIGGER trg_source_version_receipts_immutable ON source_version_command_receipts"
    )
    op.execute("DROP FUNCTION rb_guard_source_version_receipt()")
    op.execute("DROP TRIGGER trg_source_merge_records_immutable ON source_merge_records")
    op.execute("DROP FUNCTION rb_guard_source_merge_record()")
    op.execute("DROP TRIGGER trg_literature_sources_immutable ON literature_sources")
    op.execute("DROP FUNCTION rb_guard_literature_source()")
    op.execute(
        "CREATE FUNCTION rb_guard_literature_source() RETURNS trigger LANGUAGE plpgsql AS $$ "
        "BEGIN RAISE EXCEPTION 'literature source identity is immutable' USING ERRCODE='P17D1'; END $$"
    )
    op.execute(
        "CREATE TRIGGER trg_literature_sources_immutable BEFORE UPDATE OR DELETE ON literature_sources FOR EACH ROW EXECUTE FUNCTION rb_guard_literature_source()"
    )
    op.execute("DROP TRIGGER trg_source_version_refs_valid ON source_versions")
    op.execute("DROP FUNCTION rb_validate_source_version_refs()")
    op.execute("DROP TRIGGER trg_source_version_guard ON source_versions")
    op.execute("DROP FUNCTION rb_guard_source_version()")
    op.drop_index("ix_source_version_receipt_project", table_name="source_version_command_receipts")
    op.drop_table("source_version_command_receipts")
    op.drop_index("ix_source_merge_records_identity_basis", table_name="source_merge_records")
    op.drop_index("ix_source_merge_records_winner", table_name="source_merge_records")
    op.drop_index("uq_source_merge_record_unordered_pair", table_name="source_merge_records")
    op.drop_table("source_merge_records")
    op.drop_index("ix_source_versions_fulltext_artifact", table_name="source_versions")
    op.drop_index("ix_source_versions_correction_artifact", table_name="source_versions")
    op.drop_index("ix_source_versions_predecessor", table_name="source_versions")
    op.drop_index("ix_source_versions_source_status", table_name="source_versions")
    op.drop_table("source_versions")
    # Restore the accepted 0021a stale-basis validator exactly; the 0021a
    # downgrade owns dropping this trigger and function afterward.
    op.execute(
        sa.text("""
        CREATE OR REPLACE FUNCTION rb_validate_source_merge_stale_basis() RETURNS trigger
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
        END $$
    """)
    )
