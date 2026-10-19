"""B04 observed lock ordering, replay serialization, and nonblocking exact reads."""

# SQL assertions preserve the literal contract.
# ruff: noqa: E501

from concurrent.futures import ThreadPoolExecutor
from threading import Event, current_thread
from uuid import uuid4

import pytest
from sqlalchemy import event, text

from researchbase.application.manuscript_freeze import FreezeManuscriptCommand
from researchbase.application.manuscript_placement import (
    ArtifactPlacementService,
    CitationPlacementService,
    ClaimPlacementService,
)
from researchbase.application.manuscript_scientific_trace import ManuscriptScientificTraceService
from researchbase.foundation.errors import ResearchBaseError
from researchbase.persistence.manuscript_freeze_repository import (
    B04_SHARE_SQL,
    SqlAlchemyManuscriptFreezeRepository,
)
from tests.integration.phase2.test_b04_manuscript_freeze import b04_env as _b04_env
from tests.integration.phase2.test_b04_manuscript_freeze import freeze
from tests.integration.phase2.test_pr2_11_r2_persistence import conclusion_env as _conclusion_env
from tests.integration.phase2.test_pr2_11_r2_persistence import (
    phase2_database_url as _phase2_database_url,
)

conclusion_env = _conclusion_env
phase2_database_url = _phase2_database_url
b04_env = _b04_env

pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
pytestmark = pytest.mark.integration


@pytest.mark.parametrize("state", ["DRAFT", "FROZEN"])
@pytest.mark.parametrize("kind", ["exact", "citation", "claim", "artifact", "combined"])
def test_exact_reads_do_not_block_unrelated_insert(b04_env, kind, state, monkeypatch):
    service, q, actor, factory, engine, credentials, store, claim, base = b04_env
    ClaimPlacementService(factory, credentials).add(
        actor,
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        claim,
        None,
        "RESULTS",
        {"kind": "PARAGRAPH", "value": "p1"},
        "SUPPORTED",
        0,
        uuid4(),
    )
    CitationPlacementService(factory, credentials).add(
        actor,
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        base[7],
        "INTRO",
        {"kind": "PARAGRAPH", "value": "p1"},
        "BACKGROUND",
        0,
        uuid4(),
    )
    preview = service.get_manuscript_version(actor, q)
    ArtifactPlacementService(factory, credentials).add(
        actor,
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        preview.document_artifact_version_id,
        "APPENDIX",
        {"kind": "ANCHOR", "value": "doc"},
        "OTHER",
        0,
        uuid4(),
    )
    expected = (
        freeze(service, actor, q) if state == "FROZEN" else service.get_manuscript_version(actor, q)
    )
    entered, release = Event(), Event()
    thread_id = []
    original = SqlAlchemyManuscriptFreezeRepository.authority
    observed = []
    phantom = uuid4()

    def authority(self, *args):
        rows = original(self, *args)
        if current_thread().name.startswith("b04-reader") and not entered.is_set():
            assert (
                self._session.execute(text("SHOW transaction_isolation")).scalar_one()
                == "repeatable read"
            )
            assert self._session.execute(text("SHOW transaction_read_only")).scalar_one() == "on"
            pid = self._session.execute(text("SELECT pg_backend_pid()")).scalar_one()
            thread_id.append(pid)
            locks = self._session.execute(
                text(
                    "SELECT mode,locktype FROM pg_locks WHERE pid=pg_backend_pid() AND (locktype='advisory' OR mode IN ('ShareLock','RowShareLock','RowExclusiveLock'))"
                )
            ).all()
            assert locks == []
            entered.set()
            assert release.wait(10)
            assert (
                self._session.execute(
                    text("SELECT count(*) FROM actors WHERE id=:id"), {"id": phantom}
                ).scalar_one()
                == 0
            )
        return rows

    monkeypatch.setattr(SqlAlchemyManuscriptFreezeRepository, "authority", authority)
    operations = {
        "exact": lambda: service.get_manuscript_version(actor, q),
        "citation": lambda: CitationPlacementService(factory, credentials, store).trace(
            actor, q.project_id, q.publication_id, q.manuscript_version_id
        ),
        "claim": lambda: ClaimPlacementService(factory, credentials, store).trace(
            actor, q.project_id, q.publication_id, q.manuscript_version_id
        ),
        "artifact": lambda: ArtifactPlacementService(factory, credentials, store).trace(
            actor, q.project_id, q.publication_id, q.manuscript_version_id
        ),
        "combined": lambda: ManuscriptScientificTraceService(factory, credentials, store).trace(
            actor, q.project_id, q.publication_id, q.manuscript_version_id
        ),
    }
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="b04-reader") as pool:
        future = pool.submit(operations[kind])
        try:
            assert entered.wait(10)
            with engine.begin() as conn:
                conn.execute(text("SET LOCAL lock_timeout='2s'"))
                conn.execute(
                    text(
                        "INSERT INTO actors (id,actor_type,display_name,created_at,row_version) VALUES (:id,'HUMAN','Unrelated reader witness',clock_timestamp(),1)"
                    ),
                    {"id": phantom},
                )
            observed.append("writer committed before reader released")
        finally:
            release.set()
        result = future.result(timeout=10)
    assert observed and thread_id
    if kind == "exact":
        assert result == expected
        assert result.status == state


def test_concurrent_freezes_first_sql_and_stable_replay(b04_env):
    service, q, actor, _, engine, *_ = b04_env
    preview = service.get_manuscript_version(actor, q)
    cmd = FreezeManuscriptCommand(
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        preview.preview_placement_set_hash,
        preview.preview_content_hash,
    )
    emitted = {}

    def before(conn, cursor, statement, parameters, context, executemany):
        if current_thread().name.startswith("b04-freeze"):
            emitted.setdefault(current_thread().name, []).append(statement)

    event.listen(engine, "before_cursor_execute", before)
    try:
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="b04-freeze") as pool:
            futures = [pool.submit(service.freeze_manuscript_version, actor, cmd) for _ in range(2)]
            results = [f.result(timeout=20) for f in futures]
    finally:
        event.remove(engine, "before_cursor_execute", before)
    assert results[0] == results[1]
    assert len(emitted) == 2
    assert all(statements[0] == B04_SHARE_SQL for statements in emitted.values())


def test_freeze_blocks_placement_writer_then_rechecks_frozen(b04_env, monkeypatch):
    service, q, actor, factory, engine, credentials, store, claim, _ = b04_env
    preview = service.get_manuscript_version(actor, q)
    cmd = FreezeManuscriptCommand(
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        preview.preview_placement_set_hash,
        preview.preview_content_hash,
    )
    entered, release = Event(), Event()
    original = store.verify
    freezer_pid = []

    def verify(identity):
        if current_thread().name.startswith("b04-seal") and not entered.is_set():
            entered.set()
            assert release.wait(10)
        return original(identity)

    monkeypatch.setattr(store, "verify", verify)

    def add():
        return ClaimPlacementService(factory, credentials).add(
            actor,
            q.project_id,
            q.publication_id,
            q.manuscript_version_id,
            claim,
            None,
            "RESULTS",
            {"kind": "PARAGRAPH", "value": "p1"},
            "SUPPORTED",
            0,
            uuid4(),
        )

    with (
        ThreadPoolExecutor(max_workers=1, thread_name_prefix="b04-seal") as seal_pool,
        ThreadPoolExecutor(max_workers=1) as writer_pool,
    ):
        sealing = seal_pool.submit(service.freeze_manuscript_version, actor, cmd)
        try:
            assert entered.wait(10)
            writing = writer_pool.submit(add)
            # Observe a lock waiter; a scheduling sleep is not evidence.
            with engine.connect() as conn:
                pid = conn.execute(
                    text(
                        "SELECT pid FROM pg_stat_activity WHERE datname=current_database() AND query LIKE 'SELECT rb_phase2_lock_project%' AND wait_event_type='Lock' LIMIT 1"
                    )
                ).scalar_one_or_none()
            if pid is None:
                import time

                deadline = time.monotonic() + 5
                while pid is None and time.monotonic() < deadline:
                    with engine.connect() as conn:
                        pid = conn.execute(
                            text(
                                "SELECT pid FROM pg_stat_activity WHERE datname=current_database() AND wait_event_type='Lock' AND pid<>pg_backend_pid() LIMIT 1"
                            )
                        ).scalar_one_or_none()
            assert pid is not None
            freezer_pid.append(pid)
            with engine.connect() as conn:
                assert (
                    conn.execute(
                        text("SELECT cardinality(pg_blocking_pids(:pid))"), {"pid": pid}
                    ).scalar_one()
                    > 0
                )
        finally:
            release.set()
        assert sealing.result(timeout=10).status == "FROZEN"
        with pytest.raises(ResearchBaseError):
            writing.result(timeout=10)
    assert freezer_pid
    assert (
        service.get_manuscript_version(actor, q).placement_set_hash
        == preview.preview_placement_set_hash
    )


@pytest.mark.parametrize("owner", ["impact", "finding", "source_retraction", "review"])
def test_freeze_serializes_owner_changes_and_insert_phantoms(b04_env, owner, monkeypatch):
    from dataclasses import replace
    from time import monotonic
    from uuid import UUID

    from researchbase.application.governance import (
        CreateAuditFindingCommand,
        CreateImpactAssessmentCommand,
        GovernanceService,
        ProposedImpactTarget,
    )
    from researchbase.application.source_version import (
        CreateSourceVersion,
        SourceVersionService,
        TransitionSourceVersion,
        _material_from_row,
    )
    from researchbase.domain.source_version import FrozenSourceReference, SourceVersionKind
    from researchbase.foundation.execution_context import ExecutionContext
    from researchbase.foundation.time import SystemClock

    service, q, actor, factory, engine, credentials, store, claim, base = b04_env
    ClaimPlacementService(factory, credentials).add(
        actor,
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        claim,
        None,
        "RESULTS",
        {"kind": "PARAGRAPH", "value": "p1"},
        "SUPPORTED",
        0,
        uuid4(),
    )
    CitationPlacementService(factory, credentials).add(
        actor,
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        base[7],
        "INTRO",
        {"kind": "PARAGRAPH", "value": "p1"},
        "BACKGROUND",
        0,
        uuid4(),
    )
    review_evidence = None
    if owner == "review":
        from researchbase.application.scientific_conclusion import LiteratureInputRequest
        from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE

        evidence = base[2].create(actor, q.project_id, base[7], "improved recall", uuid4())
        review_evidence = UUID(evidence["id"])
        base[2].review(
            base[4], q.project_id, review_evidence, "VERIFIED", "Independent test review", uuid4()
        )
        conclusion = base[0].create(
            actor,
            q.project_id,
            "Reviewed test conclusion",
            SCOPE,
            "MODERATE",
            None,
            (),
            (LiteratureInputRequest(review_evidence, "SUPPORTS"),),
            uuid4(),
        )
        base[0].freeze(
            actor, q.project_id, conclusion.conclusion_id, conclusion.version_id, uuid4()
        )
        ClaimPlacementService(factory, credentials).add(
            actor,
            q.project_id,
            q.publication_id,
            q.manuscript_version_id,
            None,
            conclusion.version_id,
            "DISCUSSION",
            {"kind": "PARAGRAPH", "value": "p1"},
            "SUPPORTED",
            0,
            uuid4(),
        )
    preview = service.get_manuscript_version(actor, q)
    cmd = FreezeManuscriptCommand(
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        preview.preview_placement_set_hash,
        preview.preview_content_hash,
    )
    entered, release = Event(), Event()
    original = store.verify

    def verify(identity):
        if current_thread().name.startswith("b04-owner-freeze") and not entered.is_set():
            entered.set()
            assert release.wait(10)
        return original(identity)

    monkeypatch.setattr(store, "verify", verify)

    def writer():
        context = ExecutionContext(actor_id=actor.actor_id, request_id=uuid4(), client_type="test")
        governance = GovernanceService(factory, SystemClock())
        if owner == "review":
            return base[2].review(
                base[4], q.project_id, review_evidence, "DISPUTED", "Later test dispute", uuid4()
            )
        if owner == "impact":
            return governance.create_impact_assessment(
                CreateImpactAssessmentCommand(
                    q.project_id,
                    None,
                    {"test": "invalid"},
                    "invalid",
                    (ProposedImpactTarget("claim_version", claim, "invalid"),),
                    context,
                )
            )
        if owner == "finding":
            return governance.create_audit_finding(
                CreateAuditFindingCommand(
                    q.project_id,
                    "test",
                    "major",
                    "Test finding",
                    "Test phantom",
                    "claim_version",
                    claim,
                    context,
                )
            )
        with factory() as uow:
            row = uow.source_version.version(base[7])
            material = _material_from_row(uow.source_version, row)
        material = replace(
            material,
            version_kind=SourceVersionKind.RETRACTED,
            predecessor_source_version=FrozenSourceReference(base[7], row["content_hash"]),
            correction_basis_artifact=material.fulltext_artifact,
        )
        versions = SourceVersionService(factory, credentials)
        created = versions.create(CreateSourceVersion(actor, q.project_id, material, uuid4()))
        return versions.freeze(
            TransitionSourceVersion(
                actor, q.project_id, UUID(str(created["source_version_id"])), uuid4()
            )
        )

    with (
        ThreadPoolExecutor(max_workers=1, thread_name_prefix="b04-owner-freeze") as seal_pool,
        ThreadPoolExecutor(max_workers=1) as writer_pool,
    ):
        sealing = seal_pool.submit(service.freeze_manuscript_version, actor, cmd)
        try:
            assert entered.wait(10)
            writing = writer_pool.submit(writer)
            deadline = monotonic() + 5
            witness = None
            while witness is None and monotonic() < deadline:
                if writing.done():
                    writing.result()
                with engine.connect() as conn:
                    witness = conn.execute(
                        text(
                            "SELECT pid FROM pg_stat_activity WHERE datname=current_database() AND cardinality(pg_blocking_pids(pid))>0 AND pid<>pg_backend_pid() LIMIT 1"
                        )
                    ).scalar_one_or_none()
            assert witness is not None
        finally:
            release.set()
        frozen = sealing.result(timeout=15)
        writing.result(timeout=15)
    history = service.get_manuscript_version(actor, q)
    assert history.content_hash == frozen.content_hash
    assert history.current_validity == (
        "VALID" if owner == "finding" else "STALE" if owner == "review" else "INVALID"
    )


@pytest.mark.parametrize("expire", [False, True, "role"])
def test_first_share_wait_is_bounded_and_authority_is_fresh(b04_env, expire, monkeypatch):
    from time import monotonic

    from researchbase.application.manuscript_freeze import ManuscriptFreezeService
    from researchbase.foundation.errors import ErrorCode
    from researchbase.persistence.database import create_database_engine, create_session_factory
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    service, q, actor, _, engine, credentials, store, _, _ = b04_env
    preview = service.get_manuscript_version(actor, q)
    cmd = FreezeManuscriptCommand(
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        preview.preview_placement_set_hash,
        preview.preview_content_hash,
    )
    bounded = create_database_engine(
        engine.url.render_as_string(hide_password=False), b04_write_timeouts=True
    )
    sessions = create_session_factory(bounded)
    service = ManuscriptFreezeService(lambda: SqlAlchemyUnitOfWork(sessions), credentials, store)
    valid = [True]
    original = credentials.is_valid
    monkeypatch.setattr(
        credentials, "is_valid", lambda principal, at: valid[0] and original(principal, at)
    )
    until = None
    if expire == "role":
        with engine.begin() as conn:
            role, until = conn.execute(
                text("""UPDATE project_role_assignments SET
                effective_until=clock_timestamp()+interval '3 seconds',row_version=row_version+1
                WHERE actor_id=:actor AND project_id=:project AND role='OWNER'
                AND effective_until IS NULL RETURNING id,effective_until"""),
                {"actor": actor.actor_id, "project": q.project_id},
            ).one()
            conn.execute(
                text("""INSERT INTO project_role_events
                (id,role_assignment_id,actor_id,event_kind,occurred_at,reason,request_id)
                VALUES (:id,:role,:actor,'CLOSED',:until,'H2 scheduled expiry',:request)"""),
                {
                    "id": uuid4(),
                    "role": role,
                    "actor": actor.actor_id,
                    "until": until,
                    "request": uuid4(),
                },
            )
    try:
        with engine.connect() as blocker, ThreadPoolExecutor(max_workers=1) as pool:
            transaction = blocker.begin()
            blocker.execute(text("LOCK TABLE actors IN ROW EXCLUSIVE MODE"))
            future = pool.submit(service.freeze_manuscript_version, actor, cmd)
            try:
                deadline = monotonic() + 5
                witness = None
                while witness is None and monotonic() < deadline:
                    with engine.connect() as conn:
                        witness = conn.execute(
                            text(
                                "SELECT a.pid,clock_timestamp() FROM pg_stat_activity a JOIN pg_locks l ON l.pid=a.pid WHERE a.datname=current_database() AND NOT l.granted AND l.relation='actors'::regclass AND l.mode='ShareLock' LIMIT 1"
                            )
                        ).one_or_none()
                assert witness is not None
                if expire == "role":
                    assert witness[1] < until
                if expire:
                    if expire == "role":
                        blocker.execute(
                            text(
                                "SELECT pg_sleep(GREATEST(0, EXTRACT(EPOCH FROM (:until-clock_timestamp()))+0.1))"
                            ),
                            {"until": until},
                        )
                        assert blocker.execute(
                            text("SELECT clock_timestamp()>=:until"), {"until": until}
                        ).scalar_one()
                    else:
                        valid[0] = False
                    transaction.rollback()
                with pytest.raises(ResearchBaseError) as exc:
                    future.result(timeout=15)
                assert exc.value.code == (
                    ErrorCode.FORBIDDEN if expire else ErrorCode.CONCURRENT_MODIFICATION
                )
            finally:
                if transaction.is_active:
                    transaction.rollback()
    finally:
        bounded.dispose()
    valid[0] = True
    assert (
        service.get_manuscript_version(b04_env[-1][4] if expire == "role" else actor, q).status
        == "DRAFT"
    )


@pytest.mark.parametrize("protocol", ["decision", "novelty_coverage", "novelty_claim"])
def test_mixed_existing_repository_lock_protocols(b04_env, protocol, monkeypatch):
    from time import monotonic

    from researchbase.application.scientific_conclusion import ClaimInputRequest
    from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE

    service, q, actor, factory, engine, _, store, claim, base = b04_env
    conclusion = base[0].create(
        actor,
        q.project_id,
        "Test mixed-protocol target",
        SCOPE,
        "MODERATE",
        None,
        (ClaimInputRequest(claim, "SUPPORTS"),),
        (),
        uuid4(),
    )
    base[0].freeze(actor, q.project_id, conclusion.conclusion_id, conclusion.version_id, uuid4())
    preview = service.get_manuscript_version(actor, q)
    command = FreezeManuscriptCommand(
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        preview.preview_placement_set_hash,
        preview.preview_content_hash,
    )
    entered, release = Event(), Event()
    original = store.verify

    def verify(identity):
        if current_thread().name.startswith("b04-mixed") and not entered.is_set():
            entered.set()
            assert release.wait(10)
        return original(identity)

    monkeypatch.setattr(store, "verify", verify)

    def owner_lock_probe():
        # Exercise the existing owner coordination helpers without changing their protocol.
        with factory() as uow:
            if protocol == "decision":
                uow.decision.lock_request(uuid4())
                assert uow.decision.target(conclusion.version_id, q.project_id) is not None
                uow.decision.lock_snapshot()
            elif protocol == "novelty_coverage":
                uow.novelty.prepare("coverage", uuid4())
            else:
                uow.novelty.prepare("assessment", uuid4(), claim)
            uow.literature_search_plan.lock_project(q.project_id)
            uow.commit()

    with (
        ThreadPoolExecutor(max_workers=1, thread_name_prefix="b04-mixed") as freezing,
        ThreadPoolExecutor(max_workers=1) as owners,
    ):
        sealed = freezing.submit(service.freeze_manuscript_version, actor, command)
        try:
            assert entered.wait(10)
            owner = owners.submit(owner_lock_probe)
            deadline = monotonic() + 5
            witness = None
            while witness is None and monotonic() < deadline:
                if owner.done():
                    owner.result()
                with engine.connect() as conn:
                    witness = conn.execute(
                        text(
                            "SELECT pid FROM pg_stat_activity WHERE datname=current_database() AND cardinality(pg_blocking_pids(pid))>0 LIMIT 1"
                        )
                    ).scalar_one_or_none()
            assert witness is not None
        finally:
            release.set()
        result = sealed.result(timeout=15)
        owner.result(timeout=15)
    assert service.get_manuscript_version(actor, q) == result


@pytest.mark.parametrize("operation", ["update", "delete", "reparent"])
def test_freeze_vs_direct_placement_mutation(b04_env, operation, monkeypatch):
    from time import monotonic

    from sqlalchemy.exc import DBAPIError

    from researchbase.application.publication import PublicationService

    service, q, actor, factory, engine, credentials, store, claim, _ = b04_env
    item = ClaimPlacementService(factory, credentials).add(
        actor,
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        claim,
        None,
        "RESULTS",
        {"kind": "PARAGRAPH", "value": "p1"},
        "SUPPORTED",
        0,
        uuid4(),
    )
    publications = PublicationService(factory, credentials, store)
    parent = publications.create_publication(actor, q.project_id, "PAPER", "Destination", uuid4())
    document = service.get_manuscript_version(actor, q).document_artifact_version_id
    destination = publications.create_draft(
        actor, q.project_id, parent.id, document, "Destination", None, "INITIAL", uuid4()
    )
    preview = service.get_manuscript_version(actor, q)
    cmd = FreezeManuscriptCommand(
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        preview.preview_placement_set_hash,
        preview.preview_content_hash,
    )
    entered, release = Event(), Event()
    original = store.verify

    def verify(identity):
        if current_thread().name.startswith("b04-placement") and not entered.is_set():
            entered.set()
            assert release.wait(10)
        return original(identity)

    monkeypatch.setattr(store, "verify", verify)

    def mutate():
        sql = {
            "update": "UPDATE manuscript_claim_placements SET section_id='MOVED' WHERE id=:id",
            "delete": "DELETE FROM manuscript_claim_placements WHERE id=:id",
            "reparent": "UPDATE manuscript_claim_placements SET manuscript_version_id=:destination WHERE id=:id",
        }[operation]
        with engine.begin() as conn:
            conn.execute(text(sql), {"id": item.id, "destination": destination.id})

    with (
        ThreadPoolExecutor(max_workers=1, thread_name_prefix="b04-placement") as freezing,
        ThreadPoolExecutor(max_workers=1) as writers,
    ):
        sealing = freezing.submit(service.freeze_manuscript_version, actor, cmd)
        try:
            assert entered.wait(10)
            writing = writers.submit(mutate)
            deadline = monotonic() + 5
            witness = None
            while witness is None and monotonic() < deadline:
                with engine.connect() as conn:
                    witness = conn.execute(
                        text(
                            "SELECT a.pid FROM pg_stat_activity a JOIN pg_locks l ON l.pid=a.pid WHERE a.datname=current_database() AND NOT l.granted AND l.relation='manuscript_claim_placements'::regclass LIMIT 1"
                        )
                    ).scalar_one_or_none()
            assert witness is not None
        finally:
            release.set()
        frozen = sealing.result(timeout=15)
        with pytest.raises(DBAPIError) as exc:
            writing.result(timeout=15)
        assert getattr(exc.value.orig, "sqlstate", None) == "P04M1"
    assert service.get_manuscript_version(actor, q) == frozen


def test_h2_connection_and_local_bounds_survive_rollback_without_pool_leak(b04_env):
    from researchbase.persistence.database import create_database_engine
    from researchbase.persistence.manuscript_freeze_repository import B04_SHARE_SQL
    from tests.integration.phase2 import pr2_20_support as s

    engine = b04_env[4]
    bounded = create_database_engine(
        engine.url.render_as_string(hide_password=False), b04_write_timeouts=True
    )

    def settings(conn):
        return tuple(
            conn.execute(
                text("SELECT current_setting('lock_timeout'),current_setting('statement_timeout')")
            ).one()
        )

    try:
        with engine.connect() as ordinary:
            defaults = settings(ordinary)
        with bounded.connect() as conn:
            assert settings(conn) == ("10s", "30s")
        with s.capture(bounded) as capture:
            with bounded.connect() as conn:
                conn.execute(text(B04_SHARE_SQL))
                conn.execute(text("SET LOCAL lock_timeout='1s'"))
                conn.execute(text("SET LOCAL statement_timeout='2s'"))
                assert settings(conn) == ("1s", "2s")
                conn.rollback()
        assert capture.transaction_first_statements == [B04_SHARE_SQL]
        with bounded.connect() as conn:
            assert settings(conn) == ("10s", "30s")
        with engine.connect() as ordinary:
            assert settings(ordinary) == defaults
    finally:
        bounded.dispose()
