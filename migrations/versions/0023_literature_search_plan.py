"""Add versioned, project-scoped literature search plans."""

# DDL contains intentionally literal PostgreSQL expressions and constraint definitions.
# ruff: noqa: E501

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0023_literature_search_plan"
down_revision: str | None = "0022_source_version_and_merge_lineage"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "literature_search_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["actors.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("project_id", "id", name="uq_literature_search_plans_project_id"),
        sa.UniqueConstraint("id", "current_version_id", name="uq_lsp_id_current_version"),
    )
    op.create_index("ix_literature_search_plans_project", "literature_search_plans", ["project_id"])
    op.create_table(
        "literature_search_plan_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("source_scope", sa.String(32), nullable=False),
        sa.Column("inclusion_criteria", postgresql.JSONB()),
        sa.Column("exclusion_criteria", postgresql.JSONB()),
        sa.Column("time_range", postgresql.JSONB()),
        sa.Column("language_scope", postgresql.JSONB()),
        sa.Column("search_strategy", sa.String(32), nullable=False),
        sa.Column("planned_providers", postgresql.JSONB(), nullable=False),
        sa.Column("stopping_rule", postgresql.JSONB()),
        sa.Column("content_hash", sa.CHAR(64)),
        sa.Column("hash_scheme", sa.String(32), nullable=False, server_default="sha256-cjson-v1"),
        sa.Column("frozen_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint("version_number > 0", name="ck_lspv_version_number"),
        sa.CheckConstraint(
            "status IN ('DRAFT','FROZEN','SUPERSEDED','ABANDONED')", name="ck_lspv_status"
        ),
        sa.CheckConstraint(
            "source_scope IN ('BIBLIOGRAPHIC','WEB','LOCAL_CORPUS','MIXED')",
            name="ck_lspv_source_scope",
        ),
        sa.CheckConstraint(
            "search_strategy IN ('KEYWORD','PERSPECTIVE_GUIDED','SYSTEMATIC','SNOWBALL','HYBRID')",
            name="ck_lspv_search_strategy",
        ),
        sa.CheckConstraint("hash_scheme='sha256-cjson-v1'", name="ck_lspv_hash_scheme"),
        sa.CheckConstraint(
            "content_hash IS NULL OR content_hash ~ '^[0-9a-f]{64}$'", name="ck_lspv_hash"
        ),
        sa.CheckConstraint(
            "(status IN ('DRAFT','ABANDONED') AND content_hash IS NULL AND frozen_at IS NULL) OR (status IN ('FROZEN','SUPERSEDED') AND content_hash IS NOT NULL AND frozen_at IS NOT NULL AND language_scope IS NOT NULL)",
            name="ck_lspv_freeze_fields",
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["literature_search_plans.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["actors.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("plan_id", "version_number", name="uq_lspv_plan_version"),
        sa.UniqueConstraint("plan_id", "id", name="uq_lspv_plan_id"),
    )
    op.create_index("ix_lspv_plan_status", "literature_search_plan_versions", ["plan_id", "status"])
    op.create_foreign_key(
        "fk_lsp_current_version_same_plan",
        "literature_search_plans",
        "literature_search_plan_versions",
        ["id", "current_version_id"],
        ["plan_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_table(
        "search_plan_question_inputs",
        sa.Column("plan_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("research_question_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint(
            "plan_version_id", "research_question_version_id", name="pk_search_plan_question_inputs"
        ),
        sa.CheckConstraint("ordinal >= 0", name="ck_spqi_ordinal"),
        sa.UniqueConstraint("plan_version_id", "ordinal", name="uq_spqi_ordinal"),
        sa.ForeignKeyConstraint(
            ["plan_version_id"], ["literature_search_plan_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["research_question_version_id"], ["research_question_versions.id"], ondelete="RESTRICT"
        ),
    )
    op.create_index(
        "ix_spqi_question_version", "search_plan_question_inputs", ["research_question_version_id"]
    )
    op.create_table(
        "literature_search_plan_command_receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("deployment_id", sa.String(255), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("command_name", sa.String(64), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_hash", sa.CHAR(64), nullable=False),
        sa.Column("hash_scheme", sa.String(32), nullable=False),
        sa.Column("result_plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("result_plan_version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("result_dto_version", sa.Integer(), nullable=False),
        sa.Column("result_dto", postgresql.JSONB(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("request_hash ~ '^[0-9a-f]{64}$'", name="ck_lsp_receipt_hash"),
        sa.CheckConstraint("hash_scheme='sha256-cjson-v1'", name="ck_lsp_receipt_scheme"),
        sa.UniqueConstraint(
            "deployment_id",
            "actor_id",
            "project_id",
            "command_name",
            "request_id",
            name="uq_lsp_receipt_scope",
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["actors.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["project_id", "result_plan_id"],
            ["literature_search_plans.project_id", "literature_search_plans.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["result_plan_id", "result_plan_version_id"],
            ["literature_search_plan_versions.plan_id", "literature_search_plan_versions.id"],
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_lsp_receipts_result_version",
        "literature_search_plan_command_receipts",
        ["result_plan_version_id"],
    )
    op.execute("""
        CREATE FUNCTION rb_guard_lsp_identity() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP='DELETE' THEN RAISE EXCEPTION 'literature search plan identity is immutable' USING ERRCODE='P17D1'; END IF;
          IF NEW.id<>OLD.id OR NEW.project_id<>OLD.project_id OR NEW.created_by<>OLD.created_by OR NEW.created_at<>OLD.created_at THEN
            RAISE EXCEPTION 'literature search plan identity is immutable' USING ERRCODE='P17D1';
          END IF;
          IF NEW.current_version_id IS DISTINCT FROM OLD.current_version_id THEN
            IF NEW.current_version_id IS NULL OR NOT EXISTS (SELECT 1 FROM literature_search_plan_versions v WHERE v.id=NEW.current_version_id AND v.plan_id=NEW.id AND v.status='FROZEN') THEN
              RAISE EXCEPTION 'current search plan version must be frozen and owned' USING ERRCODE='23514', CONSTRAINT='fk_lsp_current_version_same_plan';
            END IF;
            IF OLD.current_version_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM literature_search_plan_versions v WHERE v.id=OLD.current_version_id AND v.status='SUPERSEDED') THEN
              RAISE EXCEPTION 'prior current search plan version must be superseded first' USING ERRCODE='23514', CONSTRAINT='ck_lsp_prior_current_superseded';
            END IF;
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_lsp_identity_guard BEFORE UPDATE OR DELETE ON literature_search_plans FOR EACH ROW EXECUTE FUNCTION rb_guard_lsp_identity();
        CREATE FUNCTION rb_guard_lsp_version() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP='DELETE' THEN RAISE EXCEPTION 'literature search plan versions are immutable history' USING ERRCODE='P17D1'; END IF;
          IF TG_OP='INSERT' THEN RETURN NEW; END IF;
          IF OLD.status IN ('FROZEN','SUPERSEDED') THEN
            IF NEW.status='SUPERSEDED' AND OLD.status='FROZEN' AND
               (to_jsonb(NEW)-'status'-'row_version')=(to_jsonb(OLD)-'status'-'row_version') THEN RETURN NEW; END IF;
            RAISE EXCEPTION 'frozen search plan material is immutable' USING ERRCODE='P17D1';
          END IF;
          IF OLD.status='DRAFT' AND NEW.status IN ('FROZEN','ABANDONED') THEN
            IF (to_jsonb(NEW)-'status'-'content_hash'-'frozen_at'-'row_version') <>
               (to_jsonb(OLD)-'status'-'content_hash'-'frozen_at'-'row_version') THEN
              RAISE EXCEPTION 'transition cannot change search plan material' USING ERRCODE='P17D1';
            END IF;
            IF NEW.status='FROZEN' AND (NEW.content_hash IS NULL OR NEW.frozen_at IS NULL OR NEW.language_scope IS NULL) THEN
              RAISE EXCEPTION 'frozen search plan requires hash, time, and language scope' USING ERRCODE='23514', CONSTRAINT='ck_lspv_freeze_fields';
            END IF;
            IF NEW.status='FROZEN' AND NOT EXISTS (SELECT 1 FROM search_plan_question_inputs i WHERE i.plan_version_id=NEW.id) THEN
              RAISE EXCEPTION 'frozen search plan requires a ResearchQuestion input' USING ERRCODE='23514', CONSTRAINT='ck_lspv_question_required';
            END IF;
            IF NEW.status='ABANDONED' AND (NEW.content_hash IS NOT NULL OR NEW.frozen_at IS NOT NULL) THEN
              RAISE EXCEPTION 'abandoned draft cannot acquire frozen fields' USING ERRCODE='23514', CONSTRAINT='ck_lspv_freeze_fields';
            END IF;
            RETURN NEW;
          END IF;
          IF OLD.status<>'DRAFT' OR NEW.status<>'DRAFT' THEN
            RAISE EXCEPTION 'invalid search plan version transition' USING ERRCODE='P17D2';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_lsp_version_guard BEFORE UPDATE OR DELETE ON literature_search_plan_versions FOR EACH ROW EXECUTE FUNCTION rb_guard_lsp_version();
        CREATE FUNCTION rb_guard_spqi() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE qid uuid; qproject uuid; pproject uuid;
        BEGIN
          IF TG_OP='DELETE' THEN
            IF (SELECT status FROM literature_search_plan_versions WHERE id=OLD.plan_version_id)<>'DRAFT' THEN RAISE EXCEPTION 'frozen search plan inputs are immutable' USING ERRCODE='P17D1'; END IF;
            RETURN OLD;
          END IF;
          IF TG_OP='UPDATE' THEN
            IF NEW.plan_version_id<>OLD.plan_version_id OR
               NEW.research_question_version_id<>OLD.research_question_version_id OR
               (SELECT status FROM literature_search_plan_versions WHERE id=OLD.plan_version_id)<>'DRAFT' THEN
              RAISE EXCEPTION 'question input identity is immutable' USING ERRCODE='P17D1';
            END IF;
          END IF;
          IF (SELECT status FROM literature_search_plan_versions WHERE id=NEW.plan_version_id)<>'DRAFT' THEN RAISE EXCEPTION 'frozen search plan inputs are immutable' USING ERRCODE='P17D1'; END IF;
          SELECT q.id,q.project_id,p.project_id INTO qid,qproject,pproject FROM research_question_versions qv JOIN research_questions q ON q.id=qv.research_question_id JOIN literature_search_plan_versions pv ON pv.id=NEW.plan_version_id JOIN literature_search_plans p ON p.id=pv.plan_id WHERE qv.id=NEW.research_question_version_id AND qv.status IN ('FROZEN','SUPERSEDED') AND qv.content_hash IS NOT NULL AND qv.frozen_at IS NOT NULL;
          IF qid IS NULL OR qproject<>pproject THEN RAISE EXCEPTION 'search plan question must belong to same project' USING ERRCODE='23514', CONSTRAINT='ck_spqi_same_project'; END IF;
          IF EXISTS (SELECT 1 FROM search_plan_question_inputs i JOIN research_question_versions other_v ON other_v.id=i.research_question_version_id WHERE i.plan_version_id=NEW.plan_version_id AND i.research_question_version_id<>NEW.research_question_version_id AND other_v.research_question_id=qid) THEN RAISE EXCEPTION 'duplicate ResearchQuestion identity in plan version' USING ERRCODE='23505', CONSTRAINT='uq_spqi_question_identity'; END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_spqi_guard BEFORE INSERT OR UPDATE OR DELETE ON search_plan_question_inputs FOR EACH ROW EXECUTE FUNCTION rb_guard_spqi();
        CREATE FUNCTION rb_guard_lsp_receipt() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'literature search plan receipts are immutable' USING ERRCODE='P17D1'; END $$;
        CREATE TRIGGER trg_lsp_receipt_guard BEFORE UPDATE OR DELETE ON literature_search_plan_command_receipts FOR EACH ROW EXECUTE FUNCTION rb_guard_lsp_receipt();
    """)


def downgrade() -> None:
    op.execute("""
      DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM literature_search_plan_command_receipts) OR
           EXISTS (SELECT 1 FROM search_plan_question_inputs) OR
           EXISTS (SELECT 1 FROM literature_search_plan_versions) OR
           EXISTS (SELECT 1 FROM literature_search_plans) THEN
          RAISE EXCEPTION '0023 downgrade refused: preserve non-empty LiteratureSearchPlan data';
        END IF;
      END $$;
    """)
    op.execute("DROP TRIGGER trg_lsp_receipt_guard ON literature_search_plan_command_receipts")
    op.execute("DROP FUNCTION rb_guard_lsp_receipt()")
    op.execute("DROP TRIGGER trg_spqi_guard ON search_plan_question_inputs")
    op.execute("DROP FUNCTION rb_guard_spqi()")
    op.execute("DROP TRIGGER trg_lsp_version_guard ON literature_search_plan_versions")
    op.execute("DROP FUNCTION rb_guard_lsp_version()")
    op.execute("DROP TRIGGER trg_lsp_identity_guard ON literature_search_plans")
    op.execute("DROP FUNCTION rb_guard_lsp_identity()")
    op.drop_table("literature_search_plan_command_receipts")
    op.drop_table("search_plan_question_inputs")
    op.drop_constraint(
        "fk_lsp_current_version_same_plan", "literature_search_plans", type_="foreignkey"
    )
    op.drop_index("ix_lspv_plan_status", table_name="literature_search_plan_versions")
    op.drop_table("literature_search_plan_versions")
    op.drop_index("ix_literature_search_plans_project", table_name="literature_search_plans")
    op.drop_table("literature_search_plans")
