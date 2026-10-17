"""TEST ONLY exact S1 catalog, normal-role guards and preserving migration paths."""

from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError

from tests.integration.phase2.test_pr2_17_authorship import (
    PREVIOUS,
    REVISION,
    _count,
    _record,
    _snapshot,
)
from tests.integration.phase2.test_pr2_17_authorship import (
    authorship_env as _env,
)
from tests.integration.phase2.test_pr2_17_authorship import (
    authorship_url as _url,
)

pytestmark = pytest.mark.integration
authorship_env = _env
authorship_url = _url
TABLES = (
    "contribution_records",
    "authorship_snapshots",
    "authorship_snapshot_authors",
    "authorship_snapshot_corresponding_authors",
    "authorship_snapshot_equal_groups",
    "authorship_snapshot_contributions",
)
ALIASES = {
    TABLES[2]: "as_authors",
    TABLES[3]: "as_corresponding",
    TABLES[4]: "as_equal_groups",
    TABLES[5]: "as_contributions",
}


def _config(url):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return config


def _tables(conn):
    return set(
        conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'")).scalars()
    )


@pytest.mark.parametrize("start", ["base", "0018_current_pointer_same_parent_integrity", PREVIOUS])
def test_install_upgrade_exact_catalog_and_one_head(authorship_url, start):
    config = _config(authorship_url)
    assert ScriptDirectory.from_config(config).get_heads() == ["0054_b11_ready_for_submission"]
    command.upgrade(config, start)
    command.upgrade(config, PREVIOUS)
    engine = create_engine(authorship_url)
    with engine.connect() as conn:
        before = _tables(conn)
    command.upgrade(config, REVISION)
    with engine.connect() as conn:
        assert int(conn.execute(text("SHOW server_version_num")).scalar_one()) // 10000 == 18
        assert _tables(conn) - before == set(TABLES)
        assert (
            conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == REVISION
        )
        actual = conn.execute(
            text("""SELECT table_name,column_name,udt_name,is_nullable
          FROM information_schema.columns WHERE table_schema='public'
            AND table_name=ANY(:tables)"""),
            {"tables": list(TABLES)},
        ).all()
        base = {
            "id": ("uuid", "NO"),
            "created_at": ("timestamptz", "NO"),
            "created_by": ("uuid", "NO"),
        }
        hash_fields = {"content_hash": ("bpchar", "NO"), "hash_scheme": ("varchar", "NO")}
        author_fields = {
            "authorship_snapshot_id": ("uuid", "NO"),
            "actor_id": ("uuid", "NO"),
            "ordinal": ("int4", "NO"),
        }
        expected = {
            TABLES[0]: {
                **base,
                **hash_fields,
                "publication_id": ("uuid", "NO"),
                "actor_id": ("uuid", "NO"),
                "recorded_by": ("uuid", "NO"),
                "contribution_role": ("varchar", "NO"),
                "contribution_statement": ("text", "NO"),
            },
            TABLES[1]: {**base, **hash_fields, "publication_id": ("uuid", "NO")},
            TABLES[2]: {**base, **author_fields},
            TABLES[3]: {**base, **author_fields},
            TABLES[4]: {**base, **author_fields, "group_ordinal": ("int4", "NO")},
            TABLES[5]: {
                **base,
                "authorship_snapshot_id": ("uuid", "NO"),
                "contribution_record_id": ("uuid", "NO"),
                "ordinal": ("int4", "NO"),
            },
        }
        assert {
            t: {n: (kind, nullable) for table, n, kind, nullable in actual if table == t}
            for t in TABLES
        } == expected
        constraints = conn.execute(
            text("""SELECT c.relname,k.conname,k.contype,k.confdeltype,
           pg_get_constraintdef(k.oid) FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid
           WHERE c.relname=ANY(:tables)"""),
            {"tables": list(TABLES)},
        ).all()
        names = {row[1] for row in constraints}
        _exact_catalog(conn, engine)
        assert {f"pk_{t}" for t in TABLES} <= names
        assert {
            "fk_corresponding_author",
            "fk_equal_group_author",
            "ck_contribution_records_nfc",
            "uq_contribution_records_parent_id",
            "uq_authorship_snapshots_parent_id",
        } <= names
        assert all(row[3] == "r" for row in constraints if row[2] == "f")
        assert all(len(name) <= 63 for name in names)
        indexes = {
            row[0]
            for row in conn.execute(
                text("SELECT indexname FROM pg_indexes WHERE tablename=ANY(:tables)"),
                {"tables": list(TABLES)},
            )
        }
        assert {
            "ix_contribution_records_created_by",
            "ix_contribution_records_actor_id",
            "ix_contribution_records_recorded_by",
            "ix_authorship_snapshots_created_by",
            "ix_authorship_snapshot_corresponding_authors_created_by",
            "ix_authorship_snapshot_corresponding_authors_actor_id",
            "ix_authorship_snapshot_contributions_contribution_record_id",
        } <= indexes
        triggers = conn.execute(
            text("""SELECT c.relname,t.tgname,t.tgdeferrable,t.tginitdeferred
           FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
           WHERE NOT t.tgisinternal AND c.relname=ANY(:tables)"""),
            {"tables": list(TABLES)},
        ).all()
        assert {f"pr217_immutable_{ALIASES.get(t, t)}" for t in TABLES} <= {
            row[1] for row in triggers
        }
        assert {f"pr217_snapshot_complete_{ALIASES.get(t, t)}" for t in TABLES[1:]} == {
            name for _, name, deferred, initially in triggers if deferred and initially
        }
    engine.dispose()


def test_empty_downgrade_roundtrip(authorship_url):
    config = _config(authorship_url)
    command.upgrade(config, PREVIOUS)
    engine = create_engine(authorship_url)
    with engine.connect() as conn:
        before = _tables(conn)
    command.upgrade(config, REVISION)
    command.downgrade(config, PREVIOUS)
    with engine.connect() as conn:
        assert _tables(conn) == before
        assert (
            conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == PREVIOUS
        )
    command.upgrade(config, REVISION)
    engine.dispose()


def test_nonempty_downgrade_refuses(authorship_env, authorship_url):
    env = authorship_env
    env[0].record_contribution(env[4], _record(env))
    with pytest.raises(DBAPIError):
        command.downgrade(_config(authorship_url), PREVIOUS)
    assert _count(env) == (1, 0)
    with env[2].connect() as conn:
        assert (
            conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == "0054_b11_ready_for_submission"
        )


@pytest.fixture
def normal_role(authorship_env):
    engine = authorship_env[2]
    role = f"pr217_test_{uuid4().hex}"
    with engine.begin() as conn:
        conn.execute(text(f'CREATE ROLE "{role}" NOLOGIN NOSUPERUSER'))
        conn.execute(text(f'GRANT USAGE ON SCHEMA public TO "{role}"'))
        conn.execute(text(f'GRANT SELECT ON ALL TABLES IN SCHEMA public TO "{role}"'))
        for table in TABLES:
            conn.execute(text(f'GRANT INSERT,UPDATE,DELETE ON {table} TO "{role}"'))
    try:
        yield role
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP OWNED BY "{role}"'))
            conn.execute(text(f'DROP ROLE "{role}"'))


def _insert(conn, table, row):
    conn.execute(
        text(
            f"INSERT INTO {table} ({','.join(row)}) VALUES ("
            + ",".join(f":{key}" for key in row)
            + ")"
        ),
        row,
    )


def _raw_snapshot(
    conn,
    env,
    record,
    *,
    author=None,
    author_ordinal=1,
    corresponding_ordinal=0,
    contribution_ordinal=0,
):
    sid = uuid4()
    common = {"created_by": env[4].actor_id}
    _insert(
        conn,
        TABLES[1],
        {
            **common,
            "id": sid,
            "publication_id": env[6],
            "content_hash": "a" * 64,
            "hash_scheme": "sha256-cjson-v1",
        },
    )
    base = {**common, "authorship_snapshot_id": sid}
    actor = author or env[4].actor_id
    _insert(conn, TABLES[2], {**base, "id": uuid4(), "actor_id": actor, "ordinal": author_ordinal})
    _insert(
        conn,
        TABLES[3],
        {**base, "id": uuid4(), "actor_id": actor, "ordinal": corresponding_ordinal},
    )
    _insert(
        conn,
        TABLES[5],
        {**base, "id": uuid4(), "contribution_record_id": record, "ordinal": contribution_ordinal},
    )
    return sid


@pytest.mark.parametrize(
    "change",
    [
        "agent",
        "wrong_parent",
        "coverage",
        "author_gap",
        "corresponding_gap",
        "contribution_gap",
        "empty",
    ],
)
def test_normal_role_aggregate_constraints_and_rollback(authorship_env, normal_role, change):
    env = authorship_env
    rec = env[0].record_contribution(env[4], _record(env))
    other = uuid4()
    with env[2].begin() as conn:
        conn.execute(
            text(
                "INSERT INTO actors(id,actor_type,display_name,created_at) VALUES "
                "(:id,:kind,'TEST ONLY',clock_timestamp())"
            ),
            {"id": other, "kind": "AGENT" if change == "agent" else "HUMAN"},
        )
    selected = rec.id
    if change == "wrong_parent":
        with env[2].begin() as conn:
            pid = uuid4()
            _insert(
                conn,
                "publications",
                {
                    "id": pid,
                    "project_id": env[5],
                    "publication_type": "PAPER",
                    "lifecycle_status": "DRAFTING",
                    "title": "TEST ONLY",
                    "row_version": 1,
                    "created_by": env[4].actor_id,
                    "created_at": conn.execute(text("SELECT clock_timestamp()")).scalar_one(),
                },
            )
        selected = env[0].record_contribution(env[4], _record(env, publication_id=pid)).id
    before = _count(env)
    with pytest.raises(DBAPIError) as error:
        with env[2].begin() as conn:
            conn.execute(text(f'SET LOCAL ROLE "{normal_role}"'))
            if change == "empty":
                _insert(
                    conn,
                    TABLES[1],
                    {
                        "id": uuid4(),
                        "created_by": env[4].actor_id,
                        "publication_id": env[6],
                        "content_hash": "a" * 64,
                        "hash_scheme": "sha256-cjson-v1",
                    },
                )
            else:
                _raw_snapshot(
                    conn,
                    env,
                    selected,
                    author=other if change in {"agent", "coverage"} else None,
                    author_ordinal=2 if change == "author_gap" else 1,
                    corresponding_ordinal=1 if change == "corresponding_gap" else 0,
                    contribution_ordinal=1 if change == "contribution_gap" else 0,
                )
    assert getattr(error.value.orig, "sqlstate", None) == "P17A2"
    assert _count(env) == before


@pytest.mark.parametrize("table", TABLES)
@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
def test_normal_role_all_immutable_rows(authorship_env, normal_role, table, operation):
    env = authorship_env
    rec = env[0].record_contribution(env[4], _record(env))
    with env[2].begin() as conn:
        # Two authors enable an equal group row to exercise every relation table.
        actor = uuid4()
        conn.execute(
            text(
                "INSERT INTO actors(id,actor_type,display_name,created_at) VALUES "
                "(:id,'HUMAN','TEST ONLY',clock_timestamp())"
            ),
            {"id": actor},
        )
    second = env[0].record_contribution(env[4], _record(env, actor_id=actor))
    env[0].create_authorship_snapshot(
        env[4],
        _snapshot(
            env,
            (rec.id, second.id),
            author_ids=(env[4].actor_id, actor),
            equal_contribution_groups=((env[4].actor_id, actor),),
        ),
    )
    with pytest.raises(DBAPIError) as error:
        with env[2].begin() as conn:
            conn.execute(text(f'SET LOCAL ROLE "{normal_role}"'))
            conn.execute(
                text(
                    f"UPDATE {table} SET id=id" if operation == "UPDATE" else f"DELETE FROM {table}"
                )
            )
    assert getattr(error.value.orig, "sqlstate", None) == "P17A1"


def test_normal_role_late_child_and_trigger_disable_denied(authorship_env, normal_role):
    env = authorship_env
    rec = env[0].record_contribution(env[4], _record(env))
    snapshot = env[0].create_authorship_snapshot(env[4], _snapshot(env, (rec.id,)))
    with pytest.raises(DBAPIError) as error:
        with env[2].begin() as conn:
            conn.execute(text(f'SET LOCAL ROLE "{normal_role}"'))
            _insert(
                conn,
                TABLES[2],
                {
                    "id": uuid4(),
                    "created_by": env[4].actor_id,
                    "authorship_snapshot_id": snapshot.id,
                    "actor_id": env[4].actor_id,
                    "ordinal": 2,
                },
            )
    assert getattr(error.value.orig, "sqlstate", None) == "P17A1"
    with pytest.raises(DBAPIError) as error:
        with env[2].begin() as conn:
            conn.execute(text(f'SET LOCAL ROLE "{normal_role}"'))
            conn.execute(text("ALTER TABLE authorship_snapshots DISABLE TRIGGER USER"))
    assert getattr(error.value.orig, "sqlstate", None) == "42501"


def _contract_name(prefix, table, suffix=""):
    name = f"{prefix}_{table}" + (f"_{suffix}" if suffix else "")
    if len(name) > 63:
        return f"{prefix}_{ALIASES[table]}" + (f"_{suffix}" if suffix else "")
    return name


def _exact_catalog(conn, engine):
    catalog = inspect(engine)
    for table in TABLES:
        uniques = (
            {"parent_id": ["publication_id", "id"]}
            if table in TABLES[:2]
            else {
                "actor" if table != TABLES[5] else "record": [
                    "authorship_snapshot_id",
                    "actor_id" if table != TABLES[5] else "contribution_record_id",
                ],
                "position" if table == TABLES[4] else "ordinal": (
                    ["authorship_snapshot_id", "group_ordinal", "ordinal"]
                    if table == TABLES[4]
                    else ["authorship_snapshot_id", "ordinal"]
                ),
            }
        )
        assert {u["name"]: u["column_names"] for u in catalog.get_unique_constraints(table)} == {
            _contract_name("uq", table, label): columns for label, columns in uniques.items()
        }
        fks = {"created_by": ("actors", ["id"])}
        if table in TABLES[:2]:
            fks["publication_id"] = ("publications", ["id"])
        if table == TABLES[0]:
            fks.update({"actor_id": ("actors", ["id"]), "recorded_by": ("actors", ["id"])})
        elif table == TABLES[2]:
            fks.update(
                {"authorship_snapshot_id": (TABLES[1], ["id"]), "actor_id": ("actors", ["id"])}
            )
        elif table == TABLES[5]:
            fks.update(
                {
                    "authorship_snapshot_id": (TABLES[1], ["id"]),
                    "contribution_record_id": (TABLES[0], ["id"]),
                }
            )
        expected_fks = {
            _contract_name("fk", table, column): ([column], target, columns)
            for column, (target, columns) in fks.items()
        }
        if table in (TABLES[3], TABLES[4]):
            expected_fks[
                "fk_corresponding_author" if table == TABLES[3] else "fk_equal_group_author"
            ] = (
                ["authorship_snapshot_id", "actor_id"],
                TABLES[2],
                ["authorship_snapshot_id", "actor_id"],
            )
        assert {
            f["name"]: (f["constrained_columns"], f["referred_table"], f["referred_columns"])
            for f in catalog.get_foreign_keys(table)
        } == expected_fks
        checks = ["digest", "scheme"] if table in TABLES[:2] else ["ordinal"]
        if table == TABLES[0]:
            checks += ["role", "statement", "recorder", "nfc"]
        if table == TABLES[4]:
            checks += ["group_ordinal"]
        assert {c["name"] for c in catalog.get_check_constraints(table)} == {
            _contract_name("ck", table, label) for label in checks
        }
        columns = {c["name"]: c for c in catalog.get_columns(table)}
        assert columns["created_at"]["default"] == "clock_timestamp()"
        for column, width in (("content_hash", 64), ("hash_scheme", 32), ("contribution_role", 24)):
            if column in columns:
                assert columns[column]["type"].length == width
                assert columns[column]["default"] is None
        leading = {"id"} | {columns[0] for columns in uniques.values()}
        fk_columns = {c for columns, _, _ in expected_fks.values() for c in columns}
        expected_indexes = {_contract_name("ix", table, c): [c] for c in fk_columns - leading}
        actual_indexes = {
            i["name"]: i["column_names"]
            for i in catalog.get_indexes(table)
            if not i.get("duplicates_constraint")
        }
        assert actual_indexes == expected_indexes
        for name in actual_indexes:
            definition = conn.execute(
                text("SELECT indexdef FROM pg_indexes WHERE indexname=:name"), {"name": name}
            ).scalar_one()
            assert "USING btree" in definition
        triggers = conn.execute(
            text("""SELECT t.tgname,t.tgtype,p.proname,t.tgdeferrable,t.tginitdeferred
            FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
            JOIN pg_proc p ON p.oid=t.tgfoid WHERE c.relname=:table AND NOT t.tgisinternal"""),
            {"table": table},
        ).all()
        alias = ALIASES.get(table, table)
        expected_triggers = {(f"pr217_immutable_{alias}", 27, "pr217_immutable", False, False)}
        if table == TABLES[0]:
            expected_triggers.add(
                ("pr217_contribution_guard", 7, "pr217_contribution_guard", False, False)
            )
        else:
            expected_triggers.add(
                (f"pr217_snapshot_complete_{alias}", 5, "pr217_snapshot_complete", True, True)
            )
        if table in TABLES[2:]:
            expected_triggers.add(
                (f"pr217_snapshot_sealed_{alias}", 7, "pr217_snapshot_sealed", False, False)
            )
        assert set(triggers) == expected_triggers


@pytest.mark.parametrize(
    "change", ["role", "blank", "long", "nfc", "recorder", "retired", "publication"]
)
def test_normal_role_contribution_guard(authorship_env, normal_role, change):
    env = authorship_env
    row = {
        "id": uuid4(),
        "created_by": env[4].actor_id,
        "publication_id": env[6],
        "actor_id": env[4].actor_id,
        "recorded_by": env[4].actor_id,
        "contribution_role": "WRITING",
        "contribution_statement": "TEST ONLY",
        "content_hash": "a" * 64,
        "hash_scheme": "sha256-cjson-v1",
    }
    if change == "retired":
        actor = uuid4()
        with env[2].begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO actors(id,actor_type,display_name,created_at,retired_at) "
                    "VALUES (:id,'HUMAN','TEST ONLY',clock_timestamp(),clock_timestamp())"
                ),
                {"id": actor},
            )
        row["actor_id"] = actor
    else:
        field, value = {
            "role": ("contribution_role", "OTHER"),
            "blank": ("contribution_statement", " "),
            "long": ("contribution_statement", "x" * 10001),
            "nfc": ("contribution_statement", "e\u0301"),
            "recorder": ("recorded_by", uuid4()),
            "publication": ("publication_id", uuid4()),
        }[change]
        row[field] = value
    with pytest.raises(DBAPIError) as error:
        with env[2].begin() as conn:
            conn.execute(text(f'SET LOCAL ROLE "{normal_role}"'))
            _insert(conn, TABLES[0], row)
    assert getattr(error.value.orig, "sqlstate", None) == "P17A3"
    assert _count(env) == (0, 0)


@pytest.mark.parametrize(
    "change,state",
    [
        ("corresponding_subset", "23503"),
        ("equal_subset", "23503"),
        ("singleton", "P17A2"),
        ("overlap", "23505"),
        ("group_gap", "P17A2"),
        ("member_gap", "P17A2"),
    ],
)
def test_normal_role_equal_and_corresponding_constraints(
    authorship_env, normal_role, change, state
):
    env = authorship_env
    first = env[0].record_contribution(env[4], _record(env))
    other = uuid4()
    with env[2].begin() as conn:
        conn.execute(
            text(
                "INSERT INTO actors(id,actor_type,display_name,created_at) "
                "VALUES (:id,'HUMAN','TEST ONLY',clock_timestamp())"
            ),
            {"id": other},
        )
    second = env[0].record_contribution(env[4], _record(env, actor_id=other))
    before = _count(env)
    with pytest.raises(DBAPIError) as error:
        with env[2].begin() as conn:
            conn.execute(text(f'SET LOCAL ROLE "{normal_role}"'))
            sid = _raw_snapshot(conn, env, first.id)
            base = {"created_by": env[4].actor_id, "authorship_snapshot_id": sid}
            if change in {"corresponding_subset", "equal_subset"}:
                _insert(
                    conn,
                    TABLES[3] if change == "corresponding_subset" else TABLES[4],
                    {
                        **base,
                        "id": uuid4(),
                        "actor_id": other,
                        "ordinal": 1,
                        **({"group_ordinal": 0} if change == "equal_subset" else {}),
                    },
                )
            else:
                _insert(conn, TABLES[2], {**base, "id": uuid4(), "actor_id": other, "ordinal": 2})
                _insert(
                    conn,
                    TABLES[5],
                    {**base, "id": uuid4(), "contribution_record_id": second.id, "ordinal": 1},
                )
                group = 1 if change == "group_gap" else 0
                _insert(
                    conn,
                    TABLES[4],
                    {
                        **base,
                        "id": uuid4(),
                        "actor_id": env[4].actor_id,
                        "ordinal": 0,
                        "group_ordinal": group,
                    },
                )
                if change != "singleton":
                    _insert(
                        conn,
                        TABLES[4],
                        {
                            **base,
                            "id": uuid4(),
                            "actor_id": other,
                            "ordinal": 2 if change == "member_gap" else 1,
                            "group_ordinal": group,
                        },
                    )
                if change == "overlap":
                    _insert(
                        conn,
                        TABLES[4],
                        {
                            **base,
                            "id": uuid4(),
                            "actor_id": other,
                            "ordinal": 0,
                            "group_ordinal": 1,
                        },
                    )
    assert getattr(error.value.orig, "sqlstate", None) == state
    assert _count(env) == before
