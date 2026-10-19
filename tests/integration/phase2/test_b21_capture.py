"""Historical membership through owning services and fresh engines."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from researchbase.application.novelty import (
    ExactReadQuery,
    NoveltyService,
    RecordSearchCoverageCommand,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.integration.phase2.b18_novelty_support import invoke, resolve_remaining

pytest_plugins = (
    "tests.integration.phase2.pr2_18_fixtures",
    "tests.integration.phase2.b18_novelty_support",
)


def fresh(e):
    engine = create_engine(e["engine"].url)
    sf = sessionmaker(engine, expire_on_commit=False, autoflush=False)
    return engine, NoveltyService(
        lambda: SqlAlchemyUnitOfWork(sf), e["credentials"], e["literature"]
    )


def test_saved_membership_restart_append_and_nested_replay(b18_env):
    e = b18_env
    before = e["saved"]["coverage"]
    assert before.material_version == 2 and before.quality.captured_unresolved_result_count == 1
    with e["engine"].connect() as conn:
        saved = conn.execute(
            text(
                "SELECT search_result_resolution_id,resolution_content_hash "
                "FROM search_coverage_resolutions WHERE search_coverage_id=:id"
            ),
            {"id": before.id},
        ).all()
    assert len(saved) == 1
    resolve_remaining(e)
    engine, service = fresh(e)
    try:
        for kind in ("coverage", "novelty"):
            for operation in ("read", "replay"):
                value = invoke(e, kind, operation, service=service)
                coverage = value if kind == "coverage" else value.search_coverage
                assert coverage.content_hash == before.content_hash
                assert coverage.quality.captured_unresolved_result_count == 1
                assert coverage.quality.current_unresolved_result_count == 0
        newer = service.record_search_coverage(
            e["author"], replace(e["commands"]["coverage"], id=uuid4())
        )
        assert newer.result_count == 2 and newer.resolved_source_count == 1
        assert newer.quality.captured_unresolved_result_count == 0
        assert newer.content_hash != before.content_hash
    finally:
        engine.dispose()


@pytest.mark.parametrize("mode", ["duplicate", "source_only", "conflicting"])
def test_all_rows_retained_without_winner(novelty_env, mode):
    from researchbase.application.source_version import (
        CreateSourceVersion,
        SourceVersionService,
        TransitionSourceVersion,
        _material_from_row,
    )
    from tests.integration.phase2.pr2_18_fixtures import add_resolution

    e = novelty_env
    add_resolution(e, e["results"][0])
    if mode == "duplicate":
        # The normal M2 writer forbids duplicate tuples. Exercise the verifier's
        # conservative all-row rule with independently hashed fixture history.
        with e["engine"].begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE search_result_resolutions DROP CONSTRAINT "
                    "search_result_resolutions_search_result_record_id_source_id_key"
                )
            )
    if mode == "conflicting":
        versions = SourceVersionService(e["factory"], e["credentials"])
        with e["factory"]() as uow:
            material = _material_from_row(
                uow.source_version, uow.source_version.version(e["source"])
            )
        created = versions.create(CreateSourceVersion(e["author"], e["project"], material, uuid4()))
        from uuid import UUID

        other = UUID(str(created["source_version_id"]))
        versions.freeze(TransitionSourceVersion(e["author"], e["project"], other, uuid4()))
        add_resolution(dict(e, source=other), e["results"][0])
    else:
        add_resolution(e, e["results"][0], version=mode == "duplicate")
    c = RecordSearchCoverageCommand(uuid4(), e["project"], e["plan"], e["executions"], "All rows")
    value = e["service"].record_search_coverage(e["author"], c)
    assert value.quality.captured_unresolved_result_count == (1 if mode == "duplicate" else 2)
    with e["engine"].connect() as conn:
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM search_coverage_resolutions WHERE search_coverage_id=:id"
                ),
                {"id": c.id},
            ).scalar_one()
            == 2
        )


def test_zero_and_empty_resolution_sets_restart(novelty_env):
    e = novelty_env
    for executions, count in [((e["executions"][1],), 0), (e["executions"], 2)]:
        c = RecordSearchCoverageCommand(
            uuid4(), e["project"], e["plan"], executions, "Exact empty history"
        )
        saved = e["service"].record_search_coverage(e["author"], c)
        engine, service = fresh(e)
        try:
            value = service.read_search_coverage(e["author"], ExactReadQuery(e["project"], c.id))
            assert value.material_version == 2
            assert value.quality.captured_unresolved_result_count == count
            assert value.content_hash == saved.content_hash
        finally:
            engine.dispose()


@pytest.mark.parametrize("target", ["hash", "missing", "count", "version"])
def test_corrupt_saved_capture_fails_closed(b18_env, target):
    e = b18_env
    c = e["commands"]["coverage"]
    with e["engine"].begin() as conn:
        conn.execute(text("SET LOCAL session_replication_role='replica'"))
        if target == "hash":
            conn.execute(
                text("UPDATE search_coverage_resolutions SET resolution_content_hash=:hash"),
                {"hash": "c" * 64},
            )
        elif target == "missing":
            conn.execute(text("DELETE FROM search_coverage_resolutions"))
        elif target == "count":
            conn.execute(text("UPDATE search_coverage SET captured_unresolved_result_count=0"))
        else:
            conn.execute(text("ALTER TABLE search_coverage DROP CONSTRAINT ck_b21_capture_version"))
            conn.execute(text("ALTER TABLE search_coverage DROP CONSTRAINT ck_b21_capture_count"))
            conn.execute(text("UPDATE search_coverage SET material_version=3"))
    with pytest.raises(ResearchBaseError) as error:
        invoke(e, "coverage", "read")
    assert error.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    e["credentials"].enabled = False
    with pytest.raises(ResearchBaseError) as error:
        invoke(e, "coverage", "read")
    assert error.value.code is ErrorCode.FORBIDDEN
    assert c.id == e["saved"]["coverage"].id


def test_membership_insert_failure_is_atomic(b18_env, monkeypatch):
    from researchbase.persistence.novelty_repository import SqlAlchemyNoveltyRepository

    e = b18_env
    original = SqlAlchemyNoveltyRepository.insert_child

    def failure(repo, kind, values):
        original(repo, kind, values)
        if kind == "coverage_resolution":
            raise RuntimeError("injected after membership")

    monkeypatch.setattr(SqlAlchemyNoveltyRepository, "insert_child", failure)
    c = replace(e["commands"]["coverage"], id=uuid4())
    with pytest.raises(RuntimeError):
        e["service"].record_search_coverage(e["author"], c)
    with e["engine"].connect() as conn:
        for table, column in [
            ("search_coverage", "id"),
            ("search_coverage_executions", "search_coverage_id"),
            ("search_coverage_resolutions", "search_coverage_id"),
        ]:
            assert (
                conn.execute(
                    text(f"SELECT count(*) FROM {table} WHERE {column}=:id"), {"id": c.id}
                ).scalar_one()
                == 0
            )
