"""Observed write coordination, lock-free reads and atomic screening sets."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import event, text

from researchbase.application.novelty import ExactReadQuery
from researchbase.persistence.novelty_repository import N, SqlAlchemyNoveltyRepository
from tests.integration.phase2.b20_screening_support import record, request
from tests.integration.phase2.test_pr2_18_concurrency import _witness


@pytest.mark.parametrize("replay", [False, True])
def test_first_statement_and_lock_free_exact_reads(novelty_env, replay):
    e = novelty_env
    c = request(e)
    if replay:
        record(e, c)
    statements = []
    transaction_modes = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)
        transaction_modes.append(
            (cursor.connection.isolation_level.name, cursor.connection.read_only)
        )

    event.listen(e["engine"], "before_cursor_execute", capture)
    try:
        record(e, c)
        expected_inventory = (
            "actor_subject_bindings,actors,artifact_versions,artifacts,audit_findings,"
            "claim_versions,claims,correction_records,datasets,experiment_spec_versions,"
            "experiment_specs,impact_assessments,impact_targets,literature_evidence,"
            "literature_evidence_review_events,literature_search_execution_events,"
            "literature_search_executions,literature_search_plan_versions,literature_search_plans,"
            "literature_search_provider_attempts,literature_source_project_links,literature_sources,"
            "metadata_observations,metric_definition_versions,metric_definitions,"
            "project_membership_events,project_memberships,project_role_assignments,projects,runs,"
            "scientific_conclusions,search_query_records,search_result_records,"
            "search_result_resolutions,source_versions"
        )
        assert N == tuple(expected_inventory.split(","))
        assert statements[0] == "LOCK TABLE " + expected_inventory + " IN SHARE MODE"
        assert {isolation for isolation, _ in transaction_modes} == {"READ_COMMITTED"}
        assert all(read_only is not True for _, read_only in transaction_modes)
        assert statements[1:3] == [
            "SET LOCAL lock_timeout='10s'",
            "SET LOCAL statement_timeout='30s'",
        ]
        assert "pg_advisory_xact_lock" in statements[3]
        assert "FOR UPDATE" in statements[4]
        statements.clear()
        transaction_modes.clear()
        e["service"].read_novelty_assessment(e["author"], ExactReadQuery(e["project"], c.id))
        assert set(transaction_modes) == {("REPEATABLE_READ", True)}
        assert not any(
            "LOCK TABLE" in x
            or "pg_advisory" in x
            or any(
                mode in x.upper()
                for mode in (
                    "FOR UPDATE",
                    "FOR SHARE",
                    "FOR KEY SHARE",
                    "FOR NO KEY UPDATE",
                )
            )
            for x in statements
        )
    finally:
        event.remove(e["engine"], "before_cursor_execute", capture)


def test_same_uuid_observed_wait_single_child_set(novelty_env, monkeypatch):
    e = novelty_env
    c = request(e)
    ready, release = Event(), Event()
    pids = []
    original = SqlAlchemyNoveltyRepository.insert

    def pause(repo, kind, values):
        result = original(repo, kind, values)
        if kind == "novelty":
            pids.append(repo._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            ready.set()
            assert release.wait(10)
        return result

    monkeypatch.setattr(SqlAlchemyNoveltyRepository, "insert", pause)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(record, e, c)
        assert ready.wait(10)
        second = pool.submit(record, e, c)
        try:
            _witness(e["race_engine"], pids[0])
        finally:
            release.set()
        assert first.result(timeout=10).content_hash == second.result(timeout=10).content_hash
    with e["engine"].connect() as conn:
        assert (
            conn.execute(text("SELECT count(*) FROM novelty_assessment_probes")).scalar_one() == 4
        )
        assert (
            conn.execute(
                text("SELECT count(*) FROM novelty_assessment_screening_results")
            ).scalar_one()
            == 2
        )


@pytest.mark.parametrize("stage", ["parent", "probe", "screen", "constraints"])
def test_failures_rollback_every_record(novelty_env, monkeypatch, stage):
    e = novelty_env
    c = request(e)
    method = (
        "insert"
        if stage == "parent"
        else "force_constraints"
        if stage == "constraints"
        else "insert_child"
    )
    original = getattr(SqlAlchemyNoveltyRepository, method)

    def fail(repo, *args):
        result = original(repo, *args)
        if stage in {"parent", "constraints"} or args[0] == "novelty_" + stage:
            raise RuntimeError("injected failure")
        return result

    monkeypatch.setattr(SqlAlchemyNoveltyRepository, method, fail)
    with pytest.raises(RuntimeError, match="injected failure"):
        record(e, replace(c, id=uuid4()))
    with e["engine"].connect() as conn:
        for table in (
            "novelty_assessments",
            "novelty_assessment_probes",
            "novelty_assessment_screening_results",
        ):
            assert conn.execute(text("SELECT count(*) FROM " + table)).scalar_one() == 0


@pytest.mark.parametrize("failure", ["40001", "40P01", "55P03", "57014", "business"])
def test_exact_retry_scope(novelty_env, monkeypatch, failure):
    import psycopg.errors
    from sqlalchemy.exc import DBAPIError

    from researchbase.foundation.errors import ErrorCode, ResearchBaseError

    e = novelty_env
    c = request(e)
    calls = []
    original = SqlAlchemyNoveltyRepository.insert_child

    def fail(repo, kind, values):
        if kind == "novelty_probe":
            calls.append(repo)
            if failure == "business":
                raise ResearchBaseError(ErrorCode.CONCURRENT_MODIFICATION, "business conflict")
            error = psycopg.errors.lookup(failure)("private SQL details")
            raise DBAPIError("private statement", {}, error, False)
        return original(repo, kind, values)

    monkeypatch.setattr(SqlAlchemyNoveltyRepository, "insert_child", fail)
    with pytest.raises((ResearchBaseError, RuntimeError)) as error:
        record(e, c)
    assert "private" not in str(error.value)
    assert len(calls) == len({id(x) for x in calls}) == (3 if failure in {"40001", "40P01"} else 1)


def test_unknown_commit_same_uuid_recovery(novelty_env, monkeypatch):
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    e = novelty_env
    c = request(e)
    calls = []
    original = SqlAlchemyUnitOfWork.commit

    def unknown(uow):
        original(uow)
        calls.append(uow)
        raise RuntimeError("Commit acknowledgement unavailable")

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", unknown)
    with pytest.raises(RuntimeError):
        record(e, c)
    assert len(calls) == 1
    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", original)
    assert record(e, c).id == c.id
    with e["engine"].connect() as conn:
        assert (
            conn.execute(text("SELECT count(*) FROM novelty_assessment_probes")).scalar_one() == 4
        )


@pytest.mark.parametrize("writer_first", [False, True])
def test_execution_insert_phantom_both_lock_orders(novelty_env, monkeypatch, writer_first):
    from researchbase.application.literature_search_execution import CreateLiteratureSearchExecution
    from researchbase.domain.novelty import NoveltyOutcome
    from researchbase.foundation.errors import ResearchBaseError
    from researchbase.persistence.literature_search_execution_repository import (
        SqlAlchemyLiteratureSearchExecutionRepository,
    )
    from tests.integration.phase2.b20_screening_support import successful_plan

    e, searches, _ = successful_plan(novelty_env)
    c = replace(request(e), assessment=NoveltyOutcome.NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE)
    ready, release = Event(), Event()
    pids = []
    target = (
        SqlAlchemyLiteratureSearchExecutionRepository
        if writer_first
        else SqlAlchemyNoveltyRepository
    )
    method = "save_receipt" if writer_first else "force_constraints"
    original = getattr(target, method)

    def pause(repo, *args):
        result = original(repo, *args)
        if writer_first:
            # Pause only after the complete execution write set is flushed.
            # Pausing create() left its CREATED event pending: the assessment
            # could SHARE-lock events, wait on executions, then deadlock the
            # writer's event flush. A retried writer no longer commits first.
            repo._session.flush()
            held = set(
                repo._session.execute(
                    text(
                        "SELECT relation::regclass::text FROM pg_locks "
                        "WHERE pid=pg_backend_pid() AND granted "
                        "AND mode='RowExclusiveLock'"
                    )
                ).scalars()
            )
            assert {"literature_search_executions", "literature_search_execution_events"} <= held
        pids.append(repo._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
        ready.set()
        assert release.wait(15)
        return result

    monkeypatch.setattr(target, method, pause)

    def insert():
        return searches.create(
            CreateLiteratureSearchExecution(
                e["project"],
                e["plan"],
                e["author"].actor_id,
                e["author"].deployment_id,
                uuid4(),
                "test",
                "v1",
                ("prior art",),
                principal=e["author"],
                max_provider_attempts=1,
            )
        )

    def assess():
        try:
            return record(e, c)
        except ResearchBaseError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(insert if writer_first else assess)
        assert ready.wait(15)
        second = pool.submit(assess if writer_first else insert)
        try:
            assert _witness(e["race_engine"], pids[0]) != pids[0]
        finally:
            release.set()
        a, b = first.result(timeout=15), second.result(timeout=15)
    assert len(pids) == 1, "the held transaction must commit without a retry reordering it"
    if writer_first:
        from researchbase.foundation.errors import ErrorCode

        assert b is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    else:
        read = e["service"].read_novelty_assessment(e["author"], ExactReadQuery(e["project"], c.id))
        from researchbase.application.novelty import NoveltyReadback

        assert isinstance(a, NoveltyReadback)
        assert read.content_hash == a.content_hash
        assert read.screening_validity.inventory_expanded
        assert not read.screening_validity.usable_for_current_judgment


@pytest.mark.parametrize("writer_first", [False, True])
@pytest.mark.parametrize("change", ["root", "correction", "resolution"])
def test_comparison_claim_and_resolution_insert_both_orders(
    novelty_env, monkeypatch, writer_first, change
):
    from researchbase.application.novelty import NoveltyReadback
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError
    from tests.integration.phase2.b20_screening_support import compared
    from tests.integration.phase2.pr2_18_fixtures import add_resolution

    e, c, rc, _ = compared(novelty_env)
    ready, release = Event(), Event()
    pids = []
    original_prepare = SqlAlchemyNoveltyRepository.prepare
    original_force = SqlAlchemyNoveltyRepository.force_constraints

    def pause(repo):
        pids.append(repo._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
        ready.set()
        assert release.wait(15)

    def prepare(repo, kind, *args):
        original_prepare(repo, kind, *args)
        if writer_first and kind == "prior_art":
            pause(repo)

    def force(repo):
        original_force(repo)
        if not writer_first:
            pause(repo)

    monkeypatch.setattr(SqlAlchemyNoveltyRepository, "prepare", prepare)
    monkeypatch.setattr(SqlAlchemyNoveltyRepository, "force_constraints", force)

    def mutate():
        if change == "resolution":
            with e["race_engine"].begin() as conn:
                add_resolution(e, e["results"][0], version=False, connection=conn)
                if writer_first:
                    pids.append(conn.execute(text("SELECT pg_backend_pid()")).scalar_one())
                    ready.set()
                    assert release.wait(15)
            return None
        return e["service"].record_prior_art_relation(
            e["author"],
            replace(
                rc,
                id=uuid4(),
                supersedes_prior_art_relation_id=rc.id if change == "correction" else None,
            ),
        )

    def assess():
        try:
            return record(e, c)
        except ResearchBaseError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(mutate if writer_first else assess)
        assert ready.wait(15)
        second = pool.submit(assess if writer_first else mutate)
        try:
            assert _witness(e["race_engine"], pids[0]) != pids[0]
        finally:
            release.set()
        a, b = first.result(timeout=15), second.result(timeout=15)
    if writer_first:
        assert b is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    else:
        assert isinstance(a, NoveltyReadback)
        read = e["service"].read_novelty_assessment(e["author"], ExactReadQuery(e["project"], c.id))
        assert read.content_hash == a.content_hash
        assert not read.screening_validity.usable_for_current_judgment


@pytest.mark.parametrize("credential_change", ["revocation", "expiry"])
def test_final_clock_after_observed_first_lock_wait(novelty_env, monkeypatch, credential_change):
    from datetime import UTC, datetime, timedelta

    from researchbase.domain.novelty import NoveltyOutcome
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError
    from tests.integration.phase2.b20_screening_support import successful_plan

    e, _, _ = successful_plan(novelty_env)
    c = replace(request(e), assessment=NoveltyOutcome.NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE)
    with e["race_engine"].begin() as blocker:
        blocker.execute(text("LOCK TABLE literature_search_executions IN ROW EXCLUSIVE MODE"))
        pid = blocker.execute(text("SELECT pg_backend_pid()")).scalar_one()
        with ThreadPoolExecutor(max_workers=1) as pool:

            def assess():
                try:
                    return record(e, c)
                except ResearchBaseError as exc:
                    return exc.code

            result = pool.submit(assess)
            try:
                assert _witness(e["race_engine"], pid) != pid
                if credential_change == "revocation":
                    e["credentials"].enabled = False
                else:
                    e["credentials"].expires_at = datetime.now(UTC) - timedelta(microseconds=1)
            finally:
                blocker.commit()
            assert result.result(timeout=15) is ErrorCode.FORBIDDEN


def test_screening_predecessor_has_one_successor(novelty_env, monkeypatch):
    from dataclasses import replace
    from uuid import uuid4

    from researchbase.foundation.errors import ErrorCode, ResearchBaseError

    e = novelty_env
    initial = request(e)
    parent = record(e, initial)
    first_command = replace(initial, id=uuid4(), supersedes_assessment_id=parent.id)
    second_command = replace(first_command, id=uuid4())
    ready, release = Event(), Event()
    pids = []
    original = SqlAlchemyNoveltyRepository.insert

    def pause(repo, kind, values):
        result = original(repo, kind, values)
        if kind == "novelty":
            pids.append(repo._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            ready.set()
            assert release.wait(10)
        return result

    monkeypatch.setattr(SqlAlchemyNoveltyRepository, "insert", pause)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(record, e, first_command)
        assert ready.wait(10)
        second = pool.submit(record, e, second_command)
        try:
            _witness(e["race_engine"], pids[0])
        finally:
            release.set()
        assert first.result(timeout=10).supersedes_assessment.id == parent.id
        with pytest.raises(ResearchBaseError) as error:
            second.result(timeout=10)
        assert error.value.code is ErrorCode.INVALID_STATE_TRANSITION
    with e["engine"].connect() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM novelty_assessments WHERE supersedes_assessment_id=:id"),
                {"id": parent.id},
            ).scalar_one()
            == 1
        )
