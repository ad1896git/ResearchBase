"""M0-CANCEL-001..004: independently confirmed provider cancellation.

No historical rows change. Invalid ambiguous history blocks upgrade. Downgrade
requires empty PR2-04 history before restoring C1-only finalization semantics.
"""

from alembic import op

revision = "0028_provider_cancellation"
down_revision = "0027_pr2_04_hash_scheme_guards"
branch_labels = None
depends_on = None

_BASE_REQUIRE_EVENT = r"""        CREATE OR REPLACE FUNCTION pr204_require_execution_event()
                  RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE matching_events integer;
        DECLARE context jsonb;
        DECLARE context_integer_key text;
        DECLARE query_item jsonb;
        DECLARE query_total integer;
        DECLARE reserved_total integer;
        DECLARE unknown_total integer;
        DECLARE successful_query_total integer;
        BEGIN
          IF TG_OP = 'INSERT' THEN
            -- Admission only: later supersession preserves this exact historical binding.
            IF NOT EXISTS (
              SELECT 1 FROM literature_search_plan_versions v
              JOIN literature_search_plans p ON p.id = v.plan_id
              WHERE v.id = NEW.search_plan_version_id
                AND p.project_id = NEW.project_id AND v.status = 'FROZEN'
            ) THEN
              RAISE EXCEPTION 'PR2-04 admission requires a same-project FROZEN plan version'
                USING ERRCODE = 'P17D5';
            END IF;
            context := NEW.execution_context;
            -- Prove JSON integer types before casts: text extraction alone
            -- would coerce numeric strings and let JSON null evade bounds.
            FOREACH context_integer_key IN ARRAY ARRAY[
              'max_results','max_provider_attempts','timeout_seconds','execution_budget_seconds'
            ] LOOP
              IF jsonb_typeof(context->context_integer_key) IS DISTINCT FROM 'number'
                 OR (context->>context_integer_key) !~ '^-?[0-9]+$' THEN
                RAISE EXCEPTION 'PR2-04 execution context requires JSON integers' USING
                  ERRCODE = 'P17D5';
              END IF;
            END LOOP;
            IF jsonb_typeof(context) <> 'object'
               OR NOT (context ?& ARRAY['schema_version','provider_id','provider_version',
                  'queries','max_results','max_provider_attempts','timeout_seconds',
                  'execution_budget_seconds'])
               OR context - ARRAY['schema_version','provider_id','provider_version','queries',
                  'max_results','max_provider_attempts','timeout_seconds',
                  'execution_budget_seconds'] <> '{}'::jsonb
               OR context->>'schema_version' <> '1'
               OR jsonb_typeof(context->'provider_id') <> 'string'
               OR normalize(context->>'provider_id', NFC) IS DISTINCT FROM context->>'provider_id'
               OR length(btrim(context->>'provider_id',
                  U&'\0009\000A\000B\000C\000D\001C\001D\001E\001F\0020\0085\00A0'
'\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200A'
'\2028\2029\202F\205F\3000')) = 0
               OR length(context->>'provider_id') NOT BETWEEN 1 AND 128
               OR jsonb_typeof(context->'provider_version') <> 'string'
               OR normalize(context->>'provider_version', NFC) IS DISTINCT FROM
                  context->>'provider_version'
               OR length(btrim(context->>'provider_version',
                  U&'\0009\000A\000B\000C\000D\001C\001D\001E\001F\0020\0085\00A0'
'\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200A'
'\2028\2029\202F\205F\3000')) = 0
               OR length(context->>'provider_version') NOT BETWEEN 1 AND 128
               OR jsonb_typeof(context->'queries') <> 'array'
               OR jsonb_array_length(context->'queries') NOT BETWEEN 1 AND 32
               OR (context->>'max_results')::numeric NOT BETWEEN 1 AND 100
               OR (context->>'max_provider_attempts')::numeric NOT BETWEEN 1 AND 3
               OR (context->>'timeout_seconds')::numeric NOT BETWEEN 1 AND 30
               OR (context->>'execution_budget_seconds')::numeric NOT BETWEEN 1 AND 600 THEN
              RAISE EXCEPTION 'PR2-04 execution context has an invalid closed shape' USING
                  ERRCODE = 'P17D5';
            END IF;
            FOR query_item IN SELECT value FROM jsonb_array_elements(context->'queries') LOOP
              IF jsonb_typeof(query_item) <> 'object'
                 OR NOT (query_item ?& ARRAY['query_type','query_text','perspective'])
                 OR query_item - ARRAY['query_type','query_text','perspective'] <> '{}'::jsonb
                 OR query_item->>'query_type' <> 'TEXT'
                 OR jsonb_typeof(query_item->'query_text') <> 'string'
                 OR length(btrim(query_item->>'query_text')) NOT BETWEEN 1 AND 4096
                 OR (jsonb_typeof(query_item->'perspective') NOT IN ('null','string'))
                 OR (jsonb_typeof(query_item->'perspective') = 'string'
                     AND length(query_item->>'perspective') > 256) THEN
                RAISE EXCEPTION 'PR2-04 query input has an invalid closed shape' USING ERRCODE
                  = 'P17D5';
              END IF;
            END LOOP;
            SELECT count(*) INTO matching_events
              FROM literature_search_execution_events
             WHERE execution_id = NEW.id AND kind = 'CREATED'
               AND sequence = 0 AND prior_status IS NULL
               AND new_status = NEW.status AND new_row_version = NEW.row_version
               AND prior_row_version IS NULL;
          ELSE
            SELECT count(*) INTO matching_events
              FROM literature_search_execution_events
             WHERE execution_id = NEW.id
               AND prior_status = OLD.status AND new_status = NEW.status
               AND prior_row_version = OLD.row_version
               AND new_row_version = NEW.row_version;
          END IF;
          IF matching_events <> 1 THEN
            RAISE EXCEPTION 'PR2-04 execution mutation requires exactly one matching event'
              USING ERRCODE = 'P17D5';
          END IF;
          IF TG_OP = 'UPDATE' AND NEW.status IS DISTINCT FROM OLD.status THEN
            SELECT count(*) INTO reserved_total
              FROM literature_search_provider_attempts
             WHERE execution_id = NEW.id AND status = 'RESERVED';
            SELECT count(*) INTO unknown_total
              FROM literature_search_provider_attempts
             WHERE execution_id = NEW.id AND status = 'UNKNOWN';
            IF NEW.status = 'RUNNING' AND reserved_total <> 1 THEN
              RAISE EXCEPTION 'PR2-04 RUNNING transition requires one reserved attempt' USING
                  ERRCODE = 'P17D5';
            ELSIF NEW.status = 'SUCCEEDED' THEN
              SELECT count(DISTINCT query_index) INTO successful_query_total
                FROM literature_search_provider_attempts
               WHERE execution_id = NEW.id AND status = 'SUCCEEDED';
              IF successful_query_total <> jsonb_array_length(NEW.execution_context->'queries') THEN
                RAISE EXCEPTION 'PR2-04 SUCCEEDED requires every input query' USING ERRCODE =
                  'P17D5';
              END IF;
            ELSIF NEW.status = 'UNKNOWN' AND unknown_total = 0 THEN
              RAISE EXCEPTION 'PR2-04 UNKNOWN requires an uncertain provider attempt' USING
                  ERRCODE = 'P17D5';
            ELSIF NEW.status = 'CANCELLED' THEN
              IF reserved_total <> 0 OR unknown_total <> 0 OR NOT EXISTS (
                SELECT 1 FROM literature_search_execution_events
                 WHERE execution_id = NEW.id AND kind = 'CANCEL_REQUESTED'
              ) THEN
                RAISE EXCEPTION 'PR2-04 CANCELLED requires resolved cancellation intent' USING
                  ERRCODE = 'P17D5';
              END IF;
              IF OLD.status = 'PLANNED' AND EXISTS (
                SELECT 1 FROM literature_search_provider_attempts WHERE execution_id = NEW.id
              ) THEN
                RAISE EXCEPTION 'PR2-04 pre-start cancellation cannot have attempts' USING
                  ERRCODE = 'P17D5';
              END IF;
            ELSIF NEW.status = 'FAILED'
              AND NEW.failure_code NOT IN ('PROVIDER_PERMANENT','PROVIDER_MALFORMED',
                  'PROVIDER_RETRY_EXHAUSTED','RECOVERY_INTERRUPTED') THEN
              RAISE EXCEPTION 'PR2-04 FAILED reason is not canonical' USING ERRCODE = 'P17D5';
            END IF;
          END IF;
          RETURN NULL;
        END; $$;
"""


def upgrade() -> None:
    op.execute(r"""LOCK TABLE literature_search_executions, literature_search_execution_events,
 literature_search_provider_attempts, literature_search_execution_command_receipts,
 search_query_records, search_result_records IN ACCESS EXCLUSIVE MODE;
DO $$ BEGIN
 IF EXISTS (SELECT 1 FROM literature_search_provider_attempts a WHERE a.status='CANCELLED'
   AND NOT EXISTS (SELECT 1 FROM literature_search_execution_events v
                   WHERE v.execution_id=a.execution_id AND v.kind='CANCEL_REQUESTED')
   AND (a.invoked_at IS NULL OR a.returned_at IS NULL OR a.query_record_id IS NULL
        OR a.provider_request_id IS NULL OR a.delivery_certainty NOT IN ('NOT_SENT',
                  'RESPONSE_RECEIVED')))
 THEN RAISE EXCEPTION 'ambiguous historical provider cancellation' USING ERRCODE='23514'; END IF;
END $$;
        CREATE OR REPLACE FUNCTION pr204_require_execution_event() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE matching_events integer;
        DECLARE context jsonb;
        DECLARE context_integer_key text;
        DECLARE query_item jsonb;
        DECLARE query_total integer;
        DECLARE reserved_total integer;
        DECLARE unknown_total integer;
        DECLARE successful_query_total integer;
        BEGIN
          IF TG_OP = 'INSERT' THEN
            -- Admission only: later supersession preserves this exact historical binding.
            IF NOT EXISTS (
              SELECT 1 FROM literature_search_plan_versions v
              JOIN literature_search_plans p ON p.id = v.plan_id
              WHERE v.id = NEW.search_plan_version_id
                AND p.project_id = NEW.project_id AND v.status = 'FROZEN'
            ) THEN
              RAISE EXCEPTION 'PR2-04 admission requires a same-project FROZEN plan version'
                USING ERRCODE = 'P17D5';
            END IF;
            context := NEW.execution_context;
            -- Prove JSON integer types before casts: text extraction alone
            -- would coerce numeric strings and let JSON null evade bounds.
            FOREACH context_integer_key IN ARRAY ARRAY[
              'max_results','max_provider_attempts','timeout_seconds','execution_budget_seconds'
            ] LOOP
              IF jsonb_typeof(context->context_integer_key) IS DISTINCT FROM 'number'
                 OR (context->>context_integer_key) !~ '^-?[0-9]+$' THEN
                RAISE EXCEPTION 'PR2-04 execution context requires JSON integers' USING
                  ERRCODE = 'P17D5';
              END IF;
            END LOOP;
            IF jsonb_typeof(context) <> 'object'
               OR NOT (context ?& ARRAY['schema_version','provider_id','provider_version',
                  'queries','max_results','max_provider_attempts','timeout_seconds',
                  'execution_budget_seconds'])
               OR context - ARRAY['schema_version','provider_id','provider_version','queries',
                  'max_results','max_provider_attempts','timeout_seconds',
                  'execution_budget_seconds'] <> '{}'::jsonb
               OR context->>'schema_version' <> '1'
               OR jsonb_typeof(context->'provider_id') <> 'string'
               OR normalize(context->>'provider_id', NFC) IS DISTINCT FROM context->>'provider_id'
               OR length(btrim(context->>'provider_id',
                  U&'\0009\000A\000B\000C\000D\001C\001D\001E\001F\0020\0085\00A0'
'\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200A'
'\2028\2029\202F\205F\3000')) = 0
               OR length(context->>'provider_id') NOT BETWEEN 1 AND 128
               OR jsonb_typeof(context->'provider_version') <> 'string'
               OR normalize(context->>'provider_version', NFC) IS DISTINCT FROM
                  context->>'provider_version'
               OR length(btrim(context->>'provider_version',
                  U&'\0009\000A\000B\000C\000D\001C\001D\001E\001F\0020\0085\00A0'
'\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200A'
'\2028\2029\202F\205F\3000')) = 0
               OR length(context->>'provider_version') NOT BETWEEN 1 AND 128
               OR jsonb_typeof(context->'queries') <> 'array'
               OR jsonb_array_length(context->'queries') NOT BETWEEN 1 AND 32
               OR (context->>'max_results')::numeric NOT BETWEEN 1 AND 100
               OR (context->>'max_provider_attempts')::numeric NOT BETWEEN 1 AND 3
               OR (context->>'timeout_seconds')::numeric NOT BETWEEN 1 AND 30
               OR (context->>'execution_budget_seconds')::numeric NOT BETWEEN 1 AND 600 THEN
              RAISE EXCEPTION 'PR2-04 execution context has an invalid closed shape' USING
                  ERRCODE = 'P17D5';
            END IF;
            FOR query_item IN SELECT value FROM jsonb_array_elements(context->'queries') LOOP
              IF jsonb_typeof(query_item) <> 'object'
                 OR NOT (query_item ?& ARRAY['query_type','query_text','perspective'])
                 OR query_item - ARRAY['query_type','query_text','perspective'] <> '{}'::jsonb
                 OR query_item->>'query_type' <> 'TEXT'
                 OR jsonb_typeof(query_item->'query_text') <> 'string'
                 OR length(btrim(query_item->>'query_text')) NOT BETWEEN 1 AND 4096
                 OR (jsonb_typeof(query_item->'perspective') NOT IN ('null','string'))
                 OR (jsonb_typeof(query_item->'perspective') = 'string'
                     AND length(query_item->>'perspective') > 256) THEN
                RAISE EXCEPTION 'PR2-04 query input has an invalid closed shape' USING ERRCODE
                  = 'P17D5';
              END IF;
            END LOOP;
            SELECT count(*) INTO matching_events
              FROM literature_search_execution_events
             WHERE execution_id = NEW.id AND kind = 'CREATED'
               AND sequence = 0 AND prior_status IS NULL
               AND new_status = NEW.status AND new_row_version = NEW.row_version
               AND prior_row_version IS NULL;
          ELSE
            SELECT count(*) INTO matching_events
              FROM literature_search_execution_events
             WHERE execution_id = NEW.id
               AND prior_status = OLD.status AND new_status = NEW.status
               AND prior_row_version = OLD.row_version
               AND new_row_version = NEW.row_version;
          END IF;
          IF matching_events <> 1 THEN
            RAISE EXCEPTION 'PR2-04 execution mutation requires exactly one matching event'
              USING ERRCODE = 'P17D5';
          END IF;
          IF TG_OP = 'UPDATE' AND NEW.status IS DISTINCT FROM OLD.status THEN
            SELECT count(*) INTO reserved_total
              FROM literature_search_provider_attempts
             WHERE execution_id = NEW.id AND status = 'RESERVED';
            SELECT count(*) INTO unknown_total
              FROM literature_search_provider_attempts
             WHERE execution_id = NEW.id AND status = 'UNKNOWN';
            IF NEW.status = 'RUNNING' AND reserved_total <> 1 THEN
              RAISE EXCEPTION 'PR2-04 RUNNING transition requires one reserved attempt' USING
                  ERRCODE = 'P17D5';
            ELSIF NEW.status = 'SUCCEEDED' THEN
              SELECT count(DISTINCT query_index) INTO successful_query_total
                FROM literature_search_provider_attempts
               WHERE execution_id = NEW.id AND status = 'SUCCEEDED';
              IF successful_query_total <> jsonb_array_length(NEW.execution_context->'queries') THEN
                RAISE EXCEPTION 'PR2-04 SUCCEEDED requires every input query' USING ERRCODE =
                  'P17D5';
              END IF;
            ELSIF NEW.status = 'UNKNOWN' AND unknown_total = 0 THEN
              RAISE EXCEPTION 'PR2-04 UNKNOWN requires an uncertain provider attempt' USING
                  ERRCODE = 'P17D5';
            ELSIF NEW.status = 'CANCELLED' THEN
              IF reserved_total <> 0 OR unknown_total <> 0 OR NOT (EXISTS (
                SELECT 1 FROM literature_search_execution_events
                 WHERE execution_id = NEW.id AND kind = 'CANCEL_REQUESTED'
              ) OR (OLD.status = 'RUNNING' AND EXISTS (
                SELECT 1 FROM literature_search_provider_attempts a
                JOIN search_query_records q ON q.id = a.query_record_id
                  AND q.provider_attempt_id = a.id
                  AND q.literature_search_execution_id = a.execution_id
                JOIN literature_search_execution_events v ON v.execution_id = a.execution_id
                  AND v.attempt_id = a.id AND v.kind = 'OUTCOME_RECORDED'
                WHERE a.execution_id = NEW.id AND a.status = 'CANCELLED'
                  AND a.failure_code = 'CANCELLED' AND a.row_version = 2
                  AND a.invoked_at IS NOT NULL AND a.returned_at IS NOT NULL
                  AND a.provider_request_id IS NOT NULL
                  AND a.delivery_certainty IN ('NOT_SENT','RESPONSE_RECEIVED')
                  AND q.executed_at = a.invoked_at
                  AND q.provider_id = NEW.execution_context->>'provider_id'
                  AND q.provider_version = NEW.execution_context->>'provider_version'
              ))) THEN
                RAISE EXCEPTION
                  'PR2-04 CANCELLED requires resolved intent or bound provider confirmation'
                  USING ERRCODE = 'P17D5';
              END IF;
              IF OLD.status = 'PLANNED' AND EXISTS (
                SELECT 1 FROM literature_search_provider_attempts WHERE execution_id = NEW.id
              ) THEN
                RAISE EXCEPTION 'PR2-04 pre-start cancellation cannot have attempts' USING
                  ERRCODE = 'P17D5';
              END IF;
            ELSIF NEW.status = 'FAILED'
              AND NEW.failure_code NOT IN ('PROVIDER_PERMANENT','PROVIDER_MALFORMED',
                  'PROVIDER_RETRY_EXHAUSTED','RECOVERY_INTERRUPTED') THEN
              RAISE EXCEPTION 'PR2-04 FAILED reason is not canonical' USING ERRCODE = 'P17D5';
            END IF;
          END IF;
          RETURN NULL;
        END; $$;

CREATE FUNCTION pr204_validate_provider_cancellation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.status = 'CANCELLED' AND NOT EXISTS (
   SELECT 1 FROM search_query_records q
   WHERE q.id=NEW.query_record_id AND q.provider_attempt_id=NEW.id
     AND q.literature_search_execution_id=NEW.execution_id AND q.executed_at=NEW.invoked_at
 ) THEN
   RAISE EXCEPTION 'provider cancellation requires bound invocation query' USING ERRCODE='P17D5';
 END IF;
 IF NEW.status = 'CANCELLED' AND (NEW.invoked_at IS NULL OR NEW.returned_at IS NULL
   OR NEW.provider_request_id IS NULL OR NEW.delivery_certainty NOT IN ('NOT_SENT',
                  'RESPONSE_RECEIVED')) THEN
   RAISE EXCEPTION 'provider cancellation requires confirmed response' USING ERRCODE='P17D5';
 END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER trg_pr204_provider_cancellation_commit
AFTER INSERT OR UPDATE ON literature_search_provider_attempts DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION pr204_validate_provider_cancellation();""")


def downgrade() -> None:
    op.execute("""LOCK TABLE literature_search_executions, literature_search_execution_events,
 literature_search_provider_attempts, literature_search_execution_command_receipts,
 search_query_records, search_result_records IN ACCESS EXCLUSIVE MODE;
DO $$ BEGIN
 IF EXISTS (SELECT 1 FROM literature_search_executions)
 OR EXISTS (SELECT 1 FROM literature_search_provider_attempts)
 OR EXISTS (SELECT 1 FROM search_query_records) OR EXISTS (SELECT 1 FROM search_result_records)
 OR EXISTS (SELECT 1 FROM literature_search_execution_events)
 OR EXISTS (SELECT 1 FROM literature_search_execution_command_receipts)
 THEN RAISE EXCEPTION 'cannot downgrade populated provider cancellation history' USING
                  ERRCODE='23514'; END IF;
END $$;
DROP TRIGGER trg_pr204_provider_cancellation_commit ON literature_search_provider_attempts;
DROP FUNCTION pr204_validate_provider_cancellation();""")
    op.execute(_BASE_REQUIRE_EVENT)
