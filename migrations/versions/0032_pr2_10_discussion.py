"""PR2-10 typed discussion sessions, immutable turns and exact references."""

# ruff: noqa: E501

from alembic import op

revision = "0032_pr2_10_discussion"
down_revision = "0031_m3_snapshot_relation_cardinality"
branch_labels = None
depends_on = None


TABLES = (
    "discussion_command_receipts",
    "discussion_turn_claim_citations",
    "discussion_turn_source_citations",
    "discussion_turns",
    "discussion_session_source_inputs",
    "discussion_session_claim_inputs",
    "discussion_session_question_inputs",
    "discussion_sessions",
)


def upgrade() -> None:
    op.execute("""
    CREATE TABLE discussion_sessions (
      id UUID PRIMARY KEY,
      project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
      topic VARCHAR(255) NOT NULL CHECK (length(btrim(topic)) BETWEEN 1 AND 255),
      status VARCHAR(16) NOT NULL CHECK (status IN ('OPEN','CLOSED','ARCHIVED')),
      created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
      created_at TIMESTAMPTZ NOT NULL,
      closed_by UUID REFERENCES actors(id) ON DELETE RESTRICT,
      closed_at TIMESTAMPTZ,
      row_version INTEGER NOT NULL CHECK (row_version > 0),
      CHECK ((status='OPEN' AND closed_by IS NULL AND closed_at IS NULL)
          OR (status IN ('CLOSED','ARCHIVED') AND closed_by IS NOT NULL
              AND closed_at IS NOT NULL AND closed_at>=created_at)),
      UNIQUE (project_id,id)
    );
    CREATE TABLE discussion_session_question_inputs (
      session_id UUID NOT NULL REFERENCES discussion_sessions(id) ON DELETE RESTRICT,
      version_id UUID NOT NULL REFERENCES research_question_versions(id) ON DELETE RESTRICT,
      ordinal INTEGER NOT NULL CHECK (ordinal>=0),
      PRIMARY KEY (session_id,version_id), UNIQUE (session_id,ordinal)
    );
    CREATE TABLE discussion_session_claim_inputs (
      session_id UUID NOT NULL REFERENCES discussion_sessions(id) ON DELETE RESTRICT,
      version_id UUID NOT NULL REFERENCES claim_versions(id) ON DELETE RESTRICT,
      ordinal INTEGER NOT NULL CHECK (ordinal>=0),
      PRIMARY KEY (session_id,version_id), UNIQUE (session_id,ordinal)
    );
    CREATE TABLE discussion_session_source_inputs (
      session_id UUID NOT NULL REFERENCES discussion_sessions(id) ON DELETE RESTRICT,
      version_id UUID NOT NULL REFERENCES source_versions(id) ON DELETE RESTRICT,
      ordinal INTEGER NOT NULL CHECK (ordinal>=0),
      PRIMARY KEY (session_id,version_id), UNIQUE (session_id,ordinal)
    );
    CREATE TABLE discussion_turns (
      id UUID PRIMARY KEY,
      session_id UUID NOT NULL REFERENCES discussion_sessions(id) ON DELETE RESTRICT,
      ordinal INTEGER NOT NULL CHECK (ordinal>=1),
      actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
      role VARCHAR(32) NOT NULL CHECK (role IN
        ('human','moderator','literature_expert','method_expert',
         'statistician','domain_critic','other')),
      utterance TEXT NOT NULL CHECK (length(btrim(utterance)) BETWEEN 1 AND 16000),
      created_at TIMESTAMPTZ NOT NULL,
      UNIQUE (session_id,ordinal), UNIQUE (session_id,id)
    );
    CREATE TABLE discussion_turn_source_citations (
      turn_id UUID NOT NULL REFERENCES discussion_turns(id) ON DELETE RESTRICT,
      version_id UUID NOT NULL REFERENCES source_versions(id) ON DELETE RESTRICT,
      ordinal INTEGER NOT NULL CHECK (ordinal>=0),
      PRIMARY KEY (turn_id,version_id), UNIQUE (turn_id,ordinal)
    );
    CREATE TABLE discussion_turn_claim_citations (
      turn_id UUID NOT NULL REFERENCES discussion_turns(id) ON DELETE RESTRICT,
      version_id UUID NOT NULL REFERENCES claim_versions(id) ON DELETE RESTRICT,
      ordinal INTEGER NOT NULL CHECK (ordinal>=0),
      PRIMARY KEY (turn_id,version_id), UNIQUE (turn_id,ordinal)
    );
    CREATE TABLE discussion_command_receipts (
      id UUID PRIMARY KEY,
      deployment_id TEXT NOT NULL,
      project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
      actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
      command_name VARCHAR(24) NOT NULL CHECK
        (command_name IN ('CREATE_SESSION','APPEND_TURN','CLOSE_SESSION')),
      request_id UUID NOT NULL,
      input_hash CHAR(64) NOT NULL CHECK (input_hash ~ '^[0-9a-f]{64}$'),
      result_session_id UUID NOT NULL,
      result_turn_id UUID REFERENCES discussion_turns(id) ON DELETE RESTRICT,
      completed_at TIMESTAMPTZ NOT NULL,
      FOREIGN KEY (project_id,result_session_id)
        REFERENCES discussion_sessions(project_id,id) ON DELETE RESTRICT,
      FOREIGN KEY (result_session_id,result_turn_id)
        REFERENCES discussion_turns(session_id,id) ON DELETE RESTRICT,
      CHECK ((command_name='APPEND_TURN')=(result_turn_id IS NOT NULL)),
      UNIQUE (deployment_id,project_id,actor_id,command_name,request_id)
    );
    CREATE INDEX ix_discussion_sessions_project_status
      ON discussion_sessions(project_id,status,created_at,id);
    CREATE INDEX ix_discussion_turns_session_ordinal
      ON discussion_turns(session_id,ordinal);
    """)
    op.execute("""
    CREATE FUNCTION pr210_session_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP='INSERT' THEN
        IF NEW.status<>'OPEN' OR NEW.row_version<>1
           OR NEW.closed_by IS NOT NULL OR NEW.closed_at IS NOT NULL THEN
          RAISE EXCEPTION 'discussion must start open' USING ERRCODE='P17D2';
        END IF;
        RETURN NEW;
      END IF;
      IF TG_OP='UPDATE' AND OLD.status='OPEN' AND NEW.status='CLOSED'
        AND NEW.row_version=OLD.row_version+1
        AND NEW.id=OLD.id AND NEW.project_id=OLD.project_id
        AND NEW.topic=OLD.topic AND NEW.created_by=OLD.created_by
        AND NEW.created_at=OLD.created_at AND NEW.closed_by IS NOT NULL
        AND NEW.closed_at>=OLD.created_at
        AND EXISTS (SELECT 1 FROM discussion_turns WHERE session_id=OLD.id) THEN
        RETURN NEW;
      END IF;
      RAISE EXCEPTION 'discussion state or history immutable' USING ERRCODE='P17D2';
    END $$;
    CREATE TRIGGER pr210_session_guard BEFORE INSERT OR UPDATE OR DELETE
      ON discussion_sessions FOR EACH ROW EXECUTE FUNCTION pr210_session_guard();

    CREATE FUNCTION pr210_reference_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE sid UUID; pid UUID; state TEXT; valid BOOLEAN;
    BEGIN
      IF TG_TABLE_NAME IN ('discussion_session_question_inputs',
                           'discussion_session_claim_inputs',
                           'discussion_session_source_inputs') THEN
        sid := NEW.session_id;
      ELSIF TG_TABLE_NAME='discussion_turns' THEN
        sid := NEW.session_id;
      ELSE
        SELECT session_id INTO sid FROM discussion_turns WHERE id=NEW.turn_id;
      END IF;
      SELECT project_id,status INTO pid,state FROM discussion_sessions
        WHERE id=sid FOR UPDATE;
      IF pid IS NULL OR state<>'OPEN' THEN
        RAISE EXCEPTION 'discussion session must be open' USING ERRCODE='P17D2';
      END IF;
      IF TG_TABLE_NAME IN ('discussion_session_question_inputs',
                           'discussion_session_claim_inputs',
                           'discussion_session_source_inputs')
         AND NOT EXISTS(SELECT 1 FROM discussion_sessions
                        WHERE id=sid AND xmin::text::bigint=
                          pg_current_xact_id()::text::bigint) THEN
        RAISE EXCEPTION 'discussion input set is sealed' USING ERRCODE='P17D1';
      END IF;
      IF TG_TABLE_NAME='discussion_session_question_inputs' THEN
        SELECT EXISTS(SELECT 1 FROM research_question_versions v
          JOIN research_questions q ON q.id=v.research_question_id
          WHERE v.id=NEW.version_id AND q.project_id=pid
            AND v.status IN ('FROZEN','SUPERSEDED')) INTO valid;
        valid := valid AND NEW.ordinal=(SELECT COALESCE(max(ordinal),-1)+1
          FROM discussion_session_question_inputs WHERE session_id=sid);
      ELSIF TG_TABLE_NAME='discussion_session_claim_inputs' THEN
        SELECT EXISTS(SELECT 1 FROM claim_versions v
          JOIN claims c ON c.id=v.claim_id
          WHERE v.id=NEW.version_id AND c.project_id=pid
            AND v.status IN ('FROZEN','SUPERSEDED')) INTO valid;
        valid := valid AND NEW.ordinal=(SELECT COALESCE(max(ordinal),-1)+1
          FROM discussion_session_claim_inputs WHERE session_id=sid);
      ELSIF TG_TABLE_NAME='discussion_session_source_inputs' THEN
        SELECT EXISTS(SELECT 1 FROM source_versions v
          JOIN literature_source_project_links l
            ON l.literature_source_id=v.literature_source_id
          WHERE v.id=NEW.version_id AND l.project_id=pid
            AND v.status IN ('FROZEN','SUPERSEDED')) INTO valid;
        valid := valid AND NEW.ordinal=(SELECT COALESCE(max(ordinal),-1)+1
          FROM discussion_session_source_inputs WHERE session_id=sid);
      ELSIF TG_TABLE_NAME='discussion_turn_source_citations' THEN
        SELECT EXISTS(SELECT 1 FROM discussion_session_source_inputs i
          WHERE i.session_id=sid AND i.version_id=NEW.version_id) INTO valid;
        valid := valid AND NEW.ordinal=(SELECT COALESCE(max(ordinal),-1)+1
          FROM discussion_turn_source_citations WHERE turn_id=NEW.turn_id);
      ELSIF TG_TABLE_NAME='discussion_turn_claim_citations' THEN
        SELECT EXISTS(SELECT 1 FROM discussion_session_claim_inputs i
          WHERE i.session_id=sid AND i.version_id=NEW.version_id) INTO valid;
        valid := valid AND NEW.ordinal=(SELECT COALESCE(max(ordinal),-1)+1
          FROM discussion_turn_claim_citations WHERE turn_id=NEW.turn_id);
      ELSE
        valid := NEW.ordinal=(SELECT COALESCE(max(ordinal),0)+1
                              FROM discussion_turns WHERE session_id=sid);
        valid := valid AND NEW.created_at >=
          (SELECT COALESCE(max(created_at),
                   (SELECT created_at FROM discussion_sessions WHERE id=sid))
             FROM discussion_turns WHERE session_id=sid);
      END IF;
      IF NOT COALESCE(valid,FALSE) THEN
        RAISE EXCEPTION 'discussion reference or order invalid' USING ERRCODE='P17D3';
      END IF;
      RETURN NEW;
    END $$;
    """)
    for table in TABLES[1:-1]:
        op.execute(
            f"CREATE TRIGGER pr210_reference_guard BEFORE INSERT ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION pr210_reference_guard()"
        )
        op.execute(
            f"CREATE TRIGGER pr210_immutable BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION m2_immutable()"
        )
    op.execute("""
      CREATE TRIGGER pr210_receipt_immutable BEFORE UPDATE OR DELETE
        ON discussion_command_receipts FOR EACH ROW EXECUTE FUNCTION m2_immutable();
    """)


def downgrade() -> None:
    op.execute("LOCK TABLE " + ",".join(TABLES) + " IN ACCESS EXCLUSIVE MODE")
    for table in TABLES:
        op.execute(
            f"DO $$ BEGIN IF EXISTS(SELECT 1 FROM {table}) THEN "
            "RAISE EXCEPTION 'PR2-10 downgrade preserves discussion history' "
            "USING ERRCODE='P17D5'; END IF; END $$"
        )
    for table in TABLES:
        op.execute(f"DROP TABLE {table}")
    op.execute("DROP FUNCTION pr210_reference_guard(); DROP FUNCTION pr210_session_guard()")
