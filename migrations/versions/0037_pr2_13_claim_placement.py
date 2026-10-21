"""PR2-13 exact ClaimVersion or ScientificConclusionVersion placement."""

from alembic import op

revision = "0037_pr2_13_claim_placement"
down_revision = "0036_pr2_13_citation_placement"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE manuscript_claim_placements (
      id UUID PRIMARY KEY,
      manuscript_version_id UUID NOT NULL REFERENCES manuscript_versions(id) ON DELETE RESTRICT,
      claim_version_id UUID REFERENCES claim_versions(id) ON DELETE RESTRICT,
      scientific_conclusion_version_id UUID
        REFERENCES scientific_conclusion_versions(id) ON DELETE RESTRICT,
      section_id TEXT NOT NULL CHECK (length(btrim(section_id)) > 0
                                      AND char_length(section_id) <= 2000),
      locator JSONB NOT NULL CHECK (
        jsonb_typeof(locator)='object' AND locator - 'kind' - 'value' = '{}'::jsonb
        AND locator ? 'kind' AND locator ? 'value'
        AND locator->>'kind' IN ('PARAGRAPH','SPAN','CAPTION','ANCHOR')
        AND jsonb_typeof(locator->'value')='string'
        AND length(btrim(locator->>'value')) > 0
        AND char_length(locator->>'value') <= 2000),
      rhetorical_strength VARCHAR(16) NOT NULL CHECK (rhetorical_strength IN
        ('DESCRIPTIVE','SUGGESTIVE','SUPPORTED','STRONG')),
      ordinal INT NOT NULL CHECK (ordinal >= 0),
      created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
      created_at TIMESTAMPTZ NOT NULL,
      row_version INT NOT NULL CHECK (row_version > 0),
      CONSTRAINT ck_pr213_claim_target_xor CHECK (
        (claim_version_id IS NOT NULL) <> (scientific_conclusion_version_id IS NOT NULL)),
      UNIQUE (manuscript_version_id,section_id,ordinal)
    );
    CREATE INDEX ix_pr213_claim_target ON manuscript_claim_placements(claim_version_id);
    CREATE INDEX ix_pr213_conclusion_target
      ON manuscript_claim_placements(scientific_conclusion_version_id);
    CREATE INDEX ix_pr213_claim_actor ON manuscript_claim_placements(created_by);
    CREATE FUNCTION pr213_claim_placement_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE manuscript_project UUID;
    BEGIN
      IF TG_OP='UPDATE' AND OLD.manuscript_version_id IS DISTINCT FROM
          NEW.manuscript_version_id THEN
        RAISE EXCEPTION 'claim placement manuscript is immutable' USING ERRCODE='P17D3';
      END IF;
      SELECT p.project_id INTO manuscript_project
        FROM manuscript_versions m JOIN publications p ON p.id=m.publication_id
        WHERE m.id=CASE WHEN TG_OP='DELETE' THEN OLD.manuscript_version_id
                        ELSE NEW.manuscript_version_id END
          AND m.status='DRAFT' AND m.frozen_at IS NULL
        FOR SHARE OF m,p;
      IF manuscript_project IS NULL THEN
        RAISE EXCEPTION 'claim placement requires draft manuscript' USING ERRCODE='P17D3';
      END IF;
      IF TG_OP='DELETE' THEN RETURN OLD; END IF;
      IF NEW.claim_version_id IS NOT NULL THEN
        PERFORM 1 FROM claim_versions v JOIN claims c ON c.id=v.claim_id
          WHERE v.id=NEW.claim_version_id AND c.project_id=manuscript_project
            AND v.status IN ('FROZEN','SUPERSEDED') AND v.frozen_at IS NOT NULL
            AND v.content_hash ~ '^[0-9a-f]{64}$'
          FOR SHARE OF v,c;
      ELSE
        PERFORM 1 FROM scientific_conclusion_versions v
          JOIN scientific_conclusions c ON c.id=v.scientific_conclusion_id
          WHERE v.id=NEW.scientific_conclusion_version_id
            AND c.project_id=manuscript_project
            AND v.status IN ('FROZEN','SUPERSEDED') AND v.frozen_at IS NOT NULL
            AND v.content_hash ~ '^[0-9a-f]{64}$'
            AND v.support_set_hash ~ '^[0-9a-f]{64}$'
          FOR SHARE OF v,c;
      END IF;
      IF NOT FOUND THEN
        RAISE EXCEPTION 'exact frozen project claim or conclusion required' USING ERRCODE='P17D3';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER pr213_claim_placement_guard BEFORE INSERT OR UPDATE OR DELETE
      ON manuscript_claim_placements FOR EACH ROW EXECUTE FUNCTION pr213_claim_placement_guard();
    """)


def downgrade() -> None:
    op.execute("""
    LOCK TABLE manuscript_claim_placements IN ACCESS EXCLUSIVE MODE;
    DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM manuscript_claim_placements) THEN
        RAISE EXCEPTION 'claim placement history cannot be discarded' USING ERRCODE='P17D4';
      END IF;
    END $$;
    DROP TRIGGER pr213_claim_placement_guard ON manuscript_claim_placements;
    DROP FUNCTION pr213_claim_placement_guard();
    DROP TABLE manuscript_claim_placements;
    """)
