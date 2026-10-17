"""B05 manuscript review coordination and deferred immutable OPEN history guards."""

# ruff: noqa: E501
from alembic import op

revision = "0049_b05_manuscript_review"
down_revision = "0048_b04_manuscript_freeze"
branch_labels = None
depends_on = None

LEGACY_GUARDS = """
    CREATE OR REPLACE FUNCTION pr214_review_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE target_status TEXT; target_hash TEXT; target_project UUID;
      target_author UUID; target_frozen TIMESTAMPTZ;
    BEGIN
      IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'internal review is immutable' USING ERRCODE='P17E1';
      END IF;
      IF NEW.claim_version_id IS NOT NULL THEN
        SELECT v.status,v.content_hash,c.project_id,v.created_by,v.frozen_at
          INTO target_status,target_hash,target_project,target_author,target_frozen
          FROM claim_versions v JOIN claims c ON c.id=v.claim_id
          WHERE v.id=NEW.claim_version_id FOR SHARE OF v,c;
      ELSIF NEW.scientific_conclusion_version_id IS NOT NULL THEN
        -- Exact target first; never acquire SHARE and upgrade during Issue INSERT.
        PERFORM 1 FROM scientific_conclusion_versions
          WHERE id=NEW.scientific_conclusion_version_id FOR UPDATE;
        IF NOT FOUND THEN
          RAISE EXCEPTION 'exact independent frozen review target required'
            USING ERRCODE='P17E2';
        END IF;
        SELECT v.status,v.content_hash,c.project_id,v.created_by,v.frozen_at
          INTO target_status,target_hash,target_project,target_author,target_frozen
          FROM scientific_conclusion_versions v
          JOIN scientific_conclusions c ON c.id=v.scientific_conclusion_id
          WHERE v.id=NEW.scientific_conclusion_version_id FOR SHARE OF c;
      ELSIF NEW.artifact_version_id IS NOT NULL THEN
        SELECT v.status,v.content_hash,a.project_id,v.created_by,v.frozen_at
          INTO target_status,target_hash,target_project,target_author,target_frozen
          FROM artifact_versions v JOIN artifacts a ON a.id=v.artifact_id
          WHERE v.id=NEW.artifact_version_id FOR SHARE OF v,a;
      ELSE
        SELECT v.status,v.content_hash,p.project_id,v.created_by,v.frozen_at
          INTO target_status,target_hash,target_project,target_author,target_frozen
          FROM manuscript_versions v JOIN publications p ON p.id=v.publication_id
          WHERE v.id=NEW.manuscript_version_id FOR SHARE OF v,p;
      END IF;
      IF target_status NOT IN ('FROZEN','SUPERSEDED') OR target_frozen IS NULL
         OR target_hash IS DISTINCT FROM NEW.target_content_hash
         OR target_project IS DISTINCT FROM NEW.project_id
         OR target_author IS NULL OR target_author=NEW.reviewer_actor_id
         OR NOT EXISTS (SELECT 1 FROM actors a WHERE a.id=NEW.reviewer_actor_id
                       AND a.actor_type='HUMAN' AND a.retired_at IS NULL) THEN
        RAISE EXCEPTION 'exact independent frozen review target required'
          USING ERRCODE='P17E2';
      END IF;
      RETURN NEW;
    END $$;
    CREATE OR REPLACE FUNCTION pr214_issue_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE review_project UUID; target_id UUID; checked_target UUID;
    BEGIN
      IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'initial issue is immutable' USING ERRCODE='P17E1';
      END IF;
      -- Discover only immutable identity without a row lock; target precedes review.
      SELECT scientific_conclusion_version_id INTO target_id
        FROM internal_review_records WHERE id=NEW.review_record_id;
      IF target_id IS NOT NULL THEN
        PERFORM 1 FROM scientific_conclusion_versions WHERE id=target_id FOR UPDATE;
        IF NOT FOUND THEN
          RAISE EXCEPTION 'issue reference outside review project' USING ERRCODE='P17E2';
        END IF;
      END IF;
      -- A new READ COMMITTED statement after any target wait rereads exact binding.
      SELECT project_id,scientific_conclusion_version_id
        INTO review_project,checked_target FROM internal_review_records
        WHERE id=NEW.review_record_id FOR SHARE;
      IF checked_target IS DISTINCT FROM target_id THEN
        RAISE EXCEPTION 'issue reference outside review project' USING ERRCODE='P17E2';
      END IF;
      IF review_project IS NULL
         OR (NEW.related_claim_version_id IS NOT NULL AND NOT EXISTS (
           SELECT 1 FROM claim_versions v JOIN claims c ON c.id=v.claim_id
           WHERE v.id=NEW.related_claim_version_id AND c.project_id=review_project))
         OR (NEW.related_source_version_id IS NOT NULL AND NOT EXISTS (
           SELECT 1 FROM source_versions v JOIN literature_source_project_links l
             ON l.literature_source_id=v.literature_source_id
           WHERE v.id=NEW.related_source_version_id AND l.project_id=review_project))
         OR (NEW.related_run_id IS NOT NULL AND NOT EXISTS (
           SELECT 1 FROM runs r WHERE r.id=NEW.related_run_id
             AND r.project_id=review_project)) THEN
        RAISE EXCEPTION 'issue reference outside review project' USING ERRCODE='P17E2';
      END IF;
      RETURN NEW;
    END $$;
    """


def upgrade() -> None:
    op.execute(
        "LOCK TABLE internal_review_records,review_issues,review_issue_events IN ACCESS EXCLUSIVE MODE"
    )
    op.execute("""
    CREATE OR REPLACE FUNCTION pr214_review_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE target_status TEXT; target_hash TEXT; target_project UUID;
      target_author UUID; target_frozen TIMESTAMPTZ;
    BEGIN
      IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'internal review is immutable' USING ERRCODE='P17E1';
      END IF;
      IF NEW.claim_version_id IS NOT NULL THEN
        SELECT v.status,v.content_hash,c.project_id,v.created_by,v.frozen_at
          INTO target_status,target_hash,target_project,target_author,target_frozen
          FROM claim_versions v JOIN claims c ON c.id=v.claim_id
          WHERE v.id=NEW.claim_version_id FOR SHARE OF v,c;
      ELSIF NEW.scientific_conclusion_version_id IS NOT NULL THEN
        -- Exact target first; never acquire SHARE and upgrade during Issue INSERT.
        PERFORM 1 FROM scientific_conclusion_versions
          WHERE id=NEW.scientific_conclusion_version_id FOR UPDATE;
        IF NOT FOUND THEN
          RAISE EXCEPTION 'exact independent frozen review target required'
            USING ERRCODE='P17E2';
        END IF;
        SELECT v.status,v.content_hash,c.project_id,v.created_by,v.frozen_at
          INTO target_status,target_hash,target_project,target_author,target_frozen
          FROM scientific_conclusion_versions v
          JOIN scientific_conclusions c ON c.id=v.scientific_conclusion_id
          WHERE v.id=NEW.scientific_conclusion_version_id FOR SHARE OF c;
      ELSIF NEW.artifact_version_id IS NOT NULL THEN
        SELECT v.status,v.content_hash,a.project_id,v.created_by,v.frozen_at
          INTO target_status,target_hash,target_project,target_author,target_frozen
          FROM artifact_versions v JOIN artifacts a ON a.id=v.artifact_id
          WHERE v.id=NEW.artifact_version_id FOR SHARE OF v,a;
      ELSE
        PERFORM 1 FROM manuscript_versions WHERE id=NEW.manuscript_version_id FOR UPDATE;
        IF NOT FOUND THEN
          RAISE EXCEPTION 'exact frozen manuscript required' USING ERRCODE='P17E2';
        END IF;
        PERFORM 1 FROM manuscript_versions WHERE id=NEW.manuscript_version_id
          AND placement_set_hash IS NOT NULL;
        IF NOT FOUND THEN
          RAISE EXCEPTION 'complete manuscript seal required' USING ERRCODE='P17E2';
        END IF;
        SELECT v.status,v.content_hash,p.project_id,v.created_by,v.frozen_at
          INTO target_status,target_hash,target_project,target_author,target_frozen
          FROM manuscript_versions v JOIN publications p ON p.id=v.publication_id
          WHERE v.id=NEW.manuscript_version_id FOR SHARE OF p;
      END IF;
      IF target_status NOT IN ('FROZEN','SUPERSEDED') OR target_frozen IS NULL
         OR target_hash IS DISTINCT FROM NEW.target_content_hash
         OR target_project IS DISTINCT FROM NEW.project_id
         OR target_author IS NULL OR target_author=NEW.reviewer_actor_id
         OR NOT EXISTS (SELECT 1 FROM actors a WHERE a.id=NEW.reviewer_actor_id
                       AND a.actor_type='HUMAN' AND a.retired_at IS NULL) THEN
        RAISE EXCEPTION 'exact independent frozen review target required'
          USING ERRCODE='P17E2';
      END IF;
      RETURN NEW;
    END $$;
    CREATE OR REPLACE FUNCTION pr214_issue_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE review_project UUID; target_id UUID; checked_target UUID; manuscript_id UUID; checked_manuscript UUID;
    BEGIN
      IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'initial issue is immutable' USING ERRCODE='P17E1';
      END IF;
      -- Discover only immutable identity without a row lock; target precedes review.
      SELECT scientific_conclusion_version_id,manuscript_version_id INTO target_id,manuscript_id
        FROM internal_review_records WHERE id=NEW.review_record_id;
      IF target_id IS NOT NULL THEN
        PERFORM 1 FROM scientific_conclusion_versions WHERE id=target_id FOR UPDATE;
        IF NOT FOUND THEN
          RAISE EXCEPTION 'issue reference outside review project' USING ERRCODE='P17E2';
        END IF;
      END IF;
      IF manuscript_id IS NOT NULL THEN
        PERFORM 1 FROM manuscript_versions WHERE id=manuscript_id FOR UPDATE;
        IF NOT FOUND THEN
          RAISE EXCEPTION 'issue reference outside review project' USING ERRCODE='P17E2';
        END IF;
      END IF;
      -- A new READ COMMITTED statement after any target wait rereads exact binding.
      SELECT project_id,scientific_conclusion_version_id,manuscript_version_id
        INTO review_project,checked_target,checked_manuscript FROM internal_review_records
        WHERE id=NEW.review_record_id FOR SHARE;
      IF checked_target IS DISTINCT FROM target_id OR checked_manuscript IS DISTINCT FROM manuscript_id THEN
        RAISE EXCEPTION 'issue reference outside review project' USING ERRCODE='P17E2';
      END IF;
      IF review_project IS NULL
         OR (NEW.related_claim_version_id IS NOT NULL AND NOT EXISTS (
           SELECT 1 FROM claim_versions v JOIN claims c ON c.id=v.claim_id
           WHERE v.id=NEW.related_claim_version_id AND c.project_id=review_project))
         OR (NEW.related_source_version_id IS NOT NULL AND NOT EXISTS (
           SELECT 1 FROM source_versions v JOIN literature_source_project_links l
             ON l.literature_source_id=v.literature_source_id
           WHERE v.id=NEW.related_source_version_id AND l.project_id=review_project))
         OR (NEW.related_run_id IS NOT NULL AND NOT EXISTS (
           SELECT 1 FROM runs r WHERE r.id=NEW.related_run_id
             AND r.project_id=review_project)) THEN
        RAISE EXCEPTION 'issue reference outside review project' USING ERRCODE='P17E2';
      END IF;
      RETURN NEW;
    END $$;
    """)
    op.execute("""
CREATE FUNCTION b05_verify_review_structure(identity UUID) RETURNS void LANGUAGE plpgsql AS $$
DECLARE target UUID; r internal_review_records; n BIGINT;
BEGIN
  SELECT manuscript_version_id INTO target FROM internal_review_records WHERE id=identity;
  IF target IS NULL THEN RETURN; END IF;
  PERFORM 1 FROM manuscript_versions WHERE id=target FOR UPDATE;
  SELECT * INTO r FROM internal_review_records WHERE id=identity FOR SHARE;
  IF r.manuscript_version_id IS DISTINCT FROM target OR NOT EXISTS (
    SELECT 1 FROM manuscript_versions m JOIN publications p ON p.id=m.publication_id
    WHERE m.id=target AND p.project_id=r.project_id AND m.status IN ('FROZEN','SUPERSEDED')
      AND m.frozen_at IS NOT NULL AND m.placement_set_hash IS NOT NULL
      AND m.content_hash=r.target_content_hash) THEN
    RAISE EXCEPTION 'B05 malformed target for review %',identity USING ERRCODE='P05R1';
  END IF;
  SELECT count(*) INTO n FROM review_issues WHERE review_record_id=identity;
  IF n>0 AND EXISTS (SELECT 1 FROM review_issues WHERE review_record_id=identity
      GROUP BY review_record_id HAVING min(ordinal)<>0 OR max(ordinal)<>n-1
        OR count(DISTINCT ordinal)<>n) THEN
    RAISE EXCEPTION 'B05 issue ordinal gap for review %',identity USING ERRCODE='P05R1';
  END IF;
  IF EXISTS (SELECT 1 FROM review_issues i WHERE i.review_record_id=identity AND
    (i.status<>'OPEN' OR (SELECT count(*) FROM review_issue_events e WHERE e.issue_id=i.id)<>1
      OR NOT EXISTS (SELECT 1 FROM review_issue_events e WHERE e.issue_id=i.id
        AND e.prior_status IS NULL AND e.new_status='OPEN'
        AND e.actor_id=r.reviewer_actor_id AND e.occurred_at=i.created_at))) THEN
    RAISE EXCEPTION 'B05 malformed OPEN history for review %',identity USING ERRCODE='P05R1';
  END IF;
END $$;
CREATE FUNCTION b05_check_review_structure() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE identity UUID;
BEGIN
  IF TG_TABLE_NAME='internal_review_records' THEN identity:=NEW.id;
  ELSIF TG_TABLE_NAME='review_issues' THEN identity:=NEW.review_record_id;
  ELSE SELECT review_record_id INTO identity FROM review_issues WHERE id=NEW.issue_id;
  END IF;
  PERFORM b05_verify_review_structure(identity);
  RETURN NEW;
END $$;
DO $$ DECLARE identity UUID; BEGIN
  FOR identity IN SELECT id FROM internal_review_records WHERE manuscript_version_id IS NOT NULL
    ORDER BY id LOOP PERFORM b05_verify_review_structure(identity); END LOOP;
END $$;
-- Target bindings are immutable. Filter at INSERT time so legacy targets do
-- not acquire new deferred work (or require retained SQL-role grants at commit).
-- VOLATILE ensures the predicates see rows inserted by the current command.
CREATE FUNCTION b05_is_manuscript_review(identity UUID) RETURNS boolean
LANGUAGE sql VOLATILE AS $$
  SELECT EXISTS (SELECT 1 FROM internal_review_records
    WHERE id=$1 AND manuscript_version_id IS NOT NULL)
$$;
CREATE FUNCTION b05_is_manuscript_issue(identity UUID) RETURNS boolean
LANGUAGE sql VOLATILE AS $$
  SELECT EXISTS (SELECT 1 FROM review_issues i JOIN internal_review_records r
    ON r.id=i.review_record_id WHERE i.id=$1 AND r.manuscript_version_id IS NOT NULL)
$$;
CREATE CONSTRAINT TRIGGER b05_complete_review AFTER INSERT ON internal_review_records
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
WHEN (NEW.manuscript_version_id IS NOT NULL) EXECUTE FUNCTION b05_check_review_structure();
CREATE CONSTRAINT TRIGGER b05_complete_issue AFTER INSERT ON review_issues
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
WHEN (b05_is_manuscript_review(NEW.review_record_id)) EXECUTE FUNCTION b05_check_review_structure();
CREATE CONSTRAINT TRIGGER b05_complete_issue_event AFTER INSERT ON review_issue_events
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
WHEN (b05_is_manuscript_issue(NEW.issue_id)) EXECUTE FUNCTION b05_check_review_structure();
""")


def downgrade() -> None:
    op.execute("""
LOCK TABLE internal_review_records,review_issues,review_issue_events IN ACCESS EXCLUSIVE MODE;
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM internal_review_records WHERE manuscript_version_id IS NOT NULL) THEN
    RAISE EXCEPTION 'B05 manuscript review history retained' USING ERRCODE='P05R1';
  END IF;
END $$;
DROP TRIGGER b05_complete_review ON internal_review_records;
DROP TRIGGER b05_complete_issue ON review_issues;
DROP TRIGGER b05_complete_issue_event ON review_issue_events;
DROP FUNCTION b05_check_review_structure();
DROP FUNCTION b05_verify_review_structure(UUID);
DROP FUNCTION b05_is_manuscript_issue(UUID);
DROP FUNCTION b05_is_manuscript_review(UUID);
""")
    op.execute(LEGACY_GUARDS)
