"""B14a catalog, forward preservation, and ordinary SQL guard enforcement."""

# SQL assertions retain the exact reviewed lock/guard literals.
# ruff: noqa: E501

from uuid import uuid4

import pytest
from alembic import command as alembic
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from researchbase.persistence.publication_repository import B14A_SHARE_SQL
from tests.disposable_postgres import disposable_database
from tests.integration.phase2.test_b04_manuscript_migration import (
    normal_sql_role as normal_sql_role,
)
from tests.integration.phase2.test_b14a_publication_entry import (
    b04_env,
    b05_env,
    command,
    conclusion_env,
    counts,
    enter,
    phase2_database_url,
    seal,
)

_FIXTURES = (b04_env, b05_env, conclusion_env, phase2_database_url, normal_sql_role)
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
pytestmark = pytest.mark.integration


def config(url):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return cfg


def catalog_inventory(conn):
    """Compare logical schema definitions, excluding physical IDs/dropped slots."""
    queries = {
        "columns": """SELECT c.relname,a.attname,format_type(a.atttypid,a.atttypmod),
          a.attnotnull,pg_get_expr(d.adbin,d.adrelid)
          FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
          JOIN pg_attribute a ON a.attrelid=c.oid
          LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum
          WHERE n.nspname='public' AND c.relkind IN ('r','p')
            AND a.attnum>0 AND NOT a.attisdropped ORDER BY c.relname,a.attname""",
        "constraints": """SELECT c.relname,k.conname,pg_get_constraintdef(k.oid),
          k.condeferrable,k.condeferred,k.convalidated FROM pg_constraint k
          JOIN pg_class c ON c.oid=k.conrelid
          JOIN pg_namespace n ON n.oid=c.relnamespace
          WHERE n.nspname='public' ORDER BY c.relname,k.conname""",
        "indexes": """SELECT tablename,indexname,indexdef FROM pg_indexes
          WHERE schemaname='public' ORDER BY tablename,indexname""",
        "triggers": """SELECT c.relname,t.tgname,pg_get_triggerdef(t.oid)
          FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
          JOIN pg_namespace n ON n.oid=c.relnamespace
          WHERE n.nspname='public' AND NOT t.tgisinternal ORDER BY c.relname,t.tgname""",
        "functions": """SELECT p.proname,pg_get_function_identity_arguments(p.oid),
          pg_get_functiondef(p.oid) FROM pg_proc p
          JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public'
          ORDER BY p.proname,pg_get_function_identity_arguments(p.oid)""",
    }
    return {name: tuple(conn.execute(text(sql)).tuples()) for name, sql in queries.items()}


def protect(conn):
    conn.execute(text(B14A_SHARE_SQL))
    conn.execute(text("LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE"))
    conn.execute(
        text(
            "LOCK TABLE approval_decisions,approval_request_reviews,approval_requests IN SHARE MODE"
        )
    )


@pytest.mark.parametrize("start", ["base", "0061_b16_consent_withdrawal"])
def test_fresh_upgrade_catalog_and_empty_downgrade(start, monkeypatch):
    with disposable_database("researchbase_pr212_test_", "RB_PR210_TEST_ADMIN_URL") as url:
        monkeypatch.setenv("DATABASE_URL", url)
        cfg = config(url)
        # "base" exercises the full predecessor chain; the other case preinstalls it.
        alembic.upgrade(cfg, start)
        alembic.upgrade(cfg, "0061_b16_consent_withdrawal")
        engine = create_engine(url)
        with engine.connect() as conn:
            predecessor = catalog_inventory(conn)
        alembic.upgrade(cfg, "head")
        with engine.connect() as conn:
            extension = catalog_inventory(conn)
            # The lane replaces distinct functions. Retain B15/B16 definitions,
            # including search_path configuration and all terminal-cause guards.
            retained = {
                row[:2]: row[2]
                for row in predecessor["functions"]
                if row[0].startswith(("b16_",))
                or row[0]
                in {
                    "b09_preheld",
                    "b13_validate_event",
                    "b15_manuscript_structure",
                    "b15_snapshot_structure",
                    "b15_projection",
                    "b15_immutable",
                    "b15_consent_guard",
                }
            }
            current = {row[:2]: row[2] for row in extension["functions"]}
            assert retained and all(current[key] == value for key, value in retained.items())
            assert conn.execute(text("SHOW server_version_num")).scalar_one().startswith("18")
            constraints = set(
                conn.execute(
                    text(
                        "SELECT conname FROM pg_constraint WHERE conrelid IN ('publications'::regclass,'publication_lifecycle_events'::regclass)"
                    )
                ).scalars()
            )
            assert {
                "ck_b14a_publication_status",
                "fk_b14a_entry_same_parent",
                "ck_b14a_event_tuple",
                "ck_b14a_event_time",
            } <= constraints
            indexes = set(
                conn.execute(
                    text(
                        "SELECT indexname FROM pg_indexes WHERE tablename='publication_lifecycle_events'"
                    )
                ).scalars()
            )
            assert {
                "uq_b14a_initial_event",
                "uq_b14a_review_entry",
                "ix_b14a_entry_manuscript",
            } <= indexes
            assert (
                conn.execute(
                    text(
                        "SELECT count(*) FROM pg_trigger WHERE tgname IN ('b14a_complete_publication','b14a_complete_entry_event') AND tgdeferrable AND tginitdeferred"
                    )
                ).scalar_one()
                == 2
            )
            assert (
                "pg_current_xact_id()::xid"
                in conn.execute(
                    text("SELECT pg_get_functiondef('b14a_verify_entry(uuid)'::regprocedure)")
                ).scalar_one()
            )
        alembic.downgrade(cfg, "0061_b16_consent_withdrawal")
        with engine.connect() as conn:
            assert catalog_inventory(conn) == predecessor
            assert (
                conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                == "0061_b16_consent_withdrawal"
            )
        alembic.upgrade(cfg, "head")
        with engine.connect() as conn:
            assert catalog_inventory(conn) == extension
        engine.dispose()


def test_populated_creation_and_b04_seal_survive_forward_roundtrip(b05_env):
    env = b05_env
    seal(env)
    cfg = config(env[5].url.render_as_string(hide_password=False))
    before = counts(env)
    alembic.downgrade(cfg, "0061_b16_consent_withdrawal")
    alembic.upgrade(cfg, "head")
    assert counts(env) == before
    enter(env)
    saved = counts(env)
    with env[5].connect() as conn:
        inventory = catalog_inventory(conn)
    with pytest.raises(DBAPIError) as error:
        alembic.downgrade(cfg, "0061_b16_consent_withdrawal")
    assert getattr(error.value.orig, "sqlstate", None) == "P14I1"
    assert counts(env) == saved
    with env[5].connect() as conn:
        assert catalog_inventory(conn) == inventory
        assert (
            conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == "0071_b23_novelty_review"
        )


@pytest.mark.parametrize(
    "attack",
    [
        "state_only",
        "event_only",
        "wrong_target",
        "wrong_actor",
        "future_time",
        "old_time",
        "wrong_tuple",
        "material",
        "pointer",
        "unlisted",
        "duplicate_initial",
        "edit",
        "delete",
    ],
)
def test_normal_role_denies_incomplete_or_invalid_graph(b05_env, normal_sql_role, attack):
    env = b05_env
    seal(env)
    cmd = command(env)
    if attack in {"edit", "delete"}:
        enter(env, cmd)
    before = counts(env)
    with pytest.raises(DBAPIError):
        with env[5].begin() as conn:
            protect(conn)
            conn.execute(text(f'SET LOCAL ROLE "{normal_sql_role}"'))
            args = dict(
                pub=cmd.publication_id,
                mid=cmd.manuscript_version_id,
                actor=env[2].actor_id,
                id=uuid4(),
            )
            if attack in {"edit", "delete"}:
                conn.execute(
                    text(
                        "UPDATE publication_lifecycle_events SET actor_id=:actor WHERE id=:id"
                        if attack == "edit"
                        else "DELETE FROM publication_lifecycle_events WHERE id=:id"
                    ),
                    {**args, "id": cmd.id},
                )
            elif attack == "material":
                conn.execute(text("UPDATE publications SET title='Changed' WHERE id=:pub"), args)
            elif attack == "pointer":
                conn.execute(
                    text(
                        "UPDATE publications SET current_manuscript_version_id=NULL WHERE id=:pub"
                    ),
                    args,
                )
            elif attack == "unlisted":
                conn.execute(
                    text(
                        "UPDATE publications SET lifecycle_status='READY',row_version=row_version+1 WHERE id=:pub"
                    ),
                    args,
                )
            elif attack == "duplicate_initial":
                conn.execute(
                    text(
                        "INSERT INTO publication_lifecycle_events(id,publication_id,new_status,actor_id,occurred_at) SELECT :id,id,'DRAFTING',created_by,created_at FROM publications WHERE id=:pub"
                    ),
                    args,
                )
            else:
                if attack != "event_only":
                    conn.execute(
                        text(
                            "UPDATE publications SET lifecycle_status='INTERNAL_REVIEW',row_version=row_version+1 WHERE id=:pub"
                        ),
                        args,
                    )
                if attack != "state_only":
                    if attack == "wrong_target":
                        args["mid"] = uuid4()
                    if attack == "wrong_actor":
                        args["actor"] = uuid4()
                    clock = (
                        "clock_timestamp()+interval '1 day'"
                        if attack == "future_time"
                        else "clock_timestamp()-interval '1 day'"
                        if attack == "old_time"
                        else "clock_timestamp()"
                    )
                    prior = "NULL" if attack == "wrong_tuple" else "'DRAFTING'"
                    conn.execute(
                        text(
                            f"INSERT INTO publication_lifecycle_events(id,publication_id,manuscript_version_id,prior_status,new_status,actor_id,occurred_at) VALUES (:id,:pub,:mid,{prior},'INTERNAL_REVIEW',:actor,{clock})"
                        ),
                        args,
                    )
            conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert counts(env) == before


def test_same_transaction_exact_graph_succeeds_as_normal_role(b05_env, normal_sql_role):
    env = b05_env
    seal(env)
    cmd = command(env)
    with env[5].begin() as conn:
        protect(conn)
        conn.execute(text(f'SET LOCAL ROLE "{normal_sql_role}"'))
        args = dict(
            pub=cmd.publication_id, mid=cmd.manuscript_version_id, id=cmd.id, actor=env[2].actor_id
        )
        conn.execute(text("SELECT id FROM manuscript_versions WHERE id=:mid FOR UPDATE"), args)
        conn.execute(text("SELECT id FROM publications WHERE id=:pub FOR UPDATE"), args)
        conn.execute(
            text(
                "UPDATE publications SET lifecycle_status='INTERNAL_REVIEW',row_version=row_version+1 WHERE id=:pub"
            ),
            args,
        )
        conn.execute(
            text(
                "INSERT INTO publication_lifecycle_events(id,publication_id,manuscript_version_id,prior_status,new_status,actor_id,occurred_at) VALUES (:id,:pub,:mid,'DRAFTING','INTERNAL_REVIEW',:actor,clock_timestamp())"
            ),
            args,
        )
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert counts(env)[0][0] == "INTERNAL_REVIEW"


def test_corrupt_legacy_history_aborts_forward_upgrade_without_repair(b05_env):
    env = b05_env
    seal(env)
    cfg = config(env[5].url.render_as_string(hide_password=False))
    alembic.downgrade(cfg, "0061_b16_consent_withdrawal")
    damaged = uuid4()
    # The predecessor permits this incomplete creation graph; B14a must reject it.
    with env[5].begin() as conn:
        conn.execute(
            text(
                "INSERT INTO publications(id,project_id,publication_type,title,lifecycle_status,created_by,created_at,row_version) VALUES (:id,:project,'PAPER','Incomplete legacy history','DRAFTING',:actor,clock_timestamp(),1)"
            ),
            dict(id=damaged, project=env[1].project_id, actor=env[2].actor_id),
        )
    with pytest.raises(DBAPIError) as error:
        alembic.upgrade(cfg, "head")
    assert getattr(error.value.orig, "sqlstate", None) == "P14P1"
    with env[5].connect() as conn:
        assert (
            conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == "0061_b16_consent_withdrawal"
        )
        assert (
            conn.execute(
                text("SELECT count(*) FROM publications WHERE id=:id"), {"id": damaged}
            ).scalar_one()
            == 1
        )
        assert (
            conn.execute(
                text("SELECT count(*) FROM publication_lifecycle_events WHERE publication_id=:id"),
                {"id": damaged},
            ).scalar_one()
            == 0
        )
