"""B22 immutable same-pair prior-art corrections; no new semantic table."""

import hashlib

from alembic import op
from sqlalchemy import text

revision = "0065_b22_prior_art_correction"
down_revision = "0064_b14_publication_ready"
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
        raise RuntimeError("B22 unexpected shared novelty guard baseline")


def upgrade() -> None:
    _preflight()
    op.execute("""
    ALTER TABLE prior_art_relations
      ADD COLUMN material_version SMALLINT NOT NULL DEFAULT 1,
      ADD COLUMN supersedes_prior_art_relation_id UUID NULL,
      ADD CONSTRAINT uq_b22_prior_art_pair UNIQUE (id,claim_version_id,source_version_id),
      ADD CONSTRAINT ck_b22_prior_art_material CHECK (
        (material_version=1 AND supersedes_prior_art_relation_id IS NULL) OR
        (material_version=2 AND supersedes_prior_art_relation_id IS NOT NULL)),
      ADD CONSTRAINT ck_b22_prior_art_not_self CHECK (
        supersedes_prior_art_relation_id IS NULL OR supersedes_prior_art_relation_id<>id),
      ADD CONSTRAINT fk_b22_prior_art_predecessor FOREIGN KEY
        (supersedes_prior_art_relation_id,claim_version_id,source_version_id)
        REFERENCES prior_art_relations(id,claim_version_id,source_version_id) ON DELETE RESTRICT;
    CREATE UNIQUE INDEX uq_b22_prior_art_predecessor
      ON prior_art_relations(supersedes_prior_art_relation_id)
      WHERE supersedes_prior_art_relation_id IS NOT NULL;
    CREATE INDEX ix_b22_prior_art_pair
      ON prior_art_relations(claim_version_id,source_version_id,id);
    CREATE FUNCTION b22_require_prelocked() RETURNS trigger LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    BEGIN
      IF NOT pr218_capture_prelocked() THEN
        RAISE EXCEPTION 'capture locks required' USING ERRCODE='P17D3';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER b22_prior_art_prelocked BEFORE INSERT ON prior_art_relations
      FOR EACH ROW EXECUTE FUNCTION b22_require_prelocked();
    CREATE FUNCTION b22_validate_correction() RETURNS trigger LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE cursor_id UUID := NEW.supersedes_prior_art_relation_id;
      visited UUID[] := ARRAY[NEW.id]; ancestor RECORD;
    BEGIN
      WHILE cursor_id IS NOT NULL LOOP
        IF cursor_id=ANY(visited) THEN
          RAISE EXCEPTION 'cyclic correction' USING ERRCODE='P17D3';
        END IF;
        visited := array_append(visited,cursor_id);
        SELECT p.*,p.xmin::text::bigint AS parent_xid INTO ancestor
          FROM prior_art_relations p WHERE p.id=cursor_id;
        IF NOT FOUND THEN
          RAISE EXCEPTION 'unresolved correction' USING ERRCODE='P17D3';
        END IF;
        IF ancestor.claim_version_id<>NEW.claim_version_id OR
           ancestor.source_version_id<>NEW.source_version_id OR
           ancestor.parent_xid=pg_current_xact_id()::text::bigint THEN
          RAISE EXCEPTION 'committed same-pair ancestry required' USING ERRCODE='P17D3';
        END IF;
        cursor_id := ancestor.supersedes_prior_art_relation_id;
      END LOOP;
      RETURN NEW;
    END $$;
    CREATE CONSTRAINT TRIGGER b22_complete_correction AFTER INSERT ON prior_art_relations
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b22_validate_correction();
    """)


def downgrade() -> None:
    op.execute("""
    LOCK TABLE prior_art_relations,prior_art_evidence_inputs IN ACCESS EXCLUSIVE MODE;
    DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM prior_art_relations
                WHERE material_version<>1 OR supersedes_prior_art_relation_id IS NOT NULL) THEN
        RAISE EXCEPTION 'B22 correction history prevents downgrade';
      END IF;
    END $$;
    DROP TRIGGER b22_complete_correction ON prior_art_relations;
    DROP TRIGGER b22_prior_art_prelocked ON prior_art_relations;
    DROP FUNCTION b22_validate_correction();
    DROP FUNCTION b22_require_prelocked();
    DROP INDEX ix_b22_prior_art_pair;
    DROP INDEX uq_b22_prior_art_predecessor;
    ALTER TABLE prior_art_relations DROP CONSTRAINT fk_b22_prior_art_predecessor,
      DROP CONSTRAINT ck_b22_prior_art_not_self, DROP CONSTRAINT ck_b22_prior_art_material,
      DROP CONSTRAINT uq_b22_prior_art_pair, DROP COLUMN supersedes_prior_art_relation_id,
      DROP COLUMN material_version;
    """)
