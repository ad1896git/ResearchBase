"""R2 typed ScientificConclusion versions and sealed scientific inputs."""

# ruff: noqa: E501

from alembic import op

revision = "0033_pr2_11_r2_scientific_conclusion"
down_revision = "0032_pr2_10_discussion"
branch_labels = None
depends_on = None

TABLES = (
    "scientific_conclusion_command_receipts",
    "scientific_conclusion_literature_inputs",
    "scientific_conclusion_claim_inputs",
    "scientific_conclusion_versions",
    "scientific_conclusions",
)


def upgrade() -> None:
    op.execute("""
    -- The composite FK below binds a snapshot to the *same* exact ClaimVersion.
    -- PostgreSQL requires a non-partial unique key on both referenced columns.
    ALTER TABLE literature_support_snapshots
      ADD CONSTRAINT uq_pr211_snapshot_id_claim UNIQUE (id,claim_version_id);

    CREATE TABLE scientific_conclusions (
      id UUID PRIMARY KEY,
      project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
      current_version_id UUID,
      created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
      created_at TIMESTAMPTZ NOT NULL,
      row_version INTEGER NOT NULL CHECK (row_version>0),
      UNIQUE (project_id,id)
    );
    CREATE TABLE scientific_conclusion_versions (
      id UUID PRIMARY KEY,
      scientific_conclusion_id UUID NOT NULL
        REFERENCES scientific_conclusions(id) ON DELETE RESTRICT,
      version_number INTEGER NOT NULL CHECK (version_number>0),
      status VARCHAR(16) NOT NULL
        CHECK (status IN ('DRAFT','FROZEN','SUPERSEDED','ABANDONED')),
      statement TEXT NOT NULL CHECK (length(btrim(statement)) BETWEEN 1 AND 2000),
      scope JSONB NOT NULL CHECK (
        jsonb_typeof(scope)='object'
        AND scope ?& ARRAY['population','conditions','time_window','applicability']
        AND (scope - ARRAY['population','conditions','time_window','applicability'])='{}'::jsonb
        AND (jsonb_typeof(scope->'population') IN ('string','null'))
        AND (jsonb_typeof(scope->'conditions') IN ('string','null'))
        AND (jsonb_typeof(scope->'time_window') IN ('string','null'))
        AND (jsonb_typeof(scope->'applicability') IN ('string','null'))),
      confidence VARCHAR(16) NOT NULL
        CHECK (confidence IN ('STRONG','MODERATE','WEAK','INCONCLUSIVE','MIXED')),
      limitation_summary TEXT CHECK (length(btrim(limitation_summary)) BETWEEN 1 AND 4096),
      support_set_hash CHAR(64) CHECK (support_set_hash ~ '^[0-9a-f]{64}$'),
      content_hash CHAR(64) CHECK (content_hash ~ '^[0-9a-f]{64}$'),
      hash_scheme VARCHAR(32) NOT NULL CHECK (hash_scheme='sha256-cjson-v1'),
      created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
      created_at TIMESTAMPTZ NOT NULL,
      frozen_at TIMESTAMPTZ,
      row_version INTEGER NOT NULL CHECK (row_version>0),
      CHECK ((status IN ('DRAFT','ABANDONED') AND support_set_hash IS NULL
               AND content_hash IS NULL AND frozen_at IS NULL)
          OR (status IN ('FROZEN','SUPERSEDED') AND support_set_hash IS NOT NULL
               AND content_hash IS NOT NULL AND frozen_at IS NOT NULL)),
      UNIQUE (scientific_conclusion_id,version_number),
      UNIQUE (scientific_conclusion_id,id)
    );
    ALTER TABLE scientific_conclusions
      ADD CONSTRAINT fk_pr211_current_same_parent
      FOREIGN KEY (id,current_version_id)
      REFERENCES scientific_conclusion_versions(scientific_conclusion_id,id)
      ON DELETE RESTRICT;

    CREATE TABLE scientific_conclusion_claim_inputs (
      conclusion_version_id UUID NOT NULL
        REFERENCES scientific_conclusion_versions(id) ON DELETE RESTRICT,
      claim_version_id UUID NOT NULL REFERENCES claim_versions(id) ON DELETE RESTRICT,
      literature_support_snapshot_id UUID,
      relation_type VARCHAR(16) NOT NULL
        CHECK (relation_type IN ('SUPPORTS','CONTRADICTS','QUALIFIES')),
      ordinal INTEGER NOT NULL CHECK (ordinal>=0),
      FOREIGN KEY (literature_support_snapshot_id,claim_version_id)
        REFERENCES literature_support_snapshots(id,claim_version_id) ON DELETE RESTRICT,
      PRIMARY KEY (conclusion_version_id,claim_version_id,relation_type),
      UNIQUE (conclusion_version_id,ordinal)
    );
    CREATE TABLE scientific_conclusion_literature_inputs (
      conclusion_version_id UUID NOT NULL
        REFERENCES scientific_conclusion_versions(id) ON DELETE RESTRICT,
      literature_evidence_id UUID NOT NULL
        REFERENCES literature_evidence(id) ON DELETE RESTRICT,
      relation_type VARCHAR(16) NOT NULL
        CHECK (relation_type IN ('SUPPORTS','CONTRADICTS','QUALIFIES')),
      ordinal INTEGER NOT NULL CHECK (ordinal>=0),
      PRIMARY KEY (conclusion_version_id,literature_evidence_id,relation_type),
      UNIQUE (conclusion_version_id,ordinal)
    );
    CREATE TABLE scientific_conclusion_command_receipts (
      id UUID PRIMARY KEY,
      deployment_id TEXT NOT NULL,
      project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
      actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
      command_name VARCHAR(24) NOT NULL
        CHECK (command_name IN
          ('CREATE_CONCLUSION','FREEZE_CONCLUSION','REVISE_CONCLUSION','REPLACE_INPUTS')),
      request_id UUID NOT NULL,
      input_hash CHAR(64) NOT NULL CHECK (input_hash ~ '^[0-9a-f]{64}$'),
      result_conclusion_id UUID NOT NULL,
      result_version_id UUID NOT NULL,
      completed_at TIMESTAMPTZ NOT NULL,
      FOREIGN KEY (project_id,result_conclusion_id)
        REFERENCES scientific_conclusions(project_id,id) ON DELETE RESTRICT,
      FOREIGN KEY (result_conclusion_id,result_version_id)
        REFERENCES scientific_conclusion_versions(scientific_conclusion_id,id)
        ON DELETE RESTRICT,
      UNIQUE (deployment_id,project_id,actor_id,command_name,request_id)
    );
    CREATE INDEX ix_pr211_conclusion_project_created
      ON scientific_conclusions(project_id,created_at,id);
    CREATE INDEX ix_pr211_version_parent_status
      ON scientific_conclusion_versions(scientific_conclusion_id,status,version_number);
    CREATE INDEX ix_pr211_claim_ref
      ON scientific_conclusion_claim_inputs(claim_version_id);
    CREATE INDEX ix_pr211_literature_ref
      ON scientific_conclusion_literature_inputs(literature_evidence_id);
    """)
    op.execute("""
    CREATE FUNCTION pr211_identity_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP='DELETE' THEN
        RAISE EXCEPTION 'scientific conclusion identity immutable' USING ERRCODE='P17D2';
      END IF;
      IF TG_OP='INSERT' THEN
        IF NEW.current_version_id IS NOT NULL OR NEW.row_version<>1 THEN
          RAISE EXCEPTION 'scientific conclusion must start without a current version'
            USING ERRCODE='P17D2';
        END IF;
        RETURN NEW;
      END IF;
      IF NEW.id IS DISTINCT FROM OLD.id OR NEW.project_id IS DISTINCT FROM OLD.project_id
         OR NEW.created_by IS DISTINCT FROM OLD.created_by
         OR NEW.created_at IS DISTINCT FROM OLD.created_at
         OR NEW.row_version<>OLD.row_version+1
         OR NEW.current_version_id IS NOT DISTINCT FROM OLD.current_version_id THEN
        RAISE EXCEPTION 'scientific conclusion identity or current pointer invalid'
          USING ERRCODE='P17D2';
      END IF;
      IF NEW.current_version_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM scientific_conclusion_versions v
         WHERE v.id=NEW.current_version_id AND v.scientific_conclusion_id=NEW.id
           AND v.status='FROZEN') THEN
        RAISE EXCEPTION 'current conclusion version must be frozen and same-parent'
          USING ERRCODE='P17D3';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER pr211_identity_guard BEFORE INSERT OR UPDATE OR DELETE
      ON scientific_conclusions FOR EACH ROW EXECUTE FUNCTION pr211_identity_guard();

    CREATE FUNCTION pr211_version_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE claim_count BIGINT; literature_count BIGINT;
    BEGIN
      IF TG_OP='DELETE' THEN
        RAISE EXCEPTION 'scientific conclusion version history immutable' USING ERRCODE='P17D2';
      END IF;
      IF TG_OP='INSERT' THEN
        IF NEW.status<>'DRAFT' OR NEW.row_version<>1 THEN
          RAISE EXCEPTION 'scientific conclusion version must start draft'
            USING ERRCODE='P17D2';
        END IF;
        RETURN NEW;
      END IF;
      IF OLD.status IN ('SUPERSEDED','ABANDONED')
         OR NEW.id IS DISTINCT FROM OLD.id
         OR NEW.scientific_conclusion_id IS DISTINCT FROM OLD.scientific_conclusion_id
         OR NEW.version_number IS DISTINCT FROM OLD.version_number
         OR NEW.created_by IS DISTINCT FROM OLD.created_by
         OR NEW.created_at IS DISTINCT FROM OLD.created_at
         OR NEW.hash_scheme IS DISTINCT FROM OLD.hash_scheme
         OR NEW.row_version<>OLD.row_version+1 THEN
        RAISE EXCEPTION 'scientific conclusion version history immutable'
          USING ERRCODE='P17D2';
      END IF;
      IF OLD.status='FROZEN' THEN
        IF NEW.status<>'SUPERSEDED'
           OR NEW.statement IS DISTINCT FROM OLD.statement
           OR NEW.scope IS DISTINCT FROM OLD.scope
           OR NEW.confidence IS DISTINCT FROM OLD.confidence
           OR NEW.limitation_summary IS DISTINCT FROM OLD.limitation_summary
           OR NEW.support_set_hash IS DISTINCT FROM OLD.support_set_hash
           OR NEW.content_hash IS DISTINCT FROM OLD.content_hash
           OR NEW.frozen_at IS DISTINCT FROM OLD.frozen_at THEN
          RAISE EXCEPTION 'frozen scientific conclusion material immutable'
            USING ERRCODE='P17D2';
        END IF;
        RETURN NEW;
      END IF;
      IF OLD.status<>'DRAFT'
         OR NEW.status NOT IN ('DRAFT','FROZEN','ABANDONED') THEN
        RAISE EXCEPTION 'scientific conclusion lifecycle invalid' USING ERRCODE='P17D2';
      END IF;
      IF NEW.status='FROZEN' THEN
        SELECT count(*) INTO claim_count FROM scientific_conclusion_claim_inputs
          WHERE conclusion_version_id=OLD.id;
        SELECT count(*) INTO literature_count FROM scientific_conclusion_literature_inputs
          WHERE conclusion_version_id=OLD.id;
        IF claim_count+literature_count=0 THEN
          RAISE EXCEPTION 'scientific conclusion requires at least one input'
            USING ERRCODE='P17D3';
        END IF;
        IF EXISTS (
          SELECT 1 FROM scientific_conclusion_claim_inputs i
          JOIN literature_support_snapshots s ON s.id=i.literature_support_snapshot_id
          JOIN scientific_conclusions c ON c.id=OLD.scientific_conclusion_id
          WHERE i.conclusion_version_id=OLD.id
            AND (s.claim_version_id IS DISTINCT FROM i.claim_version_id
                 OR s.project_id IS DISTINCT FROM c.project_id)) THEN
          RAISE EXCEPTION 'bound snapshot does not match claim and project'
            USING ERRCODE='P17D3';
        END IF;
        IF EXISTS (
          SELECT 1 FROM scientific_conclusion_claim_inputs i
          LEFT JOIN claim_versions v ON v.id=i.claim_version_id
          LEFT JOIN claims c ON c.id=v.claim_id
          JOIN scientific_conclusions parent ON parent.id=OLD.scientific_conclusion_id
          WHERE i.conclusion_version_id=OLD.id
            AND (v.id IS NULL OR v.status NOT IN ('FROZEN','SUPERSEDED')
                 OR c.project_id IS DISTINCT FROM parent.project_id)) THEN
          RAISE EXCEPTION 'conclusion claim input is not a frozen same-project version'
            USING ERRCODE='P17D3';
        END IF;
        IF EXISTS (
          SELECT 1 FROM scientific_conclusion_literature_inputs i
          JOIN literature_evidence e ON e.id=i.literature_evidence_id
          JOIN source_versions sv ON sv.id=e.source_version_id
          JOIN literature_sources src ON src.id=sv.literature_source_id
          JOIN scientific_conclusions parent ON parent.id=OLD.scientific_conclusion_id
          WHERE i.conclusion_version_id=OLD.id
            AND (e.project_id IS DISTINCT FROM parent.project_id
                 OR sv.status NOT IN ('FROZEN','SUPERSEDED')
                 OR src.lifecycle_status<>'ACTIVE'
                 OR (i.relation_type='SUPPORTS' AND (
                   e.review_status<>'VERIFIED' OR NOT EXISTS (
                   SELECT 1 FROM literature_evidence_review_events review
                   JOIN actors reviewer ON reviewer.id=review.reviewed_by
                   WHERE review.literature_evidence_id=e.id
                     AND review.new_status='VERIFIED'
                     AND reviewer.actor_type='HUMAN'
                     AND review.reviewed_by<>e.created_by
                     AND review.reviewed_by<>OLD.created_by
                     AND review.reviewed_at=(
                       SELECT max(latest.reviewed_at)
                       FROM literature_evidence_review_events latest
                       WHERE latest.literature_evidence_id=e.id)))))) THEN
          RAISE EXCEPTION 'conclusion literature input closure invalid'
            USING ERRCODE='P17D3';
        END IF;
        -- R2 admits a semantic exception only when contradictory/qualifying
        -- overlap is acknowledged in prose. No machine grammar is specified;
        -- the Application rejects every overlap rather than guessing.
        IF EXISTS (
          SELECT 1 FROM scientific_conclusion_literature_inputs direct_input
          JOIN scientific_conclusion_claim_inputs claim_input
            ON claim_input.conclusion_version_id=direct_input.conclusion_version_id
          JOIN literature_evidence_relations relation
            ON relation.literature_support_snapshot_id=
               claim_input.literature_support_snapshot_id
           AND relation.literature_evidence_id=direct_input.literature_evidence_id
          WHERE direct_input.conclusion_version_id=OLD.id) THEN
          RAISE EXCEPTION 'duplicate direct and snapshot literature input'
            USING ERRCODE='P17D3';
        END IF;
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER pr211_version_guard BEFORE INSERT OR UPDATE OR DELETE
      ON scientific_conclusion_versions FOR EACH ROW EXECUTE FUNCTION pr211_version_guard();

    CREATE FUNCTION pr211_input_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE target_version UUID; p UUID; st TEXT; project UUID; valid BOOLEAN;
    BEGIN
      IF TG_OP IN ('UPDATE','DELETE') THEN
        target_version := OLD.conclusion_version_id;
      ELSE
        target_version := NEW.conclusion_version_id;
      END IF;
      SELECT v.status,c.project_id INTO st,project
        FROM scientific_conclusion_versions v
        JOIN scientific_conclusions c ON c.id=v.scientific_conclusion_id
        WHERE v.id=target_version FOR UPDATE OF v;
      IF st IS DISTINCT FROM 'DRAFT' THEN
        RAISE EXCEPTION 'scientific conclusion inputs sealed' USING ERRCODE='P17D1';
      END IF;
      IF TG_OP='DELETE' THEN RETURN OLD; END IF;
      IF TG_OP='UPDATE' AND NEW.conclusion_version_id IS DISTINCT FROM OLD.conclusion_version_id THEN
        RAISE EXCEPTION 'scientific conclusion input parent immutable'
          USING ERRCODE='P17D2';
      END IF;
      IF TG_TABLE_NAME='scientific_conclusion_claim_inputs' THEN
        SELECT EXISTS (
          SELECT 1 FROM claim_versions v JOIN claims c ON c.id=v.claim_id
          WHERE v.id=NEW.claim_version_id AND c.project_id=project
            AND v.status IN ('FROZEN','SUPERSEDED')) INTO valid;
        IF NEW.literature_support_snapshot_id IS NOT NULL THEN
          valid := valid AND EXISTS (
            SELECT 1 FROM literature_support_snapshots s
            WHERE s.id=NEW.literature_support_snapshot_id
              AND s.claim_version_id=NEW.claim_version_id AND s.project_id=project);
        END IF;
      ELSE
        SELECT EXISTS (
          SELECT 1 FROM literature_evidence e
          JOIN source_versions sv ON sv.id=e.source_version_id
          JOIN literature_source_project_links l
            ON l.literature_source_id=sv.literature_source_id
           AND l.project_id=project
          WHERE e.id=NEW.literature_evidence_id AND e.project_id=project
            AND sv.status IN ('FROZEN','SUPERSEDED')) INTO valid;
      END IF;
      IF NOT COALESCE(valid,FALSE) THEN
        RAISE EXCEPTION 'scientific conclusion input reference invalid'
          USING ERRCODE='P17D3';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER pr211_claim_input_guard BEFORE INSERT OR UPDATE OR DELETE
      ON scientific_conclusion_claim_inputs FOR EACH ROW EXECUTE FUNCTION pr211_input_guard();
    CREATE TRIGGER pr211_literature_input_guard BEFORE INSERT OR UPDATE OR DELETE
      ON scientific_conclusion_literature_inputs FOR EACH ROW EXECUTE FUNCTION pr211_input_guard();
    CREATE TRIGGER pr211_receipt_immutable BEFORE UPDATE OR DELETE
      ON scientific_conclusion_command_receipts FOR EACH ROW EXECUTE FUNCTION m2_immutable();
    """)
    op.execute("""
    CREATE FUNCTION pr211_validate_input_cardinality() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE target_version UUID; n BIGINT; first_ordinal INT; last_ordinal INT;
    BEGIN
      IF TG_TABLE_NAME='scientific_conclusion_versions' THEN
        target_version := NEW.id;
      ELSIF TG_OP='DELETE' THEN
        target_version := OLD.conclusion_version_id;
      ELSE
        target_version := NEW.conclusion_version_id;
      END IF;
      IF (SELECT status FROM scientific_conclusion_versions WHERE id=target_version)
         IN ('FROZEN','SUPERSEDED') THEN
        SELECT count(*),min(ordinal),max(ordinal)
          INTO n,first_ordinal,last_ordinal
          FROM scientific_conclusion_claim_inputs
          WHERE conclusion_version_id=target_version;
        IF n>0 AND (first_ordinal<>0 OR last_ordinal<>n-1) THEN
          RAISE EXCEPTION 'claim input ordinals not contiguous'
            USING ERRCODE='P17D3';
        END IF;
        SELECT count(*),min(ordinal),max(ordinal)
          INTO n,first_ordinal,last_ordinal
          FROM scientific_conclusion_literature_inputs
          WHERE conclusion_version_id=target_version;
        IF n>0 AND (first_ordinal<>0 OR last_ordinal<>n-1) THEN
          RAISE EXCEPTION 'literature input ordinals not contiguous'
            USING ERRCODE='P17D3';
        END IF;
      END IF;
      RETURN NULL;
    END $$;
    CREATE CONSTRAINT TRIGGER pr211_version_cardinality
      AFTER INSERT OR UPDATE ON scientific_conclusion_versions
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
      EXECUTE FUNCTION pr211_validate_input_cardinality();
    CREATE CONSTRAINT TRIGGER pr211_claim_cardinality
      AFTER INSERT OR UPDATE OR DELETE ON scientific_conclusion_claim_inputs
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
      EXECUTE FUNCTION pr211_validate_input_cardinality();
    CREATE CONSTRAINT TRIGGER pr211_literature_cardinality
      AFTER INSERT OR UPDATE OR DELETE ON scientific_conclusion_literature_inputs
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
      EXECUTE FUNCTION pr211_validate_input_cardinality();

    CREATE FUNCTION pr211_current_frozen_at_commit() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE parent_id UUID; pointer UUID; state TEXT;
    BEGIN
      IF TG_TABLE_NAME='scientific_conclusions' THEN
        parent_id := NEW.id;
      ELSE
        parent_id := NEW.scientific_conclusion_id;
      END IF;
      SELECT current_version_id INTO pointer FROM scientific_conclusions WHERE id=parent_id;
      IF pointer IS NOT NULL THEN
        SELECT status INTO state FROM scientific_conclusion_versions
          WHERE id=pointer AND scientific_conclusion_id=parent_id;
        IF state IS DISTINCT FROM 'FROZEN' THEN
          RAISE EXCEPTION 'current conclusion pointer must resolve to frozen version'
            USING ERRCODE='P17D3';
        END IF;
      ELSIF EXISTS (SELECT 1 FROM scientific_conclusion_versions
                    WHERE scientific_conclusion_id=parent_id AND status='FROZEN') THEN
        RAISE EXCEPTION 'frozen conclusion requires current pointer'
          USING ERRCODE='P17D3';
      END IF;
      RETURN NULL;
    END $$;
    CREATE CONSTRAINT TRIGGER pr211_current_parent_commit
      AFTER INSERT OR UPDATE ON scientific_conclusions
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
      EXECUTE FUNCTION pr211_current_frozen_at_commit();
    CREATE CONSTRAINT TRIGGER pr211_current_version_commit
      AFTER INSERT OR UPDATE ON scientific_conclusion_versions
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
      EXECUTE FUNCTION pr211_current_frozen_at_commit();
    """)


def downgrade() -> None:
    op.execute("LOCK TABLE " + ",".join(TABLES) + " IN ACCESS EXCLUSIVE MODE")
    for table in TABLES:
        op.execute(
            f"DO $$ BEGIN IF EXISTS(SELECT 1 FROM {table}) THEN "
            "RAISE EXCEPTION 'PR2-11 downgrade preserves scientific history' "
            "USING ERRCODE='P17D5'; END IF; END $$"
        )
    op.execute("ALTER TABLE scientific_conclusions DROP CONSTRAINT fk_pr211_current_same_parent")
    for table in TABLES:
        op.execute(f"DROP TABLE {table}")
    op.execute("""
      DROP FUNCTION pr211_current_frozen_at_commit();
      DROP FUNCTION pr211_validate_input_cardinality();
      DROP FUNCTION pr211_input_guard();
      DROP FUNCTION pr211_version_guard();
      DROP FUNCTION pr211_identity_guard();
      ALTER TABLE literature_support_snapshots
        DROP CONSTRAINT uq_pr211_snapshot_id_claim;
    """)
