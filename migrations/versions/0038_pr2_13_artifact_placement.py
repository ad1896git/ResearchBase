"""PR2-13 exact frozen ArtifactVersion placement."""

from alembic import op

revision = "0038_pr2_13_artifact_placement"
down_revision = "0037_pr2_13_claim_placement"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE manuscript_artifact_placements (
      id UUID PRIMARY KEY,
      manuscript_version_id UUID NOT NULL REFERENCES manuscript_versions(id) ON DELETE RESTRICT,
      artifact_version_id UUID NOT NULL REFERENCES artifact_versions(id) ON DELETE RESTRICT,
      section_id TEXT NOT NULL CHECK (length(btrim(section_id)) > 0
                                      AND char_length(section_id) <= 2000),
      locator JSONB NOT NULL CHECK (
        jsonb_typeof(locator)='object' AND locator - 'kind' - 'value' = '{}'::jsonb
        AND locator ? 'kind' AND locator ? 'value'
        AND locator->>'kind' IN ('PARAGRAPH','SPAN','CAPTION','ANCHOR')
        AND jsonb_typeof(locator->'value')='string'
        AND length(btrim(locator->>'value')) > 0
        AND char_length(locator->>'value') <= 2000),
      artifact_role VARCHAR(16) NOT NULL CHECK (artifact_role IN ('FIGURE','TABLE','OTHER')),
      ordinal INT NOT NULL CHECK (ordinal >= 0),
      created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
      created_at TIMESTAMPTZ NOT NULL,
      row_version INT NOT NULL CHECK (row_version > 0),
      UNIQUE (manuscript_version_id,section_id,ordinal)
    );
    CREATE INDEX ix_pr213_artifact_target ON manuscript_artifact_placements(artifact_version_id);
    CREATE INDEX ix_pr213_artifact_actor ON manuscript_artifact_placements(created_by);
    CREATE FUNCTION pr213_artifact_placement_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE manuscript_project UUID;
    BEGIN
      IF TG_OP='UPDATE' AND OLD.manuscript_version_id IS DISTINCT FROM
          NEW.manuscript_version_id THEN
        RAISE EXCEPTION 'artifact placement manuscript is immutable' USING ERRCODE='P17D3';
      END IF;
      SELECT p.project_id INTO manuscript_project
        FROM manuscript_versions m JOIN publications p ON p.id=m.publication_id
        WHERE m.id=CASE WHEN TG_OP='DELETE' THEN OLD.manuscript_version_id
                        ELSE NEW.manuscript_version_id END
          AND m.status='DRAFT' AND m.frozen_at IS NULL
        FOR SHARE OF m,p;
      IF manuscript_project IS NULL THEN
        RAISE EXCEPTION 'artifact placement requires draft manuscript' USING ERRCODE='P17D3';
      END IF;
      IF TG_OP='DELETE' THEN RETURN OLD; END IF;
      PERFORM 1 FROM artifact_versions v JOIN artifacts a ON a.id=v.artifact_id
        WHERE v.id=NEW.artifact_version_id AND a.project_id=manuscript_project
          AND v.status IN ('FROZEN','SUPERSEDED') AND v.frozen_at IS NOT NULL
          AND v.content_hash ~ '^[0-9a-f]{64}$'
        FOR SHARE OF v,a;
      IF NOT FOUND THEN
        RAISE EXCEPTION 'exact frozen project artifact required' USING ERRCODE='P17D3';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER pr213_artifact_placement_guard BEFORE INSERT OR UPDATE OR DELETE
      ON manuscript_artifact_placements FOR EACH ROW
      EXECUTE FUNCTION pr213_artifact_placement_guard();
    """)


def downgrade() -> None:
    op.execute("""
    LOCK TABLE manuscript_artifact_placements IN ACCESS EXCLUSIVE MODE;
    DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM manuscript_artifact_placements) THEN
        RAISE EXCEPTION 'artifact placement history cannot be discarded' USING ERRCODE='P17D4';
      END IF;
    END $$;
    DROP TRIGGER pr213_artifact_placement_guard ON manuscript_artifact_placements;
    DROP FUNCTION pr213_artifact_placement_guard();
    DROP TABLE manuscript_artifact_placements;
    """)
