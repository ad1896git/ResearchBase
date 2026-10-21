"""B15 immutable local PREPARED packages and direct HUMAN consent roots."""

# ruff: noqa: E501
from alembic import op

revision = "0060_b15_package_preparation"
down_revision = "0059_b13_grant_consumption"
branch_labels = None
depends_on = None

TABLES = (
    "prepared_submission_versions",
    "author_consents",
    "prepared_submission_manifest_items",
    "prepared_submission_events",
)


def _name(prefix, table, column):
    name = f"{prefix}_{table}_{column}"
    if len(name) > 63:
        name = f"{prefix}_ps_manifest_{column}"
    assert len(name) <= 63
    return name


def upgrade():
    for table in TABLES:
        cols = [
            f"id UUID CONSTRAINT pk_{table} PRIMARY KEY",
            "created_at TIMESTAMPTZ NOT NULL",
            f"created_by UUID NOT NULL CONSTRAINT fk_{table}_created_by REFERENCES actors(id) ON DELETE RESTRICT",
        ]
        fks = ["created_by"]
        leading = {"id"}

        def fk(column, target, nullable=False, cols=cols, table=table, fks=fks):
            cols.append(
                f"{column} UUID {'NULL' if nullable else 'NOT NULL'} CONSTRAINT {_name('fk', table, column)} REFERENCES {target}(id) ON DELETE RESTRICT"
            )
            fks.append(column)

        def check(name, expr, cols=cols):
            cols.append(f"CONSTRAINT {name} CHECK ({expr})")

        if table == TABLES[0]:
            fk("publication_id", "publications")
            cols += [
                "version_number INTEGER NOT NULL",
                "manuscript_version_id UUID NOT NULL",
                "authorship_snapshot_id UUID NOT NULL",
                "status VARCHAR(16) NOT NULL",
                "package_manifest_hash CHAR(64) NULL",
                "content_hash CHAR(64) NULL",
                "hash_scheme VARCHAR(32) NOT NULL",
                "frozen_at TIMESTAMPTZ NULL",
                "row_version INTEGER NOT NULL",
                "CONSTRAINT uq_b15_package_parent UNIQUE(publication_id,id)",
                "CONSTRAINT uq_b15_package_number UNIQUE(publication_id,version_number)",
                "CONSTRAINT fk_b15_manuscript_parent FOREIGN KEY(publication_id,manuscript_version_id) REFERENCES manuscript_versions(publication_id,id) ON DELETE RESTRICT",
                "CONSTRAINT fk_b15_snapshot_parent FOREIGN KEY(publication_id,authorship_snapshot_id) REFERENCES authorship_snapshots(publication_id,id) ON DELETE RESTRICT",
            ]
            fks += ["manuscript_version_id", "authorship_snapshot_id"]
            leading.add("publication_id")
            check("ck_b15_package_number", "version_number>0")
            check("ck_b15_package_status", "status IN ('PREPARED','WITHDRAWN')")
            check(
                "ck_b15_package_hash_state",
                "package_manifest_hash IS NULL AND content_hash IS NULL AND frozen_at IS NULL",
            )
            check("ck_b15_package_scheme", "hash_scheme='sha256-cjson-v1'")
            check(
                "ck_b15_package_row_version",
                "(status='PREPARED' AND row_version=1) OR (status='WITHDRAWN' AND row_version=2)",
            )
        elif table == TABLES[1]:
            fk("prepared_submission_version_id", TABLES[0])
            fk("actor_id", "actors")
            fk("evidence_artifact_version_id", "artifact_versions")
            fk("prior_consent_id", "author_consents", True)
            cols += [
                "consent_state VARCHAR(16) NOT NULL",
                "consent_scope VARCHAR(24) NOT NULL",
                "captured_at TIMESTAMPTZ NOT NULL",
                "content_hash CHAR(64) NOT NULL",
                "hash_scheme VARCHAR(32) NOT NULL",
                "CONSTRAINT uq_b15_consent_package UNIQUE(prepared_submission_version_id,id)",
            ]
            leading.add("prepared_submission_version_id")
            check(
                "ck_b15_consent_root",
                "consent_state='GRANTED' AND consent_scope='PREPARED_PACKAGE' AND prior_consent_id IS NULL",
            )
            check("ck_b15_consent_actor", "actor_id=created_by")
            check(
                "ck_b15_consent_hash",
                "content_hash ~ '^[0-9a-f]{64}$' AND hash_scheme='sha256-cjson-v1'",
            )
            check("ck_b15_consent_time", "captured_at=created_at AND isfinite(captured_at)")
        elif table == TABLES[2]:
            fk("prepared_submission_version_id", TABLES[0])
            for column, target in (
                ("artifact_version_id", "artifact_versions"),
                ("source_version_id", "source_versions"),
                ("claim_version_id", "claim_versions"),
                ("scientific_conclusion_version_id", "scientific_conclusion_versions"),
            ):
                fk(column, target, True)
            cols += [
                "author_consent_id UUID NULL",
                "category VARCHAR(24) NOT NULL",
                "ordinal INTEGER NOT NULL",
                "CONSTRAINT fk_b15_manifest_consent FOREIGN KEY(prepared_submission_version_id,author_consent_id) REFERENCES author_consents(prepared_submission_version_id,id) ON DELETE RESTRICT",
                "CONSTRAINT uq_b15_manifest_position UNIQUE(prepared_submission_version_id,category,ordinal)",
            ]
            fks.append("author_consent_id")
            leading.add("prepared_submission_version_id")
            check("ck_b15_manifest_ordinal", "ordinal BETWEEN 0 AND 9999")
            check("ck_b15_manifest_s2", "category<>'AUTHOR_CONSENT' AND author_consent_id IS NULL")
            check(
                "ck_b15_manifest_target",
                "num_nonnulls(artifact_version_id,source_version_id,claim_version_id,scientific_conclusion_version_id,author_consent_id)=1 AND ((category IN ('FIGURE','TABLE') AND artifact_version_id IS NOT NULL) OR (category='CITATION' AND source_version_id IS NOT NULL) OR (category='CLAIM' AND claim_version_id IS NOT NULL) OR (category='CONCLUSION' AND scientific_conclusion_version_id IS NOT NULL) OR (category='AUTHOR_CONSENT' AND author_consent_id IS NOT NULL))",
            )
        else:
            fk("prepared_submission_version_id", TABLES[0])
            fk("actor_id", "actors")
            cols += [
                "prior_status VARCHAR(16) NULL",
                "new_status VARCHAR(16) NOT NULL",
                "occurred_at TIMESTAMPTZ NOT NULL",
                "reason TEXT NULL",
                "CONSTRAINT uq_b15_package_event UNIQUE(prepared_submission_version_id,new_status)",
            ]
            leading.add("prepared_submission_version_id")
            check("ck_b15_event_actor", "actor_id=created_by")
            check("ck_b15_event_time", "occurred_at=created_at AND isfinite(occurred_at)")
            check(
                "ck_b15_event_transition",
                "(prior_status IS NULL AND new_status='PREPARED' AND reason IS NULL) OR (prior_status='PREPARED' AND new_status='WITHDRAWN' AND reason IS NOT NULL)",
            )
            check(
                "ck_b15_event_reason",
                "reason IS NULL OR (length(reason) BETWEEN 1 AND 10000 AND reason ~ '[^[:space:]]' AND reason=normalize(reason,NFC))",
            )
        op.execute(f"CREATE TABLE {table} ({','.join(cols)})")
        for column in fks:
            if column not in leading:
                op.execute(f"CREATE INDEX {_name('ix', table, column)} ON {table}({column})")
    op.execute(SQL)


SQL = r"""
CREATE UNIQUE INDEX uq_author_consents_root ON author_consents(prepared_submission_version_id,actor_id,consent_scope) WHERE prior_consent_id IS NULL;
CREATE UNIQUE INDEX uq_author_consents_successor ON author_consents(prior_consent_id) WHERE prior_consent_id IS NOT NULL;
CREATE INDEX ix_b15_consent_history ON author_consents(prepared_submission_version_id,actor_id,captured_at,id);
CREATE INDEX ix_b15_event_history ON prepared_submission_events(prepared_submission_version_id,occurred_at,id);
CREATE FUNCTION b15_preheld() RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$ BEGIN
 IF current_setting('transaction_isolation')<>'read committed' OR EXISTS(SELECT 1 FROM unnest(ARRAY['actor_subject_bindings','actors','artifact_versions','artifacts','audit_findings','authorship_snapshot_authors','authorship_snapshot_contributions','authorship_snapshot_corresponding_authors','authorship_snapshot_equal_groups','authorship_snapshots','claim_versions','claims','contribution_records','correction_records','dataset_snapshots','datasets','evidence_relations','experiment_spec_versions','experiment_specs','impact_assessments','impact_targets','internal_review_records','literature_evidence','literature_evidence_relations','literature_evidence_review_events','literature_source_project_links','literature_sources','literature_support_snapshots','manuscript_artifact_placements','manuscript_citation_placements','manuscript_claim_placements','manuscript_versions','measurements','metric_definition_versions','metric_definitions','project_membership_events','project_memberships','project_role_assignments','projects','publications','review_issue_events','review_issues','run_artifact_inputs','run_dataset_inputs','runs','scientific_conclusion_claim_inputs','scientific_conclusion_literature_inputs','scientific_conclusion_versions','scientific_conclusions','source_versions','statistical_result_inputs','statistical_results']) n(name) WHERE NOT EXISTS(SELECT 1 FROM pg_locks l WHERE l.pid=pg_backend_pid() AND l.locktype='relation' AND l.relation=to_regclass('public.'||n.name) AND l.mode='ShareLock' AND l.granted)) THEN RAISE EXCEPTION 'B15 preheld inventory required' USING ERRCODE='P15S3'; END IF; END $$;
    CREATE FUNCTION b15_manuscript_structure(identity UUID) RETURNS void LANGUAGE plpgsql AS $$
    DECLARE m manuscript_versions; project UUID; pointer UUID; n BIGINT;
    BEGIN
      SELECT * INTO m FROM manuscript_versions WHERE id=identity;
      IF NOT FOUND THEN RETURN; END IF;
      IF m.status='DRAFT' THEN
        IF m.content_hash IS NOT NULL OR m.placement_set_hash IS NOT NULL OR m.frozen_at IS NOT NULL THEN
          RAISE EXCEPTION 'malformed draft seal' USING ERRCODE='P15S3'; END IF;
        RETURN;
      END IF;
      SELECT project_id,current_manuscript_version_id INTO project,pointer FROM publications WHERE id=m.publication_id;
      IF m.content_hash IS NULL OR m.placement_set_hash IS NULL OR m.frozen_at IS NULL THEN
        RAISE EXCEPTION 'incomplete manuscript seal' USING ERRCODE='P15S3'; END IF;
      IF NOT EXISTS (SELECT 1 FROM artifact_versions v JOIN artifacts a ON a.id=v.artifact_id
        WHERE v.id=m.document_artifact_version_id AND a.project_id=project AND a.artifact_type='manuscript'
          AND v.status IN ('FROZEN','SUPERSEDED') AND v.frozen_at IS NOT NULL AND v.byte_size IS NOT NULL
          AND v.content_hash ~ '^[0-9a-f]{64}$') THEN
        RAISE EXCEPTION 'manuscript document closure' USING ERRCODE='P15S3'; END IF;
      SELECT count(*) INTO n FROM (
        SELECT section_id,ordinal FROM manuscript_claim_placements WHERE manuscript_version_id=identity
        UNION ALL SELECT section_id,ordinal FROM manuscript_citation_placements WHERE manuscript_version_id=identity
        UNION ALL SELECT section_id,ordinal FROM manuscript_artifact_placements WHERE manuscript_version_id=identity) p;
      IF n>10000 THEN RAISE EXCEPTION 'placement cap exceeded' USING ERRCODE='P15S3'; END IF;
      IF EXISTS (SELECT 1 FROM (
        SELECT 'claim' AS kind,section_id,ordinal FROM manuscript_claim_placements WHERE manuscript_version_id=identity
        UNION ALL SELECT 'citation',section_id,ordinal FROM manuscript_citation_placements WHERE manuscript_version_id=identity
        UNION ALL SELECT 'artifact',section_id,ordinal FROM manuscript_artifact_placements WHERE manuscript_version_id=identity) p
        GROUP BY kind,section_id HAVING min(ordinal)<>0 OR max(ordinal)<>count(*)-1 OR count(DISTINCT ordinal)<>count(*)) THEN
        RAISE EXCEPTION 'placement ordinal gaps' USING ERRCODE='P15S3'; END IF;
      IF EXISTS (SELECT 1 FROM manuscript_claim_placements p
        LEFT JOIN claim_versions v ON v.id=p.claim_version_id LEFT JOIN claims c ON c.id=v.claim_id
        LEFT JOIN scientific_conclusion_versions s ON s.id=p.scientific_conclusion_version_id
        LEFT JOIN scientific_conclusions sc ON sc.id=s.scientific_conclusion_id
        WHERE p.manuscript_version_id=identity AND
          ((p.claim_version_id IS NULL)=(p.scientific_conclusion_version_id IS NULL)
          OR (p.claim_version_id IS NOT NULL AND (c.project_id IS DISTINCT FROM project OR v.status NOT IN ('FROZEN','SUPERSEDED') OR v.frozen_at IS NULL OR v.content_hash IS NULL))
          OR (p.scientific_conclusion_version_id IS NOT NULL AND (sc.project_id IS DISTINCT FROM project OR s.status NOT IN ('FROZEN','SUPERSEDED') OR s.frozen_at IS NULL OR s.content_hash IS NULL OR s.support_set_hash IS NULL)))) THEN
        RAISE EXCEPTION 'scientific placement closure' USING ERRCODE='P15S3'; END IF;
      IF EXISTS (SELECT 1 FROM manuscript_citation_placements p LEFT JOIN source_versions v ON v.id=p.source_version_id
        WHERE p.manuscript_version_id=identity AND (v.status NOT IN ('FROZEN','SUPERSEDED') OR v.frozen_at IS NULL OR v.content_hash IS NULL
          OR NOT EXISTS (SELECT 1 FROM literature_source_project_links l WHERE l.literature_source_id=v.literature_source_id AND l.project_id=project))) THEN
        RAISE EXCEPTION 'citation placement closure' USING ERRCODE='P15S3'; END IF;
      IF EXISTS (SELECT 1 FROM manuscript_artifact_placements p LEFT JOIN artifact_versions v ON v.id=p.artifact_version_id
        LEFT JOIN artifacts a ON a.id=v.artifact_id WHERE p.manuscript_version_id=identity
          AND (a.project_id IS DISTINCT FROM project OR v.status NOT IN ('FROZEN','SUPERSEDED') OR v.frozen_at IS NULL OR v.content_hash IS NULL)) THEN
        RAISE EXCEPTION 'artifact placement closure' USING ERRCODE='P15S3'; END IF;
    END $$;

CREATE FUNCTION b15_snapshot_structure(sid UUID) RETURNS void LANGUAGE plpgsql AS $$
DECLARE pub UUID; n integer; lo integer; hi integer;
BEGIN
      SELECT publication_id INTO pub FROM authorship_snapshots WHERE id=sid;
      SELECT count(*),min(ordinal),max(ordinal) INTO n,lo,hi
        FROM authorship_snapshot_authors WHERE authorship_snapshot_id=sid;
      IF n NOT BETWEEN 1 AND 100 OR lo<>1 OR hi<>n
        OR EXISTS (SELECT 1 FROM authorship_snapshot_authors x JOIN actors a ON a.id=x.actor_id
          WHERE x.authorship_snapshot_id=sid AND a.actor_type<>'HUMAN')
      THEN RAISE EXCEPTION 'invalid human author aggregate' USING ERRCODE='P15S3'; END IF;
      SELECT count(*),min(ordinal),max(ordinal) INTO n,lo,hi
        FROM authorship_snapshot_corresponding_authors WHERE authorship_snapshot_id=sid;
      IF n NOT BETWEEN 1 AND 100 OR lo<>0 OR hi<>n-1 THEN
        RAISE EXCEPTION 'invalid corresponding aggregate' USING ERRCODE='P15S3'; END IF;
      IF EXISTS (SELECT 1 FROM authorship_snapshot_equal_groups WHERE authorship_snapshot_id=sid
          GROUP BY group_ordinal HAVING count(*)<2 OR min(ordinal)<>0 OR max(ordinal)<>count(*)-1)
        OR (SELECT count(DISTINCT group_ordinal) FROM authorship_snapshot_equal_groups
          WHERE authorship_snapshot_id=sid) IS DISTINCT FROM
          (SELECT coalesce(max(group_ordinal)+1,0) FROM authorship_snapshot_equal_groups
          WHERE authorship_snapshot_id=sid)
      THEN RAISE EXCEPTION 'invalid equal aggregate' USING ERRCODE='P15S3'; END IF;
      SELECT count(*),min(ordinal),max(ordinal) INTO n,lo,hi
        FROM authorship_snapshot_contributions WHERE authorship_snapshot_id=sid;
      IF n NOT BETWEEN 1 AND 1000 OR lo<>0 OR hi<>n-1
        OR EXISTS (SELECT 1 FROM authorship_snapshot_contributions x
          JOIN contribution_records c ON c.id=x.contribution_record_id
          WHERE x.authorship_snapshot_id=sid AND c.publication_id<>pub)
        OR EXISTS (SELECT 1 FROM authorship_snapshot_authors a
          WHERE a.authorship_snapshot_id=sid AND NOT EXISTS (
            SELECT 1 FROM authorship_snapshot_contributions x JOIN contribution_records c
              ON c.id=x.contribution_record_id
            WHERE x.authorship_snapshot_id=sid AND c.actor_id=a.actor_id))
      THEN RAISE EXCEPTION 'invalid contribution coverage' USING ERRCODE='P15S3'; END IF;
END $$;

CREATE FUNCTION b15_projection(mid UUID) RETURNS TABLE(category text,ordinal bigint,target UUID) LANGUAGE SQL STABLE AS $$
 SELECT category,row_number() OVER(PARTITION BY category ORDER BY section_id COLLATE "C",placement_ordinal)-1,target FROM (
 SELECT artifact_role::text AS category,section_id,ordinal AS placement_ordinal,artifact_version_id AS target FROM manuscript_artifact_placements WHERE manuscript_version_id=mid
 UNION ALL SELECT 'CITATION',section_id,ordinal,source_version_id FROM manuscript_citation_placements WHERE manuscript_version_id=mid
 UNION ALL SELECT CASE WHEN claim_version_id IS NOT NULL THEN 'CLAIM' ELSE 'CONCLUSION' END,section_id,ordinal,coalesce(claim_version_id,scientific_conclusion_version_id) FROM manuscript_claim_placements WHERE manuscript_version_id=mid) p
$$;
CREATE FUNCTION b15_package_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE m manuscript_versions; context jsonb; observed_at timestamptz;
BEGIN
 PERFORM b15_preheld();
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'immutable package' USING ERRCODE='P15S1'; END IF;
 IF TG_OP='UPDATE' THEN
  IF (SELECT xmin=pg_current_xact_id()::xid FROM prepared_submission_versions WHERE id=OLD.id) OR OLD.status<>'PREPARED' OR NEW.status<>'WITHDRAWN' OR NEW.row_version<>OLD.row_version+1
   OR (to_jsonb(NEW)-ARRAY['status','row_version']) IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['status','row_version']) THEN
   RAISE EXCEPTION 'immutable package context' USING ERRCODE='P15S1'; END IF;
  context:=nullif(current_setting('researchbase.b15_withdrawal',true),'')::jsonb;
  observed_at:=(context->>'at')::timestamptz;
  IF context->>'package' IS DISTINCT FROM NEW.id::text OR context->>'actor' IS NULL
   OR context->>'reason' IS NULL OR observed_at IS NULL OR NOT isfinite(observed_at)
   OR observed_at<transaction_timestamp() OR observed_at>clock_timestamp() THEN
   RAISE EXCEPTION 'missing observed withdrawal context' USING ERRCODE='P15S3'; END IF;
  RETURN NEW;
 END IF;
 IF NEW.status<>'PREPARED' OR NEW.row_version<>1 THEN RAISE EXCEPTION 'closed package state' USING ERRCODE='P15S2'; END IF;
 SELECT * INTO m FROM manuscript_versions WHERE id=NEW.manuscript_version_id;
 IF m.id IS NULL OR m.publication_id IS DISTINCT FROM NEW.publication_id OR m.status<>'FROZEN'
 OR NOT EXISTS(SELECT 1 FROM authorship_snapshots WHERE id=NEW.authorship_snapshot_id AND publication_id=NEW.publication_id) THEN
 RAISE EXCEPTION 'package parent closure' USING ERRCODE='P15S3'; END IF;
 IF EXISTS(SELECT 1 FROM authorship_snapshots WHERE id=NEW.authorship_snapshot_id AND xmin=pg_current_xact_id()::xid) THEN
 RAISE EXCEPTION 'already sealed authorship context required' USING ERRCODE='P15S3'; END IF;
 PERFORM b15_manuscript_structure(m.id); PERFORM b15_snapshot_structure(NEW.authorship_snapshot_id);
 RETURN NEW;
END $$;
CREATE TRIGGER b15_package_guard BEFORE INSERT OR UPDATE OR DELETE ON prepared_submission_versions FOR EACH ROW EXECUTE FUNCTION b15_package_guard();
-- The immutable event is the transition observation. Caller-writable GUCs are
-- inputs only, never deferred evidence. This trigger precedes immediate package
-- constraint triggers lexically and runs after the new parent row is visible.
CREATE FUNCTION b15_capture_withdrawal() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE context jsonb;
BEGIN
 context:=current_setting('researchbase.b15_withdrawal')::jsonb;
 INSERT INTO prepared_submission_events(id,created_at,created_by,prepared_submission_version_id,
   prior_status,new_status,actor_id,occurred_at,reason)
 VALUES(gen_random_uuid(),(context->>'at')::timestamptz,(context->>'actor')::uuid,NEW.id,
   'PREPARED','WITHDRAWN',(context->>'actor')::uuid,(context->>'at')::timestamptz,context->>'reason');
 RETURN NULL;
END $$;
CREATE TRIGGER b15_capture_withdrawal AFTER UPDATE ON prepared_submission_versions
 FOR EACH ROW EXECUTE FUNCTION b15_capture_withdrawal();
CREATE FUNCTION b15_manifest_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p prepared_submission_versions; fresh boolean;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'immutable manifest' USING ERRCODE='P15S1'; END IF;
 PERFORM b15_preheld();
 SELECT * INTO p FROM prepared_submission_versions WHERE id=NEW.prepared_submission_version_id FOR UPDATE;
 SELECT xmin=pg_current_xact_id()::xid INTO fresh FROM prepared_submission_versions WHERE id=p.id;
 IF NOT coalesce(fresh,false) OR p.status<>'PREPARED' OR p.row_version<>1 OR NEW.created_at IS DISTINCT FROM p.created_at OR NEW.created_by IS DISTINCT FROM p.created_by THEN
 RAISE EXCEPTION 'sealed manifest' USING ERRCODE='P15S1'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER b15_manifest_guard BEFORE INSERT OR UPDATE OR DELETE ON prepared_submission_manifest_items FOR EACH ROW EXECUTE FUNCTION b15_manifest_guard();
CREATE FUNCTION b15_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'immutable B15 history' USING ERRCODE='P15S1'; END $$;
CREATE TRIGGER b15_immutable_consents BEFORE UPDATE OR DELETE ON author_consents FOR EACH ROW EXECUTE FUNCTION b15_immutable();
CREATE TRIGGER b15_immutable_events BEFORE UPDATE OR DELETE ON prepared_submission_events FOR EACH ROW EXECUTE FUNCTION b15_immutable();
CREATE FUNCTION b15_consent_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p prepared_submission_versions; pid UUID;
BEGIN
 PERFORM b15_preheld();
 SELECT * INTO p FROM prepared_submission_versions WHERE id=NEW.prepared_submission_version_id FOR UPDATE;
 IF p.status IS DISTINCT FROM 'PREPARED' OR NEW.consent_state<>'GRANTED' OR NEW.consent_scope<>'PREPARED_PACKAGE' OR NEW.prior_consent_id IS NOT NULL THEN
 RAISE EXCEPTION 'closed root consent state' USING ERRCODE='P15S2'; END IF;
 SELECT project_id INTO pid FROM publications WHERE id=p.publication_id;
 IF NEW.actor_id IS DISTINCT FROM NEW.created_by OR NOT EXISTS(SELECT 1 FROM authorship_snapshot_authors s JOIN actors a ON a.id=s.actor_id WHERE s.authorship_snapshot_id=p.authorship_snapshot_id AND a.id=NEW.actor_id AND a.actor_type='HUMAN' AND a.retired_at IS NULL)
 OR NOT EXISTS(SELECT 1 FROM artifact_versions v JOIN artifacts a ON a.id=v.artifact_id WHERE v.id=NEW.evidence_artifact_version_id AND a.project_id=pid AND v.status IN ('FROZEN','SUPERSEDED') AND v.frozen_at IS NOT NULL AND v.content_hash ~ '^[0-9a-f]{64}$') THEN
 RAISE EXCEPTION 'root consent provenance' USING ERRCODE='P15S3'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER b15_consent_guard BEFORE INSERT ON author_consents FOR EACH ROW EXECUTE FUNCTION b15_consent_guard();
CREATE FUNCTION b15_manifest_complete() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p prepared_submission_versions; identity UUID;
BEGIN
 IF TG_TABLE_NAME='prepared_submission_versions' THEN identity:=NEW.id; ELSE identity:=NEW.prepared_submission_version_id; END IF;
 SELECT * INTO p FROM prepared_submission_versions WHERE id=identity;
 PERFORM b15_manuscript_structure(p.manuscript_version_id); PERFORM b15_snapshot_structure(p.authorship_snapshot_id);
 IF (SELECT count(*) FROM prepared_submission_manifest_items WHERE prepared_submission_version_id=identity)+(SELECT count(*) FROM authorship_snapshot_authors WHERE authorship_snapshot_id=p.authorship_snapshot_id)>10000
 OR EXISTS(SELECT 1 FROM b15_projection(p.manuscript_version_id) WHERE category NOT IN ('FIGURE','TABLE','CITATION','CLAIM','CONCLUSION'))
 OR EXISTS((SELECT category,ordinal,target FROM b15_projection(p.manuscript_version_id)) EXCEPT ALL (SELECT category,ordinal,coalesce(artifact_version_id,source_version_id,claim_version_id,scientific_conclusion_version_id) FROM prepared_submission_manifest_items WHERE prepared_submission_version_id=identity))
 OR EXISTS((SELECT category,ordinal,coalesce(artifact_version_id,source_version_id,claim_version_id,scientific_conclusion_version_id) FROM prepared_submission_manifest_items WHERE prepared_submission_version_id=identity) EXCEPT ALL (SELECT category,ordinal,target FROM b15_projection(p.manuscript_version_id))) THEN
 RAISE EXCEPTION 'package occurrence aggregate' USING ERRCODE='P15S3'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER b15_manifest_complete_package AFTER INSERT ON prepared_submission_versions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b15_manifest_complete();
CREATE CONSTRAINT TRIGGER b15_manifest_complete_items AFTER INSERT ON prepared_submission_manifest_items DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b15_manifest_complete();
CREATE FUNCTION b15_package_events() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p prepared_submission_versions; identity UUID; fresh boolean; e prepared_submission_events;
BEGIN
 PERFORM b15_preheld();
 IF TG_TABLE_NAME='prepared_submission_versions' THEN identity:=NEW.id; ELSE identity:=NEW.prepared_submission_version_id; END IF;
 SELECT * INTO p FROM prepared_submission_versions WHERE id=identity;
 IF (SELECT count(*) FROM prepared_submission_events WHERE prepared_submission_version_id=identity)<>p.row_version
 OR NOT EXISTS(SELECT 1 FROM prepared_submission_events WHERE prepared_submission_version_id=identity AND prior_status IS NULL AND new_status='PREPARED' AND actor_id=p.created_by AND occurred_at=p.created_at) THEN
 RAISE EXCEPTION 'package event aggregate' USING ERRCODE='P15S3'; END IF;
 IF p.status='WITHDRAWN' THEN
  SELECT * INTO e FROM prepared_submission_events WHERE prepared_submission_version_id=identity AND prior_status='PREPARED' AND new_status='WITHDRAWN';
  IF e.id IS NULL OR e.occurred_at<p.created_at THEN RAISE EXCEPTION 'missing withdrawal event' USING ERRCODE='P15S3'; END IF;
  SELECT xmin=pg_current_xact_id()::xid INTO fresh FROM prepared_submission_versions WHERE id=identity;
  IF TG_TABLE_NAME='prepared_submission_events' AND NOT fresh THEN RAISE EXCEPTION 'forged event' USING ERRCODE='P15S3'; END IF;

 END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER b15_package_events_package AFTER INSERT OR UPDATE ON prepared_submission_versions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b15_package_events();
CREATE CONSTRAINT TRIGGER b15_package_events_events AFTER INSERT ON prepared_submission_events DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b15_package_events();
"""


def downgrade():
    for table in TABLES:
        op.execute(f"LOCK TABLE {table} IN ACCESS EXCLUSIVE MODE")
    predicate = " OR ".join(f"EXISTS(SELECT 1 FROM {t})" for t in TABLES)
    op.execute(
        f"DO $$ BEGIN IF {predicate} THEN RAISE EXCEPTION 'retained package history prevents downgrade'; END IF; END $$"
    )
    for table in reversed(TABLES):
        op.execute(f"DROP TABLE {table}")
    for function in (
        "b15_package_events()",
        "b15_capture_withdrawal()",
        "b15_manifest_complete()",
        "b15_consent_guard()",
        "b15_immutable()",
        "b15_manifest_guard()",
        "b15_package_guard()",
        "b15_projection(UUID)",
        "b15_snapshot_structure(UUID)",
        "b15_manuscript_structure(UUID)",
        "b15_preheld()",
    ):
        op.execute(f"DROP FUNCTION {function}")
