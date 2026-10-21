# ruff: noqa: E501
"""Approved M3 literature evidence, review history and independent support snapshots."""

from alembic import op

revision = "0030_literature_evidence"
down_revision = "0029_metadata_observations"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE literature_evidence (
      id UUID PRIMARY KEY, project_id UUID NOT NULL REFERENCES projects ON DELETE RESTRICT,
      source_version_id UUID NOT NULL REFERENCES source_versions ON DELETE RESTRICT,
      evidence_type VARCHAR(32) NOT NULL CHECK(evidence_type='QUOTATION'),
      locator JSONB NOT NULL CHECK(jsonb_typeof(locator)='object' AND locator ?& ARRAY['page','section','paragraph','figure','table','quote_span'] AND (locator - ARRAY['page','section','paragraph','figure','table','quote_span'])='{}'::jsonb AND jsonb_typeof(locator->'paragraph')='string' AND jsonb_typeof(locator->'quote_span')='string' AND length(locator->>'paragraph')>0 AND length(locator->>'quote_span')>0),
      extracted_statement TEXT NOT NULL CHECK(length(btrim(extracted_statement)) BETWEEN 1 AND 2000),
      normalized_assertion TEXT CHECK(length(btrim(normalized_assertion)) BETWEEN 1 AND 2000),
      extraction_method VARCHAR(16) NOT NULL CHECK(extraction_method IN ('HUMAN','RULE')),
      extraction_execution_ref JSONB CHECK(extraction_execution_ref IS NULL),
      confidence VARCHAR(16) NOT NULL CHECK(confidence='MODERATE'),
      review_status VARCHAR(16) NOT NULL DEFAULT 'UNREVIEWED' CHECK(review_status IN ('UNREVIEWED','VERIFIED','DISPUTED','REJECTED')),
      created_by UUID NOT NULL REFERENCES actors ON DELETE RESTRICT, created_at TIMESTAMPTZ NOT NULL,
      content_hash CHAR(64) NOT NULL CHECK(content_hash ~ '^[0-9a-f]{64}$'),
      hash_scheme VARCHAR(32) NOT NULL CHECK(hash_scheme='sha256-cjson-v1')
    );
    CREATE TABLE literature_evidence_review_events (
      id UUID PRIMARY KEY, literature_evidence_id UUID NOT NULL REFERENCES literature_evidence ON DELETE RESTRICT,
      prior_status VARCHAR(16) NOT NULL, new_status VARCHAR(16) NOT NULL,
      reviewed_by UUID NOT NULL REFERENCES actors ON DELETE RESTRICT, reviewed_at TIMESTAMPTZ NOT NULL,
      basis TEXT NOT NULL CHECK(length(btrim(basis)) BETWEEN 1 AND 4096),
      CHECK((prior_status='UNREVIEWED' AND new_status IN ('VERIFIED','DISPUTED','REJECTED')) OR
            (prior_status='VERIFIED' AND new_status='DISPUTED') OR
            (prior_status='DISPUTED' AND new_status IN ('VERIFIED','REJECTED')))
    );
    CREATE TABLE literature_support_snapshots (
      id UUID PRIMARY KEY, project_id UUID NOT NULL REFERENCES projects ON DELETE RESTRICT,
      claim_version_id UUID REFERENCES claim_versions ON DELETE RESTRICT,
      research_question_version_id UUID REFERENCES research_question_versions ON DELETE RESTRICT,
      hypothesis_version_id UUID REFERENCES hypothesis_versions ON DELETE RESTRICT,
      CHECK(num_nonnulls(claim_version_id,research_question_version_id,hypothesis_version_id)=1),
      snapshot_number INT NOT NULL CHECK(snapshot_number>0),
      previous_snapshot_id UUID REFERENCES literature_support_snapshots ON DELETE RESTRICT,
      CHECK((snapshot_number=1)=(previous_snapshot_id IS NULL)),
      literature_support_set_hash CHAR(64) NOT NULL CHECK(literature_support_set_hash ~ '^[0-9a-f]{64}$'),
      content_hash CHAR(64) NOT NULL CHECK(content_hash ~ '^[0-9a-f]{64}$'),
      hash_scheme VARCHAR(32) NOT NULL CHECK(hash_scheme='sha256-cjson-v1'),
      created_by UUID NOT NULL REFERENCES actors ON DELETE RESTRICT,
      created_at TIMESTAMPTZ NOT NULL, frozen_at TIMESTAMPTZ NOT NULL CHECK(frozen_at=created_at)
    );
    CREATE TABLE literature_evidence_relations (
      id UUID PRIMARY KEY, literature_support_snapshot_id UUID NOT NULL REFERENCES literature_support_snapshots ON DELETE RESTRICT,
      literature_evidence_id UUID NOT NULL REFERENCES literature_evidence ON DELETE RESTRICT,
      relation_type VARCHAR(16) NOT NULL CHECK(relation_type IN ('SUPPORTS','CONTRADICTS','QUALIFIES','MOTIVATES','PRIOR_ART','CONTEXTUALIZES')),
      ordinal INT NOT NULL CHECK(ordinal>=0), qualification TEXT CHECK(length(btrim(qualification)) BETWEEN 1 AND 4096),
      created_by UUID NOT NULL REFERENCES actors ON DELETE RESTRICT, created_at TIMESTAMPTZ NOT NULL,
      UNIQUE(literature_support_snapshot_id,ordinal),
      UNIQUE(literature_support_snapshot_id,literature_evidence_id,relation_type)
    );
    CREATE TABLE literature_evidence_command_receipts (
      id UUID PRIMARY KEY, deployment_id TEXT NOT NULL, project_id UUID NOT NULL REFERENCES projects ON DELETE RESTRICT,
      actor_id UUID NOT NULL REFERENCES actors ON DELETE RESTRICT, command_name TEXT NOT NULL CHECK(command_name IN ('IMPORT_DOCUMENT','CREATE_EVIDENCE','REVIEW_EVIDENCE','CREATE_SUPPORT')),
      request_id UUID NOT NULL, input_hash CHAR(64) NOT NULL CHECK(input_hash ~ '^[0-9a-f]{64}$'),
      result_artifact_version_id UUID REFERENCES artifact_versions ON DELETE RESTRICT,
      result_evidence_id UUID REFERENCES literature_evidence ON DELETE RESTRICT,
      result_review_event_id UUID REFERENCES literature_evidence_review_events ON DELETE RESTRICT,
      result_snapshot_id UUID REFERENCES literature_support_snapshots ON DELETE RESTRICT,
      CHECK(num_nonnulls(result_artifact_version_id,result_evidence_id,result_review_event_id,result_snapshot_id)=1),
      completed_at TIMESTAMPTZ NOT NULL,
      UNIQUE(deployment_id,project_id,actor_id,command_name,request_id)
    );
    CREATE FUNCTION m3_evidence_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP='INSERT' THEN
        IF NEW.review_status<>'UNREVIEWED' OR NOT EXISTS (
          SELECT 1 FROM source_versions v
          JOIN literature_source_project_links l ON l.literature_source_id=v.literature_source_id AND l.project_id=NEW.project_id
          JOIN artifact_versions av ON av.id=v.fulltext_artifact_version_id
          JOIN artifacts a ON a.id=av.artifact_id AND a.project_id=NEW.project_id
          WHERE v.id=NEW.source_version_id AND v.status IN ('FROZEN','SUPERSEDED') AND av.status IN ('FROZEN','SUPERSEDED')) THEN
          RAISE EXCEPTION 'M3 source document closure' USING ERRCODE='P17D3'; END IF;
        RETURN NEW;
      END IF;
      IF TG_OP='UPDATE' AND (to_jsonb(OLD)-'review_status')=(to_jsonb(NEW)-'review_status')
        AND NEW.review_status<>OLD.review_status AND EXISTS (
          SELECT 1 FROM literature_evidence_review_events e WHERE e.literature_evidence_id=NEW.id
          AND e.prior_status=OLD.review_status AND e.new_status=NEW.review_status
          AND e.id=(SELECT id FROM literature_evidence_review_events WHERE literature_evidence_id=NEW.id ORDER BY reviewed_at DESC,id DESC LIMIT 1)) THEN RETURN NEW; END IF;
      RAISE EXCEPTION 'M3 immutable evidence content' USING ERRCODE='P17D1';
    END $$;
    CREATE TRIGGER m3_evidence_guard BEFORE INSERT OR UPDATE OR DELETE ON literature_evidence FOR EACH ROW EXECUTE FUNCTION m3_evidence_guard();
    CREATE FUNCTION m3_review_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE e literature_evidence;
    BEGIN
      SELECT * INTO e FROM literature_evidence WHERE id=NEW.literature_evidence_id FOR UPDATE;
      IF e.review_status<>NEW.prior_status OR NEW.reviewed_at<e.created_at OR NOT EXISTS (
        SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id
        JOIN project_role_assignments r ON r.membership_id=m.id
        WHERE a.id=NEW.reviewed_by AND a.actor_type='HUMAN' AND a.retired_at IS NULL
        AND m.project_id=e.project_id AND m.status='ACTIVE'
        AND r.role IN ('OWNER','RESEARCHER','REVIEWER') AND r.effective_from<=NEW.reviewed_at
        AND (r.effective_until IS NULL OR NEW.reviewed_at<r.effective_until))
        OR (NEW.new_status='VERIFIED' AND NEW.reviewed_by=e.created_by) THEN
        RAISE EXCEPTION 'M3 review authority/separation/transition' USING ERRCODE='P17D3'; END IF;
      UPDATE literature_evidence SET review_status=NEW.new_status WHERE id=e.id;
      RETURN NEW;
    END $$;
    CREATE TRIGGER m3_review_guard AFTER INSERT ON literature_evidence_review_events FOR EACH ROW EXECUTE FUNCTION m3_review_guard();
    CREATE FUNCTION m3_support_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE s literature_support_snapshots; p UUID; st TEXT; prev literature_support_snapshots;
    BEGIN
      IF TG_TABLE_NAME='literature_evidence_relations' THEN
        SELECT * INTO s FROM literature_support_snapshots WHERE id=NEW.literature_support_snapshot_id;
        IF NOT EXISTS (SELECT 1 FROM literature_support_snapshots WHERE id=s.id AND xmin::text::bigint=pg_current_xact_id()::text::bigint) THEN
          RAISE EXCEPTION 'M3 sealed relation set' USING ERRCODE='P17D1'; END IF;
        IF NEW.created_by<>s.created_by OR NOT EXISTS (
          SELECT 1 FROM literature_evidence e JOIN source_versions v ON v.id=e.source_version_id
          WHERE e.id=NEW.literature_evidence_id AND e.project_id=s.project_id AND v.status IN ('FROZEN','SUPERSEDED')
          AND (NEW.relation_type<>'SUPPORTS' OR (e.review_status='VERIFIED' AND v.version_kind<>'RETRACTED'
          AND NOT EXISTS (SELECT 1 FROM literature_sources ls JOIN source_versions cv ON cv.id=ls.current_version_id
            WHERE ls.id=v.literature_source_id AND (cv.version_kind='RETRACTED' OR (cv.version_kind='CORRECTED' AND cv.id<>v.id)))
          AND EXISTS (SELECT 1 FROM literature_evidence_review_events re JOIN actors a ON a.id=re.reviewed_by
          WHERE re.literature_evidence_id=e.id AND re.new_status='VERIFIED' AND a.actor_type='HUMAN'
          AND re.reviewed_by<>e.created_by AND re.reviewed_by<>s.created_by
          AND re.id=(SELECT id FROM literature_evidence_review_events WHERE literature_evidence_id=e.id ORDER BY reviewed_at DESC,id DESC LIMIT 1))))) THEN
          RAISE EXCEPTION 'M3 support closure/separation' USING ERRCODE='P17D3'; END IF;
        RETURN NEW;
      END IF;
      s:=NEW;
      IF s.claim_version_id IS NOT NULL THEN
        SELECT c.project_id,v.status INTO p,st FROM claim_versions v JOIN claims c ON c.id=v.claim_id WHERE v.id=s.claim_version_id;
      ELSIF s.hypothesis_version_id IS NOT NULL THEN
        SELECT h.project_id,v.status INTO p,st FROM hypothesis_versions v JOIN hypotheses h ON h.id=v.hypothesis_id WHERE v.id=s.hypothesis_version_id;
      ELSE
        SELECT q.project_id,v.status INTO p,st FROM research_question_versions v JOIN research_questions q ON q.id=v.research_question_id WHERE v.id=s.research_question_version_id;
      END IF;
      IF p IS DISTINCT FROM s.project_id OR st NOT IN ('FROZEN','SUPERSEDED') THEN
        RAISE EXCEPTION 'M3 frozen target project' USING ERRCODE='P17D3'; END IF;
      IF s.previous_snapshot_id IS NOT NULL THEN
        SELECT * INTO prev FROM literature_support_snapshots WHERE id=s.previous_snapshot_id;
        IF prev.project_id<>s.project_id OR prev.snapshot_number+1<>s.snapshot_number
           OR prev.claim_version_id IS DISTINCT FROM s.claim_version_id
           OR prev.hypothesis_version_id IS DISTINCT FROM s.hypothesis_version_id
           OR prev.research_question_version_id IS DISTINCT FROM s.research_question_version_id THEN
          RAISE EXCEPTION 'M3 predecessor mismatch' USING ERRCODE='P17D3'; END IF;
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER m3_snapshot_guard BEFORE INSERT ON literature_support_snapshots FOR EACH ROW EXECUTE FUNCTION m3_support_guard();
    CREATE TRIGGER m3_relation_guard BEFORE INSERT ON literature_evidence_relations FOR EACH ROW EXECUTE FUNCTION m3_support_guard();
    """)
    for table in (
        "literature_evidence_review_events",
        "literature_support_snapshots",
        "literature_evidence_relations",
        "literature_evidence_command_receipts",
    ):
        op.execute(
            f"CREATE TRIGGER m3_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION m2_immutable()"
        )
    for table, columns in {
        "literature_evidence": ["project_id,review_status", "source_version_id", "created_by"],
        "literature_evidence_review_events": [
            "literature_evidence_id,reviewed_at,id",
            "reviewed_by",
        ],
        "literature_support_snapshots": ["project_id", "previous_snapshot_id", "created_by"],
        "literature_evidence_relations": ["literature_evidence_id", "created_by"],
        "literature_evidence_command_receipts": [
            "project_id",
            "actor_id",
            "result_artifact_version_id",
            "result_evidence_id",
            "result_review_event_id",
            "result_snapshot_id",
        ],
    }.items():
        for number, column in enumerate(columns):
            op.execute(f"CREATE INDEX ix_m3_{table}_{number} ON {table}({column})")
    for column in ("claim_version_id", "research_question_version_id", "hypothesis_version_id"):
        op.execute(
            f"CREATE UNIQUE INDEX uq_m3_{column}_number ON literature_support_snapshots({column},snapshot_number) WHERE {column} IS NOT NULL"
        )


def downgrade():
    tables = (
        "literature_evidence_command_receipts",
        "literature_evidence_relations",
        "literature_support_snapshots",
        "literature_evidence_review_events",
        "literature_evidence",
    )
    for table in tables:
        op.execute(
            f"DO $$ BEGIN IF EXISTS(SELECT 1 FROM {table}) THEN RAISE EXCEPTION 'M3 downgrade preserves nonempty scientific history'; END IF; END $$"
        )
    for table in tables:
        op.execute(f"DROP TABLE {table}")
    op.execute(
        "DROP FUNCTION m3_support_guard(); DROP FUNCTION m3_review_guard(); DROP FUNCTION m3_evidence_guard()"
    )
