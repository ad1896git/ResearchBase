"""PR2-13 citation-only placement on a draft manuscript version."""

from alembic import op

revision = "0036_pr2_13_citation_placement"
down_revision = "0035_pr2_12_publication_draft"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE manuscript_citation_placements (
      id UUID PRIMARY KEY,
      manuscript_version_id UUID NOT NULL REFERENCES manuscript_versions(id) ON DELETE RESTRICT,
      source_version_id UUID NOT NULL REFERENCES source_versions(id) ON DELETE RESTRICT,
      section_id TEXT NOT NULL CHECK (length(btrim(section_id)) > 0
                                      AND char_length(section_id) <= 2000),
      locator JSONB NOT NULL CHECK (
        jsonb_typeof(locator)='object' AND locator - 'kind' - 'value' = '{}'::jsonb
        AND locator ? 'kind' AND locator ? 'value'
        AND locator->>'kind' IN ('PARAGRAPH','SPAN','CAPTION','ANCHOR')
        AND jsonb_typeof(locator->'value')='string'
        AND length(btrim(locator->>'value')) > 0
        AND char_length(locator->>'value') <= 2000),
      citation_purpose VARCHAR(16) NOT NULL CHECK (citation_purpose IN
        ('BACKGROUND','METHOD','COMPARISON','EVIDENCE','PRIOR_ART','DATASET','OTHER')),
      ordinal INT NOT NULL CHECK (ordinal >= 0),
      created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
      created_at TIMESTAMPTZ NOT NULL,
      row_version INT NOT NULL CHECK (row_version > 0),
      UNIQUE (manuscript_version_id,section_id,ordinal)
    );
    CREATE INDEX ix_pr213_citation_source ON manuscript_citation_placements(source_version_id);
    CREATE INDEX ix_pr213_citation_actor ON manuscript_citation_placements(created_by);
    CREATE FUNCTION pr213_citation_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE manuscript_project UUID;
    BEGIN
      SELECT p.project_id INTO manuscript_project
        FROM manuscript_versions m JOIN publications p ON p.id=m.publication_id
        WHERE m.id=CASE WHEN TG_OP='DELETE' THEN OLD.manuscript_version_id
                        ELSE NEW.manuscript_version_id END
          AND m.status='DRAFT' AND m.frozen_at IS NULL
        FOR SHARE OF m,p;
      IF manuscript_project IS NULL THEN
        RAISE EXCEPTION 'citation placement requires draft manuscript' USING ERRCODE='P17D3';
      END IF;
      IF TG_OP='DELETE' THEN RETURN OLD; END IF;
      PERFORM 1 FROM source_versions v
        JOIN literature_source_project_links l ON l.literature_source_id=v.literature_source_id
        WHERE v.id=NEW.source_version_id AND l.project_id=manuscript_project
          AND v.status IN ('FROZEN','SUPERSEDED') AND v.frozen_at IS NOT NULL
          AND v.content_hash ~ '^[0-9a-f]{64}$'
        FOR SHARE OF v,l;
      IF NOT FOUND THEN
        RAISE EXCEPTION 'exact frozen project source required' USING ERRCODE='P17D3';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER pr213_citation_guard BEFORE INSERT OR UPDATE OR DELETE
      ON manuscript_citation_placements FOR EACH ROW EXECUTE FUNCTION pr213_citation_guard();
    """)


def downgrade() -> None:
    op.execute("""
    LOCK TABLE manuscript_citation_placements IN ACCESS EXCLUSIVE MODE;
    DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM manuscript_citation_placements) THEN
        RAISE EXCEPTION 'citation placement history cannot be discarded' USING ERRCODE='P17D4';
      END IF;
    END $$;
    DROP TRIGGER pr213_citation_guard ON manuscript_citation_placements;
    DROP FUNCTION pr213_citation_guard();
    DROP TABLE manuscript_citation_placements;
    """)
