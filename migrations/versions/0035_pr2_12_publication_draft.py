"""PR2-12 project publication identity and nonformal manuscript draft."""

# ruff: noqa: E501

from alembic import op

revision = "0035_pr2_12_publication_draft"
down_revision = "0034_pr2_10_exact_transcript_binding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE publications (
      id UUID PRIMARY KEY,
      project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
      publication_type VARCHAR(32) NOT NULL CHECK (publication_type IN
        ('PAPER','PREPRINT','REPORT','THESIS','TECHNICAL_REPORT','OTHER')),
      title TEXT NOT NULL CHECK (length(btrim(title)) BETWEEN 1 AND 2000),
      lifecycle_status VARCHAR(24) NOT NULL DEFAULT 'DRAFTING'
        CHECK (lifecycle_status='DRAFTING'),
      current_manuscript_version_id UUID,
      created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
      created_at TIMESTAMPTZ NOT NULL,
      row_version INT NOT NULL CHECK (row_version>0),
      UNIQUE (project_id,id)
    );
    CREATE TABLE manuscript_versions (
      id UUID PRIMARY KEY,
      publication_id UUID NOT NULL REFERENCES publications(id) ON DELETE RESTRICT,
      version_number INT NOT NULL CHECK (version_number>0),
      status VARCHAR(16) NOT NULL CHECK (status='DRAFT'),
      document_artifact_version_id UUID NOT NULL
        REFERENCES artifact_versions(id) ON DELETE RESTRICT,
      title TEXT NOT NULL CHECK (length(btrim(title)) BETWEEN 1 AND 2000),
      abstract TEXT,
      semantic_change_class VARCHAR(24) NOT NULL CHECK (semantic_change_class IN
        ('INITIAL','EDITORIAL','SCIENTIFIC_MINOR','SCIENTIFIC_MATERIAL')),
      placement_set_hash CHAR(64),
      content_hash CHAR(64),
      -- Phase 2 field contract shared physical rule for every content_hash row.
      hash_scheme VARCHAR(32) NOT NULL CHECK (hash_scheme='sha256-cjson-v1'),
      created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
      created_at TIMESTAMPTZ NOT NULL,
      frozen_at TIMESTAMPTZ,
      row_version INT NOT NULL CHECK (row_version>0),
      CONSTRAINT ck_pr212_unfrozen_draft CHECK
        (placement_set_hash IS NULL AND content_hash IS NULL AND frozen_at IS NULL),
      UNIQUE (publication_id,version_number),
      UNIQUE (publication_id,id)
    );
    ALTER TABLE publications ADD CONSTRAINT fk_pr212_current_same_parent
      FOREIGN KEY (id,current_manuscript_version_id)
      REFERENCES manuscript_versions(publication_id,id) ON DELETE RESTRICT;
    CREATE TABLE publication_lifecycle_events (
      id UUID PRIMARY KEY,
      publication_id UUID NOT NULL REFERENCES publications(id) ON DELETE RESTRICT,
      prior_status VARCHAR(24),
      new_status VARCHAR(24) NOT NULL CHECK (new_status='DRAFTING'),
      actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
      occurred_at TIMESTAMPTZ NOT NULL,
      basis_decision_id UUID,
      basis_grant_consumption_id UUID,
      CHECK (prior_status IS NULL AND basis_decision_id IS NULL
             AND basis_grant_consumption_id IS NULL),
      UNIQUE (publication_id)
    );
    CREATE INDEX ix_pr212_publications_project ON publications(project_id,created_at,id);
    CREATE INDEX ix_pr212_manuscript_document
      ON manuscript_versions(document_artifact_version_id);
    """)
    op.execute("""
    CREATE FUNCTION pr212_publication_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP='DELETE' THEN
        RAISE EXCEPTION 'publication history retained' USING ERRCODE='P17D1';
      END IF;
      IF TG_OP='INSERT' THEN
        IF NEW.lifecycle_status<>'DRAFTING' OR NEW.row_version<>1
           OR NEW.current_manuscript_version_id IS NOT NULL THEN
          RAISE EXCEPTION 'publication starts drafting' USING ERRCODE='P17D2';
        END IF;
        RETURN NEW;
      END IF;
      RAISE EXCEPTION 'publication transition outside draft slice' USING ERRCODE='P17D2';
    END $$;
    CREATE TRIGGER pr212_publication_guard BEFORE INSERT OR UPDATE OR DELETE ON publications
      FOR EACH ROW EXECUTE FUNCTION pr212_publication_guard();

    CREATE FUNCTION pr212_draft_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP='DELETE' THEN
        RAISE EXCEPTION 'manuscript history retained' USING ERRCODE='P17D1';
      END IF;
      IF TG_OP='UPDATE' THEN
        RAISE EXCEPTION 'draft revisions require new version' USING ERRCODE='P17D2';
      END IF;
      IF NEW.status<>'DRAFT' OR NEW.row_version<>1
         OR NEW.placement_set_hash IS NOT NULL OR NEW.content_hash IS NOT NULL
         OR NEW.frozen_at IS NOT NULL THEN
        RAISE EXCEPTION 'draft cannot claim frozen science' USING ERRCODE='P17D2';
      END IF;
      PERFORM 1 FROM publications p
        JOIN artifact_versions v ON v.id=NEW.document_artifact_version_id
        JOIN artifacts a ON a.id=v.artifact_id
        WHERE p.id=NEW.publication_id AND a.project_id=p.project_id
          AND a.artifact_type='manuscript' AND v.status='FROZEN'
          AND v.frozen_at IS NOT NULL AND v.content_hash ~ '^[0-9a-f]{64}$'
        FOR SHARE OF p,v,a;
      IF NOT FOUND THEN
        RAISE EXCEPTION 'exact frozen manuscript document required' USING ERRCODE='P17D3';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER pr212_draft_guard BEFORE INSERT OR UPDATE OR DELETE ON manuscript_versions
      FOR EACH ROW EXECUTE FUNCTION pr212_draft_guard();

    CREATE FUNCTION pr212_document_parent_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF EXISTS (SELECT 1 FROM manuscript_versions m JOIN publications p ON p.id=m.publication_id
        WHERE m.document_artifact_version_id IN
          (SELECT id FROM artifact_versions WHERE artifact_id=NEW.id)
          AND (NEW.project_id IS DISTINCT FROM p.project_id
               OR NEW.artifact_type<>'manuscript')) THEN
        RAISE EXCEPTION 'bound manuscript document parent immutable' USING ERRCODE='P17D3';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER pr212_document_parent_guard BEFORE UPDATE ON artifacts
      FOR EACH ROW EXECUTE FUNCTION pr212_document_parent_guard();
    CREATE TRIGGER pr212_events_immutable BEFORE UPDATE OR DELETE ON publication_lifecycle_events
      FOR EACH ROW EXECUTE FUNCTION m2_immutable();
    """)


def downgrade() -> None:
    op.execute("""
    LOCK TABLE publications,manuscript_versions,publication_lifecycle_events
      IN ACCESS EXCLUSIVE MODE;
    DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM publications) OR EXISTS (SELECT 1 FROM manuscript_versions)
         OR EXISTS (SELECT 1 FROM publication_lifecycle_events) THEN
        RAISE EXCEPTION 'PR2-12 draft history cannot be discarded' USING ERRCODE='P17D4';
      END IF;
    END $$;
    DROP TRIGGER pr212_events_immutable ON publication_lifecycle_events;
    DROP TRIGGER pr212_document_parent_guard ON artifacts;
    DROP FUNCTION pr212_document_parent_guard();
    DROP TRIGGER pr212_draft_guard ON manuscript_versions;
    DROP FUNCTION pr212_draft_guard();
    DROP TRIGGER pr212_publication_guard ON publications;
    DROP FUNCTION pr212_publication_guard();
    ALTER TABLE publications DROP CONSTRAINT fk_pr212_current_same_parent;
    DROP TABLE publication_lifecycle_events;
    DROP TABLE manuscript_versions;
    DROP TABLE publications;
    """)
