"""PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis."""

from alembic import op

revision = "0042_pr2_15_minimal_decision"
down_revision = "0041_pr2_15_review_coordination"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE decision_records (
      id UUID PRIMARY KEY,
      project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
      decision_type VARCHAR(40) NOT NULL CHECK (decision_type='INTERNAL_SCIENTIFIC_RELEASE'),
      question TEXT NOT NULL CHECK (length(btrim(question))>0),
      decision VARCHAR(16) NOT NULL CHECK (decision='PROCEED'),
      rationale TEXT NOT NULL CHECK (length(btrim(rationale))>0),
      decided_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
      decided_at TIMESTAMPTZ NOT NULL,
      supersedes_decision_id UUID REFERENCES decision_records(id) ON DELETE RESTRICT
        CHECK (supersedes_decision_id IS NULL),
      basis_set_hash CHAR(64) NOT NULL CHECK (basis_set_hash ~ '^[0-9a-f]{64}$'),
      content_hash CHAR(64) NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
      hash_scheme VARCHAR(32) NOT NULL CHECK (hash_scheme='sha256-cjson-v1')
    );
    CREATE INDEX ix_pr215_decision_project ON decision_records(project_id);
    CREATE INDEX ix_pr215_decision_actor ON decision_records(decided_by);
    CREATE INDEX ix_pr215_decision_supersedes ON decision_records(supersedes_decision_id);
    CREATE TABLE decision_basis_conclusions (
      decision_id UUID NOT NULL REFERENCES decision_records(id) ON DELETE RESTRICT,
      scientific_conclusion_version_id UUID NOT NULL
        REFERENCES scientific_conclusion_versions(id) ON DELETE RESTRICT,
      ordinal INT NOT NULL CHECK (ordinal>=0),
      PRIMARY KEY (decision_id,scientific_conclusion_version_id),
      UNIQUE (decision_id,ordinal),
      UNIQUE (decision_id)
    );
    CREATE INDEX ix_pr215_basis_conclusion_target
      ON decision_basis_conclusions(scientific_conclusion_version_id);
    CREATE TABLE decision_basis_reviews (
      decision_id UUID NOT NULL REFERENCES decision_records(id) ON DELETE RESTRICT,
      internal_review_record_id UUID NOT NULL
        REFERENCES internal_review_records(id) ON DELETE RESTRICT,
      ordinal INT NOT NULL CHECK (ordinal>=0),
      PRIMARY KEY (decision_id,internal_review_record_id),
      UNIQUE (decision_id,ordinal)
    );
    CREATE INDEX ix_pr215_basis_review_target
      ON decision_basis_reviews(internal_review_record_id);
    CREATE FUNCTION pr215_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      RAISE EXCEPTION 'decision history is immutable' USING ERRCODE='P17F1';
    END $$;
    CREATE TRIGGER pr215_decision_immutable BEFORE UPDATE OR DELETE ON decision_records
      FOR EACH ROW EXECUTE FUNCTION pr215_immutable();
    CREATE TRIGGER pr215_conclusion_basis_immutable BEFORE UPDATE OR DELETE
      ON decision_basis_conclusions FOR EACH ROW EXECUTE FUNCTION pr215_immutable();
    CREATE TRIGGER pr215_review_basis_immutable BEFORE UPDATE OR DELETE
      ON decision_basis_reviews FOR EACH ROW EXECUTE FUNCTION pr215_immutable();
    CREATE FUNCTION pr215_basis_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE target_id UUID; target_project UUID; parent_xmin bigint;
      decision_project UUID; target_status TEXT; target_hash TEXT;
    BEGIN
      IF TG_TABLE_NAME='decision_basis_conclusions' THEN
        target_id := NEW.scientific_conclusion_version_id;
      ELSE
        SELECT scientific_conclusion_version_id INTO target_id FROM internal_review_records
          WHERE id=NEW.internal_review_record_id;
      END IF;
      -- Same exact target exclusion as 0041; no parent/review lock precedes it.
      SELECT v.status,v.content_hash INTO target_status,target_hash
        FROM scientific_conclusion_versions v WHERE v.id=target_id FOR UPDATE;
      IF NOT FOUND OR target_status<>'FROZEN' OR target_hash IS NULL THEN
        RAISE EXCEPTION 'exact frozen conclusion basis required' USING ERRCODE='P17F2';
      END IF;
      SELECT c.project_id INTO target_project FROM scientific_conclusions c
        JOIN scientific_conclusion_versions v ON v.scientific_conclusion_id=c.id
        WHERE v.id=target_id FOR SHARE OF c;
      SELECT d.project_id,d.xmin::text::bigint INTO decision_project,parent_xmin
        FROM decision_records d WHERE d.id=NEW.decision_id;
      IF parent_xmin IS DISTINCT FROM pg_current_xact_id()::text::bigint
         OR decision_project IS DISTINCT FROM target_project THEN
        RAISE EXCEPTION 'new same-project typed decision basis required' USING ERRCODE='P17F2';
      END IF;
      IF EXISTS (SELECT 1 FROM decision_basis_conclusions b JOIN decision_records d
          ON d.id=b.decision_id WHERE b.scientific_conclusion_version_id=target_id
          AND d.project_id=decision_project AND d.decision_type='INTERNAL_SCIENTIFIC_RELEASE'
          AND d.id<>NEW.decision_id) THEN
        RAISE EXCEPTION 'initial decision scope already recorded' USING ERRCODE='P17F3';
      END IF;
      IF TG_TABLE_NAME='decision_basis_reviews' AND NOT EXISTS (
          SELECT 1 FROM internal_review_records r WHERE r.id=NEW.internal_review_record_id
            AND r.project_id=decision_project AND r.target_content_hash=target_hash
            AND r.scientific_conclusion_version_id=target_id) THEN
        RAISE EXCEPTION 'exact review binding required' USING ERRCODE='P17F2';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER pr215_conclusion_basis_guard BEFORE INSERT ON decision_basis_conclusions
      FOR EACH ROW EXECUTE FUNCTION pr215_basis_guard();
    CREATE TRIGGER pr215_review_basis_guard BEFORE INSERT ON decision_basis_reviews
      FOR EACH ROW EXECUTE FUNCTION pr215_basis_guard();
    CREATE FUNCTION pr215_complete_basis() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE did UUID; tid UUID; pid UUID; target_hash TEXT; n INT;
    BEGIN
      IF TG_TABLE_NAME='decision_records' THEN did := NEW.id;
      ELSE did := NEW.decision_id; END IF;
      SELECT d.project_id,b.scientific_conclusion_version_id,v.content_hash
        INTO pid,tid,target_hash FROM decision_records d
        JOIN decision_basis_conclusions b ON b.decision_id=d.id
        JOIN scientific_conclusion_versions v ON v.id=b.scientific_conclusion_version_id
        WHERE d.id=did;
      IF tid IS NULL THEN
        RAISE EXCEPTION 'one exact conclusion basis required' USING ERRCODE='P17F2';
      END IF;
      IF NOT EXISTS (SELECT 1 FROM decision_basis_reviews WHERE decision_id=did)
         OR EXISTS (SELECT 1 FROM decision_basis_reviews b JOIN internal_review_records r
            ON r.id=b.internal_review_record_id WHERE b.decision_id=did
            AND (r.project_id<>pid OR r.scientific_conclusion_version_id IS DISTINCT FROM tid
                 OR r.target_content_hash<>target_hash))
         OR EXISTS (SELECT 1 FROM internal_review_records r
            WHERE r.project_id=pid AND r.scientific_conclusion_version_id=tid
              AND NOT EXISTS (SELECT 1 FROM decision_basis_reviews b
                WHERE b.decision_id=did AND b.internal_review_record_id=r.id)) THEN
        RAISE EXCEPTION 'complete exact review basis required' USING ERRCODE='P17F2';
      END IF;
      IF EXISTS (SELECT 1 FROM review_issues i JOIN internal_review_records r
           ON r.id=i.review_record_id WHERE r.project_id=pid
             AND r.scientific_conclusion_version_id=tid
             AND i.status='OPEN' AND i.severity='BLOCKING') THEN
        RAISE EXCEPTION 'applicable blocking issue remains open' USING ERRCODE='P17F2';
      END IF;
      SELECT count(*) INTO n FROM decision_basis_reviews WHERE decision_id=did;
      -- R2 lexical kind order is InternalReviewRecord before ScientificConclusionVersion.
      IF (SELECT ordinal FROM decision_basis_conclusions WHERE decision_id=did)<>n
         OR EXISTS (SELECT 1 FROM (
           SELECT b.ordinal,row_number() OVER (ORDER BY b.internal_review_record_id)-1 AS expected
           FROM decision_basis_reviews b WHERE b.decision_id=did) positions
           WHERE ordinal<>expected) THEN
        RAISE EXCEPTION 'canonical contiguous basis ordinals required' USING ERRCODE='P17F2';
      END IF;
      RETURN NULL;
    END $$;
    CREATE CONSTRAINT TRIGGER pr215_complete_decision AFTER INSERT ON decision_records
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pr215_complete_basis();
    CREATE CONSTRAINT TRIGGER pr215_complete_conclusion AFTER INSERT ON decision_basis_conclusions
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pr215_complete_basis();
    CREATE CONSTRAINT TRIGGER pr215_complete_review AFTER INSERT ON decision_basis_reviews
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pr215_complete_basis();
    """)


def downgrade() -> None:
    op.execute("""
    LOCK TABLE decision_records,decision_basis_conclusions,decision_basis_reviews
      IN ACCESS EXCLUSIVE MODE;
    DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM decision_records)
         OR EXISTS (SELECT 1 FROM decision_basis_conclusions)
         OR EXISTS (SELECT 1 FROM decision_basis_reviews) THEN
        RAISE EXCEPTION 'PR2-15 decision history cannot be discarded' USING ERRCODE='P17F2';
      END IF;
    END $$;
    DROP TABLE decision_basis_reviews;
    DROP TABLE decision_basis_conclusions;
    DROP TABLE decision_records;
    DROP FUNCTION pr215_complete_basis();
    DROP FUNCTION pr215_basis_guard();
    DROP FUNCTION pr215_immutable();
    """)
