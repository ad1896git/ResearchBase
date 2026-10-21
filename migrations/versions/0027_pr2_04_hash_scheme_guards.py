"""Enforce the frozen query/result hash scheme without rewriting provenance.

Upgrade locks both tables before preflight; any invalid historical label aborts
all DDL and leaves revision 0026 intact. Downgrade is permitted only with empty
PR2-04 history, so a rollback cannot silently remove protection from provenance.
"""

from alembic import op

revision = "0027_pr2_04_hash_scheme_guards"
down_revision = "0026_pr2_04_p1_contract_guards"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        LOCK TABLE search_query_records, search_result_records IN ACCESS EXCLUSIVE MODE;
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM search_query_records
                     WHERE hash_scheme IS DISTINCT FROM 'sha256-cjson-v1')
             OR EXISTS (SELECT 1 FROM search_result_records
                        WHERE hash_scheme IS DISTINCT FROM 'sha256-cjson-v1') THEN
            RAISE EXCEPTION 'PR2-04 invalid historical hash scheme; provenance unchanged'
              USING ERRCODE = '23514';
          END IF;
        END $$;
        ALTER TABLE search_query_records ADD CONSTRAINT ck_sqrec_hash_scheme
          CHECK (hash_scheme = 'sha256-cjson-v1');
        ALTER TABLE search_result_records ADD CONSTRAINT ck_srrec_hash_scheme
          CHECK (hash_scheme = 'sha256-cjson-v1');
    """)


def downgrade() -> None:
    op.execute("""
        LOCK TABLE literature_search_executions, literature_search_execution_events,
          literature_search_provider_attempts, literature_search_execution_command_receipts,
          search_query_records, search_result_records IN ACCESS EXCLUSIVE MODE;
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM literature_search_executions)
             OR EXISTS (SELECT 1 FROM literature_search_execution_events)
             OR EXISTS (SELECT 1 FROM literature_search_provider_attempts)
             OR EXISTS (SELECT 1 FROM literature_search_execution_command_receipts)
             OR EXISTS (SELECT 1 FROM search_query_records)
             OR EXISTS (SELECT 1 FROM search_result_records) THEN
            RAISE EXCEPTION 'PR2-04 cannot downgrade populated hash scheme protection'
              USING ERRCODE = '23514';
          END IF;
        END $$;
        ALTER TABLE search_result_records DROP CONSTRAINT ck_srrec_hash_scheme;
        ALTER TABLE search_query_records DROP CONSTRAINT ck_sqrec_hash_scheme;
    """)
