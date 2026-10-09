"""PR2-03 independent-review backstops; preserve 0023 and scientific history."""
# ruff: noqa: E501
from alembic import op

revision = '0023a_search_plan_review_guards'
down_revision = '0023_literature_search_plan'
branch_labels = None
depends_on = None

# Python str.strip whitespace, without adding a language/normalization policy.
WHITESPACE = r"U&'\0009\000A\000B\000C\000D\001C\001D\001E\001F\0020\0085\00A0\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200A\2028\2029\202F\205F\3000'"
INDEXES = (
    ('ix_lsp_created_by', 'literature_search_plans', ['created_by']),
    ('ix_lsp_current_version', 'literature_search_plans', ['current_version_id']),
    ('ix_lspv_created_by', 'literature_search_plan_versions', ['created_by']),
    ('ix_lsp_receipt_actor', 'literature_search_plan_command_receipts', ['actor_id']),
    ('ix_lsp_receipt_project', 'literature_search_plan_command_receipts', ['project_id', 'result_plan_id']),
    ('ix_lsp_receipt_plan', 'literature_search_plan_command_receipts', ['result_plan_id']),
)


def upgrade():
    # Fail closed: never repair immutable historical facts during upgrade.
    op.execute(f"""
    DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM literature_search_plan_versions WHERE length(btrim(objective,{WHITESPACE}))=0)
      OR EXISTS (SELECT 1 FROM literature_search_plans p JOIN literature_search_plan_versions v ON v.id=p.current_version_id WHERE v.status<>'FROZEN')
      OR EXISTS (SELECT 1 FROM literature_search_plan_versions v JOIN literature_search_plans p ON p.id=v.plan_id WHERE v.status='FROZEN' AND (v.id IS DISTINCT FROM p.current_version_id OR NOT EXISTS (SELECT 1 FROM search_plan_question_inputs i WHERE i.plan_version_id=v.id)))
      OR EXISTS (SELECT 1 FROM search_plan_question_inputs i JOIN research_question_versions q ON q.id=i.research_question_version_id GROUP BY i.plan_version_id,q.research_question_id HAVING count(*)>1)
      THEN RAISE EXCEPTION 'PR2-03 guard upgrade refused: invalid existing scientific state'; END IF;
    END $$;
    """)
    op.create_check_constraint('ck_lspv_objective_nonblank', 'literature_search_plan_versions', f'length(btrim(objective,{WHITESPACE}))>0')
    for name, table, columns in INDEXES:
        op.create_index(name, table, columns, unique=False)
    op.execute("""
    CREATE FUNCTION rb_lsp_initial_draft() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_TABLE_NAME='literature_search_plans' THEN
        IF NEW.current_version_id IS NOT NULL THEN RAISE EXCEPTION 'initial search plan cannot have a current version' USING ERRCODE='23514'; END IF;
      ELSIF NEW.status<>'DRAFT' THEN
        RAISE EXCEPTION 'search plan version must be inserted as DRAFT' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER trg_lsp_initial_draft BEFORE INSERT ON literature_search_plans FOR EACH ROW EXECUTE FUNCTION rb_lsp_initial_draft();
    CREATE TRIGGER trg_lspv_initial_draft BEFORE INSERT ON literature_search_plan_versions FOR EACH ROW EXECUTE FUNCTION rb_lsp_initial_draft();

    CREATE FUNCTION rb_lsp_final_state() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE pid uuid; current_id uuid;
    BEGIN
      IF TG_TABLE_NAME='literature_search_plans' THEN pid:=NEW.id; ELSE pid:=NEW.plan_id; END IF;
      SELECT current_version_id INTO current_id FROM literature_search_plans WHERE id=pid FOR UPDATE;
      IF (current_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM literature_search_plan_versions WHERE id=current_id AND plan_id=pid AND status='FROZEN'))
         OR EXISTS (SELECT 1 FROM literature_search_plan_versions WHERE plan_id=pid AND status='FROZEN' AND id IS DISTINCT FROM current_id)
      THEN RAISE EXCEPTION 'invalid search plan current/frozen relationship' USING ERRCODE='23514',CONSTRAINT='ck_lsp_current_frozen'; END IF;
      IF EXISTS (SELECT 1 FROM literature_search_plan_versions v WHERE v.plan_id=pid AND v.status IN ('FROZEN','SUPERSEDED') AND (v.language_scope IS NULL OR NOT EXISTS (SELECT 1 FROM search_plan_question_inputs i JOIN research_question_versions q ON q.id=i.research_question_version_id JOIN research_questions r ON r.id=q.research_question_id JOIN literature_search_plans p ON p.id=v.plan_id WHERE i.plan_version_id=v.id AND r.project_id=p.project_id AND q.status IN ('FROZEN','SUPERSEDED') AND q.content_hash IS NOT NULL AND q.frozen_at IS NOT NULL)))
      THEN RAISE EXCEPTION 'frozen search plan requires valid question inputs and language scope' USING ERRCODE='23514',CONSTRAINT='ck_lsp_frozen_inputs'; END IF;
      RETURN NULL;
    END $$;
    CREATE CONSTRAINT TRIGGER trg_lsp_final_state AFTER INSERT OR UPDATE ON literature_search_plans DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION rb_lsp_final_state();
    CREATE CONSTRAINT TRIGGER trg_lspv_final_state AFTER INSERT OR UPDATE ON literature_search_plan_versions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION rb_lsp_final_state();

    CREATE FUNCTION rb_spqi_serialize() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE vid uuid; pid uuid; state text;
    BEGIN
      IF TG_OP='DELETE' THEN vid:=OLD.plan_version_id; ELSE vid:=NEW.plan_version_id; END IF;
      SELECT plan_id INTO pid FROM literature_search_plan_versions WHERE id=vid;
      PERFORM 1 FROM literature_search_plans WHERE id=pid FOR UPDATE;
      SELECT status INTO state FROM literature_search_plan_versions WHERE id=vid FOR UPDATE;
      IF state<>'DRAFT' THEN RAISE EXCEPTION 'frozen search plan inputs are immutable' USING ERRCODE='P17D1'; END IF;
      -- A write, rather than only a lock, also makes stale repeatable-read/
      -- serializable contenders retry instead of validating an old snapshot.
      UPDATE literature_search_plan_versions SET row_version=row_version+1 WHERE id=vid;
      IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
    END $$;
    CREATE TRIGGER trg_spqi_00_serialize BEFORE INSERT OR UPDATE OR DELETE ON search_plan_question_inputs FOR EACH ROW EXECUTE FUNCTION rb_spqi_serialize();
    CREATE FUNCTION rb_spqi_unique_identity() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF EXISTS (SELECT 1 FROM search_plan_question_inputs i JOIN research_question_versions q ON q.id=i.research_question_version_id WHERE i.plan_version_id=NEW.plan_version_id GROUP BY q.research_question_id HAVING count(*)>1)
      THEN RAISE EXCEPTION 'duplicate ResearchQuestion identity in plan version' USING ERRCODE='23505',CONSTRAINT='uq_spqi_question_identity'; END IF;
      RETURN NULL;
    END $$;
    CREATE CONSTRAINT TRIGGER trg_spqi_identity_unique AFTER INSERT OR UPDATE ON search_plan_question_inputs DEFERRABLE INITIALLY IMMEDIATE FOR EACH ROW EXECUTE FUNCTION rb_spqi_unique_identity();
    """)


def downgrade():
    op.execute("""DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM literature_search_plans) OR EXISTS (SELECT 1 FROM literature_search_plan_versions) OR EXISTS (SELECT 1 FROM search_plan_question_inputs) OR EXISTS (SELECT 1 FROM literature_search_plan_command_receipts)
      THEN RAISE EXCEPTION 'PR2-03 guard downgrade refused: preserve populated scientific state'; END IF;
    END $$;""")
    for trigger, table in (('trg_spqi_identity_unique', 'search_plan_question_inputs'), ('trg_spqi_00_serialize', 'search_plan_question_inputs'), ('trg_lspv_final_state', 'literature_search_plan_versions'), ('trg_lsp_final_state', 'literature_search_plans'), ('trg_lspv_initial_draft', 'literature_search_plan_versions'), ('trg_lsp_initial_draft', 'literature_search_plans')):
        op.execute(f'DROP TRIGGER {trigger} ON {table}')
    for function in ('rb_spqi_unique_identity', 'rb_spqi_serialize', 'rb_lsp_final_state', 'rb_lsp_initial_draft'):
        op.execute(f'DROP FUNCTION {function}()')
    for name, table, _ in INDEXES:
        op.drop_index(name, table_name=table)
    op.drop_constraint('ck_lspv_objective_nonblank', 'literature_search_plan_versions', type_='check')
