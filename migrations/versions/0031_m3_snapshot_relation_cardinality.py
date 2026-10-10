"""Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing."""

# ruff: noqa: E501

from alembic import op

revision = "0031_m3_snapshot_relation_cardinality"
down_revision = "0030_literature_evidence"
branch_labels = None
depends_on = None


# R2 permits an empty snapshot. For a nonempty set, the unique ordinal constraint
# plus min=0 and max=count-1 establishes the required contiguous 0..N-1 sequence.
CARDINALITY_GAP = """
    SELECT s.id
    FROM literature_support_snapshots AS s
    JOIN literature_evidence_relations AS r
      ON r.literature_support_snapshot_id = s.id
    GROUP BY s.id
    HAVING min(r.ordinal) <> 0 OR max(r.ordinal) <> count(*) - 1
    LIMIT 1
"""


def upgrade() -> None:
    # Block concurrent inserts between the legacy-data check and trigger installation.
    op.execute(
        "LOCK TABLE literature_support_snapshots, literature_evidence_relations "
        "IN SHARE ROW EXCLUSIVE MODE"
    )
    # Existing scientific rows are never silently rewritten during migration.
    op.execute(f"""
        DO $$
        DECLARE invalid_snapshot uuid;
        BEGIN
            {CARDINALITY_GAP.replace("SELECT s.id", "SELECT s.id INTO invalid_snapshot", 1)};
            IF invalid_snapshot IS NOT NULL THEN
                RAISE EXCEPTION 'M3 snapshot relation cardinality invalid for %', invalid_snapshot
                    USING ERRCODE = '23514';
            END IF;
        END $$;
    """)
    op.execute("""
        CREATE FUNCTION m3_validate_snapshot_relation_cardinality() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE snapshot_id uuid; relation_count bigint; first_ordinal integer; last_ordinal integer;
        BEGIN
            IF TG_TABLE_NAME = 'literature_support_snapshots' THEN
                snapshot_id := NEW.id;
            ELSE
                snapshot_id := NEW.literature_support_snapshot_id;
            END IF;
            SELECT count(*), min(ordinal), max(ordinal)
              INTO relation_count, first_ordinal, last_ordinal
              FROM literature_evidence_relations
              WHERE literature_support_snapshot_id = snapshot_id;
            IF relation_count > 0 AND
               (first_ordinal <> 0 OR last_ordinal <> relation_count - 1) THEN
                RAISE EXCEPTION 'M3 snapshot relation ordinals must be contiguous for %', snapshot_id
                    USING ERRCODE = '23514';
            END IF;
            RETURN NULL;
        END $$;
        CREATE CONSTRAINT TRIGGER m3_snapshot_relation_cardinality
          AFTER INSERT ON literature_support_snapshots
          DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
          EXECUTE FUNCTION m3_validate_snapshot_relation_cardinality();
        CREATE CONSTRAINT TRIGGER m3_relation_cardinality
          AFTER INSERT ON literature_evidence_relations
          DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
          EXECUTE FUNCTION m3_validate_snapshot_relation_cardinality();
    """)


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM literature_support_snapshots) THEN
                RAISE EXCEPTION 'M3 cardinality guard downgrade preserves nonempty scientific history'
                    USING ERRCODE = 'P17D5';
            END IF;
        END $$;
        DROP TRIGGER m3_relation_cardinality ON literature_evidence_relations;
        DROP TRIGGER m3_snapshot_relation_cardinality ON literature_support_snapshots;
        DROP FUNCTION m3_validate_snapshot_relation_cardinality();
    """)
