"""Immutable first-slice coverage, prior art and inconclusive assessments."""

# ruff: noqa: E501
from alembic import op

revision = "0047_pr2_18_novelty_prior_art"
down_revision = "0046_pr2_17_authorship"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(r"""
    CREATE FUNCTION pr218_valid_providers(v JSONB) RETURNS BOOLEAN
      IMMUTABLE STRICT LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE item JSONB; previous TEXT; value TEXT;
    BEGIN
      IF jsonb_typeof(v)<>'array' THEN RETURN FALSE; END IF;
      FOR item IN SELECT * FROM jsonb_array_elements(v) LOOP
        IF jsonb_typeof(item)<>'string' THEN RETURN FALSE; END IF;
        value:=item#>>'{}';
        IF length(btrim(value))=0 OR value<>normalize(value,NFC)
          OR (previous IS NOT NULL AND previous COLLATE "C">=value COLLATE "C") THEN RETURN FALSE; END IF;
        previous:=value;
      END LOOP; RETURN TRUE;
    END $$;
    CREATE FUNCTION pr218_valid_time_scope(v JSONB) RETURNS BOOLEAN
      IMMUTABLE STRICT LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE a DATE; b DATE;
    BEGIN
      IF jsonb_typeof(v)<>'object' OR NOT v ?& ARRAY['from','through']
        OR (SELECT count(*) FROM jsonb_object_keys(v))<>2 THEN RETURN FALSE; END IF;
      IF (v->>'from') IS NULL AND (v->>'through') IS NULL THEN RETURN FALSE; END IF;
      IF (jsonb_typeof(v->'from') NOT IN ('string','null')) OR
         (jsonb_typeof(v->'through') NOT IN ('string','null')) THEN RETURN FALSE; END IF;
      IF (v->>'from') IS NOT NULL THEN
        IF v->>'from' !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN RETURN FALSE; END IF;
        a:=(v->>'from')::date;
        IF to_char(a,'YYYY-MM-DD')<>v->>'from' THEN RETURN FALSE; END IF;
      END IF;
      IF (v->>'through') IS NOT NULL THEN
        IF v->>'through' !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN RETURN FALSE; END IF;
        b:=(v->>'through')::date;
        IF to_char(b,'YYYY-MM-DD')<>v->>'through' THEN RETURN FALSE; END IF;
      END IF;
      RETURN a IS NULL OR b IS NULL OR a<=b;
    EXCEPTION WHEN OTHERS THEN RETURN FALSE;
    END $$;
CREATE TABLE search_coverage (
  id UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  created_by UUID NOT NULL,
  search_plan_version_id UUID NOT NULL,
  providers JSONB NOT NULL,
  query_count INT NOT NULL,
  result_count INT NOT NULL,
  resolved_source_count INT NOT NULL,
  time_scope JSONB NULL,
  coverage_limitations TEXT NOT NULL,
  content_hash CHAR(64) NOT NULL,
  hash_scheme VARCHAR(32) NOT NULL,
  CONSTRAINT pk_pr218_coverage PRIMARY KEY (id),
  CONSTRAINT fk_pr218_coverage_created_by FOREIGN KEY (created_by)
    REFERENCES actors(id) ON DELETE RESTRICT,
  CONSTRAINT fk_pr218_coverage_search_plan_version_id FOREIGN KEY (search_plan_version_id)
    REFERENCES literature_search_plan_versions(id) ON DELETE RESTRICT,
  CONSTRAINT ck_pr218_coverage_counts CHECK (query_count >= 0 AND result_count >= 0 AND resolved_source_count BETWEEN 0 AND result_count),
  CONSTRAINT ck_pr218_coverage_providers CHECK (pr218_valid_providers(providers)),
  CONSTRAINT ck_pr218_coverage_time_scope CHECK (time_scope IS NULL OR pr218_valid_time_scope(time_scope)),
  CONSTRAINT ck_pr218_coverage_text CHECK
    (length(btrim(coverage_limitations)) > 0 AND char_length(coverage_limitations) BETWEEN 1 AND 16384),
  CONSTRAINT ck_pr218_coverage_hash CHECK (content_hash ~ '^[0-9a-f]{64}$'),
  CONSTRAINT ck_pr218_coverage_scheme CHECK (hash_scheme = 'sha256-cjson-v1')
);
CREATE INDEX ix_pr218_coverage_created_by ON search_coverage (created_by);
CREATE INDEX ix_pr218_coverage_search_plan_version_id ON search_coverage (search_plan_version_id);
CREATE TABLE search_coverage_executions (
  id UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  created_by UUID NOT NULL,
  search_coverage_id UUID NOT NULL,
  search_execution_id UUID NOT NULL,
  CONSTRAINT pk_pr218_coverage_execution PRIMARY KEY (id),
  CONSTRAINT fk_pr218_coverage_execution_created_by FOREIGN KEY (created_by)
    REFERENCES actors(id) ON DELETE RESTRICT,
  CONSTRAINT fk_pr218_coverage_execution_search_coverage_id FOREIGN KEY (search_coverage_id)
    REFERENCES search_coverage(id) ON DELETE RESTRICT,
  CONSTRAINT fk_pr218_coverage_execution_search_execution_id FOREIGN KEY (search_execution_id)
    REFERENCES literature_search_executions(id) ON DELETE RESTRICT,
  CONSTRAINT uq_pr218_coverage_execution_pair UNIQUE (search_coverage_id, search_execution_id)
);
CREATE INDEX ix_pr218_coverage_execution_created_by ON search_coverage_executions (created_by);
CREATE INDEX ix_pr218_coverage_execution_search_execution_id ON search_coverage_executions (search_execution_id);
CREATE TABLE prior_art_relations (
  id UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  created_by UUID NOT NULL,
  claim_version_id UUID NOT NULL,
  source_version_id UUID NOT NULL,
  relation VARCHAR(32) NOT NULL,
  rationale TEXT NOT NULL,
  assessed_by UUID NOT NULL,
  content_hash CHAR(64) NOT NULL,
  hash_scheme VARCHAR(32) NOT NULL,
  CONSTRAINT pk_pr218_prior_art PRIMARY KEY (id),
  CONSTRAINT fk_pr218_prior_art_created_by FOREIGN KEY (created_by)
    REFERENCES actors(id) ON DELETE RESTRICT,
  CONSTRAINT fk_pr218_prior_art_claim_version_id FOREIGN KEY (claim_version_id)
    REFERENCES claim_versions(id) ON DELETE RESTRICT,
  CONSTRAINT fk_pr218_prior_art_source_version_id FOREIGN KEY (source_version_id)
    REFERENCES source_versions(id) ON DELETE RESTRICT,
  CONSTRAINT fk_pr218_prior_art_assessed_by FOREIGN KEY (assessed_by)
    REFERENCES actors(id) ON DELETE RESTRICT,
  CONSTRAINT ck_pr218_prior_art_relation CHECK (relation IN ('IDENTICAL','HIGHLY_SIMILAR','PARTIAL_OVERLAP','RELATED','CONTRASTING','UNCLEAR')),
  CONSTRAINT ck_pr218_prior_art_assessor CHECK (assessed_by = created_by),
  CONSTRAINT ck_pr218_prior_art_text CHECK
    (length(btrim(rationale)) > 0 AND char_length(rationale) BETWEEN 1 AND 16384),
  CONSTRAINT ck_pr218_prior_art_hash CHECK (content_hash ~ '^[0-9a-f]{64}$'),
  CONSTRAINT ck_pr218_prior_art_scheme CHECK (hash_scheme = 'sha256-cjson-v1')
);
CREATE INDEX ix_pr218_prior_art_created_by ON prior_art_relations (created_by);
CREATE INDEX ix_pr218_prior_art_claim_version_id ON prior_art_relations (claim_version_id);
CREATE INDEX ix_pr218_prior_art_source_version_id ON prior_art_relations (source_version_id);
CREATE INDEX ix_pr218_prior_art_assessed_by ON prior_art_relations (assessed_by);
CREATE TABLE prior_art_evidence_inputs (
  id UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  created_by UUID NOT NULL,
  prior_art_relation_id UUID NOT NULL,
  literature_evidence_id UUID NOT NULL,
  CONSTRAINT pk_pr218_prior_art_input PRIMARY KEY (id),
  CONSTRAINT fk_pr218_prior_art_input_created_by FOREIGN KEY (created_by)
    REFERENCES actors(id) ON DELETE RESTRICT,
  CONSTRAINT fk_pr218_prior_art_input_prior_art_relation_id FOREIGN KEY (prior_art_relation_id)
    REFERENCES prior_art_relations(id) ON DELETE RESTRICT,
  CONSTRAINT fk_pr218_prior_art_input_literature_evidence_id FOREIGN KEY (literature_evidence_id)
    REFERENCES literature_evidence(id) ON DELETE RESTRICT,
  CONSTRAINT uq_pr218_prior_art_input_pair UNIQUE (prior_art_relation_id, literature_evidence_id)
);
CREATE INDEX ix_pr218_prior_art_input_created_by ON prior_art_evidence_inputs (created_by);
CREATE INDEX ix_pr218_prior_art_input_literature_evidence_id ON prior_art_evidence_inputs (literature_evidence_id);
CREATE TABLE novelty_assessments (
  id UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  created_by UUID NOT NULL,
  claim_version_id UUID NOT NULL,
  search_coverage_id UUID NOT NULL,
  assessment VARCHAR(40) NOT NULL,
  limitations TEXT NOT NULL,
  assessed_by UUID NOT NULL,
  supersedes_assessment_id UUID NULL,
  content_hash CHAR(64) NOT NULL,
  hash_scheme VARCHAR(32) NOT NULL,
  CONSTRAINT pk_pr218_novelty PRIMARY KEY (id),
  CONSTRAINT fk_pr218_novelty_created_by FOREIGN KEY (created_by)
    REFERENCES actors(id) ON DELETE RESTRICT,
  CONSTRAINT fk_pr218_novelty_claim_version_id FOREIGN KEY (claim_version_id)
    REFERENCES claim_versions(id) ON DELETE RESTRICT,
  CONSTRAINT fk_pr218_novelty_search_coverage_id FOREIGN KEY (search_coverage_id)
    REFERENCES search_coverage(id) ON DELETE RESTRICT,
  CONSTRAINT fk_pr218_novelty_assessed_by FOREIGN KEY (assessed_by)
    REFERENCES actors(id) ON DELETE RESTRICT,
  CONSTRAINT fk_pr218_novelty_supersedes_assessment_id FOREIGN KEY (supersedes_assessment_id)
    REFERENCES novelty_assessments(id) ON DELETE RESTRICT,
  CONSTRAINT ck_pr218_novelty_outcome CHECK (assessment IN ('NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE','CLOSE_PRIOR_ART_FOUND','INCONCLUSIVE')),
  CONSTRAINT ck_pr218_novelty_initial_slice CHECK (assessment = 'INCONCLUSIVE'),
  CONSTRAINT ck_pr218_novelty_not_self CHECK (supersedes_assessment_id IS NULL OR supersedes_assessment_id <> id),
  CONSTRAINT ck_pr218_novelty_assessor CHECK (assessed_by = created_by),
  CONSTRAINT ck_pr218_novelty_text CHECK
    (length(btrim(limitations)) > 0 AND char_length(limitations) BETWEEN 1 AND 16384),
  CONSTRAINT ck_pr218_novelty_hash CHECK (content_hash ~ '^[0-9a-f]{64}$'),
  CONSTRAINT ck_pr218_novelty_scheme CHECK (hash_scheme = 'sha256-cjson-v1')
);
CREATE INDEX ix_pr218_novelty_created_by ON novelty_assessments (created_by);
CREATE INDEX ix_pr218_novelty_claim_version_id ON novelty_assessments (claim_version_id);
CREATE INDEX ix_pr218_novelty_search_coverage_id ON novelty_assessments (search_coverage_id);
CREATE INDEX ix_pr218_novelty_assessed_by ON novelty_assessments (assessed_by);
CREATE UNIQUE INDEX uq_pr218_novelty_predecessor
  ON novelty_assessments (supersedes_assessment_id)
  WHERE supersedes_assessment_id IS NOT NULL;
    """)
    op.execute(r"""
    CREATE FUNCTION pr218_immutable() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
    BEGIN RAISE EXCEPTION 'immutable novelty record' USING ERRCODE='P17D1'; END $$;
    """)
    op.execute(r"""
    CREATE FUNCTION pr218_source_valid(vid UUID,pid UUID) RETURNS BOOLEAN LANGUAGE sql SET search_path = pg_catalog, public, pg_temp AS $$
      SELECT EXISTS(SELECT 1 FROM source_versions v
        JOIN literature_sources s ON s.id=v.literature_source_id
        JOIN literature_source_project_links l ON l.literature_source_id=s.id AND l.project_id=pid
        LEFT JOIN source_versions current ON current.id=s.current_version_id
        WHERE v.id=vid AND v.status IN ('FROZEN','SUPERSEDED') AND v.frozen_at IS NOT NULL
          AND v.content_hash ~ '^[0-9a-f]{64}$' AND v.hash_scheme='sha256-cjson-v1'
          AND v.version_kind<>'RETRACTED' AND current.version_kind IS DISTINCT FROM 'RETRACTED'
          AND NOT (current.version_kind='CORRECTED' AND current.id<>v.id))
    $$;
    CREATE FUNCTION pr218_claim_valid(vid UUID) RETURNS BOOLEAN LANGUAGE sql SET search_path = pg_catalog, public, pg_temp AS $$
      SELECT EXISTS(SELECT 1 FROM claim_versions v JOIN claims c ON c.id=v.claim_id
        WHERE v.id=vid AND v.status IN ('FROZEN','SUPERSEDED') AND v.frozen_at IS NOT NULL
          AND v.content_hash ~ '^[0-9a-f]{64}$' AND NOT EXISTS(
            SELECT 1 FROM correction_records WHERE project_id=c.project_id
              AND lower(target_type)='claim_version' AND target_id=v.id)
          AND NOT EXISTS(SELECT 1 FROM impact_targets t
            JOIN impact_assessments a ON a.id=t.impact_assessment_id
            LEFT JOIN audit_findings f ON f.id=a.audit_finding_id
            WHERE a.project_id=c.project_id AND lower(t.target_type)='claim_version'
              AND t.target_id=v.id AND lower(f.status) IS DISTINCT FROM 'dismissed'
              AND lower(a.conclusion)<>'no_impact'))
    $$;
    """)
    op.execute(r"""
CREATE FUNCTION pr218_lock_tables() RETURNS void LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$ BEGIN LOCK TABLE actor_subject_bindings,actors,artifact_versions,artifacts,audit_findings,claim_versions,claims,correction_records,datasets,experiment_spec_versions,experiment_specs,impact_assessments,impact_targets,literature_evidence,literature_evidence_review_events,literature_search_execution_events,literature_search_executions,literature_search_plan_versions,literature_search_plans,literature_search_provider_attempts,literature_source_project_links,literature_sources,metadata_observations,metric_definition_versions,metric_definitions,project_membership_events,project_memberships,project_role_assignments,projects,runs,scientific_conclusions,search_query_records,search_result_records,search_result_resolutions,source_versions IN SHARE MODE; END $$;
CREATE FUNCTION pr218_capture_prelocked() RETURNS BOOLEAN LANGUAGE sql SET search_path = pg_catalog, public, pg_temp AS $$ SELECT current_setting('transaction_isolation')='read committed' AND NOT EXISTS (SELECT 1 FROM unnest(ARRAY['actor_subject_bindings','actors','artifact_versions','artifacts','audit_findings','claim_versions','claims','correction_records','datasets','experiment_spec_versions','experiment_specs','impact_assessments','impact_targets','literature_evidence','literature_evidence_review_events','literature_search_execution_events','literature_search_executions','literature_search_plan_versions','literature_search_plans','literature_search_provider_attempts','literature_source_project_links','literature_sources','metadata_observations','metric_definition_versions','metric_definitions','project_membership_events','project_memberships','project_role_assignments','projects','runs','scientific_conclusions','search_query_records','search_result_records','search_result_resolutions','source_versions']) AS names(name) WHERE NOT EXISTS(SELECT 1 FROM pg_locks WHERE pid=pg_backend_pid() AND locktype='relation' AND relation=to_regclass(names.name) AND mode='ShareLock' AND granted)) $$;
    """)
    op.execute(r"""
    CREATE FUNCTION pr218_parent_guard() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE pid UUID; other UUID;
    BEGIN
      IF TG_TABLE_NAME='search_coverage' THEN
        IF NOT pr218_capture_prelocked() THEN
          RAISE EXCEPTION 'coverage requires read committed and preheld SHARE locks' USING ERRCODE='P17D3'; END IF;
        IF NOT EXISTS(SELECT 1 FROM literature_search_plan_versions v
          WHERE v.id=NEW.search_plan_version_id AND v.status IN ('FROZEN','SUPERSEDED')
            AND v.frozen_at IS NOT NULL AND v.content_hash ~ '^[0-9a-f]{64}$') THEN
          RAISE EXCEPTION 'exact frozen plan required' USING ERRCODE='P17D3'; END IF;
      ELSE
        PERFORM 1 FROM claim_versions WHERE id=NEW.claim_version_id FOR UPDATE;
        PERFORM pr218_lock_tables();
        IF NOT pr218_claim_valid(NEW.claim_version_id) THEN
          RAISE EXCEPTION 'valid frozen claim required' USING ERRCODE='P17D3'; END IF;
        SELECT c.project_id INTO pid FROM claims c JOIN claim_versions v ON v.claim_id=c.id WHERE v.id=NEW.claim_version_id;
        IF TG_TABLE_NAME='prior_art_relations' THEN
          IF NOT pr218_source_valid(NEW.source_version_id,pid) THEN
            RAISE EXCEPTION 'valid exact project source required' USING ERRCODE='P17D3'; END IF;
        ELSE
          SELECT p.project_id INTO other FROM search_coverage c
            JOIN literature_search_plan_versions v ON v.id=c.search_plan_version_id
            JOIN literature_search_plans p ON p.id=v.plan_id WHERE c.id=NEW.search_coverage_id;
          IF other IS DISTINCT FROM pid THEN RAISE EXCEPTION 'coverage scope mismatch' USING ERRCODE='P17D3'; END IF;
        END IF;
      END IF;
      RETURN NEW;
    END $$;
    CREATE FUNCTION pr218_child_guard() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE parent_xid BIGINT; author UUID; source UUID; pid UUID; plan UUID;
    BEGIN
      IF TG_TABLE_NAME='search_coverage_executions' THEN
        IF NOT pr218_capture_prelocked() THEN RAISE EXCEPTION 'capture locks required' USING ERRCODE='P17D3'; END IF;
        SELECT xmin::text::bigint,created_by,search_plan_version_id INTO parent_xid,author,plan
          FROM search_coverage WHERE id=NEW.search_coverage_id;
        IF NOT EXISTS(SELECT 1 FROM literature_search_executions e
          JOIN literature_search_plan_versions v ON v.id=plan JOIN literature_search_plans p ON p.id=v.plan_id
          WHERE e.id=NEW.search_execution_id AND e.search_plan_version_id=plan AND e.project_id=p.project_id
            AND e.status IN ('SUCCEEDED','FAILED','CANCELLED','UNKNOWN') AND e.finished_at IS NOT NULL) THEN
          RAISE EXCEPTION 'terminal same plan execution required' USING ERRCODE='P17D3'; END IF;
      ELSE
        SELECT p.xmin::text::bigint,p.created_by,p.source_version_id,c.project_id
          INTO parent_xid,author,source,pid FROM prior_art_relations p
          JOIN claim_versions v ON v.id=p.claim_version_id JOIN claims c ON c.id=v.claim_id
          WHERE p.id=NEW.prior_art_relation_id;
        IF NOT EXISTS(SELECT 1 FROM literature_evidence e WHERE e.id=NEW.literature_evidence_id
          AND e.project_id=pid AND e.source_version_id=source AND e.review_status='VERIFIED'
          AND e.content_hash ~ '^[0-9a-f]{64}$' AND EXISTS(
            SELECT 1 FROM literature_evidence_review_events r JOIN actors a ON a.id=r.reviewed_by
            WHERE r.id=(SELECT id FROM literature_evidence_review_events WHERE literature_evidence_id=e.id ORDER BY reviewed_at DESC,id DESC LIMIT 1)
              AND r.new_status='VERIFIED' AND a.actor_type='HUMAN' AND r.reviewed_by<>e.created_by)) THEN
          RAISE EXCEPTION 'independently verified exact evidence required' USING ERRCODE='P17D3'; END IF;
      END IF;
      IF parent_xid IS DISTINCT FROM pg_current_xact_id()::text::bigint THEN
        RAISE EXCEPTION 'sealed child set' USING ERRCODE='P17D1'; END IF;
      IF author IS DISTINCT FROM NEW.created_by THEN RAISE EXCEPTION 'child author mismatch' USING ERRCODE='P17D3'; END IF;
      RETURN NEW;
    END $$;
    CREATE FUNCTION pr218_complete_coverage() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE cid UUID; c search_coverage; n INT; q INT; r INT; resolved INT; providers JSONB; scope JSONB;
    BEGIN
      IF TG_TABLE_NAME='search_coverage' THEN cid:=NEW.id; ELSE cid:=NEW.search_coverage_id; END IF;
      SELECT * INTO c FROM search_coverage WHERE id=cid;
      SELECT count(*) INTO n FROM search_coverage_executions WHERE search_coverage_id=cid;
      IF n NOT BETWEEN 1 AND 100 OR EXISTS(
        SELECT 1 FROM search_coverage_executions b JOIN literature_search_executions e ON e.id=b.search_execution_id
        WHERE b.search_coverage_id=cid AND (e.status NOT IN ('SUCCEEDED','FAILED','CANCELLED','UNKNOWN')
          OR e.search_plan_version_id<>c.search_plan_version_id OR e.finished_at IS NULL
          OR NOT EXISTS(SELECT 1 FROM literature_search_execution_events event WHERE event.execution_id=e.id AND event.kind='FINISHED' AND event.new_status=e.status)
          OR EXISTS(SELECT 1 FROM literature_search_provider_attempts a WHERE a.execution_id=e.id AND a.status='RESERVED'))) THEN
        RAISE EXCEPTION 'complete terminal coverage required' USING ERRCODE='P17D3'; END IF;
      SELECT count(*),coalesce(jsonb_agg(provider ORDER BY provider COLLATE "C"),'[]'::jsonb) INTO n,providers
        FROM (SELECT DISTINCT normalize(q.provider_id,NFC) AS provider FROM search_query_records q
          JOIN search_coverage_executions b ON b.search_execution_id=q.literature_search_execution_id WHERE b.search_coverage_id=cid) x;
      SELECT count(*) INTO q FROM search_query_records x JOIN search_coverage_executions b
        ON b.search_execution_id=x.literature_search_execution_id WHERE b.search_coverage_id=cid;
      SELECT count(*) INTO r FROM search_result_records x JOIN search_query_records y ON y.id=x.search_query_record_id
        JOIN search_coverage_executions b ON b.search_execution_id=y.literature_search_execution_id WHERE b.search_coverage_id=cid;
      SELECT count(DISTINCT source_id) INTO resolved FROM (
        SELECT x.id,min(s.source_id::text)::uuid AS source_id FROM search_result_records x
          JOIN search_query_records y ON y.id=x.search_query_record_id
          JOIN search_coverage_executions b ON b.search_execution_id=y.literature_search_execution_id
          JOIN search_result_resolutions s ON s.search_result_record_id=x.id
          WHERE b.search_coverage_id=cid GROUP BY x.id
          HAVING bool_and(s.source_version_id IS NOT NULL)
            AND count(DISTINCT (s.source_id,s.source_version_id))=1) bindings;
      SELECT time_range INTO scope FROM literature_search_plan_versions WHERE id=c.search_plan_version_id;
      IF c.query_count<>q OR c.result_count<>r OR c.resolved_source_count<>resolved
        OR c.providers<>providers OR c.time_scope IS DISTINCT FROM scope THEN
        RAISE EXCEPTION 'coverage aggregate mismatch' USING ERRCODE='P17D3'; END IF;
      RETURN NULL;
    END $$;
    CREATE FUNCTION pr218_complete_prior_art() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE cid UUID; n INT;
    BEGIN
      IF TG_TABLE_NAME='prior_art_relations' THEN cid:=NEW.id; ELSE cid:=NEW.prior_art_relation_id; END IF;
      SELECT count(*) INTO n FROM prior_art_evidence_inputs WHERE prior_art_relation_id=cid;
      IF n NOT BETWEEN 1 AND 100 OR EXISTS(
        SELECT 1 FROM prior_art_relations p JOIN claim_versions v ON v.id=p.claim_version_id
          JOIN claims c ON c.id=v.claim_id JOIN prior_art_evidence_inputs b ON b.prior_art_relation_id=p.id
          JOIN literature_evidence e ON e.id=b.literature_evidence_id
        WHERE p.id=cid AND (e.source_version_id<>p.source_version_id OR e.project_id<>c.project_id
          OR e.review_status<>'VERIFIED' OR e.content_hash IS NULL OR e.content_hash !~ '^[0-9a-f]{64}$'
          OR NOT pr218_claim_valid(p.claim_version_id) OR NOT pr218_source_valid(p.source_version_id,c.project_id)
          OR NOT EXISTS(SELECT 1 FROM literature_evidence_review_events r JOIN actors a ON a.id=r.reviewed_by
            WHERE r.id=(SELECT id FROM literature_evidence_review_events WHERE literature_evidence_id=e.id ORDER BY reviewed_at DESC,id DESC LIMIT 1)
              AND r.new_status='VERIFIED' AND a.actor_type='HUMAN' AND r.reviewed_by<>e.created_by)))
      THEN RAISE EXCEPTION 'complete independently verified comparison required' USING ERRCODE='P17D3'; END IF;
      RETURN NULL;
    END $$;
    CREATE FUNCTION pr218_novelty_chain() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE p novelty_assessments;
    BEGIN
      IF NEW.supersedes_assessment_id IS NOT NULL THEN
        SELECT * INTO p FROM novelty_assessments WHERE id=NEW.supersedes_assessment_id FOR UPDATE;
        IF p.id IS NULL OR p.claim_version_id<>NEW.claim_version_id OR p.id=NEW.id THEN
          RAISE EXCEPTION 'same exact Claim predecessor required' USING ERRCODE='P17D3'; END IF;
        IF EXISTS(SELECT 1 FROM novelty_assessments WHERE supersedes_assessment_id=p.id) THEN
          RAISE EXCEPTION 'predecessor already superseded' USING ERRCODE='P17D2'; END IF;
      END IF;
      RETURN NEW;
    END $$;
    """)
    for table in (
        "search_coverage",
        "search_coverage_executions",
        "prior_art_relations",
        "prior_art_evidence_inputs",
        "novelty_assessments",
    ):
        op.execute(
            f"CREATE TRIGGER trg_pr218_{table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION pr218_immutable()"
        )
        kind = (
            "child"
            if table in ("search_coverage_executions", "prior_art_evidence_inputs")
            else "parent"
        )
        op.execute(
            f"CREATE TRIGGER trg_pr218_{table}_{kind}_guard BEFORE INSERT ON {table} FOR EACH ROW EXECUTE FUNCTION pr218_{kind}_guard()"
        )
    for kind, tables in (
        ("coverage", ("search_coverage", "search_coverage_executions")),
        ("prior_art", ("prior_art_relations", "prior_art_evidence_inputs")),
    ):
        for table in tables:
            op.execute(
                f"CREATE CONSTRAINT TRIGGER trg_pr218_{table}_complete_{kind} AFTER INSERT ON {table} DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pr218_complete_{kind}()"
            )
    op.execute(
        "CREATE TRIGGER trg_pr218_novelty_chain BEFORE INSERT ON novelty_assessments FOR EACH ROW EXECUTE FUNCTION pr218_novelty_chain()"
    )


def downgrade() -> None:
    op.execute(
        "LOCK TABLE novelty_assessments,prior_art_evidence_inputs,prior_art_relations,search_coverage,search_coverage_executions IN ACCESS EXCLUSIVE MODE"
    )
    op.execute("""DO $$ BEGIN IF EXISTS(SELECT 1 FROM search_coverage)
        OR EXISTS(SELECT 1 FROM prior_art_relations) OR EXISTS(SELECT 1 FROM novelty_assessments)
        THEN RAISE EXCEPTION 'PR2-18 downgrade refuses historical data'; END IF; END $$;""")
    for table in (
        "novelty_assessments",
        "prior_art_evidence_inputs",
        "prior_art_relations",
        "search_coverage_executions",
        "search_coverage",
    ):
        op.execute(f"DROP TABLE {table}")
    for function in (
        "pr218_novelty_chain",
        "pr218_complete_prior_art",
        "pr218_complete_coverage",
        "pr218_child_guard",
        "pr218_parent_guard",
        "pr218_capture_prelocked",
        "pr218_lock_tables",
        "pr218_claim_valid",
        "pr218_source_valid",
        "pr218_immutable",
        "pr218_valid_time_scope",
        "pr218_valid_providers",
    ):
        args = {
            "pr218_claim_valid": "UUID",
            "pr218_source_valid": "UUID,UUID",
            "pr218_valid_time_scope": "JSONB",
            "pr218_valid_providers": "JSONB",
        }.get(function, "")
        op.execute(f"DROP FUNCTION {function}({args})")
