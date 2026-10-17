"""B04 initial manuscript seal; retain scientific history and draft placement checks."""

# ruff: noqa: E501
from alembic import op

revision = "0048_b04_manuscript_freeze"
down_revision = "0047_pr2_18_novelty_prior_art"
branch_labels = None
depends_on = None

LEGACY_GUARDS = (
    """CREATE OR REPLACE FUNCTION pr212_publication_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
    END $$;""",
    """CREATE OR REPLACE FUNCTION pr212_draft_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
    END $$;""",
    """CREATE OR REPLACE FUNCTION pr213_claim_placement_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
    END $$;""",
    """CREATE OR REPLACE FUNCTION pr213_artifact_placement_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
    END $$;""",
    """CREATE OR REPLACE FUNCTION pr213_citation_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE manuscript_project UUID;
    BEGIN

      IF TG_OP='UPDATE' AND OLD.manuscript_version_id IS DISTINCT FROM
          NEW.manuscript_version_id THEN
        RAISE EXCEPTION 'citation placement manuscript is immutable' USING ERRCODE='P17D3';
      END IF;

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
    END $$;""",
)

SEAL_GUARDS = (
    """CREATE OR REPLACE FUNCTION pr212_publication_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
      IF OLD.lifecycle_status='DRAFTING' AND NEW.lifecycle_status='DRAFTING'
        AND OLD.current_manuscript_version_id IS NULL AND NEW.current_manuscript_version_id IS NOT NULL
        AND NEW.row_version=OLD.row_version+1
        AND (to_jsonb(NEW)-ARRAY['current_manuscript_version_id','row_version'])
          IS NOT DISTINCT FROM (to_jsonb(OLD)-ARRAY['current_manuscript_version_id','row_version'])
        AND EXISTS (SELECT 1 FROM manuscript_versions m WHERE m.id=NEW.current_manuscript_version_id
          AND m.publication_id=NEW.id AND m.status='FROZEN' AND m.content_hash IS NOT NULL
          AND m.placement_set_hash IS NOT NULL AND m.frozen_at IS NOT NULL) THEN RETURN NEW; END IF;
      RAISE EXCEPTION 'invalid manuscript pointer transition' USING ERRCODE='P04M2';
    END $$;""",
    """CREATE OR REPLACE FUNCTION pr212_draft_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP='DELETE' THEN
        RAISE EXCEPTION 'manuscript history retained' USING ERRCODE='P04M1';
      END IF;
      IF TG_OP='UPDATE' THEN
        IF OLD.status='FROZEN' THEN RAISE EXCEPTION 'sealed manuscript immutable' USING ERRCODE='P04M1'; END IF;
        IF OLD.status<>'DRAFT' OR NEW.status<>'FROZEN' OR NEW.row_version<>OLD.row_version+1
          OR NEW.content_hash IS NULL OR NEW.placement_set_hash IS NULL OR NEW.frozen_at IS NULL
          OR (to_jsonb(NEW)-ARRAY['status','row_version','content_hash','placement_set_hash','frozen_at'])
            IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['status','row_version','content_hash','placement_set_hash','frozen_at']) THEN
          RAISE EXCEPTION 'invalid manuscript seal transition' USING ERRCODE='P04M2'; END IF;
      ELSIF NEW.status<>'DRAFT' OR NEW.row_version<>1 OR NEW.placement_set_hash IS NOT NULL
        OR NEW.content_hash IS NOT NULL OR NEW.frozen_at IS NOT NULL THEN
        RAISE EXCEPTION 'insert draft only' USING ERRCODE='P04M2';
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
    END $$;""",
    """CREATE OR REPLACE FUNCTION pr213_citation_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE manuscript_project UUID;
    BEGIN
      PERFORM m.id FROM manuscript_versions m WHERE m.id IN
        (CASE WHEN TG_OP<>'INSERT' THEN OLD.manuscript_version_id END,
         CASE WHEN TG_OP<>'DELETE' THEN NEW.manuscript_version_id END)
        ORDER BY m.id FOR UPDATE;
      IF EXISTS (SELECT 1 FROM manuscript_versions m WHERE m.id IN
        (CASE WHEN TG_OP<>'INSERT' THEN OLD.manuscript_version_id END,
         CASE WHEN TG_OP<>'DELETE' THEN NEW.manuscript_version_id END) AND m.status='FROZEN') THEN
        RAISE EXCEPTION 'sealed placements immutable' USING ERRCODE='P04M1'; END IF;


      IF TG_OP='UPDATE' AND OLD.manuscript_version_id IS DISTINCT FROM
          NEW.manuscript_version_id THEN
        RAISE EXCEPTION 'citation placement manuscript is immutable' USING ERRCODE='P17D3';
      END IF;

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
    END $$;""",
    """CREATE OR REPLACE FUNCTION pr213_claim_placement_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE manuscript_project UUID;
    BEGIN
      PERFORM m.id FROM manuscript_versions m WHERE m.id IN
        (CASE WHEN TG_OP<>'INSERT' THEN OLD.manuscript_version_id END,
         CASE WHEN TG_OP<>'DELETE' THEN NEW.manuscript_version_id END)
        ORDER BY m.id FOR UPDATE;
      IF EXISTS (SELECT 1 FROM manuscript_versions m WHERE m.id IN
        (CASE WHEN TG_OP<>'INSERT' THEN OLD.manuscript_version_id END,
         CASE WHEN TG_OP<>'DELETE' THEN NEW.manuscript_version_id END) AND m.status='FROZEN') THEN
        RAISE EXCEPTION 'sealed placements immutable' USING ERRCODE='P04M1'; END IF;

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
    END $$;""",
    """CREATE OR REPLACE FUNCTION pr213_artifact_placement_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE manuscript_project UUID;
    BEGIN
      PERFORM m.id FROM manuscript_versions m WHERE m.id IN
        (CASE WHEN TG_OP<>'INSERT' THEN OLD.manuscript_version_id END,
         CASE WHEN TG_OP<>'DELETE' THEN NEW.manuscript_version_id END)
        ORDER BY m.id FOR UPDATE;
      IF EXISTS (SELECT 1 FROM manuscript_versions m WHERE m.id IN
        (CASE WHEN TG_OP<>'INSERT' THEN OLD.manuscript_version_id END,
         CASE WHEN TG_OP<>'DELETE' THEN NEW.manuscript_version_id END) AND m.status='FROZEN') THEN
        RAISE EXCEPTION 'sealed placements immutable' USING ERRCODE='P04M1'; END IF;

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
    END $$;""",
)


TABLES = (
    "publications",
    "manuscript_versions",
    "manuscript_claim_placements",
    "manuscript_citation_placements",
    "manuscript_artifact_placements",
)


def upgrade() -> None:
    op.execute("LOCK TABLE " + ",".join(TABLES) + " IN ACCESS EXCLUSIVE MODE")
    op.execute("""
    DO $$ DECLARE bad TEXT; definition TEXT; BEGIN
      SELECT pg_get_constraintdef(oid) INTO definition FROM pg_constraint
        WHERE conrelid='manuscript_versions'::regclass AND conname='manuscript_versions_status_check';
      IF definition IS NULL OR definition NOT LIKE '%status%=%DRAFT%' OR definition LIKE '%FROZEN%' THEN
        RAISE EXCEPTION 'unexpected legacy manuscript status check: %', definition; END IF;
      SELECT string_agg(id::text,',') INTO bad FROM manuscript_versions
        WHERE status<>'DRAFT' OR content_hash IS NOT NULL OR placement_set_hash IS NOT NULL OR frozen_at IS NOT NULL;
      IF bad IS NOT NULL THEN RAISE EXCEPTION 'incompatible manuscript IDs: %',bad; END IF;
      SELECT string_agg(id::text,',') INTO bad FROM publications WHERE current_manuscript_version_id IS NOT NULL;
      IF bad IS NOT NULL THEN RAISE EXCEPTION 'incompatible publication IDs: %',bad; END IF;
      SELECT string_agg(m.id::text,',') INTO bad FROM manuscript_versions m
        JOIN publications p ON p.id=m.publication_id
        LEFT JOIN artifact_versions v ON v.id=m.document_artifact_version_id
        LEFT JOIN artifacts a ON a.id=v.artifact_id
        WHERE a.project_id IS DISTINCT FROM p.project_id OR a.artifact_type IS DISTINCT FROM 'manuscript'
          OR v.status IS DISTINCT FROM 'FROZEN' OR v.frozen_at IS NULL OR v.byte_size IS NULL
          OR v.content_hash IS NULL OR v.content_hash !~ '^[0-9a-f]{64}$';
      IF bad IS NOT NULL THEN RAISE EXCEPTION 'incompatible document manuscript IDs: %',bad; END IF;
      SELECT string_agg(x.id::text,',') INTO bad FROM (
        SELECT cp.id FROM manuscript_claim_placements cp JOIN manuscript_versions m ON m.id=cp.manuscript_version_id
          JOIN publications p ON p.id=m.publication_id LEFT JOIN claim_versions v ON v.id=cp.claim_version_id
          LEFT JOIN claims c ON c.id=v.claim_id LEFT JOIN scientific_conclusion_versions s ON s.id=cp.scientific_conclusion_version_id
          LEFT JOIN scientific_conclusions sc ON sc.id=s.scientific_conclusion_id
          WHERE (cp.claim_version_id IS NULL)=(cp.scientific_conclusion_version_id IS NULL)
            OR (cp.claim_version_id IS NOT NULL AND (c.project_id IS DISTINCT FROM p.project_id OR v.status NOT IN ('FROZEN','SUPERSEDED') OR v.frozen_at IS NULL OR v.content_hash IS NULL))
            OR (cp.scientific_conclusion_version_id IS NOT NULL AND (sc.project_id IS DISTINCT FROM p.project_id OR s.status NOT IN ('FROZEN','SUPERSEDED') OR s.frozen_at IS NULL OR s.content_hash IS NULL OR s.support_set_hash IS NULL))
        UNION ALL SELECT cp.id FROM manuscript_citation_placements cp JOIN manuscript_versions m ON m.id=cp.manuscript_version_id
          JOIN publications p ON p.id=m.publication_id LEFT JOIN source_versions v ON v.id=cp.source_version_id
          WHERE v.status NOT IN ('FROZEN','SUPERSEDED') OR v.frozen_at IS NULL OR v.content_hash IS NULL
            OR NOT EXISTS (SELECT 1 FROM literature_source_project_links l WHERE l.project_id=p.project_id AND l.literature_source_id=v.literature_source_id)
        UNION ALL SELECT cp.id FROM manuscript_artifact_placements cp JOIN manuscript_versions m ON m.id=cp.manuscript_version_id
          JOIN publications p ON p.id=m.publication_id LEFT JOIN artifact_versions v ON v.id=cp.artifact_version_id
          LEFT JOIN artifacts a ON a.id=v.artifact_id WHERE a.project_id IS DISTINCT FROM p.project_id
            OR v.status NOT IN ('FROZEN','SUPERSEDED') OR v.frozen_at IS NULL OR v.content_hash IS NULL
      ) x;
      IF bad IS NOT NULL THEN RAISE EXCEPTION 'incompatible placement IDs: %',bad; END IF;

    END $$;
    ALTER TABLE manuscript_versions DROP CONSTRAINT manuscript_versions_status_check,
      DROP CONSTRAINT ck_pr212_unfrozen_draft,
      ADD CONSTRAINT ck_b04_manuscript_status CHECK (status IN ('DRAFT','FROZEN')),
      ADD CONSTRAINT ck_b04_manuscript_seal CHECK (
        (status='DRAFT' AND placement_set_hash IS NULL AND content_hash IS NULL AND frozen_at IS NULL)
        OR (status='FROZEN' AND placement_set_hash IS NOT NULL AND content_hash IS NOT NULL
          AND placement_set_hash ~ '^[0-9a-f]{64}$' AND content_hash ~ '^[0-9a-f]{64}$' AND frozen_at IS NOT NULL));
    """)
    for guard in SEAL_GUARDS:
        op.execute(guard)
    op.execute("""
    CREATE FUNCTION b04_verify_structure(identity UUID) RETURNS void LANGUAGE plpgsql AS $$
    DECLARE m manuscript_versions; project UUID; pointer UUID; n BIGINT;
    BEGIN
      SELECT * INTO m FROM manuscript_versions WHERE id=identity;
      IF NOT FOUND THEN RETURN; END IF;
      IF m.status='DRAFT' THEN
        IF m.content_hash IS NOT NULL OR m.placement_set_hash IS NOT NULL OR m.frozen_at IS NOT NULL THEN
          RAISE EXCEPTION 'malformed draft seal' USING ERRCODE='P04M3'; END IF;
        RETURN;
      END IF;
      SELECT project_id,current_manuscript_version_id INTO project,pointer FROM publications WHERE id=m.publication_id;
      IF pointer IS DISTINCT FROM m.id OR m.content_hash IS NULL OR m.placement_set_hash IS NULL OR m.frozen_at IS NULL THEN
        RAISE EXCEPTION 'incomplete manuscript seal' USING ERRCODE='P04M3'; END IF;
      IF NOT EXISTS (SELECT 1 FROM artifact_versions v JOIN artifacts a ON a.id=v.artifact_id
        WHERE v.id=m.document_artifact_version_id AND a.project_id=project AND a.artifact_type='manuscript'
          AND v.status IN ('FROZEN','SUPERSEDED') AND v.frozen_at IS NOT NULL AND v.byte_size IS NOT NULL
          AND v.content_hash ~ '^[0-9a-f]{64}$') THEN
        RAISE EXCEPTION 'manuscript document closure' USING ERRCODE='P04M3'; END IF;
      SELECT count(*) INTO n FROM (
        SELECT section_id,ordinal FROM manuscript_claim_placements WHERE manuscript_version_id=identity
        UNION ALL SELECT section_id,ordinal FROM manuscript_citation_placements WHERE manuscript_version_id=identity
        UNION ALL SELECT section_id,ordinal FROM manuscript_artifact_placements WHERE manuscript_version_id=identity) p;
      IF n>10000 THEN RAISE EXCEPTION 'placement cap exceeded' USING ERRCODE='P04M3'; END IF;
      IF EXISTS (SELECT 1 FROM (
        SELECT 'claim' AS kind,section_id,ordinal FROM manuscript_claim_placements WHERE manuscript_version_id=identity
        UNION ALL SELECT 'citation',section_id,ordinal FROM manuscript_citation_placements WHERE manuscript_version_id=identity
        UNION ALL SELECT 'artifact',section_id,ordinal FROM manuscript_artifact_placements WHERE manuscript_version_id=identity) p
        GROUP BY kind,section_id HAVING min(ordinal)<>0 OR max(ordinal)<>count(*)-1 OR count(DISTINCT ordinal)<>count(*)) THEN
        RAISE EXCEPTION 'placement ordinal gaps' USING ERRCODE='P04M3'; END IF;
      IF EXISTS (SELECT 1 FROM manuscript_claim_placements p
        LEFT JOIN claim_versions v ON v.id=p.claim_version_id LEFT JOIN claims c ON c.id=v.claim_id
        LEFT JOIN scientific_conclusion_versions s ON s.id=p.scientific_conclusion_version_id
        LEFT JOIN scientific_conclusions sc ON sc.id=s.scientific_conclusion_id
        WHERE p.manuscript_version_id=identity AND
          ((p.claim_version_id IS NULL)=(p.scientific_conclusion_version_id IS NULL)
          OR (p.claim_version_id IS NOT NULL AND (c.project_id IS DISTINCT FROM project OR v.status NOT IN ('FROZEN','SUPERSEDED') OR v.frozen_at IS NULL OR v.content_hash IS NULL))
          OR (p.scientific_conclusion_version_id IS NOT NULL AND (sc.project_id IS DISTINCT FROM project OR s.status NOT IN ('FROZEN','SUPERSEDED') OR s.frozen_at IS NULL OR s.content_hash IS NULL OR s.support_set_hash IS NULL)))) THEN
        RAISE EXCEPTION 'scientific placement closure' USING ERRCODE='P04M3'; END IF;
      IF EXISTS (SELECT 1 FROM manuscript_citation_placements p LEFT JOIN source_versions v ON v.id=p.source_version_id
        WHERE p.manuscript_version_id=identity AND (v.status NOT IN ('FROZEN','SUPERSEDED') OR v.frozen_at IS NULL OR v.content_hash IS NULL
          OR NOT EXISTS (SELECT 1 FROM literature_source_project_links l WHERE l.literature_source_id=v.literature_source_id AND l.project_id=project))) THEN
        RAISE EXCEPTION 'citation placement closure' USING ERRCODE='P04M3'; END IF;
      IF EXISTS (SELECT 1 FROM manuscript_artifact_placements p LEFT JOIN artifact_versions v ON v.id=p.artifact_version_id
        LEFT JOIN artifacts a ON a.id=v.artifact_id WHERE p.manuscript_version_id=identity
          AND (a.project_id IS DISTINCT FROM project OR v.status NOT IN ('FROZEN','SUPERSEDED') OR v.frozen_at IS NULL OR v.content_hash IS NULL)) THEN
        RAISE EXCEPTION 'artifact placement closure' USING ERRCODE='P04M3'; END IF;
    END $$;
    CREATE FUNCTION b04_check_manuscript_closure() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN PERFORM b04_verify_structure(NEW.id); RETURN NULL; END $$;
    CREATE FUNCTION b04_check_current_manuscript() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE pointer UUID; BEGIN
      SELECT current_manuscript_version_id INTO pointer FROM publications WHERE id=NEW.id;
      IF pointer IS NOT NULL THEN
        IF NOT EXISTS (SELECT 1 FROM manuscript_versions WHERE id=pointer AND publication_id=NEW.id AND status='FROZEN') THEN
          RAISE EXCEPTION 'current manuscript must be sealed same-parent' USING ERRCODE='P04M3'; END IF;
        PERFORM b04_verify_structure(pointer);
      END IF; RETURN NULL;
    END $$;
    CREATE FUNCTION b04_check_placement_closure() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP<>'INSERT' THEN PERFORM b04_verify_structure(OLD.manuscript_version_id); END IF;
      IF TG_OP<>'DELETE' THEN PERFORM b04_verify_structure(NEW.manuscript_version_id); END IF;
      RETURN NULL;
    END $$;
    CREATE CONSTRAINT TRIGGER b04_complete_manuscript AFTER INSERT OR UPDATE ON manuscript_versions
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b04_check_manuscript_closure();
    CREATE CONSTRAINT TRIGGER b04_current_manuscript AFTER INSERT OR UPDATE ON publications
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b04_check_current_manuscript();
    """)
    for kind in ("claim", "citation", "artifact"):
        op.execute(
            f"CREATE CONSTRAINT TRIGGER b04_complete_{kind}_placement AFTER INSERT OR UPDATE OR DELETE ON manuscript_{kind}_placements DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b04_check_placement_closure()"
        )


def downgrade() -> None:
    op.execute("LOCK TABLE " + ",".join(TABLES) + " IN ACCESS EXCLUSIVE MODE")
    op.execute("""DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM manuscript_versions WHERE status='FROZEN')
        OR EXISTS (SELECT 1 FROM publications WHERE current_manuscript_version_id IS NOT NULL) THEN
        RAISE EXCEPTION 'sealed manuscript history retained' USING ERRCODE='P04M1'; END IF;
    END $$;
    DROP TRIGGER b04_complete_manuscript ON manuscript_versions;
    DROP TRIGGER b04_current_manuscript ON publications;
    """)
    for kind in ("claim", "citation", "artifact"):
        op.execute(f"DROP TRIGGER b04_complete_{kind}_placement ON manuscript_{kind}_placements")
    op.execute("""
    DROP FUNCTION b04_check_placement_closure();
    DROP FUNCTION b04_check_current_manuscript();
    DROP FUNCTION b04_check_manuscript_closure();
    DROP FUNCTION b04_verify_structure(UUID);
    ALTER TABLE manuscript_versions DROP CONSTRAINT ck_b04_manuscript_status,
      DROP CONSTRAINT ck_b04_manuscript_seal,
      ADD CONSTRAINT manuscript_versions_status_check CHECK (status='DRAFT'),
      ADD CONSTRAINT ck_pr212_unfrozen_draft CHECK (placement_set_hash IS NULL AND content_hash IS NULL AND frozen_at IS NULL);
    """)
    for guard in LEGACY_GUARDS:
        op.execute(guard)
