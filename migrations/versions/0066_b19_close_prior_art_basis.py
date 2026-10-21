"""B19 sealed selected prior-art basis and versioned positive novelty material."""

# ruff: noqa: E501
import hashlib

from alembic import op
from sqlalchemy import text

revision = "0066_b19_close_prior_art_basis"
down_revision = "0065_b22_prior_art_correction"
branch_labels = None
depends_on = None

# Exact PostgreSQL 18 definitions at the accepted 0047 + 0057 baseline.
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


def _preflight() -> None:
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


def upgrade() -> None:
    _preflight()
    op.execute(r"""
    LOCK TABLE novelty_assessments IN ACCESS EXCLUSIVE MODE;
    DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM novelty_assessments a
        LEFT JOIN claim_versions v ON v.id=a.claim_version_id
        LEFT JOIN claims c ON c.id=v.claim_id
        LEFT JOIN search_coverage s ON s.id=a.search_coverage_id
        LEFT JOIN literature_search_plan_versions pv ON pv.id=s.search_plan_version_id
        LEFT JOIN literature_search_plans p ON p.id=pv.plan_id
        LEFT JOIN novelty_assessments previous ON previous.id=a.supersedes_assessment_id
        WHERE a.assessment<>'INCONCLUSIVE' OR c.project_id IS NULL
          OR p.project_id IS DISTINCT FROM c.project_id
          OR v.frozen_at IS NULL OR v.status NOT IN ('FROZEN','SUPERSEDED')
          OR v.content_hash IS NULL OR a.assessed_by<>a.created_by
          OR pv.status NOT IN ('FROZEN','SUPERSEDED') OR pv.frozen_at IS NULL
          OR (SELECT count(*) FROM search_coverage_executions WHERE search_coverage_id=s.id) NOT BETWEEN 1 AND 100
          OR EXISTS(SELECT 1 FROM search_coverage_executions ce
            JOIN literature_search_executions execution ON execution.id=ce.search_execution_id
            WHERE ce.search_coverage_id=s.id AND
              (execution.project_id IS DISTINCT FROM c.project_id
                OR execution.search_plan_version_id IS DISTINCT FROM s.search_plan_version_id
                OR execution.status NOT IN ('SUCCEEDED','FAILED','CANCELLED','UNKNOWN')
                OR execution.finished_at IS NULL))
          OR (a.supersedes_assessment_id IS NOT NULL AND
             previous.claim_version_id IS DISTINCT FROM a.claim_version_id)) THEN
        RAISE EXCEPTION 'B19 unresolved existing immutable assessment closure';
      END IF;
    END $$;
    CREATE FUNCTION b19_valid_criteria(v TEXT[]) RETURNS BOOLEAN
      IMMUTABLE STRICT LANGUAGE plpgsql SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE item TEXT; total INT := 0;
    BEGIN
      IF array_ndims(v) IS DISTINCT FROM 1 OR array_lower(v,1) IS DISTINCT FROM 1
        OR cardinality(v) NOT BETWEEN 1 AND 100 THEN RETURN FALSE; END IF;
      FOREACH item IN ARRAY v LOOP
        IF item IS NULL OR length(btrim(item,U&'\0009\000a\000b\000c\000d\001c\001d\001e\001f\0020\0085\00a0\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200a\2028\2029\202f\205f\3000'))=0 OR item<>normalize(item,NFC)
          OR char_length(item)>16384 THEN RETURN FALSE; END IF;
        total := total+char_length(item);
      END LOOP;
      RETURN total<=16384;
    END $$;
    ALTER TABLE novelty_assessments
      ADD COLUMN material_version SMALLINT NOT NULL DEFAULT 1,
      ADD COLUMN scope_statement TEXT NULL,
      ADD COLUMN closeness_criteria TEXT[] NULL,
      DROP CONSTRAINT ck_pr218_novelty_initial_slice,
      ADD CONSTRAINT ck_b19_novelty_material CHECK (
        (material_version=1 AND assessment='INCONCLUSIVE' AND scope_statement IS NULL AND closeness_criteria IS NULL)
        OR (material_version=2 AND assessment='CLOSE_PRIOR_ART_FOUND' AND scope_statement IS NOT NULL AND closeness_criteria IS NOT NULL)),
      ADD CONSTRAINT ck_b19_scope CHECK (scope_statement IS NULL OR
        (length(btrim(scope_statement,U&'\0009\000a\000b\000c\000d\001c\001d\001e\001f\0020\0085\00a0\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200a\2028\2029\202f\205f\3000'))>0 AND char_length(scope_statement)<=16384 AND scope_statement=normalize(scope_statement,NFC))),
      ADD CONSTRAINT ck_b19_criteria CHECK (closeness_criteria IS NULL OR b19_valid_criteria(closeness_criteria));
    CREATE TABLE novelty_assessment_prior_art_inputs (
      id UUID NOT NULL CONSTRAINT pk_b19_basis PRIMARY KEY,
      created_at TIMESTAMPTZ NOT NULL,
      created_by UUID NOT NULL CONSTRAINT fk_b19_basis_actor REFERENCES actors(id) ON DELETE RESTRICT,
      novelty_assessment_id UUID NOT NULL CONSTRAINT fk_b19_basis_assessment REFERENCES novelty_assessments(id) ON DELETE RESTRICT,
      prior_art_relation_id UUID NOT NULL CONSTRAINT fk_b19_basis_relation REFERENCES prior_art_relations(id) ON DELETE RESTRICT,
      search_result_resolution_id UUID NOT NULL CONSTRAINT fk_b19_basis_resolution REFERENCES search_result_resolutions(id) ON DELETE RESTRICT,
      CONSTRAINT uq_b19_basis_relation UNIQUE(novelty_assessment_id,prior_art_relation_id)
    );
    CREATE INDEX ix_b19_basis_actor ON novelty_assessment_prior_art_inputs(created_by);
    CREATE INDEX ix_b19_basis_relation ON novelty_assessment_prior_art_inputs(prior_art_relation_id);
    CREATE INDEX ix_b19_basis_resolution ON novelty_assessment_prior_art_inputs(search_result_resolution_id);
    CREATE FUNCTION b19_require_prelocked() RETURNS trigger LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    BEGIN
      IF NOT pr218_capture_prelocked() THEN
        RAISE EXCEPTION 'capture locks required' USING ERRCODE='P17D3'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER trg_b19_novelty_prelocked BEFORE INSERT ON novelty_assessments
      FOR EACH ROW EXECUTE FUNCTION b19_require_prelocked();
    CREATE FUNCTION b19_basis_insert_guard() RETURNS trigger LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE parent_xid xid; parent novelty_assessments;
    BEGIN
      IF NOT pr218_capture_prelocked() THEN
        RAISE EXCEPTION 'capture locks required' USING ERRCODE='P17D3'; END IF;
      SELECT xmin INTO parent_xid FROM novelty_assessments WHERE id=NEW.novelty_assessment_id;
      SELECT * INTO parent FROM novelty_assessments WHERE id=NEW.novelty_assessment_id;
      IF parent_xid IS DISTINCT FROM pg_current_xact_id()::xid THEN
        RAISE EXCEPTION 'sealed basis set' USING ERRCODE='P17D1'; END IF;
      IF parent.created_by IS DISTINCT FROM NEW.created_by OR parent.material_version<>2 THEN
        RAISE EXCEPTION 'basis parent mismatch' USING ERRCODE='P17D3'; END IF;
      NEW.created_at := parent.created_at;
      IF NOT EXISTS(SELECT 1 FROM prior_art_relations r
        JOIN claim_versions v ON v.id=r.claim_version_id JOIN claims c ON c.id=v.claim_id
        JOIN search_result_resolutions s ON s.id=NEW.search_result_resolution_id
        JOIN source_versions sv ON sv.id=r.source_version_id
        JOIN search_result_records result ON result.id=s.search_result_record_id
        JOIN search_query_records q ON q.id=result.search_query_record_id
        JOIN literature_search_executions execution ON execution.id=q.literature_search_execution_id
        JOIN search_coverage_executions ce ON ce.search_execution_id=q.literature_search_execution_id
        WHERE r.id=NEW.prior_art_relation_id AND r.claim_version_id=parent.claim_version_id
          AND ce.search_coverage_id=parent.search_coverage_id AND execution.project_id=c.project_id
          AND s.source_id=sv.literature_source_id AND s.source_version_id=sv.id) THEN
        RAISE EXCEPTION 'basis typed closure mismatch' USING ERRCODE='P17D3'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER trg_b19_basis_insert BEFORE INSERT ON novelty_assessment_prior_art_inputs
      FOR EACH ROW EXECUTE FUNCTION b19_basis_insert_guard();
    CREATE TRIGGER trg_b19_basis_immutable BEFORE UPDATE OR DELETE ON novelty_assessment_prior_art_inputs
      FOR EACH ROW EXECUTE FUNCTION pr218_immutable();
    CREATE FUNCTION b19_complete_basis() RETURNS trigger LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE aid UUID; parent novelty_assessments; n INT; pid UUID; b RECORD; total INT;
    BEGIN
      IF TG_TABLE_NAME='novelty_assessments' THEN aid:=NEW.id; ELSE aid:=NEW.novelty_assessment_id; END IF;
      SELECT * INTO parent FROM novelty_assessments WHERE id=aid;
      SELECT count(*) INTO n FROM novelty_assessment_prior_art_inputs WHERE novelty_assessment_id=aid;
      IF parent.material_version=1 THEN
        IF n<>0 THEN RAISE EXCEPTION 'v1 basis forbidden' USING ERRCODE='P17D2'; END IF;
        RETURN NULL;
      END IF;
      IF n NOT BETWEEN 1 AND 100 OR NOT EXISTS(
        SELECT 1 FROM novelty_assessment_prior_art_inputs i JOIN prior_art_relations r ON r.id=i.prior_art_relation_id
        WHERE i.novelty_assessment_id=aid AND r.relation IN ('IDENTICAL','HIGHLY_SIMILAR'))
        OR EXISTS(SELECT 1 FROM novelty_assessment_prior_art_inputs i JOIN prior_art_relations next
          ON next.supersedes_prior_art_relation_id=i.prior_art_relation_id WHERE i.novelty_assessment_id=aid) THEN
        RAISE EXCEPTION 'complete terminal close basis required' USING ERRCODE='P17D2'; END IF;
      SELECT c.project_id INTO pid FROM claim_versions v JOIN claims c ON c.id=v.claim_id WHERE v.id=parent.claim_version_id;
      FOR b IN SELECT r.*,s.source_id AS witness_source,s.source_version_id AS witness_version,
          s.search_result_record_id AS result_id,execution.project_id AS witness_project,q.literature_search_execution_id AS execution_id
        FROM novelty_assessment_prior_art_inputs i JOIN prior_art_relations r ON r.id=i.prior_art_relation_id
        JOIN search_result_resolutions s ON s.id=i.search_result_resolution_id
        JOIN search_result_records result ON result.id=s.search_result_record_id
        JOIN search_query_records q ON q.id=result.search_query_record_id
        JOIN literature_search_executions execution ON execution.id=q.literature_search_execution_id
        WHERE i.novelty_assessment_id=aid LOOP
        SELECT count(*) INTO total FROM prior_art_evidence_inputs WHERE prior_art_relation_id=b.id;
        IF b.claim_version_id<>parent.claim_version_id OR b.witness_project<>pid
          OR NOT pr218_claim_valid(b.claim_version_id) OR NOT pr218_source_valid(b.source_version_id,pid)
          OR total NOT BETWEEN 1 AND 100
          OR NOT EXISTS(SELECT 1 FROM source_versions sv WHERE sv.id=b.source_version_id
            AND sv.id=b.witness_version AND sv.literature_source_id=b.witness_source)
          OR NOT EXISTS(SELECT 1 FROM search_coverage_executions ce WHERE ce.search_coverage_id=parent.search_coverage_id AND ce.search_execution_id=b.execution_id)
          OR EXISTS(SELECT 1 FROM search_result_resolutions s WHERE s.search_result_record_id=b.result_id
            AND (s.source_id IS DISTINCT FROM b.witness_source OR s.source_version_id IS DISTINCT FROM b.witness_version))
          OR EXISTS(SELECT 1 FROM prior_art_evidence_inputs i JOIN literature_evidence e ON e.id=i.literature_evidence_id
            WHERE i.prior_art_relation_id=b.id AND (e.source_version_id<>b.source_version_id OR e.project_id<>pid
              OR e.review_status<>'VERIFIED' OR e.content_hash IS NULL OR e.content_hash !~ '^[0-9a-f]{64}$'
              OR NOT EXISTS(SELECT 1 FROM literature_evidence_review_events review JOIN actors a ON a.id=review.reviewed_by
                WHERE review.id=(SELECT id FROM literature_evidence_review_events WHERE literature_evidence_id=e.id ORDER BY reviewed_at DESC,id DESC LIMIT 1)
                  AND review.new_status='VERIFIED' AND a.actor_type='HUMAN' AND review.reviewed_by<>e.created_by))) THEN
          RAISE EXCEPTION 'basis scientific closure mismatch' USING ERRCODE='P17D3';
        END IF;
      END LOOP;
      RETURN NULL;
    END $$;
    CREATE CONSTRAINT TRIGGER trg_b19_novelty_complete AFTER INSERT ON novelty_assessments
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b19_complete_basis();
    CREATE CONSTRAINT TRIGGER trg_b19_basis_complete AFTER INSERT ON novelty_assessment_prior_art_inputs
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b19_complete_basis();
    """)


def downgrade() -> None:
    op.execute("""
    LOCK TABLE novelty_assessments,novelty_assessment_prior_art_inputs IN ACCESS EXCLUSIVE MODE;
    DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM novelty_assessments WHERE material_version<>1)
        OR EXISTS(SELECT 1 FROM novelty_assessment_prior_art_inputs) THEN
        RAISE EXCEPTION 'B19 basis history prevents downgrade'; END IF;
    END $$;
    DROP TRIGGER trg_b19_novelty_complete ON novelty_assessments;
    DROP TRIGGER trg_b19_novelty_prelocked ON novelty_assessments;
    DROP TABLE novelty_assessment_prior_art_inputs;
    DROP FUNCTION b19_complete_basis();
    DROP FUNCTION b19_basis_insert_guard();
    DROP FUNCTION b19_require_prelocked();
    ALTER TABLE novelty_assessments DROP CONSTRAINT ck_b19_novelty_material,
      DROP CONSTRAINT ck_b19_scope, DROP CONSTRAINT ck_b19_criteria,
      DROP COLUMN material_version, DROP COLUMN scope_statement, DROP COLUMN closeness_criteria,
      ADD CONSTRAINT ck_pr218_novelty_initial_slice CHECK (assessment='INCONCLUSIVE');
    DROP FUNCTION b19_valid_criteria(TEXT[]);
    """)
