"""B20 sealed screening and negative-probe assessment basis."""

# ruff: noqa: E501
import hashlib

from alembic import op
from sqlalchemy import text

revision = "0070_b20_screening_basis"
down_revision = "0069_b13_stale_gate_denials"
branch_labels = None
depends_on = None


FUNCTION_DIGESTS = {
    "pr218_capture_prelocked": "0282dfe6f1a9e0530d1fa0d25eda02bbe4ef080f70c7c87236aa8719b495cb3d",
    "pr218_child_guard": "e446d51b1b04cfba84750810c4f347a4e7ef4db1d5b4cf87c2c7f940b79a0271",
    "pr218_claim_valid": "b3e0e9941a88e54130e22c1b6e72d76ecd5273d9c00149ccaee68b49f4d481ec",
    "pr218_complete_coverage": "1187f9d6f8a857a03787d8aff9c358b79e5acdc9d49b376f267a208ca4245f0a",
    "pr218_complete_prior_art": "c3217430a261617e1e6b7e81dc33e3bc922177de7950149570501c1d50a56fed",
    "pr218_immutable": "290952ebe75932739418ed29e7569feea3dcaa7bb58419d6475b3b864de7457b",
    "pr218_lock_tables": "b8cdc0a7597f309b02fa6fdf4e35be736acd56b9e67fb0a1b2188bf89bd69eb6",
    "pr218_novelty_chain": "03b62313be4e5b0865672a862d31fe5bd8081a6c1b5e65edb52222b1c4047e3c",
    "pr218_parent_guard": "69bc742fe9fb539f26e19f41adf75167d950a0bd4a25d2dca3932eacbcffa8cf",
    "pr218_source_valid": "f8927443440429fda22dcba652ea2c0bbef0b4f1e9cc7ed13b60efbbfcb6b04c",
    "pr218_valid_providers": "fa50a901d1da21eee830ac25b8519cc29eaf1b1f0f4a7a88e81626134f9b943b",
    "pr218_valid_time_scope": "1399270abe469471ef1367a8128bdab8b00ede40ebc028dcdfafe4e5aafba570",
}
TRIGGER_DIGESTS = {
    "trg_pr218_novelty_assessments_immutable": "20e957f23960a81a73b0f35423289f8e58053147bf5a20843a6fbb0c8c45aa02",  # noqa: E501
    "trg_pr218_novelty_assessments_parent_guard": "6cf9d5efce374c9ca927b7a69af13f7faa72aaf4b429cc66e3dd743576a5b7dc",  # noqa: E501
    "trg_pr218_novelty_chain": "d514dd4d29d18b2f24af6afab505801d0e8edf8638b2250deafb44281f287454",
    "trg_pr218_prior_art_evidence_inputs_child_guard": "86228f8e901761707864c6b78ff8407cef30ba79a59d18ea1c92a701be3d46c0",  # noqa: E501
    "trg_pr218_prior_art_evidence_inputs_complete_prior_art": "31203ec0677faac804a96d802f717de5fc7d50384b400b14ad7bce613d45a885",  # noqa: E501
    "trg_pr218_prior_art_evidence_inputs_immutable": "95e415a1ad0151c79333572b0d39d58c40d5eb1eafd7c5ce13b0dc8de983762b",  # noqa: E501
    "trg_pr218_prior_art_relations_complete_prior_art": "778c767f3644c5576087701f5fc220ce27fb75aa50deca0bfb7955c99985b8fe",  # noqa: E501
    "trg_pr218_prior_art_relations_immutable": "585dbc28bf6ee520d33347991801242a7d52d6a9377c74e1dd05b64617510fa2",  # noqa: E501
    "trg_pr218_prior_art_relations_parent_guard": "b25c98817d50899b0ce7bf9033af8a087cc1d6036c691bd01928b52b9a9cf381",  # noqa: E501
    "trg_pr218_search_coverage_complete_coverage": "ec2e53d14fbd3cc2dcb2b79027b3b8d521ca3820dfcdd280deb111aae67ef140",  # noqa: E501
    "trg_pr218_search_coverage_executions_child_guard": "8c2e0b610908d5d4d7f8168f13bcb5c5727c08d59981fd2e2338398cc9e35aeb",  # noqa: E501
    "trg_pr218_search_coverage_executions_complete_coverage": "ccd64b21f905455e8d65ebb0f5660a584866aa8f05fcdf45c473de33295061cd",  # noqa: E501
    "trg_pr218_search_coverage_executions_immutable": "876a3eb14538de14f3321cb93be225803e9a9ef4f169f7c118aa5ca910cb7a4d",  # noqa: E501
    "trg_pr218_search_coverage_immutable": "852079cdde3acfcfc78ff707a71c4ae1ab851b1791599b60a4551b1536f03448",  # noqa: E501
    "trg_pr218_search_coverage_parent_guard": "19669b9746309a4c41a1e3ad2754270e6d82dfac54479ac027e921091cfb75da",  # noqa: E501
}


def _shared_preflight() -> None:
    connection = op.get_bind()
    functions = {
        row[0]: hashlib.sha256(row[1].encode()).hexdigest()
        for row in connection.execute(
            text("""SELECT p.proname,pg_get_functiondef(p.oid)
            FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
            WHERE n.nspname='public' AND p.proname LIKE 'pr218_%'""")
        )
    }
    triggers = dict(
        connection.execute(
            text("""SELECT tgname,pg_get_triggerdef(oid)
        FROM pg_trigger WHERE tgname LIKE 'trg_pr218_%'""")
        ).all()
    )
    triggers = {
        name: hashlib.sha256(definition.encode()).hexdigest()
        for name, definition in triggers.items()
    }
    if functions != FUNCTION_DIGESTS or triggers != TRIGGER_DIGESTS:
        raise RuntimeError("B19 unexpected shared novelty guard baseline")


SIBLING_TRIGGER_DIGESTS = {
    "b22_complete_correction": "63294a9456ba6774c22fb4ec3e856581",
    "b22_prior_art_prelocked": "b22465b0de4eed7f00f7be36a1ac7026",
    "trg_b19_basis_complete": "fe3efcbe336a4343731c6101e46bffde",
    "trg_b19_basis_immutable": "c7a5e0cc56fa516d1ca57d7f83fd5bd3",
    "trg_b19_basis_insert": "3a1c94dc4fc151a5d311d5582e9e5291",
    "trg_b19_novelty_complete": "3b2158b6fe8ba160c76ba08bf844130b",
    "trg_b19_novelty_prelocked": "ff5cb5d64ef4ac97250f382bcf23da0b",
    "trg_b21_capture_version_guard": "e034b4257a9ea252c6fb32d9b66f77de",
    "trg_b21_executions_complete": "61777a22092e8b056b39606b3890ae6a",
    "trg_b21_parent_complete": "4688aa8984f98c0b95f0937aec83a378",
    "trg_b21_resolutions_complete": "4e1ff072e04e9e7bdd488995f6b6e750",
    "trg_b21_resolutions_guard": "d4482ea36b48642893c57db843d71fcc",
    "trg_b21_resolutions_immutable": "daac4bc5e6c9495204fe15259d0c0dbb",
}

SIBLING_FUNCTION_DIGESTS = {
    "b19_basis_insert_guard()": "3bbd0f5ddb17d49bd388ddddf36d000e79d8afbc4414f1b9d408f2f1366190f7",
    "b19_complete_basis()": "9a32af2c1a262dcfc236303c515c388baa380ee0a9757556d44c32f5f1ad0350",
    "b19_require_prelocked()": "f990e6b2c95af303e985618c64f5c50264f962c380282ef8b765b08982a7558c",
    "b19_valid_criteria(text[])": "708439e0fc1884f4b26fec5d9907bb50f74c2fe3be032509487ae764f8f6fc85",
    "b21_capture_complete()": "8cd7daa9bc6b6d3f73fcbae0da4cb00ed3b1d04be7913c59cc9a52d4f720bde2",
    "b21_guard_resolution_insert()": "dd41e4cd0c1f17f6c2f554e3cec84745cff3d1edaeb066615eb1063c593d62cd",
    "b21_require_capture_version()": "371dd1970e6f5705cdb0d34ea6a1678d1d47b95300602b4f561979143607d1e6",
    "b22_require_prelocked()": "9689b4fb52db1e548d31bcef7a61a441bccc6dff224eddea6279f09aad48d82a",
    "b22_validate_correction()": "cb9a5bea8d427e3606b712dcb3d249cbd012c78701206e6630e18b72e6a2405f",
}


def upgrade() -> None:
    _shared_preflight()
    functions = dict(
        op.get_bind()
        .execute(
            text("""SELECT p.oid::regprocedure::text,pg_get_functiondef(p.oid)
        FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
        WHERE n.nspname='public' AND (p.proname LIKE 'b19_%' OR p.proname LIKE 'b21_%'
          OR p.proname LIKE 'b22_%')""")
        )
        .all()
    )
    if {
        name: hashlib.sha256(definition.encode()).hexdigest()
        for name, definition in functions.items()
    } != SIBLING_FUNCTION_DIGESTS:
        raise RuntimeError("unexpected B20 sibling function definitions")
    triggers = dict(
        op.get_bind()
        .execute(
            text("""SELECT tgname,md5(pg_get_triggerdef(oid))
        FROM pg_trigger WHERE tgname LIKE 'trg_b19_%' OR tgname LIKE 'trg_b21_%'
          OR tgname LIKE 'trg_b22_%' OR tgname LIKE 'b22_%'""")
        )
        .all()
    )
    if triggers != SIBLING_TRIGGER_DIGESTS:
        raise RuntimeError("unexpected B20 sibling attachment baseline")
    op.execute(r"""
    DO $$ BEGIN
      IF (SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='novelty_assessments'::regclass AND conname='ck_b19_novelty_material')
        IS DISTINCT FROM  $check$CHECK ((((material_version = 1) AND ((assessment)::text = 'INCONCLUSIVE'::text) AND (scope_statement IS NULL) AND (closeness_criteria IS NULL)) OR ((material_version = 2) AND ((assessment)::text = 'CLOSE_PRIOR_ART_FOUND'::text) AND (scope_statement IS NOT NULL) AND (closeness_criteria IS NOT NULL))))$check$ THEN
        RAISE EXCEPTION 'unexpected B20 material CHECK baseline'; END IF;
      IF EXISTS(SELECT 1 FROM (VALUES
      ('b22_require_prelocked()', 'c80e433d01c4db551f25254d3a10033a'),
      ('b22_validate_correction()', '997261651677ce2e03b12b2f0f57e25d'),
      ('b19_valid_criteria(text[])', '33e2fa250315b3df198072f51c10b008'),
      ('b19_require_prelocked()', '161a8c9cafcd4c6f67fecc9025fcc57c'),
      ('b19_basis_insert_guard()', 'ea907abd8624b37f05c00bf86e226435'),
      ('b19_complete_basis()', '68c49755d02bf8cd174252e9aa03cddd'),
      ('b21_require_capture_version()', '199bb75705995b8dff169fa6b3e86eb3'),
      ('b21_guard_resolution_insert()', '488d0fae2dc7d2f8e5b693a72dbe4aaf'),
      ('b21_capture_complete()', '381c6354bf487d741d928b5dad0257bf')
        ) expected(name,digest) LEFT JOIN pg_proc p ON p.oid=to_regprocedure(expected.name)
        WHERE md5(p.prosrc) IS DISTINCT FROM expected.digest OR p.prosecdef OR p.proleakproof
          OR p.provolatile<>CASE WHEN expected.name='b19_valid_criteria(text[])' THEN 'i' ELSE 'v' END OR p.proparallel<>'u'
          OR p.proconfig IS DISTINCT FROM ARRAY['search_path=pg_catalog, public, pg_temp']) THEN
        RAISE EXCEPTION 'unexpected B20 sibling guard baseline'; END IF;
      IF md5((SELECT prosrc FROM pg_proc WHERE oid='pr218_capture_prelocked()'::regprocedure))
        IS DISTINCT FROM '0716d0df49f2dac86467feb96ae1225f' THEN
        RAISE EXCEPTION 'unexpected B20 prelock baseline'; END IF;
      IF (SELECT pg_get_triggerdef(oid) FROM pg_trigger WHERE tgname='trg_b19_novelty_complete')
        IS DISTINCT FROM 'CREATE CONSTRAINT TRIGGER trg_b19_novelty_complete AFTER INSERT ON public.novelty_assessments DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b19_complete_basis()' THEN
        RAISE EXCEPTION 'unexpected B20 B19 attachment baseline'; END IF;
    END $$;
    ALTER TABLE novelty_assessments ADD COLUMN screening_captured BOOLEAN NOT NULL DEFAULT FALSE,
      DROP CONSTRAINT ck_b19_novelty_material,
      ADD CONSTRAINT ck_b20_novelty_material CHECK (
        (NOT screening_captured AND ((material_version=1 AND assessment='INCONCLUSIVE' AND scope_statement IS NULL AND closeness_criteria IS NULL)
          OR (material_version=2 AND assessment='CLOSE_PRIOR_ART_FOUND' AND scope_statement IS NOT NULL AND closeness_criteria IS NOT NULL)))
        OR (screening_captured AND material_version=2 AND assessment IN ('INCONCLUSIVE','NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE')
          AND scope_statement IS NOT NULL AND closeness_criteria IS NOT NULL));
    DROP TRIGGER trg_b19_novelty_complete ON novelty_assessments;
    CREATE CONSTRAINT TRIGGER trg_b19_novelty_complete AFTER INSERT ON novelty_assessments
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (NOT NEW.screening_captured) EXECUTE FUNCTION b19_complete_basis();
    CREATE FUNCTION b20_valid_ordinals(v INT[]) RETURNS BOOLEAN IMMUTABLE STRICT LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE item INT; previous INT := -1;
    BEGIN
      IF array_ndims(v) IS DISTINCT FROM 1 OR array_lower(v,1) IS DISTINCT FROM 1
        OR cardinality(v) NOT BETWEEN 1 AND 100 THEN RETURN FALSE; END IF;
      FOREACH item IN ARRAY v LOOP
        IF item IS NULL OR item NOT BETWEEN 0 AND 99 OR item<=previous THEN RETURN FALSE; END IF;
        previous:=item;
      END LOOP;
      RETURN TRUE;
    END $$;
    CREATE TABLE novelty_assessment_probes (
      id UUID CONSTRAINT pk_b20_probe PRIMARY KEY, novelty_assessment_id UUID NOT NULL,
      search_execution_id UUID NOT NULL, query_index INT NOT NULL, disposition VARCHAR(16) NOT NULL, rationale TEXT NOT NULL, created_by UUID NOT NULL, created_at TIMESTAMPTZ NOT NULL,
      CONSTRAINT uq_b20_probe_key UNIQUE(novelty_assessment_id,search_execution_id,query_index),
      CONSTRAINT ck_b20_probe_index CHECK (query_index BETWEEN 0 AND 31), CONSTRAINT ck_b20_probe_disposition CHECK (disposition IN ('NO_HITS','SCREENED','INCOMPLETE')), CONSTRAINT ck_b20_probe_text CHECK (char_length(rationale) BETWEEN 1 AND 16384
        AND length(btrim(rationale,U&'\0009\000a\000b\000c\000d\001c\001d\001e\001f\0020\0085\00a0\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200a\2028\2029\202f\205f\3000'))>0 AND rationale=normalize(rationale,NFC)),
      CONSTRAINT fk_b20_probe_assessment FOREIGN KEY (novelty_assessment_id) REFERENCES novelty_assessments(id) ON DELETE RESTRICT,
      CONSTRAINT fk_b20_probe_execution FOREIGN KEY (search_execution_id) REFERENCES literature_search_executions(id) ON DELETE RESTRICT,
      CONSTRAINT fk_b20_probe_actor FOREIGN KEY (created_by) REFERENCES actors(id) ON DELETE RESTRICT
    );
    CREATE INDEX ix_b20_probe_execution ON novelty_assessment_probes(search_execution_id);
    CREATE INDEX ix_b20_probe_actor ON novelty_assessment_probes(created_by);
    CREATE TABLE novelty_assessment_screening_results (
      id UUID CONSTRAINT pk_b20_screen PRIMARY KEY, novelty_assessment_id UUID NOT NULL,
      search_result_record_id UUID NOT NULL, disposition VARCHAR(16) NOT NULL, criteria_ordinals INT[] NOT NULL, rationale TEXT NOT NULL, prior_art_relation_id UUID, search_result_resolution_id UUID, created_by UUID NOT NULL, created_at TIMESTAMPTZ NOT NULL,
      CONSTRAINT uq_b20_screen_result UNIQUE(novelty_assessment_id,search_result_record_id),
      CONSTRAINT ck_b20_screen_disposition CHECK (disposition IN ('NOT_CLOSE','CLOSE','UNCLEAR','EXCLUDED','UNRESOLVED')), CONSTRAINT ck_b20_screen_refs CHECK ((prior_art_relation_id IS NULL)=(search_result_resolution_id IS NULL) AND (disposition NOT IN ('NOT_CLOSE','CLOSE') OR prior_art_relation_id IS NOT NULL) AND (disposition<>'UNRESOLVED' OR prior_art_relation_id IS NULL)), CONSTRAINT ck_b20_screen_ordinals CHECK (b20_valid_ordinals(criteria_ordinals)), CONSTRAINT ck_b20_screen_text CHECK (char_length(rationale) BETWEEN 1 AND 16384
        AND length(btrim(rationale,U&'\0009\000a\000b\000c\000d\001c\001d\001e\001f\0020\0085\00a0\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200a\2028\2029\202f\205f\3000'))>0 AND rationale=normalize(rationale,NFC)),
      CONSTRAINT fk_b20_screen_assessment FOREIGN KEY (novelty_assessment_id) REFERENCES novelty_assessments(id) ON DELETE RESTRICT,
      CONSTRAINT fk_b20_screen_result FOREIGN KEY (search_result_record_id) REFERENCES search_result_records(id) ON DELETE RESTRICT,
      CONSTRAINT fk_b20_screen_relation FOREIGN KEY (prior_art_relation_id) REFERENCES prior_art_relations(id) ON DELETE RESTRICT,
      CONSTRAINT fk_b20_screen_resolution FOREIGN KEY (search_result_resolution_id) REFERENCES search_result_resolutions(id) ON DELETE RESTRICT,
      CONSTRAINT fk_b20_screen_actor FOREIGN KEY (created_by) REFERENCES actors(id) ON DELETE RESTRICT
    );
    CREATE INDEX ix_b20_screen_result ON novelty_assessment_screening_results(search_result_record_id);
    CREATE INDEX ix_b20_screen_relation ON novelty_assessment_screening_results(prior_art_relation_id);
    CREATE INDEX ix_b20_screen_resolution ON novelty_assessment_screening_results(search_result_resolution_id);
    CREATE INDEX ix_b20_screen_actor ON novelty_assessment_screening_results(created_by);
    CREATE FUNCTION b20_child_guard() RETURNS trigger LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE parent novelty_assessments; owner_xmin xid;
    BEGIN
      IF NOT pr218_capture_prelocked() THEN RAISE EXCEPTION 'capture prelocks required' USING ERRCODE='P17D3'; END IF;
      SELECT * INTO parent FROM novelty_assessments WHERE id=NEW.novelty_assessment_id;
      SELECT xmin INTO owner_xmin FROM novelty_assessments WHERE id=NEW.novelty_assessment_id;
      IF parent.id IS NULL THEN RETURN NEW; END IF;
      IF owner_xmin IS DISTINCT FROM pg_current_xact_id()::xid THEN RAISE EXCEPTION 'sealed screening set' USING ERRCODE='P17D1'; END IF;
      IF NOT parent.screening_captured OR NEW.created_by IS DISTINCT FROM parent.created_by
        OR NEW.created_at IS DISTINCT FROM parent.created_at THEN
        RAISE EXCEPTION 'screening attribution mismatch' USING ERRCODE='P17D3'; END IF;
      RETURN NEW;
    END $$;
    CREATE FUNCTION b20_complete_screening() RETURNS trigger LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE aid UUID; parent novelty_assessments; cov search_coverage; pid UUID;
      probe RECORD; screen RECORD; expected TEXT; negative BOOLEAN; total INT;
    BEGIN
      IF TG_TABLE_NAME='novelty_assessments' THEN aid:=NEW.id; ELSE aid:=NEW.novelty_assessment_id; END IF;
      SELECT * INTO parent FROM novelty_assessments WHERE id=aid;
      IF NOT parent.screening_captured THEN
        IF EXISTS(SELECT 1 FROM novelty_assessment_probes WHERE novelty_assessment_id=aid)
          OR EXISTS(SELECT 1 FROM novelty_assessment_screening_results WHERE novelty_assessment_id=aid) THEN
          RAISE EXCEPTION 'non-screening children forbidden' USING ERRCODE='P17D3'; END IF;
        RETURN NULL;
      END IF;
      IF NOT pr218_capture_prelocked() THEN RAISE EXCEPTION 'capture prelocks required' USING ERRCODE='P17D3'; END IF;
      negative:=parent.assessment='NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE';
      SELECT * INTO cov FROM search_coverage WHERE id=parent.search_coverage_id;
      SELECT c.project_id INTO pid FROM claim_versions v JOIN claims c ON c.id=v.claim_id WHERE v.id=parent.claim_version_id;
      IF cov.material_version<>2 OR EXISTS(SELECT 1 FROM novelty_assessment_prior_art_inputs WHERE novelty_assessment_id=aid)
        OR (SELECT count(*) FROM novelty_assessment_probes WHERE novelty_assessment_id=aid) NOT BETWEEN 1 AND 3200
        OR (SELECT count(*) FROM novelty_assessment_screening_results WHERE novelty_assessment_id=aid)>10000
        OR (SELECT count(*) FROM literature_search_executions WHERE search_plan_version_id=cov.search_plan_version_id) NOT BETWEEN 1 AND 100
        OR EXISTS(SELECT 1 FROM literature_search_executions e WHERE e.search_plan_version_id=cov.search_plan_version_id
          AND (e.project_id<>pid OR e.status NOT IN ('SUCCEEDED','FAILED','CANCELLED','UNKNOWN') OR e.finished_at IS NULL)) THEN
        RAISE EXCEPTION 'screening inventory ineligible' USING ERRCODE='P17D3'; END IF;
      IF EXISTS(
        (SELECT id FROM literature_search_executions WHERE search_plan_version_id=cov.search_plan_version_id
          EXCEPT SELECT search_execution_id FROM search_coverage_executions WHERE search_coverage_id=cov.id)
        UNION ALL
        (SELECT search_execution_id FROM search_coverage_executions WHERE search_coverage_id=cov.id
          EXCEPT SELECT id FROM literature_search_executions WHERE search_plan_version_id=cov.search_plan_version_id)) THEN
        RAISE EXCEPTION 'complete exact-plan inventory required' USING ERRCODE='P17D3'; END IF;
      IF EXISTS(
        (SELECT e.id,i FROM literature_search_executions e CROSS JOIN LATERAL generate_series(0,jsonb_array_length(e.execution_context->'queries')-1) i
          WHERE e.search_plan_version_id=cov.search_plan_version_id
          EXCEPT SELECT search_execution_id,query_index FROM novelty_assessment_probes WHERE novelty_assessment_id=aid)
        UNION ALL
        (SELECT search_execution_id,query_index FROM novelty_assessment_probes WHERE novelty_assessment_id=aid
          EXCEPT SELECT e.id,i FROM literature_search_executions e CROSS JOIN LATERAL generate_series(0,jsonb_array_length(e.execution_context->'queries')-1) i
          WHERE e.search_plan_version_id=cov.search_plan_version_id)) THEN
        RAISE EXCEPTION 'complete intended probes required' USING ERRCODE='P17D3'; END IF;
      IF EXISTS(
        (SELECT r.id FROM search_result_records r JOIN search_query_records q ON q.id=r.search_query_record_id
          JOIN search_coverage_executions ce ON ce.search_execution_id=q.literature_search_execution_id WHERE ce.search_coverage_id=cov.id
          EXCEPT SELECT search_result_record_id FROM novelty_assessment_screening_results WHERE novelty_assessment_id=aid)
        UNION ALL
        (SELECT search_result_record_id FROM novelty_assessment_screening_results WHERE novelty_assessment_id=aid
          EXCEPT SELECT r.id FROM search_result_records r JOIN search_query_records q ON q.id=r.search_query_record_id
          JOIN search_coverage_executions ce ON ce.search_execution_id=q.literature_search_execution_id WHERE ce.search_coverage_id=cov.id)) THEN
        RAISE EXCEPTION 'complete retained results required' USING ERRCODE='P17D3'; END IF;
      FOR probe IN SELECT p.*,e.status FROM novelty_assessment_probes p JOIN literature_search_executions e ON e.id=p.search_execution_id WHERE p.novelty_assessment_id=aid LOOP
        expected:='INCOMPLETE';
        IF probe.status='SUCCEEDED' AND NOT EXISTS(SELECT 1 FROM literature_search_provider_attempts a WHERE a.execution_id=probe.search_execution_id
            AND (a.status<>'SUCCEEDED' OR a.warning_codes IS DISTINCT FROM '[]'::jsonb))
          AND EXISTS(SELECT 1 FROM literature_search_provider_attempts a WHERE a.execution_id=probe.search_execution_id AND a.query_index=probe.query_index AND a.status='SUCCEEDED' AND a.query_record_id IS NOT NULL) THEN
          IF EXISTS(SELECT 1 FROM search_result_records r JOIN literature_search_provider_attempts a ON a.query_record_id=r.search_query_record_id
            WHERE a.execution_id=probe.search_execution_id AND a.query_index=probe.query_index) THEN expected:='SCREENED'; ELSE expected:='NO_HITS'; END IF;
        END IF;
        IF probe.disposition<>expected THEN RAISE EXCEPTION 'probe disposition mismatch' USING ERRCODE='P17D3'; END IF;
        IF negative AND expected='INCOMPLETE' THEN RAISE EXCEPTION 'incomplete negative probe' USING ERRCODE='P17D2'; END IF;
      END LOOP;
      IF negative AND (cov.captured_unresolved_result_count<>0 OR NOT pr218_claim_valid(parent.claim_version_id)
        OR NOT EXISTS(SELECT 1 FROM search_query_records q JOIN search_coverage_executions ce ON ce.search_execution_id=q.literature_search_execution_id WHERE ce.search_coverage_id=cov.id)
        OR NOT EXISTS(SELECT 1 FROM literature_search_plan_versions v WHERE v.id=cov.search_plan_version_id AND jsonb_array_length(v.planned_providers)>0)
        OR EXISTS(
          (SELECT jsonb_array_elements_text(v.planned_providers) FROM literature_search_plan_versions v WHERE v.id=cov.search_plan_version_id
            EXCEPT SELECT q.provider_id FROM search_query_records q JOIN search_coverage_executions ce ON ce.search_execution_id=q.literature_search_execution_id WHERE ce.search_coverage_id=cov.id)
          UNION ALL
          (SELECT q.provider_id FROM search_query_records q JOIN search_coverage_executions ce ON ce.search_execution_id=q.literature_search_execution_id WHERE ce.search_coverage_id=cov.id
            EXCEPT SELECT jsonb_array_elements_text(v.planned_providers) FROM literature_search_plan_versions v WHERE v.id=cov.search_plan_version_id))) THEN
        RAISE EXCEPTION 'negative provider or unresolved coverage ineligible' USING ERRCODE='P17D2'; END IF;
      FOR screen IN SELECT s.*,r.claim_version_id,r.source_version_id,r.relation,w.search_result_record_id AS witness_result,w.source_id,w.source_version_id AS witness_version
        FROM novelty_assessment_screening_results s LEFT JOIN prior_art_relations r ON r.id=s.prior_art_relation_id
        LEFT JOIN search_result_resolutions w ON w.id=s.search_result_resolution_id WHERE s.novelty_assessment_id=aid LOOP
        IF EXISTS(SELECT 1 FROM unnest(screen.criteria_ordinals) i WHERE i>=cardinality(parent.closeness_criteria))
          OR (negative AND screen.disposition<>'NOT_CLOSE') THEN RAISE EXCEPTION 'screening criteria/outcome ineligible' USING ERRCODE='P17D2'; END IF;
        IF screen.prior_art_relation_id IS NOT NULL THEN
          IF screen.claim_version_id IS DISTINCT FROM parent.claim_version_id OR screen.witness_result IS DISTINCT FROM screen.search_result_record_id
            OR NOT EXISTS(SELECT 1 FROM source_versions sv WHERE sv.id=screen.source_version_id AND sv.id=screen.witness_version AND sv.literature_source_id=screen.source_id)
            OR NOT EXISTS(SELECT 1 FROM search_coverage_resolutions WHERE search_coverage_id=cov.id AND search_result_resolution_id=screen.search_result_resolution_id)
            OR EXISTS(SELECT 1 FROM search_coverage_resolutions b JOIN search_result_resolutions w ON w.id=b.search_result_resolution_id
              WHERE b.search_coverage_id=cov.id AND w.search_result_record_id=screen.search_result_record_id
                AND (w.source_id IS DISTINCT FROM screen.source_id OR w.source_version_id IS DISTINCT FROM screen.source_version_id))
            OR (screen.disposition='NOT_CLOSE' AND screen.relation NOT IN ('RELATED','CONTRASTING'))
            OR (screen.relation IN ('IDENTICAL','HIGHLY_SIMILAR') AND screen.disposition<>'CLOSE')
            OR (screen.relation IN ('PARTIAL_OVERLAP','UNCLEAR') AND screen.disposition<>'UNCLEAR') THEN
            RAISE EXCEPTION 'exact screening witness mismatch' USING ERRCODE='P17D3'; END IF;
          IF screen.disposition='NOT_CLOSE' THEN
            SELECT count(*) INTO total FROM prior_art_evidence_inputs WHERE prior_art_relation_id=screen.prior_art_relation_id;
            IF total NOT BETWEEN 1 AND 100 OR (negative AND (NOT pr218_source_valid(screen.source_version_id,pid)
              OR NOT pr218_claim_valid(parent.claim_version_id)
              OR EXISTS(SELECT 1 FROM search_result_resolutions w WHERE w.search_result_record_id=screen.search_result_record_id
                AND (w.source_id IS DISTINCT FROM screen.source_id OR w.source_version_id IS DISTINCT FROM screen.source_version_id))
              OR EXISTS(SELECT 1 FROM prior_art_relations r WHERE r.supersedes_prior_art_relation_id=screen.prior_art_relation_id)
              OR (SELECT count(*) FROM prior_art_relations r WHERE r.claim_version_id=parent.claim_version_id AND r.source_version_id=screen.source_version_id AND r.supersedes_prior_art_relation_id IS NULL)<>1))
              OR EXISTS(SELECT 1 FROM prior_art_evidence_inputs i JOIN literature_evidence e ON e.id=i.literature_evidence_id
                WHERE i.prior_art_relation_id=screen.prior_art_relation_id AND (e.source_version_id<>screen.source_version_id OR e.project_id<>pid
                  OR e.review_status<>'VERIFIED' OR e.content_hash IS NULL
                  OR NOT EXISTS(SELECT 1 FROM literature_evidence_review_events review JOIN actors a ON a.id=review.reviewed_by
                    WHERE review.id=(SELECT id FROM literature_evidence_review_events WHERE literature_evidence_id=e.id ORDER BY reviewed_at DESC,id DESC LIMIT 1)
                      AND review.new_status='VERIFIED' AND a.actor_type='HUMAN' AND review.reviewed_by<>e.created_by))) THEN
              RAISE EXCEPTION 'screening scientific closure unusable' USING ERRCODE='P17D3'; END IF;
          END IF;
        END IF;
      END LOOP;
      RETURN NULL;
    END $$;
    CREATE TRIGGER trg_b20_probe_insert BEFORE INSERT ON novelty_assessment_probes FOR EACH ROW EXECUTE FUNCTION b20_child_guard();
    CREATE TRIGGER trg_b20_probe_immutable BEFORE UPDATE OR DELETE ON novelty_assessment_probes FOR EACH ROW EXECUTE FUNCTION pr218_immutable();
    CREATE CONSTRAINT TRIGGER trg_b20_probe_complete AFTER INSERT ON novelty_assessment_probes DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b20_complete_screening();
    CREATE TRIGGER trg_b20_screen_insert BEFORE INSERT ON novelty_assessment_screening_results FOR EACH ROW EXECUTE FUNCTION b20_child_guard();
    CREATE TRIGGER trg_b20_screen_immutable BEFORE UPDATE OR DELETE ON novelty_assessment_screening_results FOR EACH ROW EXECUTE FUNCTION pr218_immutable();
    CREATE CONSTRAINT TRIGGER trg_b20_screen_complete AFTER INSERT ON novelty_assessment_screening_results DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b20_complete_screening();
    CREATE CONSTRAINT TRIGGER trg_b20_parent_complete AFTER INSERT ON novelty_assessments DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b20_complete_screening();
    """)


def downgrade() -> None:
    op.execute("""
    LOCK TABLE novelty_assessments,novelty_assessment_probes,novelty_assessment_screening_results IN ACCESS EXCLUSIVE MODE;
    DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM novelty_assessments WHERE screening_captured)
        OR EXISTS(SELECT 1 FROM novelty_assessment_probes) OR EXISTS(SELECT 1 FROM novelty_assessment_screening_results) THEN
        RAISE EXCEPTION 'B20 screening history prevents downgrade'; END IF;
    END $$;
    DROP TRIGGER trg_b20_parent_complete ON novelty_assessments;
    DROP TABLE novelty_assessment_screening_results,novelty_assessment_probes;
    DROP FUNCTION b20_complete_screening(),b20_child_guard(),b20_valid_ordinals(INT[]);
    DROP TRIGGER trg_b19_novelty_complete ON novelty_assessments;
    CREATE CONSTRAINT TRIGGER trg_b19_novelty_complete AFTER INSERT ON novelty_assessments DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b19_complete_basis();
    ALTER TABLE novelty_assessments DROP CONSTRAINT ck_b20_novelty_material, DROP COLUMN screening_captured,
      ADD CONSTRAINT ck_b19_novelty_material CHECK (
        (material_version=1 AND assessment='INCONCLUSIVE' AND scope_statement IS NULL AND closeness_criteria IS NULL)
        OR (material_version=2 AND assessment='CLOSE_PRIOR_ART_FOUND' AND scope_statement IS NOT NULL AND closeness_criteria IS NOT NULL));
    """)
