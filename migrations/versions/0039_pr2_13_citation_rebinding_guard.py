"""Prevent direct SQL rebinding of a Citation placement to another manuscript."""

from alembic import op

revision = "0039_pr2_13_citation_rebinding_guard"
down_revision = "0038_pr2_13_artifact_placement"
branch_labels = None
depends_on = None


def _guard_sql(*, reject_reparent: bool) -> str:
    reparent_guard = """
      IF TG_OP='UPDATE' AND OLD.manuscript_version_id IS DISTINCT FROM
          NEW.manuscript_version_id THEN
        RAISE EXCEPTION 'citation placement manuscript is immutable' USING ERRCODE='P17D3';
      END IF;
    """ if reject_reparent else ""
    return """
    CREATE OR REPLACE FUNCTION pr213_citation_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE manuscript_project UUID;
    BEGIN
    """ + reparent_guard + """
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
    """


def upgrade() -> None:
    op.execute("LOCK TABLE manuscript_citation_placements IN ACCESS EXCLUSIVE MODE")
    op.execute(_guard_sql(reject_reparent=True))


def downgrade() -> None:
    op.execute("""
    LOCK TABLE manuscript_citation_placements IN ACCESS EXCLUSIVE MODE;
    DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM manuscript_citation_placements) THEN
        RAISE EXCEPTION 'citation rebinding guard cannot be removed with history'
          USING ERRCODE='P17D4';
      END IF;
    END $$;
    """)
    op.execute(_guard_sql(reject_reparent=False))
