"""Observable PostgreSQL waits and fail-closed stale-snapshot capture."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from researchbase.application.novelty import RecordSearchCoverageCommand
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.novelty_repository import N


def _witness(engine, writer_pid, before=None):
    deadline = monotonic() + 10
    while monotonic() < deadline:
        with engine.connect() as observer:
            row = observer.execute(
                text("""SELECT pid,xact_start,clock_timestamp() AS observed_at FROM pg_stat_activity
                    WHERE :writer=ANY(pg_blocking_pids(pid))"""),
                {"writer": writer_pid},
            ).first()
            if row:
                assert row.pid != writer_pid
                if before is not None:
                    assert row.xact_start < before and row.observed_at < before
                    print(
                        "PR218_EXPIRY_WAIT",
                        {
                            "writer_pid": writer_pid,
                            "waiter_pid": row.pid,
                            "transaction_started_at": row.xact_start.isoformat(),
                            "wait_observed_at": row.observed_at.isoformat(),
                            "expiry": before.isoformat(),
                        },
                    )
                return row.pid
        Event().wait(0.01)
    pytest.fail("no PostgreSQL lock witness")


@pytest.mark.parametrize("kind", ["coverage", "prior_art", "novelty"])
def test_exact_read_does_not_block_unrelated_insert(novelty_env, monkeypatch, kind):
    from researchbase.application.novelty import (
        ExactReadQuery,
        RecordNoveltyAssessmentCommand,
        RecordPriorArtRelationCommand,
    )
    from researchbase.domain.novelty import NoveltyOutcome, PriorArtKind
    from researchbase.persistence.novelty_repository import SqlAlchemyNoveltyRepository

    e = novelty_env
    row = e["service"].record_search_coverage(
        e["author"],
        RecordSearchCoverageCommand(
            uuid4(), e["project"], e["plan"], e["executions"], "Selected scope."
        ),
    )
    if kind == "prior_art":
        row = e["service"].record_prior_art_relation(
            e["author"],
            RecordPriorArtRelationCommand(
                uuid4(),
                e["project"],
                e["claim"],
                e["source"],
                PriorArtKind.RELATED,
                "Comparison.",
                (e["evidence"],),
            ),
        )
    elif kind == "novelty":
        row = e["service"].record_novelty_assessment(
            e["author"],
            RecordNoveltyAssessmentCommand(
                uuid4(),
                e["project"],
                e["claim"],
                row.id,
                NoveltyOutcome.INCONCLUSIVE,
                "Limited coverage.",
            ),
        )
    ready, release = Event(), Event()
    reader_pids = []
    actor = uuid4()
    original = SqlAlchemyNoveltyRepository.parent

    def pause_after_parent(repo, record_kind, identity):
        result = original(repo, record_kind, identity)
        if record_kind == kind and identity == row.id:
            assert repo._session.execute(text("SHOW transaction_isolation")).scalar_one() == (
                "repeatable read"
            )
            reader_pids.append(repo._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            ready.set()
            assert release.wait(10)
            # The committed insert stays outside this read's original snapshot.
            assert repo.one("SELECT id FROM actors WHERE id=:id", {"id": actor}) is None
        return result

    monkeypatch.setattr(SqlAlchemyNoveltyRepository, "parent", pause_after_parent)
    read_method = {
        "coverage": e["service"].read_search_coverage,
        "prior_art": e["service"].read_prior_art_relation,
        "novelty": e["service"].read_novelty_assessment,
    }[kind]
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(read_method, e["author"], ExactReadQuery(e["project"], row.id))
        try:
            assert ready.wait(10)
            with e["race_engine"].begin() as writer:
                assert (
                    writer.execute(text("SELECT pg_backend_pid()")).scalar_one() != reader_pids[0]
                )
                writer.execute(text("SET LOCAL lock_timeout='1s'"))
                writer.execute(
                    text("""INSERT INTO actors (id,actor_type,display_name,created_at)
                        VALUES (:id,'HUMAN','Unrelated actor',clock_timestamp())"""),
                    {"id": actor},
                )
            with e["race_engine"].connect() as observer:
                assert (
                    observer.execute(
                        text("SELECT id FROM actors WHERE id=:id"), {"id": actor}
                    ).scalar_one()
                    == actor
                )
            assert not future.done()  # The read transaction is still open after commit.
        finally:
            release.set()
        assert future.result(timeout=10).content_hash == row.content_hash


def test_stale_serializable_capture_fails_closed(novelty_env):
    e = novelty_env
    with (
        e["race_engine"].connect() as writer,
        e["engine"].connect().execution_options(isolation_level="SERIALIZABLE") as capture,
    ):
        writer.execute(
            text("UPDATE actors SET retired_at=clock_timestamp() WHERE id=:id"),
            {"id": e["author"].actor_id},
        )
        capture.execute(
            text("SELECT retired_at FROM actors WHERE id=:id"), {"id": e["author"].actor_id}
        )

        def stale_capture():
            try:
                capture.execute(text("LOCK TABLE " + ",".join(N) + " IN SHARE MODE"))
                capture.execute(
                    text(
                        """INSERT INTO search_coverage
                            (id,created_at,created_by,search_plan_version_id,providers,query_count,
                             result_count,resolved_source_count,time_scope,coverage_limitations,
                             content_hash,hash_scheme,material_version,
                             captured_unresolved_result_count)
                            VALUES(:id,clock_timestamp(),:actor,:plan,'[]',0,0,0,NULL,
                                   'Stale capture',:hash,'sha256-cjson-v1',2,0)"""
                    ),
                    {
                        "id": uuid4(),
                        "actor": e["author"].actor_id,
                        "plan": e["plan"],
                        "hash": "a" * 64,
                    },
                )
                capture.commit()
            except DBAPIError as error:
                capture.rollback()
                return getattr(error.orig, "sqlstate", None)
            pytest.fail("stale serializable insert admitted")

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(stale_capture)
            pid = writer.execute(text("SELECT pg_backend_pid()")).scalar_one()
            _witness(e["engine"], pid)
            writer.commit()
            assert future.result(timeout=10) == "P17D3"
    with e["engine"].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM search_coverage")).scalar_one() == 0


def test_read_committed_capture_rechecks_after_revocation_wait(novelty_env):
    e = novelty_env
    c = RecordSearchCoverageCommand(
        uuid4(), e["project"], e["plan"], e["executions"], "Selected scope."
    )
    with e["race_engine"].connect() as writer:
        writer.execute(
            text("UPDATE actors SET retired_at=clock_timestamp() WHERE id=:id"),
            {"id": e["author"].actor_id},
        )

        def capture():
            with pytest.raises(ResearchBaseError) as error:
                e["service"].record_search_coverage(e["author"], c)
            return error.value.code

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(capture)
            _witness(e["engine"], writer.execute(text("SELECT pg_backend_pid()")).scalar_one())
            writer.commit()
            assert future.result(timeout=10) is ErrorCode.FORBIDDEN


def test_same_uuid_single_parent(novelty_env):
    e = novelty_env
    c = RecordSearchCoverageCommand(
        uuid4(), e["project"], e["plan"], e["executions"], "Selected scope."
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(e["service"].record_search_coverage, e["author"], c) for _ in range(2)
        ]
        rows = [f.result(timeout=15) for f in futures]
    assert rows[0].content_hash == rows[1].content_hash
    with e["engine"].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM search_coverage")).scalar_one() == 1
        assert (
            conn.execute(text("SELECT count(*) FROM search_coverage_executions")).scalar_one() == 2
        )


@pytest.mark.parametrize("capture_first", [False, True])
def test_resolution_insert_capture_orderings(novelty_env, monkeypatch, capture_first):
    from researchbase.persistence.novelty_repository import SqlAlchemyNoveltyRepository
    from tests.integration.phase2.pr2_18_fixtures import add_resolution

    e = novelty_env
    c = RecordSearchCoverageCommand(
        uuid4(), e["project"], e["plan"], e["executions"], "Selected scope."
    )
    if not capture_first:
        with e["race_engine"].connect() as holder:
            pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
            add_resolution(e, e["results"][0], connection=holder)
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(e["service"].record_search_coverage, e["author"], c)
                try:
                    _witness(e["engine"], pid)
                finally:
                    holder.commit()
                assert future.result(timeout=10).resolved_source_count == 1
    else:
        ready = Event()
        release = Event()
        pids = []
        original = SqlAlchemyNoveltyRepository.force_constraints

        def pause(repo):
            original(repo)
            pids.append(repo._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            ready.set()
            assert release.wait(10)

        monkeypatch.setattr(SqlAlchemyNoveltyRepository, "force_constraints", pause)
        with ThreadPoolExecutor(max_workers=2) as pool:
            capture = pool.submit(e["service"].record_search_coverage, e["author"], c)
            assert ready.wait(10)
            resolution = pool.submit(add_resolution, e, e["results"][0])
            try:
                _witness(e["engine"], pids[0])
            finally:
                release.set()
            assert capture.result(timeout=10).resolved_source_count == 0
            resolution.result(timeout=10)


@pytest.mark.parametrize("state", ["40001", "40P01"])
def test_exactly_three_fresh_uow_retries(novelty_env, monkeypatch, state):
    import psycopg
    from sqlalchemy.exc import OperationalError

    from researchbase.persistence.novelty_repository import SqlAlchemyNoveltyRepository

    e = novelty_env
    calls = []

    def fail_insert(repo, *args):
        calls.append(repo)
        error = (
            psycopg.errors.SerializationFailure("injected")
            if state == "40001"
            else psycopg.errors.DeadlockDetected("injected")
        )
        raise OperationalError("injected", {}, error)

    monkeypatch.setattr(SqlAlchemyNoveltyRepository, "insert", fail_insert)
    c = RecordSearchCoverageCommand(
        uuid4(), e["project"], e["plan"], e["executions"], "Selected scope."
    )
    with pytest.raises(ResearchBaseError) as error:
        e["service"].record_search_coverage(e["author"], c)
    assert error.value.code is ErrorCode.CONCURRENT_MODIFICATION
    assert len(calls) == 3 and len({id(x) for x in calls}) == 3
    assert error.value.details is None


@pytest.mark.parametrize("stage", ["insert_child", "force_constraints"])
def test_mid_write_failure_rolls_back_parent_and_children(novelty_env, monkeypatch, stage):
    from researchbase.persistence.novelty_repository import SqlAlchemyNoveltyRepository

    e = novelty_env

    def injected(*args):
        raise RuntimeError("injected failure")

    monkeypatch.setattr(SqlAlchemyNoveltyRepository, stage, injected)
    c = RecordSearchCoverageCommand(
        uuid4(), e["project"], e["plan"], e["executions"], "Selected scope."
    )
    with pytest.raises(RuntimeError):
        e["service"].record_search_coverage(e["author"], c)
    with e["engine"].connect() as conn:
        for table in ("search_coverage", "search_coverage_executions"):
            assert conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0


@pytest.mark.parametrize("kind", ["coverage", "prior_art", "novelty"])
@pytest.mark.parametrize("wait_stage", ["request", "foreign_key"])
@pytest.mark.parametrize("authority", ["credential", "role"])
def test_expiry_across_required_database_wait(
    novelty_env, monkeypatch, kind, wait_stage, authority
):
    from researchbase.application.novelty import (
        RecordNoveltyAssessmentCommand,
        RecordPriorArtRelationCommand,
    )
    from researchbase.domain.novelty import NoveltyOutcome, PriorArtKind

    e = novelty_env
    principal = e["author"] if authority == "credential" else e["researcher"]
    cov = (
        e["service"].record_search_coverage(
            e["author"],
            RecordSearchCoverageCommand(
                uuid4(), e["project"], e["plan"], e["executions"], "Selected scope."
            ),
        )
        if kind == "novelty"
        else None
    )
    c = {
        "coverage": lambda: RecordSearchCoverageCommand(
            uuid4(), e["project"], e["plan"], e["executions"], "Scope."
        ),
        "prior_art": lambda: RecordPriorArtRelationCommand(
            uuid4(),
            e["project"],
            e["claim"],
            e["source"],
            PriorArtKind.RELATED,
            "Comparison.",
            (e["evidence"],),
        ),
        "novelty": lambda: RecordNoveltyAssessmentCommand(
            uuid4(),
            e["project"],
            e["claim"],
            cov.id if cov else uuid4(),
            NoveltyOutcome.INCONCLUSIVE,
            "Limited.",
        ),
    }[kind]()
    method = {
        "coverage": "record_search_coverage",
        "prior_art": "record_prior_art_relation",
        "novelty": "record_novelty_assessment",
    }[kind]
    from researchbase.persistence.novelty_repository import SqlAlchemyNoveltyRepository

    samples = []
    original_at = SqlAlchemyNoveltyRepository.at

    def capture_clock(repo):
        value = original_at(repo)
        samples.append(value)
        return value

    monkeypatch.setattr(SqlAlchemyNoveltyRepository, "at", capture_clock)
    with e["engine"].begin() as conn:
        deadline = conn.execute(text("SELECT clock_timestamp()+interval '1 second'")).scalar_one()
        if authority == "role":
            role = conn.execute(
                text(
                    """UPDATE project_role_assignments SET effective_until=:until,
                    row_version=row_version+1 WHERE actor_id=:actor
                    AND role='RESEARCHER' RETURNING id"""
                ),
                {"until": deadline, "actor": principal.actor_id},
            ).scalar_one()
            conn.execute(
                text("""INSERT INTO project_role_events
                (id,role_assignment_id,actor_id,event_kind,occurred_at,reason,request_id)
                VALUES(:id,:role,:actor,'CLOSED',:until,'Scheduled test expiry',:request)"""),
                {
                    "id": uuid4(),
                    "role": role,
                    "actor": principal.actor_id,
                    "until": deadline,
                    "request": uuid4(),
                },
            )
        else:
            e["credentials"].expires_at = deadline

    def operation():
        with pytest.raises(ResearchBaseError) as error:
            getattr(e["service"], method)(principal, c)
        assert error.value.code is ErrorCode.FORBIDDEN

    with e["race_engine"].connect() as holder:
        if wait_stage == "request":
            holder.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                {"key": f"pr218:{kind}:{c.id}"},
            )
        else:
            holder.execute(
                text("SELECT id FROM actors WHERE id=:id FOR UPDATE"), {"id": principal.actor_id}
            )
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(operation)
            try:
                _witness(e["engine"], pid, before=deadline)
                with e["engine"].connect() as observer:
                    while (
                        observer.execute(text("SELECT clock_timestamp()")).scalar_one() <= deadline
                    ):
                        Event().wait(0.01)
            finally:
                holder.commit()
            future.result(timeout=10)
            assert samples and max(samples) >= deadline
            print("PR218_FINAL_AUTH_CLOCK", max(samples).isoformat())
    with e["engine"].connect() as conn:
        table = {
            "coverage": "search_coverage",
            "prior_art": "prior_art_relations",
            "novelty": "novelty_assessments",
        }[kind]
        assert (
            conn.execute(
                text(f"SELECT count(*) FROM {table} WHERE id=:id"), {"id": c.id}
            ).scalar_one()
            == 0
        )


def test_evidence_dispute_during_table_wait_denies_comparison(novelty_env):
    from researchbase.application.novelty import RecordPriorArtRelationCommand
    from researchbase.domain.novelty import PriorArtKind

    e = novelty_env
    c = RecordPriorArtRelationCommand(
        uuid4(),
        e["project"],
        e["claim"],
        e["source"],
        PriorArtKind.RELATED,
        "Comparison.",
        (e["evidence"],),
    )
    with e["race_engine"].connect() as holder:
        holder.execute(
            text("""INSERT INTO literature_evidence_review_events
            (id,literature_evidence_id,prior_status,new_status,reviewed_by,reviewed_at,basis)
            VALUES(:id,:evidence,'VERIFIED','DISPUTED',:actor,clock_timestamp(),'New concern')"""),
            {"id": uuid4(), "evidence": e["evidence"], "actor": e["reviewer"].actor_id},
        )
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()

        def compare():
            with pytest.raises(ResearchBaseError) as error:
                e["service"].record_prior_art_relation(e["author"], c)
            return error.value.code

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(compare)
            try:
                _witness(e["engine"], pid)
            finally:
                holder.commit()
            assert future.result(timeout=10) is ErrorCode.INVALID_STATE_TRANSITION
