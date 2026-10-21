"""Forward-only consent guard changes, native transaction causes and retained roots."""

from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError

from researchbase.persistence.prepared_submission_repository import B16_SHARE_SQL
from tests.integration.phase2.b16_fixtures import (  # noqa: F401
    b04_env as _b04_env,
)
from tests.integration.phase2.b16_fixtures import (
    b15_env as _b15_env,
)
from tests.integration.phase2.b16_fixtures import (
    conclusion_env as _conclusion_env,
)
from tests.integration.phase2.b16_fixtures import (
    rooted,
    successor,
)
from tests.integration.phase2.test_b15_package_schema import normal_sql_role as _normal_sql_role
from tests.integration.phase2.test_pr2_17_authorship_schema import _insert

normal_sql_role = _normal_sql_role
b04_env = _b04_env
b15_env = _b15_env
conclusion_env = _conclusion_env


def prefix(conn):
    conn.execute(text(B16_SHARE_SQL))
    conn.execute(text("LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE"))
    conn.execute(
        text(
            "LOCK TABLE approval_decisions,approval_request_reviews,approval_requests IN SHARE MODE"
        )
    )


def test_catalog_and_root_upgrade_downgrade_preserve_hashes(b15_env, monkeypatch):
    _, _, _, _, engine, *_ = b15_env
    _, _, _, root = rooted(b15_env)
    url = engine.url.render_as_string(hide_password=False)
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    with engine.connect() as conn:
        before = set(inspect(conn).get_table_names())
        checks = {c["name"] for c in inspect(conn).get_check_constraints("author_consents")}
        assert {"ck_b16_consent_" + s for s in ("state", "scope", "root", "not_self")} <= checks
        assert all(
            f["options"].get("ondelete") == "RESTRICT"
            for f in inspect(conn).get_foreign_keys("author_consents")
        )
        assert not next(
            c
            for c in inspect(conn).get_columns("author_consents")
            if c["name"] == "evidence_artifact_version_id"
        )["nullable"]
    command.downgrade(config, "0060_b15_package_preparation")
    command.upgrade(config, "head")
    with engine.connect() as conn:
        assert set(inspect(conn).get_table_names()) == before
        assert (
            conn.execute(
                text("SELECT content_hash FROM author_consents WHERE id=:id"), {"id": root.id}
            ).scalar_one()
            == root.content_hash
        )
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM pg_trigger WHERE tgname LIKE 'b16_%' "
                    "AND tgdeferrable AND tginitdeferred"
                )
            ).scalar_one()
            == 4
        )


def test_successor_history_refuses_downgrade(b15_env, monkeypatch):
    service, _, actor, _, engine, *_ = b15_env
    _, _, cmd, root = rooted(b15_env)
    service.record_author_consent(actor, successor(cmd, root))
    url = engine.url.render_as_string(hide_password=False)
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    with pytest.raises(DBAPIError, match="retained B16 history"):
        command.downgrade(config, "0060_b15_package_preparation")


@pytest.mark.parametrize(
    "defect,expected",
    [
        ("missing_prefix", "P16G1"),
        ("same_state", "P15S2"),
        ("wrong_hash", "P17F2"),
        ("missing_evidence", "P17F2"),
    ],
)
def test_normal_role_rejects_malformed_successors(b15_env, normal_sql_role, defect, expected):
    service, _, actor, _, engine, *_ = b15_env
    _, _, _, root = rooted(b15_env)
    with engine.connect() as conn:
        raw = dict(
            conn.execute(text("SELECT * FROM author_consents WHERE id=:id"), {"id": root.id})
            .mappings()
            .one()
        )
    raw.update(id=uuid4(), prior_consent_id=root.id, consent_state="WITHDRAWN")
    if defect == "same_state":
        raw["consent_state"] = "GRANTED"
    if defect == "missing_evidence":
        raw["evidence_artifact_version_id"] = None
    with pytest.raises(DBAPIError) as exc, engine.begin() as conn:
        if defect != "missing_prefix":
            prefix(conn)
        conn.execute(text(f'SET LOCAL ROLE "{normal_sql_role}"'))
        _insert(conn, "author_consents", raw)
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert getattr(exc.value.orig, "sqlstate", None) == expected


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE author_consents SET consent_state='WITHDRAWN' WHERE id=:id",
        "DELETE FROM author_consents WHERE id=:id",
    ],
)
def test_consent_immutable_even_with_protocol(b15_env, normal_sql_role, sql):
    _, _, _, _, engine, *_ = b15_env
    _, _, _, root = rooted(b15_env)
    with pytest.raises(DBAPIError) as exc, engine.begin() as conn:
        prefix(conn)
        conn.execute(text(f'SET LOCAL ROLE "{normal_sql_role}"'))
        conn.execute(text(sql), {"id": root.id})
    assert getattr(exc.value.orig, "sqlstate", None) == "P15S1"


@pytest.mark.parametrize(
    "case",
    [
        "forged_cause",
        "missing_event",
        "extra_event",
        "wrong_event",
        "active_remainder",
        "issuance_missing_prefix",
    ],
)
def test_prepare_grant_graph_guards(b15_env, b04_env, normal_sql_role, case):
    from tests.integration.phase2.b16_fixtures import grant_context, issue_grant, sql_withdrawal

    ctx = grant_context(b15_env, b04_env[-1][4])
    grant = issue_grant(ctx)
    engine, author = b15_env[4], b15_env[2]
    with pytest.raises(DBAPIError) as exc, engine.begin() as conn:
        if case != "issuance_missing_prefix":
            prefix(conn)
        conn.execute(text(f'SET LOCAL ROLE "{normal_sql_role}"'))
        if case == "issuance_missing_prefix":
            raw = dict(
                conn.execute(text("SELECT * FROM approval_grants WHERE id=:id"), {"id": grant.id})
                .mappings()
                .one()
            )
            raw["id"] = uuid4()
            _insert(conn, "approval_grants", raw)
        else:
            identity, at = (uuid4(), None) if case == "forged_cause" else sql_withdrawal(conn, ctx)
            if case == "missing_event":
                conn.execute(
                    text("UPDATE approval_grants SET status='STALE' WHERE id=:id"), {"id": grant.id}
                )
            elif case != "active_remainder":
                at = at or conn.execute(text("SELECT clock_timestamp()")).scalar_one()
                actor = ctx["approver"].actor_id if case == "wrong_event" else author.actor_id
                values = dict(
                    grant=grant.id,
                    actor=actor,
                    at=at,
                    reason=f"author consent withdrawn:{identity}",
                )
                statement = text(
                    "INSERT INTO approval_grant_events(grant_id,prior_status,new_status,"
                    "actor_id,occurred_at,reason) "
                    "VALUES(:grant,'ACTIVE','STALE',:actor,:at,:reason)"
                )
                conn.execute(statement, values)
                conn.execute(
                    text("UPDATE approval_grants SET status='STALE' WHERE id=:id"), {"id": grant.id}
                )
                if case == "extra_event":
                    conn.execute(statement, values)
            conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    state = getattr(exc.value.orig, "sqlstate", None)
    assert state in {"P16G1", "P16A1", "P17F1", "P17F2"}
    if case == "active_remainder":
        assert state == "P17F2"
    if case == "issuance_missing_prefix":
        assert "preheld prepare issuance" in str(exc.value.orig)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM author_consents")).scalar_one() == 1
        assert (
            conn.execute(
                text("SELECT status FROM approval_grants WHERE id=:id"), {"id": grant.id}
            ).scalar_one()
            == "ACTIVE"
        )
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM approval_grant_events WHERE prior_status='ACTIVE' "
                    "AND grant_id IN (SELECT id FROM approval_grants "
                    "WHERE purpose='PREPARE_SUBMISSION')"
                )
            ).scalar_one()
            == 0
        )


def test_roundtrip_restores_exact_0060_function_catalog(monkeypatch):
    from sqlalchemy import create_engine

    from tests.disposable_postgres import disposable_database

    with disposable_database("researchbase_pr212_test_", "RB_TEST_ADMIN_URL") as url:
        monkeypatch.setenv("DATABASE_URL", url)
        cfg = Config("alembic.ini")
        cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
        engine = create_engine(url)

        def catalog():
            with engine.connect() as conn:
                return {
                    (r[0], r[1]): (r[2], r[3])
                    for r in conn.execute(
                        text(
                            "SELECT proname,pg_get_function_identity_arguments(oid),"
                            "pg_get_functiondef(oid),proconfig FROM pg_proc "
                            "WHERE pronamespace='public'::regnamespace AND prokind='f'"
                        )
                    )
                }

        try:
            # Obtain the real predecessor by forward migration only, never by B16 restoration.
            command.upgrade(cfg, "0060_b15_package_preparation")
            before = catalog()
            command.upgrade(cfg, "head")
            after = catalog()
            command.downgrade(cfg, "0060_b15_package_preparation")
            assert catalog() == before
            command.upgrade(cfg, "head")
            assert catalog() == after
        finally:
            engine.dispose()
