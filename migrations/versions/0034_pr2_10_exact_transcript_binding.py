"""Enforce the contracted exact transcript ArtifactVersion FK without a seal column."""

# ruff: noqa: E501

from alembic import op

revision = "0034_pr2_10_exact_transcript_binding"
down_revision = "0033_pr2_11_r2_scientific_conclusion"
branch_labels = None
depends_on = None


ORIGINAL_SESSION_GUARD = """
CREATE OR REPLACE FUNCTION pr210_session_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
    AND NEW.closed_at >= (SELECT max(created_at) FROM discussion_turns
                          WHERE session_id=OLD.id)
    AND EXISTS (SELECT 1 FROM discussion_turns WHERE session_id=OLD.id) THEN
    RETURN NEW;
  END IF;
  RAISE EXCEPTION 'discussion state or history immutable' USING ERRCODE='P17D2';
END $$
"""


def upgrade() -> None:
    op.execute("""
    ALTER TABLE discussion_sessions ADD COLUMN transcript_artifact_version_id UUID
      REFERENCES artifact_versions(id) ON DELETE RESTRICT;
    CREATE INDEX ix_pr210_session_transcript_artifact_version
      ON discussion_sessions(transcript_artifact_version_id);
    DO $$ DECLARE old_check name;
    BEGIN
      SELECT conname INTO STRICT old_check FROM pg_constraint
       WHERE conrelid='discussion_command_receipts'::regclass AND contype='c'
         AND pg_get_constraintdef(oid) LIKE '%command_name%'
         AND pg_get_constraintdef(oid) LIKE '%CREATE_SESSION%'
         AND pg_get_constraintdef(oid) LIKE '%APPEND_TURN%'
         AND pg_get_constraintdef(oid) LIKE '%CLOSE_SESSION%';
      EXECUTE format('ALTER TABLE discussion_command_receipts DROP CONSTRAINT %I', old_check);
    END $$;
    ALTER TABLE discussion_command_receipts
      ADD CONSTRAINT ck_pr210_receipt_command_with_binding CHECK
      (command_name IN ('CREATE_SESSION','APPEND_TURN','CLOSE_SESSION','BIND_TRANSCRIPT'));
    """)
    op.execute("""
    CREATE FUNCTION pr210_cjson_time(value TIMESTAMPTZ) RETURNS TEXT
    LANGUAGE plpgsql AS $$
    DECLARE instant TIMESTAMP; spelled TEXT;
    BEGIN
      IF value IS NULL OR extract(year FROM value AT TIME ZONE 'UTC') NOT BETWEEN 1 AND 9999
      THEN
        RAISE EXCEPTION 'unsupported discussion instant' USING ERRCODE='P17D3';
      END IF;
      instant := value AT TIME ZONE 'UTC';
      spelled := to_char(instant,'YYYY-MM-DD"T"HH24:MI:SS');
      IF extract(microseconds FROM instant)::integer % 1000000 <> 0 THEN
        spelled := spelled || '.' || to_char(instant,'US');
      END IF;
      RETURN to_json(spelled || 'Z')::text;
    END $$;

    CREATE FUNCTION pr210_transcript_cjson(target_session_id UUID) RETURNS TEXT
    LANGUAGE plpgsql AS $$
    DECLARE s RECORD; questions TEXT; claims TEXT; sources TEXT; turns TEXT;
    BEGIN
      SELECT * INTO s FROM discussion_sessions WHERE id=target_session_id;
      IF NOT FOUND OR s.status<>'CLOSED' OR s.closed_at IS NULL THEN
        RAISE EXCEPTION 'closed discussion required' USING ERRCODE='P17D3';
      END IF;
      SELECT '[' || COALESCE(string_agg(to_json(version_id::text)::text,',' ORDER BY ordinal),'') || ']'
        INTO questions FROM discussion_session_question_inputs WHERE session_id=s.id;
      SELECT '[' || COALESCE(string_agg(to_json(version_id::text)::text,',' ORDER BY ordinal),'') || ']'
        INTO claims FROM discussion_session_claim_inputs WHERE session_id=s.id;
      SELECT '[' || COALESCE(string_agg(to_json(version_id::text)::text,',' ORDER BY ordinal),'') || ']'
        INTO sources FROM discussion_session_source_inputs WHERE session_id=s.id;
      SELECT '[' || COALESCE(string_agg(
        '{"actor_id":' || to_json(t.actor_id::text)::text ||
        ',"cited_claim_version_ids":' ||
          (SELECT '[' || COALESCE(string_agg(to_json(c.version_id::text)::text,',' ORDER BY c.ordinal),'') || ']'
           FROM discussion_turn_claim_citations c WHERE c.turn_id=t.id) ||
        ',"cited_source_version_ids":' ||
          (SELECT '[' || COALESCE(string_agg(to_json(c.version_id::text)::text,',' ORDER BY c.ordinal),'') || ']'
           FROM discussion_turn_source_citations c WHERE c.turn_id=t.id) ||
        ',"created_at":' || pr210_cjson_time(t.created_at) ||
        ',"id":' || to_json(t.id::text)::text ||
        ',"ordinal":' || t.ordinal::text ||
        ',"role":' || to_json(t.role)::text ||
        ',"utterance":' || to_json(t.utterance)::text || '}',
        ',' ORDER BY t.ordinal),'') || ']'
        INTO turns FROM discussion_turns t WHERE t.session_id=s.id;
      IF turns='[]' THEN
        RAISE EXCEPTION 'discussion has no turns' USING ERRCODE='P17D3';
      END IF;
      RETURN '{"artifact_role":"discussion_transcript","closed_at":' ||
        pr210_cjson_time(s.closed_at) || ',"created_at":' || pr210_cjson_time(s.created_at) ||
        ',"created_by":' || to_json(s.created_by::text)::text ||
        ',"input_claim_version_ids":' || claims ||
        ',"input_research_question_version_ids":' || questions ||
        ',"input_source_version_ids":' || sources ||
        ',"project_id":' || to_json(s.project_id::text)::text ||
        ',"session_id":' || to_json(s.id::text)::text ||
        ',"topic":' || to_json(s.topic)::text ||
        ',"turns":' || turns || '}';
    END $$;
    """)
    op.execute("""
    CREATE OR REPLACE FUNCTION pr210_session_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE payload TEXT;
    BEGIN
      IF TG_OP='INSERT' THEN
        IF NEW.status<>'OPEN' OR NEW.row_version<>1
           OR NEW.closed_by IS NOT NULL OR NEW.closed_at IS NOT NULL
           OR NEW.transcript_artifact_version_id IS NOT NULL THEN
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
        AND NEW.closed_at >= (SELECT max(created_at) FROM discussion_turns
                              WHERE session_id=OLD.id)
        AND EXISTS (SELECT 1 FROM discussion_turns WHERE session_id=OLD.id)
        AND OLD.transcript_artifact_version_id IS NULL
        AND NEW.transcript_artifact_version_id IS NULL THEN
        RETURN NEW;
      END IF;
      IF TG_OP='UPDATE' AND OLD.status='CLOSED' AND NEW.status='CLOSED'
        AND OLD.transcript_artifact_version_id IS NULL
        AND NEW.transcript_artifact_version_id IS NOT NULL
        AND NEW.row_version=OLD.row_version+1
        AND NEW.id=OLD.id AND NEW.project_id=OLD.project_id
        AND NEW.topic=OLD.topic AND NEW.created_by=OLD.created_by
        AND NEW.created_at=OLD.created_at
        AND NEW.closed_by=OLD.closed_by AND NEW.closed_at=OLD.closed_at THEN
        payload := pr210_transcript_cjson(OLD.id);
        PERFORM 1 FROM artifact_versions v JOIN artifacts a ON a.id=v.artifact_id
         WHERE v.id=NEW.transcript_artifact_version_id
           AND v.status='FROZEN' AND v.frozen_at IS NOT NULL
           AND v.media_type='application/json'
           AND v.content_hash=encode(sha256(convert_to(payload,'UTF8')),'hex')
           AND v.byte_size=octet_length(convert_to(payload,'UTF8'))
           AND a.project_id=NEW.project_id AND a.artifact_type='discussion_transcript'
         FOR SHARE OF v,a;
        IF NOT FOUND THEN
          RAISE EXCEPTION 'discussion transcript version does not match sealed rows'
            USING ERRCODE='P17D3';
        END IF;
        RETURN NEW;
      END IF;
      RAISE EXCEPTION 'discussion state or history immutable' USING ERRCODE='P17D2';
    END $$;

    CREATE FUNCTION pr210_bound_artifact_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_TABLE_NAME='artifact_versions' THEN
        IF EXISTS (SELECT 1 FROM discussion_sessions s
                   WHERE s.transcript_artifact_version_id=OLD.id)
           AND (NEW.status NOT IN ('FROZEN','SUPERSEDED')
                OR NEW.artifact_id IS DISTINCT FROM OLD.artifact_id) THEN
          RAISE EXCEPTION 'bound transcript version must remain immutable'
            USING ERRCODE='P17D3';
        END IF;
      ELSIF EXISTS (SELECT 1 FROM discussion_sessions s
                    JOIN artifact_versions v ON v.id=s.transcript_artifact_version_id
                   WHERE v.artifact_id=OLD.id)
        AND (NEW.project_id IS DISTINCT FROM OLD.project_id
             OR NEW.artifact_type IS DISTINCT FROM OLD.artifact_type) THEN
        RAISE EXCEPTION 'bound transcript artifact identity immutable'
          USING ERRCODE='P17D3';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER pr210_bound_version_guard BEFORE UPDATE ON artifact_versions
      FOR EACH ROW EXECUTE FUNCTION pr210_bound_artifact_guard();
    CREATE TRIGGER pr210_bound_artifact_guard BEFORE UPDATE ON artifacts
      FOR EACH ROW EXECUTE FUNCTION pr210_bound_artifact_guard();
    """)


def downgrade() -> None:
    op.execute("""
    LOCK TABLE discussion_sessions,discussion_command_receipts IN ACCESS EXCLUSIVE MODE;
    DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM discussion_sessions
                  WHERE transcript_artifact_version_id IS NOT NULL)
         OR EXISTS (SELECT 1 FROM discussion_command_receipts
                     WHERE command_name='BIND_TRANSCRIPT') THEN
        RAISE EXCEPTION 'PR2-10 binding downgrade preserves history'
          USING ERRCODE='P17D5';
      END IF;
    END $$;
    DROP TRIGGER pr210_bound_version_guard ON artifact_versions;
    DROP TRIGGER pr210_bound_artifact_guard ON artifacts;
    DROP FUNCTION pr210_bound_artifact_guard();
    ALTER TABLE discussion_command_receipts
      DROP CONSTRAINT ck_pr210_receipt_command_with_binding;
    ALTER TABLE discussion_command_receipts
      ADD CONSTRAINT ck_pr210_receipt_command_original CHECK
      (command_name IN ('CREATE_SESSION','APPEND_TURN','CLOSE_SESSION'));
    """)
    op.execute(ORIGINAL_SESSION_GUARD)
    op.execute("""
    DROP FUNCTION pr210_transcript_cjson(UUID);
    DROP FUNCTION pr210_cjson_time(TIMESTAMPTZ);
    DROP INDEX ix_pr210_session_transcript_artifact_version;
    ALTER TABLE discussion_sessions DROP COLUMN transcript_artifact_version_id;
    """)
