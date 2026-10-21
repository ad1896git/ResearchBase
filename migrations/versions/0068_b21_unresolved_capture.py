"""B21 sealed historical resolution membership; preserve all v1 material."""

# ruff: noqa: E501
from alembic import op

revision = "0068_b21_unresolved_capture"
down_revision = "0067_b17_prepared_package_freeze"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(r"""
    DO $$ BEGIN
      -- Exact frozen function bodies: 0047, with 0057's native-xid correction.
      IF EXISTS (SELECT 1 FROM (VALUES
          ('pr218_parent_guard()', '0b905d6ba13603bc3233135c248aa5e9'),
          ('pr218_child_guard()', 'f5119a5cdb036dd1f196c44990bd8ea6'),
          ('pr218_capture_prelocked()', '0716d0df49f2dac86467feb96ae1225f'),
          ('pr218_complete_coverage()', 'ae7be8d6a0151580a5f271e357bdf74e'),
          ('pr218_immutable()', 'c07819cae1031ad75778793c26bcaa4e')
        ) AS expected(name,digest)
        LEFT JOIN pg_proc p ON p.oid=to_regprocedure(expected.name)
        WHERE md5(p.prosrc) IS DISTINCT FROM expected.digest
          OR p.prosecdef OR p.proleakproof OR p.provolatile<>'v' OR p.proparallel<>'u'
          OR p.proconfig IS DISTINCT FROM ARRAY['search_path=pg_catalog, public, pg_temp']
          OR p.prolang IS DISTINCT FROM (SELECT oid FROM pg_language
              WHERE lanname=CASE WHEN expected.name='pr218_capture_prelocked()'
                THEN 'sql' ELSE 'plpgsql' END)) THEN
        RAISE EXCEPTION 'unexpected B21 baseline';
      END IF;
    END $$;
    ALTER TABLE search_coverage
      ADD COLUMN material_version SMALLINT NOT NULL DEFAULT 1,
      ADD COLUMN captured_unresolved_result_count INT,
      ADD CONSTRAINT ck_b21_capture_version CHECK (material_version IN (1,2)),
      ADD CONSTRAINT ck_b21_capture_count CHECK (
        (material_version=1 AND captured_unresolved_result_count IS NULL) OR
        (material_version=2 AND captured_unresolved_result_count IS NOT NULL
          AND captured_unresolved_result_count BETWEEN 0 AND result_count));
    ALTER TABLE search_coverage ALTER COLUMN material_version SET DEFAULT 2;
    CREATE TABLE search_coverage_resolutions (
      id UUID CONSTRAINT pk_b21_resolutions PRIMARY KEY,
      created_at TIMESTAMPTZ NOT NULL,
      created_by UUID NOT NULL CONSTRAINT fk_b21_resolutions_actor REFERENCES actors(id) ON DELETE RESTRICT,
      search_coverage_id UUID NOT NULL CONSTRAINT fk_b21_resolutions_coverage REFERENCES search_coverage(id) ON DELETE RESTRICT,
      search_result_resolution_id UUID NOT NULL CONSTRAINT fk_b21_resolutions_resolution REFERENCES search_result_resolutions(id) ON DELETE RESTRICT,
      resolution_content_hash CHAR(64) NOT NULL,
      CONSTRAINT ck_b21_resolution_hash CHECK (resolution_content_hash ~ '^[0-9a-f]{64}$'),
      CONSTRAINT uq_b21_resolutions_pair UNIQUE(search_coverage_id,search_result_resolution_id)
    );
    CREATE INDEX ix_b21_resolutions_actor ON search_coverage_resolutions(created_by);
    CREATE INDEX ix_b21_resolutions_target ON search_coverage_resolutions(search_result_resolution_id);
    CREATE FUNCTION b21_require_capture_version() RETURNS trigger LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    BEGIN
      IF NEW.material_version IS DISTINCT FROM 2 THEN
        RAISE EXCEPTION 'new coverage requires v2' USING ERRCODE='P17D3';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER trg_b21_capture_version_guard BEFORE INSERT ON search_coverage
      FOR EACH ROW EXECUTE FUNCTION b21_require_capture_version();
    CREATE FUNCTION b21_guard_resolution_insert() RETURNS trigger LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE p search_coverage; owner_xmin xid; r search_result_resolutions;
    BEGIN
      IF NOT pr218_capture_prelocked() THEN
        RAISE EXCEPTION 'capture prelocks required' USING ERRCODE='P17D3'; END IF;
      SELECT * INTO p FROM search_coverage WHERE id=NEW.search_coverage_id;
      SELECT xmin INTO owner_xmin FROM search_coverage WHERE id=NEW.search_coverage_id;
      SELECT * INTO r FROM search_result_resolutions WHERE id=NEW.search_result_resolution_id;
      IF p.id IS NULL OR r.id IS NULL THEN RETURN NEW; END IF; -- Concrete FKs report 23503.
      IF owner_xmin IS DISTINCT FROM pg_current_xact_id()::xid THEN
        RAISE EXCEPTION 'sealed capture membership' USING ERRCODE='P17D1'; END IF;
      IF p.material_version<>2 OR NEW.created_by IS DISTINCT FROM p.created_by
        OR NEW.created_at IS DISTINCT FROM p.created_at
        OR NEW.resolution_content_hash IS DISTINCT FROM r.content_hash
        OR NOT EXISTS(SELECT 1 FROM search_result_records x
          JOIN search_query_records q ON q.id=x.search_query_record_id
          JOIN search_coverage_executions e ON e.search_execution_id=q.literature_search_execution_id
          WHERE x.id=r.search_result_record_id AND e.search_coverage_id=p.id) THEN
        RAISE EXCEPTION 'exact attributed capture membership required' USING ERRCODE='P17D3'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER trg_b21_resolutions_guard BEFORE INSERT ON search_coverage_resolutions
      FOR EACH ROW EXECUTE FUNCTION b21_guard_resolution_insert();
    CREATE TRIGGER trg_b21_resolutions_immutable BEFORE UPDATE OR DELETE ON search_coverage_resolutions
      FOR EACH ROW EXECUTE FUNCTION pr218_immutable();
    CREATE FUNCTION b21_capture_complete() RETURNS trigger LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE cid UUID; p search_coverage; unresolved BIGINT; resolved BIGINT; total BIGINT;
    BEGIN
      IF TG_TABLE_NAME='search_coverage' THEN cid:=NEW.id; ELSE cid:=NEW.search_coverage_id; END IF;
      SELECT * INTO p FROM search_coverage WHERE id=cid;
      IF NOT pr218_capture_prelocked() OR p.material_version<>2 THEN
        RAISE EXCEPTION 'v2 protected capture required' USING ERRCODE='P17D3'; END IF;
      IF EXISTS(
        (SELECT r.id,r.content_hash FROM search_result_resolutions r
          JOIN search_result_records x ON x.id=r.search_result_record_id
          JOIN search_query_records q ON q.id=x.search_query_record_id
          JOIN search_coverage_executions e ON e.search_execution_id=q.literature_search_execution_id
          WHERE e.search_coverage_id=cid
         EXCEPT SELECT search_result_resolution_id,resolution_content_hash
          FROM search_coverage_resolutions WHERE search_coverage_id=cid)
        UNION ALL
        (SELECT search_result_resolution_id,resolution_content_hash FROM search_coverage_resolutions WHERE search_coverage_id=cid
         EXCEPT SELECT r.id,r.content_hash FROM search_result_resolutions r
          JOIN search_result_records x ON x.id=r.search_result_record_id
          JOIN search_query_records q ON q.id=x.search_query_record_id
          JOIN search_coverage_executions e ON e.search_execution_id=q.literature_search_execution_id
          WHERE e.search_coverage_id=cid)) THEN
        RAISE EXCEPTION 'complete resolution capture required' USING ERRCODE='P17D3'; END IF;
      WITH per_result AS (
        SELECT x.id,CASE WHEN count(r.id)>0 AND bool_and(r.source_version_id IS NOT NULL)
            AND count(DISTINCT (r.source_id,r.source_version_id))=1
          THEN min(r.source_id::text)::uuid ELSE NULL END AS source_id
        FROM search_result_records x JOIN search_query_records q ON q.id=x.search_query_record_id
        JOIN search_coverage_executions e ON e.search_execution_id=q.literature_search_execution_id
        LEFT JOIN search_result_resolutions r ON r.search_result_record_id=x.id
        LEFT JOIN search_coverage_resolutions b ON b.search_result_resolution_id=r.id AND b.search_coverage_id=cid
        WHERE e.search_coverage_id=cid GROUP BY x.id)
      SELECT count(*),count(*) FILTER (WHERE source_id IS NULL),count(DISTINCT source_id)
        INTO total,unresolved,resolved FROM per_result;
      IF total<>p.result_count OR unresolved IS DISTINCT FROM p.captured_unresolved_result_count
        OR resolved<>p.resolved_source_count THEN
        RAISE EXCEPTION 'capture accounting mismatch' USING ERRCODE='P17D3'; END IF;
      RETURN NULL;
    END $$;
    """)
    for name, table in (
        ("parent", "search_coverage"),
        ("executions", "search_coverage_executions"),
        ("resolutions", "search_coverage_resolutions"),
    ):
        op.execute(
            f"CREATE CONSTRAINT TRIGGER trg_b21_{name}_complete AFTER INSERT ON {table} DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b21_capture_complete()"
        )


def downgrade() -> None:
    op.execute("LOCK TABLE search_coverage,search_coverage_resolutions IN ACCESS EXCLUSIVE MODE")
    op.execute("""DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM search_coverage WHERE material_version=2)
        OR EXISTS(SELECT 1 FROM search_coverage_resolutions) THEN
        RAISE EXCEPTION 'cannot downgrade populated B21 history'; END IF;
    END $$""")
    for name, table in (
        ("parent", "search_coverage"),
        ("executions", "search_coverage_executions"),
        ("resolutions", "search_coverage_resolutions"),
    ):
        op.execute(f"DROP TRIGGER trg_b21_{name}_complete ON {table}")
    op.execute("""
      DROP TRIGGER trg_b21_capture_version_guard ON search_coverage;
      DROP TABLE search_coverage_resolutions;
      DROP FUNCTION b21_capture_complete();
      DROP FUNCTION b21_guard_resolution_insert();
      DROP FUNCTION b21_require_capture_version();
      ALTER TABLE search_coverage DROP COLUMN captured_unresolved_result_count,
        DROP COLUMN material_version;
    """)
