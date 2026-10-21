"""B02 immutable typed strategy candidate admission relations (ADR-0020)."""

# ruff: noqa: E501
from alembic import op

revision = "0073_b02_strategy_admission"
down_revision = "0072_b03_discussion_hypothesis"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(r"""
CREATE TABLE strategy_candidate_captures (
 id UUID CONSTRAINT pk_b02_capture PRIMARY KEY,
 project_id UUID NOT NULL CONSTRAINT fk_b02_capture_project REFERENCES projects(id) ON DELETE RESTRICT,
 artifact_version_id UUID NOT NULL CONSTRAINT fk_b02_capture_artifact REFERENCES artifact_versions(id) ON DELETE RESTRICT,
 artifact_content_hash CHAR(64) NOT NULL,
 topic VARCHAR(255) NOT NULL,
 max_evidence_candidates INTEGER NOT NULL,
 strategy_id TEXT NOT NULL,
 strategy_version TEXT NOT NULL,
 captured_by UUID NOT NULL CONSTRAINT fk_b02_capture_actor REFERENCES actors(id) ON DELETE RESTRICT,
 captured_at TIMESTAMPTZ NOT NULL,
 content_hash CHAR(64) NOT NULL,
 hash_scheme TEXT NOT NULL,
 CONSTRAINT uq_b02_capture_artifact UNIQUE(artifact_version_id),
 CONSTRAINT ck_b02_capture_topic CHECK(length(btrim(topic)) BETWEEN 1 AND 255),
 CONSTRAINT ck_b02_capture_limit CHECK(max_evidence_candidates BETWEEN 1 AND 100),
 CONSTRAINT ck_b02_capture_strategy CHECK(strategy_id='native-storm-like' AND strategy_version='candidate-v1'),
 CONSTRAINT ck_b02_capture_hash CHECK(content_hash ~ '^[0-9a-f]{64}$' AND artifact_content_hash ~ '^[0-9a-f]{64}$' AND hash_scheme='sha256-cjson-v1')
);
CREATE TABLE strategy_candidate_sources (
 capture_id UUID NOT NULL CONSTRAINT fk_b02_source_capture REFERENCES strategy_candidate_captures(id) ON DELETE RESTRICT,
 source_version_id UUID NOT NULL CONSTRAINT fk_b02_source_version REFERENCES source_versions(id) ON DELETE RESTRICT,
 CONSTRAINT pk_b02_sources PRIMARY KEY(capture_id,source_version_id)
);
CREATE INDEX ix_b02_capture_project ON strategy_candidate_captures(project_id);
CREATE INDEX ix_b02_capture_actor ON strategy_candidate_captures(captured_by);
CREATE INDEX ix_b02_sources_version ON strategy_candidate_sources(source_version_id);
CREATE TABLE strategy_question_admissions (
 id UUID CONSTRAINT pk_b02_q PRIMARY KEY,
 project_id UUID NOT NULL CONSTRAINT fk_b02_q_project REFERENCES projects(id) ON DELETE RESTRICT,
 capture_id UUID NOT NULL CONSTRAINT fk_b02_q_capture REFERENCES strategy_candidate_captures(id) ON DELETE RESTRICT,
 capture_content_hash CHAR(64) NOT NULL,
 candidate_index INTEGER NOT NULL,
 candidate_text TEXT NOT NULL,
 question_text TEXT NOT NULL,
 rationale TEXT NOT NULL,
 research_question_id UUID NOT NULL CONSTRAINT fk_b02_q_question REFERENCES research_questions(id) ON DELETE RESTRICT,
 research_question_version_id UUID NOT NULL CONSTRAINT fk_b02_q_version REFERENCES research_question_versions(id) ON DELETE RESTRICT,
 admitted_by UUID NOT NULL CONSTRAINT fk_b02_q_actor REFERENCES actors(id) ON DELETE RESTRICT,
 admitted_at TIMESTAMPTZ NOT NULL,
 content_hash CHAR(64) NOT NULL,
 hash_scheme TEXT NOT NULL,
 CONSTRAINT uq_b02_q_candidate UNIQUE(capture_id,candidate_index),
 CONSTRAINT uq_b02_q_version UNIQUE(research_question_version_id),
 CONSTRAINT ck_b02_q_index CHECK(candidate_index BETWEEN 0 AND 999),
 CONSTRAINT ck_b02_q_text CHECK(length(btrim(question_text)) BETWEEN 1 AND 16000 AND question_text=btrim(question_text) AND length(btrim(rationale)) BETWEEN 1 AND 16000 AND rationale=btrim(rationale) AND length(btrim(candidate_text))>0),
 CONSTRAINT ck_b02_q_hash CHECK(content_hash ~ '^[0-9a-f]{64}$' AND capture_content_hash ~ '^[0-9a-f]{64}$' AND hash_scheme='sha256-cjson-v1')
);
CREATE INDEX ix_b02_q_project ON strategy_question_admissions(project_id);
CREATE INDEX ix_b02_q_actor ON strategy_question_admissions(admitted_by);
CREATE INDEX ix_b02_q_question ON strategy_question_admissions(research_question_id);
CREATE TABLE strategy_hypothesis_admissions (
 id UUID CONSTRAINT pk_b02_h PRIMARY KEY,
 project_id UUID NOT NULL CONSTRAINT fk_b02_h_project REFERENCES projects(id) ON DELETE RESTRICT,
 capture_id UUID NOT NULL CONSTRAINT fk_b02_h_capture REFERENCES strategy_candidate_captures(id) ON DELETE RESTRICT,
 capture_content_hash CHAR(64) NOT NULL,
 candidate_index INTEGER NOT NULL,
 candidate_text TEXT NOT NULL,
 statement TEXT NOT NULL,
 rationale TEXT NOT NULL,
 research_question_id UUID  CONSTRAINT fk_b02_h_question REFERENCES research_questions(id) ON DELETE RESTRICT,
 hypothesis_id UUID NOT NULL CONSTRAINT fk_b02_h_hypothesis REFERENCES hypotheses(id) ON DELETE RESTRICT,
 hypothesis_version_id UUID NOT NULL CONSTRAINT fk_b02_h_version REFERENCES hypothesis_versions(id) ON DELETE RESTRICT,
 admitted_by UUID NOT NULL CONSTRAINT fk_b02_h_actor REFERENCES actors(id) ON DELETE RESTRICT,
 admitted_at TIMESTAMPTZ NOT NULL,
 content_hash CHAR(64) NOT NULL,
 hash_scheme TEXT NOT NULL,
 CONSTRAINT uq_b02_h_candidate UNIQUE(capture_id,candidate_index),
 CONSTRAINT uq_b02_h_version UNIQUE(hypothesis_version_id),
 CONSTRAINT ck_b02_h_index CHECK(candidate_index BETWEEN 0 AND 999),
 CONSTRAINT ck_b02_h_text CHECK(length(btrim(statement)) BETWEEN 1 AND 16000 AND statement=btrim(statement) AND length(btrim(rationale)) BETWEEN 1 AND 16000 AND rationale=btrim(rationale) AND length(btrim(candidate_text))>0),
 CONSTRAINT ck_b02_h_hash CHECK(content_hash ~ '^[0-9a-f]{64}$' AND capture_content_hash ~ '^[0-9a-f]{64}$' AND hash_scheme='sha256-cjson-v1')
);
CREATE INDEX ix_b02_h_project ON strategy_hypothesis_admissions(project_id);
CREATE INDEX ix_b02_h_actor ON strategy_hypothesis_admissions(admitted_by);
CREATE INDEX ix_b02_h_question ON strategy_hypothesis_admissions(research_question_id);
CREATE INDEX ix_b02_h_hypothesis ON strategy_hypothesis_admissions(hypothesis_id);
CREATE FUNCTION b02_preheld() RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
BEGIN
 IF current_setting('transaction_isolation')<>'read committed' OR EXISTS (
 SELECT 1 FROM unnest(ARRAY['actor_subject_bindings','actors','artifact_versions','artifacts','hypotheses','hypothesis_versions','literature_source_project_links','literature_sources','project_membership_events','project_memberships','project_role_assignments','projects','research_question_versions','research_questions','source_versions','strategy_candidate_captures','strategy_candidate_sources','strategy_hypothesis_admissions','strategy_question_admissions']) n(name)
 WHERE NOT EXISTS(SELECT 1 FROM pg_locks l WHERE l.pid=pg_backend_pid() AND l.locktype='relation'
 AND l.relation=to_regclass('public.'||n.name) AND l.mode='ShareLock' AND l.granted)) THEN
 RAISE EXCEPTION 'B02 requires preheld SHARE inventory at READ COMMITTED' USING ERRCODE='P22B2'; END IF;
END $$;
CREATE FUNCTION b02_immutable() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
BEGIN RAISE EXCEPTION 'immutable B02 history' USING ERRCODE='P22B1'; END $$;
CREATE FUNCTION b02_source_guard() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
BEGIN
 PERFORM b02_preheld();
 IF NOT EXISTS(SELECT 1 FROM strategy_candidate_captures WHERE id=NEW.capture_id AND xmin=pg_current_xact_id()::xid) THEN
 RAISE EXCEPTION 'late B02 source binding' USING ERRCODE='P22B1'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION b02_capture_closure() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE c strategy_candidate_captures%ROWTYPE; capture uuid;
BEGIN
 PERFORM b02_preheld();
 IF TG_TABLE_NAME='strategy_candidate_captures' THEN capture:=NEW.id; ELSE capture:=NEW.capture_id; END IF;
 SELECT * INTO STRICT c FROM strategy_candidate_captures WHERE id=capture;
 IF NOT EXISTS(SELECT 1 FROM artifact_versions v JOIN artifacts a ON a.id=v.artifact_id
 WHERE v.id=c.artifact_version_id AND a.project_id=c.project_id AND a.artifact_type='research_brief'
 AND v.status IN ('FROZEN','SUPERSEDED') AND v.frozen_at=c.captured_at
 AND v.content_hash=c.artifact_content_hash AND v.locator='sha256:'||c.artifact_content_hash
 AND v.media_type='application/json' AND v.byte_size BETWEEN 1 AND 8388608
 AND v.created_by=c.captured_by AND v.created_at=c.captured_at
 AND a.created_by=c.captured_by AND a.created_at=c.captured_at)
 OR (SELECT count(*) FROM strategy_candidate_sources WHERE capture_id=c.id) NOT BETWEEN 1 AND 100
 OR EXISTS(SELECT 1 FROM strategy_candidate_sources b
 JOIN source_versions v ON v.id=b.source_version_id
 JOIN literature_sources s ON s.id=v.literature_source_id
 LEFT JOIN source_versions current ON current.id=s.current_version_id
 WHERE b.capture_id=c.id AND (
 NOT EXISTS(SELECT 1 FROM literature_source_project_links l WHERE l.literature_source_id=s.id AND l.project_id=c.project_id)
 OR v.status NOT IN ('FROZEN','SUPERSEDED') OR v.frozen_at IS NULL OR v.content_hash IS NULL
 OR s.lifecycle_status<>'ACTIVE' OR v.version_kind='RETRACTED' OR current.version_kind='RETRACTED'
 OR (current.version_kind='CORRECTED' AND current.id<>v.id))) THEN
 RAISE EXCEPTION 'invalid B02 capture closure' USING ERRCODE='P22B2'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION b02_admission_closure() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE valid boolean;
BEGIN
 PERFORM b02_preheld();
 IF NOT EXISTS(SELECT 1 FROM strategy_candidate_captures WHERE id=NEW.capture_id AND project_id=NEW.project_id AND content_hash=NEW.capture_content_hash) THEN
 RAISE EXCEPTION 'invalid B02 capture binding' USING ERRCODE='P22B2'; END IF;
 IF TG_TABLE_NAME='strategy_question_admissions' THEN
 SELECT EXISTS(SELECT 1 FROM research_questions q JOIN research_question_versions v ON v.research_question_id=q.id
 WHERE q.id=NEW.research_question_id AND v.id=NEW.research_question_version_id AND q.project_id=NEW.project_id
 AND q.current_version_id=v.id AND q.xmin=pg_current_xact_id()::xid AND v.xmin=pg_current_xact_id()::xid
 AND q.created_by=NEW.admitted_by AND v.created_by=NEW.admitted_by AND q.created_at=NEW.admitted_at AND v.created_at=NEW.admitted_at
 AND v.version_number=1 AND v.status='DRAFT' AND v.question_text=NEW.question_text AND v.rationale=NEW.rationale
 AND (v.scope IS NULL OR v.scope='null'::jsonb) AND v.content_hash IS NULL AND v.frozen_at IS NULL) INTO valid;
 ELSE
 SELECT EXISTS(SELECT 1 FROM hypotheses h JOIN hypothesis_versions v ON v.hypothesis_id=h.id
 WHERE h.id=NEW.hypothesis_id AND v.id=NEW.hypothesis_version_id AND h.project_id=NEW.project_id
 AND h.research_question_id IS NOT DISTINCT FROM NEW.research_question_id
 AND (h.research_question_id IS NULL OR EXISTS(SELECT 1 FROM research_questions q WHERE q.id=h.research_question_id AND q.project_id=NEW.project_id))
 AND h.current_version_id=v.id AND h.xmin=pg_current_xact_id()::xid AND v.xmin=pg_current_xact_id()::xid
 AND h.created_by=NEW.admitted_by AND v.created_by=NEW.admitted_by AND h.created_at=NEW.admitted_at AND v.created_at=NEW.admitted_at
 AND v.version_number=1 AND v.status='DRAFT' AND v.statement=NEW.statement AND v.rationale=NEW.rationale
 AND v.expected_direction IS NULL AND (v.success_criteria IS NULL OR v.success_criteria='null'::jsonb) AND v.content_hash IS NULL AND v.frozen_at IS NULL) INTO valid;
 END IF;
 IF NOT valid THEN RAISE EXCEPTION 'invalid B02 fresh draft closure' USING ERRCODE='P22B2'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER b02_capture_immutable BEFORE UPDATE OR DELETE ON strategy_candidate_captures FOR EACH ROW EXECUTE FUNCTION b02_immutable();
CREATE CONSTRAINT TRIGGER b02_capture_complete AFTER INSERT ON strategy_candidate_captures DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b02_capture_closure();
CREATE TRIGGER b02_sources_immutable BEFORE UPDATE OR DELETE ON strategy_candidate_sources FOR EACH ROW EXECUTE FUNCTION b02_immutable();
CREATE CONSTRAINT TRIGGER b02_sources_complete AFTER INSERT ON strategy_candidate_sources DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b02_capture_closure();
CREATE TRIGGER b02_q_immutable BEFORE UPDATE OR DELETE ON strategy_question_admissions FOR EACH ROW EXECUTE FUNCTION b02_immutable();
CREATE CONSTRAINT TRIGGER b02_q_complete AFTER INSERT ON strategy_question_admissions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b02_admission_closure();
CREATE TRIGGER b02_h_immutable BEFORE UPDATE OR DELETE ON strategy_hypothesis_admissions FOR EACH ROW EXECUTE FUNCTION b02_immutable();
CREATE CONSTRAINT TRIGGER b02_h_complete AFTER INSERT ON strategy_hypothesis_admissions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b02_admission_closure();
CREATE TRIGGER b02_source_insert_guard BEFORE INSERT ON strategy_candidate_sources FOR EACH ROW EXECUTE FUNCTION b02_source_guard();
    """)


def downgrade() -> None:
    op.execute(r"""
LOCK TABLE strategy_candidate_captures,strategy_candidate_sources,strategy_hypothesis_admissions,strategy_question_admissions IN ACCESS EXCLUSIVE MODE;
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM strategy_candidate_captures) OR EXISTS(SELECT 1 FROM strategy_candidate_sources)
 OR EXISTS(SELECT 1 FROM strategy_hypothesis_admissions) OR EXISTS(SELECT 1 FROM strategy_question_admissions) THEN
 RAISE EXCEPTION 'B02 populated history cannot be downgraded'; END IF;
END $$;
DROP TABLE strategy_hypothesis_admissions,strategy_question_admissions,strategy_candidate_sources,strategy_candidate_captures;
DROP FUNCTION b02_admission_closure(),b02_capture_closure(),b02_source_guard(),b02_immutable(),b02_preheld();
    """)
