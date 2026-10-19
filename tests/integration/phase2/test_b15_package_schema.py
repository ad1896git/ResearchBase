"""B15 PostgreSQL catalog, preserved migrations and normal-role aggregate guards."""

from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError

from researchbase.persistence.prepared_submission_repository import B15_SHARE_SQL, B16_SHARE_SQL
from tests.disposable_postgres import disposable_database
from tests.integration.phase2.b15_support import (  # noqa: F401
    b04_env as _b04_env,
)
from tests.integration.phase2.b15_support import (
    b15_env as _b15_env,
)
from tests.integration.phase2.b15_support import (
    conclusion_env as _conclusion_env,
)
from tests.integration.phase2.b15_support import (
    prepared,
)
from tests.integration.phase2.test_pr2_17_authorship_schema import _insert

b04_env = _b04_env
b15_env = _b15_env
conclusion_env = _conclusion_env

pytestmark = pytest.mark.integration

TABLES = (
    "prepared_submission_versions",
    "author_consents",
    "prepared_submission_manifest_items",
    "prepared_submission_events",
)


@pytest.fixture
def normal_sql_role(b15_env):
    engine = b15_env[4]
    role = f"b15_test_{uuid4().hex}"
    with engine.begin() as conn:
        conn.execute(text(f'CREATE ROLE "{role}" NOLOGIN NOSUPERUSER'))
        conn.execute(text(f'GRANT USAGE ON SCHEMA public TO "{role}"'))
        conn.execute(
            text(f'GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO "{role}"')
        )
    try:
        yield role
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP OWNED BY "{role}"'))
            conn.execute(text(f'DROP ROLE "{role}"'))


def test_clean_upgrade_catalog_and_empty_downgrade(monkeypatch):
    with disposable_database("researchbase_pr212_test_", "RB_TEST_ADMIN_URL") as url:
        monkeypatch.setenv("DATABASE_URL", url)
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
        command.upgrade(config, "0059_b13_grant_consumption")
        engine = create_engine(url)
        with engine.connect() as conn:
            before = set(inspect(conn).get_table_names())
        command.upgrade(config, "head")
        with engine.connect() as conn:
            assert int(conn.execute(text("SHOW server_version_num")).scalar_one()) // 10000 == 18
            assert set(inspect(conn).get_table_names()) - before == set(TABLES) | {
                "novelty_assessment_prior_art_inputs",
                "search_coverage_resolutions",
                "novelty_assessment_probes",
                "novelty_assessment_screening_results",
            }
            assert (
                conn.execute(
                    text(
                        "SELECT count(*) FROM pg_trigger WHERE tgname LIKE 'b15_%' "
                        "AND tgdeferrable AND tginitdeferred"
                    )
                ).scalar_one()
                == 4
            )
            assert all(
                fk.get("options", {}).get("ondelete") == "RESTRICT"
                for table in TABLES
                for fk in inspect(conn).get_foreign_keys(table)
            )
            assert "uq_author_consents_root" in {
                i["name"] for i in inspect(conn).get_indexes("author_consents")
            }
        command.downgrade(config, "0059_b13_grant_consumption")
        command.upgrade(config, "head")
        engine.dispose()


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE prepared_submission_versions SET manuscript_version_id=:new WHERE id=:id",
        "DELETE FROM prepared_submission_versions WHERE id=:id",
        "UPDATE prepared_submission_versions SET status='FROZEN' WHERE id=:id",
        "UPDATE prepared_submission_events SET reason='rewrite' "
        "WHERE prepared_submission_version_id=:id",
        "DELETE FROM prepared_submission_events WHERE prepared_submission_version_id=:id",
    ],
)
def test_normal_role_cannot_mutate_sealed_history(b15_env, normal_sql_role, sql):
    result, _ = prepared(b15_env)
    with pytest.raises(DBAPIError) as exc, b15_env[4].begin() as conn:
        conn.execute(text(B15_SHARE_SQL))
        conn.execute(text(f'SET LOCAL ROLE "{normal_sql_role}"'))
        conn.execute(text(sql), {"id": result.id, "new": uuid4()})
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert getattr(exc.value.orig, "sqlstate", None) == "P15S1"


def test_committed_empty_manifest_is_sealed(b15_env, normal_sql_role):
    service, _, actor, _, engine, *_ = b15_env
    result, _ = prepared(b15_env)
    with engine.connect() as conn:
        artifact = conn.execute(
            text("SELECT document_artifact_version_id FROM manuscript_versions WHERE id=:id"),
            {"id": result.manuscript_version_id},
        ).scalar_one()
    with pytest.raises(DBAPIError) as exc, engine.begin() as conn:
        conn.execute(text(B15_SHARE_SQL))
        conn.execute(text(f'SET LOCAL ROLE "{normal_sql_role}"'))
        _insert(
            conn,
            TABLES[2],
            {
                "id": uuid4(),
                "prepared_submission_version_id": result.id,
                "category": "FIGURE",
                "ordinal": 0,
                "artifact_version_id": artifact,
                "created_at": result.created_at,
                "created_by": actor.actor_id,
            },
        )
    assert getattr(exc.value.orig, "sqlstate", None) == "P15S1"


def test_final_graph_rejects_missing_event_and_preheld_inventory(b15_env, normal_sql_role):
    result, _ = prepared(b15_env)
    with b15_env[4].connect() as conn:
        raw = dict(
            conn.execute(
                text("SELECT * FROM prepared_submission_versions WHERE id=:id"), {"id": result.id}
            )
            .mappings()
            .one()
        )
    raw.update(id=uuid4(), version_number=2)
    with pytest.raises(DBAPIError) as exc, b15_env[4].begin() as conn:
        conn.execute(text(f'SET LOCAL ROLE "{normal_sql_role}"'))
        _insert(conn, TABLES[0], raw)
    assert getattr(exc.value.orig, "sqlstate", None) == "P15S3"
    with pytest.raises(DBAPIError) as exc, b15_env[4].begin() as conn:
        conn.execute(text(B15_SHARE_SQL))
        conn.execute(text(f'SET LOCAL ROLE "{normal_sql_role}"'))
        _insert(conn, TABLES[0], raw)
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert getattr(exc.value.orig, "sqlstate", None) == "P15S3"


def test_populated_downgrade_refuses(b15_env, monkeypatch):
    prepared(b15_env)
    url = b15_env[4].url.render_as_string(hide_password=False)
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    with pytest.raises(DBAPIError, match="retained package history"):
        command.downgrade(config, "0059_b13_grant_consumption")
    with b15_env[4].connect() as conn:
        assert (
            conn.execute(text("SELECT count(*) FROM prepared_submission_versions")).scalar_one()
            == 1
        )


@pytest.mark.parametrize("wrong", ["actor", "time", "reason"])
def test_terminal_event_matches_observed_transition(b15_env, normal_sql_role, wrong):
    import json
    from datetime import timedelta

    result, _ = prepared(b15_env)
    engine = b15_env[4]
    actor = b15_env[2].actor_id
    with pytest.raises(DBAPIError) as exc, engine.begin() as conn:
        conn.execute(text(B15_SHARE_SQL))
        conn.execute(text(f'SET LOCAL ROLE "{normal_sql_role}"'))
        at = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
        context = json.dumps(
            {
                "package": str(result.id),
                "actor": str(actor),
                "at": at.isoformat(),
                "reason": "observed",
            }
        )
        conn.execute(
            text("SELECT set_config('researchbase.b15_withdrawal', :context, true)"),
            {"context": context},
        )
        conn.execute(
            text(
                "UPDATE prepared_submission_versions SET status='WITHDRAWN',row_version=2 "
                "WHERE id=:id"
            ),
            {"id": result.id},
        )
        other_actor = conn.execute(
            text("SELECT id FROM actors WHERE id<>:actor LIMIT 1"), {"actor": actor}
        ).scalar_one()
        forged_at = at + timedelta(days=1) if wrong == "time" else at
        _insert(
            conn,
            "prepared_submission_events",
            {
                "id": uuid4(),
                "prepared_submission_version_id": result.id,
                "prior_status": "PREPARED",
                "new_status": "WITHDRAWN",
                "actor_id": other_actor if wrong == "actor" else actor,
                "occurred_at": forged_at,
                "reason": "forged" if wrong == "reason" else "observed",
                "created_by": other_actor if wrong == "actor" else actor,
                "created_at": forged_at,
            },
        )
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert getattr(exc.value.orig, "sqlstate", None) == "23505"


@pytest.mark.parametrize("immediate", [False, True])
def test_observation_cannot_be_rewritten_and_immediate_constraints_work(
    b15_env, normal_sql_role, immediate
):
    import json
    from datetime import timedelta

    result, _ = prepared(b15_env)
    actor = b15_env[2].actor_id
    engine = b15_env[4]
    with engine.begin() as conn:
        conn.execute(text(B15_SHARE_SQL))
        conn.execute(text(f'SET LOCAL ROLE "{normal_sql_role}"'))
        if immediate:
            conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        at = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
        context = {
            "package": str(result.id),
            "actor": str(actor),
            "at": at.isoformat(),
            "reason": "observed",
        }
        conn.execute(
            text("SELECT set_config('researchbase.b15_withdrawal',:context,true)"),
            {"context": json.dumps(context)},
        )
        conn.execute(
            text(
                "UPDATE prepared_submission_versions SET status='WITHDRAWN',row_version=2 "
                "WHERE id=:id"
            ),
            {"id": result.id},
        )
        forged = {**context, "at": (at + timedelta(days=1)).isoformat(), "reason": "forged"}
        conn.execute(
            text("SELECT set_config(:key,:context,true)"),
            {"key": "researchbase.b15_observed_" + result.id.hex, "context": json.dumps(forged)},
        )
        conn.execute(
            text("SELECT set_config('researchbase.b15_withdrawal',:context,true)"),
            {"context": json.dumps(forged)},
        )
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    with engine.connect() as conn:
        saved = conn.execute(
            text(
                "SELECT occurred_at,reason FROM prepared_submission_events "
                "WHERE prepared_submission_version_id=:id AND new_status='WITHDRAWN'"
            ),
            {"id": result.id},
        ).one()
        assert tuple(saved) == (at, "observed")


@pytest.mark.parametrize(
    "change,expected", [("duplicate", "23505"), ("successor", "P15S2"), ("nonauthor", "P17F2")]
)
def test_normal_sql_cannot_forge_root_shape(b15_env, normal_sql_role, change, expected):
    from tests.integration.phase2.b15_support import consent_command

    service, _, actor, _, engine, *_ = b15_env
    package, _ = prepared(b15_env)
    root = service.record_author_consent(actor, consent_command(b15_env, package.id))
    with engine.connect() as conn:
        raw = dict(
            conn.execute(text("SELECT * FROM author_consents WHERE id=:id"), {"id": root.id})
            .mappings()
            .one()
        )
        other = conn.execute(
            text("SELECT id FROM actors WHERE id<>:actor LIMIT 1"), {"actor": actor.actor_id}
        ).scalar_one()
    raw["id"] = uuid4()
    if change == "successor":
        raw["prior_consent_id"] = root.id
    if change == "nonauthor":
        raw.update(actor_id=other, created_by=other)
    with pytest.raises(DBAPIError) as exc, engine.begin() as conn:
        conn.execute(text(B16_SHARE_SQL))
        conn.execute(text("LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE"))
        conn.execute(
            text(
                "LOCK TABLE approval_decisions,approval_request_reviews,"
                "approval_requests IN SHARE MODE"
            )
        )
        conn.execute(text(f'SET LOCAL ROLE "{normal_sql_role}"'))
        _insert(conn, "author_consents", raw)
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert getattr(exc.value.orig, "sqlstate", None) == expected
