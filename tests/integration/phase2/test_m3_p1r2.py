"""Real Alembic downgrade race regressions for M3-P1R2."""

# Pytest discovers the imported M3 fixture by name.
# ruff: noqa: F401, F811

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from researchbase.domain.literature_evidence import digest, ref, snapshot_material, support_material
from tests.integration.phase2.test_m3_evidence import create, m3


def _alembic(database_url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _insert_empty_snapshot(connection, m3) -> UUID:
    service, author, _reviewer, project, _source, hypothesis, *_ = m3
    with service._factory() as uow:
        target = uow.literature_evidence.target("HypothesisVersion", hypothesis, project)
    binding_hash = digest(support_material([]))
    content_hash = digest(
        snapshot_material(
            {
                "project_id": project,
                "snapshot_number": 1,
                "literature_support_set_hash": binding_hash,
            },
            ref("HypothesisVersion", target),
            None,
        )
    )
    snapshot_id = uuid4()
    at = datetime.now(UTC)
    connection.execute(
        text("""INSERT INTO literature_support_snapshots
            (id,project_id,hypothesis_version_id,snapshot_number,
             literature_support_set_hash,content_hash,hash_scheme,
             created_by,created_at,frozen_at)
            VALUES (:id,:project,:target,1,:binding,:content,
                    'sha256-cjson-v1',:actor,:at,:at)"""),
        {
            "id": snapshot_id,
            "project": project,
            "target": hypothesis,
            "binding": binding_hash,
            "content": content_hash,
            "actor": author.actor_id,
            "at": at,
        },
    )
    return snapshot_id


def _cardinality_trigger_count(connection) -> int:
    return connection.execute(
        text("""SELECT count(*) FROM pg_trigger
            WHERE tgrelid IN ('literature_support_snapshots'::regclass,
                              'literature_evidence_relations'::regclass)
              AND tgname IN ('m3_snapshot_relation_cardinality','m3_relation_cardinality')""")
    ).scalar_one()


def test_downgrade_observes_insert_committed_while_waiting_for_table_lock(m3):
    service, author, _reviewer, project, _source, _hypothesis, _document, engine, _ = m3
    config = _alembic(engine.url.render_as_string(hide_password=False))
    writer = engine.connect()
    try:
        snapshot_id = _insert_empty_snapshot(writer, m3)
        writer_pid = writer.execute(text("SELECT pg_backend_pid()")).scalar_one()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(command.downgrade, config, "0030_literature_evidence")
            deadline = time.monotonic() + 10
            blocked = False
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as observer:
                while time.monotonic() < deadline and not future.done():
                    blocked = observer.execute(
                        text("""SELECT EXISTS (
                            SELECT 1 FROM pg_stat_activity a
                            WHERE a.datname=current_database() AND a.pid<>:writer_pid
                              AND :writer_pid=ANY(pg_blocking_pids(a.pid)))"""),
                        {"writer_pid": writer_pid},
                    ).scalar_one()
                    if blocked:
                        break
                    time.sleep(0.01)
            writer.commit()
            assert blocked, "downgrade never waited for the writer's table lock"
            with pytest.raises(Exception, match="preserves nonempty scientific history"):
                future.result(timeout=10)
        with engine.connect() as observer:
            assert observer.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one() == ("0031_m3_snapshot_relation_cardinality")
            assert _cardinality_trigger_count(observer) == 2
        assert service.get_snapshot(author, project, snapshot_id)["validity"] == "VALID"
    finally:
        writer.rollback()
        writer.close()


def test_downgrade_holds_both_table_locks_until_commit(m3):
    from threading import Event
    from unittest.mock import patch

    from alembic import op
    from sqlalchemy.exc import DBAPIError

    service, _author, _reviewer, _project, _source, _hypothesis, _document, engine, _ = m3
    config = _alembic(engine.url.render_as_string(hide_password=False))
    lock_acquired = Event()
    release_downgrade = Event()
    real_execute = op.execute

    def pause_after_real_lock(sql, *args, **kwargs):
        result = real_execute(sql, *args, **kwargs)
        if isinstance(sql, str) and sql.lstrip().startswith(
            "LOCK TABLE literature_support_snapshots, literature_evidence_relations"
        ):
            lock_acquired.set()
            if not release_downgrade.wait(timeout=10):
                raise AssertionError("downgrade lock pause was not released")
        return result

    with engine.connect() as observer:
        snapshot_oid, relation_oid = observer.execute(
            text("""SELECT 'literature_support_snapshots'::regclass::oid,
                           'literature_evidence_relations'::regclass::oid""")
        ).one()
    try:
        with patch.object(op, "execute", pause_after_real_lock):
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(command.downgrade, config, "0030_literature_evidence")
                try:
                    assert lock_acquired.wait(timeout=10), (
                        "real downgrade never acquired both locks"
                    )
                    with engine.connect() as observer:
                        locked_oids = set(
                            observer.execute(
                                text("""SELECT relation FROM pg_locks
                                    WHERE relation IN (:snapshot_oid,:relation_oid)
                                      AND mode='AccessExclusiveLock' AND granted"""),
                                {"snapshot_oid": snapshot_oid, "relation_oid": relation_oid},
                            ).scalars()
                        )
                    assert locked_oids == {snapshot_oid, relation_oid}
                    with engine.connect() as observer:
                        assert observer.execute(
                            text("SELECT version_num FROM alembic_version")
                        ).scalar_one() == ("0031_m3_snapshot_relation_cardinality")
                        assert _cardinality_trigger_count(observer) == 2
                    with engine.connect() as writer:
                        writer.execute(text("SET lock_timeout='300ms'"))
                        with pytest.raises(DBAPIError) as blocked:
                            _insert_empty_snapshot(writer, m3)
                        assert getattr(blocked.value.orig, "sqlstate", None) == "55P03"
                        writer.rollback()
                    assert not future.done(), "downgrade committed while paused after the locks"
                finally:
                    release_downgrade.set()
                future.result(timeout=10)
        with engine.connect() as observer:
            assert observer.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one() == ("0030_literature_evidence")
            assert _cardinality_trigger_count(observer) == 0
    finally:
        release_downgrade.set()


def test_populated_downgrade_rolls_back_and_keeps_cardinality_guard(m3):
    from sqlalchemy.exc import DBAPIError

    service, author, _reviewer, project, _source, hypothesis, _document, engine, _ = m3
    config = _alembic(engine.url.render_as_string(hide_password=False))
    snapshot = service.snapshot(author, project, "HypothesisVersion", hypothesis, [], uuid4())
    with pytest.raises(DBAPIError, match="preserves nonempty scientific history") as failure:
        command.downgrade(config, "0030_literature_evidence")
    assert getattr(failure.value.orig, "sqlstate", None) == "P17D5"
    with engine.connect() as observer:
        assert observer.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0031_m3_snapshot_relation_cardinality"
        )
        assert _cardinality_trigger_count(observer) == 2
        assert (
            observer.execute(
                text("SELECT count(*) FROM literature_support_snapshots WHERE id=:id"),
                {"id": UUID(snapshot["id"])},
            ).scalar_one()
            == 1
        )
    assert service.get_snapshot(author, project, UUID(snapshot["id"])) == snapshot

    evidence = create(m3)
    with pytest.raises(DBAPIError) as gap:
        with engine.begin() as writer:
            new_id = uuid4()
            at = datetime.now(UTC)
            writer.execute(
                text("""INSERT INTO literature_support_snapshots
                    (id,project_id,hypothesis_version_id,snapshot_number,previous_snapshot_id,
                     literature_support_set_hash,content_hash,hash_scheme,
                     created_by,created_at,frozen_at)
                    VALUES (:id,:project,:target,2,:previous,:digest,:digest,
                            'sha256-cjson-v1',:actor,:at,:at)"""),
                {
                    "id": new_id,
                    "project": project,
                    "target": hypothesis,
                    "previous": UUID(snapshot["id"]),
                    "digest": "0" * 64,
                    "actor": author.actor_id,
                    "at": at,
                },
            )
            writer.execute(
                text("""INSERT INTO literature_evidence_relations
                    (id,literature_support_snapshot_id,literature_evidence_id,
                     relation_type,ordinal,qualification,created_by,created_at)
                    VALUES (:id,:snapshot,:evidence,'CONTEXTUALIZES',1,
                            'Context only',:actor,:at)"""),
                {
                    "id": uuid4(),
                    "snapshot": new_id,
                    "evidence": UUID(evidence["id"]),
                    "actor": author.actor_id,
                    "at": at,
                },
            )
    assert getattr(gap.value.orig, "sqlstate", None) == "23514"


def test_empty_downgrade_removes_only_0031_guards(m3):
    _service, _author, _reviewer, _project, _source, _hypothesis, _document, engine, _ = m3
    config = _alembic(engine.url.render_as_string(hide_password=False))
    trigger_query = text("""SELECT tgrelid::regclass::text,tgname FROM pg_trigger
        WHERE tgrelid IN ('literature_support_snapshots'::regclass,
                          'literature_evidence_relations'::regclass)""")
    with engine.connect() as observer:
        before = set(observer.execute(trigger_query).all())
        assert _cardinality_trigger_count(observer) == 2
    command.downgrade(config, "0030_literature_evidence")
    with engine.connect() as observer:
        after = set(observer.execute(trigger_query).all())
        assert before - after == {
            ("literature_support_snapshots", "m3_snapshot_relation_cardinality"),
            ("literature_evidence_relations", "m3_relation_cardinality"),
        }
        assert after - before == set()
        assert observer.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0030_literature_evidence"
        )
        assert _cardinality_trigger_count(observer) == 0
        assert (
            observer.execute(
                text("SELECT to_regprocedure('m3_validate_snapshot_relation_cardinality()')")
            ).scalar_one()
            is None
        )
