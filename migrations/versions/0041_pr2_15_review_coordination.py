"""Forward exact-conclusion review/Issue coordination, preserving immutable history.

Database order: target FOR UPDATE -> parent (review creation only) -> review
FOR SHARE -> Issue/event writes. A review INSERT takes UPDATE immediately,
including zero-Issue reviews. Non-conclusion PR2-14 semantics are unchanged.
Any deadlock/serialization error aborts the transaction; the Application caller
must restart the whole command and authorization, never continue a failed attempt.
"""

from alembic import op

revision = "0041_pr2_15_review_coordination"
down_revision = "0040_pr2_14_initial_internal_review"
branch_labels = None
depends_on = None

def upgrade() -> None:
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
    """)


def downgrade() -> None:
    # Restoring weaker guards while history exists would silently remove guarantees.
    # Keep all rows and the migration revision intact by failing transactionally.
    op.execute("""
    LOCK TABLE internal_review_records,review_issues,review_issue_events
      IN ACCESS EXCLUSIVE MODE;
    DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM internal_review_records
                 WHERE scientific_conclusion_version_id IS NOT NULL) THEN
        RAISE EXCEPTION 'PR2-15 coordination history guarantees cannot be removed'
          USING ERRCODE='P17E3';
      END IF;
    END $$;
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
        SELECT v.status,v.content_hash,c.project_id,v.created_by,v.frozen_at
          INTO target_status,target_hash,target_project,target_author,target_frozen
          FROM scientific_conclusion_versions v
          JOIN scientific_conclusions c ON c.id=v.scientific_conclusion_id
          WHERE v.id=NEW.scientific_conclusion_version_id FOR SHARE OF v,c;
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
    DECLARE review_project UUID;
    BEGIN
      IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'initial issue is immutable' USING ERRCODE='P17E1';
      END IF;
      SELECT project_id INTO review_project FROM internal_review_records
        WHERE id=NEW.review_record_id FOR SHARE;
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
