"""PR2-17 S1 immutable contribution and authorship foundation only."""

from alembic import op

revision = "0046_pr2_17_authorship"
down_revision = "0045_pr2_16_basic_approval"
branch_labels = None
depends_on = None

TABLES = (
    "contribution_records",
    "authorship_snapshots",
    "authorship_snapshot_authors",
    "authorship_snapshot_corresponding_authors",
    "authorship_snapshot_equal_groups",
    "authorship_snapshot_contributions",
)
ALIASES = {
    "authorship_snapshot_authors": "as_authors",
    "authorship_snapshot_corresponding_authors": "as_corresponding",
    "authorship_snapshot_equal_groups": "as_equal_groups",
    "authorship_snapshot_contributions": "as_contributions",
}


def _name(prefix, table, suffix=""):
    name = f"{prefix}_{table}" + (f"_{suffix}" if suffix else "")
    if len(name) > 63:
        name = f"{prefix}_{ALIASES.get(table, table)}" + (f"_{suffix}" if suffix else "")
    return name


def upgrade():
    for table in TABLES:
        columns = [
            f"id UUID NOT NULL CONSTRAINT {_name('pk', table)} PRIMARY KEY",
            "created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()",
            f"created_by UUID NOT NULL CONSTRAINT {_name('fk', table, 'created_by')} "
            "REFERENCES actors(id) ON DELETE RESTRICT",
        ]
        fks = ["created_by"]
        leading = {"id"}

        def fk(column, target, columns=columns, table=table, fks=fks):
            columns.append(
                f"{column} UUID NOT NULL CONSTRAINT {_name('fk', table, column)} "
                f"REFERENCES {target}(id) ON DELETE RESTRICT"
            )
            fks.append(column)

        def check(label, expression, columns=columns, table=table):
            columns.append(f"CONSTRAINT {_name('ck', table, label)} CHECK ({expression})")

        def unique(label, fields, columns=columns, table=table, leading=leading):
            columns.append(f"CONSTRAINT {_name('uq', table, label)} UNIQUE ({fields})")
            leading.add(fields.split(",")[0])

        if table in TABLES[:2]:
            columns += ["content_hash CHAR(64) NOT NULL", "hash_scheme VARCHAR(32) NOT NULL"]
            check("digest", "content_hash IS NULL OR content_hash ~ '^[0-9a-f]{64}$'")
            check("scheme", "hash_scheme = 'sha256-cjson-v1'")
            fk("publication_id", "publications")
            unique("parent_id", "publication_id,id")
        if table == "contribution_records":
            fk("actor_id", "actors")
            fk("recorded_by", "actors")
            columns += [
                "contribution_role VARCHAR(24) NOT NULL",
                "contribution_statement TEXT NOT NULL",
            ]
            check(
                "role",
                "contribution_role IN ('CONCEPTUALIZATION','INVESTIGATION','ANALYSIS',"
                "'SOFTWARE','WRITING','REVIEW')",
            )
            check(
                "statement",
                "length(contribution_statement) BETWEEN 1 AND 10000 "
                "AND contribution_statement ~ '[^[:space:]]'",
            )
            check("recorder", "recorded_by = created_by")
            check("nfc", "contribution_statement = normalize(contribution_statement, NFC)")
        elif table in TABLES[2:]:
            if table in (TABLES[3], TABLES[4]):
                columns += ["authorship_snapshot_id UUID NOT NULL", "actor_id UUID NOT NULL"]
                fks += ["authorship_snapshot_id", "actor_id"]
                constraint = (
                    "fk_corresponding_author" if table == TABLES[3] else "fk_equal_group_author"
                )
                columns.append(
                    f"CONSTRAINT {constraint} FOREIGN KEY (authorship_snapshot_id,actor_id) "
                    "REFERENCES authorship_snapshot_authors(authorship_snapshot_id,actor_id) "
                    "ON DELETE RESTRICT"
                )
            else:
                fk("authorship_snapshot_id", "authorship_snapshots")
                if table == TABLES[2]:
                    fk("actor_id", "actors")
                else:
                    fk("contribution_record_id", "contribution_records")
            columns.append("ordinal INTEGER NOT NULL")
            if table == TABLES[4]:
                columns.append("group_ordinal INTEGER NOT NULL")
                check("group_ordinal", "group_ordinal BETWEEN 0 AND 49")
                unique("position", "authorship_snapshot_id,group_ordinal,ordinal")
            else:
                unique("ordinal", "authorship_snapshot_id,ordinal")
            if table == TABLES[5]:
                unique("record", "authorship_snapshot_id,contribution_record_id")
                check("ordinal", "ordinal BETWEEN 0 AND 999")
            else:
                unique("actor", "authorship_snapshot_id,actor_id")
                check(
                    "ordinal",
                    "ordinal BETWEEN 1 AND 100"
                    if table == TABLES[2]
                    else "ordinal BETWEEN 0 AND 99",
                )
        op.execute(f"CREATE TABLE {table} ({','.join(columns)})")
        for column in fks:
            if column not in leading:
                op.execute(f"CREATE INDEX {_name('ix', table, column)} ON {table}({column})")
    op.execute("""
    CREATE FUNCTION pr217_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'authorship history is immutable' USING ERRCODE='P17A1'; END $$;
    CREATE FUNCTION pr217_snapshot_sealed() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE parent_xmin bigint;
    BEGIN
      SELECT xmin::text::bigint INTO parent_xmin FROM authorship_snapshots
        WHERE id=NEW.authorship_snapshot_id FOR UPDATE;
      IF parent_xmin IS DISTINCT FROM pg_current_xact_id()::text::bigint THEN
        RAISE EXCEPTION 'snapshot relation set is sealed' USING ERRCODE='P17A1';
      END IF;
      RETURN NEW;
    END $$;
    CREATE FUNCTION pr217_contribution_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM publications WHERE id=NEW.publication_id)
        OR NOT EXISTS (SELECT 1 FROM actors WHERE id=NEW.actor_id AND retired_at IS NULL)
        OR NEW.recorded_by IS DISTINCT FROM NEW.created_by
        OR NEW.contribution_role NOT IN
          ('CONCEPTUALIZATION','INVESTIGATION','ANALYSIS','SOFTWARE','WRITING','REVIEW')
        OR length(NEW.contribution_statement) NOT BETWEEN 1 AND 10000
        OR NEW.contribution_statement !~ '[^[:space:]]'
        OR NEW.contribution_statement IS DISTINCT FROM normalize(NEW.contribution_statement,NFC)
      THEN RAISE EXCEPTION 'invalid contribution material' USING ERRCODE='P17A3'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER pr217_contribution_guard BEFORE INSERT ON contribution_records
      FOR EACH ROW EXECUTE FUNCTION pr217_contribution_guard();
    CREATE FUNCTION pr217_snapshot_complete() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE sid UUID; pub UUID; n integer; lo integer; hi integer;
    BEGIN
      IF TG_TABLE_NAME='authorship_snapshots' THEN sid:=NEW.id;
      ELSE sid:=NEW.authorship_snapshot_id; END IF;
      SELECT publication_id INTO pub FROM authorship_snapshots WHERE id=sid;
      SELECT count(*),min(ordinal),max(ordinal) INTO n,lo,hi
        FROM authorship_snapshot_authors WHERE authorship_snapshot_id=sid;
      IF n NOT BETWEEN 1 AND 100 OR lo<>1 OR hi<>n
        OR EXISTS (SELECT 1 FROM authorship_snapshot_authors x JOIN actors a ON a.id=x.actor_id
          WHERE x.authorship_snapshot_id=sid AND a.actor_type<>'HUMAN')
      THEN RAISE EXCEPTION 'invalid human author aggregate' USING ERRCODE='P17A2'; END IF;
      SELECT count(*),min(ordinal),max(ordinal) INTO n,lo,hi
        FROM authorship_snapshot_corresponding_authors WHERE authorship_snapshot_id=sid;
      IF n NOT BETWEEN 1 AND 100 OR lo<>0 OR hi<>n-1 THEN
        RAISE EXCEPTION 'invalid corresponding aggregate' USING ERRCODE='P17A2'; END IF;
      IF EXISTS (SELECT 1 FROM authorship_snapshot_equal_groups WHERE authorship_snapshot_id=sid
          GROUP BY group_ordinal HAVING count(*)<2 OR min(ordinal)<>0 OR max(ordinal)<>count(*)-1)
        OR (SELECT count(DISTINCT group_ordinal) FROM authorship_snapshot_equal_groups
          WHERE authorship_snapshot_id=sid) IS DISTINCT FROM
          (SELECT coalesce(max(group_ordinal)+1,0) FROM authorship_snapshot_equal_groups
          WHERE authorship_snapshot_id=sid)
      THEN RAISE EXCEPTION 'invalid equal aggregate' USING ERRCODE='P17A2'; END IF;
      SELECT count(*),min(ordinal),max(ordinal) INTO n,lo,hi
        FROM authorship_snapshot_contributions WHERE authorship_snapshot_id=sid;
      IF n NOT BETWEEN 1 AND 1000 OR lo<>0 OR hi<>n-1
        OR EXISTS (SELECT 1 FROM authorship_snapshot_contributions x
          JOIN contribution_records c ON c.id=x.contribution_record_id
          WHERE x.authorship_snapshot_id=sid AND c.publication_id<>pub)
        OR EXISTS (SELECT 1 FROM authorship_snapshot_authors a
          WHERE a.authorship_snapshot_id=sid AND NOT EXISTS (
            SELECT 1 FROM authorship_snapshot_contributions x JOIN contribution_records c
              ON c.id=x.contribution_record_id
            WHERE x.authorship_snapshot_id=sid AND c.actor_id=a.actor_id))
      THEN RAISE EXCEPTION 'invalid contribution coverage' USING ERRCODE='P17A2'; END IF;
      RETURN NULL;
    END $$;
    """)
    for table in TABLES:
        alias = ALIASES.get(table, table)
        op.execute(
            f"CREATE TRIGGER pr217_immutable_{alias} BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION pr217_immutable()"
        )
        if table != TABLES[0]:
            op.execute(
                f"CREATE CONSTRAINT TRIGGER pr217_snapshot_complete_{alias} "
                f"AFTER INSERT ON {table} DEFERRABLE INITIALLY DEFERRED "
                "FOR EACH ROW EXECUTE FUNCTION pr217_snapshot_complete()"
            )
        if table in TABLES[2:]:
            op.execute(
                f"CREATE TRIGGER pr217_snapshot_sealed_{alias} BEFORE INSERT ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION pr217_snapshot_sealed()"
            )


def downgrade():
    for table in TABLES:
        op.execute(f"LOCK TABLE {table} IN ACCESS EXCLUSIVE MODE")
    predicate = " OR ".join(f"EXISTS (SELECT 1 FROM {table})" for table in TABLES)
    op.execute(
        f"DO $$ BEGIN IF {predicate} THEN RAISE EXCEPTION "
        "'retained authorship history prevents downgrade'; END IF; END $$"
    )
    for table in reversed(TABLES):
        op.execute(f"DROP TABLE {table}")
    for function in (
        "pr217_snapshot_complete",
        "pr217_contribution_guard",
        "pr217_snapshot_sealed",
        "pr217_immutable",
    ):
        op.execute(f"DROP FUNCTION {function}()")
