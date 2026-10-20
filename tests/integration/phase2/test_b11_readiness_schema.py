"""B11 exact relational catalog, deferred guards and history-safe downgrade."""

# SQL and independent literal hash vectors preserve contract spelling.
# ruff: noqa: E501

from uuid import uuid4

import pytest
from alembic import command as alembic
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from researchbase.persistence.decision_repository import B11_SHARE_SQL
from tests.integration.phase2.test_b04_manuscript_migration import normal_sql_role
from tests.integration.phase2.test_b11_readiness_decision import (
    b04_env,
    b05_env,
    conclusion_env,
    create,
    phase2_database_url,
    record,
    seal,
)
from tests.integration.phase2.test_pr2_15_decision import decision_env

_FIXTURES = (b04_env, b05_env, conclusion_env, phase2_database_url, normal_sql_role, decision_env)
pytestmark = pytest.mark.integration


def config(env):
    c = Config("alembic.ini")
    c.set_main_option("sqlalchemy.url", env[5].url.render_as_string(hide_password=False))
    return c


def parent(conn, env, identity):
    conn.execute(
        text("""INSERT INTO decision_records
    (id,project_id,decision_type,decision,question,rationale,decided_by,decided_at,basis_set_hash,content_hash,hash_scheme)
    VALUES (:id,:project,'READY_FOR_SUBMISSION','PROCEED','Q','R',:actor,clock_timestamp(),:hash,:hash,'sha256-cjson-v1')"""),
        dict(id=identity, project=env[1].project_id, actor=env[3].actor_id, hash="a" * 64),
    )


def basis(conn, env, identity, review, *, ordinal=0, target=None, manuscript_ordinal=1):
    conn.execute(
        text("INSERT INTO decision_basis_manuscripts VALUES (:id,:target,:ordinal)"),
        dict(
            id=identity, target=target or env[1].manuscript_version_id, ordinal=manuscript_ordinal
        ),
    )
    conn.execute(
        text("INSERT INTO decision_basis_reviews VALUES (:id,:review,:ordinal)"),
        dict(id=identity, review=review.id, ordinal=ordinal),
    )


def test_catalog_and_empty_downgrade(b05_env):
    env = b05_env
    with env[5].connect() as conn:
        columns = dict(
            conn.execute(
                text(
                    "SELECT column_name,data_type FROM information_schema.columns WHERE table_name='decision_basis_manuscripts'"
                )
            ).all()
        )
        assert columns == dict(decision_id="uuid", manuscript_version_id="uuid", ordinal="integer")
        fks = dict(
            conn.execute(
                text(
                    "SELECT conname,confdeltype FROM pg_constraint WHERE conrelid='decision_basis_manuscripts'::regclass AND contype='f'"
                )
            ).all()
        )
        assert fks == {"fk_b11_basis_decision": "r", "fk_b11_basis_manuscript": "r"}
        trigger = conn.execute(
            text(
                "SELECT tgdeferrable,tginitdeferred FROM pg_trigger WHERE tgname='b11_complete_manuscript'"
            )
        ).one()
        assert trigger == (True, True)
    alembic.downgrade(config(env), "0053_b08_issue_disposition")
    alembic.upgrade(config(env), "head")


def test_populated_readiness_refuses_downgrade_preserving_every_byte(b05_env):
    env = b05_env
    seal(env)
    create(env)
    saved = record(env)
    with env[5].connect() as conn:
        before = conn.execute(text("SELECT * FROM decision_records")).all()
    with pytest.raises(DBAPIError):
        alembic.downgrade(config(env), "0053_b08_issue_disposition")
    with env[5].connect() as conn:
        assert conn.execute(text("SELECT * FROM decision_records")).all() == before
        assert conn.execute(text("SELECT id FROM decision_records")).scalar_one() == saved.id


@pytest.mark.parametrize(
    "mutation",
    [
        "parent_only",
        "omitted_review",
        "ordinal",
        "manuscript_ordinal",
        "wrong_target",
        "no_snapshot",
        "isolation",
        "wrong_purpose",
        "mixed",
    ],
)
@pytest.mark.parametrize("force", [False, True])
def test_direct_sql_guard_and_atomic_rollback(b05_env, normal_sql_role, mutation, force):
    env = b05_env
    seal(env)
    review = create(env)
    if mutation == "omitted_review":
        create(env)
    identity = uuid4()
    with pytest.raises(DBAPIError):
        with env[5].begin() as conn:
            if mutation == "isolation":
                conn.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            if mutation != "no_snapshot":
                conn.execute(text(B11_SHARE_SQL))
            conn.execute(text(f'SET LOCAL ROLE "{normal_sql_role}"'))
            parent(conn, env, identity)
            if mutation == "wrong_purpose":
                # Parent history cannot be changed to manufacture another purpose.
                conn.execute(
                    text(
                        "UPDATE decision_records SET decision_type='INTERNAL_SCIENTIFIC_RELEASE' WHERE id=:id"
                    ),
                    {"id": identity},
                )
            if mutation != "parent_only":
                basis(
                    conn,
                    env,
                    identity,
                    review,
                    ordinal=3 if mutation == "ordinal" else 0,
                    manuscript_ordinal=0 if mutation == "manuscript_ordinal" else 1,
                    target=uuid4() if mutation == "wrong_target" else None,
                )
            if mutation == "mixed":
                conn.execute(
                    text("INSERT INTO decision_basis_claims VALUES (:id,:claim,0)"),
                    dict(id=identity, claim=env[8]),
                )
            if force:
                conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    with env[5].connect() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM decision_records WHERE id=:id"), {"id": identity}
            ).scalar_one()
            == 0
        )
        assert (
            conn.execute(
                text("SELECT count(*) FROM decision_basis_manuscripts WHERE decision_id=:id"),
                {"id": identity},
            ).scalar_one()
            == 0
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "parent_update",
        "parent_delete",
        "basis_update",
        "basis_delete",
        "late_review",
        "late_manuscript",
    ],
)
def test_saved_history_immutable(b05_env, normal_sql_role, mutation):
    env = b05_env
    seal(env)
    review = create(env)
    saved = record(env)
    with pytest.raises(DBAPIError) as exc:
        with env[5].begin() as conn:
            conn.execute(text(B11_SHARE_SQL))
            conn.execute(text(f'SET LOCAL ROLE "{normal_sql_role}"'))
            if mutation == "parent_update":
                sql = "UPDATE decision_records SET rationale='Other' WHERE id=:id"
            elif mutation == "parent_delete":
                sql = "DELETE FROM decision_records WHERE id=:id"
            elif mutation == "basis_update":
                sql = "UPDATE decision_basis_manuscripts SET ordinal=2 WHERE decision_id=:id"
            elif mutation == "basis_delete":
                sql = "DELETE FROM decision_basis_manuscripts WHERE decision_id=:id"
            elif mutation == "late_review":
                sql = "INSERT INTO decision_basis_reviews VALUES (:id,:review,2)"
            else:
                sql = "INSERT INTO decision_basis_manuscripts VALUES (:id,:target,2)"
            conn.execute(
                text(sql), dict(id=saved.id, review=review.id, target=env[1].manuscript_version_id)
            )
    assert getattr(exc.value.orig, "sqlstate", None) == "P17F1"


def test_populated_release_upgrade_and_permissible_downgrade_preserve_history(decision_env):
    from tests.integration.phase2.test_pr2_15_decision import _command, _review

    env = decision_env
    _review(env)
    request = _command(env)
    saved = env[0].record_decision(env[2], request)
    base = env[-1]
    c = Config("alembic.ini")
    c.set_main_option("sqlalchemy.url", base[8].url.render_as_string(hide_password=False))

    def history():
        with base[8].connect() as conn:
            return {
                table: conn.execute(text(f"SELECT * FROM {table} ORDER BY 1")).all()
                for table in (
                    "decision_records",
                    "decision_basis_conclusions",
                    "decision_basis_reviews",
                )
            }

    before = history()
    alembic.downgrade(c, "0053_b08_issue_disposition")
    assert history() == before
    alembic.upgrade(c, "0054_b11_ready_for_submission")
    assert history() == before
    alembic.downgrade(c, "0053_b08_issue_disposition")
    assert history() == before
    alembic.upgrade(c, "head")
    assert env[0].record_decision(env[2], request).content_hash == saved.content_hash


def test_temporary_table_cannot_spoof_preheld_inventory(b05_env, normal_sql_role):
    env = b05_env
    with pytest.raises(DBAPIError) as exc:
        with env[5].begin() as conn:
            conn.execute(text(f'SET LOCAL ROLE "{normal_sql_role}"'))
            conn.execute(text("CREATE TEMP TABLE actors(id UUID)"))
            conn.execute(text(B11_SHARE_SQL))
            conn.execute(text("SELECT b11_require_snapshot()"))
    assert getattr(exc.value.orig, "sqlstate", None) == "P17F2"


def test_downgrade_restores_live_0053_function_definitions(phase2_database_url):
    c = Config("alembic.ini")
    c.set_main_option("sqlalchemy.url", phase2_database_url.replace("%", "%%"))
    engine = create_engine(phase2_database_url)

    def definitions():
        with engine.connect() as conn:
            return conn.execute(
                text("""SELECT p.proname,pg_get_functiondef(p.oid),p.proconfig
                FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                WHERE n.nspname='public'
                  AND p.proname IN ('pr215_basis_guard','pr215_complete_basis')
                ORDER BY p.proname""")
            ).all()

    try:
        alembic.upgrade(c, "0053_b08_issue_disposition")
        before = definitions()
        assert len(before) == 2
        assert all(row.proconfig is None for row in before)
        alembic.upgrade(c, "0054_b11_ready_for_submission")
        upgraded = definitions()
        assert len(upgraded) == 2
        assert all(row.proconfig == ["search_path=pg_catalog, public, pg_temp"] for row in upgraded)
        alembic.downgrade(c, "0053_b08_issue_disposition")
        assert definitions() == before
        alembic.upgrade(c, "0054_b11_ready_for_submission")
        assert definitions() == upgraded
        alembic.upgrade(c, "head")
        integrated = definitions()
        assert all(
            row.proconfig == ["search_path=pg_catalog, public, pg_temp"] for row in integrated
        )
        for row in integrated:
            assert "READY_FOR_SUBMISSION" in row[1]
            assert "REVISION_RESPONSE" in row[1]
            assert "RECONSIDER_REJECTION" in row[1]
        alembic.downgrade(c, "0053_b08_issue_disposition")
        assert definitions() == before
        alembic.upgrade(c, "head")
        assert definitions() == integrated
    finally:
        engine.dispose()
