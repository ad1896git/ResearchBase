"""PR2-14 immutable frozen-target review and initial OPEN issues."""

from alembic import op

revision = "0040_pr2_14_initial_internal_review"
down_revision = "0039_pr2_13_citation_rebinding_guard"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE internal_review_records (
      id UUID PRIMARY KEY,
      project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
      manuscript_version_id UUID REFERENCES manuscript_versions(id) ON DELETE RESTRICT,
      claim_version_id UUID REFERENCES claim_versions(id) ON DELETE RESTRICT,
      scientific_conclusion_version_id UUID
        REFERENCES scientific_conclusion_versions(id) ON DELETE RESTRICT,
      artifact_version_id UUID REFERENCES artifact_versions(id) ON DELETE RESTRICT,
      target_content_hash CHAR(64) NOT NULL CHECK
        (target_content_hash ~ '^[0-9a-f]{64}$'),
      reviewer_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
      review_type VARCHAR(24) NOT NULL CHECK (review_type IN
        ('SCIENTIFIC','STATISTICAL','LITERATURE','REPRODUCIBILITY','EDITORIAL','COMPREHENSIVE')),
      recommendation VARCHAR(24) NOT NULL CHECK (recommendation IN
        ('ACCEPT','MINOR_REVISION','MAJOR_REVISION','REJECT','UNCERTAIN')),
      summary TEXT NOT NULL CHECK (length(btrim(summary)) BETWEEN 1 AND 16000),
      created_at TIMESTAMPTZ NOT NULL,
      content_hash CHAR(64) NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
      hash_scheme VARCHAR(32) NOT NULL CHECK (hash_scheme='sha256-cjson-v1'),
      CONSTRAINT ck_pr214_one_target CHECK (num_nonnulls(manuscript_version_id,
        claim_version_id,scientific_conclusion_version_id,artifact_version_id)=1)
    );
    CREATE TABLE review_issues (
      id UUID PRIMARY KEY,
      review_record_id UUID NOT NULL REFERENCES internal_review_records(id) ON DELETE RESTRICT,
      severity VARCHAR(16) NOT NULL CHECK (severity IN ('INFO','MINOR','MAJOR','BLOCKING')),
      issue_type VARCHAR(32) NOT NULL CHECK (issue_type IN
        ('UNSUPPORTED_CLAIM','CITATION','STATISTICAL','METHODOLOGICAL',
         'REPRODUCIBILITY','OVERCLAIM','CONTRADICTION','NOVELTY','WRITING','OTHER')),
      target_locator JSONB,
      description TEXT NOT NULL CHECK (length(btrim(description)) BETWEEN 1 AND 16000),
      related_claim_version_id UUID REFERENCES claim_versions(id) ON DELETE RESTRICT,
      related_source_version_id UUID REFERENCES source_versions(id) ON DELETE RESTRICT,
      related_run_id UUID REFERENCES runs(id) ON DELETE RESTRICT,
      status VARCHAR(16) NOT NULL CHECK (status='OPEN'),
      created_at TIMESTAMPTZ NOT NULL,
      ordinal INT NOT NULL CHECK (ordinal>=0),
      UNIQUE (review_record_id,ordinal)
    );
    CREATE TABLE review_issue_events (
      id UUID PRIMARY KEY,
      issue_id UUID NOT NULL REFERENCES review_issues(id) ON DELETE RESTRICT,
      actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
      prior_status VARCHAR(16),
      new_status VARCHAR(16) NOT NULL CHECK (new_status='OPEN'),
      occurred_at TIMESTAMPTZ NOT NULL,
      CHECK (prior_status IS NULL),
      UNIQUE (issue_id)
    );
    CREATE INDEX ix_pr214_review_manuscript ON internal_review_records(manuscript_version_id);
    CREATE INDEX ix_pr214_review_claim ON internal_review_records(claim_version_id);
    CREATE INDEX ix_pr214_review_conclusion
      ON internal_review_records(scientific_conclusion_version_id);
    CREATE INDEX ix_pr214_review_artifact ON internal_review_records(artifact_version_id);
    CREATE INDEX ix_pr214_review_reviewer ON internal_review_records(reviewer_actor_id);
    CREATE INDEX ix_pr214_issue_review_severity ON review_issues(review_record_id,severity);
    CREATE INDEX ix_pr214_issue_related_claim ON review_issues(related_claim_version_id);
    CREATE INDEX ix_pr214_issue_related_source ON review_issues(related_source_version_id);
    CREATE INDEX ix_pr214_issue_related_run ON review_issues(related_run_id);
    CREATE INDEX ix_pr214_issue_event_actor ON review_issue_events(actor_id);
    """)
    op.execute("""
    CREATE FUNCTION pr214_review_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
    CREATE TRIGGER pr214_review_guard BEFORE INSERT OR UPDATE OR DELETE
      ON internal_review_records FOR EACH ROW EXECUTE FUNCTION pr214_review_guard();
    CREATE FUNCTION pr214_issue_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
    CREATE TRIGGER pr214_issue_guard BEFORE INSERT OR UPDATE OR DELETE
      ON review_issues FOR EACH ROW EXECUTE FUNCTION pr214_issue_guard();
    CREATE FUNCTION pr214_open_event() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      INSERT INTO review_issue_events(id,issue_id,actor_id,prior_status,new_status,occurred_at)
        SELECT gen_random_uuid(),NEW.id,r.reviewer_actor_id,NULL,'OPEN',NEW.created_at
          FROM internal_review_records r WHERE r.id=NEW.review_record_id;
      RETURN NEW;
    END $$;
    CREATE TRIGGER pr214_open_event AFTER INSERT ON review_issues
      FOR EACH ROW EXECUTE FUNCTION pr214_open_event();
    CREATE TRIGGER pr214_issue_events_immutable BEFORE UPDATE OR DELETE
      ON review_issue_events FOR EACH ROW EXECUTE FUNCTION m2_immutable();
    """)


def downgrade() -> None:
    op.execute("""
    LOCK TABLE internal_review_records,review_issues,review_issue_events
      IN ACCESS EXCLUSIVE MODE;
    DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM internal_review_records)
         OR EXISTS (SELECT 1 FROM review_issues)
         OR EXISTS (SELECT 1 FROM review_issue_events) THEN
        RAISE EXCEPTION 'PR2-14 review history cannot be discarded' USING ERRCODE='P17E3';
      END IF;
    END $$;
    DROP TABLE review_issue_events;
    DROP TRIGGER pr214_open_event ON review_issues;
    DROP FUNCTION pr214_open_event();
    DROP TABLE review_issues;
    DROP TABLE internal_review_records;
    DROP FUNCTION pr214_issue_guard();
    DROP FUNCTION pr214_review_guard();
    """)
