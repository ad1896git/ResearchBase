"""TEST ONLY SQL coordination; fixture databases and roles are disposable."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from tests.integration.phase2.test_pr2_14_conclusion_review import (
    _frozen_conclusion,
    conclusion_env,
    phase2_database_url,
)
from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker

pytestmark = pytest.mark.integration
# Imported fixture aliases deliberately use the accepted identity-checking fixture.
assert conclusion_env and phase2_database_url
REVISION = "0041_pr2_15_review_coordination"


@pytest.fixture
def coordination_env(conclusion_env, phase2_database_url):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "head")
    service, _, reviewer, project, version, engine = _frozen_conclusion(conclusion_env)
    review = service.create(
        reviewer,
        project,
        "SCIENTIFIC_CONCLUSION_VERSION",
        version,
        "SCIENTIFIC",
        "UNCERTAIN",
        "Test-only immutable review",
        (),
        uuid4(),
    )
    # Roles are cluster-scoped, unique, NOLOGIN, and removed before fixture DB cleanup.
    role = f"pr215_sql_{uuid4().hex}"
    with engine.begin() as conn:
        conn.execute(text(f'CREATE ROLE "{role}" NOLOGIN NOSUPERUSER'))
        conn.execute(text(f'GRANT USAGE ON SCHEMA public TO "{role}"'))
        conn.execute(
            text(f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "{role}"')
        )
    print("PR215_ROLE_CREATED", role)
    try:
        yield config, engine, version, review, role
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP OWNED BY "{role}"'))
            conn.execute(text(f'DROP ROLE "{role}"'))
        print("PR215_ROLE_DROPPED", role)


def _normal(conn, role):
    conn.execute(text(f'SET LOCAL ROLE "{role}"'))
    assert not conn.execute(
        text("SELECT rolsuper FROM pg_roles WHERE rolname=current_user")
    ).scalar_one()
    conn.execute(text("SET LOCAL statement_timeout='12s'"))


def _insert(conn, kind, review):
    identity = uuid4()
    if kind == "review":
        conn.execute(
            text("""INSERT INTO internal_review_records
          (id,project_id,scientific_conclusion_version_id,target_content_hash,
           reviewer_actor_id,review_type,recommendation,summary,created_at,
           content_hash,hash_scheme)
          SELECT :new,id_project,scientific_conclusion_version_id,target_content_hash,
           reviewer_actor_id,review_type,recommendation,summary,clock_timestamp(),
           content_hash,hash_scheme FROM
           (SELECT *, project_id AS id_project FROM internal_review_records WHERE id=:old) r"""),
            {"new": identity, "old": review.id},
        )
    else:
        conn.execute(
            text("""INSERT INTO review_issues
          (id,review_record_id,severity,issue_type,description,status,created_at,ordinal)
          VALUES (:id,:review,'BLOCKING','OVERCLAIM','Test-only blocker',
                  'OPEN',clock_timestamp(),0)"""),
            {"id": identity, "review": review.id},
        )
    return identity


@pytest.mark.parametrize("kind", ["review", "issue"])
def test_target_first_writer_waits_even_on_share_lock(coordination_env, kind):
    """FOR SHARE witnesses FOR UPDATE from the start, not a compatible weaker lock."""
    _, engine, version, review, role = coordination_env

    def writer():
        with engine.begin() as conn:
            _normal(conn, role)
            return _insert(conn, kind, review)

    with ThreadPoolExecutor(max_workers=1) as pool:
        with engine.begin() as holder:
            _normal(holder, role)
            pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
            holder.execute(
                text("SELECT id FROM scientific_conclusion_versions WHERE id=:id FOR SHARE"),
                {"id": version},
            )
            pending = pool.submit(writer)
            witness = _wait_for_pg_blocker(engine, pid, "transactionid")
            assert kind in witness["query"]
            assert not pending.done()
        identity = pending.result(timeout=15)
    with engine.connect() as conn:
        table = "internal_review_records" if kind == "review" else "review_issues"
        assert (
            conn.execute(
                text(f"SELECT count(*) FROM {table} WHERE id=:id"), {"id": identity}
            ).scalar_one()
            == 1
        )


@pytest.mark.parametrize("kind", ["review", "issue"])
def test_writer_first_holds_target_until_commit_and_fresh_read_sees_insert(coordination_env, kind):
    _, engine, version, review, role = coordination_env

    def snapshot():
        with engine.begin() as conn:
            _normal(conn, role)
            conn.execute(
                text("SELECT id FROM scientific_conclusion_versions WHERE id=:id FOR UPDATE"),
                {"id": version},
            )
            table = "internal_review_records" if kind == "review" else "review_issues"
            return conn.execute(
                text(f"SELECT count(*) FROM {table} WHERE id=:id"), {"id": identity}
            ).scalar_one()

    with ThreadPoolExecutor(max_workers=1) as pool:
        with engine.begin() as writer:
            _normal(writer, role)
            pid = writer.execute(text("SELECT pg_backend_pid()")).scalar_one()
            identity = _insert(writer, kind, review)
            pending = pool.submit(snapshot)
            witness = _wait_for_pg_blocker(engine, pid, "transactionid")
            assert "scientific_conclusion_versions" in witness["query"]
            assert not pending.done()
        assert pending.result(timeout=15) == 1


@pytest.mark.parametrize("table", ["internal_review_records", "review_issues"])
@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
def test_history_stays_immutable(coordination_env, table, operation):
    _, engine, _, review, role = coordination_env
    with engine.begin() as conn:
        _insert(conn, "issue", review)
    with pytest.raises(DBAPIError) as error, engine.begin() as conn:
        _normal(conn, role)
        sql = f"DELETE FROM {table}" if operation == "DELETE" else f"UPDATE {table} SET id=id"
        conn.execute(text(sql))
    assert getattr(error.value.orig, "sqlstate", None) == (
        "P17F1" if table == "review_issues" else "P17E1"
    )


def test_catalog_and_downgrade_refuses_to_remove_history_guarantees(coordination_env):
    config, engine, _, review, _ = coordination_env
    installed_head = ScriptDirectory.from_config(config).get_current_head()
    with engine.connect() as conn:
        before = conn.execute(
            text("SELECT * FROM internal_review_records WHERE id=:id"), {"id": review.id}
        ).one()
        names = set(
            conn.execute(
                text("""SELECT tgname FROM pg_trigger
          WHERE NOT tgisinternal AND tgrelid IN
          ('internal_review_records'::regclass,'review_issues'::regclass)""")
            ).scalars()
        )
        assert {"pr214_review_guard", "pr214_issue_guard", "pr214_open_event"} <= names
        assert (
            conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == installed_head
        )
    with pytest.raises(DBAPIError):
        command.downgrade(config, "0040_pr2_14_initial_internal_review")
    with engine.connect() as conn:
        assert (
            conn.execute(
                text("SELECT * FROM internal_review_records WHERE id=:id"), {"id": review.id}
            ).one()
            == before
        )
        assert (
            conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == installed_head
        )


def test_empty_upgrade_downgrade_round_trip(phase2_database_url):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "0040_pr2_14_initial_internal_review")
    engine = create_engine(phase2_database_url)

    def catalog():
        with engine.connect() as conn:
            return (
                conn.execute(
                    text("""SELECT conrelid::regclass::text,conname,
                  pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid IN
                  ('internal_review_records'::regclass,'review_issues'::regclass,
                   'review_issue_events'::regclass) ORDER BY 1,2""")
                ).all(),
                conn.execute(
                    text("""SELECT tablename,indexname,indexdef FROM pg_indexes
                  WHERE tablename IN ('internal_review_records','review_issues',
                    'review_issue_events') ORDER BY 1,2""")
                ).all(),
            )

    before = catalog()
    command.upgrade(config, REVISION)
    assert catalog() == before
    command.downgrade(config, "0040_pr2_14_initial_internal_review")
    assert catalog() == before
    command.upgrade(config, REVISION)
    assert catalog() == before
    engine.dispose()


def test_application_target_precedes_project_authority_lock(conclusion_env, phase2_database_url):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "head")
    service, _, reviewer, project, version, engine = _frozen_conclusion(conclusion_env)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with engine.begin() as holder:
            pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
            holder.execute(text("SELECT id FROM projects WHERE id=:id FOR UPDATE"), {"id": project})
            pending = pool.submit(
                service.create,
                reviewer,
                project,
                "SCIENTIFIC_CONCLUSION_VERSION",
                version,
                "SCIENTIFIC",
                "ACCEPT",
                "Test-only target before authority",
                (),
                uuid4(),
            )
            witness = _wait_for_pg_blocker(engine, pid, "transactionid")
            assert "project" in witness["query"]
            # The blocked command must already exclude competing target writers.
            with pytest.raises(DBAPIError) as error, engine.begin() as observer:
                observer.execute(
                    text(
                        "SELECT id FROM scientific_conclusion_versions "
                        "WHERE id=:id FOR UPDATE NOWAIT"
                    ),
                    {"id": version},
                )
            assert getattr(error.value.orig, "sqlstate", None) == "55P03"
        pending.result(timeout=15)


@pytest.mark.parametrize("kind", ["review", "issue"])
def test_sql_target_precedes_parent_or_review_row(coordination_env, kind):
    _, engine, version, review, role = coordination_env

    def writer():
        with engine.begin() as conn:
            _normal(conn, role)
            return _insert(conn, kind, review)

    with ThreadPoolExecutor(max_workers=1) as pool:
        with engine.begin() as holder:
            pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
            if kind == "review":
                holder.execute(
                    text("""SELECT c.id FROM scientific_conclusions c
                  JOIN scientific_conclusion_versions v ON v.scientific_conclusion_id=c.id
                  WHERE v.id=:id FOR UPDATE OF c"""),
                    {"id": version},
                )
            else:
                holder.execute(
                    text("SELECT id FROM internal_review_records WHERE id=:id FOR UPDATE"),
                    {"id": review.id},
                )
            pending = pool.submit(writer)
            _wait_for_pg_blocker(engine, pid, "transactionid")
            with pytest.raises(DBAPIError) as error, engine.begin() as observer:
                observer.execute(
                    text(
                        "SELECT id FROM scientific_conclusion_versions "
                        "WHERE id=:id FOR UPDATE NOWAIT"
                    ),
                    {"id": version},
                )
            assert getattr(error.value.orig, "sqlstate", None) == "55P03"
        pending.result(timeout=15)


def test_initial_reviews_do_not_upgrade_share_locks_during_issue_insert(coordination_env):
    _, engine, _, review, role = coordination_env

    def second_writer():
        with engine.begin() as conn:
            _normal(conn, role)
            identity = _insert(conn, "review", review)
            conn.execute(
                text("""INSERT INTO review_issues
              (id,review_record_id,severity,issue_type,description,status,created_at,ordinal)
              VALUES (:id,:review,'BLOCKING','OVERCLAIM','Test-only second initial issue',
                      'OPEN',clock_timestamp(),0)"""),
                {"id": uuid4(), "review": identity},
            )

    with ThreadPoolExecutor(max_workers=1) as pool:
        with engine.begin() as first:
            _normal(first, role)
            pid = first.execute(text("SELECT pg_backend_pid()")).scalar_one()
            identity = _insert(first, "review", review)
            pending = pool.submit(second_writer)
            _wait_for_pg_blocker(engine, pid, "transactionid")
            # The first writer already owns UPDATE; Issue insert cannot form an upgrade cycle.
            first.execute(
                text("""INSERT INTO review_issues
              (id,review_record_id,severity,issue_type,description,status,created_at,ordinal)
              VALUES (:id,:review,'BLOCKING','OVERCLAIM','Test-only first initial issue',
                      'OPEN',clock_timestamp(),0)"""),
                {"id": uuid4(), "review": identity},
            )
        pending.result(timeout=15)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM review_issues")).scalar_one() == 2
        assert conn.execute(text("SELECT count(*) FROM review_issue_events")).scalar_one() == 2
