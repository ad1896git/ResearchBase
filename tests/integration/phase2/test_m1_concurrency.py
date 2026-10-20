"""M1 disjoint editing locks witnessed on actual PostgreSQL backends."""

from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
from sqlalchemy import text

from researchbase.persistence.manuscript_freeze_repository import M1_EDIT_SQL, M1_SHARE_SQL
from tests.integration.phase2.test_b05_manuscript_review import (
    b04_env,
    b05_env,
    conclusion_env,
    phase2_database_url,
)
from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker

pytestmark = pytest.mark.integration
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
_FIXTURES = (b04_env, b05_env, conclusion_env, phase2_database_url)


def test_successor_placements_and_freeze_keep_disjoint_first_locks(b05_env):
    """Routing initial writers to legacy locks must retain §12.2 for successors."""
    from dataclasses import replace
    from uuid import uuid4

    from researchbase.application.manuscript_placement import (
        ArtifactPlacementService,
        CitationPlacementService,
        ClaimPlacementService,
    )
    from tests.integration.phase2.pr2_20_support import capture
    from tests.integration.phase2.test_b04_manuscript_freeze import freeze
    from tests.integration.phase2.test_m1_manuscript_revision import seal, successor

    env = b05_env
    seal(env)
    _, _, draft = successor(env)
    _, q, author, _, factory, engine, manuscripts, store, claim, credentials, base = env
    common = (author, q.project_id, q.publication_id, draft.id)
    location = {"kind": "PARAGRAPH", "value": "p1"}
    with engine.connect() as conn:
        document = conn.execute(
            text("SELECT document_artifact_version_id FROM manuscript_versions WHERE id=:id"),
            {"id": draft.id},
        ).scalar_one()

    def assert_writer(observed):
        writers = [tx for tx in observed.transactions if M1_SHARE_SQL in tx]
        assert len(writers) == 1
        assert writers[0][:2] == [M1_SHARE_SQL, M1_EDIT_SQL]

    with capture(engine) as observed:
        CitationPlacementService(factory, credentials, store).add(
            *common, base[7], "INTRO", location, "BACKGROUND", 0, uuid4()
        )
    assert_writer(observed)
    with capture(engine) as observed:
        ClaimPlacementService(factory, credentials, store).add(
            *common, claim, None, "RESULTS", location, "SUPPORTED", 0, uuid4()
        )
    assert_writer(observed)
    with capture(engine) as observed:
        ArtifactPlacementService(factory, credentials, store).add(
            *common, document, "APPENDIX", location, "OTHER", 0, uuid4()
        )
    assert_writer(observed)
    # The fixture's freeze service owns the original B04 engine.
    with capture(base[8]) as observed:
        frozen = freeze(manuscripts, author, replace(q, manuscript_version_id=draft.id))
    assert_writer(observed)
    assert frozen.version_number == 2


@pytest.mark.parametrize("first", [0, 1])
def test_s1_two_writer_table_lock_order(b05_env, first):
    engine = b05_env[5]
    connections = [engine.connect(), engine.connect()]
    try:
        holder, waiter = connections[first], connections[1 - first]
        # Application first-statement inventory, both writers at READ COMMITTED.
        holder.execute(text(M1_SHARE_SQL))
        waiter.execute(text(M1_SHARE_SQL))
        holder.execute(text(M1_EDIT_SQL))
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()

        def finish():
            waiter.execute(text(M1_EDIT_SQL))
            waiter.commit()

        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(finish)
            try:
                witness = _wait_for_pg_blocker(engine, pid, "relation")
                assert witness["mode"] == "ExclusiveLock"
                assert witness["relation"] == "manuscript_artifact_placements"
                with engine.connect() as observer:
                    assert (
                        observer.execute(
                            text(
                                "SELECT count(*) FROM pg_locks WHERE pid=:pid "
                                "AND locktype IN ('advisory','tuple')"
                            ),
                            {"pid": witness["pid"]},
                        ).scalar_one()
                        == 0
                    )
            finally:
                holder.commit()
            pending.result(timeout=10)
    finally:
        for conn in connections:
            conn.close()


@pytest.mark.parametrize("release_with_expired_credential", [False, True])
def test_successor_post_wait_credentials_are_fresh_and_atomic(
    b05_env, monkeypatch, release_with_expired_credential
):
    from time import sleep
    from uuid import uuid4

    from researchbase.application.publication import PublicationService
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError
    from tests.integration.phase2.test_b05_manuscript_review import seal
    from tests.integration.phase2.test_pr2_10_binding_contract import _artifact

    env = b05_env
    seal(env)
    _, q, author, _, factory, engine, _, store, _, credentials, _ = env
    document = _artifact(
        factory, store, author, q.project_id, b"Next frozen document", "manuscript"
    )
    service = PublicationService(factory, credentials, store)
    seen = []
    with engine.connect() as holder:
        holder.execute(text("LOCK TABLE publications IN EXCLUSIVE MODE"))
        holder_pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        expires = holder.execute(text("SELECT clock_timestamp()+interval '1 second'")).scalar_one()
        original = credentials.is_valid

        def valid(principal, at):
            seen.append(at)
            return original(principal, at) and (not release_with_expired_credential or at < expires)

        monkeypatch.setattr(credentials, "is_valid", valid)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                service.create_draft,
                author,
                q.project_id,
                q.publication_id,
                document,
                "Next",
                None,
                "EDITORIAL",
                uuid4(),
            )
            try:
                witness = _wait_for_pg_blocker(engine, holder_pid, "relation")
                assert witness["relation"] == "publications"
                with engine.connect() as observer:
                    started = observer.execute(
                        text("SELECT xact_start FROM pg_stat_activity WHERE pid=:pid"),
                        {"pid": witness["pid"]},
                    ).scalar_one()
                    assert started < expires
                    if release_with_expired_credential:
                        now = observer.execute(text("SELECT clock_timestamp()")).scalar_one()
                        sleep(max(0, (expires - now).total_seconds()) + 0.02)
            finally:
                holder.commit()
            if release_with_expired_credential:
                with pytest.raises(ResearchBaseError) as caught:
                    future.result(timeout=10)
                assert caught.value.code == ErrorCode.FORBIDDEN
                assert seen[-1] >= expires
            else:
                assert future.result(timeout=10).version_number == 2
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM manuscript_versions")).scalar_one() == (
            1 if release_with_expired_credential else 2
        )


@pytest.mark.parametrize("kind", ["citation", "claim", "artifact"])
def test_placement_replay_race_survives_freeze_between_lookup_and_writer(
    b05_env, monkeypatch, kind
):
    from threading import Event, current_thread
    from uuid import uuid4

    from researchbase.application import manuscript_placement as placement
    from tests.integration.phase2.test_b05_manuscript_review import seal

    env = b05_env
    _, q, author, _, factory, engine, _, store, claim, credentials, base = env
    with engine.connect() as conn:
        document = conn.execute(
            text("SELECT document_artifact_version_id FROM manuscript_versions WHERE id=:id"),
            {"id": q.manuscript_version_id},
        ).scalar_one()
    service: Any
    args: tuple[Any, ...]
    common = (author, q.project_id, q.publication_id, q.manuscript_version_id)
    if kind == "citation":
        service = placement.CitationPlacementService(factory, credentials, store)
        args = (
            *common,
            base[7],
            "INTRO",
            {"kind": "PARAGRAPH", "value": "p1"},
            "BACKGROUND",
            0,
            uuid4(),
        )
    elif kind == "claim":
        service = placement.ClaimPlacementService(factory, credentials, store)
        args = (
            *common,
            claim,
            None,
            "RESULTS",
            {"kind": "PARAGRAPH", "value": "p1"},
            "SUPPORTED",
            0,
            uuid4(),
        )
    else:
        service = placement.ArtifactPlacementService(factory, credentials, store)
        args = (
            *common,
            document,
            "APPENDIX",
            {"kind": "ANCHOR", "value": "doc"},
            "OTHER",
            0,
            uuid4(),
        )
    entered, release = Event(), Event()
    original = placement._placement_replay

    def pause(*args, **kwargs):
        result = original(*args, **kwargs)
        if current_thread().name.startswith("m1-replay-race") and not entered.is_set():
            assert result == (None, False)
            entered.set()
            assert release.wait(10)
        return result

    monkeypatch.setattr(placement, "_placement_replay", pause)
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="m1-replay-race") as pool:
        pending = pool.submit(service.add, *args)
        try:
            assert entered.wait(10)
            saved = service.add(*args)
            seal(env)
        finally:
            release.set()
        assert pending.result(timeout=10) == saved
    assert service.trace(*common) == (saved,)


@pytest.mark.parametrize("same_request", [False, True])
def test_competing_successor_drafts_serialize_without_partial_history(
    b05_env, monkeypatch, same_request
):
    from threading import Event, current_thread
    from uuid import uuid4

    from researchbase.application.publication import PublicationService
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError
    from researchbase.persistence.manuscript_freeze_repository import (
        SqlAlchemyManuscriptFreezeRepository,
    )
    from tests.integration.phase2.test_b05_manuscript_review import seal
    from tests.integration.phase2.test_pr2_10_binding_contract import _artifact

    seal(b05_env)
    _, q, author, _, factory, engine, _, store, _, credentials, _ = b05_env
    document = _artifact(factory, store, author, q.project_id, b"Successor race", "manuscript")
    service = PublicationService(factory, credentials, store)
    entered, release = Event(), Event()
    holder_pid = []
    original = SqlAlchemyManuscriptFreezeRepository.prepare_revision_write

    def prepare(repo):
        original(repo)
        if current_thread().name.startswith("m1-draft-holder"):
            holder_pid.append(repo._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            entered.set()
            assert release.wait(10)

    monkeypatch.setattr(SqlAlchemyManuscriptFreezeRepository, "prepare_revision_write", prepare)
    request = uuid4()
    args = (author, q.project_id, q.publication_id, document, "Next", None, "EDITORIAL")
    with (
        ThreadPoolExecutor(max_workers=1, thread_name_prefix="m1-draft-holder") as first,
        ThreadPoolExecutor(max_workers=1) as second,
    ):
        winner = first.submit(service.create_draft, *args, request)
        try:
            assert entered.wait(10)
            loser = second.submit(service.create_draft, *args, request if same_request else uuid4())
            witness = _wait_for_pg_blocker(engine, holder_pid[0], "relation")
            assert witness["mode"] == "ExclusiveLock"
            assert witness["relation"] == "manuscript_artifact_placements"
        finally:
            release.set()
        saved = winner.result(timeout=10)
        if same_request:
            assert loser.result(timeout=10) == saved
        else:
            with pytest.raises(ResearchBaseError) as caught:
                loser.result(timeout=10)
            assert caught.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    with engine.connect() as conn:
        assert conn.execute(
            text(
                "SELECT array_agg(version_number ORDER BY version_number) FROM manuscript_versions"
            )
        ).scalar_one() == [1, 2]
    assert service.create_draft(*args, request) == saved


@pytest.mark.parametrize("repository", ["decision", "internal_review"])
@pytest.mark.parametrize("configured", [False, True])
def test_repository_snapshot_keeps_actual_read_committed_without_ignored_options(
    b05_env, repository, configured
):
    import warnings

    from sqlalchemy.exc import SAWarning

    factory = b05_env[4]
    with factory() as uow, warnings.catch_warnings():
        warnings.simplefilter("error", SAWarning)
        if configured:
            uow.configure_revision_transaction()
        if repository == "decision":
            uow.decision.lock_snapshot()
        else:
            uow.internal_review.prepare_write()
        assert (
            uow._session.execute(text("SHOW transaction_isolation")).scalar_one()
            == "read committed"
        )
        assert uow._session.execute(text("SHOW transaction_read_only")).scalar_one() == "off"
