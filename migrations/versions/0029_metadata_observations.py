# ruff: noqa: E501
"""M2-AQ-001: dependent bibliographic observations and established resolutions."""

from alembic import op

revision = "0029_metadata_observations"
down_revision = "0028_provider_cancellation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE metadata_observations (
      id UUID PRIMARY KEY,
      project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
      result_id UUID NOT NULL REFERENCES search_result_records(id) ON DELETE RESTRICT,
      deployment_id TEXT NOT NULL CHECK(length(btrim(deployment_id)) BETWEEN 1 AND 256),
      invocation_id UUID NOT NULL,
      request_fingerprint CHAR(64) NOT NULL CHECK(request_fingerprint ~ '^[0-9a-f]{64}$'),
      provider_id TEXT NOT NULL CHECK(length(btrim(provider_id)) BETWEEN 1 AND 128),
      provider_version TEXT NOT NULL CHECK(length(btrim(provider_version)) BETWEEN 1 AND 128),
      adapter_version TEXT NOT NULL CHECK(length(btrim(adapter_version)) BETWEEN 1 AND 128),
      endpoint TEXT NOT NULL CHECK(length(btrim(endpoint)) BETWEEN 1 AND 4096),
      request_started_at TIMESTAMPTZ NOT NULL,
      observed_at TIMESTAMPTZ NOT NULL CHECK(observed_at >= request_started_at),
      observed_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
      outcome TEXT NOT NULL CHECK(outcome IN ('MATCH','CONFLICT','AMBIGUOUS','UNRESOLVED','UNAVAILABLE')),
      failure_code TEXT CHECK(length(failure_code) BETWEEN 1 AND 128),
      http_status INTEGER CHECK(http_status BETWEEN 100 AND 599),
      artifact_version_id UUID REFERENCES artifact_versions(id) ON DELETE RESTRICT,
      source_id UUID REFERENCES literature_sources(id) ON DELETE RESTRICT,
      source_version_id UUID,
      content_hash CHAR(64) NOT NULL CHECK(content_hash ~ '^[0-9a-f]{64}$'),
      hash_scheme TEXT NOT NULL CHECK(hash_scheme='sha256-cjson-v1'),
      UNIQUE(deployment_id,project_id,observed_by,invocation_id),
      FOREIGN KEY(source_id,source_version_id) REFERENCES source_versions(literature_source_id,id) ON DELETE RESTRICT,
      CHECK(source_version_id IS NULL OR source_id IS NOT NULL),
      CHECK(source_id IS NULL OR outcome='MATCH'),
      CHECK(outcome<>'MATCH' OR (artifact_version_id IS NOT NULL AND failure_code IS NULL)),
      CHECK(artifact_version_id IS NOT NULL OR
        (outcome='UNAVAILABLE' AND http_status IS NULL AND failure_code IS NOT NULL AND failure_code IN ('TRANSPORT_TIMEOUT','TRANSPORT_UNKNOWN')))
    );
    CREATE TABLE search_result_resolutions (
      id UUID PRIMARY KEY,
      search_result_record_id UUID NOT NULL REFERENCES search_result_records(id) ON DELETE RESTRICT,
      source_id UUID NOT NULL REFERENCES literature_sources(id) ON DELETE RESTRICT,
      source_version_id UUID,
      resolved_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
      resolved_at TIMESTAMPTZ NOT NULL,
      basis TEXT NOT NULL CHECK(length(btrim(basis)) BETWEEN 1 AND 4096),
      content_hash CHAR(64) NOT NULL CHECK(content_hash ~ '^[0-9a-f]{64}$'),
      hash_scheme TEXT NOT NULL CHECK(hash_scheme='sha256-cjson-v1'),
      FOREIGN KEY(source_id,source_version_id) REFERENCES source_versions(literature_source_id,id) ON DELETE RESTRICT,
      UNIQUE NULLS NOT DISTINCT(search_result_record_id,source_id,source_version_id)
    );
    CREATE INDEX ix_mo_project ON metadata_observations(project_id);
    CREATE INDEX ix_mo_result ON metadata_observations(result_id);
    CREATE INDEX ix_mo_actor ON metadata_observations(observed_by);
    CREATE INDEX ix_mo_artifact ON metadata_observations(artifact_version_id);
    CREATE INDEX ix_mo_source_version ON metadata_observations(source_id,source_version_id);
    CREATE INDEX ix_mo_version ON metadata_observations(source_version_id);
    CREATE INDEX ix_srr_source_version ON search_result_resolutions(source_id,source_version_id);
    CREATE INDEX ix_srr_version ON search_result_resolutions(source_version_id);
    CREATE INDEX ix_srr_actor ON search_result_resolutions(resolved_by);
    CREATE FUNCTION m2_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'M2 append-only history' USING ERRCODE='P17D1'; END $$;
    CREATE FUNCTION m2_check_closure() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE p UUID; s UUID; v UUID; a UUID; result UUID;
    BEGIN
      IF TG_TABLE_NAME='metadata_observations' THEN
        result := NEW.result_id; a := NEW.artifact_version_id;
      ELSE result := NEW.search_result_record_id; END IF;
      SELECT e.project_id INTO p FROM search_result_records r
        JOIN search_query_records q ON q.id=r.search_query_record_id
        JOIN literature_search_executions e ON e.id=q.literature_search_execution_id
        JOIN literature_search_plan_versions pv ON pv.id=e.search_plan_version_id
        JOIN literature_search_plans plan ON plan.id=pv.plan_id
        WHERE r.id=result AND plan.project_id=e.project_id AND pv.status IN ('FROZEN','SUPERSEDED');
      IF p IS NULL THEN RAISE EXCEPTION 'M2 invalid result closure' USING ERRCODE='P17D3'; END IF;
      IF TG_TABLE_NAME='metadata_observations' THEN
        IF NEW.project_id<>p THEN
          RAISE EXCEPTION 'M2 project mismatch' USING ERRCODE='P17D3'; END IF;
      END IF;
      IF a IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM artifact_versions av JOIN artifacts ar ON ar.id=av.artifact_id
        WHERE av.id=a AND av.status IN ('FROZEN','SUPERSEDED') AND ar.project_id=p) THEN
        RAISE EXCEPTION 'M2 invalid observation artifact' USING ERRCODE='P17D3'; END IF;
      s := NEW.source_id; v := NEW.source_version_id;
      IF s IS NOT NULL THEN
        PERFORM 1 FROM literature_source_project_links WHERE literature_source_id=s AND project_id=p FOR KEY SHARE;
        IF NOT FOUND THEN RAISE EXCEPTION 'M2 source project mismatch' USING ERRCODE='P17D3'; END IF;
      END IF;
      IF v IS NOT NULL AND NOT EXISTS (SELECT 1 FROM source_versions WHERE id=v AND literature_source_id=s AND status IN ('FROZEN','SUPERSEDED')) THEN
        RAISE EXCEPTION 'M2 version closure mismatch' USING ERRCODE='P17D3'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER m2_observation_immutable BEFORE UPDATE OR DELETE ON metadata_observations FOR EACH ROW EXECUTE FUNCTION m2_immutable();
    CREATE TRIGGER m2_resolution_immutable BEFORE UPDATE OR DELETE ON search_result_resolutions FOR EACH ROW EXECUTE FUNCTION m2_immutable();
    CREATE TRIGGER m2_observation_closure BEFORE INSERT ON metadata_observations FOR EACH ROW EXECUTE FUNCTION m2_check_closure();
    CREATE TRIGGER m2_resolution_closure BEFORE INSERT ON search_result_resolutions FOR EACH ROW EXECUTE FUNCTION m2_check_closure();
    """)


def downgrade() -> None:
    op.execute("""DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM metadata_observations) OR EXISTS(SELECT 1 FROM search_result_resolutions) THEN
        RAISE EXCEPTION 'M2 downgrade refuses historical data'; END IF; END $$;
      DROP TABLE search_result_resolutions;
      DROP TABLE metadata_observations;
      DROP FUNCTION m2_check_closure();
      DROP FUNCTION m2_immutable();""")
